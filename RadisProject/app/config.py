"""Configuration module for AgentRadis."""

import os
import sys
import logging
import yaml
from enum import Enum
from typing import Dict, List, Optional, Union, Any, ClassVar
from pathlib import Path

from pydantic import BaseModel, Field, model_validator, field_validator, computed_field

# Import LLMType from schema.enums
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


class LLMConfig(BaseModel):
    """Configuration for language model settings."""
    api_type: str = "local"
    model: str = "mistralai/mistral-7b-instruct"
    api_key: Optional[str] = None
    api_base: Optional[str] = "http://127.0.0.1:1234/"
    fallback_model: Optional[str] = None
    model_path: Optional[str] = None
    tokenizer: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    max_retries: int = 3
    timeout: float = 120.0
    stream: bool = False
    _default_config: bool = False

    @model_validator(mode='after')
    def validate_api_config(self):
        # Simple validation for local LLMs
        if self.api_type == "local":
            if not (self.model_path or self.api_base):
                raise ValueError(
                    "For local LLMs, either 'model_path' (for local models) or 'api_base' (for LM Studio API) must be configured."
                )
            
            if not self.api_key:
                self.api_key = "lm-studio"
        
        # Tokenizer defaults
        if not self.tokenizer:
            if self.api_type == "anthropic":
                self.tokenizer = "claude"
            elif self.api_type == "local":
                self.tokenizer = "llama2"
            else:
                self.tokenizer = "gpt2"
        
        return self


class BrowserConfig(BaseModel):
    """Configuration for browser automation."""
    headless: bool = True
    executable_path: Optional[str] = None


class LoggingConfig(BaseModel):
    """Configuration for logging settings."""
    level: str = "INFO"
    file_path: str = "logs/radis.log"
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    console: bool = True


class SecurityConfig(BaseModel):
    """Configuration for security settings."""
    workspace_dir: Optional[str] = None
    allowed_tools: List[str] = Field(default_factory=list)
    max_tokens: int = 2000
    restricted_paths: List[str] = Field(default_factory=list)


class RadisConfig(BaseModel):
    """Main configuration class."""
    config_path: ClassVar[Path] = Path("config.yaml")
    active_llm: str = "lm_studio"
    llm_settings: Dict[str, LLMConfig] = {}
    browser: BrowserConfig = BrowserConfig()
    logging: LoggingConfig = LoggingConfig()

    def __init__(self, **data):
        if 'active_llm' not in data:
            data['active_llm'] = "lm_studio"
        super().__init__(**data)
        self._initialize_default_settings()

    def _initialize_default_settings(self):
        """Initialize default settings."""
        if not self.llm_settings:
            # Try to load settings from config.yaml
            yaml_settings = {}
            try:
                if self.config_path.exists():
                    with open(self.config_path, 'r') as file:
                        yaml_config = yaml.safe_load(file)
                        if yaml_config and 'llm_settings' in yaml_config:
                            yaml_settings = yaml_config['llm_settings']
            except Exception as e:
                logging.warning(f"Failed to load settings from {self.config_path}: {e}")
            
            # If yaml settings are available, convert them to LLMConfig objects
            if yaml_settings:
                default_configs = {}
                for name, settings in yaml_settings.items():
                    settings['_default_config'] = True
                    default_configs[name] = LLMConfig(**settings)
            else:
                # Fall back to default values if yaml loading fails
                default_configs = {
                    "lm_studio": LLMConfig(
                        api_type="local",
                        model="gemma-3-27b-it",  # Default model from config.yaml
                        api_base="http://127.0.0.1:1234/",
                        api_key="lm-studio",
                        _default_config=True
                    ),
                    "gpt-4-turbo": LLMConfig(
                        api_type="openai",
                        model="gpt-4-1106-preview",  # Default model from config.yaml
                        fallback_model="gpt-3.5-turbo",  # Default fallback from config.yaml
                        api_key="test-key-123",
                        _default_config=True
                    ),
                }
            self.llm_settings = default_configs

    @computed_field
    @property
    def current_llm_config(self) -> LLMConfig:
        """Get the current LLM configuration."""
        return self.get_llm_config()

    def get_llm_config(self) -> LLMConfig:
        """Get the configuration for the active LLM."""
        return self.llm_settings[self.active_llm]

    def get_security_config(self) -> SecurityConfig:
        """Returns a SecurityConfig instance."""
        return SecurityConfig()

    def get_workspace_config(self) -> Dict[str, Any]:
        """Returns workspace configuration."""
        return {"workspace_dir": os.path.join(os.getcwd(), "workspace")}

    def get(self, path: str, default: Any = None) -> Any:
        """Access config values using dot notation path."""
        current = self.model_dump()
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

# Global config instance
config = RadisConfig()
