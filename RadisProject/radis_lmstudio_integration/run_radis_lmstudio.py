#!/usr/bin/env python3
"""
RadisLMStudio Runner

A script that runs RadisProject with direct LM Studio integration,
bypassing any problematic API layers.
"""

import argparse
import asyncio
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from .model_tokenizer import ModelTokenizer
from .response_sanitizer import ResponseSanitizer
from .lm_studio_direct import LMStudioDirect
from app.agent import RadisAgent
from app.core.errors import SecurityCommandError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("radis_lmstudio.log")
    ]
)
logger = logging.getLogger("radis_lmstudio")

class RunTimeStats:
    """Class to track runtime statistics"""
    def __init__(self):
        self.start_time: Optional[float] = None
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_requests: int = 0
        self.total_errors: int = 0

    def start_request(self):
        """Start timing a request"""
        self.start_time = time.time()
        self.total_requests += 1

    def end_request(self, prompt_tokens: int, completion_tokens: int):
        """End timing a request and update stats"""
        duration = time.time() - self.start_time
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        return duration

    def log_error(self):
        """Log an error occurrence"""
        self.total_errors += 1

    def get_summary(self) -> str:
        """Get a summary of all statistics"""
        return (
            f"\nSession Statistics:\n"
            f"Total Requests: {self.total_requests}\n"
            f"Total Errors: {self.total_errors}\n"
            f"Total Tokens: {self.total_prompt_tokens + self.total_completion_tokens}\n"
            f"  - Prompt Tokens: {self.total_prompt_tokens}\n"
            f"  - Completion Tokens: {self.total_completion_tokens}\n"
        )

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="RadisLMStudio Runner")
    parser.add_argument(
        "prompt", nargs="?", default=None, help="Initial prompt (optional)"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--no-sanitize", action="store_true",
        help="Disable response sanitization"
    )
    parser.add_argument(
        "--model", default="qwen2.5-7b-instruct-1m",
        help="Model name to use in LM Studio"
    )
    parser.add_argument(
        "--temperature", type=float, default=0.7,
        help="Temperature for text generation (0.0-1.0)"
    )
    parser.add_argument(
        "--max_tokens", type=int, default=1000,
        help="Maximum number of tokens to generate"
    )
    return parser.parse_args()

def print_banner():
    """Print the RadisLMStudio banner"""
    print("\n" + "=" * 39)
    print("           Starting AgentRadis")
    print("=" * 39 + "\n")

# Initialize global statistics tracker
stats = RunTimeStats()

async def run_radis_agent(prompt: str, config: Dict[str, Any]) -> bool:
    """Run the Radis agent with the given prompt"""
    stats.start_request()
    try:
        # Create the LM Studio client with sanitizer and tokenizer
        lm_studio = LMStudioDirect(
            config=config,
            tokenizer=ModelTokenizer(),
            sanitizer=None if config.get("no_sanitize") else ResponseSanitizer()
        )

        # Initialize the RadisAgent
        agent = RadisAgent()

        # Set up the agent
        await agent.async_setup()

        logger.info(f"Processing prompt with model: {lm_studio.model_name}")

        # Get token count for prompt
        prompt_tokens = lm_studio.count_tokens(prompt)
        logger.debug(f"Prompt tokens: {prompt_tokens}")

        # Generate the completion
        response = await lm_studio.generate_completion(
            prompt=prompt,
            temperature=config.get("temperature"),
            max_tokens=config.get("max_tokens")
        )

        # Get token counts for completion
        completion_tokens = lm_studio.count_tokens(response)
        duration = time.time() - stats.start_time

        # Log and display results
        logger.info(
            f"Request completed in {duration:.2f}s. "
            f"Tokens - Prompt: {prompt_tokens}, Completion: {completion_tokens}"
        )

        print(f"\nResponse:\n{response}\n")
        print(
            f"Request completed in {duration:.2f}s\n"
            f"Tokens used - Prompt: {prompt_tokens}, Completion: {completion_tokens},"
            f"Total: {prompt_tokens + completion_tokens}"
        )
        print("\nProcessing your request...")
    except Exception as e:
        stats.log_error()
        logger.error(f"Error processing request: {e}", exc_info=True)
        print(f"\nError: {str(e)}")
        if isinstance(e, (ValueError, TypeError)):
            print("This appears to be an input validation error. Please check your input and try again.")
        elif isinstance(e, SecurityCommandError):
            print("Failed to connect to LM Studio. Please ensure the service is running.")
        else:
            print("An unexpected error occurred. Please check the logs for details.")
        return False

async def main_async():
    """Async main entry point"""
    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Set up the configuration
    config = {
        "api_base": "http://localhost:1234",
        "model": args.model,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "no_sanitize": args.no_sanitize,
    }

    logger.info(f"Starting with configuration: {config}")

    # Print the banner
    print_banner()

    # Process initial prompt if provided
    if args.prompt:
        await run_radis_agent(args.prompt, config)
    else:
        # Enter interactive loop
        print("\nInteractive mode. Type 'exit' to quit.\n")

        while True:
            try:
                prompt = input("\nEnter your query: ")
                if prompt.lower() in ["exit", "quit"]:
                    print("\n\nExiting due to keyboard interrupt.")
                    break
            except KeyboardInterrupt:
                print("\n\nExiting due to keyboard interrupt.")
                break
            except Exception as e:
                stats.log_error()
                logger.error(f"Interactive mode error: {e}", exc_info=True)
                print(f"\nError encountered: {str(e)}\n")
            finally:
                if prompt.lower() in ["exit", "quit"]:
                    # Print final statistics
                    print(stats.get_summary())

def main():
    """Main entry point"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
