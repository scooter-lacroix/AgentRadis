"""
Tool Manager for handling registration and access to tools.
"""

import logging
from typing import Dict, Any, Optional, List, Type

from app.tool.base import BaseTool
from app.logger import logger
from app.tool.shell_tool import ShellTool
from app.tool.file_tool import FileTool
from app.tool.python_tool import PythonTool
from app.tool.web_tool import WebTool
from app.tool.speech_tool import SpeechTool
from app.tool.bash import Bash

class ToolManager:
    """
    Manager for registering and accessing tools.
    
    The ToolManager provides a centralized registry for all tools in the system.
    It handles registration, retrieval, and execution of tools by name.
    """
    
    def __init__(self):
        """Initialize the tool manager with an empty tools registry."""
        self.tools = {}
        logger.info("Tool Manager initialized")
        
    def register_tool(self, tool: BaseTool) -> None:
        """
        Register a tool with the manager.
        
        Args:
            tool: The tool instance to register
        """
        if not isinstance(tool, BaseTool):
            logger.error(f"Failed to register tool: {tool} is not a BaseTool instance")
            return
            
        tool_name = tool.name
        logger.info(f"Registering tool: {tool_name}")
        self.tools[tool_name] = tool
    
    def register_tools(self) -> None:
        """
        Register all default tools with the manager.
        
        This method initializes the standard set of tools that
        should be available by default in the system.
        """
        # Register core tools
        self.register_tool(ShellTool())
        self.register_tool(FileTool())
        self.register_tool(PythonTool())
        self.register_tool(WebTool())
        self.register_tool(SpeechTool())
        self.register_tool(Bash())
        
        logger.info(f"Registered {len(self.tools)} default tools")
        
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            name: The name of the tool to retrieve
            
        Returns:
            The tool instance or None if not found
        """
        if name not in self.tools:
            logger.warning(f"Tool not found: {name}")
            return None
            
        return self.tools[name]
        
    def list_tools(self) -> List[str]:
        """
        List all registered tool names.
        
        Returns:
            List of registered tool names
        """
        return list(self.tools.keys())
        
    def get_all_tools(self) -> Dict[str, BaseTool]:
        """
        Get all registered tools.
        
        Returns:
            Dictionary mapping tool names to tool instances
        """
        return self.tools.copy()
        
    async def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a tool by name with the given parameters.
        
        Args:
            name: The name of the tool to execute
            **kwargs: Parameters for the tool
            
        Returns:
            Dictionary with the tool execution results
        """
        tool = self.get_tool(name)
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
