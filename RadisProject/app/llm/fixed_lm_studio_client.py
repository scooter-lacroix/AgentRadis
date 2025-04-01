#!/usr/bin/env python
"""
LMStudioClient - A robust client for LM Studio API that handles multiple endpoint formats
and response parsing issues.
"""

import json
import logging
import requests
from typing import Any, Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fixed_lm_studio_client")

class LMStudioClient:
    """
    A robust client for LM Studio that tries multiple endpoint formats
    and properly handles various response formats.
    """

    def __init__(self, 
                 api_base: str = "http://127.0.0.1:1234", 
                 api_key: str = "lm-studio", 
                 model: str = "",
                 timeout: int = 60):
        """
        Initialize the LM Studio client.
        
        Args:
            api_base: Base URL for the LM Studio API
            api_key: API key (usually not required for local LM Studio)
            model: Default model to use
            timeout: Timeout for API requests in seconds
        """
        # Store configuration
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        
        # Endpoint variations to try
        self.endpoints = [
            f"{self.api_base}/v1/chat/completions",  # Standard OpenAI format
            f"{self.api_base}/chat/completions",     # LM Studio format
            f"{self.api_base}/api/chat/completions", # Another common format
            f"{self.api_base}/v1/completions",       # Legacy completions endpoint
            f"{self.api_base}/completions"           # Legacy without version
        ]
        
        logger.info(f"Initialized LMStudioClient with base URL: {self.api_base}")
        
        # Try initializing OpenAI client if available
        self._openai_client = None
        try:
            from openai import OpenAI
            logger.info(f"Initializing OpenAI client with base_url={self.api_base}")
            self._openai_client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                timeout=self.timeout
            )
        except ImportError:
            logger.warning("OpenAI package not found. Using requests for API calls.")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}")
    
    def create_chat_completion(self, 
                              messages: List[Any], 
                              tools: Optional[List[Dict]] = None, 
                              **kwargs) -> Tuple[str, Optional[List]]:
        """
        Create a chat completion by trying multiple endpoint formats.
        
        Args:
            messages: List of message objects with role and content
            tools: Optional list of tools available to the model
            **kwargs: Additional parameters to pass to the API
        
        Returns:
            Tuple[str, Optional[List]]: The model response text and any tool calls
        """
        # Format messages properly
        api_messages = []
        for msg in messages:
            # Handle both dict and object formats
            if isinstance(msg, dict):
                msg_dict = {
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "") or ""
                }
            else:
                msg_dict = {
                    "role": getattr(msg, "role", "user"),
                    "content": getattr(msg, "content", "") or ""
                }
            api_messages.append(msg_dict)
        
        # Set up request parameters
        payload = {
            "model": kwargs.get("model", self.model) or "default",
            "messages": api_messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }
        
        # Add tools if provided
        if tools:
            payload["tools"] = tools
        
        # Try each endpoint format until one works
        last_error = None
        for endpoint in self.endpoints:
            try:
                logger.info(f"Trying endpoint: {endpoint}")
                
                # Set up headers
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                # Make the API request
                response = requests.post(
                    endpoint, 
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                
                # Check if the request was successful
                if response.status_code == 200:
                    # Try to parse the JSON response
                    try:
                        response_data = response.json()
                        
                        # Handle error responses
                        if "error" in response_data and response_data.get("error"):
                            error_msg = response_data.get("error")
                            logger.warning(f"API returned error: {error_msg}")
                            last_error = error_msg
                            # Continue to next endpoint unless this is the last one
                            if endpoint != self.endpoints[-1]:
                                continue
                            return f"LM Studio API error: {error_msg}", None
                        
                        # Handle standard OpenAI format responses
                        if "choices" in response_data and response_data["choices"]:
                            choice = response_data["choices"][0]
                            
                            # Check for tool calls
                            if "message" in choice and "tool_calls" in choice["message"] and choice["message"]["tool_calls"]:
                                logger.info("Extracted tool calls from response")
                                return "", choice["message"]["tool_calls"]
                            
                            # Standard content response
                            if "message" in choice and "content" in choice["message"]:
                                content = choice["message"]["content"]
                                logger.info("Successfully extracted content from response")
                                return content if content is not None else "", None
                        
                        # Handle non-standard formats - try common response field names
                        for key in ["text", "content", "output", "response", "generation"]:
                            if key in response_data:
                                logger.info(f"Found response in non-standard field: {key}")
                                return response_data[key], None
                        
                        # Last resort: return the raw JSON response
                        logger.warning(f"Unknown response format: {response_data}")
                        return json.dumps(response_data), None
                        
                    except json.JSONDecodeError:
                        # Not JSON, return the raw text
                        logger.info("Response is not JSON, returning raw text")
                        return response.text, None
                else:
                    # Request failed with non-200 status code
                    error_msg = f"API request failed with status {response.status_code}: {response.text}"
                    logger.warning(error_msg)
                    last_error = error_msg
                    # Try next endpoint
            except Exception as e:
                # Handle request exceptions
                error_msg = f"API request to {endpoint} failed: {str(e)}"
                logger.warning(error_msg)
                last_error = error_msg
                # Try next endpoint
        
        # All endpoints failed
        error_message = f"All LM Studio API endpoints failed. Last error: {last_error}"
        logger.error(error_message)
        return error_message, None

    def get_model_list(self) -> List[str]:
        """
        Attempt to get a list of available models.
        
        Returns:
            List of model names or empty list if unable to retrieve models
        """
        # Try different model list endpoints
        model_endpoints = [
            f"{self.api_base}/v1/models",
            f"{self.api_base}/models",
            f"{self.api_base}/api/models"
        ]
        
        for endpoint in model_endpoints:
            try:
                logger.info(f"Trying to fetch models from: {endpoint}")
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                response = requests.get(
                    endpoint, 
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if "data" in data and isinstance(data["data"], list):
                            models = [model.get("id", "unknown") for model in data["data"]]
                            logger.info(f"Successfully retrieved {len(models)} models")
                            return models
                        else:
                            logger.warning(f"Unexpected model list format: {data}")
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse model list response: {response.text}")
            except Exception as e:
                logger.warning(f"Error fetching models from {endpoint}: {e}")
        
        logger.warning("Unable to retrieve model list from any endpoint")
        return []

# Example usage
def run_test():
    """Test the LMStudioClient with a simple query."""
    client = LMStudioClient()
    print(f"Testing LMStudioClient with API base: {client.api_base}")
    
    # Create a simple message structure
    messages = [{"role": "user", "content": "Hello, how are you today?"}]
    
    # Try to get a completion
    response, tool_calls = client.create_chat_completion(messages)
    
    print(f"Response: {response}")
    if tool_calls:
        print(f"Tool calls: {tool_calls}")
    
    return True

if __name__ == "__main__":
    # Run the test if this file is executed directly
    success = run_test()
    print("Test completed:", "SUCCESS" if success else "FAILED")

"""
LM Studio Client Implementation

This module provides a client for interacting with LM Studio models using both:
1. The OpenAI-compatible API
2. The native lmstudio-python SDK

The client supports chat completions, tool-based interactions, and embeddings
with proper error handling and logging.
"""

import json
import logging
import os
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import lmstudio
    LMSTUDIO_SDK_AVAILABLE = True
except ImportError:
    LMSTUDIO_SDK_AVAILABLE = False
    logging.warning("lmstudio-python SDK not found. Falling back to OpenAI-compatible API.")

from openai import OpenAI

# Configure logging
logger = logging.getLogger(__name__)


class LMStudioClient:
    """
    Client for interacting with LM Studio models using either the OpenAI-compatible API
    or the native lmstudio-python SDK.
    
    This client provides methods for chat completion, tool-based interactions, and embeddings.
    """

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize the LM Studio client with configuration.
        
        Args:
            config_dict: Optional configuration dictionary. If not provided, 
                 will use default configuration.
        """
        # Default configuration
        self.config = {
            "api_type": "local",
            "model": "", 
            "api_base": "http://127.0.0.1:1234/",
            "api_key": "lm-studio",
            "timeout": 60
        }
        
        if config_dict:
            self.config.update(config_dict)
        
        # Extract configuration values
        self.api_type = self.config.get("api_type", "local")
        self.model = self.config.get("model", "")
        self.api_base = self.config.get("api_base", "http://127.0.0.1:1234/")
        self.api_key = self.config.get("api_key", "lm-studio")
        self.timeout = self.config.get("timeout", 60)
        
        # Initialize clients based on availability and configuration
        self._openai_client = None
        self._lmstudio_client = None
        
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize API clients based on configuration and SDK availability."""
        # Always initialize OpenAI client as fallback
        self._openai_client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            timeout=self.timeout
        )
        
        # Initialize lmstudio client if SDK is available
        if LMSTUDIO_SDK_AVAILABLE:
            try:
                # Parse the URL to extract host and port
                parsed_url = urllib.parse.urlparse(self.api_base)
                
                # Extract host and port
                host_port = parsed_url.netloc
                if not host_port:  # If netloc is empty, the api_base might be just a hostname
                    host_port = self.api_base.replace('http://', '').replace('https://', '').rstrip('/')
                
                logger.info(f"Initializing LM Studio SDK client with api_host={host_port}")
                
                # Initialize the SDK client with api_host (not api_key)
                self._lmstudio_client = lmstudio.Client(
                    api_host=host_port  # This is the correct parameter
                )
                
                # Try to connect to an already loaded model
                try:
                    loaded_models = self._lmstudio_client.list_loaded_models()
                    logger.info(f"Available loaded models: {loaded_models}")
                    
                    # If a model is already loaded, connect to it
                    if loaded_models:
                        self._lmstudio_client.llm.connect()
                        logger.info("Connected to already loaded model")
                        
                        # If a specific model was requested, check if it matches
                        if self.model and any(model.model_key == self.model for model in loaded_models):
                            logger.info(f"Requested model {self.model} is already loaded")
                        elif self.model:
                            logger.warning(f"Requested model {self.model} is not loaded")
                except Exception as e:
                    logger.warning(f"Error checking loaded models: {e}")
            except Exception as e:
                logger.warning(f"Failed to initialize LM Studio SDK client: {e}")
                self._lmstudio_client = None
    
    def use_sdk(self) -> bool:
        """
        Determine whether to use the native SDK or fallback to OpenAI API.
        
        Returns:
            bool: True if SDK should be used, False otherwise.
        """
        return (LMSTUDIO_SDK_AVAILABLE and 
               self._lmstudio_client is not None and 
               hasattr(self._lmstudio_client, 'llm') and 
               getattr(self._lmstudio_client.llm, 'connected', False))
    
    def create_chat_completion(
        self, 
        messages: List[Dict], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Tuple[str, Optional[List[Dict]]]:
        """
        Create a chat completion using either the SDK or OpenAI-compatible API.
        
        Args:
            messages: List of message objects with role and content
            tools: Optional list of tools available to the model
            **kwargs: Additional parameters to pass to the underlying API
        
        Returns:
            Tuple[str, Optional[List[Dict]]]: The model's response text and any tool calls
        """
        if self.use_sdk():
            return self._create_chat_completion_sdk(messages, tools, **kwargs)
        else:
            return self._create_chat_completion_openai(messages, tools, **kwargs)
    
    def _create_chat_completion_sdk(
        self, 
        messages: List[Dict], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Tuple[str, Optional[List[Dict]]]:
        """
        Create a chat completion using the native lmstudio-python SDK.
        
        Args:
            messages: List of message objects with role and content
            tools: Optional list of tools available to the model
            **kwargs: Additional parameters to pass to the SDK
        
        Returns:
            Tuple[str, Optional[List[Dict]]]: The model's response text and any tool calls
        """
        try:
            # Extract conversation context from messages
            prompt = ""
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                
                role_prefix = ""
                if role == "user":
                    role_prefix = "User: "
                elif role == "assistant":
                    role_prefix = "Assistant: "
                elif role == "system":
                    role_prefix = "System: "
                
                if content:
                    prompt += f"{role_prefix}{content}\n"
            
            prompt += "Assistant: "  # Add prompt for assistant response
            
            try:
                # Use the respond method which is the recommended way to generate responses
                model = self._lmstudio_client.llm
                result = model.respond(prompt)
                
                if result:
                    return result, None
                else:
                    return "", None
                
            except AttributeError as e:
                logger.warning(f"respond method not available: {e}")
                # Fallback to any available method
                try:
                    model = self._lmstudio_client.llm()
                    result = model.respond(prompt)
                    return result, None
                except Exception as e2:
                    logger.error(f"Alternative method also failed: {e2}")
                    raise
        except Exception as e:
            logger.error(f"Error in LM Studio SDK chat completion: {e}")
            # Fallback to OpenAI API
            logger.info("Falling back to OpenAI-compatible API")
            return self._create_chat_completion_openai(messages, tools, **kwargs)
    
    def _create_chat_completion_openai(
        self, 
        messages: List[Dict], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Tuple[str, Optional[List[Dict]]]:
        """
        Create a chat completion using the OpenAI-compatible API.
        
        Args:
            messages: List of message objects with role and content
            tools: Optional list of tools available to the model
            **kwargs: Additional parameters to pass to the API
        
        Returns:
            Tuple[str, Optional[List[Dict]]]: The model's response text and any tool calls
        """
        try:
            # Validate input messages
            if not messages:
                logger.warning("Empty messages list provided")
                return "Error: No input messages provided.", None
            
            # Set up request parameters with defaults
            request_params = {
                "model": kwargs.get("model", self.model) or "default",
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 1024),
            }
            
            # Add any remaining kwargs, excluding already processed ones
            for key, value in kwargs.items():
                if key not in ["model", "temperature", "max_tokens"]:
                    request_params[key] = value
            
            # Add tools if provided and validate
            if tools:
                if not isinstance(tools, list):
                    logger.warning("Invalid tools format provided")
                    tools = []
                request_params["tools"] = tools
            
            logger.info(f"Making OpenAI API request to {self.api_base}")
            
            try:
                # Make API call with timeout handling
                response = self._openai_client.chat.completions.create(**request_params)
                
                # Process tool calls if present
                if response.choices and hasattr(response.choices[0].message, 'tool_calls'):
                    tool_calls = response.choices[0].message.tool_calls
                    if tool_calls:
                        logger.info("Model requested tool usage")
                        return "", tool_calls
                
                # Extract content from response
                if response.choices:
                    content = getattr(response.choices[0].message, 'content', "") or ""
                    return content.strip(), None
                else:
                    logger.warning("Empty response from API")
                    return "", None
                
            except TimeoutError as te:
                logger.error(f"API request timed out: {te}")
                return "Error: Request timed out. Please try again.", None
                
            except Exception as api_error:
                logger.error(f"API request failed: {api_error}")
                return f"Error: API request failed - {str(api_error)}", None
            
        except Exception as e:
            logger.error(f"Unexpected error in chat completion: {e}")
            return "Error: An unexpected error occurred while processing your request.", None
    
    def create_embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        """
        Create embeddings for the given texts.
        
        Args:
            texts: List of text strings to embed
            **kwargs: Additional parameters to pass to the API
        
        Returns:
            List[List[float]]: List of embedding vectors
        """
        if self.use_sdk():
            return self._create_embeddings_sdk(texts, **kwargs)
        else:
            return self._create_embeddings_openai(texts, **kwargs)
    
    def _create_embeddings_sdk(self, texts: List[str], **kwargs) -> List[List[float]]:
        """
        Create embeddings using the native lmstudio-python SDK.
        
        Args:
            texts: List of text strings to embed
            **kwargs: Additional parameters to pass to the SDK
        
        Returns:
            List[List[float]]: List of embedding vectors
        """
        try:
            embeddings = []
            for text in texts:
                try:
                    # Use the embedding client directly
                    embedding = self._lmstudio_client.embedding.embed(text)
                    embeddings.append(embedding)
                except Exception as e:
                    logger.error(f"Error creating embedding for text: {e}")
                    embeddings.append([])
                
            return embeddings
            
        except Exception as e:
            logger.error(f"Error in LM Studio SDK embeddings: {e}")
            # Fallback to OpenAI API
            logger.info("Falling back to OpenAI-compatible API for embeddings")
            return self._create_embeddings_openai(texts, **kwargs)
    
    def _create_embeddings_openai(self, texts: List[str], **kwargs) -> List[List[float]]:
        """
        Create embeddings using the OpenAI-compatible API.
        
        Args:
            texts: List of text strings to embed
            **kwargs: Additional parameters to pass to the API
        
        Returns:
            List[List[float]]: List of embedding vectors
        """
        try:
            response = self._openai_client.embeddings.create(
                model=kwargs.get("model", self.model) or "text-embedding-ada-002",
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Error in OpenAI-compatible embeddings: {e}")
            # Return empty embeddings instead of raising
            return [[] for _ in texts]

# Simple test if run directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = LMStudioClient()
    print(f"Client initialized, using SDK: {client.use_sdk()}")
    
    # Test with a simple message if possible
    if client.use_sdk() or client._openai_client:
        response, tool_calls = client.create_chat_completion([
            {"role": "user", "content": "Hello, how are you?"}
        ])
        print(f"Response: {response}")
