#!/usr/bin/env python3

# Suppress deprecation warnings at the very top
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", module="app.schema")

import sys
import os
import asyncio
import threading
import traceback
import json
import time
import logging
import httpx
from typing import Optional, Dict, Any
from pydantic import BaseModel, ValidationError
import argparse
import app.tool  # Ensure tool registration happens early

from app.logger import logger
from rich.console import Console
from rich.box import DOUBLE
from rich.panel import Panel
from app.agent import EnhancedRadis, Radis
from app.flow.flow_factory import FlowFactory
from app.flow.base import FlowType
from app.config import config
from app.core.tool_registry import get_tool_registry # Import the registry getter
from app.display import ArtifactDisplay
from app.agent.response_processor import ResponseProcessor
from app.agent.identity_context import RadisIdentityContext
from app.errors import (
    ValidationError,
    ConfigurationError,
    APIConnectionError,
    IdentityError,
    ToolError,
    ResourceError,
    ConfigurationError
)

async def check_api_connectivity() -> bool:
    """Check if the API endpoint is accessible.
    
    Returns:
        bool: True if API is accessible, False otherwise
    """
    try:
        api_base = config.current_llm_config.api_base
        if not api_base:
            logger.warning("API base URL not configured")
            return False
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                api_base,
                timeout=5.0
            )
            return response.status_code < 400
    except (httpx.RequestError, httpx.HTTPError) as e:
        logger.warning(f"API connectivity check failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during API connectivity check: {str(e)}")
        return False
import api

# Create argument parser
# Create argument parser - will be configured fully in setup_argument_parser()
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("prompt", nargs="?", help="Query to process")  # Make prompt optional
parser.add_argument("-h", "--help", action="store_true", help="Show help message")
parser.add_argument("--debug", action="store_true", help="Enable debug mode")
parser.add_argument("--api", action="store_true", help="Start API server")
parser.add_argument("--web", action="store_true", help="Start web interface")
parser.add_argument("--config", action="store_true", help="Show configuration")
parser.add_argument("--flow", action="store_true", help="Use Flow execution mode")
parser.add_argument("--verbose", action="store_true", help="Show verbose output")

class QueryRequest(BaseModel):
    """Pydantic model for validating incoming query requests"""
    query: str


class RadisFlow:
    """Main flow for processing queries through the Radis agent"""
    
    def __init__(self, debug=False):
        """Initialize the flow with identity context and agent"""
        self.debug = debug
        self.response_processor = ResponseProcessor()
        self.identity_context = RadisIdentityContext()
        # Fetch tools from the now-populated registry
        tool_registry = get_tool_registry()
        registered_tools = tool_registry.list_tools()
        self.agent = EnhancedRadis(
            api_base=None,  # Add api_base to match interface
            planning_tool=None,  # Add planning_tool to match interface
            model="gpt-3.5-turbo",  # Specify default model
            temperature=0.7,  # Add default temperature
            identity_context=self.identity_context,
            tools=registered_tools # Pass registered tools explicitly
        )
        
    def validate_request(self, request_data: Dict[str, Any]) -> QueryRequest:
        """Validate incoming request data using Pydantic model"""
        try:
            if isinstance(request_data, str):
                request_data = {"query": request_data}
            return QueryRequest(**request_data)
        except ValidationError as e:
            raise ValidationError(f"Invalid request format: {str(e)}")

    async def process_query(self, query: str | Dict[str, Any]) -> Dict[str, Any]:
        """Process a user query through the agent."""
        logger.info("=== Starting New Query Processing ===")
        
        try:
            # Validate request
            request = self.validate_request(query)
            logger.info(f"Received query: {request.query}")
            
            # Check identity context
            if not self.identity_context.validate_request(request.query):
                raise IdentityError("Request contains invalid identity references")
            
            # Initialize processing
            logger.info("Initializing query processing...")
            
            # Get agent response
            raw_response = await self.agent.run(request.query)
            
            try:
                response = self.response_processor.sanitize_response(raw_response)
            except ResourceError as e:
                logger.warning(f"Sanitization warning: {e}")
                response = raw_response  # Fallback to original response
            
            # Handle string responses immediately
            if isinstance(response, str):
                formatted_response = self._format_response(response)
            else:
                # Process dictionary responses with get() methods
                if response.get("status") == "thinking":
                    logger.info(f"Thinking: {response.get('thought', 'Processing your request...')}")
                
                if response.get("status") == "using_tool":
                    tool_name = response.get("tool", "unknown")
                    tool_action = response.get("action", "performing task")
                    logger.info(f"Using tool {tool_name}: {tool_action}")
                
                # Format the response
                formatted_response = self._format_response(response)
            
            logger.info("=== Query Processing Complete ===")
            return formatted_response
            
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "error_type": "validation_error"
            }
        except IdentityError as e:
            logger.error(f"Identity error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "error_type": "identity_error"
            }
        except ResourceError as e:
            logger.error(f"Sanitization error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "error_type": "sanitization_error",
                "details": response
            }


    #flow = FlowFactory.create_flow(
    #    flow_type=FlowType.PLANNING,
    #    agents=agents,
    #    planning_tool=planning_tool
    #)
    #logger.warning("Processing your request...")

