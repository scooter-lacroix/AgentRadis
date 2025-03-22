"""Collection classes for managing multiple tools."""
from typing import Any, Dict, List, Optional, Set, Type, Union

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolFailure, ToolResult
from app.logger import logger


class ToolCollection:
    """A collection of defined tools."""

    def __init__(self, *tools: BaseTool):
        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}

    def __iter__(self):
        return iter(self.tools)

    def to_params(self) -> List[Dict[str, Any]]:
        return [tool.to_param() for tool in self.tools]

    async def execute(self, name: str, **kwargs) -> Any:
        """
        Execute a tool by name with the given keyword arguments.
        
        Args:
            name: Name of the tool
            **kwargs: Arguments for the tool
            
        Returns:
            Tool execution result
            
        Raises:
            KeyError: If the tool doesn't exist
            Exception: Any error from the tool execution
        """
        # Get the tool
        tool = self.get(name)
        if not tool:
            raise KeyError(f"Tool '{name}' not found in collection")
        
        # Resolve aliases
        if hasattr(tool, 'aliases') and name in tool.aliases:
            # If using an alias, update the name for the logging
            actual_name = tool.name
            logger.info(f"Tool alias '{name}' resolved to '{actual_name}'")
        
        # Execute the tool
        try:
            # First try the 'run' method (modern interface)
            if hasattr(tool, 'run') and callable(tool.run):
                result = await tool.run(**kwargs)
            # Fallback to execute method
            elif hasattr(tool, 'execute') and callable(tool.execute):
                result = await tool.execute(**kwargs)
            # Last resort - call directly
            else:
                result = await tool(**kwargs)
                
            # Ensure the result is a proper tool result
            from app.schema import ToolResult as SchemaToolResult
            if isinstance(result, SchemaToolResult):
                return result
                
            # If it's a dict, try to convert to ToolResult
            if isinstance(result, dict) and 'status' in result:
                try:
                    return SchemaToolResult(
                        tool=name,
                        action=name,
                        status=result.get('status', 'SUCCESS'),
                        result=result
                    )
                except Exception as e:
                    logger.warning(f"Failed to convert dict to ToolResult: {e}")
                    
            # For any other result, create a basic success result
            return SchemaToolResult(
                tool=name,
                action=name,
                status="SUCCESS",
                result={"result": str(result)} if result is not None else {"result": "No result"}
            )
            
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
            # Create an error result
            from app.schema import ToolResult as SchemaToolResult
            return SchemaToolResult(
                tool=name,
                action=name,
                status="ERROR",
                result={"error": str(e)}
            )

    async def execute_all(self) -> List[ToolResult]:
        """Execute all tools in the collection sequentially."""
        results = []
        for tool in self.tools:
            try:
                result = await tool()
                results.append(result)
            except ToolError as e:
                results.append(ToolFailure(error=e.message))
        return results

    def get_tool(self, name: str) -> BaseTool:
        return self.tool_map.get(name)

    def add_tool(self, tool: BaseTool):
        self.tools += (tool,)
        self.tool_map[tool.name] = tool
        return self

    def add_tools(self, *tools: BaseTool):
        for tool in tools:
            self.add_tool(tool)
        return self

    def get_tools(self) -> Dict[str, BaseTool]:
        """Get a dictionary of tools with their names as keys."""
        return self.tool_map
