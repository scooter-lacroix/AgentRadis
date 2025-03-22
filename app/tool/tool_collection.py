"""
Tool collection for managing groups of tools.
"""
from typing import Any, Dict, List, Optional, Union, Callable
import inspect
import json

from app.logger import logger
from app.tool.base import BaseTool

class ToolCollection:
    """
    Collection for managing and accessing multiple tools.
    
    The ToolCollection provides a way to manage a group of tools and
    access them by name or other properties.
    """
    
    def __init__(self, *args):
        """
        Initialize the tool collection with provided tools.
        
        Args:
            *args: Tools to include in the collection
        """
        self.tools = {}
        
        # Add all provided tools
        for tool in args:
            if isinstance(tool, BaseTool):
                self.add(tool)
            else:
                logger.warning(f"Skipping non-tool object: {tool}")
    
    def add(self, tool: BaseTool) -> None:
        """
        Add a tool to the collection.
        
        Args:
            tool: The tool instance to add
        """
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Expected BaseTool instance, got {type(tool)}")
            
        name = tool.name
        self.tools[name] = tool
        logger.debug(f"Added tool '{name}' to collection")
    
    def remove(self, name: str) -> None:
        """
        Remove a tool from the collection.
        
        Args:
            name: The name of the tool to remove
        """
        if name in self.tools:
            del self.tools[name]
            logger.debug(f"Removed tool '{name}' from collection")
    
    def get(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            name: The name of the tool to retrieve
            
        Returns:
            The tool instance or None if not found
        """
        return self.tools.get(name)
    
    def get_all(self) -> Dict[str, BaseTool]:
        """
        Get all tools in the collection.
        
        Returns:
            Dictionary of tool names to tool instances
        """
        return self.tools.copy()
    
    def filter(self, predicate: Callable[[BaseTool], bool]) -> "ToolCollection":
        """
        Filter tools based on a predicate function.
        
        Args:
            predicate: Function that returns True for tools to include
            
        Returns:
            New ToolCollection with filtered tools
        """
        new_collection = ToolCollection()
        for tool in self.tools.values():
            if predicate(tool):
                new_collection.add(tool)
        return new_collection
    
    def list_names(self) -> List[str]:
        """
        Get the names of all tools in the collection.
        
        Returns:
            List of tool names
        """
        return list(self.tools.keys())
    
    def list_tools_with_params(self) -> List[Dict[str, Any]]:
        """
        Get list of tools with their parameters for function calling.
        
        Returns:
            List of tool definitions in function calling format
        """
        result = []
        for tool in self.tools.values():
            tool_def = {
                "name": tool.name,
                "description": tool.description.strip(),
                "parameters": tool.parameters
            }
            result.append(tool_def)
        return result
    
    def to_params(self) -> List[Dict[str, Any]]:
        """
        Get list of tools with their parameters in the format expected by LLMs.
        This returns tools in the OpenAI function calling format.
        
        Returns:
            List of tool definitions in function calling format
        """
        result = []
        for tool in self.tools.values():
            if hasattr(tool, 'to_param') and callable(tool.to_param):
                result.append(tool.to_param())
            else:
                # Fallback to constructing it manually
                tool_def = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description.strip(),
                        "parameters": tool.parameters
                    }
                }
                result.append(tool_def)
        return result
    
    async def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a tool by name with the provided parameters.
        
        Args:
            name: The name of the tool to execute
            **kwargs: Parameters for the tool
            
        Returns:
            Dictionary with the results or error
        """
        tool = self.get(name)
        if not tool:
            return {
                "status": "error",
                "error": f"Tool not found: {name}"
            }
            
        try:
            logger.info(f"Executing tool: {name}")
            result = await tool.run(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return {
                "status": "error",
                "error": f"Tool execution failed: {str(e)}"
            }
    
    def __contains__(self, name: str) -> bool:
        """Check if a tool with the given name is in the collection."""
        return name in self.tools
    
    def __getitem__(self, name: str) -> BaseTool:
        """Get a tool by name using dictionary syntax."""
        if name not in self.tools:
            raise KeyError(f"Tool not found: {name}")
        return self.tools[name]
    
    def __iter__(self):
        """Iterate through the tools in the collection."""
        return iter(self.tools.values())
    
    def __len__(self) -> int:
        """Get the number of tools in the collection."""
        return len(self.tools)
    
    def __repr__(self) -> str:
        """String representation of the tool collection."""
        return f"ToolCollection({', '.join(self.tools.keys())})" 