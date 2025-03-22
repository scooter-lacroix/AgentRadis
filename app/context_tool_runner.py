"""
Context-Aware Tool Runner for executing complex multi-step tool operations
"""

import os
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Union
import logging

from app.logger import logger
from app.mcp_app_store import MCPAppStore

class ContextToolRunner:
    """
    Context-aware tool runner for executing complex multi-step tool operations
    
    This class handles the execution of tools while maintaining context between
    steps, allowing for more complex operations that require multiple tools or
    sequential steps.
    """
    
    def __init__(self, tool_manager, app_store: Optional[MCPAppStore] = None):
        """
        Initialize the context tool runner.
        
        Args:
            tool_manager: Tool manager instance to execute tools
            app_store: Optional MCP App Store for installing required tools
        """
        self.tool_manager = tool_manager
        self.app_store = app_store or MCPAppStore()
        self.context = {}
        self.execution_history = []
        
    async def run_with_context(self, tool_name: str, params: Dict[str, Any], 
                             context_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a tool with context preservation.
        
        Args:
            tool_name: Name of the tool to run
            params: Parameters for the tool
            context_id: Optional ID for the context to use/create
            
        Returns:
            Results of the tool execution with context information
        """
        # Create or get context
        ctx = self._get_or_create_context(context_id)
        
        # Log the execution request
        logger.info(f"Running tool '{tool_name}' with context '{context_id}'")
        
        # Check if the tool is available
        tool = self.tool_manager.get_tool(tool_name)
        if not tool:
            # Try to install the tool if we have an app store
            tool_installed = False
            if self.app_store:
                logger.info(f"Tool '{tool_name}' not found, attempting to install")
                if await self._install_required_tool(tool_name):
                    # Try to get the tool again after installation
                    tool = self.tool_manager.get_tool(tool_name)
                    tool_installed = True
                    
            if not tool:
                logger.error(f"Tool '{tool_name}' not found and could not be installed")
                return {
                    "status": "error",
                    "error": f"Tool '{tool_name}' not found",
                    "context_id": context_id,
                    "installed_attempt": tool_installed
                }
                
        # Merge context values into params if needed
        merged_params = self._merge_context_params(ctx, params)
        
        # Execute the tool
        start_time = time.time()
        try:
            result = await tool.run(**merged_params)
            execution_time = time.time() - start_time
            
            # Record execution in history
            execution_record = {
                "tool": tool_name,
                "params": merged_params,
                "result_status": result.get("status", "unknown"),
                "timestamp": time.time(),
                "execution_time": execution_time,
                "context_id": context_id
            }
            self.execution_history.append(execution_record)
            
            # Update context with results
            self._update_context(ctx, result)
            
            # Add context_id to result
            result["context_id"] = context_id
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {str(e)}")
            execution_time = time.time() - start_time
            
            # Record execution error in history
            execution_record = {
                "tool": tool_name,
                "params": merged_params,
                "result_status": "error",
                "error": str(e),
                "timestamp": time.time(),
                "execution_time": execution_time,
                "context_id": context_id
            }
            self.execution_history.append(execution_record)
            
            return {
                "status": "error",
                "error": f"Error executing tool '{tool_name}': {str(e)}",
                "context_id": context_id
            }
            
    async def run_multi_step(self, steps: List[Dict[str, Any]], 
                           context_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Run multiple tools in sequence, sharing context between them.
        
        Args:
            steps: List of steps to execute, each containing tool_name and params
            context_id: Optional ID for the context to use/create
            
        Returns:
            List of results from each step
        """
        results = []
        ctx_id = context_id or f"multi_{int(time.time())}"
        
        logger.info(f"Running multi-step operation with {len(steps)} steps, context: {ctx_id}")
        
        for i, step in enumerate(steps):
            tool_name = step.get("tool_name")
            params = step.get("params", {})
            
            if not tool_name:
                error_result = {
                    "status": "error",
                    "error": f"Missing tool_name in step {i}",
                    "step": i,
                    "context_id": ctx_id
                }
                results.append(error_result)
                break
                
            # Execute the step with shared context
            result = await self.run_with_context(tool_name, params, ctx_id)
            results.append(result)
            
            # Check if we should continue
            if result.get("status") == "error" and not step.get("continue_on_error", False):
                logger.warning(f"Stopping multi-step execution after error in step {i}")
                break
                
        return results
        
    def _get_or_create_context(self, context_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get or create a context by ID.
        
        Args:
            context_id: ID of the context to get or create
            
        Returns:
            The context dictionary
        """
        if not context_id:
            # Generate a unique context ID
            context_id = f"ctx_{int(time.time())}"
            
        if context_id not in self.context:
            self.context[context_id] = {
                "created_at": time.time(),
                "updated_at": time.time(),
                "values": {},
                "results": []
            }
            
        return self.context[context_id]
        
    def _merge_context_params(self, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge context values into params.
        
        Args:
            context: Context dictionary
            params: Parameters dictionary
            
        Returns:
            Merged parameters dictionary
        """
        # Start with a copy of the original params
        merged = dict(params)
        
        # Get context values
        context_values = context.get("values", {})
        
        # Check for context references in params
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("${context.") and value.endswith("}"):
                # Extract the context key
                ctx_key = value[10:-1]
                if ctx_key in context_values:
                    merged[key] = context_values[ctx_key]
                    
        return merged
        
    def _update_context(self, context: Dict[str, Any], result: Dict[str, Any]):
        """
        Update context with results from a tool execution.
        
        Args:
            context: Context dictionary to update
            result: Result dictionary from tool execution
        """
        # Update the last update timestamp
        context["updated_at"] = time.time()
        
        # Add the result to the results history
        context["results"].append(result)
        
        # Extract values from the result and add to context values
        # We exclude some keys that are not useful for context
        excluded_keys = ["status", "error", "message", "context_id"]
        
        for key, value in result.items():
            if key not in excluded_keys:
                context["values"][key] = value
                
    async def _install_required_tool(self, tool_name: str) -> bool:
        """
        Install a required tool using the MCP App Store.
        
        Args:
            tool_name: Name of the tool to install
            
        Returns:
            True if installation was successful, False otherwise
        """
        if not self.app_store:
            return False
            
        # Map tool names to MCP tool IDs
        tool_mapping = {
            "speech": "realtimestt"  # Also installs realtimetts
        }
        
        # Check if we have a mapping for this tool
        mcp_id = tool_mapping.get(tool_name)
        if not mcp_id:
            logger.warning(f"No MCP mapping for tool '{tool_name}'")
            return False
            
        logger.info(f"Installing required tool '{mcp_id}' for '{tool_name}'")
        
        # Handle special cases
        if mcp_id == "realtimestt":
            # Install both STT and TTS for speech tools
            result = await asyncio.to_thread(
                self.app_store.install_speech_capabilities
            )
            return all(result.values())
        else:
            # General case
            result = await asyncio.to_thread(
                self.app_store.install_tool, mcp_id
            )
            return result
            
    def get_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a context by ID.
        
        Args:
            context_id: ID of the context to get
            
        Returns:
            The context dictionary, or None if not found
        """
        return self.context.get(context_id)
        
    def get_context_value(self, context_id: str, key: str) -> Any:
        """
        Get a value from a context.
        
        Args:
            context_id: ID of the context
            key: Key of the value to get
            
        Returns:
            The value, or None if not found
        """
        context = self.get_context(context_id)
        if not context:
            return None
            
        return context.get("values", {}).get(key)
        
    def clear_context(self, context_id: Optional[str] = None):
        """
        Clear a context or all contexts.
        
        Args:
            context_id: ID of the context to clear, or None to clear all
        """
        if context_id:
            if context_id in self.context:
                del self.context[context_id]
                logger.info(f"Cleared context '{context_id}'")
        else:
            self.context = {}
            logger.info("Cleared all contexts")
            
    def get_execution_history(self, context_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get execution history, optionally filtered by context ID.
        
        Args:
            context_id: Optional context ID to filter by
            
        Returns:
            List of execution records
        """
        if context_id:
            return [r for r in self.execution_history if r.get("context_id") == context_id]
        return self.execution_history
        
    def get_available_tools(self, category: Optional[str] = None) -> List[str]:
        """
        Get names of available tools, optionally filtered by category.
        
        Args:
            category: Optional category to filter by
            
        Returns:
            List of tool names
        """
        # Get tools from tool manager
        tools = self.tool_manager.list_tools()
        
        # Add potential tools from MCP app store that aren't installed yet
        if self.app_store:
            # Convert to async to thread to work with synchronous app store methods
            try:
                available_tools = asyncio.run(asyncio.to_thread(
                    self.app_store.get_available_tools, category
                ))
                
                for tool in available_tools:
                    tool_id = tool.get("id")
                    if tool_id and tool_id not in tools:
                        tools.append(tool_id)
            except Exception as e:
                logger.error(f"Error getting available tools from app store: {e}")
                
        return tools 