#        try:
#            start_time = time.time()
#            result = await asyncio.wait_for(
#                flow.execute(prompt),
#                timeout=3600,  # 60 minute timeout for the entire execution
#            )
#            elapsed_time = time.time() - start_time
#            logger.info(f"Request processed in {elapsed_time:.2f} seconds")
#            logger.info(result)
#        except asyncio.TimeoutError:
#            logger.error("Request processing timed out after 1 hour")
#            logger.info(
#                "Operation terminated due to timeout. Please try a simpler request."
#            )

#    except KeyboardInterrupt:
#        logger.info("Operation cancelled by user.")
#    except Exception as e:
#        logger.error(f"Error: {str(e)}")

## Add this function to help detect and handle failed searches
def is_failed_search_response(response):
    """Check if a response indicates a failed search where only the search URL was returned"""
    failed_indicators = [
        "just returned the search query itself",
        "search result just returned",
        "returned a link to Google Search itself",
        "No search results found",
        "didn't provide any useful information",
        "I need to refine my search"
    ]
    return any(indicator in response for indicator in failed_indicators)

async def run_flow_with_prompt(prompt: str, verbose=False, planning_tool=None, plan_id=None, **kwargs) -> dict:
    """Run the flow with the given prompt and return the result.
    
    Args:
        prompt (str): The input prompt to process
        verbose (bool, optional): Enable verbose logging. Defaults to False.
        planning_tool (PlanningTool, optional): Planning tool instance. Defaults to None.
        plan_id (str, optional): ID of an existing plan. Defaults to None.
        **kwargs: Additional keyword arguments
        
    Returns:
        dict: Response containing result or error information
    """
    try:
        # Check API connectivity before proceeding
        if not await check_api_connectivity():
            error_msg = "API endpoint is not accessible. Please check your connection and configuration."
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "details": "API connectivity check failed. Ensure the API endpoint is correctly configured and accessible."
            }

        # Import here to avoid circular imports
        from app.tool.planning import PlanningTool

        # Ensure we have a valid PlanningTool instance
        if planning_tool is None:
            # Initialize planning tool with the task
            planning_tool = PlanningTool()
            # Create initial plan
            logger.info(f"Creating initial plan with task: {prompt}")
            try:
                plan_result = await planning_tool.run(task=prompt)
                if hasattr(plan_result, 'content'):
                    plan_result = plan_result.content
                if isinstance(plan_result, dict) and plan_result.get('status') == 'error':
                    logger.error(f"Failed to create plan: {plan_result.get('error')}")
            except Exception as e:
                logger.error(f"Error creating plan: {e}")

        # Fetch tools from the now-populated registry
        tool_registry = get_tool_registry()
        registered_tools = tool_registry.list_tools()

        agents = {
            "radis": Radis(planning_tool=planning_tool, tools=registered_tools), # Pass registered tools
        }
        agent = agents["radis"]

        # Create a context accumulator for tool results
        tool_context = {
            "accumulated_results": [],
            "search_history": [],
            "failed_attempts": []
        }

        if not prompt or prompt.strip() == "":
            logger.warning("Empty prompt provided.")
            return {
                'status': 'error',
                'error': 'No prompt provided. Please specify what you\'d like to know.',
                'processed_response': 'No prompt provided. Please specify what you\'d like to know.'
            }

        # Check API connectivity first
        try:
            if not await check_api_connectivity():
                return {
                    'status': 'error',
                    'error': 'Error: Could not connect to LLM API. Please check your configuration and ensure the API server is running.',
                    'processed_response': 'Error: Could not connect to LLM API. Please check your configuration and ensure the API server is running.'
                }
        except Exception as e:
            logger.warning(f"API connectivity check failed: {e}")
            # Continue anyway to handle offline mode or custom configurations

        # Create a consistent plan ID if one isn't provided
        if plan_id is None:
            plan_id = f"plan_{int(time.time())}"

        # Initialize flow with proper task context
        # Create a FlowFactory instance first
        flow_factory = FlowFactory(config)
        
        # Create initial context with all necessary information
        initial_context = {
            "agents": agents,
            "planning_tool": planning_tool,
            "plan_id": plan_id,
            "task": prompt  # Pass the task explicitly
        }
        
        # Call create_flow with the correct parameters
        flow = flow_factory.create_flow(
            flow_type=FlowType.PLANNING,
            system_message="You are an AI assistant that helps users accomplish tasks.",
            initial_context=initial_context,
            max_turns=10,
            timeout=300
        )

        # Ensure the flow has access to the planning context
        if hasattr(flow, 'set_planning_context'):
            flow.set_planning_context({
                'task': prompt,
                'plan_id': plan_id,
                'tool_context': {}
            })

        logger.warning(f"Processing request: {prompt}")

        try:
            start_time = time.time()
            
            # Setup variables for retry logic
            max_attempts = 3  # Maximum number of retry attempts
            attempt = 0
            result = None
            current_prompt = prompt

            while attempt < max_attempts:
                # Incorporate previous tool results into the context if available
                if attempt > 0 and tool_context["accumulated_results"]:
                    # Format accumulated tool results as context for the model
                    tool_results_context = "\n\nPrevious tool results:\n"
                    for idx, result_info in enumerate(tool_context["accumulated_results"]):
                        tool_results_context += f"{idx+1}. Tool '{result_info['tool_name']}': {result_info['result']}\n"

                    # Add search history context if available
                    if tool_context["search_history"]:
                        tool_results_context += "\n\nPrevious search queries attempted:\n"
                        for idx, query in enumerate(tool_context["search_history"]):
                            tool_results_context += f"{idx+1}. {query}\n"

                    # Combine original prompt with tool results for better context
                    if attempt == 1:
                        # On first retry, include the original prompt with tool context
                        current_prompt = f"{prompt}\n\n{tool_results_context}\n\nThe previous attempt didn't provide useful results. Please use the above information and try a different approach to answer the original question."
                    else:
                        # On subsequent retries, be more specific about what failed
                        current_prompt = f"{prompt}\n\n{tool_results_context}\n\nMultiple approaches have failed. Please analyze why previous attempts failed and try a completely different strategy to answer the original question."

                # Execute the flow with current context
                # Task is already set in planning context
                result = await asyncio.wait_for(
                    flow.execute(current_prompt),
                    timeout=3600  # 1 hour timeout
                )

                # Extract message content if it's a Message object
                if hasattr(result, 'content'):
                    result = {'response': result.content}

                # Check for planning-specific errors
                if isinstance(result, dict) and result.get('status') == 'error':
                    if 'No task provided' in result.get('error', ''):
                        logger.error("Planning error: No task provided")
                        # Retry with explicit task
                        # Update planning context with retry information
                        if hasattr(flow, 'set_planning_context'):
                            flow.set_planning_context({
                                'task': current_prompt,
                                'plan_id': plan_id,
                                'tool_context': {},
                                'retry_count': attempt + 1
                            })
                        result = await asyncio.wait_for(
                            flow.execute(current_prompt),
                            timeout=3600
                        )

                # Extract and store tool results from this execution for future context
                if isinstance(result, dict) and 'tool_calls' in result:
                    for tool_call in result['tool_calls']:
                        tool_name = tool_call.get('name', '')
                        tool_args = tool_call.get('args', {})
                        tool_result = tool_call.get('result', {})

                        # Store the tool result
                        tool_context["accumulated_results"].append({
                            'tool_name': tool_name,
                            'args': tool_args,
                            'result': tool_result
                        })

                        # Track search queries specifically
                        if tool_name == 'web_search' and isinstance(tool_args, dict):
                            query = tool_args.get('query', '')
                            if query:
                                tool_context["search_history"].append(query)

                # Check if the result indicates a failed search
                response_text = extract_response_from_result(result)
                if is_failed_search_response(response_text) and attempt < max_attempts - 1:
                    attempt += 1
                    if verbose:
                        print(f"\nSearch attempt {attempt} failed. Trying a different approach...")

                    # Track this failed attempt
                    tool_context["failed_attempts"].append({
                        'attempt': attempt,
                        'response': response_text
                    })
                else:
                    # Either we got good results or we've reached max attempts
                    break

            # Process and format the response
            processed_response = await process_response(result, tool_context)

            # Return both the original result and the processed response
            if isinstance(result, dict):
                result['processed_response'] = processed_response
                # Include tool context in the result for future reference
                result['tool_context'] = tool_context
                return result
            else:
                return {
          
                    'response': result,
                    'processed_response': processed_response,
                    'tool_context': tool_context
                }
        except asyncio.TimeoutError:
            logger.error("Request processing timed out after 1 hour")
            return {
                'status': 'error',
                'error': 'Operation terminated due to timeout. Please try a simpler request.',
                'processed_response': 'Operation terminated due to timeout. Please try a simpler request.'
            }
        except Exception as e:
            # Check for common errors and provide better messages
            error_str = str(e)
            if "ChatCompletionMessageToolCall" in error_str and "name" in error_str:
                logger.error("Error: API format mismatch with tool calls. This may be due to LM Studio API compatibility issues.")
                return {
                    'status': 'error',
                    'error': 'The LLM\'s response format is incompatible with the expected tool call format. Try updating to a newer version of the LLM API server.',
                    'processed_response': 'The LLM\'s response format is incompatible with the expected tool call format. Try updating to a newer version of the LLM API server.'
                }
            if "RetryError" in error_str and "APIConnectionError" in error_str:
                logger.error("Error: Failed to connect to the LLM API after multiple retries. Please check your API base URL and network connection.")
                return {
                    'status': 'error',
                    'error': 'Could not establish a stable connection to the language model. Please check your API endpoint and network connection.',
                    'processed_response': 'Could not establish a stable connection to the language model. Please check your API endpoint and network connection.'
                }
            # Re-raise for general handling
            raise


    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'processed_response': f"Radis: I encountered an error while processing your request: {str(e)}"
        }
    finally:
        # Ensure resources are cleaned up
        try:
            await agent.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

