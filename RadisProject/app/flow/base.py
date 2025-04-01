"""Base flow module defining flow types and interfaces.

This module provides base classes and enums for different flow types in
the application, ensuring consistent interface across flow implementations.
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

from app.config import config, RadisConfig
from app.schema.models import Message
from app.conversation import Conversation


class FlowType(str, Enum):
    """Enumeration of available flow types."""

    BASIC = "basic"
    PLANNING = "planning"
    TOOL = "tool"
    STREAMING = "streaming"


@dataclass
class FlowConfig:
    """Configuration for a flow instance."""

    flow_type: FlowType
    system_message: str
    initial_context: Optional[Dict[str, Any]] = None
    max_turns: int = 10
    timeout: int = 300  # seconds


class BaseFlow:
    """Base class for all flow implementations."""

    def __init__(self, config: RadisConfig, flow_config: FlowConfig):
        """Initialize the flow.

        Args:
            config: Application configuration
            flow_config: Flow-specific configuration
        """
        self.config = config
        self.flow_config = flow_config
        self.conversation = Conversation(config=config)
        self._initialize()

    def _initialize(self) -> None:
        """Initialize the flow with system message and context."""
        self.conversation.add_message(
            Message(role="system", content=self.flow_config.system_message)
        )
        if self.flow_config.initial_context:
            self.conversation.set_context(self.flow_config.initial_context)
