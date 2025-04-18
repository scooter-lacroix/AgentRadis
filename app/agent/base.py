from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, model_validator

from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, AgentMemory, Message, ROLE_TYPE, ToolCall, ToolResponse, AgentResult, Status
from app.tool.base import BaseTool


class BaseAgent(BaseModel, ABC):
    """Abstract base class for managing agent state and execution.

    Provides foundational functionality for state transitions, memory management,
    and a step-based execution loop. Subclasses must implement the `step` method.
    """

    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    # Prompts
    system_prompt: Optional[str] = Field(
        None, description="System-level instruction prompt"
    )
    next_step_prompt: Optional[str] = Field(
        None, description="Prompt for determining next action"
    )

    # Dependencies
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    memory: AgentMemory = Field(default_factory=AgentMemory, description="Agent's memory store")
    state: AgentState = Field(
        default=AgentState.IDLE, description="Current agent state"
    )

    # Execution control
    max_steps: int = Field(default=10, description="Maximum steps before termination")
    current_step: int = Field(default=0, description="Current step in execution")

    duplicate_threshold: int = 2

    def __init__(self, **kwargs):
        """Initialize base agent"""
        super().__init__(**kwargs)
        self.tools: List[BaseTool] = []

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra fields for flexibility in subclasses

    @model_validator(mode="after")
    def initialize_agent(self) -> "BaseAgent":
        """Initialize agent with default settings if not provided."""
        if self.llm is None or not isinstance(self.llm, LLM):
            self.llm = LLM(config_name=self.name.lower())
        if not isinstance(self.memory, AgentMemory):
            self.memory = AgentMemory()
        return self

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """Context manager for safe agent state transitions.

        Args:
            new_state: The state to transition to during the context.

        Yields:
            None: Allows execution within the new state.

        Raises:
            ValueError: If the new_state is invalid.
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")

        previous_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR  # Transition to ERROR on failure
            raise e
        finally:
            self.state = previous_state  # Revert to previous state

    def update_memory(
        self,
        role: ROLE_TYPE, # type: ignore
        content: str,
        **kwargs,
    ) -> None:
        """Add a message to the agent's memory.

        Args:
            role: The role of the message sender (user, system, assistant, tool).
            content: The message content.
            **kwargs: Additional arguments (e.g., tool_call_id for tool messages).

        Raises:
            ValueError: If the role is unsupported.
        """
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }

        if role not in message_map:
            raise ValueError(f"Unsupported message role: {role}")

        msg_factory = message_map[role]
        msg = msg_factory(content, **kwargs) if role == "tool" else msg_factory(content)
        self.memory.messages.append(msg)

    async def run(self, prompt: str) -> AgentResult:
        """
        Run the agent with a prompt.
        
        Args:
            prompt: The input prompt to process
            
        Returns:
            AgentResult containing the response, memory state, iterations count, and status
        """
        self.current_step = 0
        self.memory.clear()  # Clear memory for a new run
        self.state = AgentState.RUNNING

        try:
            # Process the prompt with the LLM
            response = await self.llm.generate_response(prompt)
            self.memory.add_message(role="user", content=prompt)

            # Create a ToolCall and execute it if necessary
            tool_call = ToolCall(function=Function(name="example_tool", arguments={"param": "value"}))
            tool_response = await self.execute_tool(tool_call)

            # Update memory with tool response
            self.memory.add_observation(tool_response)

            # Create and return the AgentResult
            return AgentResult(
                response=response,
                success=True,
                status=self.state,
                memory=self.memory,
                iterations=self.current_step,
                error=None
            )
        except Exception as e:
            logger.error(f"Error during agent run: {e}")
            return AgentResult(
                response="",
                success=False,
                status=AgentState.ERROR,
                memory=self.memory,
                iterations=self.current_step,
                error=str(e)
            )

    async def execute_tool(self, tool_call: ToolCall) -> ToolResponse:
        """Execute a tool call and return the response."""
        # Implement tool execution logic here
        # For example, call the tool and return a ToolResponse
        return ToolResponse(
            call_id=tool_call.id,
            tool_name=tool_call.function.name,
            success=True,
            result={"data": "example result"},
            error=None
        )

    async def cleanup(self):
        """Clean up agent resources"""
        pass

    @abstractmethod
    async def step(self) -> str:
        """Execute a single step in the agent's workflow.

        Must be implemented by subclasses to define specific behavior.
        """

    def handle_stuck_state(self):
        """Handle stuck state by adding a prompt to change strategy"""
        stuck_prompt = "\
        Observed duplicate responses. Consider new strategies and avoid repeating ineffective paths already attempted."
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt}"
        logger.warning(f"Agent detected stuck state. Added prompt: {stuck_prompt}")

    def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate content"""
        if len(self.memory.messages) < 2:
            return False

        last_message = self.memory.messages[-1]
        if not last_message.content:
            return False

        # Count identical content occurrences
        duplicate_count = sum(
            1
            for msg in reversed(self.memory.messages[:-1])
            if msg.role == "assistant" and msg.content == last_message.content
        )

        return duplicate_count >= self.duplicate_threshold

    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value
