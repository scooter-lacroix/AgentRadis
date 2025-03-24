import asyncio
import json
import os
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agent import Radis, EnhancedRadis
from app.logger import logger
from app.config import config  # Import the config object

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

# Ensure the agentradis directory exists
os.makedirs("agentradis", exist_ok=True)

# Serve the UI
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

async def initialize_agent():
    return await EnhancedRadis()

async def get_radis_agent():
    global radis_agent
    if radis_agent is None:
        radis_agent = await EnhancedRadis()
    return radis_agent

# In-memory storage for tracking tool usage and files
tools_used = []
saved_files = []
tool_results = []

# Root route redirects to UI
@app.get("/")
async def root():
    """Redirect root to the UI page"""
    return RedirectResponse(url="/ui/index.html", status_code=302)

# Favicon route
@app.get("/favicon.ico")
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
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"Artifact not found: {path}")
        
        if not os.path.isfile(path):
            raise HTTPException(status_code=400, detail=f"Path is not a file: {path}")
        
        # Simple security check to prevent directory traversal
        if ".." in path:
            raise HTTPException(status_code=403, detail="Path traversal not allowed")
        
        # Read and return the file content
        with open(path, "r") as file:
            content = file.read()
        
        return PlainTextResponse(content)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error retrieving artifact: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving artifact: {str(e)}")

# Main chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat request with the Radis agent"""
    global tools_used, saved_files, tool_results

    # Reset tracking
    tools_used = []
    saved_files = []
    tool_results = []

    try:
        # Get the prompt from either field
        prompt = request.prompt or request.message
        if not prompt:
            raise HTTPException(status_code=400, detail="Either 'prompt' or 'message' field is required")

        # Log the request
        logger.info(f"Received chat request: {prompt}")

        # Process with Radis agent - now expecting a dictionary
        agent = await get_radis_agent()
        result = await agent.run(prompt, mode=request.mode)

        # Handle both string responses and dictionary results
        if isinstance(result, dict):
            response_text = result.get("response", "No response generated")
        else:
            # Fall back to treating as string for backward compatibility
            response_text = str(result)

        # Clean up the response by removing internal tool request markers
        cleaned_response = clean_agent_response(response_text)

        # Collect tools used by examining memory
        collect_tool_usage()

        # Return response
        return ChatResponse(
            response=cleaned_response,
            tools_used=tools_used,
            tool_results=tool_results,
            saved_files=saved_files
        )

    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        return ChatResponse(
            response="An error occurred while processing your request.",
            error=str(e)
        )

def clean_agent_response(text):
    """Clean the agent response by removing internal tool request markers and formatting"""
    import re

    # Ensure text is a string
    if not isinstance(text, str):
        text = str(text)

    # Remove tool request blocks
    text = re.sub(r'\[TOOL_REQUEST\]\s*\{.*?\}\s*\[END_TOOL_REQUEST\]', '', text, flags=re.DOTALL)

    # Remove any remaining tool markers
    text = re.sub(r'\[TOOL_REQUEST\].*?\[END_TOOL_REQUEST\]', '', text, flags=re.DOTALL)

    # Clean up any extra whitespace from the removals
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)

    # Check if the response indicates a failed search
    if "just returned the search query itself" in text or "search result just returned" in text:
        # Add a suggestion to try again with a different approach
        text += "\n\nI'll try another approach to find more specific information for you."

    return text.strip()

def collect_tool_usage():
    """Extract tool usage information from agent memory"""
    global tools_used, saved_files, tool_results

    try:
        # Extract tools from memory
        for message in radis_agent.memory.messages:
            # Check for tool messages
            if hasattr(message, 'role') and hasattr(message, 'name') and message.role == "tool" and message.name:
                # Add to tools used if not already there
                if message.name not in tools_used:
                    tools_used.append(message.name)

                # Check for file_saver tool
                if message.name == "file_saver" and hasattr(message, 'content') and message.content:
                    # Extract file path from content
                    content = message.content
                    if "saved" in content.lower() and "to" in content.lower():
                        # Basic extraction, can be improved
                        parts = content.split(" to ")
                        if len(parts) > 1:
                            file_path = parts[1].strip()
                            if file_path not in saved_files:
                                saved_files.append(file_path)

                # Add tool result
                if hasattr(message, 'content'):
                    tool_results.append({
                        "name": message.name,
                        "message": message.content
                    })
    except Exception as e:
        logger.error(f"Error collecting tool usage: {str(e)}")
        # Don't re-raise, just continue with empty collections

# Function to start the API server
async def start_api_server(host="0.0.0.0", port=5000):
    """Start the FastAPI server with uvicorn"""
    import uvicorn
    import uvicorn
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

# Run the app with uvicorn when script is executed directly
async def main():
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Start the AgentRadis API server')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    parser.add_argument('--host', type=str, default="0.0.0.0", help='Host to run the server on')
    
    args = parser.parse_args()
    
    print(f"Starting AgentRadis API server on {args.host}:{args.port}")
    await start_api_server(host=args.host, port=args.port)

if __name__ == "__main__":
    asyncio.run(main())
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Start the AgentRadis API server')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    parser.add_argument('--host', type=str, default="0.0.0.0", help='Host to run the server on')
    
    args = parser.parse_args()
    
    print(f"Starting AgentRadis API server on {args.host}:{args.port}")
    start_api_server(host=args.host, port=args.port)
