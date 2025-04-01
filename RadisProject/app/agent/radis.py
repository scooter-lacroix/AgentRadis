#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field, asdict  # Added asdict

from app.base import BaseAgent
from app.memory import RollingWindowMemory
from app.schema.types import AgentState, Role, ToolChoice
from app.schema.models import Message, ToolCall, ToolResponse, Function
from app.logger import get_logger
from app.llm import get_default_llm, BaseLLM
from app.tool.base import BaseTool
from app.config import RadisConfig

logger = get_logger(__name__)


@dataclass
class DiagnosticInfo:
    """Tracks runtime diagnostic information for the agent."""

    errors: List[Dict[str, Any]] = field(default_factory=list)
    last_llm_request: Optional[Dict[str, Any]] = None
    last_tool_execution: Optional[Dict[str, Any]] = None
    runtime_states: List[Dict[str, Any]] = field(default_factory=list)

    def add_error(
        self, error_type: str, error_msg: str, context: Optional[Dict[str, Any]] = None
    ):
        """Add an error entry with timestamp."""
        self.errors.append(
            {
                "type": error_type,
                "message": error_msg,
                "context": context or {},
                "timestamp": time.time()
            }
        )
        
    def add_state(self, state: str, context: Optional[Dict[str, Any]] = None):
        """Track runtime state changes."""
        self.runtime_states.append(
            {"state": state, "context": context or {}, "timestamp": time.time()}
        )

class RadisAgent(BaseAgent):
    """
    Core implementation of the Radis agent.

    This agent manages conversations, tools, and memory, allowing for multi-step
    reasoning and tool execution based on natural language inputs.
    """

    def __init__(
        self,
        model: str = RadisConfig().get_llm_config().model,
        temperature: float = 0.7,
        memory_max_tokens: int = 16000,
        system_prompt: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        tool_choice: Union[str, ToolChoice] = ToolChoice.AUTO,  # Added tool_choice
        llm: Optional[BaseLLM] = None,
        name: Optional[str] = None,
        **kwargs,  # Added kwargs for super init
    ):
        """
        Initialize a RadisAgent.

        Args:
            model: The LLM model to use.
            temperature: The temperature parameter for LLM responses.
            memory_max_tokens: Maximum number of tokens to retain in memory.
            system_prompt: Optional system prompt to set agent behavior.
            tools: Optional list of tools available to the agent.
            tool_choice: Strategy for tool usage (e.g., 'auto', 'required', or specific tool).
            llm: Optional LLM interface to use instead of default.
            name: Optional custom name for the agent instance.
            **kwargs: Additional arguments for the parent class.
        """
        super().__init__(name=name or "RadisAgent")  # Call parent initializer

        self.model = model
        self.temperature = temperature
        # Ensure tool_choice is the enum type
        if isinstance(tool_choice, str):
            try:
                self.tool_choice = ToolChoice(tool_choice)
            except ValueError:
                logger.warning(
                    f"Invalid tool_choice string '{tool_choice}'. Defaulting to AUTO."
                )
                self.tool_choice = ToolChoice.AUTO
        else:
            self.tool_choice = tool_choice

        # Initialize memory and tools
        self.memory = RollingWindowMemory(model=model, max_tokens=memory_max_tokens)
        self.tools = tools or []
        self.llm = llm or get_default_llm()
        if isinstance(self.tools, list):
            pass
        else:
            self.tools = []

        # Set initial state
        self.state = AgentState.IDLE
        self.conversation_id = str(uuid.uuid4())
        self.pending_tool_calls: List[ToolCall] = []
        self.current_execution_mode = "sequential"  # or "parallel"

        # Initialize diagnostic info
        self.diagnostic_info = DiagnosticInfo()

        # Add system prompt if provided
        if system_prompt:
            self.set_system_prompt(system_prompt)

        # Mark as configured (can be set in async_setup if setup is truly async)
        self._is_configured = True  # Assuming sync setup for now

    def set_system_prompt(self, prompt: str) -> None:
        """Set or update the system prompt."""
        system_message = Message(role=Role.SYSTEM, content=prompt)
        # Check if a system message already exists and replace it
        existing_system_message_index = -1
        for i, msg in enumerate(self.memory.messages):
            if msg.role == Role.SYSTEM:
                existing_system_message_index = i
                break
        if existing_system_message_index != -1:
            self.memory.messages[existing_system_message_index] = system_message
            logger.info("Updated existing system prompt.")
        else:
            self.memory.add_message(system_message)
            logger.info("Set new system prompt.")

    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the agent's available tools."""
        # Check if tool with same name already exists
        for i, existing_tool in enumerate(self.tools):
            if existing_tool.name == tool.name:
                logger.warning(
                    f"Tool with name '{tool.name}' already exists, replacing it."
                )
                self.tools[i] = tool  # Replace in place
                return  # Exit after replacing

        self.tools.append(tool)
        logger.info(f"Added tool: {tool.name}")

    def remove_tool(self, tool_name: str) -> bool:
        """Remove a tool from the agent's available tools."""
        initial_len = len(self.tools)
        self.tools = [tool for tool in self.tools if tool.name != tool_name]
        if len(self.tools) < initial_len:
            logger.info(f"Removed tool: {tool_name}")
            return True
        else:
            logger.warning(f"Tool '{tool_name}' not found, nothing removed.")
            return False

    def get_tools_as_functions(self) -> List[Dict[str, Any]]:
        """Get all tools formatted as LLM functions."""
        return [tool.as_function() for tool in self.tools]

    async def async_setup(self) -> None:
        """
        Set up the agent asynchronously (if needed).

        Currently, initialization is synchronous. This method can be used
        for future async setup requirements.
        """
        # If there were truly async setup steps, they would go here.
        # self._is_configured = True # Set here if setup is async
        self.state = AgentState.IDLE
        logger.info("Agent async_setup complete (currently no-op).")

    async def reset(self) -> None:
        """
        Reset the agent to its initial state.

        This clears memory (except system prompt) and resets tool states.
        """
        # Remember system prompt
        system_messages = [
            msg for msg in self.memory.get_messages() if msg.role == Role.SYSTEM
        ]

        # Clear memory
        self.memory.clear()

        # Restore system messages
        for msg in system_messages:
            self.memory.add_message(msg)

        # Reset tools state (handle potential async reset)
        reset_tasks = []
        for tool in self.tools:
            # Check if tool has an async reset method
            if hasattr(tool, "reset") and asyncio.iscoroutinefunction(tool.reset):
                reset_tasks.append(tool.reset())
            # Optionally handle synchronous reset if needed
            # elif hasattr(tool, 'reset'):
            #     tool.reset()

        if reset_tasks:
            await asyncio.gather(*reset_tasks)
            logger.info("Asynchronously reset tools.")
        else:
            logger.info("Reset tools (no async reset methods found).")

        self.pending_tool_calls = []
        self.state = AgentState.IDLE
        self.conversation_id = str(uuid.uuid4())  # Generate new conversation ID
        self.diagnostic_info = DiagnosticInfo()  # Reset diagnostics
        logger.info("Agent reset complete.")

    async def cleanup(self) -> None:
        """
        Clean up resources used by the agent.

        This method releases any resources or connections held by tools.
        """
        # Clean up tools (handle potential async cleanup)
        cleanup_tasks = []
        for tool in self.tools:
            if hasattr(tool, "cleanup") and asyncio.iscoroutinefunction(tool.cleanup):
                cleanup_tasks.append(tool.cleanup())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks)
            logger.info("Asynchronously cleaned up tools.")
        else:
            logger.info("Cleaned up tools (no async cleanup methods found).")

        # Clear memory
        self.memory.clear()

        # Reset state
        self.state = AgentState.IDLE
        logger.info("Agent cleanup complete.")

    async def get_diagnostic_report(self) -> Dict[str, Any]:
        """Get a comprehensive diagnostic report."""
        tool_stats = {}
        for tool in self.tools:
            try:
                if hasattr(tool, "get_stats") and asyncio.iscoroutinefunction(
                    tool.get_stats
                ):
                    tool_stats[tool.name] = await tool.get_stats()
                elif hasattr(tool, "get_stats"):
                    tool_stats[tool.name] = (
                        tool.get_stats()
                    )  # Assuming sync version exists
                else:
                    tool_stats[tool.name] = {"status": "No stats method"}
            except Exception as e:
                logger.error(f"Error getting stats for tool {tool.name}: {e}")
                tool_stats[tool.name] = {"error": str(e)}

        return {
            "agent_name": self.name,
            "conversation_id": self.conversation_id,
            "current_state": self.state.value,
            "model": self.model,
            "temperature": self.temperature,
            "tool_choice": self.tool_choice.value,
            "execution_mode": self.current_execution_mode,
            "is_configured": self._is_configured,
            "errors": self.diagnostic_info.errors,
            "last_llm_request": self.diagnostic_info.last_llm_request,
            "last_tool_execution": self.diagnostic_info.last_tool_execution,
            "runtime_states": self.diagnostic_info.runtime_states,
            "memory_stats": {
                "message_count": len(self.memory.messages),
                "token_estimate": self.memory.get_current_token_count(),
            },
            "tool_stats": tool_stats,
        }

    async def run(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """
        Process input and generate a response, potentially using tools.

        Args:
            input_text: The input text to process.
            **kwargs: Additional arguments (currently unused but allows flexibility).

        Returns:
            Dict containing the results, including:
                - response: The final response text.
                - tool_calls: List of ToolCall objects made during processing.
                - tool_results: List of ToolResponse objects from tool execution.
                - conversation_id: The current conversation ID.
                - diagnostic_report: A snapshot of diagnostics after the run.
        """
        if not self._is_configured:
            # This might be unnecessary if __init__ always configures
            await self.async_setup()

        self.state = AgentState.THINKING
        self.diagnostic_info.add_state("run_start", {"input": input_text})

        # Add the user input to memory
        user_message = Message(role=Role.USER, content=input_text)
        self.memory.add_message(user_message)

        all_tool_calls: List[ToolCall] = []
        all_tool_results: List[ToolResponse] = []

        try:
            while self.state not in [AgentState.DONE, AgentState.ERROR]:
                step_complete = await self.step()
                # Collect results from this step if tools were executed
                # Note: _execute_tool_calls now adds results to memory directly
                # We might want to collect them here if needed for the final output structure
                if (
                    self.state == AgentState.THINKING
                    and self.diagnostic_info.last_tool_execution
                ):
                    # Logic to potentially retrieve last step's tool results if needed
                    pass

                if step_complete:
                    self.state = AgentState.DONE
                    break  # Exit loop if step indicates completion

            # Get final response from memory
            final_response = ""
            assistant_messages = [
                msg for msg in self.memory.messages if msg.role == Role.ASSISTANT
            ]
            if assistant_messages:
                # Usually the last assistant message without tool calls is the final one
                for msg in reversed(assistant_messages):
                    if not msg.tool_calls:
                        final_response = msg.content or ""
                        break
                if not final_response and assistant_messages[-1].content:
                    # Fallback if the last message had tool calls but also content
                    final_response = assistant_messages[-1].content

            # Collect all tool calls and results from memory for the report
            all_tool_calls = [
                call
                for msg in self.memory.messages
                if msg.role == Role.ASSISTANT and msg.tool_calls
                for call in msg.tool_calls
            ]
            all_tool_results = [
                ToolResponse(
                    call_id=msg.tool_call_id,
                    tool_name=msg.name,
                    success=True,
                    result=msg.content,
                )  # Simplified reconstruction
                for msg in self.memory.messages
                if msg.role == Role.TOOL
            ]  # TODO: Reconstruct ToolResponse more accurately if needed (e.g., success/error status)

            self.diagnostic_info.add_state(
                "run_end", {"final_response": final_response}
            )
            final_diagnostics = await self.get_diagnostic_report()

            # Prepare result
            result = {
                "response": final_response,
                "tool_calls": [
                    asdict(tc) for tc in all_tool_calls
                ],  # Convert to dicts for JSON serialization
                "tool_results": [
                    asdict(tr) for tr in all_tool_results
                ],  # Convert to dicts
                "conversation_id": self.conversation_id,
                "diagnostic_report": final_diagnostics,
            }

            # Ensure state is IDLE or ERROR after run finishes
            if self.state != AgentState.ERROR:
                self.state = AgentState.IDLE

            return result

        except Exception as e:
            logger.exception("Critical error during agent run.")  # Log with traceback
            self.diagnostic_info.add_error("run_critical_error", str(e))
            self.state = AgentState.ERROR
            # Return error information
            # Process potential JSON tool call in response
            if isinstance(result, dict) and 'response' in result:
                response_text = result['response']
                
                # Check if the response is a JSON object that looks like a tool call
                if isinstance(response_text, str) and response_text.startswith('{') and response_text.endswith('}'):
                    try:
                        # Try to parse the JSON
                        tool_call_data = json.loads(response_text)
                        
                        # Check if it looks like a time tool call
                        if 'action' in tool_call_data and tool_call_data['action'] in ['time', 'date', 'day']:
                            logger.info(f"Detected JSON tool call in response: {tool_call_data}")
                            
                            # Find the time tool
                            time_tool = next((tool for tool in self.tools if tool.name == 'time'), None)
                            
                            if time_tool:
                                logger.info(f"Found time tool, executing with args: {tool_call_data}")
                                # Execute the tool
                                tool_result = await time_tool.run(**tool_call_data)
                                logger.info(f"Tool execution result: {tool_result}")
                                
                                # Update the response with the tool result
                                result['response'] = tool_result
                                
                                # Generate a unique ID for the tool call
                                tool_call_id = str(uuid.uuid4())
                                
                                # Add a simulated tool call for tracking
                                result['tool_calls'].append({
                                    'id': tool_call_id,
                                    'type': 'function',
                                    'function': {
                                        'name': 'time',
                                        'arguments': json.dumps(tool_call_data)
                                    }
                                })
                                
                                # Add a simulated tool result
                                result['tool_results'].append({
                                    'call_id': tool_call_id,
                                    'tool_name': 'time',
                                    'success': True,
                                    'result': tool_result
                                })
                                
                                # Also add a message to memory
                                tool_message = Message(
                                    role=Role.TOOL,
                                    content=tool_result,
                                    name='time',
                                    tool_call_id=tool_call_id
                                )
                                self.memory.add_message(tool_message)
                            else:
                                logger.warning("Time tool not found in agent tools")
                    except json.JSONDecodeError:
                        logger.warning(f"Response looks like JSON but could not be parsed: {response_text}")
                    except Exception as e:
                        logger.error(f"Error processing potential tool call: {str(e)}")
            
            return {
                "response": f"An error occurred: {str(e)}",
                "tool_calls": [asdict(tc) for tc in all_tool_calls],
                "tool_results": [asdict(tr) for tr in all_tool_results],
                "conversation_id": self.conversation_id,
                "diagnostic_report": await self.get_diagnostic_report(),  # Get diagnostics even on error
            }

    async def step(self) -> bool:
        """
        Execute a single step in the agent's reasoning process.

        Returns:
            True if processing is complete (final response generated),
            False if more steps are needed (e.g., after tool execution).
        """
        try:
            # Handle non-thinking states first
            if self.state == AgentState.IDLE:
                # Should be initiated by run() method
                logger.warning("Step called while agent is IDLE.")
                self.state = AgentState.THINKING
                self.diagnostic_info.add_state("thinking_from_idle")
                return False  # Needs LLM call

            if self.state == AgentState.EXECUTING:
                # Transition back to thinking after tool execution is handled by _execute_tool_calls
                logger.error("Step called while in EXECUTING state, should not happen.")
                self.state = AgentState.THINKING  # Force back to thinking
                self.diagnostic_info.add_state("thinking_from_executing_error")
                return False  # Needs LLM call

            if self.state == AgentState.ERROR:
                logger.error("Step called while in ERROR state.")
                return True  # End processing

            if self.state == AgentState.DONE:
                logger.warning("Step called after agent reached DONE state.")
                return True  # Already done

            # --- Handle THINKING state ---
            if self.state == AgentState.THINKING:
                self.diagnostic_info.add_state("thinking_start")
                messages = self.memory.get_messages()
                functions = self.get_tools_as_functions() if self.tools else None

                # Prepare request for LLM
                llm_request_params = {
                    "messages": messages,
                    "model": self.model,  # Pass model and temp if needed by llm.complete
                    "temperature": self.temperature,
                }
                if functions:
                    llm_request_params["tools"] = (
                        functions  # Use "tools" for function calling
                    )
                    # Format tool_choice based on LLM provider requirements
                    if isinstance(self.tool_choice, ToolChoice):
                        # Example: Convert enum to string value expected by API
                        llm_request_params["tool_choice"] = self.tool_choice.value
                    else:
                        llm_request_params["tool_choice"] = str(
                            self.tool_choice
                        )  # Fallback

                # Track LLM request details
                self.diagnostic_info.last_llm_request = {
                    "timestamp": time.time(),
                    "messages_count": len(messages),
                    "functions_count": len(functions) if functions else 0,
                    "tool_choice": llm_request_params.get("tool_choice", "none"),
                }

                # Execute LLM call with retry logic
                max_retries = 3
                response_message: Optional[Message] = (
                    None  # Store the full response message
                )

                for attempt in range(max_retries):
                    try:
                        response_message = await self._execute_llm_call(
                            llm_request_params
                        )
                        break  # Success
                    except Exception as e:
                        error_msg = f"LLM call failed (attempt {attempt+1}/{max_retries}): {str(e)}"
                        logger.warning(error_msg)
                        self.diagnostic_info.add_error(
                            "llm_call_attempt_error",
                            error_msg,
                            {"attempt": attempt + 1},
                        )
                        if attempt == max_retries - 1:
                            self.diagnostic_info.add_error(
                                "llm_call_failed",
                                str(e),
                                {"request": llm_request_params},
                            )
                            self.state = AgentState.ERROR
                            raise  # Propagate error after final retry
                        await asyncio.sleep(
                            1 * (2**attempt)
                        )  # Exponential backoff starting at 1s

                if not response_message:
                    # Should not happen if retry logic works, but handle defensively
                    logger.error(
                        "LLM call failed after retries, response_message is None."
                    )
                    self.state = AgentState.ERROR
                    return True  # End processing due to error

                # Add LLM response to memory
                self.memory.add_message(response_message)
                self.diagnostic_info.add_state(
                    "llm_response_received",
                    {"has_tool_calls": bool(response_message.tool_calls)},
                )

                if response_message.tool_calls:
                    # Process tool calls
                    self.pending_tool_calls = response_message.tool_calls
                    self.state = AgentState.EXECUTING
                    self.diagnostic_info.add_state(
                        "executing_tools_start", {"count": len(self.pending_tool_calls)}
                    )

                    # Execute tools (this method handles state transition back to THINKING)
                    await self._execute_tool_calls()
                    return False  # More processing needed after tool execution
                else:
                    # No tool calls, this is a final response
                    self.diagnostic_info.add_state("final_response_generated")
                    # State will be set to DONE by the run() method
                    return True  # Final response reached

            # Fallback if state is somehow unexpected
            logger.error(f"Step encountered unexpected state: {self.state}")
            self.state = AgentState.ERROR
            return True

        except Exception as e:
            logger.exception("Error during agent step execution.")  # Log with traceback
            self.diagnostic_info.add_error("step_critical_error", str(e))
            self.state = AgentState.ERROR
            return True  # End processing due to error

    async def _execute_tool_calls(self) -> None:
        """
        Execute pending tool calls, add results to memory, and transition state.
        Handles both sequential and parallel execution.
        """
        if not self.pending_tool_calls:
            self.state = AgentState.THINKING  # Nothing to execute, go back to thinking
            return

        tool_responses: List[Union[ToolResponse, Exception]] = []
        start_time = time.time()
        executed_call_ids = {call.id for call in self.pending_tool_calls}

        try:
            if self.current_execution_mode == "parallel":
                tasks = [
                    self._execute_single_tool_call(call)
                    for call in self.pending_tool_calls
                ]
                # return_exceptions=True ensures gather doesn't stop on first error
                tool_responses = await asyncio.gather(*tasks, return_exceptions=True)
            else:  # Sequential execution
                for tool_call in self.pending_tool_calls:
                    try:
                        response = await self._execute_single_tool_call(tool_call)
                        tool_responses.append(response)
                    except Exception as e:
                        logger.exception(
                            f"Error during sequential execution of tool {tool_call.function.name}"
                        )
                        # Create a ToolResponse error object to maintain structure
                        error_response = ToolResponse(
                            call_id=tool_call.id,
                            tool_name=tool_call.function.name,
                            success=False,
                            result=f"Error: {str(e)}",
                            error=str(e),
                        )
                        tool_responses.append(error_response)

            # Process responses and add to memory
            successful_count = 0
            for i, response_or_exc in enumerate(tool_responses):
                tool_call = self.pending_tool_calls[i]  # Get corresponding call
                tool_response: Optional[ToolResponse] = None

                if isinstance(response_or_exc, ToolResponse):
                    tool_response = response_or_exc
                    if tool_response.success:
                        successful_count += 1
                elif isinstance(response_or_exc, Exception):
                    # Handle exceptions raised during gather or sequential execution
                    error_msg = (
                        f"Exception during tool execution: {str(response_or_exc)}"
                    )
                    logger.error(error_msg)
                    tool_response = ToolResponse(
                        call_id=tool_call.id,
                        tool_name=tool_call.function.name,
                        success=False,
                        result=f"Error: {error_msg}",
                        error=str(response_or_exc),
                    )
                    self.diagnostic_info.add_error(
                        "tool_execution_exception",
                        str(response_or_exc),
                        {"tool_call": asdict(tool_call)},
                    )
                else:
                    # Should not happen, but handle defensively
                    logger.error(
                        f"Unexpected item in tool_responses: {response_or_exc}"
                    )
                    tool_response = ToolResponse(
                        call_id=tool_call.id,
                        tool_name=tool_call.function.name,
                        success=False,
                        result="Error: Unexpected execution result type",
                        error="Unexpected execution result type",
                    )

                # Add message to memory regardless of success/failure
                if tool_response:
                    tool_message = Message(
                        role=Role.TOOL,
                        content=tool_response.result,
                        name=tool_response.tool_name,
                        tool_call_id=tool_response.call_id,  # Link response to call
                    )
                    self.memory.add_message(tool_message)

            # Update diagnostic info after processing all responses
            self.diagnostic_info.last_tool_execution = {
                "start_time": start_time,
                "end_time": time.time(),
                "duration_ms": (time.time() - start_time) * 1000,
                "tool_count": len(self.pending_tool_calls),
                "successful_responses": successful_count,
                "execution_mode": self.current_execution_mode,
                "executed_call_ids": list(executed_call_ids),
            }
            self.diagnostic_info.add_state(
                "executing_tools_end", self.diagnostic_info.last_tool_execution
            )

        except Exception as e:
            # Catch-all for unexpected errors during the execution process itself
            error_msg = f"Critical error during _execute_tool_calls: {str(e)}"
            logger.exception(error_msg)
            self.diagnostic_info.add_error("tool_execution_critical_error", error_msg)
            self.state = AgentState.ERROR  # Set error state
            # Optionally add error messages to memory for each pending call
            for tool_call in self.pending_tool_calls:
                error_message = Message(
                    role=Role.TOOL,
                    content=f"Error during tool execution phase: {error_msg}",
                    name=tool_call.function.name,
                    tool_call_id=tool_call.id,
                )
                self.memory.add_message(error_message)

        finally:
            # Clear pending calls and transition back to thinking (unless error occurred)
            self.pending_tool_calls = []
            if self.state != AgentState.ERROR:
                self.state = AgentState.THINKING
                self.diagnostic_info.add_state("thinking_after_tools")

    async def _execute_single_tool_call(self, tool_call: ToolCall) -> ToolResponse:
        """
        Execute a single tool call, handling argument parsing and execution.

        Returns:
            ToolResponse with execution results (success or failure).
        """
        function_name = tool_call.function.name
        function_args_raw = tool_call.function.arguments  # Can be dict or string
        start_time = time.time()
        logger.debug(
            f"Attempting to execute tool: {function_name} with ID: {tool_call.id}"
        )

        # Find matching tool
        matching_tool = next(
            (tool for tool in self.tools if tool.name == function_name), None
        )

        if not matching_tool:
            error_msg = f"Tool '{function_name}' not found"
            logger.warning(error_msg)
            return ToolResponse(
                call_id=tool_call.id,
                tool_name=function_name,
                success=False,
                result=f"Error: {error_msg}",
                error=error_msg,
            )

        # Parse arguments
        args: Dict[str, Any] = {}
        try:
            if isinstance(function_args_raw, str):
                # Handle potential empty string or invalid JSON
                if not function_args_raw.strip():
                    args = {}
                else:
                    args = json.loads(function_args_raw)
            elif isinstance(function_args_raw, dict):
                args = function_args_raw  # Already a dict
            else:
                raise TypeError(f"Unexpected argument type: {type(function_args_raw)}")

            # Validate parameters against tool's schema
            validated_args = matching_tool.validate_parameters(args)

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            error_msg = f"Invalid arguments for tool '{function_name}': {str(e)}. Raw args: {function_args_raw}"
            logger.error(error_msg)
            return ToolResponse(
                call_id=tool_call.id,
                tool_name=function_name,
                success=False,
                result=f"Error: {error_msg}",
                error=str(e),
            )

        # Execute tool
        try:
            logger.info(f"Executing tool '{function_name}' with args: {validated_args}")
            # Execute the tool's run method (assuming it's async)
            if not asyncio.iscoroutinefunction(matching_tool.run):
                raise TypeError(f"Tool '{function_name}' run method is not async")

            result = await matching_tool.run(**validated_args)

            # Ensure result is a string for consistency in memory/LLM
            result_str = str(result) if not isinstance(result, str) else result

            logger.info(f"Tool '{function_name}' executed successfully.")
            return ToolResponse(
                call_id=tool_call.id,
                tool_name=function_name,
                success=True,
                result=result_str,
            )

        except Exception as e:
            error_msg = f"Error executing tool '{function_name}': {str(e)}"
            logger.exception(
                f"Tool execution failed for {function_name}"
            )  # Log with traceback
            return ToolResponse(
                call_id=tool_call.id,
                tool_name=function_name,
                success=False,
                result=f"Error: {error_msg}",
                error=str(e),
            )
        finally:
            duration = time.time() - start_time
            logger.debug(
                f"Tool '{function_name}' (ID: {tool_call.id}) finished in {duration:.3f}s"
            )

    async def _execute_llm_call(self, request_params: Dict[str, Any]) -> Message:
        """
        Execute LLM call, parse response, and return a Message object.

        Args:
            request_params: The LLM request parameters.

        Returns:
            A Message object representing the assistant's response.

        Raises:
            Exception: If the LLM call fails.
        """
        logger.debug(
            f"Executing LLM call with {len(request_params.get('messages', []))} messages."
        )
        # Make LLM call using the provided interface
        # llm.complete should return (content_string, metadata_dict)
        content, metadata = self.llm.complete(**request_params)

        # Check for and format tool calls from metadata
        parsed_tool_calls: List[ToolCall] = []
        raw_tool_calls = metadata.get("tool_calls")

        if isinstance(raw_tool_calls, list):
            for tc_data in raw_tool_calls:
                try:
                    # Defensive parsing of potentially varied tool call structures
                    func_data = tc_data.get("function", {})
                    func_name = func_data.get("name")
                    func_args_raw = func_data.get("arguments")  # Often a string
                    call_id = tc_data.get(
                        "id", str(uuid.uuid4())
                    )  # Generate ID if missing

                    if not func_name:
                        logger.warning(
                            f"Skipping tool call with missing function name: {tc_data}"
                        )
                        continue

                    # Parse arguments string into dict
                    func_args_dict: Dict[str, Any] = {}
                    if isinstance(func_args_raw, str):
                        if func_args_raw.strip():
                            try:
                                func_args_dict = json.loads(func_args_raw)
                            except json.JSONDecodeError:
                                logger.error(
                                    f"Failed to parse JSON arguments for tool call {call_id} ({func_name}): {func_args_raw}"
                                )
                                # Decide how to handle: error, skip, or pass raw string?
                                # Option: Pass error dict
                                func_args_dict = {
                                    "error": "Failed to parse arguments JSON",
                                    "raw_arguments": func_args_raw,
                                }
                        # else: empty string means empty dict {}
                    elif isinstance(func_args_raw, dict):
                        func_args_dict = func_args_raw  # Already a dict
                    elif func_args_raw is None:
                        func_args_dict = {}  # No arguments provided
                    else:
                        logger.error(
                            f"Unexpected argument type for tool call {call_id} ({func_name}): {type(func_args_raw)}"
                        )
                        func_args_dict = {
                            "error": "Unexpected arguments type",
                            "raw_arguments": str(func_args_raw),
                        }

                    tool_call = ToolCall(
                        id=call_id,
                        type=tc_data.get("type", "function"),  # Default to function
                        function=Function(
                            name=func_name,
                            arguments=func_args_dict,  # Store parsed dict
                        ),
                    )
                    parsed_tool_calls.append(tool_call)
                except Exception as e:
                    logger.exception(
                        f"Error parsing tool call data: {tc_data}. Error: {e}"
                    )
                    # Decide whether to skip this call or add an error marker

        # Construct the assistant's message
        assistant_message = Message(
            role=Role.ASSISTANT,
            content=content or "",  # Ensure content is not None
            tool_calls=(
                parsed_tool_calls if parsed_tool_calls else None
            ),  # Use None if list is empty
        )
        logger.debug(
            f"LLM call successful. Content length: {len(assistant_message.content)}. Tool calls: {len(parsed_tool_calls)}"
        )
        return assistant_message
