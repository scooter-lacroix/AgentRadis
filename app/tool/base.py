from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List

from pydantic import BaseModel, Field


class BaseTool(ABC):
    """Base class for all tools."""

    name: str = ""
    description: str = ""
    examples: List[str] = []
    timeout: float = 30.0
    is_stateful: bool = False
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, **kwargs):
        """Initialize the tool, optionally with kwargs for initialization options."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @abstractmethod
    async def execute(self, **kwargs):
        """Execute the tool with the given parameters."""
        raise NotImplementedError("Tool must implement execute method")

    async def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with the given arguments."""
        raise NotImplementedError("Tool must implement run method")

    async def cleanup(self):
        """Clean up any resources used by the tool."""
        pass

    async def reset(self):
        """Reset the tool's state if it's stateful."""
        pass

    async def __call__(self, **kwargs):
        """Make the tool callable."""
        return await self.execute(**kwargs)

    def to_param(self) -> Dict:
        """Convert tool to OpenAI function call format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters.get("properties", {}),
                    "required": self.parameters.get("required", [])
                }
            }
        }


class ToolResult(BaseModel):
    """Represents the result of a tool execution."""

    output: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    def __bool__(self):
        return any(getattr(self, field) for field in self.__fields__)

    def __add__(self, other: "ToolResult"):
        def combine_fields(
            field: Optional[str], other_field: Optional[str], concatenate: bool = True
        ):
            if field and other_field:
                if concatenate:
                    return field + other_field
                raise ValueError("Cannot combine tool results")
            return field or other_field

        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            system=combine_fields(self.system, other.system),
        )

    def __str__(self):
        return f"Error: {self.error}" if self.error else self.output

    def replace(self, **kwargs):
        """Returns a new ToolResult with the given fields replaced."""
        # return self.copy(update=kwargs)
        return type(self)(**{**self.dict(), **kwargs})


class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""


class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""


class AgentAwareTool:
    agent: Optional[Any] = None
