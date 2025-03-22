#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AgentRadis - A powerful AI agent that helps users with various tasks
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
import asyncio
import traceback
import threading
from typing import Dict, Any, List, Optional, Union

# Import app modules
from app.agent.enhanced_radis import EnhancedRadis
from app.config import config
from app.logger import logger
from app.display import ToolDisplay, ArtifactDisplay, ProgressDisplay, setup_display, print_ascii_banner_with_stars

# Global state management
is_shutting_down = False
shutdown_event = threading.Event()
_sudo_password = None
_sudo_timestamp = None

async def cleanup_resources():
    """Clean up resources before shutdown"""
    global agent, _sudo_password, _sudo_timestamp
    
    print("\nShutdown requested. Cleaning up resources...")
    
    try:
        # Clear any cached sudo password
        _sudo_password = None
        _sudo_timestamp = None
        
        # Clean up agent resources if it exists
        if 'agent' in globals() and agent:
            await agent.cleanup()
            
        # Additional cleanup for web/API servers if running
        for task in asyncio.all_tasks():
            if not task.done() and task != asyncio.current_task():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    finally:
        print("Cleanup completed.")

def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    global is_shutting_down
    
    if is_shutting_down:
        print("\nForce quitting...")
        sys.exit(1)
        
    is_shutting_down = True
    shutdown_event.set()
    
    # Run cleanup in the event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(cleanup_resources())
        else:
            loop.run_until_complete(cleanup_resources())
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        sys.exit(1)

# Set up signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def run_sudo_command(cmd: str, require_password: bool = True) -> Dict[str, Any]:
    """
    Run a command with sudo privileges.
    
    Args:
        cmd: The command to run
        require_password: Whether to require password input
        
    Returns:
        Dict containing command output and status
    """
    global _sudo_password, _sudo_timestamp
    
    # Check if we need a new sudo password
    current_time = time.time()
    if require_password and (not _sudo_timestamp or current_time - _sudo_timestamp > 300):  # 5 minute timeout
        # Prompt for sudo password
        import getpass
        print("\nSudo privileges required. Please enter your password:")
        _sudo_password = getpass.getpass()
        _sudo_timestamp = current_time
    
    try:
        # Prepare the command
        if require_password and _sudo_password:
            full_cmd = f'echo "{_sudo_password}" | sudo -S {cmd}'
        else:
            full_cmd = f'sudo {cmd}'
            
        # Run the command
        process = await asyncio.create_subprocess_shell(
            full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            'success': process.returncode == 0,
            'output': stdout.decode() if stdout else '',
            'error': stderr.decode() if stderr else '',
            'code': process.returncode
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'code': -1
        }

def print_banner():
    """Print welcome banner for AgentRadis"""
    print_ascii_banner_with_stars()
    print("\nYour gateway to the internet awaits and Radis will be your guide. Embrace the cosmos.")
    print("Type 'exit' to quit.")

def print_tools_info(agent):
    """
    Print information about the available tools in the agent.
    
    Args:
        agent: The Radis agent instance
    """
    tools = agent.get_tools()
    if not tools:
        print("No tools available.")
        return
    
    ToolDisplay.show_tools(tools)

def start_api_server_thread():
    """Start the API server in a separate thread"""
    print(f"🌐 Starting API server at http://localhost:5000")
    thread = threading.Thread(target=api.start_api_server)
    thread.daemon = True  # Thread will exit when main program exits
    thread.start()
    return thread

def check_exit_requested():
    """Check if exit has been requested"""
    return shutdown_event.is_set() or is_shutting_down