async def process_response(result, tool_context):
    """Process and format the response with tool insights"""
    def clean_text(text):
        """Helper to clean and format response text"""
        if not text:
            return ""
        clean_lines = [
            line.strip() for line in text.split('\n')
            if line.strip() and not line.strip().startswith(('Step', 'INFO', 'WARNING', 'ERROR'))
        ]
        return '\n'.join(clean_lines)
        
    try:
        # Extract main response from result
        main_response = ""
        tool_insights = []
        
        # Extract the main response text
        if isinstance(result, str):
            main_response = result
        elif isinstance(result, dict):
            if 'processed_response' in result and result['processed_response']:
                main_response = result['processed_response']
            elif 'response' in result:
                response_obj = result['response']
                if isinstance(response_obj, str):
                    main_response = response_obj
                elif hasattr(response_obj, 'content'):
                    main_response = response_obj.content
            
            # Process tool calls if available
            if 'tool_calls' in result and result['tool_calls']:
                for tool_call in result['tool_calls']:
                    tool_name = tool_call.get('name', '')
                    tool_result = tool_call.get('result', {})
                    
                    # Handle web search results
                    if tool_name == 'web_search' and isinstance(tool_result, dict):
                        results = tool_result.get('results', [])
                        if results:
                            for result in results[:3]:  # Top 3 results
                                title = result.get('title', '')
                                snippet = result.get('snippet', '')
                                if title and snippet:
                                    tool_insights.append(f"• {title}: {snippet}")
                    elif tool_result:
                        tool_insights.append(f"• {tool_name}: {tool_result}")
        
        # If we have tool context from previous attempts, use that
        if not tool_insights and tool_context and tool_context.get("accumulated_results"):
            for result_info in tool_context["accumulated_results"]:
                tool_name = result_info.get('tool_name', '')
                result = result_info.get('result', '')
                
                if tool_name == 'web_search' and isinstance(result, dict):
                    search_results = result.get('results', [])
                    if search_results:
                        for sr in search_results[:3]:  # Top 3 results
                            title = sr.get('title', '')
                            snippet = sr.get('snippet', '')
                            if title and snippet:
                                tool_insights.append(f"• {title}: {snippet}")
                elif result:
                    tool_insights.append(f"• {tool_name}: {result}")
        
        # Build final response
        main_response = clean_text(main_response)
        tool_insights_text = "\n".join(tool_insights) if tool_insights else ""
        
        if main_response and tool_insights_text:
            if tool_context and tool_context.get("accumulated_results"):
                return f"Radis: {main_response}\n\n[Source Information]\n{tool_insights_text}"
            return f"Radis: {main_response}"
        elif main_response:
            return f"Radis: {main_response}"
        elif tool_insights_text:
            return f"Radis: Based on my findings:\n\n{tool_insights_text}"
        
        return "Radis: I processed your request but couldn't generate a meaningful response."
    except Exception as e:
        import traceback
        print(f"Error in process_response: {e}")
        print(traceback.format_exc())
        return f"Radis: I encountered an error while processing your request. Please try again."

