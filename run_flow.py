import asyncio
import os
import sys
import time
import threading
import argparse

from app.agent.radis import Radis
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.logger import logger
from app.config import config
import api
from app.display import print_ascii_banner_with_stars, ArtifactDisplay

def print_banner():
    """Print welcome banner for AgentRadis Flow"""
    print_ascii_banner_with_stars()
    print("\nA versatile AI agent with flow capabilities.")

def print_help():
    """Print usage information"""
    print("\nUsage: python run_flow.py [OPTIONS] [PROMPT]")
    print("\nOptions:")
    print("  --help           Show this help message and exit")
    print("  --api            Start the API server in standalone mode")
    print("  --web            Start API server and web interface")
    print("  --config         Show current configuration")
    print("\nExamples:")
    print("  python run_flow.py \"What is the weather in New York?\"")
    print("  python run_flow.py --web")
    print("  python run_flow.py --api")

async def run_flow_interactive():
    """Run the flow in interactive mode"""
    print_banner()
    agents = {
        "radis": Radis(),
    }

    try:
        prompt = input("Enter your prompt: ")

        if prompt.strip().isspace() or not prompt:
            logger.warning("Empty prompt provided.")
            return

        flow = FlowFactory.create_flow(
            flow_type=FlowType.PLANNING,
            agents=agents,
        )
        logger.warning("Processing your request...")

        try:
            start_time = time.time()
            result = await asyncio.wait_for(
                flow.execute(prompt),
                timeout=3600,  # 60 minute timeout for the entire execution
            )
            elapsed_time = time.time() - start_time
            logger.info(f"Request processed in {elapsed_time:.2f} seconds")
            logger.info(result)
        except asyncio.TimeoutError:
            logger.error("Request processing timed out after 1 hour")
            logger.info(
                "Operation terminated due to timeout. Please try a simpler request."
            )

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")

# Add this function to help detect and handle failed searches
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

# Then modify the run_flow_with_prompt function to handle failed searches
async def run_flow_with_prompt(prompt, verbose=False, **kwargs):
    """Run a flow with a specific prompt."""
    agents = {
        "radis": Radis(),
    }
    agent = agents["radis"]

    try:
        if not prompt or prompt.strip() == "":
            logger.warning("Empty prompt provided.")
            return "No prompt provided. Please specify what you'd like to know."

        # Check API connectivity first
        if not check_api_connectivity():
            return "Error: Could not connect to LLM API. Please check your configuration and ensure the API server is running."

        flow = FlowFactory.create_flow(
            flow_type=FlowType.PLANNING,
            agents=agents,
        )
        logger.warning(f"Processing request: {prompt}")

        try:
            start_time = time.time()

            # Execute the prompt with multiple attempts if needed
            max_attempts = 3  # Allow up to 3 attempts for failed searches
            attempt = 0
            result = None
            current_prompt = prompt

            while attempt < max_attempts:
                result = await asyncio.wait_for(
                    flow.execute(current_prompt),
                    timeout=3600  # 1 hour timeout
                )

                # Check if the result indicates a failed search
                response_text = extract_response_from_result(result)
                if is_failed_search_response(response_text) and attempt < max_attempts - 1:
                    attempt += 1
                    if verbose:
                        print(f"\nSearch attempt {attempt} failed. Trying a different approach...")

                    # Add a follow-up message to trigger a new search approach
                    current_prompt = "That search didn't provide useful results. Please try a different search query or approach to answer the original question."
                else:
                    # Either we got good results or we've reached max attempts
                    break

            return extract_output(result, prompt, verbose, start_time)

        except asyncio.TimeoutError:
            logger.error("Request processing timed out after 1 hour")
            return "Operation terminated due to timeout. Please try a simpler request."
        except Exception as e:
            # Check for common errors and provide better messages
            error_str = str(e)
            if "ChatCompletionMessageToolCall" in error_str and "name" in error_str:
                logger.error("Error: API format mismatch with tool calls. This may be due to LM Studio API compatibility issues.")
                return "The LLM's response format is incompatible with the expected tool call format. Try updating to a newer version of the LLM API server."
            if "RetryError" in error_str and "APIConnectionError" in error_str:
                logger.error("Error: Failed to connect to the LLM API after multiple retries.")
                return "Could not establish a stable connection to the language model. Please check your API endpoint and network connection."
            # Re-raise for general handling
            raise

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return f"Error processing your request: {str(e)}"
    finally:
        # Ensure resources are cleaned up
        try:
            await agent._cleanup_resources()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Helper function to extract response text from result for checking
def extract_response_from_result(result):
    """Extract the response text from the result object for analysis"""
    if isinstance(result, str):
        return result
    elif hasattr(result, 'response'):
        return result.response
    elif isinstance(result, dict) and 'response' in result:
        return result['response']
    return str(result)

def start_api_server_thread():
    """Start the API server in a separate thread"""
    print("Starting API server...")
    api_thread = threading.Thread(target=api.start_api_server)
    api_thread.daemon = True
    api_thread.start()
    print(f"API server running at http://localhost:5000")
    print("Visit http://localhost:5000 in your browser to use the web interface")
    return api_thread

def check_api_connectivity():
    """Check if the LLM API is accessible"""
    llm_config = config.get_llm_config()

    # Try different field names for the base URL
    base_url = None
    for field in ['api_base', 'base_url']:
        if hasattr(llm_config, field) and getattr(llm_config, field):
            base_url = getattr(llm_config, field)
            break

    if not base_url:
        print("\nWarning: No API base URL configured. Check your config.toml file.")
        return False

    # Add /models endpoint to test if not already present
    test_url = base_url
    if not test_url.endswith('/'):
        test_url += '/'
    if not test_url.endswith('models'):
        test_url += 'models'

    print(f"\nTesting connection to LLM API at: {base_url}")

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

# Parse command line arguments
parser = argparse.ArgumentParser(description="AgentRadis Flow Runner")
parser.add_argument("prompt", nargs="?", help="The prompt to process")
parser.add_argument("--api", action="store_true", help="Start API server")
parser.add_argument("--web", action="store_true", help="Start web interface")
parser.add_argument("--config", action="store_true", help="Show current configuration")
parser.add_argument("--flow", action="store_true", help="Use Flow execution mode")
parser.add_argument("--verbose", action="store_true", help="Show verbose output including errors")
def main():
    """Main entry point with command line argument handling"""
    # Parse arguments
    args = parser.parse_args()

    # Set up error handling based on verbose flag
    setup_error_handling(args.verbose)

    # Show help message if no arguments provided
    if len(sys.argv) == 1:
        print_banner()
        print_help()
        return

    # Show configuration
    if args.config:
        print_banner()
        from app.config import print_config
        print_config()
        return

    # Start API server if requested
    if args.api or args.web:
        print_banner()
        api_thread = start_api_server_thread()
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
        return

    # Run flow with prompt if provided
    if args.prompt:
        print_banner()
        try:
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
                result_lines = result.split('\n')
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
        asyncio.run(run_flow_interactive())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"\nError: {str(e)}")

# Error redirection for cleaner output
def setup_error_handling(verbose=False):
    """Redirect error output to a log file unless verbose mode is enabled"""
    if not verbose:
        try:
            # Create logs directory if it doesn't exist
            os.makedirs("logs", exist_ok=True)

            # Redirect stderr to a log file
            sys.stderr = open(os.path.join("logs", f"errors_{int(time.time())}.log"), "w")
        except Exception:
            # Fall back to normal error output if redirection fails
            pass

def extract_output(result, prompt, verbose=False, start_time=None):
    """Extract the key information from the result (exclude error messages)"""
    if verbose and start_time is not None:
        elapsed_time = time.time() - start_time
        print(f"Request processed in {elapsed_time:.2f} seconds")
        # Display the result using our formatter
        clean_result = result if isinstance(result, str) else str(result)
        ArtifactDisplay.format_result(clean_result, "Complete Results")
        return result

    # Extract the key information from the result (exclude error messages)
    if isinstance(result, str):
        # Remove or simplify common error messages
        clean_result = result.replace("Error in browser cleanup during destruction: There is no current event loop in thread 'MainThread'.", "")
        clean_result = clean_result.replace("Error cleaning up browser resources", "")

        # Extract the final response from the response field if available
        if "response='" in clean_result and "'" in clean_result.split("response='", 1)[1]:
            # Extract the response field value
            response_part = clean_result.split("response='", 1)[1].split("'", 1)[0]
            # Check if it contains any actual text (not just newlines or empty)
            if response_part.strip():
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
                ArtifactDisplay.format_result(result_text, "Result")
                return result_text

        # Remove technical details if the result is too long
        if len(clean_result) > 500 and not verbose:
            result_text = "The agent processed your request but the response contains technical details. Please use the --verbose flag for full output."
            ArtifactDisplay.format_result(result_text, "Result")
            return result_text

        # Format the clean result
        ArtifactDisplay.format_result(clean_result.strip(), "Result")
        return clean_result.strip()
    
    # Format the result if it's not a string
    result_text = str(result)
    ArtifactDisplay.format_result(result_text, "Result")
    return result

if __name__ == "__main__":
    # Run the main function
    main()
