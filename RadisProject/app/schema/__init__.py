from .models import (
    Function, ToolCall, ToolResponse, Message, Memory,
    RadisConfig, RadisResponse, AgentConfig
)

"""

The top-level imports are maintained for backward compatibility but will emit
deprecation warnings directing users to the new import paths.
"""

import functools
import warnings
from enum import Enum
from typing import Any, Type, TypeVar, cast, Callable

# Import from new locations using relative imports
from .types import (
    Role, AgentState, ToolChoice, Status,
    ROLE_VALUES, ROLE_TYPE, TOOL_CHOICE_VALUES, TOOL_CHOICE_TYPE,
    AgentResult, Plan, Result
)
from .models import (
    Function, ToolCall, ToolResponse, Message,
    RadisConfig, RadisResponse, AgentConfig
)
from .enums import LLMType
from .errors import ConfigValidationError
from .memory import AgentMemory

# Ensure deprecation warnings are always shown
warnings.filterwarnings("always", category=DeprecationWarning, module=__name__)

T = TypeVar("T")
class EnumDeprecatedImportWrapper:
    """Special wrapper for Enum types that preserves enum functionality while adding deprecation warnings."""
    
    def __init__(self, enum_class: Type[Enum], name: str, module: str):
        self._enum_class = enum_class
        self._name = name
        self._module = module
        
    def _warn(self):
        warnings.warn(
            f"Importing {self._name} from app.schema is deprecated. "
            f"Please import from app.schema.{self._module} instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
    def __getattr__(self, name: str) -> Any:
        self._warn()
        return getattr(self._enum_class, name)
        
    def __call__(self, *args, **kwargs):
        self._warn()
        return self._enum_class(*args, **kwargs)
        
    def __iter__(self):
        self._warn()
        return iter(self._enum_class)
    
    def __getitem__(self, name: str) -> Any:
        self._warn()
        return self._enum_class[name]

class FunctionDeprecatedImportWrapper:
    """Wrapper for function types that need deprecation warnings."""
    
    def __init__(self, func: Callable, name: str, module: str):
        self._func = func
        self._name = name
        self._module = module
        
    def _warn(self):
        warnings.warn(
            f"Importing {self._name} from app.schema is deprecated. "
            f"Please import from app.schema.{self._module} instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
    def __call__(self, *args, **kwargs):
        self._warn()
        return self._func(*args, **kwargs)

class DeprecatedImportWrapper:
    """Wrapper class that emits deprecation warnings when accessing wrapped objects."""

    def __init__(self, wrapped: Any, name: str, module: str):
        self._wrapped = wrapped
        self._name = name
        self._module = module
class DeprecatedImportWrapper:
    """Wrapper class that emits deprecation warnings when accessing wrapped objects."""

    def __init__(self, wrapped: Any, name: str, module: str):
        self._wrapped = wrapped
        self._name = name
        self._module = module

    def _warn(self):
        warnings.warn(
            f"Importing {self._name} from app.schema is deprecated. "
            f"Please import from app.schema.{self._module} instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def __class_getitem__(cls, item: Any) -> Any:
        # Support for generic type hints like ToolChoice[str]
        # Look for a wrapped type in class attributes
        for value in vars(cls).values():
            if isinstance(value, DeprecatedImportWrapper):
                if isinstance(value._wrapped, type):
                    try:
                        # Try standard type subscription
                        return value._wrapped[item]
                    except (AttributeError, TypeError):
                        # If that fails, return the type itself
                        return value._wrapped
        # Fallback for when we can't find the wrapped type
        return Any

    def __instancecheck__(self, instance: Any) -> bool:
        # Support for isinstance() checks
        return isinstance(instance, self._wrapped)

    def __subclasscheck__(self, subclass: Any) -> bool:
        # Support for issubclass() checks
        return issubclass(subclass, self._wrapped)

    def __getitem__(self, key: Any) -> Any:
        # Support for subscripting operations
        self._warn()
        try:
            if isinstance(self._wrapped, type):
                # If wrapped is a type, try to use its type subscription
                return self._wrapped[key]
            # For instances, use normal indexing
            return self._wrapped[key]
        except (TypeError, AttributeError):
            # If type subscription fails, return the wrapped type itself
            if isinstance(self._wrapped, type):
                return self._wrapped
            raise

    def __call__(self, *args, **kwargs):
        self._warn()
        return self._wrapped(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        self._warn()
        return getattr(self._wrapped, name)

    @property
    def __class__(self) -> Type[T]:
        self._warn()
        return cast(Type[T], self._wrapped)

    def __str__(self) -> str:
        self._warn()
        return str(self._wrapped)

    def __repr__(self) -> str:
        self._warn()
        return repr(self._wrapped)


# Handle Enum types with special wrapper
Role = EnumDeprecatedImportWrapper(Role, "Role", "types")
AgentState = EnumDeprecatedImportWrapper(AgentState, "AgentState", "types")
ToolChoice = EnumDeprecatedImportWrapper(ToolChoice, "ToolChoice", "types")
Status = EnumDeprecatedImportWrapper(Status, "Status", "types")
LLMType = EnumDeprecatedImportWrapper(LLMType, "LLMType", "enums")

# Handle special function cases
ROLE_VALUES = FunctionDeprecatedImportWrapper(ROLE_VALUES, "ROLE_VALUES", "types")
ROLE_TYPE = FunctionDeprecatedImportWrapper(ROLE_TYPE, "ROLE_TYPE", "types")
TOOL_CHOICE_VALUES = FunctionDeprecatedImportWrapper(TOOL_CHOICE_VALUES, "TOOL_CHOICE_VALUES", "types")
TOOL_CHOICE_TYPE = FunctionDeprecatedImportWrapper(TOOL_CHOICE_TYPE, "TOOL_CHOICE_TYPE", "types")

# Regular class types
AgentResult = DeprecatedImportWrapper(AgentResult, "AgentResult", "types")
Plan = DeprecatedImportWrapper(Plan, "Plan", "types")
Result = DeprecatedImportWrapper(Result, "Result", "types")

# Models
Function = DeprecatedImportWrapper(Function, "Function", "models")
ToolCall = DeprecatedImportWrapper(ToolCall, "ToolCall", "models")
ToolResponse = DeprecatedImportWrapper(ToolResponse, "ToolResponse", "models")
Message = DeprecatedImportWrapper(Message, "Message", "models")
RadisConfig = DeprecatedImportWrapper(RadisConfig, "RadisConfig", "models")
RadisResponse = DeprecatedImportWrapper(RadisResponse, "RadisResponse", "models")
AgentConfig = DeprecatedImportWrapper(AgentConfig, "AgentConfig", "models")
ConfigValidationError = DeprecatedImportWrapper(ConfigValidationError, "ConfigValidationError", "errors")
AgentMemory = DeprecatedImportWrapper(AgentMemory, "AgentMemory", "memory")

__all__ = [
    # Core types
    "Plan",
    "Result",
    "Role",
    "AgentState",
    "Status",
    "ToolChoice",
    "LLMType",
    "ROLE_VALUES",
    "ROLE_TYPE",
    "TOOL_CHOICE_VALUES",
    "TOOL_CHOICE_TYPE",
    "AgentMemory",
    "AgentResult",
    # Message and tool models
    "Function",
    "ToolCall",
    "ToolResponse",
    "Message",
    "RadisConfig",
    "RadisResponse",
    "AgentConfig",
    "ConfigValidationError",
]
