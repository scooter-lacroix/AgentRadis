from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class SecurityConfig:
    """Security configuration for the agent."""

    enabled: bool = True
    allowed_commands: List[str] = field(default_factory=list)
    blocked_commands: List[str] = field(default_factory=list)
    max_command_length: int = 1000
    max_output_size: int = 10 * 1024 * 1024  # 10MB
    safe_mode: bool = True
    allowed_paths: List[str] = field(default_factory=list)
    restricted_paths: List[str] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    timeout: int = 300  # seconds
    command_rate_limit: int = 10  # commands per minute
    require_confirmation: bool = True
    logging_enabled: bool = True
    validation_rules: Dict[str, str] = field(default_factory=dict)
    project_root: Optional[str] = None
