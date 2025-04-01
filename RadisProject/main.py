#!/usr/bin/env python3
"""Tool for Radis configuration management."""

# Standard library imports
import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
from app.core.tool_registry import get_tool_registry, ToolNotFoundError, ToolRegistryError
from logging.handlers import RotatingFileHandler
import shutil
import signal
import sys
import threading
import time
import traceback
from typing import Any, Dict, List, Optional, Union
import warnings

# Configure deprecation warnings with more granular control
warnings.filterwarnings("ignore", category=DeprecationWarning, module=".*urllib3.*")
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, module=".*pkg_resources.*"
)
warnings.filterwarnings(
    "once", category=DeprecationWarning
)  # Show other deprecation warnings once

# ANSI escape codes for colors
RED = "\033[91m"
RESET = "\033[0m"

# Configure warnings
import warnings

warnings.simplefilter("ignore", DeprecationWarning)

# Third-party imports
import httpx

import app.tool  # Ensure tool registration happens early
from app.tool.time_tool import TimeTool
# Local imports
from app.display import (
    ThinkingHandler,
    print_ascii_banner_with_stars,
    display_system_introduction,
)
from app.config import config, RadisConfig, SecurityConfig
from app.agent import EnhancedRadis
from app.ui.display import ToolDisplay, ArtifactDisplay, ProgressDisplay, setup_display
from app.tool.planning import create_planning_tool
from app.tool.base import BaseTool
from app.errors import (
    PlanningError,
    ConfigurationError,
    RadisExecutionError,
    RadisToolError,
    RadisAuthenticationError,
    RadisValidationError,
)
from app.schema import Plan, Result
from run_flow import RadisFlow, run_flow_with_prompt


async def parse_arguments():
    """Parse and return command line arguments"""
    parser = argparse.ArgumentParser(description="AgentRadis - A versatile AI agent")
    parser.add_argument("prompt", nargs="?", help="Prompt to process")
    parser.add_argument("--web", action="store_true", help="Start the web interface")
    parser.add_argument("--api", action="store_true", help="Start the API server")
    parser.add_argument("--api-base", type=str, help="Override the API base URL")
    parser.add_argument(
        "--port", type=int, default=5000, help="Port for web/API server"
    )
    parser.add_argument("--flow", action="store_true", help="Use flow-based execution")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--config", type=str, help="Path to custom configuration file")
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level",
    )
    parser.add_argument(
        "--model-path", type=str, help="Path to a local model file (.gguf, .safetensors)"
    )
    parser.add_argument(
        "--check-api", action="store_true", help="Check API connectivity and exit"
    )
    return parser.parse_args()


async def load_configuration(args):
    """Load and validate configuration settings"""
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {args.config}")
        config.load_from_file(config_path)

    llm_config = config.get_llm_config()
    if not llm_config:
        raise ConfigurationError("Failed to load LLM configuration")

    # Ensure api_base attribute exists or handle appropriately
    api_base_from_config = getattr(llm_config, "api_base", None)
    api_base = args.api_base or api_base_from_config

    # Check for model_path first and override config if provided
    if args.model_path:
        llm_config.model_path = args.model_path
        # If model_path is set, api_base is not strictly required for loading,
        # but might be needed for other parts or if loading fails.
        # We'll keep the api_base check for now, but prioritize model_path.
        if not api_base:
            logger.warning("Local model path provided, but no API base URL configured. API-based features might fail.")
    elif not api_base:
        # Only raise error if neither model_path nor api_base is available
        raise ConfigurationError(
            "No API base URL or model path configured. Please provide --api-base or --model-path or configure in config file."
        )

    return api_base


def setup_logging(args):
    """Configure logging with thinking handler"""
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    if args.debug:
        log_level = logging.DEBUG

    # Get the root logger and set initial level
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers to prevent duplicates
    root_logger.handlers.clear()

    # Configure formatters and handlers
    formatter = logging.Formatter(config.logging.format)

    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # Add file handler if path is specified
    if config.logging.file_path:
        try:
            # Ensure log directory exists
            log_dir = Path(config.logging.file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                config.logging.file_path,
                maxBytes=config.logging.max_file_size * 1024 * 1024,
                backupCount=config.logging.backup_count,
            )
            # File handler level respects the overall log level
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

            # Use print for initial file setup message since logging might not be ready
            print(f"File logging configured at: {config.logging.file_path}")
        except Exception as e:
            # Use print here as logging might not be fully set up
            print(f"Failed to set up file logging: {e}")

    # Log successful setup
    root_logger.info(f"Logging level set to {logging.getLevelName(log_level)}")
    return root_logger


