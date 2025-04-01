import asyncio
import json
import os
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agent import EnhancedRadis  # Assuming EnhancedRadis is the primary agent now
from app.logger import logger
from app.config import config  # Import the config object
import uvicorn  # Keep only one import

# Create FastAPI app
app = FastAPI(title="AgentRadis API", description="REST API for AgentRadis AI Agent")

# Configure CORS to allow requests from the UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure the agentradis directory exists (assuming this is for static UI files)
os.makedirs("agentradis", exist_ok=True)

# Serve the UI (adjust directory if needed)
app.mount("/ui", StaticFiles(directory="agentradis"), name="agentradis_ui")


# Models for requests and responses
class ChatRequest(BaseModel):
    prompt: Optional[str] = None
    message: Optional[str] = None
    mode: Optional[str] = "action"


class ChatResponse(BaseModel):
    response: str
    tools_used: List[str] = []
    tool_results: List[Dict[str, Any]] = []
    saved_files: List[str] = []
    error: Optional[str] = None


# Create a global Radis instance
radis_agent = None

# Removed initialize_agent as get_radis_agent handles lazy init


async def get_radis_agent():
    global radis_agent
    if radis_agent is None:
        logger.info("Initializing EnhancedRadis agent for API...")
        radis_agent = await EnhancedRadis()  # Use await for async init
        # Consider adding await radis_agent.async_setup() if needed
        logger.info("EnhancedRadis agent initialized.")
    return radis_agent


# In-memory storage for tracking tool usage and files (Consider if this state management is robust enough)
tools_used = []
saved_files = []
tool_results = []


# Root route redirects to UI
@app.get("/")
async def root():
    """Redirect root to the UI page"""
    return RedirectResponse(url="/ui/index.html", status_code=302)


# Favicon route
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return empty response for favicon requests"""
    return JSONResponse(content={})


# Health check endpoint
@app.get("/health")
async def health_check():
    """Check if the API is running"""
    return {"status": "ok"}


# Artifact content endpoint
@app.get("/api/artifact")
async def get_artifact(path: str):
    """Retrieve the content of an artifact file by path"""
    try:
        # Basic security check
        if ".." in path or not path.startswith("CWlogs"):  # Example: Restrict to CWlogs
            raise HTTPException(status_code=403, detail="Access restricted")

        # Use absolute path based on project root or a designated artifacts dir
        # This needs careful consideration based on where artifacts are stored
        safe_path = os.path.abspath(
            os.path.join(".", path)
        )  # Example, adjust as needed
        project_root = os.path.abspath(".")
        if not safe_path.startswith(project_root):
            raise HTTPException(status_code=403, detail="Access restricted")

        if not os.path.exists(safe_path):
            raise HTTPException(status_code=404, detail=f"Artifact not found: {path}")

        if not os.path.isfile(safe_path):
            raise HTTPException(status_code=400, detail=f"Path is not a file: {path}")

        # Read and return the file content
        with open(safe_path, "r", encoding="utf-8") as file:  # Specify encoding
            content = file.read()

        return PlainTextResponse(content)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error retrieving artifact '{path}': {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving artifact: {str(e)}"
        )


# Main chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat request with the Radis agent"""
    global tools_used, saved_files, tool_results  # Consider better state management

    # Reset tracking
    tools_used = []
    saved_files = []
    tool_results = []

    try:
        # Get the prompt from either field
        prompt = request.prompt or request.message
        if not prompt:
            raise HTTPException(
                status_code=400, detail="Either 'prompt' or 'message' field is required"
            )

        # Log the request
        logger.info(f"Received chat request: {prompt[:100]}...")  # Log truncated prompt

        # Process with Radis agent - now expecting a dictionary
        agent = await get_radis_agent()
        # Assuming agent.run exists and is async, adjust if method name/signature differs
        result = await agent.run(prompt, mode=request.mode)

        # Handle both string responses and dictionary results
        if isinstance(result, dict):
            response_text = result.get("response", "No response generated")
            # Potentially extract tool usage directly from result if available
            # tools_used = result.get("tools_used", [])
            # tool_results = result.get("tool_results", [])
            # saved_files = result.get("saved_files", [])
        else:
            # Fall back to treating as string for backward compatibility
            response_text = str(result)

        # Clean up the response by removing internal tool request markers
        cleaned_response = clean_agent_response(response_text)

        # Collect tools used by examining memory (Fallback if not in result dict)
        # This might be redundant if result dict contains tool info
        collect_tool_usage(agent)  # Pass agent instance

        # Return response
        return ChatResponse(
            response=cleaned_response,
            tools_used=tools_used,
            tool_results=tool_results,
            saved_files=saved_files,
        )

    except Exception as e:
        logger.error(
            f"Error processing chat request: {str(e)}", exc_info=True
        )  # Add traceback
        return ChatResponse(
            response="An error occurred while processing your request.", error=str(e)
        )


