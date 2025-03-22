"""
Base Tool - Abstract base class for all tools
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List, Union
from abc import ABC, abstractmethod

from app.logger import logger

class BaseTool(ABC):
    """
    Abstract base class for all tools.
    
    This class defines the interface that all tools must implement.
    """
    
    # Tool properties to be defined by subclasses
    name = "base"
    description = "Base tool class"
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self, **kwargs):
        """Initialize the tool with optional keyword arguments."""
        for key, value in kwargs.items():
            setattr(self, key, value)
            
    @abstractmethod
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Run the tool with the given parameters.
        
        Args:
            **kwargs: Parameters for the tool
            
        Returns:
            Dictionary with the results of the tool execution
        """
        raise NotImplementedError("Subclasses must implement run()")
        
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool, wrapping run() with logging and error handling.
        
        Args:
            **kwargs: Parameters for the tool
            
        Returns:
            Dictionary with the results of the tool execution
        """
        logger.info(f"Executing tool '{self.name}'")
        try:
            return await self.run(**kwargs)
        except Exception as e:
            logger.error(f"Error executing tool '{self.name}': {e}")
            return {
                "status": "error",
                "error": str(e)
            }
            
    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters against the tool's schema.
        
        Args:
            params: Parameters to validate
            
        Returns:
            Dictionary with validation results
        """
        # For now, just check required parameters
        required = self.parameters.get("required", [])
        missing = [param for param in required if param not in params]
        
        if missing:
            return {
                "valid": False,
                "missing": missing,
                "error": f"Missing required parameters: {', '.join(missing)}"
            }
            
        return {
            "valid": True
        }
        
    async def cleanup(self):
        """Clean up resources used by the tool."""
        pass

    async def reset(self):
        """Reset the tool's state if it's stateful."""
        pass

    async def __call__(self, **kwargs):
        """Make the tool callable."""
        return await self.execute(**kwargs)

    def to_param(self) -> Dict:
        """Convert tool to OpenAI function call format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters.get("properties", {}),
                    "required": self.parameters.get("required", [])
                }
            }
        }
