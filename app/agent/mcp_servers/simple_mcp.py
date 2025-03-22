"""
Simple MCP Server implementation for testing.
"""

from typing import Dict, Any, List, Optional
import logging

from app.tool.base import BaseTool

logger = logging.getLogger(__name__)

class MCPServer(BaseTool):
    """
    A simple Model Context Protocol (MCP) server for testing purposes.
    """
    
    name: str = "simple_mcp"
    description: str = "A simple MCP server that can perform basic operations for testing"
    examples: List[str] = [
        "simple_mcp(text='Hello world!')",
        "simple_mcp(action='reverse', text='test')"
    ]
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "The action to perform (echo, reverse, uppercase, lowercase)",
                "enum": ["echo", "reverse", "uppercase", "lowercase"]
            },
            "text": {
                "type": "string",
                "description": "The text to process"
            }
        },
        "required": ["text"]
    }
    
    def __init__(self, **kwargs):
        """Initialize the simple MCP server."""
        super().__init__(**kwargs)
        logger.info("Simple MCP server initialized")
    
    async def execute(self, text: str, action: Optional[str] = "echo") -> Dict[str, Any]:
        """
        Execute an operation on the given text.
        
        Args:
            text: The text to process
            action: The action to perform (echo, reverse, uppercase, lowercase)
            
        Returns:
            Dict containing the processing result
        """
        logger.info(f"Simple MCP server executing {action} on text: {text}")
        
        try:
            result = ""
            
            if action == "reverse":
                result = text[::-1]
            elif action == "uppercase":
                result = text.upper()
            elif action == "lowercase":
                result = text.lower()
            else:  # Default to echo
                result = text
                
            return {
                'status': 'success',
                'content': f"Result: {result}"
            }
        
        except Exception as e:
            logger.error(f"Error in Simple MCP server: {str(e)}")
            return {
                'status': 'error',
                'content': f"Error processing text: {str(e)}"
            }
    
    async def run(self, **kwargs):
        """Execute an MCP operation (alias for execute)."""
        if "text" not in kwargs:
            return {
                'status': 'error',
                'content': "Missing required parameter: text"
            }
        
        action = kwargs.get("action", "echo")
        return await self.execute(text=kwargs["text"], action=action)
        
    async def cleanup(self):
        """Clean up resources."""
        logger.info("Simple MCP server cleaning up resources")
        
    async def reset(self):
        """Reset the tool's state."""
        logger.info("Simple MCP server reset") 