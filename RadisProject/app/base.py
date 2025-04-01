"""
Base module providing core tool functionality and abstract base classes.

This module defines the foundation for all tools in the system, including:
- Abstract base classes that define the tool interface
- Common utility methods
- Logging and error handling capabilities
"""

import abc
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class ToolStatus(Enum):
    """Enum representing the current status of a tool."""

    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class ToolResult:
    """Represents the result of a tool operation."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None


class BaseTool(abc.ABC):
    """
    Abstract base class for all tools in the system.

    Provides common functionality and defines the interface that all tools must implement.
    """

    def __init__(self, name: str, description: str):
        """
        Initialize a new tool instance.

        Args:
            name: The name of the tool
            description: A brief description of what the tool does
        """
        self.name = name
        self.description = description
        self.status = ToolStatus.IDLE
        self.logger = logging.getLogger(f"tool.{name}")

        # Configure tool-specific logging
        self._setup_logging()

    @abc.abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool's main functionality.

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            ToolResult containing success status and any relevant data
        """
        raise NotImplementedError

    @abc.abstractmethod
    def validate_input(self, **kwargs) -> bool:
        """
        Validate input parameters before execution.

        Args:
            **kwargs: Tool-specific arguments to validate

        Returns:
            True if inputs are valid, False otherwise
        """
        raise NotImplementedError

    @property
    def is_running(self) -> bool:
        """Check if the tool is currently running."""
        return self.status == ToolStatus.RUNNING

    def _setup_logging(self):
        """Configure logging for this tool instance."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            f"%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _update_status(self, new_status: ToolStatus):
        """
        Update the tool's status and log the change.

        Args:
            new_status: The new status to set
        """
        old_status = self.status
        self.status = new_status
        self.logger.info(
            f"Status changed from {old_status.value} to {new_status.value}"
        )

    async def run(self, **kwargs) -> ToolResult:
        """
        Main entry point for running the tool.

        Handles:
        - Input validation
        - Status management
        - Error handling
        - Logging

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            ToolResult containing execution results
        """
        self.logger.info(f"Starting {self.name} tool")

        try:
            # Validate inputs
            if not self.validate_input(**kwargs):
                raise ValueError("Invalid input parameters")

            # Update status and execute
            self._update_status(ToolStatus.RUNNING)
            result = await self.execute(**kwargs)

            # Handle success
            self._update_status(ToolStatus.SUCCESS)
            return result

        except Exception as e:
            # Handle failure
            self.logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
            self._update_status(ToolStatus.ERROR)
            return ToolResult(
                success=False, message=f"Tool execution failed: {str(e)}", error=e
            )

    def cleanup(self):
        """
        Clean up any resources used by the tool.

        Override this method if your tool needs special cleanup.
        """
        self.logger.info(f"Cleaning up {self.name} tool")

    def __str__(self) -> str:
        """String representation of the tool."""
        return f"{self.name} ({self.status.value})"

    def __repr__(self) -> str:
        """Detailed string representation of the tool."""
        return f"<{self.__class__.__name__} name='{self.name}' status='{self.status.value}'>"


from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Generic
from dataclasses import dataclass
import logging
from enum import Enum


class ToolError(Exception):
    """Base exception for tool-related errors."""

    pass


class ToolExecutionError(ToolError):
    """Exception raised when a tool execution fails."""

    pass


class ToolCleanupError(ToolError):
    """Exception raised when tool cleanup fails."""

    pass


class AgentError(Exception):
    """Base exception for agent-related errors."""

    pass


class AgentExecutionError(AgentError):
    """Exception raised when agent execution fails."""

    pass


@dataclass
class ToolResponse:
    """Container for tool execution results."""

    success: bool
    result: Any
    error: Optional[Exception] = None


# Generic type variables for input and output types
I = TypeVar("I")  # Input type
O = TypeVar("O")  # Output type


class BaseTool(Generic[I, O], ABC):
    """
    Abstract base class for all tools.

    Generic Parameters:
        I: Type of the input parameters
        O: Type of the output/result
    """

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"tool.{name}")

    @abstractmethod
    async def run(self, input_data: I) -> O:
        """
        Execute the tool's main functionality.

        Args:
            input_data: Input parameters for the tool execution

        Returns:
            The result of the tool execution

        Raises:
            ToolExecutionError: If tool execution fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Perform cleanup operations after tool execution.

        Raises:
            ToolCleanupError: If cleanup operations fail
        """
        raise NotImplementedError()

    async def should_run(self, input_data: I) -> bool:
        """
        Determine if the tool should run given the input.

        Args:
            input_data: Input parameters to evaluate

        Returns:
            True if the tool should run, False otherwise
        """
        return True

    async def execute(self, input_data: I) -> ToolResponse:
        """
        Safe execution wrapper for the tool's run method.

        Args:
            input_data: Input parameters for the tool execution

        Returns:
            ToolResponse containing execution results and status
        """
        try:
            if not await self.should_run(input_data):
                return ToolResponse(
                    success=False,
                    result=None,
                    error=ToolExecutionError("Tool execution skipped"),
                )

            result = await self.run(input_data)
            return ToolResponse(success=True, result=result)

        except Exception as e:
            self.logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
            return ToolResponse(success=False, result=None, error=e)


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")

    @abstractmethod
    async def run(self, context: Dict[str, Any]) -> Any:
        """
        Execute the agent's main functionality.

        Args:
            context: Execution context containing necessary information

        Returns:
            The result of the agent execution

        Raises:
            AgentExecutionError: If agent execution fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Perform cleanup operations for the agent.

        This method should be called when the agent is no longer needed
        to free up resources and perform necessary cleanup operations.

        Raises:
            AgentError: If cleanup operations fail
        """
        raise NotImplementedError()

    async def execute(self, context: Dict[str, Any]) -> Any:
        """
        Safe execution wrapper for the agent's run method.

        Args:
            context: Execution context containing necessary information

        Returns:
            The result of the agent execution

        Raises:
            AgentExecutionError: If execution fails
        """
        try:
            return await self.run(context)
        except Exception as e:
            self.logger.error(f"Agent execution failed: {str(e)}", exc_info=True)
            raise AgentExecutionError(f"Agent execution failed: {str(e)}") from e
