from typing import List, Optional, Any
import json
import logging
from datetime import datetime

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.prompt.swe import NEXT_STEP_TEMPLATE, SYSTEM_PROMPT
from app.tool import Bash, StrReplaceEditor, Terminate, ToolCollection
from app.schema import ToolCall, Function, AgentMemory

# Define a logger
logger = logging.getLogger(__name__)

class SWEAgent(ToolCallAgent):
    """An agent that implements the SWEAgent paradigm for executing code and natural conversations."""

    name: str = "swe"
    description: str = "An autonomous AI programmer that interacts directly with the computer to solve tasks."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_TEMPLATE

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(Bash(), StrReplaceEditor(), Terminate())
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    max_steps: int = 30

    bash: Bash = Field(default_factory=Bash)
    working_dir: str = "."

    async def think(self) -> bool:
        """Process current state and decide next action"""
        try:
            # Update working directory
            self.working_dir = await self.bash.execute("pwd")
            self.next_step_prompt = self.next_step_prompt.format(
                current_dir=self.working_dir
            )

            # Call the super method to process thinking
            return await super().think()
        except Exception as e:
            logger.error(f"Error in think method: {str(e)}")
            return False  # Indicate that thinking could not be completed

    async def act(self) -> str:
        """Execute the decided actions and handle errors."""
        try:
            # Implement action logic here
            # For example, execute a tool call
            tool_call = ToolCall(function=Function(name="example_tool", arguments={"param": "value"}))
            result = await self.execute_tool(tool_call)
            return result
        except Exception as e:
            logger.error(f"Error during action execution: {str(e)}")
            return "Action execution failed."

    def track_artifact(self, artifact_type: str, content: Any, **kwargs) -> None:
        """Track generated artifacts."""
        artifact = {
            "type": artifact_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        for key, value in kwargs.items():
            artifact[key] = value
        self.artifacts.append(artifact)

    async def load_session(self):
        """Load session context from a file."""
        try:
            with open(self.get_session_file(), "r") as f:
                session_data = json.load(f)
            self.memory = AgentMemory.from_dict(session_data["memory"])
            self.working_dir = session_data.get("working_dir", ".")
            self.mode = session_data["mode"]
            self.system_prompt = session_data["system_prompt"]
            logger.info("Loaded session from file.")
        except FileNotFoundError:
            logger.info("No session file found, starting new session.")
        except json.JSONDecodeError as e:
            logger.warning(f"Session file is corrupted, starting new session. {e}")
        except Exception as e:
            logger.error(f"Error loading session: {e}")

    async def save_session(self):
        """Save session context to a file."""
        try:
            session_data = {
                "memory": self.memory.to_dict(),
                "working_dir": self.working_dir,
                "mode": self.mode,
                "system_prompt": self.system_prompt,
            }
            with open(self.get_session_file(), "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=4, sort_keys=True, ensure_ascii=False)
            logger.info("Saved session to file.")
        except Exception as e:
            logger.error(f"Error saving session: {e}")

    def get_session_file(self):
        """Get the session file path."""
        return "swe_session.json"  # Define the session file path
