"""Core type definitions for the Radis system."""

from enum import Enum
from typing import List

class Role(str, Enum):
    """Enumeration of possible roles in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"  # For function calling capability

class AgentState(str, Enum):
    """States an agent can be in."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"

class Status(str, Enum):
    """Status enum for operations."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PENDING = "pending"
    PAUSED = "paused"

class ToolChoice(str, Enum):
    """Enum representing the tool choice options."""
    AUTO = "auto"
    NONE = "none"
    REQUIRED = "required"

class Plan(str, Enum):
    """Plan status enum for task management."""
    DRAFT = "draft"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Result(str, Enum):
    """Result status enum for validation results."""
    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"

class LLMType(str, Enum):
    """Enum for LLM service types."""
    OPENAI = "openai"
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LMSTUDIO = "lm_studio"
    CUSTOM = "custom"
    GPT4_TURBO = "gpt-4-turbo"
    GPT35_TURBO = "gpt-3.5-turbo"
    GEMMA34B = "gemma-3.4b"
    MISTRAL_MEDIUM = "mistral-medium"
    MISTRAL_SMALL = "mistral-small"
    CLAUDE3_OPUS = "claude-3-opus"
    CLAUDE3_SONNET = "claude-3-sonnet"

# Define base class for role types to support issubclass checks
class ROLE_TYPE:
    """Base class for role types to support issubclass checks."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"

    @classmethod
    def values(cls) -> List[str]:
        """Get all valid role values."""
        return [v for v in vars(cls).values() if isinstance(v, str)]

# Define ROLE_VALUES
ROLE_VALUES: List[str] = ROLE_TYPE.values()

# Define base class for tool choice types
class TOOL_CHOICE_TYPE:
    """Base class for tool choice types to support issubclass checks."""
    AUTO = "auto"
    NONE = "none"
    REQUIRED = "required"
    FUNCTION = "function"  # For backward compatibility

    @classmethod
    def values(cls) -> List[str]:
        """Get all valid tool choice values."""
        return [v for v in vars(cls).values() if isinstance(v, str)]

# Define TOOL_CHOICE_VALUES
TOOL_CHOICE_VALUES: List[str] = TOOL_CHOICE_TYPE.values()

# AgentResult with necessary fields
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ProcessingMetrics(BaseModel):
    """Metrics for tracking computation performance and resource usage."""
    processing_time: float = Field(
        ..., description="Time taken for computation in seconds", ge=0
    )
    peak_memory_usage: int = Field(
        ..., description="Maximum memory used during processing in bytes", ge=0
    )
    device_used: str = Field(
        ...,
        description="Computing device used for processing (e.g. 'cpu', 'rocm', 'cuda')",
    )

class AgentResult(BaseModel):
    """Result of an agent operation."""
    status: Status = Field(..., description="Status of the operation")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Result data")
    error: Optional[str] = Field(
        default=None, description="Error message if status is ERROR"
    )
    metrics: Optional[ProcessingMetrics] = Field(
        default=None, description="Processing metrics"
    )

    @property
    def is_success(self) -> bool:
        """Check if the operation was successful."""
        return self.status == Status.COMPLETED

    @property
    def is_error(self) -> bool:
        """Check if the operation resulted in an error."""
        return self.status == Status.FAILED
