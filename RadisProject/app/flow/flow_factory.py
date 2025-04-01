"""Factory module for creating conversation flows.

This module provides factory methods for creating and configuring
different types of conversation flows based on the application needs.
"""

from typing import Dict, Optional, Type

from app.config import config, RadisConfig
from app.schema.models import Message
from app.schema.types import Role
from .base import FlowType, FlowConfig, BaseFlow


class FlowFactory:
    """Factory class for creating conversation flows."""

    def __init__(self, config: RadisConfig):
        """Initialize the flow factory.

        Args:
            config: Application configuration instance
        """
        self.config = config

    def create_flow(
        self,
        flow_type: FlowType,
        system_message: str,
        initial_context: Optional[Dict] = None,
        max_turns: int = 10,
        timeout: int = 300,
    ) -> BaseFlow:
        """Create a new conversation flow.

        Args:
            flow_type: Type of flow to create
            system_message: The system message to initialize the flow
            initial_context: Optional initial context for the flow
            max_turns: Maximum number of conversation turns
            timeout: Timeout in seconds for the flow

        Returns:
            A new BaseFlow instance configured with the given parameters
        """
        flow_config = FlowConfig(
            flow_type=flow_type,
            system_message=system_message,
            initial_context=initial_context,
            max_turns=max_turns,
            timeout=timeout,
        )

        if flow_type == FlowType.PLANNING:
            from .planning import PlanningFlow

            return PlanningFlow(self.config, flow_config)
        elif flow_type == FlowType.TOOL:
            from .tool import ToolFlow

            return ToolFlow(self.config, flow_config)
        elif flow_type == FlowType.STREAMING:
            from .streaming import StreamingFlow

            return StreamingFlow(self.config, flow_config)
        else:
            from .basic import BasicFlow

            return BasicFlow(self.config, flow_config)

    @classmethod
    def create_flow_type(cls, flow_type: str) -> FlowType:
        """Create a FlowType enum from a string.

        Args:
            flow_type: String representation of the flow type

        Returns:
            Corresponding FlowType enum value

        Raises:
            ValueError: If the flow type is not recognized
        """
        try:
            return FlowType(flow_type.lower())
        except ValueError:
            raise ValueError(f"Unknown flow type: {flow_type}")
