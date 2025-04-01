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
from fixed_lm_studio_client import LMStudioClient
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

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.config = config or {}
        
        # Initialize required attributes
        self.model_name = self.config.get("model", "gemma-3-4b-it")
        self.api_base = self.config.get("api_base", "http://127.0.0.1:1234/")
        self.api_key = self.config.get("api_key", "lm-studio")  # Default API key
        self.timeout = self.config.get("timeout", 120)
        self.model_path = self.config.get("model_path", None)
        self.gpu_layers = self.config.get("gpu_layers", 1)
        self.context_length = self.config.get("context_length", 2048)
        
        # Initialize attributes needed for either local file or API
        self.loaded_model = None
        self.tokenizer = None
        self.client = None
        self.lm_studio_client = None
        self.is_local_file = False
        
        # Initialize based on available configuration
        if self.model_path:
            self._init_local_model()
        elif self.api_base: # Ensure api_base is present for API client init
             self._init_api_client()
        else:
             # If neither model_path nor api_base is provided, raise error early
             raise ValueError("LMStudioLLM requires either 'model_path' or 'api_base' to be configured.")


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
        if not self.api_base: # Double check api_base
             raise ValueError("Cannot initialize API client without 'api_base' configured.")
             
        logger.info(f"Initializing LM Studio client for API base: {self.api_base}")
        try:
            # Create standard OpenAI-compatible client as fallback
            self.client = OpenAI(
                base_url=self.api_base,
                api_key=self.api_key,
                timeout=self.timeout
            )
            
            # Create our robust fixed LMStudioClient
            logger.info("Initializing improved LMStudioClient with multiple endpoint support")
            client_config = {
                "api_type": "local",
                "model": self.model_name,
                "api_base": self.api_base,
                "api_key": self.api_key,
                "timeout": self.timeout
            }
            self.lm_studio_client = LMStudioClient(client_config)
            
            # Test connection to API
            logger.debug("Testing connection to LM Studio API...")
            try:
                # First try with standard client
                response = self.client.models.list()
                logger.info(f"Successfully connected to LM Studio API using standard client. Available models: {response}")
            except Exception as e:
                logger.warning(f"Could not list models from LM Studio API using standard client: {e}")
                # Try with fixed client's model list function
                try:
                    models = self.lm_studio_client.get_model_list() if hasattr(self.lm_studio_client, 'get_model_list') else []
                    if models:
                        logger.info(f"Successfully connected to LM Studio API using fixed client. Available models: {models}")
                    else:
                        logger.warning("Could not retrieve model list using fixed client. Continuing anyway.")
                except Exception as e2:
                    logger.warning(f"Could not list models using fixed client: {e2}. Continuing anyway.")
        except Exception as e:
            logger.error(f"Failed to initialize LM Studio API clients: {e}", exc_info=True)
            if "Connection refused" in str(e):
                raise ConnectionError(f"Could not connect to LM Studio API at {self.api_base}. "
                                     "Is the LM Studio server running?") from e
            raise RuntimeError(f"Failed to initialize LM Studio API clients: {e}") from e

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

        # Check for local model first
        if self.is_local_file and self.loaded_model:
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

        # If no local model, try API clients
        elif self.lm_studio_client or self.client:
            try:
                # First try with our improved fixed LMStudioClient
                if not self.lm_studio_client:
                     raise Exception("Fixed LMStudioClient not initialized, attempting fallback.") # Skip if not initialized

                logger.info(f"Generating completion using fixed LMStudioClient with multi-endpoint support")
                content, tool_calls = self.lm_studio_client.create_chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=self.model_name
                )

                # Check if the response indicates an error OR is empty
                if content is None or content == "" or (isinstance(content, str) and content.startswith("Error:")):
                    logger.warning(f"LMStudioClient returned an error or empty content: {content}")
                    # Raise exception to trigger fallback
                    raise Exception(f"Fixed client error or empty response: {content}")

                # Handle successful response from fixed client
                logger.info("Successfully generated response using fixed LMStudioClient")
                metadata = {
                    "model": self.model_name,
                    "usage": { "prompt_tokens": -1, "completion_tokens": -1, "total_tokens": -1 }
                }
                return content, metadata

            except Exception as fixed_client_error:
                # Log the error from the fixed client attempt and fall back
                logger.warning(f"Fixed LMStudioClient failed: {fixed_client_error}. Falling back to standard client.")

                # Fall back to standard OpenAI client if available
                if self.client:
                    try:
                        logger.info("Falling back to standard OpenAI client")
                        response = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )

                        # Add null/empty checking here for the standard client response
                        if response is None:
                            logger.error("Received None response from LM Studio API (standard client)")
                            return "Error: No response from LM Studio API", {"model": self.model_name, "error": "null_response"}

                        if not hasattr(response, 'choices') or response.choices is None or len(response.choices) == 0:
                            logger.error(f"Invalid response format from LM Studio API (standard client): {response}")
                            return "Error: Invalid response format from LM Studio API", {"model": self.model_name, "error": "invalid_response_format"}

                        if not hasattr(response.choices[0], 'message') or response.choices[0].message is None:
                            logger.error(f"No message in response from LM Studio API (standard client): {response.choices[0]}")
                            return "Error: No message in response from LM Studio API", {"model": self.model_name, "error": "no_message"}

                        content = response.choices[0].message.content

                        # Check for empty content from standard client as well
                        if not content:
                             logger.error("Received empty content from standard LM Studio API client.")
                             return "Error: Empty content from LM Studio API", {"model": self.model_name, "error": "empty_content"}

                        # Metadata for standard API client
                        metadata = {
                            "model": self.model_name,
                            "usage": {
                                "prompt_tokens": getattr(response.usage, 'prompt_tokens', -1),
                                "completion_tokens": getattr(response.usage, 'completion_tokens', -1),
                                "total_tokens": getattr(response.usage, 'total_tokens', -1),
                            }
                        }
                        return content, metadata

                    except Exception as e:
                        # This catches errors specifically from the standard client fallback attempt
                        logger.error(f"Error in LM Studio API completion (standard client fallback failed): {e}", exc_info=True)
                        # Check for connection errors specifically
                        if "Connection refused" in str(e) or "Failed to connect" in str(e):
                            raise ConnectionError(f"Could not connect to LM Studio API at {self.api_base}. Is it running?") from e
                        raise # Re-raise other errors from standard client
                else:
                    # If fixed client failed and standard client wasn't even initialized
                    logger.error("Fixed LMStudioClient failed, and no standard client available for fallback.")
                    raise fixed_client_error # Re-raise the original error from the fixed client

        # Neither local model nor API clients were initialized successfully in __init__
        else:
            logger.error("LMStudioLLM complete called but neither local model nor API clients are initialized.")
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
                return TokenCounter.count_tokens(text, model_for_tiktoken) # Added return here
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
        elif provider.lower() == "local": # Changed from lm_studio to local to match config.yaml api_type
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
        llm_config = config.get_llm_config() # Get the LLMConfig object for the active LLM
        provider = llm_config.api_type  # Get the provider name (api_type)
        
        # Pass the dictionary representation of the active LLM's config
        return LLMFactory.create(provider, llm_config.model_dump())
    except Exception as e:
        logger.error(f"Error creating default LLM: {e}", exc_info=True) # Added exc_info
        raise  # Don't fall back to OpenAI, let the error propagate
