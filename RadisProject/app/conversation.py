"""Conversation management module.

This module implements the core conversation functionality, including
message handling, context management, and state tracking.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from app.config import config, RadisConfig
from app.config import config
from app.schema.models import Message
from app.schema.types import Role, Status


@dataclass
class Conversation:
    """Manages a conversation session with message history and context."""

    config: RadisConfig
    messages: List[Message] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    status: Status = Status.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_message(self, message: Message) -> None:
        """Add a message to the conversation history.

        Args:
            message: The message to add
        """
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_messages(self) -> List[Message]:
        """Get all messages in the conversation.

        Returns:
            List of messages in chronological order
        """
        return self.messages

    def set_context(self, context: Dict[str, Any]) -> None:
        """Set or update the conversation context.

        Args:
            context: Dictionary of context values to set
        """
        self.context.update(context)
        self.updated_at = datetime.now()

    def get_context(self, key: str) -> Optional[Any]:
        """Get a value from the conversation context.

        Args:
            key: The context key to retrieve

        Returns:
            The context value if found, None otherwise
        """
        return self.context.get(key)

    def clear(self) -> None:
        """Clear all messages and context from the conversation."""
        self.messages.clear()
        self.context.clear()
        self.updated_at = datetime.now()
