from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import time


class Role(Enum):
    """Enumeration of possible roles in the system.
    
    Attributes:
        SYSTEM: System-level messages and notifications
        USER: Messages from the user/client
        ASSISTANT: Messages from the AI assistant
        TOOL: Messages from tool executions
    """
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """Represents a chat message in the system.
    
    Attributes:
        role: The role of the message sender
        content: The actual message content
        timestamp: When the message was created
        metadata: Optional additional data about the message
    """
    role: Role
    content: str
    timestamp: datetime = datetime.now()
    metadata: Optional[Dict[str, Any]] = None


class ToolMetrics:
    """Tracks and manages metrics for tool usage and performance.
    
    Attributes:
        total_calls: Total number of times tools were called
        successful_calls: Number of successful tool executions
        failed_calls: Number of failed tool executions
        execution_times: Dictionary of tool execution times
    """
    
    def __init__(self):
        """Initialize metrics tracking."""
        self.total_calls: int = 0
        self.successful_calls: int = 0
        self.failed_calls: int = 0
        self.execution_times: Dict[str, float] = {}
        self._start_time: Optional[float] = None

    def start_execution(self, tool_name: str) -> None:
        """Start timing the execution of a tool.
        
        Args:
            tool_name: Name of the tool being executed
        """
        self._start_time = time.time()
        self.total_calls += 1

    def end_execution(self, tool_name: str, success: bool) -> None:
        """End timing of a tool execution and record metrics.
        
        Args:
            tool_name: Name of the tool that was executed
            success: Whether the execution was successful
        """
        if self._start_time is None:
            return

        execution_time = time.time() - self._start_time
        self.execution_times[tool_name] = execution_time
        
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1

    def get_success_rate(self) -> float:
        """Calculate the success rate of tool executions.
        
        Returns:
            Float representing the percentage of successful calls
        """
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100

    def get_average_execution_time(self, tool_name: str) -> float:
        """Get the average execution time for a specific tool.
        
        Args:
            tool_name: Name of the tool to get metrics for
            
        Returns:
            Average execution time in seconds
        """
        if tool_name not in self.execution_times:
            return 0.0
        return self.execution_times[tool_name]

    def reset(self) -> None:
        """Reset all metrics to their initial state."""
        self.__init__()

