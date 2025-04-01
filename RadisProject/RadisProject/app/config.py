from pathlib import Path
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator

class RadisConfig(BaseModel):
    """Configuration for Radis application settings."""
    
    # Base paths
    app_dir: Path = Field(
        default=Path.home() / ".radis",
        description="Root directory for Radis application data"
    )
    config_dir: Path = Field(
        default=Path.home() / ".radis/config",
        description="Directory for configuration files"
    )
    data_dir: Path = Field(
        default=Path.home() / ".radis/data",
        description="Directory for application data storage"
    )
    cache_dir: Path = Field(
        default=Path.home() / ".radis/cache",
        description="Directory for cached data"
    )
    
    # Application settings
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level for the application"
    )
    max_history: int = Field(
        default=1000,
        description="Maximum number of history entries to keep",
        gt=0
    )
    
    # Security settings
    enable_telemetry: bool = Field(
        default=True,
        description="Enable anonymous usage statistics"
    )
    allow_remote_connections: bool = Field(
        default=False,
        description="Allow connections from non-localhost sources"
    )
    trusted_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="List of trusted host addresses"
    )
    
    # Database settings
    db_path: Path = Field(
        default=None,
        description="Path to the SQLite database file"
    )
    
    @field_validator("*_dir", "db_path", mode="before")
    @classmethod
    def validate_path(cls, value: Union[str, Path], info) -> Path:
        """Validate and convert path fields to Path objects."""
        if value is None and info.field_name == "db_path":
            return None
            
        path = Path(value).expanduser().resolve()
        if info.field_name != "db_path":  # Don't create db_path
            path.mkdir(parents=True, exist_ok=True)
        return path
        
    @model_validator(mode="after")
    def validate_config(self) -> 'RadisConfig':
        """Validate the complete configuration."""
        # Set db_path default if not specified
        if self.db_path is None:
            self.db_path = self.data_dir / "radis.db"
            
        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
            
        return self
        
    def ensure_dirs(self) -> None:
        """Ensure all required directories exist."""
        for dir_name in ["app_dir", "config_dir", "data_dir", "cache_dir"]:
            getattr(self, dir_name).mkdir(parents=True, exist_ok=True)
            
    def get_path(self, name: str) -> Path:
        """Get a Path object for a named configuration directory."""
        if hasattr(self, f"{name}_dir"):
            return getattr(self, f"{name}_dir")
        raise ValueError(f"Unknown path name: {name}")
        
    def get_file_path(self, name: str, create_parents: bool = True) -> Path:
        """Get a Path object for a file in the data directory."""
        path = self.data_dir / name
        if create_parents:
            path.parent.mkdir(parents=True, exist_ok=True)
        return path
        
    def to_dict(self) -> Dict:
        """Convert configuration to a dictionary with string paths."""
        config_dict = self.model_dump()
        # Convert Path objects to strings
        for key, value in config_dict.items():
            if isinstance(value, Path):
                config_dict[key] = str(value)
        return config_dict

class LLMConfig(BaseModel):
    """Configuration for language model settings."""
    
    # Core API settings
    api_type: str = Field(
        default="local",
        description="Type of API to use (local, openai, anthropic, etc)"
    )
    model: str = Field(
        default="mistralai/mistral-7b-instruct",
        description="Name of the model to use"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication"
    )
    api_base: Optional[str] = Field(
        default="http://127.0.0.1:1234/",
        description="Base URL for API endpoint"
    )
    
    # Model settings
    fallback_model: Optional[str] = Field(
        default=None,
        description="Fallback model to use if primary model fails"
    )
    model_path: Optional[str] = Field(
        default=None,
        description="Path to local model file"
    )
    tokenizer: Optional[str] = Field(
        default=None,
        description="Tokenizer to use for the model"
    )
    
    # Generation settings
    temperature: float = Field(
        default=0.7,
        description="Sampling temperature",
        ge=0.0,
        le=2.0
    )
    max_tokens: int = Field(
        default=4096,
        description="Maximum tokens to generate",
        gt=0
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts",
        ge=0
    )
    timeout: float = Field(
        default=120.0,
        description="API request timeout in seconds",
        gt=0
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream responses"
    )
    
    # Internal settings
    _default_config: bool = Field(
        default=False,
        description="Whether this is a default configuration",
        exclude=True
    )
    @field_validator("api_key", mode="before")
    @classmethod
    def validate_api_key(cls, value: Optional[str], info) -> Optional[str]:
        """Validate and process API key."""
        if value:
            return value
            
        # Check environment variables based on api_type
        if "values" in info.data:
            api_type = info.data.get("api_type", "local")
            env_var = f"AGENTRADIS_{api_type.upper()}_API_KEY"
            env_key = os.getenv(env_var)
            if env_key:
                return env_key
                
        # Default for local LLMs
        if "values" in info.data and info.data.get("api_type") == "local":
            return "lm-studio"
            
        return value

    @field_validator("api_base", mode="before")
    @classmethod
    def validate_api_base(cls, value: Optional[str], info) -> Optional[str]:
        """Validate API base URL."""
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("API base URL must start with http:// or https://")
        return value

    @model_validator(mode='after')
    def validate_api_config(self) -> 'LLMConfig':
        """Validate full configuration."""
        # Validate local LLM configuration
        if self.api_type == "local" and not (self.model_path or self.api_base):
            raise ValueError(
                "For local LLMs, either 'model_path' (for local models) or "
                "'api_base' (for LM Studio API) must be configured."
            )
        
        # Set tokenizer defaults based on api_type
        if not self.tokenizer:
            tokenizer_map = {
                "anthropic": "claude",
                "local": "llama2",
                "default": "gpt2"
            }
            self.tokenizer = tokenizer_map.get(self.api_type, tokenizer_map["default"])
        
        return self
