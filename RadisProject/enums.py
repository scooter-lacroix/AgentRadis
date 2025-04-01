"""Enumeration types for configuration and models.

This module contains enums used for system configuration, logging, and LLM
models and their configurations.
"""

from enum import Enum
from typing import List


class LLMType(str, Enum):
    """Type of Language Model to use."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"
    LLAMA = "llama"
    LOCAL = "local"
    CUSTOM = "custom"

    @classmethod
    def get_all_types(cls) -> List[str]:
        """Get a list of all available LLM types.

        Returns:
            List[str]: A list of all enum values as strings.
        """
        return [member.value for member in cls]


class LogLevel(str, Enum):
    """Log levels for the application."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


__all__ = ["LLMType", "LogLevel"]
