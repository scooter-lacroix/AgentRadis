"""
LM Studio Client Implementation

A standalone module for interacting with LM Studio models that doesn't depend
on the full app structure.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field
from enum import Enum
from uuid import uuid4

# Configure logging
logging.basicConfig(level=logging.INFO, 
                 format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check if lmstudio SDK is available
try:
    import lmstudio
    LMSTUDIO_SDK_AVAILABLE = True
    logger.info("lmstudio-python SDK found")
except ImportError:
    LMSTUDIO_SDK_AVAILABLE = False
    logger.warning("lmstudio-python SDK not found. Falling back to OpenAI-compatible API.")

# Import OpenAI for API access
try:
    from openai import OpenAI
except ImportError:
    logger.error("OpenAI package not found. Please install it with: pip install openai")
    raise


# Define basic data models
class Function(BaseModel):
    """Function definition for a tool call."""
    name: str = Field(..., description="Name of the function")
    arguments: Union[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Arguments for the function"
    )


class ToolCall(BaseModel):
    """Tool call request - compatible with OpenAI API format."""
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this tool call",
    )
    type: str = Field(default="function", description="Type of tool call")
    function: Dict[str, Any] = Field(..., description="Function to call")


class Message(BaseModel):
    """A message in a conversation."""
    role: str = Field(..., description="Role of the message sender")
    content: Optional[str] = Field(default=None, description="Content of the message")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Tool calls requested by the assistant"
    )
    tool_call_id: Optional[str] = Field(
        default=None, description="ID of the tool call this message is responding to"
    )
    name: Optional[str] = Field(
        default=None, description="Name of the assistant or tool"
    )


class ToolResponse(BaseModel):
    """Response from a tool call."""
    call_id: str = Field(..., description="ID of the tool call this is responding to")
    tool_name: str = Field(..., description="Name of the tool that was called")
    success: bool = Field(..., description="Whether the tool call succeeded")
    result: Union[str, Dict[str, Any]] = Field(..., description="Result of the tool call")
    error: Optional[str] = Field(default=None, description="Error message if the tool call failed")


class LMStudioClient:
    """
    Client for interacting with LM Studio models using either the OpenAI-compatible API
    or the native lmstudio-python SDK.
    """

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize the LM Studio client with configuration.
        
        Args:
            config_dict: Optional configuration dictionary with settings.
        """
        # Default configuration
        self.config = {
            "api_type": "local",
            "model": "", 
            "api_base": "http://127.0.0.1:1234",
            "api_key": "lm-studio",
            "timeout": 60
        }
        
        if config_dict:
            self.config.update(config_dict)
        
        # Extract configuration values
        self.api_type = self.config.get("api_type", "local")
        self.model = self.config.get("model", "")
        self.api_base = self.config.get("api_base", "http://127.0.0.1:1234")
        self.api_key = self.config.get("api_key", "lm-studio")
        self.timeout = self.config.get("timeout", 60)
        
        # Initialize OpenAI client
        logger.info(f"Initializing OpenAI client with base_url={self.api_base}")
        try:
            self._openai_client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                timeout=self.timeout
            )
            # Test API connectivity and model availability
            models_response = self._openai_client.models.list()
            if not models_response:
                logger.warning("No models available from LM Studio API")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self._openai_client = None
        
        # Initialize LM Studio SDK client (if available)
        self._lmstudio_client = None
        self._initialize_sdk_client()
    
    def _initialize_sdk_client(self):
        """Initialize the LM Studio SDK client."""
        if not LMSTUDIO_SDK_AVAILABLE:
            return
            
        try:
            # The correct parameter is api_host, not api_url or api_base
            api_host = self.api_base.rstrip('/')  # Remove trailing slash
            logger.info(f"Initializing LM Studio SDK client with api_host={api_host}")
            
            self._lmstudio_client = lmstudio.Client(
                api_host=api_host
            )
            
            # Check if model loading is needed
            if self.model:
                try:
                    # First check if the model is already loaded
                    loaded_models = self._lmstudio_client.list_loaded_models()
                    logger.info(f"Currently loaded models: {loaded_models}")
                    
                    if self.model not in [m['name'] for m in loaded_models]:
                        # Then check if it's available for download
                        available_models = self._lmstudio_client.list_downloaded_models()
                        logger.info(f"Available models: {available_models}")
                        
                        # Load the model if needed
                        self._lmstudio_client.llm.load_model(self.model)
                        logger.info(f"Loaded model: {self.model}")
                except Exception as model_err:
                    logger.warning(f"Failed to load model {self.model}: {model_err}")
        except Exception as e:
            logger.warning(f"Failed to initialize LM Studio SDK client: {e}")
            self._lmstudio_client = None
    
    def use_sdk(self) -> bool:
        """
        Determine whether to use the native SDK or fallback to OpenAI API.
        
        Returns:
            bool: True if SDK should be used, False otherwise.
        """
        return LMSTUDIO_SDK_AVAILABLE and self._lmstudio_client is not None
    
    def create_chat_completion(
        self, 
        messages: List[Message], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Tuple[str, Optional[List[ToolCall]]]:
        """
        Create a chat completion using either the SDK or OpenAI-compatible API.
        
        Args:
            messages: List of message objects with role and content
            tools: Optional list of tools available to the model
            **kwargs: Additional parameters to pass to the underlying API
        
        Returns:
            Tuple[str, Optional[List[ToolCall]]]: The model's response text and any tool calls
        """
        if self.use_sdk():
            return self._create_chat_completion_sdk(messages, tools, **kwargs)
        else:
            return self._create_chat_completion_openai(messages, tools, **kwargs)
    
    def _create_chat_completion_sdk(
        self, 
        messages: List[Message], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Tuple[str, Optional[List[ToolCall]]]:
        """
        Create a chat completion using the native lmstudio-python SDK.
        
        Args:
            messages: List of message objects with role and content
            tools: Optional list of tools available to the model
            **kwargs: Additional parameters to pass to the SDK
        
        Returns:
            Tuple[str, Optional[List[ToolCall]]]: The model's response text and any tool calls
        """
        try:
            # Extract the last user message as the prompt
            prompt = ""
            for msg in reversed(messages):
                if msg.role == "user" and msg.content:
                    prompt = msg.content
                    break
            
            if not prompt:
                # If no user message found, use the last message or an empty string
                if messages and messages[-1].content:
                    prompt = messages[-1].content
                else:
                    prompt = ""
            
            logger.info(f"Generating completion with prompt: {prompt[:50]}...")
            
            # Use the llm session to create the completion
            response = self._lmstudio_client.llm.generate(
                prompt=prompt,
                **kwargs
            )
            
            logger.info(f"Got SDK response: {response.text[:50]}...")
            return response.text, None
                
        except Exception as e:
            logger.error(f"Error in LM Studio SDK chat completion: {e}")
            # Fallback to OpenAI API
            logger.info("Falling back to OpenAI-compatible API")
            return self._create_chat_completion_openai(messages, tools, **kwargs)
    
    def _create_chat_completion_openai(
        self, 
        messages: List[Message], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Tuple[str, Optional[List[ToolCall]]]:
        """
        Create a chat completion using the OpenAI-compatible API.
        
        Args:
            messages: List of message objects with role and content
            tools: Optional list of tools available to the model
            **kwargs: Additional parameters to pass to the API
        
        Returns:
            Tuple[str, Optional[List[ToolCall]]]: The model's response text and any tool calls
        """
        try:
            # Convert messages to OpenAI format
            openai_messages = [
                {"role": msg.role, "content": msg.content if msg.content else ""} 
                for msg in messages
            ]
            
            # Set up request parameters
            request_params = {
                "model": kwargs.get("model", self.model) or "local-model",
                "messages": openai_messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 1500),
            }
            
            # Add tools if provided
            if tools:
                request_params["tools"] = tools
            
            # Add any additional kwargs
            for key, value in kwargs.items():
                if key not in ["model", "temperature", "max_tokens"]:
                    request_params[key] = value
            
            logger.info(f"Making OpenAI API request with params: {request_params}")
            
            # Check if client is initialized
            if not self._openai_client:
                logger.error("OpenAI client not initialized")
                return "Error: Language model service is not available.", None

            # Make API call to v1 endpoint
            try:
                response = self._openai_client.chat.completions.create(**request_params)
            except Exception as e:
                logger.error(f"API request failed: {e}")
                if "model not found" in str(e).lower():
                    return "Error: The requested model is not currently loaded in LM Studio.", None
                return "Error: Failed to communicate with the language model service.", None
            
            # Check if the model wants to use a tool
            if response.choices and response.choices[0].message.tool_calls:
                # Convert to ToolCall format
                tool_calls = []
                for tc in response.choices[0].message.tool_calls:
                    try:
                        function_data = {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                        
                        tool_call = ToolCall(
                            id=tc.id,
                            type="function",
                            function=function_data
                        )
                        tool_calls.append(tool_call)
                    except Exception as e:
                        logger.error(f"Error processing tool call: {e}")
                
                logger.info(f"Received {len(tool_calls)} tool calls")
                return "", tool_calls
            
            # If no tool calls, return the content
            content = ""
            if response.choices:
                message = response.choices[0].message
                if hasattr(message, "content") and message.content is not None:
                    content = message.content
                else:
                    logger.warning("Received empty content in response")
            
            logger.info(f"Received content: {content[:50]}...")
            return content, None
            
        except Exception as e:
            logger.error(f"Error in OpenAI-compatible chat completion: {e}")
            # Return empty string and None to prevent raising exceptions
            return "I encountered an error connecting to the language model service.", None


# Simple usage example
if __name__ == "__main__":
    client = LMStudioClient()
    print(f"API Base: {client.api_base}")
    print(f"Using SDK: {client.use_sdk()}")
    
    # Try a simple completion
    messages = [Message(role="user", content="Hello, how are you today?")]
    response, tool_calls = client.create_chat_completion(messages)
    
    print(f"\nResponse: {response}")
    if tool_calls:
        for tc in tool_calls:
            print(f"Tool Call: {tc.function['name']}({tc.function['arguments']})")
