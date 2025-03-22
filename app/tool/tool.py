"""
Base tool implementation for AgentRadis.

This module defines the base Tool class from which all tools should inherit.
"""
import asyncio
import inspect
import time
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union, ClassVar, get_type_hints

from pydantic import BaseModel, Field, create_model

from app.exceptions import (
    InvalidToolArgumentException,
    ToolExecutionException,
    ToolTimeoutException,
)
from app.logger import get_tool_logger, logger
from app.schema import ToolResult


def wrap_sync_method(method: Callable) -> Callable:
    """Wraps a synchronous method to be called asynchronously."""
    @wraps(method)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: method(*args, **kwargs))
    return wrapper


class Tool(ABC):
    """Base class for all tools.
    
    All tools must inherit from this base class and implement the execute method.
    """
    
    # Class attributes that should be overridden by subclasses
    name: ClassVar[str] = "base_tool"
    description: ClassVar[str] = "Base tool class"
    examples: ClassVar[List[str]] = []
    is_stateful: ClassVar[bool] = False
    timeout: ClassVar[float] = 30.0  # Default timeout in seconds
    
    # Parameter schema for documentation
    _param_schema: Optional[Type[BaseModel]] = None
    _return_schema: Optional[Type[BaseModel]] = None
    
    def __init__(self):
        """Initialize the tool."""
        self.logger = get_tool_logger(self.name)
        self._execution_count = 0
        self._last_execution_time = 0
        self._execution_times = []  # Track recent execution times
        self._max_times_to_track = 10
        
    def __init_subclass__(cls, **kwargs):
        """Automatically generate parameter schema from execute method annotations."""
        super().__init_subclass__(**kwargs)
        
        # Ensure name is set
        if cls.name == "base_tool" and cls.__name__ != "Tool":
            cls.name = cls.__name__.lower()
            
        # Generate parameter schema from _execute method's type hints
        try:
            hints = get_type_hints(cls._execute)
            
            # Remove return type and self
            hints.pop('return', None)
            hints.pop('self', None)
            
            # Create fields with defaults from method signature
            fields = {}
            sig = inspect.signature(cls._execute)
            for name, param in sig.parameters.items():
                if name == 'self':
                    continue
                
                default = ... if param.default is inspect.Parameter.empty else param.default
                annotation = hints.get(name, Any)
                
                fields[name] = (annotation, Field(default, description=f"Parameter {name}"))
                
            # Create parameter schema
            param_model_name = f"{cls.__name__}Params"
            cls._param_schema = create_model(
                param_model_name,
                **fields,
                __module__=cls.__module__
            )
            
            # Create return schema
            if 'return' in hints:
                return_model_name = f"{cls.__name__}Return"
                cls._return_schema = create_model(
                    return_model_name,
                    result=(hints['return'], ...),
                    __module__=cls.__module__
                )
                
        except (AttributeError, TypeError) as e:
            logger.warning(f"Could not generate parameter schema for {cls.__name__}: {e}")
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get tool metadata.
        
        Returns:
            Dict of metadata about the tool.
        """
        execution_metrics = {}
        if self._execution_times:
            execution_metrics = {
                "avg_execution_time": sum(self._execution_times) / len(self._execution_times),
                "min_execution_time": min(self._execution_times),
                "max_execution_time": max(self._execution_times),
                "last_execution_time": self._last_execution_time,
                "execution_count": self._execution_count
            }
            
        return {
            "name": self.name,
            "description": self.description,
            "examples": self.examples,
            "is_stateful": self.is_stateful,
            "timeout": self.timeout,
            "parameters": self._param_schema.schema() if self._param_schema else {},
            "returns": self._return_schema.schema() if self._return_schema else {},
            "execution_metrics": execution_metrics
        }
    
    def to_param(self) -> Dict[str, Any]:
        """Convert tool to function call format for LLM API.
        
        Returns:
            Dict containing the tool definition in function calling format
        """
        parameters = self._param_schema.schema() if self._param_schema else {"type": "object", "properties": {}}
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with the provided arguments.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            ToolResult containing the result of the execution
        """
        self._execution_count += 1
        start_time = time.time()
        exec_id = self.logger.start_execution(**kwargs)
        
        try:
            # Create a task with timeout
            task = asyncio.create_task(self._execute(**kwargs))
            result = await asyncio.wait_for(task, timeout=self.timeout)
            
            # Track execution time
            execution_time = time.time() - start_time
            self._last_execution_time = execution_time
            self._execution_times.append(execution_time)
            if len(self._execution_times) > self._max_times_to_track:
                self._execution_times.pop(0)
                
            # Ensure result is a ToolResult
            if not isinstance(result, ToolResult):
                if isinstance(result, dict):
                    # Try to convert dict to ToolResult
                    try:
                        from app.schema import ToolResult as SchemaToolResult
                        result = SchemaToolResult.from_dict(result)
                    except Exception as e:
                        self.logger.error(f"Failed to convert dict to ToolResult: {e}")
                        result = ToolResult(
                            tool=self.name,
                            action=self.name,
                            status="SUCCESS",
                            result={"result": str(result)} if result else {"result": "No result"}
                        )
                else:
                    # Create a ToolResult from the raw result
                    result = ToolResult(
                        tool=self.name,
                        action=self.name,
                        status="SUCCESS",
                        result={"result": str(result)} if result else {"result": "No result"}
                    )
                
            # Log success
            self.logger.end_execution(True, f"Completed in {execution_time:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            self.logger.error(f"Tool execution timed out after {self.timeout}s")
            self.logger.end_execution(False, f"Timed out after {self.timeout}s")
            
            from app.schema import ToolResult as SchemaToolResult
            return SchemaToolResult(
                tool=self.name,
                action=self.name,
                status="ERROR",
                result={"error": f"Tool '{self.name}' execution timed out after {self.timeout} seconds"}
            )
            
        except InvalidToolArgumentException as e:
            self.logger.error(f"Invalid tool argument: {str(e)}")
            self.logger.end_execution(False, f"Invalid argument: {e.argument_name}")
            
            from app.schema import ToolResult as SchemaToolResult
            return SchemaToolResult(
                tool=self.name,
                action=self.name,
                status="ERROR",
                result={"error": f"Invalid argument: {str(e)}", "detail": "Please check the argument values and try again."}
            )
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
            self.logger.end_execution(False, f"Error: {str(e)}")
            
            from app.schema import ToolResult as SchemaToolResult
            return SchemaToolResult(
                tool=self.name,
                action=self.name,
                status="ERROR",
                result={"error": f"Tool '{self.name}' execution failed: {str(e)}", "suggestion": "Please try again or use a different approach."}
            )
    
    @abstractmethod
    async def _execute(self, **kwargs) -> ToolResult:
        """Tool-specific implementation.
        
        This method must be implemented by all tool subclasses.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            ToolResult containing the result of the execution
        """
        pass
    
    def validate_arguments(self, **kwargs) -> Dict[str, Any]:
        """Validate the arguments against the parameter schema.
        
        Args:
            **kwargs: Arguments to validate
            
        Returns:
            Validated arguments
            
        Raises:
            InvalidToolArgumentException: If the arguments are invalid
        """
        if not self._param_schema:
            return kwargs
            
        try:
            validated = self._param_schema(**kwargs)
            return validated.dict()
        except Exception as e:
            raise InvalidToolArgumentException(
                tool_name=self.name,
                argument_name=str(e).split("'")[1] if "'" in str(e) else "unknown",
                value="invalid",
                reason=str(e)
            )
    
    async def reset(self) -> ToolResult:
        """Reset the tool state.
        
        This method should be overridden by stateful tools to reset their state.
        
        Returns:
            ToolResult indicating success or failure
        """
        if not self.is_stateful:
            return ToolResult(
                success=True,
                message=f"Tool '{self.name}' reset (no state to reset)",
                content=f"Tool '{self.name}' has no state to reset."
            )
            
        return ToolResult(
            success=True,
            message=f"Tool '{self.name}' reset",
            content=f"Tool '{self.name}' has been reset to its initial state."
        )
    
    @classmethod
    def get_tools_from_module(cls, module) -> Dict[str, 'Tool']:
        """Find all Tool subclasses in a module.
        
        Args:
            module: The module to search
            
        Returns:
            Dict of tool names to tool instances
        """
        tools = {}
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type) 
                and issubclass(attr, cls) 
                and attr is not cls 
                and attr.__module__ == module.__name__
            ):
                try:
                    tool = attr()
                    tools[tool.name] = tool
                except Exception as e:
                    logger.error(f"Failed to instantiate tool {attr_name}: {e}")
        return tools 

    async def run(self, **kwargs) -> ToolResult:
        """Execute the tool with the provided arguments (alias for execute).
        
        This method exists to ensure compatibility with all tool calling interfaces
        including OpenAI's and other LLM providers.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            ToolResult containing the result of the execution
        """
        return await self.execute(**kwargs) 