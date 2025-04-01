import abc
import asyncio
from typing import Any, Dict, List, Optional, Union

from ..schema.types import AgentState, ToolChoice
from ..schema.models import Message, ToolCall
from ..logger import get_logger

logger = get_logger(__name__)
from app.schema.memory import AgentMemory
from app.schema.models import ToolResponse
from app.schema.types import Status, ROLE_TYPE, AgentResult


class BaseAgent(abc.ABC):
    """Abstract base class for all agents in the system.

    All agents must inherit from this class and implement the required methods.

    Attributes:
        name (str): The name of the agent, used for identification
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """The name of the agent."""
        pass

    def __init__(self, model: str = "gpt-3.5-turbo", temperature: float = 0.7):
        """Initialize the base agent.

        Args:
            model: The LLM model to use
            temperature: The temperature parameter for LLM responses
        """
        self.model = model
        self.temperature = temperature
        self.state = AgentState.IDLE
        self._is_configured = False
        self._tool_choice = ToolChoice.AUTO

    @property
    def is_configured(self) -> bool:
        """Check if the agent is properly configured."""
        return self._is_configured

    @property
    def tool_choice(self) -> ToolChoice:
        """Get the current tool choice setting."""
        return self._tool_choice

    @tool_choice.setter
    def tool_choice(self, value: Union[str, ToolChoice]) -> None:
        """Set the tool choice setting.

        Args:
            value: The tool choice value to set
        """
        if isinstance(value, str):
            value = ToolChoice[value.upper()]
        self._tool_choice = value

    @abc.abstractmethod
    async def async_setup(self) -> None:
        """Set up the agent asynchronously.

        This method should be called before using the agent.
        """
        pass

    @abc.abstractmethod
    async def run(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """Run the agent with the given input.

        Args:
            input_text: The input text to process
            **kwargs: Additional arguments

        Returns:
            Dict containing the results
        """
        pass

    @abc.abstractmethod
    async def step(self) -> bool:
        """Execute a single step in the agent's processing.

        Returns:
            True if more steps are needed, False if processing is complete
        """
        pass

    @abc.abstractmethod
    async def reset(self) -> None:
        """Reset the agent to its initial state."""
        pass

    @abc.abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources used by the agent."""
        pass

    def validate_state(self, expected_state: AgentState) -> None:
        """Validate that the agent is in the expected state.

        Args:
            expected_state: The state that the agent should be in

        Raises:
            ValueError: If the agent is not in the expected state
        """
        if self.state != expected_state:
            raise ValueError(
                f"Agent must be in {expected_state} state, but is in {self.state}"
            )

    def validate_name(self) -> None:
        """Validate that the agent has a non-empty name.

        Checks if the name property is set and contains a non-empty string.

        Raises:
            ValueError: If the agent's name is empty or not set
        """
        if not self.name or not self.name.strip():
            raise ValueError("Agent must have a non-empty name")

    async def format_messages(
        self, messages: List[Message], tool_choice: Optional[ToolChoice] = None
    ) -> List[Dict[str, Any]]:
        """Format messages for LLM consumption.

        Args:
            messages: List of messages to format
            tool_choice: Optional tool choice override

        Returns:
            Formatted messages in LLM-compatible format
        """
        formatted = []
        for msg in messages:
            msg_dict = {"role": msg.role.value.lower(), "content": msg.content}
            if msg.name:
                msg_dict["name"] = msg.name
            if msg.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            formatted.append(msg_dict)
        return formatted

    async def prepare_llm_request(
        self,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Prepare a request for the LLM.

        Args:
            messages: The messages to send
            functions: Optional function descriptions
            **kwargs: Additional LLM parameters

        Returns:
            Dict containing the LLM request parameters
        """
        request = {
            "model": self.model,
            "messages": await self.format_messages(messages),
            "temperature": self.temperature,
        }

        tool_choice = kwargs.pop("tool_choice", self.tool_choice)
        if functions:
            request["functions"] = functions
            request["tool_choice"] = tool_choice.value.lower()

        request.update(kwargs)
        return request