async def main():
    """Main entry function with enhanced error handling"""
    args = await parse_arguments()
    setup_logging(args)  # Setup logging early
    logger = logging.getLogger("app")  # Define logger after setup

    # ANSI color codes for display
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    CYAN = "\033[96m"

    # Define separators
    USER_SEPARATOR = "===" * 27
    TASK_SEPARATOR = "⋆⋆⋆" * 27
    RESULT_SEPARATOR = "•••" * 27

    # --- Main execution logic ---
    try:
        api_base = await load_configuration(args)  # Load config after logging is set up

        if args.check_api:
            # Run API connectivity check and exit
            await check_api_connectivity()
            return

        if args.web:
            # Start web UI
            logo = r"""    _                      _   ____            _ _
   / \   __ _  ___ _ __  | |_|  _ \ __ _  __| (_)___
  / _ \ / _` |/ _ \ '_ \ | __| |_) / _` |/ _` | / __|
 / ___ \ (_| |  __/ | | || |_|  _ < (_| | (_| | \__ \
/_/   \_\__, |\___|_| |_| \__|_| \_\__,_|\__,_|_|___/
        |___/
        """
            print("\n\033[1;36m" + logo + "\033[0m")
            print(
                "Your gateway to the internet awaits and Radis will be your guide. Embrace the cosmos."
            )
            print("Type 'exit' to quit.")
            print("    ")

            port = args.port  # Default is set in argparse
            print(f"🌐 Starting AgentRadis Web Interface on port {port}")

            # Import API start function here to avoid circular dependency issues if api.py imports main elements
            try:
                from api import start_api_server as start_web_api_server
            except ImportError:
                logger.error(
                    "Could not import start_api_server from api.py for web mode."
                )
                sys.exit(1)

            # Run the async web server function
            # This assumes start_web_api_server is an async function
            # Running directly in the main loop might block other async tasks if not careful
            # Consider uvicorn or hypercorn for production deployment
            logger.info(f"Attempting to start web server on 0.0.0.0:{port}")
            # Note: Running the server directly like this might be suitable for simple cases,
            # but a dedicated ASGI server runner (like uvicorn) is generally preferred.
            # If start_web_api_server itself uses uvicorn.run(), this might be okay.
            await start_web_api_server(host="0.0.0.0", port=port)
            # If it returns immediately, the server might be running in the background.
            # If it blocks, the following code won't run until the server stops.
            print("Web server process started (or finished if it doesn't block).")
            # Keep alive loop might be needed if server runs in background thread implicitly
            # try:
            #     while True: await asyncio.sleep(3600) # Sleep for an hour
            # except KeyboardInterrupt:
            #     print("\nShutting down AgentRadis Web Interface...")

            return  # Exit main after starting web server (or if it blocks)

        elif args.api:
            # Start API server
            print(f"\U0001f680 Starting AgentRadis API Server on port {args.port}")
            # Assuming start_api_server_thread is defined and works correctly
            # Make sure api.py is importable and start_api_server is async
            try:
                from api import start_api_server

                logger.info(f"Attempting to start API server on 0.0.0.0:{args.port}")
                # Run the API server directly in the main event loop
                await start_api_server(host="0.0.0.0", port=args.port)
                # If start_api_server blocks, execution stops here until server exits.
            except ImportError:
                logger.error(
                    "Could not import start_api_server from api.py for API mode."
                )
                sys.exit(1)
            except Exception as api_err:
                logger.error(f"Failed to start API server: {api_err}", exc_info=True)
                sys.exit(1)

            return  # Exit main after starting API server

        elif args.prompt:
            # Process a single prompt
            print_ascii_banner_with_stars()
            display_system_introduction()
            print(f"Running AgentRadis with prompt: {args.prompt}")

            # Create a shared PlanningTool instance with error handling
            try:
                planning_tool = create_planning_tool()
                logger.info("PlanningTool initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize PlanningTool: {e}", exc_info=True)
                print(
                    f"{RED}Error: Could not initialize planning capabilities - {str(e)}{RESET}"
                )
                sys.exit(1)

            if args.flow:
                # Use flow-based execution
                logger.info("Using flow-based execution for single prompt.")
                await run_flow_with_prompt(args.prompt, planning_tool=planning_tool)
            else:
                # Use standard agent execution with debug mode
                logger.info("Using standard agent execution for single prompt.")
                # Create agent instance with planning tool
                agent = await create_agent(api_base, planning_tool)
                response = await agent.run(args.prompt)

                # Print the response in a nice box format
                print_response_box("RESULT", response)
                print("\nOperation completed.")
        else:
            # Start interactive mode
            print_ascii_banner_with_stars()
            display_system_introduction()
            print("Starting interactive mode...")
            # Initialize display elements for interactive mode
            progress = ProgressDisplay()
            artifacts = ArtifactDisplay()

            async def interactive_session(
                agent_instance,
                debug=False,
                progress_display=None,
                artifact_display=None,
            ):
                """Run an interactive session with the agent"""
                try:
                    # Send welcome message first
                    print(
                        f"\n{BLUE}{BOLD}Radis:{RESET} Hi! I'm Radis, your true Omni agent! We can just chat, or I can carry out whatever task you need!"
                    )
                    print("Starting interactive session...\n")
                    while True:
                        # Get user input
                        try:
                            user_input = input(f"\n{GREEN}{BOLD}You:{RESET} ").strip()
                        except EOFError:  # Handle piped input ending
                            print("\nInput stream closed. Exiting interactive session.")
                            break

                        if not user_input:
                            continue

                        if user_input.lower() in ["exit", "quit"]:
                            break

                        # Let the agent decide if tools are needed
                        print(f"\n{USER_SEPARATOR}") # Separator before processing

                        if progress_display:
                            progress_display.show_thinking()
                        try:
                            # Call agent.run directly and handle display here
                            response = await agent_instance.run(user_input)

                            # Handle display of response, tools, artifacts
                            if isinstance(response, dict):
                                # Process artifacts first if needed
                                for artifact in safe_iterate(
                                    response.get("artifacts", [])
                                ):
                                    if artifact_display:
                                        # Assuming ArtifactDisplay has a method to show various types
                                        if artifact["type"] == "code":
                                            artifact_display.code_preview(
                                                artifact["content"],
                                                artifact.get("language", "python"),
                                            )
                                        elif artifact["type"] == "web":
                                            artifact_display.web_preview(
                                                artifact["content"]
                                            )
                                        elif artifact["type"] == "project":
                                            artifact_display.project_structure(
                                                artifact["content"]
                                            )
                                        # Add more artifact types as needed
                                        else:
                                            logger.warning(
                                                f"Unsupported artifact type: {artifact.get('type')}"
                                            )

                                # Process tool calls
                                for tool_call in safe_iterate(
                                    response.get("tool_calls", [])
                                ):
                                    # Display tool call and result (assuming ToolDisplay exists)
                                    # ToolDisplay.show_tool_call(
                                    #     tool_call.get("name"), tool_call.get("args")
                                    # )
                                    # ToolDisplay.show_tool_result(
                                    #     tool_call.get("result"),
                                    #     tool_call.get("success", True),
                                    # )
                                    # Basic print for now if ToolDisplay is complex
                                    print(f"\n{CYAN}Tool Call:{RESET} {tool_call.get('name')}({tool_call.get('args')})")
                                    print(f"{CYAN}Tool Result:{RESET} {tool_call.get('result')}")


                                # Display final response text
                                print_response_box(
                                    "RESULT", response.get("response", "")
                                )
                            else:
                                print_response_box("RESULT", str(response))

                        except RadisExecutionError as e:
                            logger.error(f"Execution error: {e}", exc_info=debug)
                            print(f"\n{RED}❌ Execution Error: {str(e)}{RESET}")
                        except RadisToolError as e:
                            logger.error(f"Tool error: {e}", exc_info=debug)
                            print(f"\n{RED}❌ Tool Error: {str(e)}{RESET}")
                        except RadisAuthenticationError as e:
                            logger.error(f"Authentication error: {e}", exc_info=debug)
                            print(f"\n{RED}❌ Authentication Error: {str(e)}{RESET}")
                        except RadisValidationError as e:
                            logger.error(f"Validation error: {e}", exc_info=debug)
                            print(f"\n{RED}❌ Validation Error: {str(e)}{RESET}")
                        except Exception as e:
                            logger.error(f"Unexpected error: {e}", exc_info=debug)
                            print(f"\n{RED}❌ Unexpected Error: {str(e)}{RESET}")
                            if debug:
                                print("\nError details:", traceback.format_exc())
                        finally:
                            if progress_display:
                                progress_display.stop_thinking()  # Ensure thinking stops

                except KeyboardInterrupt:
                    print("\nSession terminated by user.")
                except Exception as e:
                    logger.error(f"Interactive session error: {e}", exc_info=True)
                    print(f"\n{RED}Session error: {str(e)}{RESET}")

            # Create a shared PlanningTool instance for interactive mode
            try:
                interactive_planning_tool = create_planning_tool()
                logger.info("Interactive PlanningTool initialized successfully")
            except Exception as e:
                logger.error(
                    f"Failed to initialize interactive PlanningTool: {e}", exc_info=True
                )
                print(
                    f"{RED}Error: Could not initialize planning capabilities for interactive mode - {str(e)}{RESET}"
                )
                sys.exit(1)

            interactive_agent = await create_agent(api_base, interactive_planning_tool)
            await interactive_session(
                interactive_agent,
                debug=args.debug,
                progress_display=progress,
                artifact_display=artifacts,
            )

    # Correctly indented except/finally blocks for the main try statement
    except ConfigurationError as e:
        # Logger might not be fully configured if error happens early
        print(f"{RED}Configuration error: {e}{RESET}")
        # Attempt to log anyway
        if "logger" in locals():
            logger.error(f"Configuration error: {e}", exc_info=True)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        # Perform cleanup if possible
        # await cleanup_resources() # Might need loop handling if called here
    except Exception as e:
        print(f"{RED}An unexpected error occurred: {str(e)}{RESET}")
        # Attempt to log
        if "logger" in locals():
            logger.critical(f"Unhandled error in main: {e}", exc_info=True)
        # Optionally print traceback if not logged
        # traceback.print_exc()
        sys.exit(1)
    finally:
        # This will run even if sys.exit() was called in the try/except blocks
        print("Radis shutting down...")
        # Consider if cleanup is needed here vs. signal handler
        # If the loop is running, cleanup might need scheduling
        # loop = asyncio.get_event_loop()
        # if loop.is_running():
        #     loop.create_task(cleanup_resources())


