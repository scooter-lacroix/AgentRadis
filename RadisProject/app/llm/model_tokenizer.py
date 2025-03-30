"""
Model Tokenizer Module

Provides tokenization capabilities for different LLM families.
"""

import logging
import re
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import tiktoken (may not be available in all environments)
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    logger.warning("tiktoken not available, token counting will use fallback methods")
    TIKTOKEN_AVAILABLE = False

class ModelTokenizer:
    """
    Handles tokenization for different model types.
    Provides appropriate tokenizers for different models or falls back to reasonable defaults.
    """
    
    # Mapping of model families to tiktoken encoding names
    MODEL_TO_ENCODING = {
        # LLaMA family
        "llama": "cl100k_base",
        "llama-2": "cl100k_base",
        "llama-3": "cl100k_base",
        
        # Mistral family
        "mistral": "cl100k_base",
        "mixtral": "cl100k_base",
        
        # Gemma family
        "gemma": "cl100k_base",  # Best approximation for Gemma
        
        # Qwen family
        "qwen": "cl100k_base",   # Best approximation for Qwen
        
        # Generic fallbacks
        "gpt": "cl100k_base",
        "default": "cl100k_base"
    }
    
    @classmethod
    def get_encoding_name(cls, model_name: str) -> str:
        """
        Get the appropriate tiktoken encoding name for a given model.
        
        Args:
            model_name: The name of the model
            
        Returns:
            The encoding name to use with tiktoken
        """
        if not model_name:
            return cls.MODEL_TO_ENCODING["default"]
            
        # Convert to lowercase for case-insensitive matching
        model_lower = model_name.lower()
        
        # Check each model family prefix
        for family, encoding in cls.MODEL_TO_ENCODING.items():
            if family in model_lower:
                logger.info(f"Using {encoding} encoding for {model_name}")
                return encoding
                
        # If no match, use default encoding
        logger.info(f"No specific encoding for {model_name}, using default encoding")
        return cls.MODEL_TO_ENCODING["default"]
    
    @classmethod
    def get_tokenizer(cls, model_name: str) -> Callable[[str], int]:
        """
        Get a tokenizer function for the specified model.
        
        Args:
            model_name: The name of the model
            
        Returns:
            A tokenizer function that counts tokens in text
        """
        if TIKTOKEN_AVAILABLE:
            try:
                encoding_name = cls.get_encoding_name(model_name)
                encoding = tiktoken.get_encoding(encoding_name)
                
                def tiktoken_tokenizer(text: str) -> int:
                    """Count tokens using tiktoken"""
                    if not text:
                        return 0
                    return len(encoding.encode(text))
                        
                return tiktoken_tokenizer
            except Exception as e:
                logger.warning(f"Error creating tiktoken tokenizer: {e}")
                # Fall through to the fallback tokenizer
        
        # Fallback tokenizer: rough approximation
        def fallback_tokenizer(text: str) -> int:
            """Approximate token count when tiktoken is unavailable"""
            if not text:
                return 0
            # Simple approximation: average English word is ~1.3 tokens
            words = text.split()
            return int(len(words) * 1.3) + 1
        
        logger.info(f"Using fallback tokenizer for {model_name}")
        return fallback_tokenizer
