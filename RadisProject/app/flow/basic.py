"""Basic flow implementation for simple conversations.

This module implements a basic conversation flow that handles
straightforward request-response interactions.
"""

from typing import Dict, Any
from datetime import datetime

from app.config import config, RadisConfig
from app.schema.models import Message
from app.schema.types import Role, Status
from .base import BaseFlow, FlowConfig


class BasicFlow(BaseFlow):
    """Flow implementation for basic conversations."""

    def __init__(self, config: RadisConfig, flow_config: FlowConfig):
        """Initialize the basic flow.

        Args:
            config: Application configuration
            flow_config: Flow-specific configuration
        """
        super().__init__(config, flow_config)

    async def execute(self, prompt: str) -> Dict[str, Any]:
        """Execute the basic flow.

        Args:
            prompt: User's request or message

        Returns:
            Dictionary containing the response
        """
        # Add user message to conversation
        self.conversation.add_message(Message(role=Role.USER, content=prompt))

        try:
            # TODO: Implement basic response generation logic here
            response = "This is a placeholder response from the basic flow."

            # Add assistant response to conversation
            self.conversation.add_message(
                Message(role=Role.ASSISTANT, content=response)
            )

            return {
                "status": "success",
                "response": response,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
