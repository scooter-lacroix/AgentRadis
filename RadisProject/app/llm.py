#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import abc
import logging
import os
import time
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path

import tiktoken
import openai
from openai import OpenAI
import numpy as np
from ctransformers import AutoModelForCausalLM, AutoConfig # Import ctransformers

from app.config import RadisConfig

logger = logging.getLogger(__name__)


class TokenCounter:
    """Utility class for counting tokens in text."""

    # Cache encoders to avoid reloading
    _encoders = {}
    # Track models that don't work with tiktoken
    _unsupported_models = set()

    @classmethod
    def get_encoder(cls, model: str):
        """Get the appropriate encoder for a model."""
        # Check if we already know this model is unsupported
        if model in cls._unsupported_models:
            logger.debug(f"Using approximate token counting for unsupported model: {model}")
            return None
            
        # Return cached encoder if available
        if model in cls._encoders:
            return cls._encoders[model]
            
        # Try to get an encoder for this model
        try:
            cls._encoders[model] = tiktoken.encoding_for_model(model)
            return cls._encoders[model]
        except KeyError:
            # Try to find a similar model
            try:
                # Map custom models to known tiktoken models
                if "gemma" in model.lower():
                    logger.warning(f"Model {model} not directly supported by tiktoken, using cl100k_base encoder")
                    cls._encoders[model] = tiktoken.get_encoding("cl100k_base")
                elif "llama" in model.lower() or "mistral" in model.lower():
                    logger.warning(f"Model {model} not directly supported by tiktoken, using cl100k_base encoder")
                    cls._encoders[model] = tiktoken.get_encoding("cl100k_base")
                else:
                    # Fall back to cl100k_base for unknown models
                    logger.warning(f"Model {model} not found, using cl100k_base encoder")
                    cls._encoders[model] = tiktoken.get_encoding("cl100k_base")
                return cls._encoders[model]
            except Exception as e:
                # If all tiktoken approaches fail, mark as unsupported
                logger.warning(f"Tiktoken failed for model {model}: {e}. Using approximate token counting.")
                cls._unsupported_models.add(model)
                return None

    @classmethod
    def count_tokens(cls, text: str, model: str = "gpt-3.5-turbo") -> int:
        """Count the number of tokens in the given text for the specified model."""
        encoder = cls.get_encoder(model)
        
        # If we have a tiktoken encoder, use it
        if encoder:
            return len(encoder.encode(text))
        
        # Fallback: approximate token count (4 chars ~= 1 token)
        # This is a very rough approximation but better than nothing
        return len(text) // 4

    @classmethod
    def count_messages_tokens(
        cls, messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo"
    ) -> int:
        """Count tokens in a list of chat messages."""
        encoder = cls.get_encoder(model)
        
        # If we have a tiktoken encoder, use it
        if encoder:
            # Base token count for messages format
            tokens = 3  # Every reply is primed with <|start|>assistant<|message|>

            for message in messages:
                tokens += (
                    4  # Every message follows <|start|>{role}<|message|>{content}<|end|>
                )
                for key, value in message.items():
                    tokens += len(encoder.encode(value))

            return tokens
        
        # Fallback: approximate token count
        tokens = 3  # Base tokens
        for message in messages:
            tokens += 4  # Message format tokens
            for key, value in message.items():
                # Approximate token count (4 chars ~= 1 token)
                tokens += len(value) // 4
                
        return tokens


