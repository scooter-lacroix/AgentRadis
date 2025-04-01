from typing import List, Optional

from app.schema.models import Message


class RollingWindowMemory:
    """
    A memory implementation that maintains a rolling window of messages.
    It stores messages up to a specified maximum count.
    """

    def __init__(self, max_messages: int = 100):
        """
        Initialize the RollingWindowMemory.

        Args:
            max_messages: The maximum number of messages to store (default: 100)
        """
        self.messages: List[Message] = []
        self.max_messages = max_messages

    def add_message(self, message: Message) -> None:
        """
        Add a message to the memory.
        If the number of messages exceeds max_messages, the oldest messages are removed.

        Args:
            message: The message to add to memory
        """
        self.messages.append(message)
        
        # Remove oldest messages if we exceed the maximum
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def clear(self) -> None:
        """
        Clear all messages from memory.
        """
        self.messages = []

    def get_messages(self) -> List[Message]:
        """
        Get all messages in memory.

        Returns:
            A list of all messages currently in memory
        """
        return self.messages

