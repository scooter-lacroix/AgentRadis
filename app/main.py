from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import logging
from typing import Dict, Any, Optional, Literal

from app.agent.radis import create_radis_agent
from app.agent.enhanced_radis import EnhancedRadis
from app.config import config
from app.logger import logger

app = FastAPI(title="AgentRadis API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    prompt: str
    api_base: Optional[str] = None
    mode: Literal["plan", "act"] = "act"  # Default to action mode
    debug: bool = True

# Global agent instance
agent = None

async def get_agent(api_base: Optional[str] = None, mode: str = "act") -> EnhancedRadis:
    """Get or create an agent instance with the specified mode"""
    global agent
    if agent is None:
        agent = EnhancedRadis(mode=mode, api_base=api_base)
    elif agent.mode != mode:
        # If mode has changed, create a new agent
        await agent.cleanup()
        agent = EnhancedRadis(mode=mode, api_base=api_base)
    return agent

@app.post("/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """Chat endpoint that supports mode switching."""
    try:
        # Get or create agent with specified mode
        agent = await get_agent(request.api_base, request.mode)
        
        # Run the agent with the prompt
        response = await agent.run(request.prompt)
        
        return {
            "status": "success",
            "response": response.get("response", ""),
            "mode": agent.mode
        }
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"} 