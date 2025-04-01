"""
Tool Registry - Core Implementation

This module provides a thread-safe singleton implementation for managing tools
in the RadisProject. It handles tool registration, validation, and metrics tracking.
"""

import logging
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

class ToolRegistryError(Exception):
    """Base exception for all tool registry related errors."""
    pass

class ToolNotFoundError(ToolRegistryError):
    """Raised when attempting to access a tool that isn't registered."""
    pass

class ToolValidationError(ToolRegistryError):
    """Raised when a tool fails validation checks."""
    pass

class DuplicateToolError(ToolRegistryError):
    """Raised when attempting to register a tool with a name that's already taken."""
    pass

@dataclass
class ToolMetrics:
    """Stores metrics for a registered tool."""
    calls: int = 0
    total_execution_time: float = 0.0
    last_called: Optional[float] = None
    average_execution_time: float = 0.0

class Tool:
    """Represents a registered tool with its handler and metadata."""
    def __init__(self, name: str, handler: Callable, description: str):
        self.name = name
        self.handler = handler
        self.description = description
        self.metrics = ToolMetrics()

class ToolRegistry:
    """
    Thread-safe singleton registry for managing tools.
    
    This class provides centralized tool management with features including:
    - Thread-safe tool registration and access
    - Tool validation
    - Usage metrics tracking
    - Comprehensive error handling
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._tools: Dict[str, Tool] = {}
            self._tools_lock = threading.Lock()
            self._initialized = True
    
    def register_tool(self, name: str, handler: Callable, description: str = "") -> None:
        """
        Register a new tool with the registry.
        
        Args:
            name: Unique identifier for the tool
            handler: Callable that implements the tool's functionality
            description: Optional description of the tool's purpose
            
        Raises:
            DuplicateToolError: If a tool with the same name is already registered
            ToolValidationError: If the tool fails validation checks
        """
        if not callable(handler):
            raise ToolValidationError(f"Tool handler for '{name}' must be callable")
            
        with self._tools_lock:
            if name in self._tools:
                raise DuplicateToolError(f"Tool '{name}' is already registered")
                
            self._tools[name] = Tool(name, handler, description)
            logger.info(f"Successfully registered tool: {name}")
    
    def get_tool(self, name: str) -> Callable:
        """
        Retrieve a registered tool's handler.
        
        Args:
            name: Name of the tool to retrieve
            
        Returns:
            The tool's handler function
            
        Raises:
            ToolNotFoundError: If the requested tool isn't registered
        """
        with self._tools_lock:
            if name not in self._tools:
                raise ToolNotFoundError(f"Tool '{name}' not found in registry")
            
            tool = self._tools[name]
            return self._create_metric_wrapper(tool)
    
    def _create_metric_wrapper(self, tool: Tool) -> Callable:
        """Create a wrapper that tracks metrics for tool execution."""
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = tool.handler(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                with self._tools_lock:
                    tool.metrics.calls += 1
                    tool.metrics.total_execution_time += execution_time
                    tool.metrics.last_called = time.time()
                    tool.metrics.average_execution_time = (
                        tool.metrics.total_execution_time / tool.metrics.calls
                    )
        return wrapper
    
    def unregister_tool(self, name: str) -> None:
        """
        Remove a tool from the registry.
        
        Args:
            name: Name of the tool to remove
            
        Raises:
            ToolNotFoundError: If the tool isn't registered
        """
        with self._tools_lock:
            if name not in self._tools:
                raise ToolNotFoundError(f"Cannot unregister non-existent tool: {name}")
            
            del self._tools[name]
            logger.info(f"Successfully unregistered tool: {name}")
    
    def list_tools(self) -> List[str]:
        """
        Get a list of all registered tool names.
        
        Returns:
            List of registered tool names
        """
        with self._tools_lock:
            return list(self._tools.keys())
    
    def get_tool_metrics(self, name: str) -> ToolMetrics:
        """
        Get usage metrics for a specific tool.
        
        Args:
            name: Name of the tool
            
        Returns:
            ToolMetrics object containing usage statistics
            
        Raises:
            ToolNotFoundError: If the tool isn't registered
        """
        with self._tools_lock:
            if name not in self._tools:
                raise ToolNotFoundError(f"Cannot get metrics for non-existent tool: {name}")
            return self._tools[name].metrics

def get_tool_registry() -> ToolRegistry:
    """
    Get the global ToolRegistry instance.
    
    Returns:
        The singleton ToolRegistry instance
    """
    return ToolRegistry()

import logging
import threading
from typing import Dict, Optional, Type, Any, Protocol
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Tool(Protocol):
    """Protocol defining the interface that all tools must implement."""
    
    def execute(self, *args: Any, **kwargs: Any) -> Any: ...

class ToolRegistryError(Exception):
    """Base exception for tool registry related errors."""
    pass

class ToolAlreadyRegisteredError(ToolRegistryError):
    """Exception raised when attempting to register a tool that already exists."""
    pass

class ToolNotFoundError(ToolRegistryError):
    """Exception raised when attempting to access a tool that doesn't exist."""
    pass

