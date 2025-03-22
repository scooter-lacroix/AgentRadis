from typing import Dict, List, Optional, Union, Any
import asyncio
import time
from functools import lru_cache

from openai import (
    APIError,
    AsyncAzureOpenAI,
    AsyncOpenAI,
    AuthenticationError,
    OpenAIError,
    RateLimitError,
)
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_random_exponential, 
    retry_if_exception_type,
    RetryError
)

from app.config import LLMConfig, config
from app.logger import logger
from app.schema import Message, TOOL_CHOICE_TYPE, ROLE_VALUES, TOOL_CHOICE_VALUES, ToolChoice, ToolCall, Function
from app.exceptions import LLMException, ModelUnavailableException

# Cache for storing model capabilities and status
MODEL_STATUS_CACHE = {}
MODEL_FALLBACKS = {
    # Mistral models
    "mistral-grand-r1-dolphin-3.0-deep-reasoning-brainstorm-45b": [
        "gpt-4-turbo",
        "mistral-large-latest",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229"
    ],
    # GPT models
    "gpt-4-turbo": [
        "gpt-4",
        "claude-3-opus-20240229",
        "mistral-large-latest"
    ],
    # Claude models
    "claude-3-opus-20240229": [
        "claude-3-sonnet-20240229",
        "gpt-4-turbo",
        "mistral-large-latest"
    ]
}