async def create_agent(
    api_base: Optional[str] = None, planning_tool: Optional["PlanningTool"] = None
) -> EnhancedRadis:
    """Create a new agent instance with comprehensive tool initialization logging"""
    logger = logging.getLogger("app")  # Ensure logger is accessible
    logger.info(
        f"Creating agent instance. API Base: {'Provided' if api_base else 'Default'}, Planning Tool: {'Provided' if planning_tool else 'None'}"
    )
    print("\nInitializing agent and tools...")

    # Get the core tool registry instance
    try:
        tool_registry = get_tool_registry()
        logger.info("Successfully obtained core tool registry")
    except ToolRegistryError as e:
        logger.error(f"Failed to get core tool registry: {e}")
        raise RuntimeError(f"Failed to initialize tool registry: {e}") from e

    # Create configuration objects
    # Use the global config object which load_configuration updated
    llm_config = config.get_llm_config()
    radis_config = RadisConfig(
        api_base=api_base, # Keep passing api_base for potential direct use or fallback
        model_name=llm_config.model,
        # Pass model_path explicitly if needed by RadisConfig or agent internals
        # model_path=llm_config.model_path
    )
    # Note: EnhancedRadis likely uses the global `config` internally to get the full LLMConfig,
    # including the potentially updated model_path. Passing it via RadisConfig might be redundant
    # depending on EnhancedRadis implementation.

    security_config = SecurityConfig(
        workspace_dir=config.get_workspace_config()["workspace_dir"],
        allowed_tools=config.get_security_config().allowed_tools,
        max_tokens=config.get_security_config().max_tokens,
        restricted_paths=config.get_security_config().restricted_paths,
    )

    # Pass planning_tool, configurations, and registered tools
    try:
        # Get all registered tools from the core registry
        registered_tools = tool_registry.list_tools()
        logger.info(f"Retrieved {len(registered_tools)} tools from core registry")

        agent = EnhancedRadis(
            config=radis_config, # Pass the potentially updated config
            security_config=security_config,
            planning_tool=planning_tool,
            tools=registered_tools  # Pass pre-registered tools from core registry
        )
    except ToolNotFoundError as e:
        logger.error(f"Failed to retrieve tools from registry: {e}")
        raise RuntimeError(f"Tool retrieval error: {e}") from e
    except ToolRegistryError as e:
        logger.error(f"Registry error while creating agent: {e}")
        raise RuntimeError(f"Registry error: {e}") from e

    try:
        # Initialize core tools first
        logger.info("Setting up core agent components...")
        await agent.async_setup()  # This likely initializes internal tools/components

        # Verify tools were properly registered with the agent
        available_tools = agent.get_tools()
        available_tool_names = []
        for tool in available_tools:
            try:
                # Verify each tool exists in the core registry
                if hasattr(tool, "name"):
                    tool_name = tool.name
                    tool_registry.get_tool(tool_name)  # Verify tool exists in registry
                    available_tool_names.append(tool_name)
                else:
                    available_tool_names.append(str(tool))
            except ToolNotFoundError as e:
                logger.warning(f"Tool not found in core registry: {e}")
            except ToolRegistryError as e:
                logger.warning(f"Registry error during tool verification: {e}")

        logger.info(
            f"Found {len(available_tool_names)} tools registered: {', '.join(available_tool_names)}"
        )

        # Track initialization status
        tool_status = {
            "total": len(available_tool_names),
            "initialized": 0,
            "failed": 0,
            "status_by_tool": {},
        }

        # Verify each registered tool seems operational (add specific checks if needed)
        for tool in available_tools:
            try:
                tool_name = tool.name if hasattr(tool, "name") else str(tool)
                if tool is None:
                    raise ValueError("Tool instance not found")

                # Add specific verification logic per tool if necessary
                # e.g., check API keys for web search tool, file paths for file tool, etc.
                success = True  # Assume success unless verification fails
                error_msg = None

                # Example: Special handling for web search tool verification
                # if tool_name == 'web_search':
                #     success = await verify_web_search_tool(agent) # Assuming verify_web_search_tool exists
                #     if not success: error_msg = "Web search tool verification failed."

                # Basic validation: Check if required methods exist (example)
                if not hasattr(tool, "run") or not callable(getattr(tool, "run")):
                    success = False
                    error_msg = (
                        f"Tool '{tool_name}' is missing a callable 'run' method."
                    )

                if success:
                    log_tool_initialization(tool_name, True)
                    tool_status["initialized"] += 1
                else:
                    log_tool_initialization(
                        tool_name, False, error_msg or "Generic validation failed"
                    )
                    tool_status["failed"] += 1

                tool_status["status_by_tool"][tool_name] = success

            except Exception as tool_init_error:
                error_msg = f"Failed during initialization/verification of {tool_name}: {str(tool_init_error)}"
                logger.error(error_msg, exc_info=True)
                log_tool_initialization(tool_name, False, str(tool_init_error))
                tool_status["failed"] += 1
                tool_status["status_by_tool"][tool_name] = False

        # Log comprehensive initialization summary
        summary_msg = (
            f"Tool initialization summary: {tool_status['initialized']} successful, "
            f"{tool_status['failed']} failed out of {tool_status['total']} total tools."
        )
        if tool_status["failed"] > 0:
            logger.warning(summary_msg)
            failed_tools = [
                name
                for name, status in tool_status["status_by_tool"].items()
                if not status
            ]
            logger.warning(f"Failed tools: {', '.join(failed_tools)}")
        else:
            logger.info(summary_msg)

        logger.info("Agent created successfully.")
        return agent

    except Exception as e:
        error_msg = f"Failed during core agent setup or tool verification: {str(e)}"
        logger.critical(
            error_msg, exc_info=True
        )  # Use critical for agent creation failure
        # Raising RuntimeError to indicate a fundamental setup failure
        raise RuntimeError(error_msg) from e


async def process_user_input(prompt: str) -> Dict[str, Any]:
    """
    Process user input using run_flow_with_prompt and handle the response.
    Note: This function seems specific to flow-based execution.
    Consider if standard agent.run needs a different processing function.
    """
    logger = logging.getLogger("app")
    try:
        logger.debug(
            f"Processing user prompt via run_flow_with_prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
        )

        # Validate input
        if not prompt or not prompt.strip():
            logger.warning("Empty prompt received in process_user_input")
            # Return a dictionary structure consistent with expected output, or adjust caller
            return {
                "response": "Radis: Please provide a valid prompt and try again.",
                "tool_use": False,
            }

        # Run the flow with the prompt
        # Assuming run_flow_with_prompt handles planning_tool internally if needed
        result = await run_flow_with_prompt(prompt)
        logger.debug(f"Result received from run_flow_with_prompt: {type(result)}")

        # --- Response Handling Logic ---
        # This part needs careful review based on what run_flow_with_prompt actually returns.
        # The original code had complex handling for strings, dicts, JSON strings.
        # Simplify based on the expected structure from run_flow_with_prompt.

        final_response_text = "Radis: I encountered an issue processing your request."
        tool_calls_display = []  # Store info for display later if needed
        artifacts_display = []

        if isinstance(result, dict):
            # Assume result dict has keys like 'response', 'tool_calls', 'artifacts'
            response_text = result.get("response", "")
            tool_calls = result.get("tool_calls", [])
            artifacts = result.get("artifacts", [])
            tool_used = bool(tool_calls)  # Infer tool use from presence of calls

            if response_text:
                final_response_text = (
                    f"Radis: {response_text}"
                    if not response_text.startswith("Radis:")
                    else response_text
                )
            elif tool_used:
                final_response_text = "Radis: Task completed using tools."  # Placeholder if no text response
            else:
                final_response_text = "Radis: Processing complete."  # Placeholder

            # Prepare display info (caller should handle actual display)
            tool_calls_display = tool_calls
            artifacts_display = artifacts

            logger.debug(
                f"Processed dict result. Response: {final_response_text[:50]}..., Tools Used: {tool_used}"
            )

        elif isinstance(result, str):
            # Handle plain string result
            final_response_text = (
                f"Radis: {result}" if not result.startswith("Radis:") else result
            )
            tool_used = False  # Assume no tools if only string returned
            logger.debug(f"Processed string result: {final_response_text[:50]}...")

        elif result is None:
            logger.warning("Received None result from run_flow_with_prompt")
            final_response_text = (
                "Radis: I received no specific response. Please try again."
            )
            tool_used = False
        else:
            # Handle unexpected result types
            logger.warning(
                f"Received unexpected result type from run_flow_with_prompt: {type(result)}"
            )
            final_response_text = f"Radis: Received unexpected data: {str(result)}"
            tool_used = False

        # Return a consistent dictionary structure
        return {
            "response": final_response_text,
            "tool_use": tool_used,
            "tool_calls": tool_calls_display,  # Pass raw data for caller to display
            "artifacts": artifacts_display,  # Pass raw data for caller to display
        }

    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error processing user input via flow: {e}\n{error_traceback}")
        # Return error in the consistent dictionary structure
        return {
            "response": "Radis: I encountered an unexpected error while processing your request. Please try again.",
            "tool_use": False,
            "tool_calls": [],
            "artifacts": [],
        }


