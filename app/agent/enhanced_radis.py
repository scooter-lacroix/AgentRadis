"""
Enhanced Radis Agent Module

This module extends the Radis agent with planning and execution features.
"""

from typing import Dict, List, Optional, Any, Union
import uuid
import json
import time
from datetime import datetime

from app.agent.radis import Radis
from app.schema import AgentMemory, Message, Role, AgentState, ToolChoice, ToolCall, Function
from app.logger import logger
from app.tool.base import BaseTool

class EnhancedRadis(Radis):
    """
    Enhanced version of Radis with additional functionality for planning and execution.
    """
    name: str = "EnhancedRadis"
    mode: str = "act"  # Default to action mode

    def __init__(self,
                 mode: str = "act",
                 tools: Optional[List[BaseTool]] = None,
                 api_base: Optional[str] = None,
                 **kwargs):
        """Initialize the enhanced agent with specified mode"""
        super().__init__(tools=tools, api_base=api_base, **kwargs)

        self.mode = mode
        self.system_prompt = "You are EnhancedRadis in planning mode" if mode == "plan" else "You are EnhancedRadis in action mode"

        # Tracking for planning
        self.active_plan_id = None
        self.current_step_index = None
        self.step_execution_tracker = {}

        # Tracking for artifacts and tool calls
        self.artifacts = []
        self.tool_calls = []

        # Error handling
        self.error_recovery_attempts = 0
        self.max_consecutive_errors = 3
        self.session_context = {}

    async def async_setup(self):
        await self.load_session()

    async def run(self, prompt: str, mode: str = None) -> Dict[str, Any]:
        """Run the agent with the given prompt."""
        # Update mode if provided
        if mode is not None:
            if mode.lower() == "plan":
                self.mode = "plan"
                self.system_prompt = "You are EnhancedRadis in planning mode"
            else:
                self.mode = "act"
                self.system_prompt = "You are EnhancedRadis in action mode"

        # Reset state for new run
        await self.reset()

        # Add user prompt to memory
        self.memory.messages.append(Message(role=Role.USER, content=prompt))

        try:
            # Set up state variables
            self.state = AgentState.IDLE
            self.iteration_count = 0
            max_iterations = 15

            # Main agent loop
            while self.state != AgentState.DONE and self.iteration_count < max_iterations:
                # Execute a step
                step_result = await self.step()
                logger.info(f"Step {self.iteration_count + 1}: {step_result}")
                self.iteration_count += 1

                # Check if we have a final response
                if self.state == AgentState.THINKING:
                    # Get the last assistant message
                    assistant_messages = [m for m in self.memory.messages if m.role == Role.ASSISTANT and m.content]
                    if assistant_messages and not hasattr(assistant_messages[-1], 'tool_calls'):
                        # If we have a response without tool calls, we're done
                        self.state = AgentState.DONE
                        break

            # Generate final response
            final_response = self._generate_final_response()

            await self.save_session()
            return {
                "status": "success",
                "response": final_response,
                "artifacts": self.artifacts,
                "tool_calls": self.tool_calls
            }
        except Exception as e:
            logger.error(f"Error in EnhancedRadis.run: {str(e)}")
            return {
                "status": "error",
                "response": f"I encountered an error while processing your request: {str(e)}",
                "artifacts": self.artifacts,
                "tool_calls": self.tool_calls
            }

    async def reset(self) -> None:
        """Reset the agent state for a new conversation"""
        await super().reset()
        # Reset planning state
        self.session_context = {}
        self.active_plan_id = None
        self.current_step_index = None
        self.step_execution_tracker = {}
        # Reset artifacts and tool calls
        self.artifacts = []
        self.tool_calls = []
        self.error_recovery_attempts = 0
        await self.load_session()

    def _generate_final_response(self) -> str:
        """Generate a final response from the conversation history"""
        # Find the last assistant message
        assistant_messages = [m for m in self.memory.messages if m.role == Role.ASSISTANT and m.content]

        if assistant_messages:
            # Get the last assistant message
            last_message = assistant_messages[-1]

            # Return the content
            return last_message.content

        # If no assistant message with content, check for tool results
        tool_messages = [m for m in self.memory.messages if m.role == Role.TOOL]

        if tool_messages:
            # Process tool messages to create a coherent response
            response_parts = []

            for message in tool_messages:
                if hasattr(message, 'name') and message.name == 'web_search':
                    if 'current date' in message.content or 'current time' in message.content:
                        # Return the date/time directly for date/time queries
                        return message.content
                    # Add web search results to response
                    response_parts.append(message.content)
                elif hasattr(message, 'name') and message.name:
                    # Add other tool results to response
                    tool_name = message.name.replace('_', ' ').title()
                    response_parts.append(f"From {tool_name}: {message.content}")

            if response_parts:
                return "\n\n".join(response_parts)

        # Get the original user query
        user_messages = [m.content for m in self.memory.messages if m.role == Role.USER]
        original_query = user_messages[0] if user_messages else "your request"

        # If no response could be generated, return a default message
        return f"I processed {original_query}, but I don't have a specific response at this time."

    async def step(self) -> str:
        """Execute a single step of the agent's reasoning."""
        if self.state == AgentState.IDLE:
            self.state = AgentState.THINKING
            return await self._think()
        elif self.state == AgentState.THINKING:
            self.state = AgentState.EXECUTING
            return await self._act()
        elif self.state == AgentState.EXECUTING:
            self.state = AgentState.THINKING  # Go back to thinking phase
            return "Completed execution phase, now thinking about next steps"
        return "Unknown state"

    async def _think(self) -> str:
        """Process current state and decide next actions"""
        try:
            # Format tools for the LLM
            formatted_tools = self.get_tools_for_llm()

            # Get response with tool options
            response = await self.llm.ask_tool(
                messages=self.memory.messages,
                system_msgs=[Message(role=Role.SYSTEM, content=self.system_prompt)]
                if self.system_prompt
                else None,
                tools=formatted_tools,
                tool_choice=ToolChoice.AUTO,
            )

            # Add the response to memory
            self.memory.messages.append(response)

            # Extract tool calls
            self.tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []

            return "Thought about the request and decided on next steps"
        except Exception as e:
            logger.error(f"Error in thinking phase: {str(e)}")
            self.memory.messages.append(
                Message(
                    role=Role.ASSISTANT,
                    content=f"Error encountered while processing: {str(e)}"
                )
            )
            return f"Error in thinking: {str(e)}"

    async def _act(self) -> str:
        """Execute tool calls and handle their results"""
        if not self.tool_calls:
            # No tool calls, just return
            return "No tools to execute"

        results = []
        errors = []

        # Execute each tool and collect results
        for command in self.tool_calls:
            try:
                await self._execute_tool_call(command)
                results.append(f"Executed tool: {command.function.name if hasattr(command, 'function') else command.get('name', 'unknown')}")
            except Exception as e:
                error_msg = f"Error executing tool: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

                # Add error message to memory
                tool_name = command.function.name if hasattr(command, 'function') else command.get('name', 'unknown')
                tool_id = command.id if hasattr(command, 'id') else command.get('id', str(uuid.uuid4()))
                self.memory.messages.append(Message(
                    role=Role.TOOL,
                    content=error_msg,
                    tool_call_id=tool_id,
                    name=tool_name
                ))

        # Reset tool calls for next iteration
        self.tool_calls = []

        # Combine results and errors
        all_outputs = results + (errors if errors else [])

        if not all_outputs:
            return "All tools completed with no output"

        return "\n".join(all_outputs)

    async def create_plan(self, task: str) -> str:
        """Create a new plan for the given task"""
        self.active_plan_id = f"plan_{str(uuid.uuid4())[:8]}"
        return f"Created plan {self.active_plan_id} for task: {task}"

    async def update_plan_status(self, step_index: int, status: str, result: Any = None) -> None:
        """Update the status of a plan step"""
        self.step_execution_tracker[step_index] = {
            "status": status,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }

    async def get_plan(self) -> str:
        """Get the current plan status"""
        if not self.active_plan_id:
            return "No active plan"

        # Return a string representation of the plan
        steps_status = "\n".join([
            f"Step {idx}: {status['status']}"
            for idx, status in self.step_execution_tracker.items()
        ])

        return f"Plan {self.active_plan_id}\n{steps_status}"

    def add_artifact(self, artifact_type: str, content: Any, **kwargs) -> None:
        """Add an artifact to the agent's output"""
        artifact = {
            "type": artifact_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }

        # Add any additional metadata
        for key, value in kwargs.items():
            artifact[key] = value

        self.artifacts.append(artifact)

    def add_tool_call(self, name: str, args: Dict[str, Any], result: Any, success: bool) -> None:
        """Add a tool call to the agent's tracking"""
        self.tool_calls.append({
            "name": name,
            "args": args,
            "result": result,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })

    _SESSION_FILE = "agentradis_session.json"

    async def load_session(self):
        """Load session context from a file."""
        try:
            with open(self._SESSION_FILE, "r") as f:
                session_data = json.load(f)
            self.memory = AgentMemory.from_dict(session_data["memory"])
            self.mode = session_data["mode"]
            self.system_prompt = session_data["system_prompt"]
            logger.info("Loaded session from file.")
        except FileNotFoundError:
            logger.info("No session file found, starting new session.")
        except json.JSONDecodeError as e:
            logger.warning(f"Session file is corrupted, starting new session. {e}")
            try:
                import os
                os.remove(self._SESSION_FILE)
                logger.info("Deleted corrupted session file.")
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.error(f"Error deleting corrupted session file: {e}")
        except Exception as e:
            logger.error(f"Error loading session: {e}")

    async def save_session(self):
        """Save session context to a file."""
        try:
            session_data = {
                "memory": self.memory.to_dict(),
                "mode": self.mode,
                "system_prompt": self.system_prompt,
            }
            with open(self._SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=4, sort_keys=True, ensure_ascii=False)
            logger.info("Saved session to file.")
        except Exception as e:
            logger.error(f"Error saving session: {e}")

    def get_session_file(self):
        """Get the session file path."""
        return self._SESSION_FILE