def extract_response_from_result(result):
    """Extract the response text from the result object for analysis"""
    if result is None:
        return "No response available."
        
    # Handle string result
    if isinstance(result, str):
        return result
    
    # Handle Message objects
    if hasattr(result, 'content'):
        content = getattr(result, 'content')
        return content if content is not None else "No content available."
    
    # Handle objects with response attribute
    if hasattr(result, 'response'):
        response = result.response
        if response is None:
            return "No response available."
        if isinstance(response, str):
            return response
        if hasattr(response, 'content'):
            content = getattr(response, 'content')
            return content if content is not None else "No content available."
        return str(response)
    
    # Handle dictionary with response key
    if isinstance(result, dict) and 'response' in result:
        response = result['response']
        if response is None:
            return "No response available."
        if isinstance(response, str):
            return response
        if hasattr(response, 'content'):
            content = getattr(response, 'content')
            return content if content is not None else "No content available."
        return str(response)
    
    return "Unable to extract response from result."
# Main entry point with command line argument handling
def main():
    """Main entry point with command line argument handling"""
    try:
        # Parse arguments, but catch the exit to handle missing required arguments
        args = parser.parse_args()
        
        # Always show banner first
        print_flow_ascii_banner_with_stars()
        
        # Show help if no args provided or help flag is set
        if args.help or len(sys.argv) == 1:
            print_help(parser)
            return
        
        # Set up error handling based on verbose flag
        setup_error_handling(args.verbose)
        
        # Create console for rich formatting
        console = Console()

        # Show configuration    
        if args.config:
            # Banner already displayed at the beginning of main()
            from app.config import print_config
            print_config()
            return

        # Start API server if requested
        if args.api or args.web:
            api_thread = start_api_server_thread()
            try:
                # Keep main thread alive
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")
            return

        # Run flow with prompt if provided
        # Run flow with prompt if provided
        if args.prompt:
            try:
                result = asyncio.run(run_flow_with_prompt(args.prompt, args.verbose))
                if result:
                    # Try to use colorful output if possible
                    colored = None
                    has_colors = False
            except Exception as e:
                print(f"Error running flow with prompt: {e}")
    except Exception as e:
        print(f"Unhandled error in main: {e}")


