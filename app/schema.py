"""
Schema definitions for AgentRadis.

This module contains Pydantic models that define the structure
of data used throughout the application.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import json

from pydantic import BaseModel, Field, model_validator, validator, field_validator
import uuid

# Basic types

class Status(str, Enum):
    """Status enum for operations"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PENDING = "pending"


class ToolResult(BaseModel):
    """Result of a tool execution"""
    tool: str = Field(..., description="Name of the tool")
    action: str = Field(..., description="Name of the action")
    status: str = Field(..., description="Status of the tool execution (SUCCESS/ERROR)")
    result: Dict[str, Any] = Field(..., description="Result data from the tool")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the tool was executed")
    
    # For backward compatibility
    @property
    def success(self) -> bool:
        return self.status == "SUCCESS"
        
    @property
    def message(self) -> str:
        if self.success:
            return f"Successfully executed {self.action} with {self.tool}"
        return f"Error executing {self.action} with {self.tool}"
        
    @property
    def content(self) -> str:
        return str(self.result)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolResult":
        """Create a ToolResult from a dictionary, handling various formats"""
        if "success" in data and "message" in data:
            # Handle legacy format with success/message
            status = "SUCCESS" if data.get("success", False) else "ERROR"
            tool = data.get("tool", "unknown")
            action = data.get("action", tool)
            content = data.get("content", "")
            
            # Create result dict
            result = {"result": content}
            if "error" in data:
                result["error"] = data["error"]
                
            return cls(
                tool=tool,
                action=action,
                status=status,
                result=result,
                timestamp=data.get("timestamp", datetime.now())
            )
        return cls(**data)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to legacy format for backward compatibility"""
        return {
            "tool": self.tool,
            "action": self.action,
            "success": self.success,
            "message": self.message,
            "content": self.content,
            "timestamp": self.timestamp
        }


class ToolCallType(str, Enum):
    """Types of tool calls"""
    FUNCTION = "function"
    ACTION = "action"
    CODE = "code"


class Function(BaseModel):
    """Function definition for a tool call"""
    name: str = Field(..., description="Name of the function")
    arguments: Union[str, Dict[str, Any]] = Field(default_factory=dict, description="Arguments for the function")


class ToolCall(BaseModel):
    """Tool call request - compatible with OpenAI API format"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for this tool call")
    type: ToolCallType = Field(default=ToolCallType.FUNCTION, description="Type of tool call")
    function: Function = Field(..., description="Function to call")
    
    # For backward compatibility
    @property
    def name(self) -> str:
        """Get the function name for backward compatibility"""
        return self.function.name if self.function else ""
        
    @property
    def arguments(self) -> Union[str, Dict[str, Any]]:
        """Get the arguments for backward compatibility"""
        return self.function.arguments if self.function else {}


class ToolResponse(BaseModel):
    """Response from a tool call"""
    call_id: str = Field(..., description="ID of the original tool call")
    tool_name: str = Field(..., description="Name of the tool")
    success: bool = Field(..., description="Whether the tool execution was successful")
    result: Union[str, Dict[str, Any]] = Field(..., description="Result from the tool")
    error: Optional[str] = Field(None, description="Error message if the tool failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the tool was executed")


# Message types