# Global state management (Keep minimal)
is_shutting_down = False
shutdown_event = threading.Event()
# Consider removing global agent if instance is managed within main/sessions
# agent = None
# logger is configured in setup_logging


async def cleanup_resources():
    """Clean up resources before shutdown"""
    logger = logging.getLogger("app")
    print("\nShutdown requested. Cleaning up resources...")
    logger.info("Cleanup requested. Cleaning up resources...")

    try:
        # Cancel any remaining asyncio tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            logger.info(f"Cancelling {len(tasks)} outstanding tasks...")
            for task in tasks:
                task.cancel()
            # Allow tasks to finish cancelling
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("Outstanding tasks cancelled.")

        # Notify tools to perform cleanup
        if "agent" in globals() and agent:
            logger.info("Cleaning up agent resources...")
            await agent.cleanup_resources()  # New cleanup method

            # Clean up tool resources
            tools = agent.get_tools()
            for tool in tools:
                if hasattr(tool, "cleanup"):
                    try:
                        await tool.cleanup()
                        logger.info(f"Cleaned up tool: {tool.name}")
                    except Exception as e:
                        logger.error(f"Error cleaning up tool {tool.name}: {e}")

        # Close any open files or connections
        for handler in logger.handlers[:]:
            if isinstance(handler, RotatingFileHandler):
                handler.close()
                logger.removeHandler(handler)

    except Exception as e:
        logger.error(f"Error during resource cleanup: {e}", exc_info=True)
        raise

    try:
        # Clean up agent resources if applicable (e.g., close connections)
        # If agent instance is local to main/session, this might not be needed here.
        # if 'agent' in globals() and agent and hasattr(agent, 'cleanup'):
        #     logger.info("Cleaning up agent resources...")
        #     await agent.cleanup()

        # Cancel any remaining asyncio tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            logger.info(f"Cancelling {len(tasks)} outstanding tasks...")
            for task in tasks:
                task.cancel()
            # Allow tasks to finish cancelling
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("Outstanding tasks cancelled.")

    except Exception as e:
        logger.error(f"Error during resource cleanup: {e}", exc_info=True)
    finally:
        print("Cleanup completed.")
        logger.info("Cleanup completed.")


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    global is_shutting_down
    logger = logging.getLogger("app")

    sig_name = signal.Signals(signum).name
    print(f"\nReceived signal {sig_name}. Initiating shutdown...")
    logger.info(f"Received signal {sig_name}. Initiating shutdown...")

    if is_shutting_down:
        print("Shutdown already in progress. Force quitting...")
        logger.warning("Shutdown already in progress. Force quitting...")
        sys.exit(1)

    is_shutting_down = True
    shutdown_event.set()

    # Schedule cleanup_resources to run in the event loop
    try:
        loop = asyncio.get_running_loop()
        # Ensure cleanup runs even if loop is stopped or stopping
        asyncio.ensure_future(cleanup_resources(), loop=loop)
        # Optionally add a timeout for cleanup
        # loop.call_later(5, loop.stop) # Example: Force stop after 5s
    except RuntimeError:  # Loop not running
        # If no loop is running, run cleanup synchronously (might block)
        print("Event loop not running. Running cleanup synchronously.")
        logger.info("Event loop not running. Running cleanup synchronously.")
        try:
            asyncio.run(cleanup_resources())
        except Exception as e:
            logger.error(f"Error running synchronous cleanup: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error scheduling cleanup: {e}", exc_info=True)
        sys.exit(1)  # Exit if cleanup cannot be scheduled