def clean_agent_response(text):
    """Clean the agent response by removing internal tool request markers and formatting"""
    import re

    # Ensure text is a string
    if not isinstance(text, str):
        text = str(text)

    # Remove tool request blocks (adjust regex if format changed)
    text = re.sub(
        r"\[TOOL_REQUEST\]\s*\{.*?\}\s*\[END_TOOL_REQUEST\]", "", text, flags=re.DOTALL
    )
    text = re.sub(
        r"\[TOOL_REQUEST\].*?\[END_TOOL_REQUEST\]", "", text, flags=re.DOTALL
    )  # Catch variations

    # Clean up any extra whitespace from the removals
    text = re.sub(r"\n\s*\n\s*\n", "\n\n", text).strip()

    # Check if the response indicates a failed search (adjust keywords if needed)
    # if "just returned the search query itself" in text or "search result just returned" in text:
    #     text += "\n\nI'll try another approach to find more specific information for you."

    return text


def collect_tool_usage(agent_instance):
    """Extract tool usage information from agent memory"""
    global tools_used, saved_files, tool_results

    if (
        not agent_instance
        or not hasattr(agent_instance, "memory")
        or not hasattr(agent_instance.memory, "messages")
    ):
        logger.warning(
            "Agent instance or memory not available for tool usage collection."
        )
        return

    try:
        # Extract tools from memory
        for message in agent_instance.memory.messages:
            # Check for tool messages (adjust based on actual Message structure)
            if (
                hasattr(message, "role")
                and message.role == "tool"
                and hasattr(message, "name")
                and message.name
            ):
                tool_name = message.name
                if tool_name not in tools_used:
                    tools_used.append(tool_name)

                # Check for file_saver tool (adjust logic if needed)
                if (
                    tool_name == "file_saver"
                    and hasattr(message, "content")
                    and message.content
                ):
                    content = message.content
                    if (
                        isinstance(content, str)
                        and "saved" in content.lower()
                        and " to " in content.lower()
                    ):
                        parts = content.split(" to ")
                        if len(parts) > 1:
                            file_path = parts[1].strip().strip("'\"")  # Clean path
                            if file_path not in saved_files:
                                saved_files.append(file_path)

                # Add tool result (consider structure)
                if hasattr(message, "content"):
                    tool_results.append(
                        {
                            "name": tool_name,
                            "message": message.content,  # Or specific result field if available
                        }
                    )
    except Exception as e:
        logger.error(f"Error collecting tool usage: {str(e)}", exc_info=True)
        # Don't re-raise, just continue with potentially incomplete collections


# Function to start the API server
async def start_api_server(host="0.0.0.0", port=5000):
    """Start the FastAPI server with uvicorn"""
    # Ensure agent is initialized before server starts accepting requests
    await get_radis_agent()
    logger.info(f"Attempting to start Uvicorn on {host}:{port}")
    server_config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(server_config)
    try:
        await server.serve()
    except Exception as e:
        logger.error(f"Failed to start Uvicorn server: {e}", exc_info=True)
        raise  # Re-raise after logging


# Run the app with uvicorn when script is executed directly
async def main():
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Start the AgentRadis API server")
    parser.add_argument(
        "--port",
        type=int,
        default=config.api_port if hasattr(config, "api_port") else 5000,
        help="Port to run the server on",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=config.api_host if hasattr(config, "api_host") else "0.0.0.0",
        help="Host to run the server on",
    )

    args = parser.parse_args()

    logger.info(f"Starting AgentRadis API server on {args.host}:{args.port}")
    await start_api_server(host=args.host, port=args.port)


if __name__ == "__main__":
    # Use the async main function correctly
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("API server shut down by user.")
    except Exception as e:
        logger.critical(f"API server failed to run: {e}", exc_info=True)
        # Exit with error code if server fails to start/run
        import sys

        sys.exit(1)