class Role(str, Enum):
    """Roles in a conversation"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MessageContent(BaseModel):
    """Content of a message"""
    type: str = Field(default="text", description="Type of content")
    text: Optional[str] = Field(None, description="Text content")
    tool_calls: Optional[List[ToolCall]] = Field(None, description="Tool calls if applicable")
    tool_responses: Optional[List[ToolResponse]] = Field(None, description="Tool responses if applicable")
    
    @model_validator(mode='before')
    def validate_content(cls, values):
        content_type = values.get("type")
        if content_type == "text" and not values.get("text"):
            raise ValueError("Text content is required for text type")
        elif content_type == "tool_calls" and not values.get("tool_calls"):
            raise ValueError("Tool calls are required for tool_calls type")
        elif content_type == "tool_response" and not values.get("tool_responses"):
            raise ValueError("Tool response is required for tool_response type")
        return values


class Message(BaseModel):
    """A message in a conversation"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for this message")
    role: Role = Field(..., description="Role of the message sender")
    content: Union[str, List[MessageContent]] = Field(default="", description="Content of the message")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the message was created")
    tool_calls: Optional[List[ToolCall]] = Field(None, description="Tool calls in this message")
    tool_call_id: Optional[str] = Field(None, description="Tool call ID for tool responses")
    name: Optional[str] = Field(None, description="Name of the tool for tool responses")
    
    @field_validator("content", mode="before")
    def validate_content(cls, v):
        """Ensure content is a string or None"""
        if v is None:
            return None
        return str(v)
    
    @field_validator("tool_calls", mode="before")
    def validate_tool_calls(cls, v):
        """Ensure tool_calls is a list or None"""
        if v is None:
            return None
        if not isinstance(v, list):
            return [v]
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to a dict format compatible with LLM APIs"""
        result = {"role": self.role.value if isinstance(self.role, Role) else self.role}
        
        # Handle content
        if self.content or self.content == "":
            result["content"] = self.content
        
        # Handle tool response
        if self.role == Role.TOOL and self.tool_call_id and self.name:
            result["tool_call_id"] = self.tool_call_id
            result["name"] = self.name
            
        # Handle tool calls - converting to OpenAI compatible format
        if self.tool_calls:
            # Format tool calls for OpenAI API
            api_tool_calls = []
            for tc in self.tool_calls:
                api_tool_call = {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments if isinstance(tc.function.arguments, str) 
                                     else json.dumps(tc.function.arguments)
                    }
                }
                api_tool_calls.append(api_tool_call)
            result["tool_calls"] = api_tool_calls
            
        return result
    
    @classmethod
    def system_message(cls, content: str) -> "Message":
        """Create a system message"""
        return cls(role=Role.SYSTEM, content=content)
    
    @classmethod
    def user_message(cls, content: str) -> "Message":
        """Create a user message"""
        return cls(role=Role.USER, content=content)
    
    @classmethod
    def assistant_message(cls, content: str, tool_calls: Optional[List[ToolCall]] = None) -> "Message":
        """Create an assistant message"""
        return cls(role=Role.ASSISTANT, content=content, tool_calls=tool_calls)
    
    @classmethod
    def tool_message(cls, content: str, tool_call_id: str, name: str) -> "Message":
        """Create a tool message"""
        return cls(role=Role.TOOL, content=content, tool_call_id=tool_call_id, name=name)
    
    @classmethod
    def from_tool_calls(cls, content: str, tool_calls: List[ToolCall]) -> "Message":
        """Create a message from tool calls"""
        return cls(role=Role.ASSISTANT, content=content, tool_calls=tool_calls)


# Agent types

class AgentState(str, Enum):
    """States an agent can be in"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"


class AgentMemory(BaseModel):
    """Memory of an agent"""
    messages: List[Message] = Field(default_factory=list, description="Conversation history")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context variables")
    session_id: Optional[str] = Field(None, description="Current session ID")
    actions: List[Any] = Field(default_factory=list, description="Actions taken by the agent")
    observations: List[Any] = Field(default_factory=list, description="Observations from tools")
    max_messages: int = 100
    
    def add_message(self, role: Role, content: Union[str, List[MessageContent]]) -> Message:
        """Add a message to the memory"""
        message = Message(role=role, content=content)
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        return message
    
    def add_action(self, action: Any) -> None:
        """Add an action to memory"""
        self.actions.append(action)
    
    def add_observation(self, observation: Any) -> None:
        """Add an observation to memory"""
        self.observations.append(observation)
    
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """Get recent messages from memory"""
        if limit is not None:
            return self.messages[-limit:]
        return self.messages
    
    def clear(self) -> None:
        """Clear memory"""
        self.messages = []
        self.actions = []
        self.observations = []
        self.context = {}

    def get_context(self, max_tokens: Optional[int] = None) -> str:
        """Get conversation context as a string"""
        context = []
        for msg in self.messages:
            if msg.content:
                context.append(f"{msg.role}: {msg.content}")
        return "\n".join(context)


class AgentResult(BaseModel):
    """Result of an agent execution"""
    response: str = Field(..., description="Text response from the agent")
    success: bool = Field(..., description="Whether the execution was successful")
    status: Status = Field(..., description="Status of the execution")
    memory: Optional[AgentMemory] = Field(None, description="Agent's memory after execution")
    iterations: int = Field(0, description="Number of iterations/steps taken")
    error: Optional[str] = Field(None, description="Error message if not successful")