# Set up signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


async def run_sudo_command(cmd: str, require_password: bool = True) -> Dict[str, Any]:
    """
    Run a command with sudo privileges.
    WARNING: Handling passwords like this is insecure. Consider alternatives.
    """
    # This function remains largely unchanged but acknowledge security risk
    logger = logging.getLogger("app")
    logger.warning("Executing run_sudo_command. Password handling is insecure.")
    global _sudo_password, _sudo_timestamp  # These globals are problematic

    # Check if we need a new sudo password
    current_time = time.time()
    if require_password and (
        not _sudo_timestamp or current_time - _sudo_timestamp > 300
    ):  # 5 minute timeout
        # Prompt for sudo password
        import getpass

        print("\nSudo privileges required. Please enter your password:")
        try:
            _sudo_password = getpass.getpass()
            _sudo_timestamp = current_time
        except Exception as e:
            logger.error(f"Failed to get sudo password: {e}")
            return {"success": False, "error": "Failed to get password", "code": -1}

    try:
        # Prepare the command
        if require_password and _sudo_password:
            # Using echo | sudo -S is insecure
            full_cmd = f'echo "{_sudo_password}" | sudo -S {cmd}'
            logger.debug(f"Preparing sudo command (insecure): sudo -S {cmd}")
        else:
            full_cmd = f"sudo {cmd}"
            logger.debug(f"Preparing sudo command: {full_cmd}")

        # Run the command
        process = await asyncio.create_subprocess_shell(
            full_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        logger.info(f"Sudo command finished with code: {process.returncode}")

        return {
            "success": process.returncode == 0,
            "output": stdout.decode(errors="ignore") if stdout else "",
            "error": stderr.decode(errors="ignore") if stderr else "",
            "code": process.returncode,
        }

    except Exception as e:
        logger.error(f"Error running sudo command '{cmd}': {e}", exc_info=True)
        return {"success": False, "error": str(e), "code": -1}


def log_tool_initialization(tool_name: str, success: bool, error_msg: str = None):
    """Log the initialization status of a tool."""
    logger = logging.getLogger("app")
    if success:
        logger.info(f"✓ Successfully initialized/verified {tool_name} tool")
        print(f"✓ Tool loaded: {tool_name}")
    else:
        msg = f"✗ Failed to initialize/verify {tool_name} tool"
        if error_msg:
            msg += f": {error_msg}"
        logger.error(msg)
        print(f"✗ Failed to load {tool_name} tool")


def print_tools_info(agent):
    """Print information about the available tools in the agent."""
    logger = logging.getLogger("app")
    try:
        tools = (
            agent.get_tools()
        )  # Assuming this returns a list/dict of tool names/info
        if not tools:
            logger.warning("No tools available in the agent.")
            print("No tools available.")
            return

        print("\nAvailable Tools:")
        # Log each available tool (assuming verification happened in create_agent)
        for tool_name in tools:  # Adjust if tools is not just names
            print(f"- {tool_name}")
            # log_tool_initialization(tool_name, True) # Logging done during creation

        # ToolDisplay might be redundant if create_agent logs status
        # ToolDisplay.show_tools(tools)

    except Exception as e:
        logger.error(f"Failed to print tools info: {e}", exc_info=True)
        print("Error retrieving tool information.")


# start_api_server_thread might be redundant if API/Web started directly in main
# def start_api_server_thread(): ...


def check_exit_requested():
    """Check if exit has been requested via signal"""
    return shutdown_event.is_set() or is_shutting_down


async def handle_file_upload(file_path: str) -> Dict[str, Any]:
    """
    Handle file upload in CLI mode. Requires agent instance.
    Consider passing agent instance instead of relying on global.
    """
    logger = logging.getLogger("app")
    logger.info(f"Handling file upload for: {file_path}")
    # This function needs a valid agent instance. How is it obtained?
    # Option 1: Pass agent instance as argument
    # Option 2: Create a temporary agent (potentially inefficient)
    # Option 3: Rely on a global 'agent' (problematic)

    # Assuming Option 2 for now, but needs review
    try:
        # Create a temporary agent instance JUST for this upload? Seems wrong.
        # This suggests file upload might need to happen within an active session/agent context.
        # temp_agent = await create_agent() # Needs api_base, planning_tool?

        # Placeholder: Assume an agent instance 'cli_agent' exists or is passed
        # if cli_agent is None: raise RuntimeError("Agent not available for file upload")

        # Get file handler tool from the appropriate agent instance
        # file_handler = cli_agent.get_tool('file_handler')
        # if not file_handler:
        #     raise ValueError("File handler tool not available in the agent.")

        # # Process the upload using the tool
        # result = await file_handler.run(
        #     action='upload',
        #     file_path=file_path
        # )

        # Mock result until agent instance strategy is clear
        logger.warning(
            "File upload logic needs agent instance. Returning mock success."
        )
        result = {
            "status": "success",
            "message": f"File {Path(file_path).name} processed (mock).",
        }

        if result.get("status") != "success":
            raise Exception(result.get("error", "Upload failed"))

        logger.info(f"File upload result: {result}")
        return result

    except Exception as e:
        logger.error(f"Error handling file upload '{file_path}': {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


# handle_interruption might be redundant with signal_handler
# async def handle_interruption(): ...


# Piped input handling - needs integration into main loop or separate logic
async def handle_piped_input():
    """Process input piped directly to stdin."""
    logger = logging.getLogger("app")
    if not sys.stdin.isatty():
        logger.info("Processing piped input from stdin.")
        try:
            prompt = sys.stdin.read().strip()
            if not prompt:
                logger.info("No piped input received.")
                return True  # Indicate piped input was handled (even if empty)

            print(f"\n{TASK_SEPARATOR}")  # Visual separator for piped input

            # Need agent instance here too. Assume created in main.
            # This logic needs to be called from main() if piped input is detected.
            # It cannot run independently without context (args, api_base, agent).
            logger.error(
                "Piped input handling called out of context. Needs integration."
            )
            print(
                f"{RED}Error: Piped input cannot be processed in this context.{RESET}"
            )
            # Example: How it *might* look if integrated into main()
            # progress = ProgressDisplay()
            # artifacts = ArtifactDisplay()
            # api_base = await load_configuration(args) # Assuming args available
            # planning_tool = create_planning_tool() # Assuming needed
            # agent = await create_agent(api_base, planning_tool)
            # progress.show_thinking()
            # response_data = await agent.run(prompt) # Use agent.run or process_user_input
            # progress.stop_thinking()
            # # Display response_data (artifacts, tool calls, text)
            # print_response_box("RESULT", response_data.get('response', str(response_data)))

            return True  # Indicate piped input was processed

        except Exception as e:
            logger.error(f"Error processing piped input: {e}", exc_info=True)
            print(f"\n{RED}❌ Error processing piped input: {str(e)}{RESET}")
            return True  # Indicate attempt was made
    return False  # Indicate stdin is a TTY, not piped


# check_api_connectivity - useful diagnostic, maybe call from main or separate script
async def check_api_connectivity():
    """Check if the LLM API is accessible based on current config."""
    logger = logging.getLogger("app")
    # ANSI color codes
    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"
    print("\nChecking API connectivity...")
    logger.info("Checking API connectivity...")
    try:
        llm_config = config.get_llm_config()
        if not llm_config:
            print(f"{RED}✗ LLM configuration not loaded.{RESET}")
            logger.error("API check failed: LLM configuration not loaded.")
            return False

        # Try different field names for the base URL
        base_url = None
        for field in ["api_base", "base_url"]:  # Add other potential names
            if hasattr(llm_config, field) and getattr(llm_config, field):
                base_url = getattr(llm_config, field)
                break

        if not base_url:
            print(f"{RED}✗ No API base URL configured. Check your config file.{RESET}")
            logger.error("API check failed: No API base URL configured.")
            return False

        # Common health/model endpoints to check
        endpoints_to_try = [
            "/v1/models",
            "/api/tags",
            "/health",
        ]  # Add others if needed
        test_url_base = base_url.rstrip("/")

        print(f"Testing connection to LLM API at: {base_url}")
        logger.info(f"Testing connection to LLM API at: {base_url}")

        async with httpx.AsyncClient(timeout=10.0) as client:  # Increased timeout
            for endpoint in endpoints_to_try:
                test_url = f"{test_url_base}{endpoint}"
                logger.debug(f"Trying endpoint: {test_url}")
                try:
                    response = await client.get(test_url)
                    # Consider status code < 500 as potentially reachable
                    if response.status_code < 500:
                        print(
                            f"{GREEN}✓ Successfully connected to LLM API (endpoint {endpoint} returned {response.status_code}).{RESET}"
                        )
                        logger.info(
                            f"API check successful at {test_url} (Status: {response.status_code})"
                        )
                        return True
                    else:
                        logger.warning(
                            f"Endpoint {test_url} returned status code {response.status_code}"
                        )
                except httpx.RequestError as req_err:
                    # Log specific request errors but continue trying other endpoints
                    logger.warning(f"Connection error for {test_url}: {req_err}")
                    continue  # Try next endpoint

        # If loop finishes without success
        print(
            f"{RED}✗ Could not connect successfully to any standard API endpoints.{RESET}"
        )
        logger.error(
            "API check failed: Could not connect successfully to any standard endpoints."
        )
        return False

    except Exception as e:
        print(f"{RED}✗ Error during API connectivity check: {str(e)}{RESET}")
        logger.error(f"API check failed with unexpected error: {e}", exc_info=True)
        return False


# setup_error_handling - Maybe useful, but Python's logging already handles stderr
# def setup_error_handling(verbose=False): ...


# print_response_box - utility function for formatting output
def print_response_box(title: str, content: str):
    """Print content in a formatted box with a title."""
    # ANSI color codes
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    # Get terminal width or default to 80
    try:
        term_width = os.get_terminal_size().columns
    except:
        term_width = 80

    # Ensure minimum width
    box_width = max(term_width - 4, 76)  # -4 for padding

    # Create box elements
    horizontal_line = "─" * box_width
    top_border = f"╭{horizontal_line}╮"
    bottom_border = f"╰{horizontal_line}╯"

    # Print box
    print(f"\n{top_border}")

    # Print title if provided
    if title:
        title_line = (
            f"║ {BLUE}{BOLD}{title}{RESET}".ljust(
                box_width + len(BLUE) + len(BOLD) + len(RESET)
            )
            + " ║"
        )
        print(title_line)
        print(f"║{' ' * box_width}║")

    # Split content into lines and print
    content_lines = str(content).split("\n")
    for line in content_lines:
        # Handle long lines by wrapping
        while len(line) > box_width - 2:  # -2 for padding
            split_at = line[: box_width - 2].rfind(" ")
            if split_at == -1:  # No space found
                split_at = box_width - 2
            print(f"║ {line[:split_at]}".ljust(box_width + 1) + "║")
            line = line[split_at:].lstrip()
        print(f"║ {line}".ljust(box_width + 1) + "║")

    print(bottom_border)


# display_response - This seems redundant if interactive_session handles display
# def display_response(response): ...


# log_current_config - Simple helper, keep as is
def log_current_config():
    """Logs the current LLM configuration."""
    logger = logging.getLogger("app")
    try:
        llm_config = config.get_llm_config()
        logger.info(f"Current LLM Configuration: {llm_config}")
        print(f"Current LLM Configuration: {llm_config}")
    except Exception as e:
        logger.error(f"Failed to log current config: {e}")
        print("Failed to retrieve LLM configuration.")


# safe_iterate - Utility function, keep as is
def safe_iterate(iterable):
    """Safely iterate over a potentially None object."""
    if iterable is None:
        return []
    # If it's not None, ensure it's actually iterable (basic check)
    if not hasattr(iterable, "__iter__") or isinstance(iterable, (str, bytes)):
        # Log or handle non-iterable types if necessary
        logging.getLogger("app").warning(
            f"safe_iterate called with non-iterable type: {type(iterable)}"
        )
        return []
    return iterable


if __name__ == "__main__":
    # Check for piped input before starting the main async loop if desired
    # if asyncio.run(handle_piped_input()):
    #     sys.exit(0) # Exit if piped input was handled

    # Run the main async function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # This might catch the interrupt before the signal handler in some cases
        print("\nShutdown initiated from __main__.")
    except Exception as main_run_err:
        print(f"\n{RED}Critical error during asyncio.run(main): {main_run_err}{RESET}")
        traceback.print_exc()  # Print traceback for critical errors
        sys.exit(1)
