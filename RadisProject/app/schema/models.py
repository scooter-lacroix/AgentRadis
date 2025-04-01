# Added Memory class as a stub to resolve import issues in tests
class Memory:
    def __init__(self, data=None):
        self.data = data

    def __repr__(self):
        return f"<Memory data={self.data}>"

# End of Memory class addition

"""
Schema models for the Radis system.

This module defines the common data models used throughout the application.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any, Union
from uuid import uuid4

from app.schema.types import Role, Result


class Function(BaseModel):
    """Function definition for a tool call."""
    name: str = Field(..., description="Name of the function")
    arguments: Union[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Arguments for the function"
    )


class ToolCall(BaseModel):
    """Tool call request - compatible with OpenAI API format."""
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this tool call",
    )
    type: str = Field(default="function", description="Type of tool call")
    function: Dict[str, Any] = Field(..., description="Function to call")


class Message(BaseModel):
    """A message in a conversation."""
    role: str = Field(..., description="Role of the message sender")
    content: Optional[str] = Field(default=None, description="Content of the message")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Tool calls requested by the assistant"
    )
    tool_call_id: Optional[str] = Field(
        default=None, description="ID of the tool call this message is responding to"
    )
    name: Optional[str] = Field(
        default=None, description="Name of the assistant or tool"
    )


class ToolResponse(BaseModel):
    """Response from a tool call."""
    call_id: str = Field(..., description="ID of the tool call this is responding to")
    tool_name: str = Field(..., description="Name of the tool that was called")
    success: bool = Field(..., description="Whether the tool call succeeded")
    result: Union[str, Dict[str, Any]] = Field(..., description="Result of the tool call")
    error: Optional[str] = Field(default=None, description="Error message if the tool call failed")


class RadisConfig(BaseModel):
    """Configuration for the Radis system."""
    name: str = Field(default="radis", description="Name of this Radis instance")
    version: str = Field(default="1.0.0", description="Version of Radis")
    api_base: Optional[str] = Field(default=None, description="API base URL")
    model_name: Optional[str] = Field(default=None, description="Name of the model to use")


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    name: str = Field(..., description="Name of the agent")
    role: str = Field(..., description="Role of the agent")
    model: Optional[str] = Field(default=None, description="Model override for this agent")
    tools: Optional[List[str]] = Field(default=None, description="Tool overrides for this agent")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RadisResponse(BaseModel):
    """Response from Radis."""
    result: Result = Field(..., description="Result of the operation")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional data")


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass
