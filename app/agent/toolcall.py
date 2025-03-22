import json
import re
import uuid

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import Field

from app.agent.react import ReActAgent
from app.logger import logger
from app.prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import AgentState, Message, ToolCall, TOOL_CHOICE_TYPE, ToolChoice, Function, Role, AgentMemory
from app.tool import CreateChatCompletion, Terminate, ToolCollection


TOOL_CALL_REQUIRED = "Tool calls required but none provided"


class ToolCallAgent(ReActAgent):
    """Base agent class for handling tool/function calls with enhanced abstraction"""

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = ToolCollection(
        CreateChatCompletion(), Terminate()
    )
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)

    max_steps: int = 300
    max_observe: Optional[Union[int, bool]] = None

    def __init_subclass__(cls, **kwargs):
        """Set up subclasses"""
        super().__init_subclass__(**kwargs)
        
        # Initialize memory if not already defined
        if not hasattr(cls, "memory") or cls.memory is None:
            cls.memory = AgentMemory()

    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        if self.next_step_prompt:
            # Create a user message manually since we don't have the static method
            user_msg = Message(role=Role.USER, content=self.next_step_prompt)
            self.messages.append(user_msg)

        try:
            # Get response with tool options
            response = await self.llm.ask_tool(
                messages=self.messages,
                system_msgs=[Message(role=Role.SYSTEM, content=self.system_prompt)]
                if self.system_prompt
                else None,
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
            
            # Check for empty content with tool calls - symptom of looping
            if not response.content and response.tool_calls:
                logger.warning(f"⚠️ Empty content with tool calls detected - possible looping")
                
                # Add a message to guide the model
                self.memory.messages.append(Message(
                    role=Role.SYSTEM, 
                    content="I notice you're making tool calls without providing any reasoning. "
                    "Please explain your thought process before using tools."
                ))
                
                # Still allow the tool calls to proceed this time
                self.tool_calls = response.tool_calls or []
                return bool(self.tool_calls)
            
            # Ensure tool_calls is a list, even if empty
            self.tool_calls = response.tool_calls or []

            # Check if the response contains text-based tool requests like [TOOL_REQUEST]
            text_tool_patterns = [
                r'\[TOOL_REQUEST\]', 
                r'\"name\":', 
                r'\{\"name\"', 
                r'\{\s*\"name\"', 
                r'function:\s*{\s*name:',
                r'tool\(.*\)'
            ]
            
            is_text_tool_request = False
            if response.content:
                for pattern in text_tool_patterns:
                    if re.search(pattern, response.content):
                        is_text_tool_request = True
                        break
            
            if is_text_tool_request:
                logger.warning(f"⚠️ Model is trying to use text-based tool requests instead of API")
                
                # Extract potential tool calls from text
                try:
                    # First, look for [TOOL_REQUEST] format
                    json_matches = []
                    tool_request_blocks = re.findall(r'\[TOOL_REQUEST\](.*?)\[END_TOOL_REQUEST\]', response.content, re.DOTALL)
                    
                    if tool_request_blocks:
                        for block in tool_request_blocks:
                            # Clean up the block and extract JSON
                            block = block.strip()
                            if block.startswith('{') and block.endswith('}'):
                                json_matches.append(block)
                            else:
                                # Look for JSON within the block
                                inner_json = re.findall(r'\{[\s\S]*?\"name\"[\s\S]*?\}', block)
                                json_matches.extend(inner_json)
                    else:
                        # Look for general JSON-like content
                        json_matches = re.findall(r'\{[\s\S]*?\"name\"[\s\S]*?\}', response.content)
                    
                    if json_matches:
                        for match in json_matches:
                            try:
                                # Try to properly format the JSON if needed
                                match = match.replace("'", '"')
                                # Fix common issues like unquoted keys
                                match = re.sub(r'(\w+):', r'"\1":', match)
                                
                                tool_data = json.loads(match)
                                if "name" in tool_data and ("arguments" in tool_data or "params" in tool_data):
                                    # Get arguments from whichever key exists
                                    args = tool_data.get("arguments", tool_data.get("params", {}))
                                    
                                    # Create a proper tool call
                                    tool_call = ToolCall(
                                        id=str(uuid.uuid4()),
                                        type="function",
                                        function=Function(
                                            name=tool_data["name"],
                                            arguments=json.dumps(args) if isinstance(args, dict) else args
                                        )
                                    )
                                    self.tool_calls.append(tool_call)
                                    logger.info(f"🛠️ Extracted tool call from text: {tool_data['name']}")
                            except Exception as e:
                                logger.error(f"Failed to parse text-based tool call: {e}")
                except Exception as parsing_error:
                    logger.error(f"Error parsing potential tool calls from text: {parsing_error}")
                
                # Add an informative message to help model use the correct format
                content_without_tools = re.sub(r'\[TOOL_REQUEST\][\s\S]*?\[END_TOOL_REQUEST\]', '', response.content)
                content_without_tools = content_without_tools.strip()
                
                # Create modified content to inform model about proper tool usage
                modified_content = content_without_tools
                if modified_content:
                    modified_content += "\n\n"
                modified_content += "(System: Please use the API tools interface directly, not text-based tool requests. I've processed your intended tool call for now.)"
                
                # Update the response content
                assistant_msg = Message(role=Role.ASSISTANT, content=modified_content)
                self.memory.messages.append(assistant_msg)
                
                # We have processed tool calls, so return True
                return bool(self.tool_calls)
            
            # Log response info with improved messaging
            logger.info(f"✨ {self.name}'s thoughts: {response.content or 'No content provided'}")
            
            tool_count = len(self.tool_calls)
            if tool_count > 0:
                logger.info(f"🛠️ {self.name} selected {tool_count} tool{'s' if tool_count > 1 else ''} to use")
                logger.info(
                    f"🧰 Tools being prepared: {[call.function.name for call in self.tool_calls]}"
                )
            else:
                logger.info(f"🤔 {self.name} didn't select any tools for this step")

            # Handle different tool_choices modes
            if self.tool_choices == ToolChoice.NONE:
                if self.tool_calls:
                    logger.warning(
                        f"🤔 Hmm, {self.name} tried to use tools when they weren't available!"
                    )
                if response.content:
                    self.memory.add_message(Message.assistant_message(response.content))
                    return True
                return False

            # Create and add assistant message if not already added
            if not self.tool_calls and not any(msg.role == Role.ASSISTANT and msg.content == response.content 
                                              for msg in self.messages[-1:]):
                assistant_msg = Message(role=Role.ASSISTANT, content=response.content or "")
                self.memory.messages.append(assistant_msg)
            elif self.tool_calls:
                # Create a message with tool calls
                assistant_msg = Message(
                    role=Role.ASSISTANT, 
                    content=response.content or "",
                    tool_calls=self.tool_calls
                )
                # Check if we haven't already added this message
                if not any(msg.role == Role.ASSISTANT and 
                          (hasattr(msg, 'tool_calls') and msg.tool_calls and 
                           self.tool_calls and msg.tool_calls[0].function.name == self.tool_calls[0].function.name)
                          for msg in self.messages[-1:]):
                    self.memory.messages.append(assistant_msg)

            if self.tool_choices == ToolChoice.REQUIRED and not self.tool_calls:
                logger.warning(f"⚠️ Tool calls were required but none were provided")
                return True  # Will be handled in act()

            # For 'auto' mode, continue with content if no commands but content exists
            if self.tool_choices == ToolChoice.AUTO and not self.tool_calls:
                return bool(response.content)

            return bool(self.tool_calls)
        
        except Exception as e:
            # Check specifically for API connection errors and re-raise them
            error_str = str(e)
            if "APIConnectionError" in error_str or "Connection error" in error_str:
                logger.error(f"🚨 API connection error in {self.name}'s thinking process: {e}")
                # Don't re-raise, just log the error
            
            logger.error(f"🚨 Oops! The {self.name}'s thinking process hit a snag: {e}")
            self.memory.messages.append(
                Message(
                    role=Role.ASSISTANT, 
                    content=f"Error encountered while processing: {str(e)}"
                )
            )
            return False

    async def act(self) -> str:
        """Execute tool calls and handle their results"""
        if not self.tool_calls:
            if self.tool_choices == ToolChoice.REQUIRED:
                return "Error: Tool calls were required but none were provided"

            # Return last message content if no tool calls
            return self.messages[-1].content or "No content or commands to execute"

        results = []
        errors = []
        
        # Execute each tool and collect results
        for command in self.tool_calls:
            try:
                result = await self._execute_tool_call(command)

                if self.max_observe and isinstance(result, str):
                    if isinstance(self.max_observe, int):
                        result = result[:self.max_observe]
                    # If max_observe is True but not a number, we don't truncate

                logger.info(
                    f"🎯 Tool '{command.function.name}' completed. Result length: {len(str(result)) if result else 0} chars"
                )

                # Add tool response to memory
                tool_msg = Message(
                    role=Role.TOOL,
                    content=result,
                    tool_call_id=command.id,
                    name=command.function.name
                )
                self.memory.messages.append(tool_msg)
                results.append(result)
            except Exception as e:
                error_msg = f"Error executing tool '{command.function.name}': {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                
                # Add error message to memory
                tool_msg = Message(
                    role=Role.TOOL,
                    content=error_msg,
                    tool_call_id=command.id,
                    name=command.function.name
                )
                self.memory.messages.append(tool_msg)

        # Combine results and errors
        all_outputs = results + (errors if errors else [])
        
        if not all_outputs:
            return "All tools completed with no output"
        
        return "\n\n".join(all_outputs)

    async def _execute_tool_call(self, tool_call, tool_call_id=None, try_multiple_methods=True):
        """Execute a tool call and return the result.
        
        Args:
            tool_call: The tool call to execute
            tool_call_id: Optional ID for the tool call
            try_multiple_methods: Whether to try multiple methods of executing the tool
            
        Returns:
            The result of the tool execution
        """
        # Extract tool name and arguments
        if hasattr(tool_call, 'function') and hasattr(tool_call.function, 'name'):
            # New format (OpenAI style)
            tool_name = tool_call.function.name
            arguments_raw = tool_call.function.arguments
        elif hasattr(tool_call, 'name'):
            # Old format
            tool_name = tool_call.name
            arguments_raw = getattr(tool_call, 'arguments', {})
        else:
            # Unknown format
            raise ValueError(f"Invalid tool call format: {tool_call}")
        
        # Get the tool ID
        tool_id = getattr(tool_call, 'id', tool_call_id or str(uuid.uuid4()))
            
        # Parse arguments if they're a string
        if isinstance(arguments_raw, str):
            try:
                arguments = json.loads(arguments_raw)
            except json.JSONDecodeError:
                # If not valid JSON, treat as a text argument
                arguments = {"text": arguments_raw}
        else:
            arguments = arguments_raw or {}
        
        # Get the tool from available tools
        if not self.available_tools:
            raise ValueError("No tools available")
            
        tool = self.available_tools.get(tool_name)
        if not tool:
            logger.warning(f"Tool '{tool_name}' not found")
            return f"Error: Tool '{tool_name}' not found in available tools"
        
        # Execute the tool
        try:
            logger.info(f"Executing tool: {tool_name} with args: {arguments}")
            
            # Try different methods for executing the tool
            if try_multiple_methods:
                # Try the run method first (new standard interface)
                if hasattr(tool, "run") and callable(tool.run):
                    result = await tool.run(**arguments)
                # Fall back to execute method
                elif hasattr(tool, "execute") and callable(tool.execute):
                    result = await tool.execute(**arguments)
                # Last resort - try calling the tool directly
                else:
                    result = await tool(**arguments)
            else:
                # Call the tool through the collection
                result = await self.available_tools.execute(tool_name, **arguments)
                
            logger.info(f"Tool result: {str(result)[:200]}...")
            return result
            
        except Exception as e:
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """Handle special tool execution and state changes"""
        if not self._is_special_tool(name):
            return

        if self._should_finish_execution(name=name, result=result, **kwargs):
            # Set agent state to finished
            logger.info(f"🏁 Special tool '{name}' has completed the task!")
            self.state = AgentState.FINISHED

    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        """Determine if tool execution should finish the agent"""
        return True

    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list"""
        return name.lower() in [n.lower() for n in self.special_tool_names]
