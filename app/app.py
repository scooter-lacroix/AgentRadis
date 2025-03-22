"""
Main Radis application module
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

from app.logger import logger
from app.tool.tool_manager import ToolManager
from app.mcp_app_store import MCPAppStore
from app.mcp_installer import MCPInstaller
from app.context_tool_runner import ContextToolRunner

class Radis:
    def __init__(self, config=None):
        # Initialize MCP components
        self.mcp_installer = MCPInstaller()
        self.mcp_app_store = MCPAppStore()
        
        # Initialize tools
        self.tool_manager = ToolManager()
        self.tool_manager.register_tools()
        
        # Initialize context-aware tool runner
        self.context_tool_runner = ContextToolRunner(self.tool_manager, self.mcp_app_store)
    
    async def execute_tool(self, tool_name, **params):
        """Execute a tool with the given parameters."""
        try:
            tool = self.tool_manager.get_tool(tool_name)
            if tool:
                return await tool.run(**params)
            else:
                return {"status": "error", "error": f"Tool '{tool_name}' not found"}
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            return {"status": "error", "error": str(e)}
            
    async def execute_tool_with_context(self, tool_name, params, context_id=None):
        """Execute a tool with context preservation."""
        return await self.context_tool_runner.run_with_context(tool_name, params, context_id)
        
    async def execute_multi_step(self, steps, context_id=None):
        """Execute multiple tools in sequence with shared context."""
        return await self.context_tool_runner.run_multi_step(steps, context_id)
        
    async def search_mcp_tools(self, query):
        """Search for MCP tools matching the query."""
        return self.mcp_app_store.search(query)
        
    async def install_mcp_tool(self, tool_id, force=False):
        """Install an MCP tool."""
        success = self.mcp_app_store.install_tool(tool_id, force)
        return {
            "status": "success" if success else "error",
            "tool_id": tool_id,
            "message": f"Tool {tool_id} {'installed successfully' if success else 'failed to install'}"
        }
        
    async def get_available_tools(self, category=None):
        """Get all available tools, optionally filtered by category."""
        tools = []
        
        # Get regular tools from the tool manager
        tool_names = self.tool_manager.list_tools()
        for name in tool_names:
            tool = self.tool_manager.get_tool(name)
            if tool:
                tools.append({
                    "name": name,
                    "description": getattr(tool, "description", ""),
                    "installed": True,
                    "type": "built-in"
                })
                
        # Get MCP tools
        mcp_tools = self.mcp_app_store.get_available_tools(category)
        for tool in mcp_tools:
            # Skip if already in the list
            if tool.get("name") in [t["name"] for t in tools]:
                continue
                
            tools.append({
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "installed": self.mcp_app_store.is_installed(tool.get("id")),
                "type": tool.get("type", "mcp"),
                "id": tool.get("id")
            })
            
        return tools
        
    async def get_tool_info(self, tool_name):
        """Get detailed information about a tool."""
        # Check if it's a regular tool
        tool = self.tool_manager.get_tool(tool_name)
        if tool:
            return {
                "name": tool_name,
                "description": getattr(tool, "description", ""),
                "installed": True,
                "type": "built-in",
                "parameters": getattr(tool, "parameters", {})
            }
            
        # Check MCP tools
        mcp_tools = self.mcp_app_store.search(tool_name)
        if mcp_tools:
            tool = mcp_tools[0]  # Get the first match
            return self.mcp_app_store.get_tool_info(tool.get("id"))
            
        return {"status": "error", "error": f"Tool '{tool_name}' not found"} 