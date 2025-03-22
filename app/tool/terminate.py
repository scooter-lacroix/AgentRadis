"""
Termination tool for ending agent execution.
"""
from typing import Any, Dict

from app.logger import logger
from app.tool.base import BaseTool

class Terminate(BaseTool):
    """
    Tool for gracefully terminating agent execution.
    """
    
    name = "terminate"
    description = """
    Terminate the current agent execution.
    This tool signals the agent to stop processing and return a final answer.
    Use this when you have completed a task or have a final answer to provide.
    """
    parameters = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Final message or result to return to the user"
            },
            "reason": {
                "type": "string",
                "description": "Reason for termination (for logging purposes)"
            }
        },
        "required": ["message"]
    }
    
    def __init__(self, **kwargs):
        """Initialize the Terminate tool."""
        super().__init__(**kwargs)
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute a termination request.
        
        Args:
            message: Final message or result to return to the user
            reason: Reason for termination (for logging purposes)
            
        Returns:
            Dictionary with termination status and message
        """
        message = kwargs.get("message", "Task completed.")
        reason = kwargs.get("reason", "Task completed successfully.")
        
        logger.info(f"Agent termination requested: {reason}")
        
        return {
            "status": "terminate",
            "message": message,
            "reason": reason,
            "terminate": True
        }
    
    async def cleanup(self):
        """Clean up resources."""
        pass
    
    async def reset(self):
        """Reset the tool state."""
        pass 