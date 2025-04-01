"""
Enum definitions for the Radis system.
"""

from enum import Enum


class LogLevel(str, Enum):
    """Log level enum."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LLMType(str, Enum):
    """Enum for LLM service types."""
    OPENAI = "openai"
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LMSTUDIO = "lm_studio"
    CUSTOM = "custom"
    GPT4_TURBO = "gpt-4-turbo"
    GPT35_TURBO = "gpt-3.5-turbo"
    GEMMA34B = "gemma-3.4b"
    MISTRAL_MEDIUM = "mistral-medium"
    MISTRAL_SMALL = "mistral-small"
    CLAUDE3_OPUS = "claude-3-opus"
    CLAUDE3_SONNET = "claude-3-sonnet"
