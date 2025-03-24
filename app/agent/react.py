from abc import ABC, abstractmethod
from typing import Optional, List

from pydantic import Field

from app.agent.base import BaseAgent
from app.llm import LLM
from app.schema import AgentState, AgentMemory, Role, ToolCall


class ReActAgent(BaseAgent, ABC):
    name: str
    description: Optional[str] = None

    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None

    llm: Optional[LLM] = Field(default_factory=LLM)
    memory: AgentMemory = Field(default_factory=AgentMemory)
    state: AgentState = AgentState.IDLE

    max_steps: int = 10
    current_step: int = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = AgentState.IDLE  # Initialize state
        self.memory = AgentMemory()  # Initialize memory

    def reset_state(self) -> None:
        """Reset the agent state to the initial state."""
        self.state = AgentState.IDLE
        self.current_step = 0
        self.memory.clear()  # Clear memory

    def transition_state(self, new_state: AgentState) -> None:
        """Transition to a new state."""
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")
        self.state = new_state

    async def run(self, prompt: str) -> None:
        """Run the agent with the given prompt."""
        self.reset_state()  # Reset state for new run
        self.memory.add_message(Role.USER, prompt)  # Add user prompt to memory

        try:
            while self.current_step < self.max_steps:
                await self.step()  # Execute a step
                self.current_step += 1
                if self.state == AgentState.DONE:
                    break
        except Exception as e:
            logger.error(f"Error during run: {str(e)}")
            self.memory.add_message(Role.ASSISTANT, f"Error: {str(e)}")

    @abstractmethod
    async def think(self) -> bool:
        """Process current state and decide next action"""

    @abstractmethod
    async def act(self) -> str:
        """Execute decided actions"""

    async def step(self) -> str:
        """Execute a single step: think and act."""
        should_act = await self.think()
        if not should_act:
            return "Thinking complete - stop action"
        return await self.act()

    async def load_session(self):
        """Load session context from a file."""
        # Implement loading logic using AgentMemory
        pass

    async def save_session(self):
        """Save session context to a file."""
        # Implement saving logic using AgentMemory
        pass