def test_llm_connection(test_url):
    """Test connection to the LLM API endpoint"""
    import httpx
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(test_url)
            if response.status_code < 400:
                print(f"✓ Successfully connected to LLM API")
                return True
            else:
                print(f"✗ API server returned status code {response.status_code}")
                return False
    except httpx.ConnectError:
        print(f"✗ Could not connect to API server. Is LM Studio running?")
        return False
    except Exception as e:
        print(f"✗ Error connecting to API: {str(e)}")
        return False
def setup_argument_parser():
    """Set up argument parser with detailed help and all available arguments"""
    parser = argparse.ArgumentParser(
        description='AgentRadis Flow Runner - Execute and manage flow-based operations',
        usage=None,  # Disable default usage
        add_help=False  # Disable built-in help
    )
    # Add arguments with groups for better organization
    required = parser.add_argument_group('Required Arguments')
    optional = parser.add_argument_group('Optional Arguments')
    
    # Required arguments
    required.add_argument('prompt', nargs='?', help='Query or prompt to process through the flow system')
    
    # Optional arguments
    optional.add_argument('--help', '-h', action='store_true', help='Show this help message')
    optional.add_argument('--debug', action='store_true', help='Enable debug mode for detailed logging')
    optional.add_argument('--api', action='store_true', help='Start the API server for remote access')
    optional.add_argument('--web', action='store_true', help='Start the web interface')
    optional.add_argument('--config', action='store_true', help='Show current configuration settings')
    optional.add_argument('--flow', action='store_true', help='Use Flow execution mode for advanced processing')
    optional.add_argument('--verbose', action='store_true', help='Show verbose output including debug information')
    return parser

def check_llm_config() -> bool:
    """Validate LLM configuration settings and print friendly error messages"""
    console = Console()
    try:
        llm_config = config.get_llm_config()
        
        # Check for required configuration fields
        if not hasattr(llm_config, 'model') or not llm_config.model:
            console.print("[red]Error: Missing 'model' in LLM configuration[/red]")
            console.print("[yellow]Please set the 'model' field in your config.toml file.[/yellow]")
            return False
            
    except Exception as e:
        console = Console()
        console.print(f"[red]Error: {str(e)}[/red]")
        return
        
    # Run interactive mode if no prompt provided
    try:
        asyncio.run(run_flow_interactive())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"\nError: {str(e)}")
        return False

