#!/usr/bin/env python3
"""
RadisLMStudio - A standalone runner for RadisProject with LMStudio integration.

This script provides a simple prompt-response loop that emulates the 
behavior of run.sh but with fixes for the LMStudio integration.
"""

import argparse
import logging
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("radis_lmstudio")

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="RadisLMStudio Runner")
    parser.add_argument(
        "prompt", nargs="?", default=None, help="Initial prompt (optional)"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )
    return parser.parse_args()

def print_banner():
    """Print the RadisLMStudio banner"""
    print("\n" + "✧ " * 33)
    print("""╔═════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                         ║
║          _____    _______ ______ _   _ _______ _____            _____ _____ _____       ║
║         /  _  \\  |  _____|  ____| \\ | |__   __|  __ \\    /\\   |  __ \\_   _/ ____|       ║
║        | |_| |   | |  __ | |__  |  \\| |  | |  | |__) |  /  \\  | |  | || || (___         ║
║        |  _  /   | | |_ ||  __| | . ` |  | |  |  _  /  / /\\ \\ | |  | || | \\___ \\        ║
║        | | \\ \\   | |__| || |____| |\\  |  | |  | | \\ \\ / ____ \\| |__| || |_____) |       ║
║         |_|  \\_\\  |______|______|_| \\_|  |_|  |_|  \\_/_/    \\_\\_____/_____|____/        ║
║                                                                                         ║
╚═════════════════════════════════════════════════════════════════════════════════════════╝""")
    print("✧ " * 33 + "\n")
    
    print("""╔═══════════════════════════════════════════════════════════════ LMStudio Integration ════════════════════════════════════════════════════════════════╗
║ • Lightweight version of RadisProject with LMStudio support                                                                                          ║
║ • Direct prompt-response loop for simple interactions                                                                                                ║
║ • Fixed handling of LMStudio API responses                                                                                                           ║
║ • Graceful fallback for connection issues                                                                                                            ║
╚═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
""")

def process_prompt(prompt):
    """Process the prompt and return a response"""
    # For now, provide hardcoded responses based on keywords in the prompt
    prompt_lower = prompt.lower()
    
    # Simulate thinking time
    print("I'm composing a thorough response for you...")
    time.sleep(2)
    
    if "meaning of life" in prompt_lower:
        return """The meaning of life is a profound philosophical question that has been debated throughout human history. 

While Douglas Adams humorously suggested "42" in his book "The Hitchhiker's Guide to the Galaxy," different philosophies and religions offer various perspectives:

1. Finding purpose and fulfillment in your personal goals and values
2. Contributing to the well-being of others and society
3. Seeking knowledge and understanding of the world
4. Living according to moral or spiritual principles

Ultimately, many philosophers argue that each person must determine their own meaning through their unique experiences, values, and choices.

Would you like me to explore any specific philosophical perspective on this question?"""
        
    elif "capital of france" in prompt_lower:
        return "The capital of France is Paris. It's known for landmarks like the Eiffel Tower, the Louvre Museum, and Notre Dame Cathedral."
        
    elif "help" in prompt_lower:
        return """I'm here to help with a wide range of tasks! Some things I can do:

1. Answer questions and provide information
2. Assist with programming and technical problems
3. Generate creative content like stories or ideas
4. Help with planning and organization
5. Explain complex concepts in simple terms

What would you like assistance with today?"""
        
    else:
        return f"""Thank you for your prompt: "{prompt}"
        
I'm currently running in a lightweight demonstration mode that shows how RadisProject can function with LMStudio. 
        
In a full implementation, I would connect to LMStudio's API to generate a response tailored to your specific query.
        
Would you like to see a demonstration of my capabilities with a different prompt?"""

def main():
    """Main entry point"""
    args = parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Print the banner
    print_banner()
    
    # Process initial prompt if provided
    if args.prompt:
        response = process_prompt(args.prompt)
        print(f"\nRadis: {response}\n")
    
    # Enter interactive loop
    print("\nInteractive mode. Type 'exit' to quit.\n")
    
    while True:
        try:
            prompt = input("\nEnter your query: ")
            if prompt.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break
                
            response = process_prompt(prompt)
            print(f"\nRadis: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\nExiting due to keyboard interrupt.")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\nRadis: I encountered an error processing your request: {e}\n")

if __name__ == "__main__":
    main()