class ToolValidationError(ToolRegistryError):
    """Exception raised when tool validation fails."""
    pass

class ToolRegistry:
    """
    A thread-safe singleton registry for managing tools.
    Provides methods for registering, unregistering, and retrieving tools.
    
    This class implements the singleton pattern to ensure only one registry
    instance exists throughout the application.
    """
    _instance: Optional['ToolRegistry'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'ToolRegistry':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                # Initialize instance attributes
                cls._instance._tools: Dict[str, Any] = {}
                cls._instance._metrics: Dict[str, Dict[str, Any]] = {}
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        with self._lock:
            if not self._initialized:
                self._tools = {}
                self._metrics = {}
                self._initialized = True
                logger.info("ToolRegistry initialized")

    def register_tool(self, tool_name: str, tool_instance: Any, validate_on_register: bool = False) -> None:
        """
        Register a new tool with optional validation.
        
        Args:
            tool_name: Name of the tool
            tool_instance: Instance of the tool to register
            validate_on_register: If True, validate the tool's parameters before registering
            
        Raises:
            ToolAlreadyRegisteredException: If tool is already registered
            ToolValidationException: If tool validation fails and validate_on_register is True
        """
        with self._lock:
            if tool_name in self._tools:
                raise ToolAlreadyRegisteredError(f"Tool '{tool_name}' is already registered")

            try:
                # Only validate if validate_on_register is True
                if validate_on_register:
                    if hasattr(tool_instance, 'validate_parameters'):
                        # Pass empty dict as default parameters for validation
                        validation_result = tool_instance.validate_parameters({})
                        if not validation_result.get('valid', False):
                            raise ToolValidationError(validation_result.get('error', 'Unknown validation error'))
                    else:
                        logger.warning(f"Tool '{tool_name}' does not implement validate_parameters")

                self._tools[tool_name] = tool_instance
                self._metrics[tool_name] = {
                    'registration_time': datetime.now(),
                    'call_count': 0,
                    'last_used': None
                }
                logger.info(f"Tool '{tool_name}' successfully registered")
            except Exception as e:
                logger.error(f"Failed to register tool '{tool_name}': {str(e)}")
                raise ToolValidationError(f"Tool validation failed: {str(e)}")

    def unregister_tool(self, tool_name: str) -> None:
        """
        Unregister a tool from the registry.
        
        Args:
            tool_name: Name of the tool to unregister
            
        Raises:
            ToolNotFoundException: If tool is not found in registry
        """
        with self._lock:
            if tool_name not in self._tools:
                raise ToolNotFoundError(f"Tool '{tool_name}' not found in registry")

            del self._tools[tool_name]
            del self._metrics[tool_name]
            logger.info(f"Tool '{tool_name}' successfully unregistered")

    def get_tool(self, tool_name: str) -> Any:
        """
        Retrieve a tool from the registry.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            The requested tool instance
            
        Raises:
            ToolNotFoundException: If tool is not found in registry
        """
        with self._lock:
            if tool_name not in self._tools:
                raise ToolNotFoundError(f"Tool '{tool_name}' not found in registry")

            # Update metrics
            self._metrics[tool_name]['call_count'] += 1
            self._metrics[tool_name]['last_used'] = datetime.now()
            
            return self._tools[tool_name]

    def list_tools(self) -> Dict[str, Any]:
        """
        Get a dictionary of all registered tools.
        
        Returns:
            Dictionary of tool names and their instances
        """
        with self._lock:
            return self._tools.copy()

    def get_metrics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get usage metrics for tools.
        
        Args:
            tool_name: Optional specific tool to get metrics for
            
        Returns:
            Dictionary of metrics
            
        Raises:
            ToolNotFoundException: If specific tool is requested but not found
        """
        with self._lock:
            if tool_name is not None:
                if tool_name not in self._metrics:
                    raise ToolNotFoundError(f"Tool '{tool_name}' not found in registry")
                return self._metrics[tool_name].copy()
            return self._metrics.copy()

    def clear_registry(self) -> None:
        """Clear all tools from the registry."""
        with self._lock:
            self._tools.clear()
            self._metrics.clear()
            self._metrics.clear()
            logger.info("Tool registry cleared")

    def has_tool(self, tool_name: str) -> bool:
        """
        Check if a tool exists in the registry.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if the tool exists, False otherwise
        """
        with self._lock:
            return tool_name in self._tools

    def get_tool_count(self) -> int:
        """
        Get the number of tools registered.
        
        Returns:
            Number of registered tools
        """
        with self._lock:
            return len(self._tools)


# Singleton global access function
def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.
    
    This function provides global access to the singleton ToolRegistry instance,
    ensuring only one registry exists throughout the application.
    
    Returns:
        The global ToolRegistry instance
    """
    return ToolRegistry()  # The instance is created or retrieved in __new__


__all__ = ["ToolRegistry", "get_tool_registry", "ToolRegistryError", 
           "ToolAlreadyRegisteredError", "ToolNotFoundError", "ToolValidationError"]

# Test Tool Implementation
class TestCalculatorTool:
    """A simple calculator tool for testing the registry."""
    
    def execute(self, operation: str, x: float, y: float) -> float:
        """
        Execute basic arithmetic operations.
        
        Args:
            operation: One of 'add', 'subtract', 'multiply', 'divide'
            x: First number
            y: Second number
            
        Returns:
            Result of the arithmetic operation
        """
        operations = {
            'add': lambda a, b: a + b,
            'subtract': lambda a, b: a - b,
            'multiply': lambda a, b: a * b,
            'divide': lambda a, b: a / b if b != 0 else float('inf')
        }
        
        if operation not in operations:
            raise ValueError(f"Unknown operation: {operation}")
            
        return operations[operation](x, y)
        
    def validate_parameters(self) -> None:
        """Validate that the tool has all required methods."""
        if not hasattr(self, 'execute'):
            raise ToolValidationError("TestCalculatorTool must implement execute method")

# Example usage and testing
def test_tool_registry():
    """Test the tool registry functionality with the calculator tool."""
    registry = get_tool_registry()
    
    # Create and register the test tool
    calc_tool = TestCalculatorTool()
    try:
        registry.register_tool("calculator", calc_tool)
        print("Successfully registered calculator tool")
        
        # Retrieve and use the tool
        retrieved_tool = registry.get_tool("calculator")
        result = retrieved_tool.execute("add", 5, 3)
        print(f"Calculator test (5 + 3): {result}")
        
        # Check metrics
        metrics = registry.get_metrics("calculator")
        print(f"Tool metrics: {metrics}")
        
        # List all tools
        tools = registry.list_tools()
        print(f"Registered tools: {tools}")
        
        # Clean up
        registry.unregister_tool("calculator")
        print("Successfully unregistered calculator tool")
        
    except Exception as e:
        print(f"Error during tool testing: {str(e)}")
        raise

if __name__ == "__main__":
    test_tool_registry()
