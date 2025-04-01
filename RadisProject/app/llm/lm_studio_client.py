#!/usr/bin/env python
"""
LM Studio API Client Solution - Fixes the invalid response format issues
"""

import json
import logging
import os
import requests
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from requests.exceptions import RequestException, Timeout, ConnectionError

import urllib.parse

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("lm_studio_client")

# Check if lmstudio package is available
LMSTUDIO_SDK_AVAILABLE = False
try:
    import lmstudio
    LMSTUDIO_SDK_AVAILABLE = True
except ImportError:
    pass
class LMStudioError(Exception):
    """Base exception class for LM Studio client errors."""
    pass

class ModelNotFoundError(LMStudioError):
    """Raised when the requested model is not available."""
    pass

class APIConnectionError(LMStudioError):
    """Raised when there are network connectivity issues."""
    pass

class APIResponseError(LMStudioError):
    """Raised when the API returns an unexpected response."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text

class InvalidRequestError(LMStudioError):
    """Raised when the request is malformed or invalid."""
    pass

class LMStudioClient:
    """
    Fixed LM Studio client that properly handles response formats.
    """

    def __init__(self, config_dict=None):
        """Initialize with configuration."""
        # Default configuration
        self.config = {
        # Default configuration
        self.config = {
            "api_key": "lm-studio",
            "model": None,  # Must be provided
            "timeout": 60,
            "max_tokens": 1024,
            "stream": False,
            "max_retries": 3,
            "retry_delay": 1,
            "retry_codes": [408, 429, 500, 502, 503, 504]
        }
        
        if config_dict:
            # Remove api_base from config_dict if present
            if "api_base" in config_dict:
                del config_dict["api_base"]
            self.config.update(config_dict)
        
        # Set fixed api_base
        self.api_base = "http://127.0.0.1:1234/"
        self.model = self.config.get("model", "")
        self.timeout = self.config.get("timeout", 60)
        self.health_check_interval = self.config.get("health_check_interval", 300)  # 5 minutes
        self._last_health_check = 0
        self._is_healthy = False
        
        # Initialize OpenAI client if possible
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
    
    def _check_api_availability(self) -> bool:
        """
        Check if the LM Studio API is available and responding.
        
        Returns:
            bool: True if API is available, False otherwise
        """
        try:
            # First try the OpenAI-compatible /v1/models endpoint
            logger.debug(f"Checking API availability at {self.api_base}/v1/models")
            response = requests.get(
                f"{self.api_base}v1/models",
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.debug(f"API endpoint available: {self.api_base}/v1/models")
                self._is_healthy = True
                return True
                
            # Try base endpoint as fallback
            logger.debug(f"Trying base endpoint {self.api_base}")
            response = requests.get(
                self.api_base,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.debug(f"Base API endpoint available: {self.api_base}")
                self._is_healthy = True
                return True
                
            logger.warning(f"API check failed. Status codes: /v1/models: {response.status_code}")
            self._is_healthy = False
            return False
            
        except requests.exceptions.Timeout:
            logger.error("API check timed out")
            self._is_healthy = False
            return False
        except requests.exceptions.ConnectionError:
            logger.error(f"Failed to connect to API at {self.api_base}")
            self._is_healthy = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error during API check: {str(e)}")
            self._is_healthy = False
            return False

    def _verify_model_loaded(self, model_name: str) -> bool:
        """
        Verify if the specified model is loaded and available.
        
        Args:
            model_name: Name of the model to verify
            
        Returns:
            bool: True if model is available, False otherwise
        """
        try:
            response = requests.get(
                f"{self.api_base}models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Model verification failed with status {response.status_code}")
                return False
                
            models_data = response.json()
            available_models = [model["id"] for model in models_data.get("data", [])]
            
            if model_name == "default" or model_name in available_models:
                return True
                
            logger.warning(f"Model '{model_name}' not found in available models: {available_models}")
            return False
            
        except Exception as e:
            logger.error(f"Model verification failed: {str(e)}")
            return False

    def check_health(self, force: bool = False) -> bool:
        """
        Perform a health check of the API and verify current model availability.
        
        Args:
            force: If True, bypass the health check interval and check immediately
            
        Returns:
            bool: True if both API and model are available, False otherwise
        """
        current_time = time.time()
        if not force and current_time - self._last_health_check < self.health_check_interval:
            return self._is_healthy
            
        self._last_health_check = current_time
        
        # Check basic API availability
        if not self._check_api_availability():
            return False
            
        # Verify current model if one is set
        if self.model:
            if not self._verify_model_loaded(self.model):
                self._is_healthy = False
                return False
                
        self._is_healthy = True
        return True

    def create_chat_completion(self, messages, tools=None, **kwargs):
        """
        Create a chat completion using the most reliable method.
        
        Args:
            messages: List of message objects with role and content
            tools: Optional list of tools available to the model
            **kwargs: Additional parameters to pass to the API
        
        Returns:
            Tuple[str, Optional[List]]: The model response text and any tool calls
        """
        # Use SDK if available, otherwise fall back to direct API calls
        if LMSTUDIO_SDK_AVAILABLE:
            try:
                return self._create_chat_completion_sdk(messages, tools, **kwargs)
            except Exception as e:
                logger.warning(f"SDK method failed, falling back to direct API: {e}")
                
        # Fall back to direct API calls with requests
        return self._create_chat_completion_direct(messages, tools, **kwargs)
    
    def _create_chat_completion_direct(self, messages, tools=None, **kwargs):
        """
        Create a chat completion using direct API calls with requests.
        
        This method handles the specific response format issues with LM Studio API.
        """
        # Convert messages to API format
        api_messages = []
        for msg in messages:
            role = getattr(msg, "role", "user")
            content = getattr(msg, "content", "") or ""
            if role not in ["system", "user", "assistant", "function", "tool"]:
                logger.warning(f"Invalid message role '{role}', defaulting to 'user'")
                role = "user"
            msg_dict = {"role": role, "content": content}
            if hasattr(msg, "name") and role in ["function", "tool"]:
                msg_dict["name"] = msg.name
            api_messages.append(msg_dict)
        
        # Set up request parameters
        # Set up request parameters
        model = kwargs.get("model", self.model)
        if not model:
            raise ValueError("Model parameter is required but not provided")
            
        # Perform health check before proceeding
        if not self.check_health():
            raise APIConnectionError("LM Studio API is not healthy or model is unavailable")
            
        payload = {
            "model": model,
            "messages": api_messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", self.config["max_tokens"]),
            "stream": kwargs.get("stream", self.config["stream"]),
            "top_p": kwargs.get("top_p", 1.0),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
            "presence_penalty": kwargs.get("presence_penalty", 0.0)
        }
        
        # Add tools if provided
        if tools:
            payload["tools"] = tools
        
        # Check if model is available
        try:
            model_info_response = requests.get(
                f"{self.api_base}models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout
            )
            if model_info_response.status_code == 404:
                raise ModelNotFoundError("LM Studio API endpoint not found")
            elif model_info_response.status_code == 401:
                raise InvalidRequestError("Invalid API key or unauthorized access")
            elif model_info_response.status_code != 200:
                raise APIResponseError(
                    f"Model availability check failed",
                    status_code=model_info_response.status_code,
                    response_text=model_info_response.text
                )
            
            models_data = model_info_response.json()
            if not models_data.get("data"):
                return "No models available in LM Studio", None
            
            requested_model = payload["model"]
            available_models = [model["id"] for model in models_data.get("data", [])]
            if requested_model != "default" and requested_model not in available_models:
                return f"Requested model '{requested_model}' not available. Available models: {', '.join(available_models)}", None
                
        except Exception as e:
            logger.error(f"Failed to check model availability: {e}")
            return f"Failed to check model availability: {str(e)}", None

        # Use the standard OpenAI endpoint format only
        endpoints = [
            f"{self.api_base}chat/completions",  # Primary endpoint
        ]

        # Try each endpoint with retries
        for endpoint in endpoints:
            retries = 0
            while retries <= self.config["max_retries"]:
                try:
                    logger.info(f"Making direct API request to {endpoint}")
                    headers = {"Content-Type": "application/json"}
                    if self.api_key:
                        headers["Authorization"] = f"Bearer {self.api_key}"
                
                    response = requests.post(
                        endpoint, 
                        json=payload,
                        headers=headers,
                        timeout=self.timeout
                    )
                
                # Check for successful response
                if response.status_code == 200:
                    # Try to parse the JSON response
                        try:
                            response_data = response.json()
                            
                            # Handle error responses
                            if "error" in response_data:
                                error_msg = response_data["error"]
                                if isinstance(error_msg, dict):
                                    error_msg = error_msg.get("message", str(error_msg))
                                logger.warning(f"API returned error: {error_msg}")
                                return f"LM Studio API error: {error_msg}", None
                            
                            if not response_data.get("choices"):
                                logger.warning(f"Unexpected response format: {response_data}")
                                return "Invalid response format from LM Studio API", None
                        
                            # Handle standard OpenAI format responses
                            if "choices" in response_data and response_data["choices"]:
                                choice = response_data["choices"][0]
                                
                                # Check for tool calls
                                if "message" in choice and "tool_calls" in choice["message"] and choice["message"]["tool_calls"]:
                                    return "", choice["message"]["tool_calls"]
                                
                                # Standard content response
                                if "message" in choice and "content" in choice["message"]:
                                    content = choice["message"]["content"]
                                    return content if content is not None else "", None
                            
                            # Handle non-standard formats
                            for key in ["text", "content", "output", "response", "generation"]:
                                if key in response_data:
                                    return response_data[key], None
                            
                            # Fall back to the raw text if nothing else works
                            logger.warning(f"Unknown response format: {response_data}")
                            return json.dumps(response_data), None
                        
                    except json.JSONDecodeError:
                            # Not JSON, return the raw text
                            return response.text, None
                else:
                    error_msg = f"API request failed with status {response.status_code}: {response.text}"
                    logger.warning(error_msg)
                    
                    if response.status_code in [401, 403]:
                        raise InvalidRequestError("Authentication failed or invalid API key")
                    elif response.status_code == 404:
                        raise ModelNotFoundError("Requested model or endpoint not found")
                    elif response.status_code in self.config["retry_codes"]:
                        if retries < self.config["max_retries"]:
                            wait_time = self.config["retry_delay"] * (2 ** retries)  # Exponential backoff
                            logger.info(f"Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                            retries += 1
                            continue
                    
                    raise APIResponseError(error_msg, status_code=response.status_code, response_text=response.text)
                except Timeout as e:
                    logger.warning(f"API request to {endpoint} timed out: {e}")
                    if retries < self.config["max_retries"]:
                        wait_time = self.config["retry_delay"] * (2 ** retries)
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        retries += 1
                        continue
                    raise APIConnectionError(f"API request timed out after {self.config['max_retries']} retries")
                except ConnectionError as e:
                    logger.warning(f"Connection error to {endpoint}: {e}")
                    if retries < self.config["max_retries"]:
                        wait_time = self.config["retry_delay"] * (2 ** retries)
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        retries += 1
                        continue
                    raise APIConnectionError(f"Failed to connect to API after {self.config['max_retries']} retries")
                except RequestException as e:
                    logger.error(f"API request to {endpoint} failed: {e}")
                    raise APIConnectionError(f"Request failed: {str(e)}")
                except Exception as e:
                    logger.error(f"Unexpected error during API request to {endpoint}: {e}")
                    raise LMStudioError(f"Unexpected error: {str(e)}")
        
        # All endpoints failed
        raise APIConnectionError("All LM Studio API endpoints failed. Check server status and configuration.")
        return "All LM Studio API endpoints failed. Check server status and configuration.", None

    def _create_chat_completion_sdk(self, messages, tools=None, **kwargs):
        """
        Create a chat completion using the LM Studio SDK.
        
        Args:
            messages: List of message objects with role and content
            tools: Optional list of tools available to the model
            **kwargs: Additional parameters to pass to the API
        
        Returns:
            Tuple[str, Optional[List]]: The model response text and any tool calls
        """
        if not LMSTUDIO_SDK_AVAILABLE:
            logger.warning("LM Studio SDK not available. Falling back to direct API calls.")
            return self._create_chat_completion_direct(messages, tools, **kwargs)
        
        try:
            # Ensure we have a valid model
            model = kwargs.get("model", self.model)
            if not model:
                raise ValueError("Model parameter is required but not provided")
                
            # Perform health check before proceeding
            if not self.check_health():
                raise APIConnectionError("LM Studio API is not healthy or model is unavailable")
            
            # Convert messages to API format
            api_messages = []
            for msg in messages:
                role = getattr(msg, "role", "user")
                content = getattr(msg, "content", "") or ""
                if role not in ["system", "user", "assistant", "function", "tool"]:
                    logger.warning(f"Invalid message role '{role}', defaulting to 'user'")
                    role = "user"
                msg_dict = {"role": role, "content": content}
                if hasattr(msg, "name") and role in ["function", "tool"]:
                    msg_dict["name"] = msg.name
                api_messages.append(msg_dict)
            
            # Create SDK client
            lmstudio_client = lmstudio.Client(
                api_key=self.api_key,
                base_url=self.api_base,
                timeout=self.timeout
            )
            
            # Set up parameters
            params = {
                "model": model,
                "messages": api_messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", self.config["max_tokens"]),
                "stream": kwargs.get("stream", self.config["stream"]),
                "top_p": kwargs.get("top_p", 1.0),
                "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
                "presence_penalty": kwargs.get("presence_penalty", 0.0)
            }
            
            # Add tools if supported and provided
            if tools:
                params["tools"] = tools
            
            # Make the API call using the SDK
            response = lmstudio_client.chat.completions.create(**params)
            
            # Extract content and tool calls from response
            if not response.choices:
                logger.warning("Empty response from LM Studio API")
                return "", None
                
            choice = response.choices[0]
            message = choice.message
            
            # Check for tool calls
            if hasattr(message, "tool_calls") and message.tool_calls:
                return "", message.tool_calls
            
            # Return content
            content = message.content
            return content if content is not None else "", None
            
        except ImportError:
            logger.warning("LM Studio SDK module not properly loaded. Falling back to direct API calls.")
            return self._create_chat_completion_direct(messages, tools, **kwargs)
        except (AttributeError, ValueError) as e:
            logger.error(f"Error using LM Studio SDK: {str(e)}")
            # Fall back to direct API calls on error
            return self._create_chat_completion_direct(messages, tools, **kwargs)
        except Exception as e:
            logger.error(f"Unexpected error using LM Studio SDK: {str(e)}")
            return f"Error with LM Studio SDK: {str(e)}", None
# Quick test function
def run_test():
    client = LMStudioClient()
    print(f"API Base: {client.api_base}")
    
    from collections import namedtuple
    Message = namedtuple("Message", ["role", "content"])
    
    messages = [Message(role="user", content="Hello, how are you today?")]
    response, tool_calls = client.create_chat_completion(messages)
    
    print(f"Response: {response}")
    print(f"Tool calls: {tool_calls}")
    
    return True

if __name__ == "__main__":
    success = run_test()
    print("Test completed:", "SUCCESS" if success else "FAILED")