def main():
    """Main entry point with command line argument handling"""
    try:
        # Parse arguments, but catch the exit to handle missing required arguments
        args = parser.parse_args()
        
        # Always show banner first
        print_flow_ascii_banner_with_stars()
        
        # Show help if no args provided or help flag is set
        if args.help or len(sys.argv) == 1:
            print_help(parser)
            return
        
        # Set up error handling based on verbose flag
        setup_error_handling(args.verbose)
        
        # Create console for rich formatting
        console = Console()

    except Exception as e:
        console = Console()
        console.print(f"[red]Error: {str(e)}[/red]")
        return

    # Show configuration    
    if args.config:
        # Banner already displayed at the beginning of main()
        from app.config import print_config
        print_config()
        return

    # Start API server if requested
    if args.api or args.web:
        # Banner already displayed at the beginning of main()
        api_thread = start_api_server_thread()
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")
        return

    # Banner already displayed at the beginning of main()

    # Run flow with prompt if provided
    if args.prompt:
        try:
            # Validate LLM config first
            if not check_llm_config():
                console = Console()
                console.print("[red]Error: Missing LLM configuration. Please check your configuration file.[/red]")
                return
                
            result = asyncio.run(run_flow_with_prompt(args.prompt, args.verbose))
            if result:
                # Try to use colorful output if possible
                colored = None
                has_colors = False
                try:
                    from termcolor import colored
                    has_colors = True
                except ImportError:
                    has_colors = False

                # Print the result in a highlighted, easy-to-read format
                print("\n")

                # Create a prominent header
                if has_colors and colored is not None:
                    header = colored("┌" + "─" * 78 + "┐", "cyan")
                    title = colored("│", "cyan") + colored(" RESULT ", "white", "on_cyan") + " " * 70 + colored("│", "cyan")
                    footer = colored("└" + "─" * 78 + "┘", "cyan")
                    print(header)
                    print(title)
                    print(footer)
                else:
                    print("┌" + "─" * 78 + "┐")
                    print("│" + " RESULT " + " " * 70 + "│")
                    print("└" + "─" * 78 + "┘")
                print()

                # Split the result into lines and format each line
                result_lines = result.get('processed_response', '').split('\n')
                for line in result_lines:
                    # Wrap long lines
                    if len(line) > 76:
                        wrapped_lines = [line[i:i+76] for i in range(0, len(line), 76)]
                        for wrapped in wrapped_lines:
                            if has_colors and colored is not None:
                                print("  " + colored(wrapped, "white"))
                            else:
                                print("  " + wrapped)
                    else:
                        if has_colors and colored is not None:
                            print("  " + colored(line, "white"))
                        else:
                            print("  " + line)

                print("\n")

                # Only show shutdown and error messages if verbose mode is enabled
                if args.verbose:
                    print("System Information:")
                    print("=" * 50)
                    print("Operation completed successfully.")
                    print("=" * 50)
                else:
                    if has_colors and colored is not None:
                        print(colored("Operation completed.", "green"))
                    else:
                        print("Operation completed.")
            else:
                print("\nNo result returned. Check logs for errors.")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
        except Exception as e:
            print(f"\nError: {str(e)}")
        return

    # Run interactive mode if no prompt provided
    try:
        # Validate LLM config first
        if not check_llm_config():
            console = Console()
            console.print("[red]Error: Missing LLM configuration. Please check your configuration file.[/red]")
            return
            
        asyncio.run(run_flow_interactive())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"\nError: {str(e)}")
    except SystemExit:
        # If parsing fails for some reason, we've already shown help
        return

def setup_error_handling(verbose=False):
    """Set up error handling based on verbose flag"""
    if verbose:
        # Show full errors in verbose mode
        # Show full errors in verbose mode
        logging.basicConfig(level=logging.DEBUG)
    else:
        # Redirect errors to log file in normal mode
        logging.basicConfig(level=logging.ERROR, 
                           filename='radis_error.log',
                           filemode='a')

# Import the ASCII banner function from app/display.py
# Import the ASCII banner function from app/display.py
from app.display import print_ascii_banner_with_stars
def print_flow_ascii_banner_with_stars():
    """Display the Flow Runner ASCII banner with stars and capabilities"""
    # Call the centralized ASCII banner function
    print_ascii_banner_with_stars()
    
    # Create console for rich formatting
    console = Console()
    
    
    # Create capabilities panel with rich styling
    capabilities_content = (
        "[bold]• Executes predefined flows using natural language queries[/bold]\n"
        "[bold]• Processes inputs through configured flow pipelines[/bold]\n"
        "[bold]• Supports multiple flow types and execution strategies[/bold]\n"
        "[bold]• Maintains context and state throughout flow execution[/bold]\n"
        "[bold]• Provides detailed error handling and execution tracing[/bold]\n"
        "[bold]• Supports integration with external tools and services[/bold]"
    )
    
    # Create and display the panel with capabilities
    capabilities_panel = Panel(
        capabilities_content,
        title="Flow Runner Capabilities",
        title_align="center",
        box=DOUBLE,
        style="cyan",
        border_style="cyan"
    )
    console.print(capabilities_panel)
    console.print()
