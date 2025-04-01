"""Module for handling tool calls in the agent system."""

from typing import Any, Dict, List, Optional, Union
from copy import deepcopy

from .base import BaseAgent
from ..schema.types import AgentState
from ..schema.models import Message, ToolCall, ToolResponse
from ..tool import get_tool_registry
from ..logger import get_logger

logger = get_logger(__name__)


class ToolCallAgent(BaseAgent):
    """Agent specializing in handling and executing tool calls."""

    def __init__(self, model: str = "gpt-4-turbo-preview", temperature: float = 0.7):
        """Initialize the tool call agent.

        Args:
            model: The LLM model to use
            temperature: The temperature parameter for LLM responses
        """
        super().__init__(model=model, temperature=temperature)
        self.tool_registry = get_tool_registry()
        self.available_tools: Dict[str, Any] = {}
        self._messages: List[Message] = []
        self._current_tool_calls: List[ToolCall] = []

    async def async_setup(self) -> None:
        """Set up the agent and initialize available tools."""
        # Register all available tools
        tool_names = self.tool_registry.list_tools()
        self.available_tools = {
            name: self.tool_registry.get_tool(name) for name in tool_names
        }
        self._is_configured = True
        self.state = AgentState.READY

    async def run(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """Run the agent with the given input.

        Args:
            input_text: The input text to process
            **kwargs: Additional arguments

        Returns:
            Dict containing the results including any tool calls
        """
        if not self.is_configured:
            await self.async_setup()

        self.state = AgentState.PROCESSING
        self._messages = [Message.user_message(input_text)]

        continuing = True
        while continuing:
            continuing = await self.step()

        self.state = AgentState.READY
        return {
            "status": "success",
            "messages": deepcopy(self._messages),
            "tool_calls": [
                tc for msg in self._messages for tc in (msg.tool_calls or [])
            ],
        }

    async def step(self) -> bool:
        """Execute a single step in the agent's processing.

        Returns:
            True if more steps are needed, False if processing is complete
        """
        self.validate_state(AgentState.PROCESSING)

        # Get available tool schemas
        tool_schemas = [tool.get_schema() for tool in self.available_tools.values()]

        # Prepare and make LLM request
        request = await self.prepare_llm_request(self._messages, functions=tool_schemas)

        # TODO: Implement LLM call and response handling
        # For now, return False to indicate completion
        return False

    async def reset(self) -> None:
        """Reset the agent to its initial state."""
        self._messages.clear()
        self._current_tool_calls.clear()
        self.state = AgentState.READY

    async def cleanup(self) -> None:
        """Clean up resources used by the agent."""
        await self.reset()
        self.available_tools.clear()
        self.state = AgentState.IDLE