async def handle_file_upload(file_path: str) -> Dict[str, Any]:
    """
    Handle file upload in CLI mode.
    
    Args:
        file_path: Path to the file to upload
        
    Returns:
        Dict containing upload results
    """
    try:
        # Create agent if needed
        global agent
        if not agent:
            agent = create_agent()
            
        # Get file handler tool
        file_handler = agent.get_tool('file_handler')
        if not file_handler:
            raise ValueError("File handler tool not available")
            
        # Process the upload
        result = await file_handler.run(
            action='upload',
            file_path=file_path
        )
        
        if result['status'] != 'success':
            raise Exception(result.get('error', 'Upload failed'))
            
        return result
        
    except Exception as e:
        logger.error(f"Error handling file upload: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }

async def interactive_session(agent, debug=False):
    """Run an interactive session with the agent"""
    setup_display()
    progress = ProgressDisplay()
    artifacts = ArtifactDisplay()
    
    print_tools_info(agent)
    
    # ANSI color codes
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    
    # Separator line
    SEPARATOR = "=" * 80
    
    while not check_exit_requested():
        try:
            prompt = input(f"\n{GREEN}{BOLD}You:{RESET} ")
            if not prompt:
                continue
                
            if prompt.lower() in ['exit', 'quit']:
                break
            
            # Add separator after user input
            print(f"\n{SEPARATOR}")
            
            progress.show_thinking()
            response = await process_user_input(prompt, agent)
            
            # Handle artifacts if present
            if 'artifacts' in response:
                for artifact in response['artifacts']:
                    if artifact['type'] == 'code':
                        artifacts.code_preview(artifact['content'], artifact.get('language', 'python'))
                    elif artifact['type'] == 'web':
                        artifacts.web_preview(artifact['content'])
                    elif artifact['type'] == 'project':
                        artifacts.project_structure(artifact['content'])
            
            # Show tool calls and results
            if 'tool_calls' in response:
                print()  # Add spacing before tool calls
                for tool_call in response['tool_calls']:
                    ToolDisplay.show_tool_call(tool_call['name'], tool_call['args'])
                    ToolDisplay.show_tool_result(tool_call['result'], tool_call.get('success', True))
            
            # Add separator before response box
            print(f"\n{SEPARATOR}")
            
            # Print response in a box
            print_response_box("RESULT", response.get('response', ''))
            
        except KeyboardInterrupt:
            await handle_interruption()
        except Exception as e:
            if debug:
                traceback.print_exc()
            print(f"\n❌ Error: {str(e)}")

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

def print_response_box(title="RESPONSE", response_text=""):
    """
    Print the response in a nice colorful box with a narrow header and wider content section.
    
    Args:
        title: The title of the box
        response_text: The response text to display
    """
    # ANSI color codes
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    
    # Check for errors in the response
    is_error = "error" in response_text.lower() or "❌" in response_text
    box_color = RED if is_error else CYAN
    
    # Get terminal width, default to 80 if can't determine
    try:
        terminal_width = os.get_terminal_size().columns
    except:
        terminal_width = 80
    
    # Limit width to reasonable size
    box_width = min(terminal_width - 4, 100)
    header_width = min(30, box_width)  # Narrow header width
    
    # Word wrap the response text
    import textwrap
    wrapped_lines = []
    for line in response_text.split('\n'):
        if line.strip():
            wrapped_lines.extend(textwrap.wrap(line, width=box_width-4))
        else:
            wrapped_lines.append('')
    
    # Print the header section
    print(f"\n{box_color}{BOLD}┌{'─' * (header_width)}┐{RESET}")
    title_padding = (header_width - len(title)) // 2
    print(f"{box_color}{BOLD}│{' ' * title_padding}{title}{' ' * (header_width - len(title) - title_padding)}│{RESET}")
    print(f"{box_color}{BOLD}└{'─' * (header_width)}┘{RESET}")
    
    # Print the content section
    print(f"{box_color}{BOLD}┌{'─' * (box_width)}┐{RESET}")
    
    # Print content
    for line in wrapped_lines:
        padding = ' ' * (box_width - len(line))
        print(f"{box_color}{BOLD}│{RESET}  {line}{padding}  {box_color}{BOLD}│{RESET}")
    
    print(f"{box_color}{BOLD}└{'─' * (box_width)}┘{RESET}")
    print()

async def process_with_radis(prompt, api_base=None, with_plan=False, debug=True):
    """Process a prompt with the Radis agent"""
    # Create agent with API base override if provided
    agent = create_agent(api_base)
    
    # Test connection to LLM API first
    llm_config = config.get_llm_config()
    api_base = api_base or llm_config.api_base
    print(f"Testing connection to LLM API at: {api_base}")
    
    from app.llm import LLM
    llm = LLM()
    connection_result = await llm.test_llm_connection(api_base)
    
    if not connection_result["success"]:
        error_msg = connection_result.get("error", "Unknown error connecting to LLM API")
        print(f"❌ Connection error: {error_msg}")
        print("Please check your API configuration and try again.")
        return f"Error: Could not connect to LLM API - {error_msg}"
        
    print("✓ Successfully connected to LLM API")
    
    # Process the query and get response
    start_time = time.time()
    
    try:
        # Execute with agent
        result = await agent.run(prompt)
        end_time = time.time()
        
        # Unpack the result
        response_text = result.get('response', 'No response generated')
        
        # Return the response without printing a box
        return response_text
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        error_msg = f"Error generating response: {str(e)}. Please try again."
        return error_msg

def create_agent(api_base: Optional[str] = None) -> EnhancedRadis:
    """Create a new agent instance"""
    return EnhancedRadis(api_base=api_base)

async def process_user_input(prompt: str, agent: EnhancedRadis) -> Dict[str, Any]:
    """
    Process user input with the agent.
    
    Args:
        prompt: The user's input prompt
        agent: The EnhancedRadis agent instance
        
    Returns:
        Dict containing the response, artifacts, and tool calls
    """
    try:
        # Process with agent
        result = await agent.run(prompt)
        
        if isinstance(result, dict):
            return {
                'response': result.get('response', 'No response generated'),
                'artifacts': result.get('artifacts', []),
                'tool_calls': result.get('tool_calls', []),
                'status': result.get('status', 'success')
            }
        else:
            # Handle string responses
            return {
                'response': str(result),
                'artifacts': [],
                'tool_calls': [],
                'status': 'success'
            }
            
    except Exception as e:
        logger.error(f"Error processing input: {e}")
        return {
            'response': f"Error: {str(e)}",
            'artifacts': [],
            'tool_calls': [],
            'status': 'error'
        }

def main():
    """Main entry function with enhanced error handling"""
    parser = argparse.ArgumentParser(description="AgentRadis - A versatile AI agent")
    parser.add_argument("prompt", nargs="?", help="Prompt to process")
    parser.add_argument("--web", action="store_true", help="Start the web interface")
    parser.add_argument("--api", action="store_true", help="Start the API server")
    parser.add_argument("--api-base", type=str, help="Override the API base URL")
    parser.add_argument("--port", type=int, default=5000, help="Port for web/API server")
    parser.add_argument("--flow", action="store_true", help="Use flow-based execution")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Get LLM config
    llm_config = config.get_llm_config()
    
    # Override API base if provided
    api_base = args.api_base or llm_config.api_base
        
    try:
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
            print("Your gateway to the internet awaits and Radis will be your guide. Embrace the cosmos.")
            print("Type 'exit' to quit.")
            print("    ")
            
            port = args.port if args.port else 5001
            print(f"🌐 Starting AgentRadis Web Interface on port {port}")
            
            # Initialize the agent for web service
            from app.agent.enhanced_radis import EnhancedRadis
            from api import start_api_server
            
            from app.logger import configure_logging
            configure_logging(level=logging.INFO)
            
            # Start the web server in a separate thread
            import threading
            api_thread = threading.Thread(target=start_api_server, args=("0.0.0.0", port))
            api_thread.daemon = True
            api_thread.start()
            
            # Keep the main thread alive to maintain the web server
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down AgentRadis Web Interface...")
            
            return
        elif args.api:
            # Start API server
            print("🚀 Starting AgentRadis API Server")
            from app.api import start_api_server
            start_api_server(port=args.port)
            
        elif args.prompt:
            # Process a single prompt
            from app.display import print_ascii_banner_with_stars
            print_ascii_banner_with_stars()
            print(f"Running AgentRadis with prompt: {args.prompt}")
            
            if args.flow:
                # Use flow-based execution
                from run_flow import run_with_prompt
                asyncio.run(run_with_prompt(args.prompt))
            else:
                # Use standard execution with debug mode
                response = asyncio.run(process_with_radis(args.prompt, api_base=api_base, with_plan=False, debug=args.debug))
                
                # Print the response in a nice box format
                print_response_box("RESULT", response)
                print("\nOperation completed.")
        else:
            # Start interactive mode
            print("Starting interactive mode...")
            agent = create_agent(api_base)
            asyncio.run(interactive_session(agent, debug=args.debug))
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        print("Shutting down...")

if __name__ == "__main__":
    main()