def print_help(parser):
    """Print help information with rich formatting"""
    console = Console()
    
    console.print("\n[bold]Usage:[/bold]")
    console.print("  python run_flow.py [prompt]     Process a query or prompt")
    console.print("  python run_flow.py --help       Show this detailed help message")
    console.print("  python run_flow.py --api        Start the API server")
    console.print("  python run_flow.py --web        Start the web interface")
    console.print("  python run_flow.py --config     Show current configuration")
    console.print("  python run_flow.py --verbose    Show verbose output")
    console.print("  python run_flow.py --debug      Enable debug mode")
    console.print("  python run_flow.py --flow       Use Flow execution mode\n")

    console.print("[bold]Description:[/bold]")
    console.print("  AgentRadis Flow Runner enables powerful flow-based operations through")
    console.print("  natural language queries. It provides a flexible system for executing")
    console.print("  complex flows, managing state, and integrating with external tools.\n")

    console.print("[bold]Arguments:[/bold]")
    # Get argument help from argparse
    for action in parser._actions:
        if action.option_strings:  # Optional arguments
            opts = ', '.join(action.option_strings)
            console.print(f"  {opts:<20} {action.help}")
        elif action.dest != 'help':  # Positional arguments, excluding help
            console.print(f"  {action.dest:<20} {action.help}")
    console.print("")

async def run_flow_interactive():
    """Run the flow in interactive mode"""
    # Banner already displayed in main()
    print("Interactive mode. Type 'exit' to quit.\n")
    
    while True:
        prompt = input("\nEnter your query: ")
        if prompt.lower() in ["exit", "quit"]:
            break
            
        if prompt.strip():
            result = await run_flow_with_prompt(prompt)
            if 'processed_response' in result:
                print("\n" + result['processed_response'] + "\n")
            else:
                print("\n" + str(result) + "\n")