class LLM:
    """
    LLM client for interacting with various large language models with
    enhanced error handling, caching, and automated fallbacks.
    """
    
    _instances: Dict[str, "LLM"] = {}
    _model_lock = asyncio.Lock()  # Lock for model switching
    
    def __new__(
        cls, config_name: str = "default", llm_config: Optional[LLMConfig] = None
    ):
        if config_name not in cls._instances:
            instance = super().__new__(cls)
            instance.__init__(config_name, llm_config)
            cls._instances[config_name] = instance
        return cls._instances[config_name]

    def __init__(
        self, config_name: str = "default", llm_config: Optional[LLMConfig] = None
    ):
        if not hasattr(self, "client"):  # Only initialize if not already initialized
            llm_config = llm_config or config.llm
            
            # Get the config for the specified name, or use the active_llm config if not found
            if config_name in llm_config:
                model_config = llm_config.get(config_name)
            else:
                active_llm = getattr(config, 'active_llm', 'mistral')
                model_config = llm_config.get(active_llm, next(iter(llm_config.values())))
            
            # Primary configuration
            self.model = model_config.model
            self.original_model = self.model  # Store original for reset capability
            self.max_tokens = model_config.max_tokens
            self.temperature = model_config.temperature
            self.api_type = model_config.api_type
            self.api_key = model_config.api_key
            self.api_version = getattr(model_config, 'api_version', None)
            self.base_url = getattr(model_config, 'base_url', None) or model_config.api_base
            
            # Performance metrics
            self.request_count = 0
            self.total_tokens = 0
            self.last_response_time = 0
            self.fallback_attempts = 0
            self.max_fallback_attempts = 3
            
            # Initialize client based on API type
            if self.api_type == "azure":
                self.client = AsyncAzureOpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    api_version=self.api_version,
                    timeout=180.0,  # Increased timeout to prevent disconnection
                )
            else:
                self.client = AsyncOpenAI(
                    api_key=self.api_key, 
                    base_url=self.base_url,
                    timeout=180.0,  # Increased timeout to prevent disconnection
                )

    @staticmethod
    def format_messages(messages: List[Any]) -> List[dict]:
        """
        Format messages for LLM by converting them to OpenAI message format.
        
        Args:
            messages: List of messages 
            
        Returns:
            List[dict]: List of formatted messages in OpenAI format
        """
        formatted_messages = []

        for message in messages:
            if isinstance(message, dict):
                # If message is already a dict, ensure it has required fields
                if "role" not in message:
                    raise ValueError("Message dict must contain 'role' field")
                formatted_messages.append(message)
            elif isinstance(message, Message):
                # If message is a Message object, convert it to dict
                if hasattr(message, 'to_dict'):
                    formatted_messages.append(message.to_dict())
                else:
                    # Manually convert to dict if to_dict not available
                    msg_dict = {
                        "role": message.role.value if hasattr(message.role, 'value') else message.role,
                        "content": message.content
                    }
                    # Add tool_calls if present
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        msg_dict["tool_calls"] = message.tool_calls
                    formatted_messages.append(msg_dict)
            else:
                raise TypeError(f"Unsupported message type: {type(message)}")

        # Validate all messages have required fields
        for msg in formatted_messages:
            if msg["role"] not in ROLE_VALUES:
                raise ValueError(f"Invalid role: {msg['role']}")
            if "content" not in msg and "tool_calls" not in msg:
                raise ValueError(
                    "Message must contain either 'content' or 'tool_calls'"
                )

        return formatted_messages

    async def try_fallback_model(self) -> bool:
        """
        Attempt to switch to a fallback model when the current one fails.
        
        Returns:
            bool: True if fallback succeeded, False if no more fallbacks available
        """
        async with self._model_lock:
            self.fallback_attempts += 1
            
            if self.fallback_attempts > self.max_fallback_attempts:
                logger.error(f"Maximum fallback attempts ({self.max_fallback_attempts}) reached")
                return False
                
            if self.model not in MODEL_FALLBACKS:
                logger.warning(f"No fallback models defined for {self.model}")
                return False
                
            fallbacks = MODEL_FALLBACKS[self.model]
            if not fallbacks:
                return False
                
            # Try each fallback model
            for fallback in fallbacks:
                if fallback in MODEL_STATUS_CACHE and not MODEL_STATUS_CACHE[fallback]:
                    # Skip models we already know are unavailable
                    continue
                    
                logger.warning(f"⚠️ Falling back from {self.model} to {fallback}")
                self.model = fallback
                return True
                
            return False

    async def reset_to_original_model(self) -> None:
        """Reset to the original model configuration"""
        async with self._model_lock:
            self.model = self.original_model
            self.fallback_attempts = 0
            logger.info(f"Reset to original model: {self.model}")

    def _should_retry_exception(self, exception: Exception) -> bool:
        """Determine if an exception should trigger a retry"""
        if isinstance(exception, (RateLimitError, AuthenticationError)):
            # Don't retry auth errors or rate limits
            return False
            
        if isinstance(exception, (APIError, OpenAIError)):
            # Check for specific error messages that shouldn't be retried
            error_str = str(exception)
            if "model_not_found" in error_str or "Model unloaded" in error_str:
                # Update the model status cache
                MODEL_STATUS_CACHE[self.model] = False
                return False
                
        # Default to retry for other errors
        return True

    @retry(
        wait=wait_random_exponential(min=1, max=30),
        stop=stop_after_attempt(4),
        retry=retry_if_exception_type(
            (APIError, OpenAIError)
        ),
    )
    async def ask(
        self,
        messages: List[Union[dict, Message]],
        system_msgs: Optional[List[Union[dict, Message]]] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Send a prompt to the LLM and get the response with fallback support.
        
        Args:
            messages: List of conversation messages
            system_msgs: Optional system messages to prepend
            stream (bool): Whether to stream the response
            temperature (float): Sampling temperature for the response
            
        Returns:
            str: The generated response
        """
        start_time = time.time()
        self.request_count += 1
        
        try:
            # Convert messages to tuples for caching
            msgs_tuple = tuple(messages)
            sys_msgs_tuple = tuple(system_msgs) if system_msgs else None
            
            # Format system and user messages, using cache when possible
            if sys_msgs_tuple:
                formatted_sys_msgs = self.format_messages(sys_msgs_tuple)
                formatted_msgs = self.format_messages(msgs_tuple)
                all_messages = formatted_sys_msgs + formatted_msgs
            else:
                all_messages = self.format_messages(msgs_tuple)

            if not stream:
                # Non-streaming request
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=all_messages,
                    max_tokens=self.max_tokens,
                    temperature=temperature or self.temperature,
                    stream=False,
                    timeout=300,  # Add explicit timeout to prevent disconnection
                )
                
                # Track metrics
                if hasattr(response, 'usage') and response.usage:
                    self.total_tokens += response.usage.total_tokens
                    
                if not response.choices or not response.choices[0].message.content:
                    raise ValueError("Empty or invalid response from LLM")
                    
                self.last_response_time = time.time() - start_time
                return response.choices[0].message.content

            # Streaming request
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=all_messages,
                max_tokens=self.max_tokens,
                temperature=temperature or self.temperature,
                stream=True,
                timeout=300,  # Add explicit timeout to prevent disconnection
            )

            collected_messages = []
            token_count = 0
            
            async for chunk in response:
                chunk_message = chunk.choices[0].delta.content or ""
                token_count += 1  # Approximate token count
                collected_messages.append(chunk_message)
                if stream:
                    print(chunk_message, end="", flush=True)

            if stream:
                print()  # Newline after streaming
                
            full_response = "".join(collected_messages).strip()
            self.total_tokens += token_count
            
            if not full_response:
                raise ValueError("Empty response from streaming LLM")
                
            self.last_response_time = time.time() - start_time
            return full_response

        except (OpenAIError, APIError) as api_error:
            logger.error(f"API error: {api_error}")
            # Update model status cache for specific errors
            error_str = str(api_error)
            if "model_not_found" in error_str or "Model unloaded" in error_str:
                MODEL_STATUS_CACHE[self.model] = False
                
                # Try fallback if possible
                if await self.try_fallback_model():
                    logger.info(f"Retrying with fallback model: {self.model}")
                    return await self.ask(messages, system_msgs, stream, temperature)
                else:
                    raise ModelUnavailableException(f"Model unavailable and no fallbacks left: {error_str}")
            raise
            
        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            raise
            
        except RetryError as re:
            logger.error(f"Retry error: {re}")
            # Try fallback if possible
            if await self.try_fallback_model():
                logger.info(f"Retrying with fallback model: {self.model}")
                return await self.ask(messages, system_msgs, stream, temperature)
            else:
                raise LLMException(f"All retries and fallbacks failed: {re}")
                
        except Exception as e:
            logger.error(f"Unexpected error in ask: {e}")
            raise
            
        finally:
            # Record performance metrics regardless of success/failure
            self.last_response_time = time.time() - start_time

    @retry(
        wait=wait_random_exponential(min=1, max=20),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(
            (APIError, OpenAIError)
        ),
    )
    async def ask_tool(
        self,
        messages: List[Union[dict, Message]],
        system_msgs: Optional[List[Union[dict, Message]]] = None,
        timeout: int = 60,
        tools: Optional[List[dict]] = None,
        tool_choice: TOOL_CHOICE_TYPE = ToolChoice.AUTO, # type: ignore
        temperature: Optional[float] = None,
        **kwargs,
    ):
        """
        Ask LLM using functions/tools and return the response with fallback support.
        
        Args:
            messages: List of conversation messages
            system_msgs: Optional system messages to prepend
            timeout: Request timeout in seconds
            tools: List of tools to use
            tool_choice: Tool choice strategy
            temperature: Sampling temperature for the response
            **kwargs: Additional completion arguments
            
        Returns:
            ChatCompletionMessage: The model's response
        """
        start_time = time.time()
        self.request_count += 1
        
        try:
            # Validate tool_choice
            if tool_choice not in TOOL_CHOICE_VALUES:
                raise ValueError(f"Invalid tool_choice: {tool_choice}")

            # Convert messages to tuples for caching
            msgs_tuple = tuple(messages)
            sys_msgs_tuple = tuple(system_msgs) if system_msgs else None
            
            # Format messages, using cache when possible
            if sys_msgs_tuple:
                formatted_sys_msgs = self.format_messages(sys_msgs_tuple)
                formatted_msgs = self.format_messages(msgs_tuple)
                all_messages = formatted_sys_msgs + formatted_msgs
            else:
                all_messages = self.format_messages(msgs_tuple)

            # Validate tools if provided
            if tools:
                for tool in tools:
                    if not isinstance(tool, dict) or "type" not in tool:
                        raise ValueError("Each tool must be a dict with 'type' field")

            # Set up the completion request with more efficient timeout
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=all_messages,
                temperature=temperature or self.temperature,
                max_tokens=self.max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                timeout=min(timeout, 300),  # Increased timeout cap to prevent disconnection
                **kwargs,
            )

            # Track metrics
            if hasattr(response, 'usage') and response.usage:
                self.total_tokens += response.usage.total_tokens
                
            # Check if response is valid
            if not response.choices or not response.choices[0].message:
                logger.error(f"Invalid response structure: {response}")
                raise ValueError("Invalid or empty response from LLM")

            # Convert OpenAI's ChatCompletionMessage to our internal Message format
            result = response.choices[0].message
            from app.schema import Message, Role, ToolCall, Function
            
            # Create a Message object with the right attributes
            message = Message(
                role=Role.ASSISTANT,
                content=result.content or ""
            )
            
            # Process tool calls if present
            if hasattr(result, 'tool_calls') and result.tool_calls:
                tool_calls = []
                for tc in result.tool_calls:
                    # Create our internal ToolCall format
                    function_args = tc.function.arguments
                    try:
                        # Try to parse JSON if it's a string
                        if isinstance(function_args, str):
                            import json
                            function_args = json.loads(function_args)
                    except json.JSONDecodeError:
                        # Keep as string if not valid JSON
                        pass
                    
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        type="function",
                        function=Function(
                            name=tc.function.name,
                            arguments=function_args
                        )
                    ))
                message.tool_calls = tool_calls
            # Add LM Studio compatibility: check for tool calls in content
            elif result.content and '```tool_code' in result.content:
                try:
                    import re
                    import json
                    # Extract tool calls from markdown code blocks
                    tool_code_pattern = r'```tool_code\s+(.*?)\s*```'
                    matches = re.findall(tool_code_pattern, result.content, re.DOTALL)
                    
                    if matches:
                        tool_calls = []
                        for i, match in enumerate(matches):
                            # Try to parse function name and arguments
                            fn_match = re.match(r'(\w+)\((.*?)\)', match.strip(), re.DOTALL)
                            if fn_match:
                                fn_name, args_str = fn_match.groups()
                                # Handle different formats of arguments
                                try:
                                    args_str = args_str.strip()
                                    if args_str.startswith("{") and args_str.endswith("}"):
                                        # JSON object format
                                        args = json.loads(args_str)
                                    else:
                                        # Key=value format
                                        args = {}
                                        for arg in re.findall(r'(\w+)=(?:"([^"]*?)"|\'([^\']*?)\'|([^,\s]+))', args_str):
                                            key = arg[0]
                                            value = arg[1] or arg[2] or arg[3]
                                            args[key] = value
                                except Exception as e:
                                    logger.warning(f"Error parsing tool arguments: {e}")
                                    args = {"query": args_str}
                                    
                                tool_calls.append(ToolCall(
                                    id=f"call_{i}_{int(time.time())}",
                                    type="function",
                                    function=Function(
                                        name=fn_name,
                                        arguments=args
                                    )
                                ))
                        
                        if tool_calls:
                            message.tool_calls = tool_calls
                            # Clean up the content to remove tool calls
                            message.content = re.sub(tool_code_pattern, '', result.content).strip()
                            logger.info(f"Extracted {len(tool_calls)} tool calls from content")
                except Exception as e:
                    logger.error(f"Error extracting tool calls from content: {e}")
            # Add another LM Studio fallback pattern with <function_call> syntax
            elif result.content and '<function_call>' in result.content:
                try:
                    import re
                    import json
                    # Extract function calls using <function_call> tags
                    function_call_pattern = r'<function_call>\s*(.*?)\s*</function_call>'
                    matches = re.findall(function_call_pattern, result.content, re.DOTALL)
                    
                    if matches:
                        tool_calls = []
                        for i, match in enumerate(matches):
                            try:
                                # Try to parse as JSON
                                fn_data = json.loads(match.strip())
                                fn_name = fn_data.get('name', '')
                                args = fn_data.get('arguments', {})
                                
                                # Convert string arguments to dict if needed
                                if isinstance(args, str):
                                    try:
                                        args = json.loads(args)
                                    except:
                                        args = {"text": args}
                                
                                tool_calls.append(ToolCall(
                                    id=f"call_{i}_{int(time.time())}",
                                    type="function",
                                    function=Function(
                                        name=fn_name,
                                        arguments=args
                                    )
                                ))
                            except json.JSONDecodeError:
                                # Try alternate format: name(args)
                                fn_match = re.match(r'(\w+)\((.*?)\)', match.strip(), re.DOTALL)
                                if fn_match:
                                    fn_name, args_str = fn_match.groups()
                                    try:
                                        if args_str.startswith("{") and args_str.endswith("}"):
                                            args = json.loads(args_str)
                                        else:
                                            args = {"query": args_str.strip('"\'').strip()}
                                    except:
                                        args = {"query": args_str.strip()}
                                        
                                    tool_calls.append(ToolCall(
                                        id=f"call_{i}_{int(time.time())}",
                                        type="function",
                                        function=Function(
                                            name=fn_name,
                                            arguments=args
                                        )
                                    ))
                        
                        if tool_calls:
                            message.tool_calls = tool_calls
                            # Clean up the content to remove function calls
                            message.content = re.sub(function_call_pattern, '', result.content).strip()
                            logger.info(f"Extracted {len(tool_calls)} tool calls from <function_call> tags")
                except Exception as e:
                    logger.error(f"Error extracting function calls: {e}")
                
            self.last_response_time = time.time() - start_time
            return message

        except (OpenAIError, APIError) as api_error:
            logger.error(f"API error: {api_error}")
            # Update model status cache for specific errors
            error_str = str(api_error)
            if "model_not_found" in error_str or "Model unloaded" in error_str:
                MODEL_STATUS_CACHE[self.model] = False
                
                # Try fallback if possible
                if await self.try_fallback_model():
                    logger.info(f"Retrying with fallback model: {self.model}")
                    return await self.ask_tool(
                        messages, system_msgs, timeout, tools, tool_choice, temperature, **kwargs
                    )
                else:
                    raise ModelUnavailableException(f"Model unavailable and no fallbacks left: {error_str}")
            raise
            
        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            raise
            
        except RetryError as re:
            logger.error(f"Retry error: {re}")
            # Try fallback if possible
            if await self.try_fallback_model():
                logger.info(f"Retrying with fallback model: {self.model}")
                return await self.ask_tool(
                    messages, system_msgs, timeout, tools, tool_choice, temperature, **kwargs
                )
            else:
                raise LLMException(f"All retries and fallbacks failed: {re}")
                
        except Exception as e:
            logger.error(f"Unexpected error in ask_tool: {e}")
            raise
            
        finally:
            # Record performance metrics regardless of success/failure
            self.last_response_time = time.time() - start_time

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the LLM client"""
        return {
            "model": self.model,
            "original_model": self.original_model,
            "fallback_attempts": self.fallback_attempts,
            "request_count": self.request_count,
            "total_tokens": self.total_tokens,
            "average_response_time": self.last_response_time,
            "available_fallbacks": MODEL_FALLBACKS.get(self.model, [])
        }

    async def test_llm_connection(self, api_base: str = None) -> Dict[str, Any]:
        """
        Test connection to the LLM API.
        
        Args:
            api_base: Optional API base URL to test
            
        Returns:
            Dict with success status and error message if any
        """
        try:
            # Create a test client
            client = AsyncOpenAI(
                base_url=api_base or "http://127.0.0.1:1234/v1",
                api_key="not-needed"  # Local API doesn't need a key
            )
            
            # Try to list models as a simple test
            await client.models.list()
            
            return {
                "success": True,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error testing LLM connection: {e}")
            return {
                "success": False,
                "error": str(e)
            }

def create_llm(config_name: str = "default") -> LLM:
    """Factory function to create an LLM instance with given configuration"""
    return LLM(config_name=config_name)
