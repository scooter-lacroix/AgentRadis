"""
LM Studio Client - Fixed

This module provides a fixed version of the LM Studio client that
properly handles error responses from the LM Studio server.
"""

import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from app.schema.models import Message, ToolCall

logger = logging.getLogger(__name__)

class LMStudioClient:
    """
    Client for interacting with LM Studio's API, with improved error handling
    for the responses the server is actually sending.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize LM Studio client with configuration"""
        self.config = config or {}
        
        # Extract configuration
        self.api_base = "http://127.0.0.1:1234"
        self.model = self.config.get("model", "gemma-3-4b-it")
        self.temperature = float(self.config.get("temperature", 0.7))
        self.max_tokens = int(self.config.get("max_tokens", 1000))
        self.timeout = float(self.config.get("timeout", 120.0))
        
        # Parse host and port from api_base
        self.host = "127.0.0.1"
        self.port = 1234
        
        if "://" in self.api_base:
            base_url = self.api_base.split("://")[1].split("/")[0]
            if ":" in base_url:
                self.host, port_str = base_url.split(":")
                self.port = int(port_str)
        
        logger.info(f"Initialized LM Studio client with host:port: {self.host}:{self.port}")
    
    def create_chat_completion(
        self, messages: List[Message], **kwargs
    ) -> Tuple[str, List[ToolCall]]:
        """
        Process a list of messages to generate a chat completion.
        Returns the completion text and any tool calls.
        
        This method tries the OpenAI-compatible API first, and gracefully
        handles the error responses from LM Studio.
        """
        # Extract parameters from kwargs with defaults from config
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        
        try:
            # Try the OpenAI-compatible API
            return self._create_chat_completion_openai(messages, temperature, max_tokens)
        except Exception as e:
            logger.error(f"Error using OpenAI API: {e}")
            
            # Return a graceful error response rather than crashing
            return (
                "I encountered a connection issue with LM Studio. "
                "Please ensure the LM Studio server is running correctly.",
                []
            )
    
    def _create_chat_completion_openai(
        self, messages: List[Message], temperature: float, max_tokens: int
    ) -> Tuple[str, List[ToolCall]]:
        """
        Create a chat completion using the OpenAI-compatible API
        with improved error handling.
        """
        try:
            from openai import OpenAI
            import requests

            # Check if model is available
            try:
                models_response = requests.get(f"{self.api_base}/v1/models")
                if models_response.status_code == 200:
                    models_data = models_response.json()
                    available_models = [model["id"] for model in models_data["data"]]
                    if self.model not in available_models:
                        return f"The requested model '{self.model}' is not currently loaded in LM Studio. Available models: {', '.join(available_models)}", []
                else:
                    logger.warning(f"Failed to check model availability: {models_response.status_code}")
            except Exception as e:
                logger.warning(f"Failed to check model availability: {e}")
            
            # Convert our schema.models.Message objects to OpenAI format
            openai_messages = [
                {"role": msg.role, "content": msg.content} 
                for msg in messages
            ]
            
            # Create the OpenAI client
            client = OpenAI(
                base_url=f"{self.api_base}/v1",  # Ensure we use the v1 endpoint
                api_key="lm-studio",  # LM Studio doesn't use API keys
                timeout=self.timeout
            )
            
            logger.debug(f"Sending request to OpenAI-compatible API at {self.api_base}")
            logger.debug(f"Messages: {openai_messages}")
            
            # Send the request
            try:
                response = client.chat.completions.create(
                    messages=openai_messages,
                    model=self.model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                # Check if we got a valid response
                if hasattr(response, 'choices') and response.choices:
                    # Extract the response text
                    message = response.choices[0].message
                    response_text = message.content if message and message.content else ""
                    
                    # Extract any tool calls if present
                    tool_calls = []
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        tool_calls = [
                            ToolCall(
                                id=tool.id,
                                type=tool.type,
                                function=tool.function.name,
                                arguments=tool.function.arguments
                            ) for tool in message.tool_calls
                        ]
                    
                    return response_text, tool_calls
                else:
                    logger.warning("Unexpected response format from LM Studio")
                    return "Unexpected response format from LM Studio", []
                    
                    # If we can't extract content in a structured way, return the whole thing
                    return f"LM Studio response: {raw_response}", []
                    
            except Exception as api_error:
                logger.warning(f"OpenAI API request failed: {api_error}")
                
                # Check if the error contains a JSON response from LM Studio
                error_str = str(api_error)
                if "{" in error_str and "}" in error_str:
                    try:
                        # Extract JSON from error message
                        json_start = error_str.find("{")
                        json_end = error_str.rfind("}") + 1
                        json_str = error_str[json_start:json_end]
                        
                        # Parse JSON
                        error_data = json.loads(json_str)
                        
                        # Check if there's an error message to extract
                        if "error" in error_data:
                            error_msg = error_data["error"]
                            return f"LM Studio error: {error_msg}", []
                    except:
                        pass
                
                # If JSON extraction failed, create a more useful error message
                if "Unexpected endpoint or method" in error_str:
                    return (
                        "The LM Studio server doesn't support this API endpoint. "
                        "Please ensure you're using a compatible LM Studio version.",
                        []
                    )
                
                # Fallback error message
                return f"LM Studio API error: {api_error}", []
        
        except Exception as e:
            logger.error(f"Error in _create_chat_completion_openai: {e}")
            raise
