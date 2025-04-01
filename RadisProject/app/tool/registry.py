"""Tool registry system for managing and accessing tool implementations.

DEPRECATED: This module is being maintained for backward compatibility.
For new code, use app.core.tool_registry directly.
"""

import warnings
from typing import Optional, Any

warnings.warn(
    'This module is deprecated. Use app.core.tool_registry instead.',
    DeprecationWarning,
    stacklevel=2
)

from app.core.tool_registry import get_tool_registry as get_core_registry
from app.core.tool_registry import ToolNotFoundError
from app.tool.base import BaseTool
Tool = BaseTool  # Type alias for backward compatibility

class ToolRegistry:
    """Registry for managing tool implementations.

    DEPRECATED: This class is a wrapper around the core ToolRegistry for 
    backward compatibility. For new code, use app.core.tool_registry directly.

    This class provides a thread-safe registry for storing and retrieving tool
    instances. Tools are stored by name and can be retrieved using their names.

    Attributes:
        _core_registry: The underlying core tool registry instance
    """

    def __init__(self) -> None:
        """Initialize with a reference to the core tool registry."""
        self._core_registry = get_core_registry()

    def register_tool(self, name: str, tool_instance: BaseTool) -> None:
        """Register a new tool instance.

        Args:
            name: The name under which to register the tool
            tool_instance: The tool instance to register

        Raises:
            ValueError: If a tool with the same name is already registered
        """
        try:
            self._core_registry.register_tool(name, tool_instance)
        except Exception as e:
            # Convert core exceptions to maintain backward compatibility
            raise ValueError(f"Tool {name} is already registered") from e

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Retrieve a tool implementation by name.

        Args:
            tool_name: Name of the tool instance to retrieve

        Returns:
            The registered tool instance if found, None otherwise
        """
        try:
            return self._core_registry.get_tool(tool_name)
        except ToolNotFoundError:
            # Return None instead of raising an exception for backward compatibility
            return None

    def unregister_tool(self, tool_name: str) -> None:
        """Remove a tool implementation from the registry.

        Args:
            tool_name: Name of the tool instance to unregister

        Raises:
            KeyError: If the tool is not registered
        """
        try:
            self._core_registry.unregister_tool(tool_name)
        except ToolNotFoundError as e:
            # Convert core exceptions to maintain backward compatibility
            raise KeyError(f"Tool {tool_name} is not registered") from e

    def list_tools(self) -> list[str]:
        """Get a list of all registered tool names.

        Returns:
            List of registered tool names
        """
        # Convert dict of {name: instance} to list of names for backward compatibility
        return list(self._core_registry.list_tools().keys())


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance.

    This function implements the singleton pattern, ensuring only one
    ToolRegistry instance exists throughout the application.
    
    DEPRECATED: This function is maintained for backward compatibility.
    For new code, use app.core.tool_registry.get_tool_registry() directly.

    Returns:
        The global ToolRegistry instance
    """
    warnings.warn(
        '\nSTRONG DEPRECATION WARNING: get_tool_registry() will be removed in a future version.\n'
        'Please update your code to use app.core.tool_registry.get_tool_registry() instead.\n'
        'This function currently wraps the core implementation but will be removed to reduce confusion.',
        FutureWarning,
        stacklevel=2
    )
    return ToolRegistry()


__all__ = ["ToolRegistry", "get_tool_registry"]
