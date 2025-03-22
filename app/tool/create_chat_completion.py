"""
Chat completion tool for generating text with LLM models.
"""
import os
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, Union

from app.logger import logger
from app.tool.base import BaseTool
from app.config import config

# Import the appropriate LLM backend based on configuration
try:
    from app.llm import get_llm
except ImportError:
    logger.warning("LLM module not available, using dummy implementation")
    def get_llm():
        return DummyLLM()

class DummyLLM:
    """Fallback LLM implementation that returns a placeholder response."""
    
    async def generate(self, messages, **kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "This is a placeholder response. The LLM module is not available."
                    }
                }
            ]
        }

class CreateChatCompletion(BaseTool):
    """
    Tool for generating text using LLM models.
    """
    
    name = "create_chat_completion"
    description = """
    Generate text using a language model based on provided messages.
    This tool communicates with LLM APIs to generate responses based on conversation history.
    """
    parameters = {
        "type": "object",
        "properties": {
            "messages": {
                "type": "array",
                "description": "List of messages in the conversation history",
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {
                            "type": "string",
                            "enum": ["system", "user", "assistant", "function"],
                            "description": "The role of the message sender"
                        },
                        "content": {
                            "type": "string",
                            "description": "The content of the message"
                        },
                        "name": {
                            "type": "string",
                            "description": "The name of the function (for function role)"
                        }
                    },
                    "required": ["role", "content"]
                }
            },
            "model": {
                "type": "string",
                "description": "The model to use for generation (default: config default model)"
            },
            "temperature": {
                "type": "number",
                "description": "Temperature for generation (0-2, default: 0.7)"
            },
            "max_tokens": {
                "type": "integer",
                "description": "Maximum tokens to generate (default: determined by model)"
            },
            "system_prompt": {
                "type": "string",
                "description": "System prompt to prepend to the messages"
            }
        },
        "required": ["messages"]
    }
    
    def __init__(self, **kwargs):
        """Initialize the CreateChatCompletion tool."""
        super().__init__(**kwargs)
        self.llm = get_llm()
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute a chat completion.
        
        Args:
            messages: List of message objects with role and content
            model: Model to use for generation
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            system_prompt: System prompt to prepend to the messages
            
        Returns:
            Dictionary with generation results
        """
        messages = kwargs.get("messages", [])
        model = kwargs.get("model", config.get("default_model", "gpt-3.5-turbo"))
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")
        system_prompt = kwargs.get("system_prompt")
        
        if not messages:
            return {
                "status": "error",
                "error": "No messages provided for chat completion"
            }
        
        # Add system prompt if provided and not already in messages
        if system_prompt and not any(m.get("role") == "system" for m in messages):
            messages = [{"role": "system", "content": system_prompt}] + messages
        
        try:
            # Prepare parameters for the LLM
            llm_params = {
                "model": model,
                "temperature": temperature
            }
            
            if max_tokens:
                llm_params["max_tokens"] = max_tokens
            
            # Generate completion
            logger.info(f"Generating chat completion with model: {model}")
            response = await self.llm.generate(messages, **llm_params)
            
            # Extract and format the response
            completion = ""
            if response and "choices" in response and len(response["choices"]) > 0:
                choice = response["choices"][0]
                message = choice.get("message", {})
                completion = message.get("content", "")
            
            return {
                "status": "success",
                "completion": completion,
                "model": model,
                "full_response": response
            }
        except Exception as e:
            logger.error(f"Error generating chat completion: {str(e)}")
            return {
                "status": "error",
                "error": f"Chat completion failed: {str(e)}"
            }
    
    async def cleanup(self):
        """Clean up resources."""
        pass
    
    async def reset(self):
        """Reset the tool state."""
        pass 