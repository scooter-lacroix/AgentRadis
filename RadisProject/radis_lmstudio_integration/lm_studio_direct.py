import json
import logging
import requests
from typing import Dict, Optional, Any, Tuple

from .model_tokenizer import ModelTokenizer
from .response_sanitizer import ResponseSanitizer

logger = logging.getLogger(__name__)

class LMStudioDirect:
    """Direct integration with LM Studio server with token tracking and response sanitization."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        sanitize_response: bool = True,
        timeout: int = 60,
    ):
        """
        Initialize LM Studio connection with token tracking.
        
        Args:
            base_url: Base URL for the LM Studio server
            sanitize_response: Whether to sanitize model responses
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.sanitize_response = sanitize_response
        self.timeout = timeout
        
        # Initialize components
        self.tokenizer = ModelTokenizer()
        self.sanitizer = ResponseSanitizer()
        
        # Usage tracking
        self._prompt_tokens = 0
        self._completion_tokens = 0
        
        # Auto-detect model on init
        self.model_name = self._detect_model()

    def _detect_model(self) -> str:
        """
        Auto-detect the model being served by LM Studio.
        
        Returns:
            str: Detected model name or "unknown" if detection fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/models",
                timeout=self.timeout
            )
            response.raise_for_status()
            models = response.json()
            
            if models and len(models) > 0:
                return models[0].get("id", "unknown")
            return "unknown"
            
        except Exception as e:
            logger.warning(f"Failed to detect model: {str(e)}")
            return "unknown"

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in the given text using ModelTokenizer.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            int: Number of tokens
        """
        try:
            return self.tokenizer.count_tokens(text, self.model_name)
        except Exception as e:
            logger.warning(f"Token counting failed: {str(e)}")
            # Fallback: rough estimate based on words
            return len(text.split())

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stop: Optional[list] = None,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate completion from LM Studio with token tracking.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            Tuple[str, Dict]: Generated text and metadata including usage
        """
        # Count prompt tokens
        prompt_tokens = self._count_tokens(prompt)
        self._prompt_tokens += prompt_tokens
        
        # Prepare request
        payload = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stop": stop or [],
            **kwargs
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/completions",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract completion
            completion = result.get("choices", [{}])[0].get("text", "")
            
            # Sanitize if enabled
            if self.sanitize_response:
                completion = self.sanitizer.clean_response(completion)
            
            # Count completion tokens
            completion_tokens = self._count_tokens(completion)
            self._completion_tokens += completion_tokens
            
            return completion, {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"LM Studio API request failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            raise

    def get_usage(self) -> Dict[str, int]:
        """
        Get token usage statistics.
        
        Returns:
            Dict containing prompt, completion and total token counts
        """
        return {
            "prompt_tokens": self._prompt_tokens,
            "completion_tokens": self._completion_tokens,
            "total_tokens": self._prompt_tokens + self._completion_tokens
        }

"""
LM Studio Direct Client

A direct HTTP client for LM Studio that bypasses the OpenAI library
and uses raw HTTP requests to communicate with the server.
"""

import json
import logging
import requests
import time
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

class LMStudioDirect:
    """
    Direct HTTP client for LM Studio's inference API.
    This client uses direct HTTP requests to LM Studio's chat completions endpoint.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the direct LM Studio client"""
        self.config = config or {}
        
        # Extract configuration
        self.api_base = self.config.get("api_base", "http://localhost:1234").rstrip("/")
        self.model = self.config.get("model", "gemma-3-4b-it")
        self.temperature = float(self.config.get("temperature", 0.7))
        self.max_tokens = int(self.config.get("max_tokens", 1000))
        self.timeout = float(self.config.get("timeout", 120.0))
        
        # Set the endpoint URL
        self.endpoint = f"{self.api_base}/v1/chat/completions"
        
        logger.info(f"Initialized LM Studio Direct client with endpoint: {self.endpoint}")
    
    def generate(self, prompt: str) -> str:
        """
        Generate a completion for the given prompt.
        
        Args:
            prompt: The input prompt
            
        Returns:
            The generated text
        """
        # Create a messages array with the user prompt
        messages = [{"role": "user", "content": prompt}]
        
        # Call the chat endpoint
        return self.generate_from_messages(messages)
    
    def generate_from_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate a completion from a list of messages.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            
        Returns:
            The generated text
        """
        try:
            # Prepare the request data
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            logger.info(f"Sending request to LM Studio: {self.endpoint}")
            logger.debug(f"Request data: {data}")
            
            # Send the request
            start_time = time.time()
            response = requests.post(
                self.endpoint,
                json=data,
                timeout=self.timeout
            )
            duration = time.time() - start_time
            
            logger.info(f"Response received in {duration:.2f}s (status: {response.status_code})")
            
            # Parse the response
            if response.status_code == 200:
                response_data = response.json()
                
                # Check if there's an error message
                if "error" in response_data:
                    error_msg = response_data["error"]
                    logger.warning(f"LM Studio error: {error_msg}")
                    return f"I encountered an error: {error_msg}"
                
                # Extract the completion text
                if "choices" in response_data and response_data["choices"]:
                    completion = response_data["choices"][0]["message"]["content"]
                    return completion
                else:
                    logger.warning(f"No choices in response: {response_data}")
                    return "I received an empty response from the language model."
            else:
                logger.error(f"Error response: {response.status_code} {response.text}")
                return f"I received an error response from the language model: {response.status_code}"
                
        except requests.exceptions.Timeout:
            logger.error("Request timed out")
            return "I'm sorry, but the request to the language model timed out. Please try again later."
            
        except Exception as e:
            logger.error(f"Error in generate_from_messages: {e}")
            return f"I encountered an error while generating a response: {e}"
