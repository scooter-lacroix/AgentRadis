"""Minimal API server for testing"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

# Create FastAPI app
app = FastAPI(title="Minimal AgentRadis API", description="Minimal API for testing")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models for requests and responses
class ChatRequest(BaseModel):
    prompt: Optional[str] = None
    message: Optional[str] = None
    mode: Optional[str] = "action"

class ChatResponse(BaseModel):
    response: str
    status: str = "success"
    error: Optional[str] = None

# Health check endpoint
@app.get("/health")
async def health_check():
    """Check if the API is running"""
    return {"status": "ok"}

# Main chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat request"""
    try:
        # Get the prompt from either field
        prompt = request.prompt or request.message
        if not prompt:
            return ChatResponse(
                response="No prompt provided", 
                status="error",
                error="Either 'prompt' or 'message' field is required"
            )

        # Return a simple response
        return ChatResponse(
            response=f"Received your prompt: {prompt}. Mode: {request.mode}",
            status="success"
        )

    except Exception as e:
        return ChatResponse(
            response="An error occurred while processing your request.",
            status="error",
            error=str(e)
        )

# Function to start the API server
def start_api_server(host="0.0.0.0", port=5002):
    """Start the FastAPI server with uvicorn"""
    import uvicorn
    print(f"Starting Minimal API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

# Run the app with uvicorn when script is executed directly
if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Start the Minimal API server')
    parser.add_argument('--port', type=int, default=5002, help='Port to run the server on')
    parser.add_argument('--host', type=str, default="0.0.0.0", help='Host to run the server on')
    
    args = parser.parse_args()
    
    start_api_server(host=args.host, port=args.port) 