class AgentAction(BaseModel):
    """Action taken by an agent"""
    tool: str = Field(..., description="Name of the tool")
    action: str = Field(..., description="Name of the action")
    action_input: Dict[str, Any] = Field(..., description="Input for the action")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the action was taken")
    
    # For backward compatibility
    @property
    def type(self) -> str:
        return self.tool
        
    @property
    def description(self) -> str:
        return f"{self.action} with {self.tool}"
        
    @property
    def data(self) -> Dict[str, Any]:
        return self.action_input


class AgentSession(BaseModel):
    """Session information for an agent"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique session ID")
    agent_id: str = Field(..., description="ID of the agent")
    start_time: datetime = Field(default_factory=datetime.now, description="When the session started")
    end_time: Optional[datetime] = Field(None, description="When the session ended")
    status: Status = Field(default=Status.RUNNING, description="Current status of the session")
    actions: List[AgentAction] = Field(default_factory=list, description="Actions taken during the session")
    

# API types

class APIRequest(BaseModel):
    """Base model for API requests"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Request timestamp")


class APIResponse(BaseModel):
    """Base model for API responses"""
    request_id: str = Field(..., description="ID of the original request")
    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error details if success is False")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class RunAgentRequest(APIRequest):
    """Request to run an agent"""
    agent_id: str = Field(..., description="ID of the agent to run")
    input: str = Field(..., description="Input for the agent")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class RunAgentResponse(APIResponse):
    """Response from running an agent"""
    agent_id: str = Field(..., description="ID of the agent that was run")
    session_id: str = Field(..., description="ID of the created session")
    output: Optional[str] = Field(None, description="Output from the agent")
    status: Status = Field(..., description="Status of the agent run")


class ToolRequest(APIRequest):
    """Request to execute a tool"""
    tool_name: str = Field(..., description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool")


class ToolResponse(APIResponse):
    """Response from executing a tool"""
    tool_name: str = Field(..., description="Name of the tool that was executed")
    result: Optional[Dict[str, Any]] = Field(None, description="Result of the tool execution")


class LLMRequest(APIRequest):
    """Request to the LLM API"""
    model: str = Field(..., description="Model to use")
    messages: List[Message] = Field(..., description="Messages to send to the LLM")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(None, description="Temperature for sampling")
    tools: Optional[List[Dict[str, Any]]] = Field(None, description="Available tools for the LLM")


class LLMResponse(APIResponse):
    """Response from the LLM API"""
    model: str = Field(..., description="Model that was used")
    message: Message = Field(..., description="Message from the LLM")
    tool_calls: Optional[List[ToolCall]] = Field(None, description="Tool calls from the LLM")
    usage: Dict[str, int] = Field(default_factory=dict, description="Token usage information")


# Tool choice enums and type
class ToolChoice(str, Enum):
    """Tool choice options for LLMs"""
    NONE = "none"
    AUTO = "auto"
    REQUIRED = "required"

TOOL_CHOICE_VALUES = [choice.value for choice in ToolChoice]
TOOL_CHOICE_TYPE = Union[str, Dict[str, str], ToolChoice]

# Role values
ROLE_VALUES = ["system", "user", "assistant", "tool"]
ROLE_TYPE = Union[str, Role]

class Memory(BaseModel):
    """Agent memory store"""
    messages: List[Message] = Field(default_factory=list)
    
    def add(self, role: ROLE_TYPE, content: str) -> Message:
        """Add a message to memory"""
        message = Message(role=role, content=content)
        self.messages.append(message)
        return message
    
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """Get messages from memory, optionally limited"""
        if limit is not None:
            return self.messages[-limit:]
        return self.messages
    
    def clear(self) -> None:
        """Clear all messages from memory"""
        self.messages = []

# Export all models
__all__ = [
    "Status", "ToolResult", "ToolCallType", "ToolCall", "ToolResponse",
    "Role", "MessageContent", "Message", 
    "AgentState", "AgentMemory", "AgentAction", "AgentSession",
    "APIRequest", "APIResponse", "RunAgentRequest", "RunAgentResponse",
    "ToolRequest", "ToolResponse", "LLMRequest", "LLMResponse",
    "ToolChoice", "TOOL_CHOICE_VALUES", "TOOL_CHOICE_TYPE",
    "ROLE_VALUES", "ROLE_TYPE", "Memory", "Function", "AgentResult"
]
