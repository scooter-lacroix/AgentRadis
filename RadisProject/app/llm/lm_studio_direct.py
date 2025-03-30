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

# Import our modules
from app.llm.model_tokenizer import ModelTokenizer
from app.llm.response_sanitizer import ResponseSanitizer

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
        self.api_base = self.config.get("api_base", "http://127.0.0.1:1234").rstrip("/")
        self.model = self.config.get("model", "auto")
        self.temperature = float(self.config.get("temperature", 0.7))
        self.max_tokens = int(self.config.get("max_tokens", 1000))
        self.timeout = float(self.config.get("timeout", 120.0))
        self.sanitize_response = self.config.get("sanitize_response", True)
        
        # Set the endpoint URL
        self.endpoint = f"{self.api_base}/v1/chat/completions"
        
        # Detect model if not specified
        if not self.model or self.model == "auto":
            self.model = self._detect_model() or "unknown-model"
        
        # Initialize the tokenizer
        self.tokenizer = ModelTokenizer.get_tokenizer(self.model)
        
        # Initialize counters for metrics
        self.prompt_tokens = 0
        self.completion_tokens = 0
        
        logger.info(f"Initialized LM Studio Direct client with endpoint: {self.endpoint}")
        logger.info(f"Using model: {self.model}")
    
    def _detect_model(self) -> Optional[str]:
        """Try to detect which model is running in LM Studio"""
        try:
            # Try to access the info endpoint to get the model name
            response = requests.get(f"{self.api_base}/info", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if "model" in data:
                    return data["model"]
                    
        except Exception as e:
            logger.warning(f"Couldn't detect LM Studio model via /info: {e}")
            
        # Fallback: try a simple completion to see if we can detect the model
        try:
            # Prepare a minimal request
            data = {
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10
            }
            
            response = requests.post(
                self.endpoint,
                json=data,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if "model" in data:
                    return data["model"]
                
        except Exception as e:
            logger.warning(f"Couldn't detect model from chat completion: {e}")
        
        # Fallback to a reasonable default based on CUDA availability
        try:
            import torch
            if torch.cuda.is_available():
                # CUDA available, probably using a mid-size model
                logger.info("CUDA available, assuming qwen2.5-7b-instruct")
                return "qwen2.5-7b-instruct"
            else:
                # CPU only, probably using a small model
                logger.info("CUDA not available, assuming gemma-3-4b-it")
                return "gemma-3-4b-it"
        except ImportError:
            # Torch not available
            logger.warning("Could not detect GPU status, using generic model name")
            pass
            
        return "gemma-3-4b-it"  # Default to a common model
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in the given text using the appropriate tokenizer"""
        return self.tokenizer(text)
    
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
            
            # Count prompt tokens
            prompt_text = " ".join([msg.get("content", "") for msg in messages])
            self.prompt_tokens = self._count_tokens(prompt_text)
            
            logger.info(f"Sending request to LM Studio: {self.endpoint}")
            logger.info(f"Prompt tokens: {self.prompt_tokens}")
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
                    completion_raw = response_data["choices"][0]["message"]["content"]
                    
                    # Count completion tokens
                    self.completion_tokens = self._count_tokens(completion_raw)
                    logger.info(f"Completion tokens: {self.completion_tokens}")
                    
                    completion_text = completion_raw
                    
                    # Process and sanitize the response if enabled
                    if self.sanitize_response:
                        # Extract initial response (remove continuations)
                        completion_text = ResponseSanitizer.extract_initial_response(completion_text)
                        
                        # Sanitize the content
                        completion_text = ResponseSanitizer.sanitize(completion_text, self.model)
                        
                        logger.info(f"Response processed and sanitized (original length: {len(completion_raw)}, final length: {len(completion_text)})")
                    
                    # Add a RadisProject signature to identify the source
                    completion_with_signature = (
                        completion_text + 
                        f"\n\n_Response generated by {self.model} via RadisProject_"
                    )
                    
                    return completion_with_signature
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
    
    def get_usage(self) -> Dict[str, int]:
        """
        Get the token usage statistics from the last request.
        
        Returns:
            Dictionary with token usage stats
        """
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens
        }