class ConversationContext:
    """Manages conversation history and context for LLM interactions."""

    def __init__(
        self,
        model: str = "gpt-3.5-turbo",
        max_tokens: int = 4096,
        system_message: Optional[str] = None,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.messages: List[Dict[str, str]] = []

        # Add system message if provided
        if system_message:
            self.add_system_message(system_message)

    def add_system_message(self, content: str) -> None:
        """Add a system message to the conversation."""
        # Replace any existing system message
        self.messages = [msg for msg in self.messages if msg["role"] != "system"]
        self.messages.insert(0, {"role": "system", "content": content})

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        self.messages.append({"role": "user", "content": content})
        self._trim_if_needed()

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation."""
        self.messages.append({"role": "assistant", "content": content})
        self._trim_if_needed()

    def _trim_if_needed(self) -> None:
        """Trim conversation history if it exceeds the token limit."""
        current_tokens = TokenCounter.count_messages_tokens(self.messages, self.model)

        # Reserve tokens for response
        allowed_tokens = self.max_tokens - 1000  # Reserve 1000 tokens for response

        if current_tokens > allowed_tokens:
            # Keep system message if present
            system_message = None
            if self.messages and self.messages[0]["role"] == "system":
                system_message = self.messages[0]
                remaining_messages = self.messages[1:]
            else:
                remaining_messages = self.messages.copy()

            # Remove oldest messages (but keep at least the latest exchange)
            while current_tokens > allowed_tokens and len(remaining_messages) > 2:
                # Remove oldest user/assistant pair
                if len(remaining_messages) >= 2:
                    remaining_messages = remaining_messages[2:]
                else:
                    remaining_messages = remaining_messages[1:]

                # Recalculate token count
                messages_to_count = [system_message] if system_message else []
                messages_to_count.extend(remaining_messages)
                current_tokens = TokenCounter.count_messages_tokens(
                    messages_to_count, self.model
                )

            # Reassemble messages
            self.messages = [system_message] if system_message else []
            self.messages.extend(remaining_messages)

    def get_messages(self) -> List[Dict[str, str]]:
        """Get the current conversation messages."""
        return self.messages

    def clear(self) -> None:
        """Clear the conversation history except for system message."""
        if self.messages and self.messages[0]["role"] == "system":
            system_message = self.messages[0]
            self.messages = [system_message]
        else:
            self.messages = []


class BaseLLM(abc.ABC):
    """Base abstract class for LLM providers."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.retry_count = self.config.get("retry_count", 3)
        self.retry_delay = self.config.get("retry_delay", 1)
        self.model_name = self.config.get("model", "unknown") # Store model name

    @abc.abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text based on a prompt."""
        pass

    @abc.abstractmethod
    def complete(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """Complete a conversation based on message history."""
        pass

    @abc.abstractmethod
    def embed(self, text: Union[str, List[str]], **kwargs) -> np.ndarray:
        """Generate embeddings for the given text."""
        pass

    @abc.abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in the given text."""
        pass

    @property
    def model(self) -> str:
        """Return the model name being used."""
        return self.model_name

    def _handle_error(self, error: Exception, operation: str, attempt: int) -> bool:
        """
        Handle errors during LLM operations.
        Returns True if operation should be retried, False otherwise.
        """
        logger.error(
            f"Error during {operation} (attempt {attempt}/{self.retry_count}): {error}"
        )

        if attempt >= self.retry_count:
            logger.error(f"Maximum retry attempts reached for {operation}")
            return False

        # Handle rate limiting
        if hasattr(error, "status_code") and error.status_code == 429:
            wait_time = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
            logger.warning(f"Rate limited. Waiting {wait_time}s before retry.")
            time.sleep(wait_time)
            return True

        # Handle server errors
        if hasattr(error, "status_code") and 500 <= error.status_code < 600:
            wait_time = self.retry_delay * (2 ** (attempt - 1))
            logger.warning(f"Server error. Waiting {wait_time}s before retry.")
            time.sleep(wait_time)
            return True

        return False


class OpenAILLM(BaseLLM):
    """OpenAI implementation of the LLM interface."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.config = config or {}

        # Get API key from config or environment
        api_key = self.config.get("api_key") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key is required. Set it in config or OPENAI_API_KEY environment variable."
            )

        # Set up client
        self.client = OpenAI(api_key=api_key)

        # Default model for different operations
        self.completion_model = self.config.get("completion_model", "gpt-3.5-turbo")
        self.embedding_model = self.config.get(
            "embedding_model", "text-embedding-ada-002"
        )

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text based on a prompt using OpenAI."""
        messages = [{"role": "user", "content": prompt}]
        response, _ = self.complete(messages, **kwargs)
        return response

    def complete(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """Complete a conversation based on message history using OpenAI."""
        model = kwargs.get("model", self.completion_model)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1000)
        top_p = kwargs.get("top_p", 1.0)
        frequency_penalty = kwargs.get("frequency_penalty", 0.0)
        presence_penalty = kwargs.get("presence_penalty", 0.0)

        # Verify messages format
        for msg in messages:
            if "role" not in msg or "content" not in msg:
                raise ValueError("Messages must contain 'role' and 'content' keys")

        for attempt in range(1, self.retry_count + 1):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
                )

                # Extract content from the response
                content = response.choices[0].message.content

                # Prepare metadata
                metadata = {
                    "id": response.id,
                    "model": response.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    },
                }

                return content, metadata

            except Exception as e:
                retry = self._handle_error(e, "chat completion", attempt)
                if not retry:
                    raise

    def embed(self, text: Union[str, List[str]], **kwargs) -> np.ndarray:
        """Generate embeddings for the given text using OpenAI."""
        model = kwargs.get("model", self.embedding_model)

        # Ensure text is a list
        if isinstance(text, str):
            text = [text]

        for attempt in range(1, self.retry_count + 1):
            try:
                response = self.client.embeddings.create(model=model, input=text)

                # Extract embeddings from response
                embeddings = [item.embedding for item in response.data]

                # If only one text was provided, return just that embedding
                if len(text) == 1:
                    return np.array(embeddings[0])

                return np.array(embeddings)

            except Exception as e:
                retry = self._handle_error(e, "embedding", attempt)
                if not retry:
                    raise

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in the given text."""
        return TokenCounter.count_tokens(text, self.completion_model)


class LMStudioLLM(BaseLLM):
    is_local_file = False
    """LM Studio implementation of the LLM interface."""


    def _init_local_model(self):
        """Initialize a local model using ctransformers."""
        logger.info(f"Attempting to load local model from: {self.model_path}")
        model_file_path = Path(self.model_path)
        
        # Validate model file
        if not model_file_path.exists():
            raise FileNotFoundError(f"Local model file not found at: {self.model_path}")
        if not model_file_path.is_file():
            raise ValueError(f"Provided model path is not a file: {self.model_path}")

        try:
            # Determine model type based on filename and suffix
            model_type = "llama"  # Default model type
            model_name_lower = model_file_path.name.lower()
            
            if "llama" in model_name_lower:
                model_type = "llama"
            elif "mistral" in model_name_lower:
                model_type = "mistral"
            elif "gemma" in model_name_lower:
                model_type = "gemma"
            elif "mpt" in model_name_lower:
                model_type = "mpt"
            
            # Adjust based on file extension
            if ".gguf" in model_file_path.suffix.lower():
                # GGUF usually doesn't need explicit type, but helps config
                pass  # Keep model_type from above
            elif ".safetensors" in model_file_path.suffix.lower():
                # Safetensors might need more specific config
                logger.warning("Loading Safetensors with ctransformers might have limitations.")

            # Load the model with configuration
            logger.info(f"Loading model with type={model_type}, gpu_layers={self.gpu_layers}")
            self.loaded_model = AutoModelForCausalLM.from_pretrained(
                str(model_file_path.parent),  # Pass directory
                model_file=model_file_path.name,  # Pass filename
                model_type=model_type,  # Specify model type
                gpu_layers=self.gpu_layers,
                context_length=self.context_length,
                # Add other relevant parameters as needed
            )
            self.is_local_file = True
            logger.info(f"Successfully loaded local model: {self.model_path} with {self.gpu_layers} GPU layers.")
            
            # Try to get the tokenizer if available
            if hasattr(self.loaded_model, 'tokenizer'):
                self.tokenizer = self.loaded_model.tokenizer
                logger.info("Successfully loaded model tokenizer.")
            
        except Exception as e:
            logger.error(f"Failed to load local model from {self.model_path}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize local model: {e}") from e

    def _init_api_client(self):
        """Initialize an API client for LM Studio."""
        logger.info(f"Initializing LM Studio client for API base: {self.api_base}")
        try:
            # Create OpenAI-compatible client
            self.client = OpenAI(
                base_url=self.api_base,
                api_key=self.api_key,
                timeout=self.timeout
            )
            # is_local_file already initialized as a class attribute
            
            # Test connection to API
            logger.debug("Testing connection to LM Studio API...")
            try:
                response = self.client.models.list()
                logger.info(f"Successfully connected to LM Studio API. Available models: {response}")
            except Exception as e:
                logger.warning(f"Could not list models from LM Studio API: {e}. Continuing anyway.")
        except Exception as e:
            logger.error(f"Failed to initialize LM Studio API client: {e}", exc_info=True)
            if "Connection refused" in str(e):
                raise ConnectionError(f"Could not connect to LM Studio API at {self.api_base}. "
                                     "Is the LM Studio server running?") from e
            raise RuntimeError(f"Failed to initialize LM Studio API client: {e}") from e

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text based on a prompt using LM Studio."""
        messages = [{"role": "user", "content": prompt}]
        response, _ = self.complete(messages, **kwargs)
        return response

    def complete(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """Complete a conversation based on message history using LM Studio."""
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1000)

        if self.is_local_file and self.loaded_model:
            # Use ctransformers model
            try:
                # Basic chat templating (adapt as needed for specific models)
                prompt_string = ""
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    # Example Llama-2 like template - THIS NEEDS ADJUSTMENT FOR OTHER MODELS
                    if role == "system":
                        prompt_string += f"<<SYS>>\n{content}\n<</SYS>>\n\n"
                    elif role == "user":
                        prompt_string += f"[INST] {content} [/INST]"
                    elif role == "assistant":
                        prompt_string += f" {content} " # Note leading/trailing spaces

                logger.debug(f"Generating with local model. Formatted prompt: {prompt_string[:200]}...")

                # Generate text using the loaded ctransformers model
                response_text = self.loaded_model(
                    prompt_string,
                    temperature=temperature,
                    max_new_tokens=max_tokens,
                    stop=["[INST]", "<<SYS>>"], # Example stop sequences
                    # Add other generation parameters as needed (top_k, top_p, etc.)
                )

                logger.debug(f"Local model raw response: {response_text[:200]}...")
                content = response_text.strip()

                # Metadata for local file models is limited
                metadata = {
                    "model": self.model_name or self.model_path,
                    "usage": {"prompt_tokens": -1, "completion_tokens": -1, "total_tokens": -1}, # Token count harder with ctransformers direct call
                }
                return content, metadata

            except Exception as e:
                logger.error(f"Error during local model generation: {e}", exc_info=True)
                raise RuntimeError(f"Local model generation failed: {e}") from e

        elif self.client:
            # Use OpenAI client pointed at local API (existing logic)
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name, # Use model name configured
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                content = response.choices[0].message.content

                # Metadata for local API models might be limited
                metadata = {
                    "model": self.model_name,
                    "usage": {
                 # Attempt to get usage if API provides it, else -1
                         "prompt_tokens": getattr(response.usage, 'prompt_tokens', -1),
                         "completion_tokens": getattr(response.usage, 'completion_tokens', -1),
                         "total_tokens": getattr(response.usage, 'total_tokens', -1),
                                }
                }
                return content, metadata # Return inside the try block

            except Exception as e: # Indented to align with try at 435
                logger.error(f"Error in LM Studio API completion: {e}", exc_info=True)
                # Check for connection errors specifically
                if "Connection refused" in str(e) or "Failed to connect" in str(e):
                    raise ConnectionError(f"Could not connect to LM Studio API at {self.api_base}. Is it running?") from e
                raise # Re-raise other errors
        else: # This else corresponds to the main if/elif structure
            # This state should not be reached if __init__ validation is correct
            raise RuntimeError("LMStudioLLM is not properly initialized. No model path or API base configured.")

    def embed(self, text: Union[str, List[str]], **kwargs) -> np.ndarray:
        """Generate embeddings for the given text."""
        raise NotImplementedError("Embedding not supported in LM Studio")

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in the given text."""
        # Prioritize local model tokenizer if available
        if self.is_local_file and self.loaded_model and hasattr(self.loaded_model, 'tokenizer'):
            try:
                # Use the tokenizer from the loaded ctransformers model
                return len(self.loaded_model.tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"Failed to use local model tokenizer for token count: {e}. Falling back to tiktoken.")
                # Fallback to tiktoken if local tokenizer fails or raises an error
                # Use the actual model name if available for better accuracy with tiktoken
                model_for_tiktoken = self.model_name if self.model_name != "local-model" else "gemma-3-4b-it" # Fallback model
            return TokenCounter.count_tokens(text, model_for_tiktoken)
        else:
            # Use tiktoken for API-based models or as fallback
            model_for_tiktoken = self.model_name if self.model_name != "local-model" else "gemma-3-4b-it" # Fallback model
            return TokenCounter.count_tokens(text, model_for_tiktoken)


class LLMFactory:
    """Factory class for creating LLM instances."""

    @staticmethod
    def create(provider: str, config: Optional[Dict[str, Any]] = None) -> BaseLLM:
        """
        Create and return an LLM instance based on the provider.

        Args:
            provider: The LLM provider name (e.g., 'openai', 'anthropic', etc.)
            config: Provider-specific configuration

        Returns:
            An instance of BaseLLM implementation
        """
        config = config or {}

        if provider.lower() == "openai":
            return OpenAILLM(config)
        elif provider.lower() == "local":
            return LMStudioLLM(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")


def get_default_llm() -> BaseLLM:
    """
    Get default LLM instance based on application configuration.

    Returns:
        An instance of BaseLLM implementation
    """
    try:
        config = RadisConfig()
        llm_config = config.get_llm_config()
        provider = llm_config.api_type  # Use api_type from LLMConfig
        return LLMFactory.create(provider, llm_config.model_dump())
    except Exception as e:
        logger.error(f"Error creating default LLM: {e}")
        raise  # Don't fall back to OpenAI, let the error propagate
