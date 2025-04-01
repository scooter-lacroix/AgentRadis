from typing import Dict, Any, Optional, List
from collections import OrderedDict


class ToolRegistry:
    """
    Registry for tools that can be used by the agent.
    Provides methods to register, retrieve, and list available tools.
    """
    
    def __init__(self):
        self._tools = OrderedDict()
    
    def register_tool(self, tool_name: str, tool_instance: Any) -> None:
        """
        Register a tool with the registry.
        
        Args:
            tool_name: The name of the tool
            tool_instance: The tool instance to register
            
        Raises:
            ValueError: If tool_instance is None
        """
        if tool_instance is None:
            raise ValueError("Cannot register a None tool instance")
        self._tools[tool_name] = tool_instance
    
    def get_tool(self, tool_name: str) -> Optional[Any]:
        """
        Get a tool by name.
        
        Args:
            tool_name: The name of the tool to retrieve
            
        Returns:
            The tool instance if found, None otherwise
        """
        return self._tools.get(tool_name)
    
    def list_tools(self) -> Dict[str, Any]:
        """
        Get a dictionary of all registered tools.
        
        Returns:
            Dictionary mapping tool names to tool instances
        """
        return self._tools.copy()
    
    def has_tool(self, tool_name: str) -> bool:
        """
        Check if a tool is registered.
        
        Args:
            tool_name: The name of the tool to check
            
        Returns:
            True if the tool is registered, False otherwise
        """
        return tool_name in self._tools
    
    def unregister_tool(self, tool_name: str) -> None:
        """
        Unregister a tool from the registry.
        
        Args:
            tool_name: The name of the tool to unregister
        """
        if tool_name in self._tools:
            del self._tools[tool_name]