def extract_output(result, prompt, verbose=False, start_time=None):
    """Extract the key information from the result (exclude error messages)"""
    logger.info(f"Extracting output from result type: {type(result)}")

    if verbose and start_time is not None:
        elapsed_time
        elapsed_time = time.time() - start_time
        print(f"Request processed in {elapsed_time:.2f} seconds")
        # Display the result using our formatter
        clean_result = result if isinstance(result, str) else str(result)
        ArtifactDisplay.format_result(clean_result, "Complete Results")
        logger.debug(f"Verbose complete results: {clean_result}")
        return result

    # For proper JSON response handling with some models like Gemma
    try:
        if isinstance(result, dict):
            logger.info("Processing dictionary result")
            # Check for processed_response in the result which is our preferred format
            if 'processed_response' in result and result['processed_response']:
                processed = result['processed_response']
                logger.info(f"Found processed_response: {processed[:100]}...")
                ArtifactDisplay.format_result(processed, "Result")
                return processed
            
            # Check for direct response key
            if 'response' in result:
                response_value = result['response']
                logger.info(f"Found response key, type: {type(response_value)}")
                
                # Handle string responses
                if isinstance(response_value, str) and response_value.strip():
                    ArtifactDisplay.format_result(response_value.strip(), "Result")
                    return response_value.strip()
                
                # Handle object responses with content attribute (Message objects)
                if hasattr(response_value, 'content') and getattr(response_value, 'content'):
                    content = getattr(response_value, 'content')
                    logger.info(f"Extracted content from object: {content[:100]}...")
                    ArtifactDisplay.format_result(content, "Result")
                    return content
                
                # Try converting to string as fallback
                if response_value:
                    str_response = str(response_value)
                    if str_response.strip():
                        logger.info(f"Converted response to string: {str_response[:100]}...")
                        ArtifactDisplay.format_result(str_response.strip(), "Result")
                        return str_response.strip()
            
            # Look for tool calls if no direct response
            if 'tool_calls' in result and result['tool_calls']:
                logger.info(f"Processing {len(result['tool_calls'])} tool calls")
                tool_texts = []
                for tool_call in result['tool_calls']:
                    tool_name = tool_call.get('name', 'unknown')
                    tool_result = tool_call.get('result', {})
                    
                    # Try to extract readable content from tool result
                    if isinstance(tool_result, dict) and 'results' in tool_result:
                        # Likely search results
                        results = tool_result['results']
                        for idx, res in enumerate(results[:3]):  # Show top 3
                            if isinstance(res, dict):
                                title = res.get('title', '')
                                snippet = res.get('snippet', '')
                                if title and snippet:
                                    tool_texts.append(f"{idx+1}. {title}: {snippet}")
                    elif isinstance(tool_result, str) and tool_result.strip():
                        tool_texts.append(f"{tool_name} result: {tool_result.strip()}")
                    elif isinstance(tool_result, (dict, list)) and tool_result:
                        tool_texts.append(f"{tool_name} result: {str(tool_result)}")
                
                if tool_texts:
                    combined = "Based on the tools I used, here's what I found:\n\n" + "\n\n".join(tool_texts)
                    logger.info(f"Constructed response from tool results: {combined[:100]}...")
                    ArtifactDisplay.format_result(combined, "Result")
                    return combined

    except Exception as e:
        logger.error(f"Error processing dictionary result: {e}")
    
    # Extract the key information from string results (exclude error messages)
    if isinstance(result, str):
        logger.info("Processing string result")
        # Remove or simplify common error messages
        clean_result = result.replace("Error in browser cleanup during destruction: There is no current event loop in thread 'MainThread'.", "")
        clean_result = clean_result.replace("Error cleaning up browser resources", "")

        # Special handling for Gemma model responses which might include JSON-like structures
        if "```json" in clean_result and "```" in clean_result.split("```json", 1)[1]:
            logger.info("Found JSON code block in response")
            json_part = clean_result.split("```json", 1)[1].split("```", 1)[0].strip()
            try:
                import json
                json_data = json.loads(json_part)
                if isinstance(json_data, dict):
                    if 'response' in json_data and json_data['response']:
                        extracted = json_data['response']
                        logger.info(f"Extracted JSON response: {extracted[:100]}...")
                        ArtifactDisplay.format_result(extracted, "Result")
                        return extracted
                    # Try other common response fields
                    for field in ['content', 'answer', 'message', 'text', 'output']:
                        if field in json_data and json_data[field]:
                            extracted = json_data[field]
                            logger.info(f"Extracted JSON {field}: {extracted[:100]}...")
                            ArtifactDisplay.format_result(extracted, "Result")
                            return extracted
            except Exception as e:
                logger.error(f"Error parsing JSON from response: {e}")

        # Generic handling for code blocks that might contain responses
        code_block_markers = ["```", "```python", "```text"]
        for marker in code_block_markers:
            if marker in clean_result and "```" in clean_result.split(marker, 1)[1]:
                logger.info(f"Found code block with marker: {marker}")
                code_part = clean_result.split(marker, 1)[1].split("```", 1)[0].strip()
                if code_part and len(code_part) > 20:  # Only if it has substantial content
                    logger.info(f"Extracted code block: {code_part[:100]}...")
                    ArtifactDisplay.format_result(code_part, "Result")
                    return code_part

        # Extract the final response from the response field if available
        if "response='" in clean_result and "'" in clean_result.split("response='", 1)[1]:
            # Extract the response field value
            response_part = clean_result.split("response='", 1)[1].split("'", 1)[0]
            # Check if it contains any actual text (not just newlines or empty)
            if response_part.strip():
                logger.info(f"Extracted response field: {response_part[:100]}...")
                ArtifactDisplay.format_result(response_part.strip(), "Result")
                return response_part.strip()

        # If that didn't work, look for any useful user-facing text
        # First check if there's a proper agent response message
        if "ASSISTANT: 'assistant'>, content='" in clean_result:
            parts = clean_result.split("ASSISTANT: 'assistant'>, content='")
            for part in parts[1:]:  # Skip the first part before the pattern
                if "'" in part:
                    content = part.split("'", 1)[0].strip()
                    if content and content != "" and not content.startswith("[TOOL_REQUEST]"):
                        logger.info(f"Extracted assistant content: {content[:100]}...")
                        ArtifactDisplay.format_result(content, "Result")
                        return content

        # Otherwise, clean up memory dump and return the result
        # Remove multiple blank lines
        while "\n\n\n" in clean_result:
            clean_result = clean_result.replace("\n\n\n", "\n\n")

        # Try to extract key information from tool results if present
        if "Tool result:" in clean_result:
            tool_results = []
            for line in clean_result.split("\n"):
                if "Tool result:" in line:
                    tool_results.append(line.split("Tool result:", 1)[1].strip())

            if tool_results:
                result_text = "Based on the tools I used, here's what I found:\n\n" + "\n".join(tool_results)
                logger.info(f"Constructed from tool results: {result_text[:100]}...")
                ArtifactDisplay.format_result(result_text, "Result")
                return result_text

        # Remove technical details if the result is too long
        if len(clean_result) > 500 and not verbose:
            result_text = "The agent processed your request but the response contains technical details. Please use the --verbose flag for full output."
            logger.info("Result too technical and long, providing simplified response")
            ArtifactDisplay.format_result(result_text, "Result")
            return result_text

        # Format the clean result
        logger.info(f"Using cleaned string result: {clean_result[:100]}...")
        ArtifactDisplay.format_result(clean_result.strip(), "Result")
        return clean_result.strip()
    
    # Handle message objects directly (common with Gemma models)
    if hasattr(result, 'content'):
        content = getattr(result, 'content')
        if content and isinstance(content, str):
            logger.info(f"Extracted message content: {content[:100]}...")
            ArtifactDisplay.format_result(content.strip(), "Result")
            return content.strip()
    
    # Final fallback: just convert to string
    str_result = str(result).strip()
    logger.info(f"Using string conversion as fallback: {str_result[:100]}...")
    ArtifactDisplay.format_result(str_result, "Result")
    return str_result

if __name__ == "__main__":
    # Run the main function
    main()
