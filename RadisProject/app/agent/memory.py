from typing import Dict, List, Optional, Union
import tiktoken
from dataclasses import asdict

from ..schema.models import Message
from ..schema.types import Role
from ..logger import get_logger

logger = get_logger(__name__)


class AgentMemory:
    def __init__(self, model: str = "gpt-4", max_tokens: Optional[int] = None):
        """Initialize AgentMemory with optional token limit.

        Args:
            model (str): The model name for token counting (default: "gpt-4")
            max_tokens (Optional[int]): Maximum tokens to store (None for unlimited)
        """
        self.messages: List[Message] = []
        self.max_tokens = max_tokens
        self._encoding = tiktoken.encoding_for_model(model)

    def add(self, message: Union[Message, Dict]) -> None:
        """Add a message to memory.

        Args:
            message (Union[Message, Dict]): Message to add
        """
        if isinstance(message, dict):
            message = Message(**message)

        self.messages.append(message)

        if self.max_tokens:
            self._truncate_to_token_limit()

    def get_all(self) -> List[Message]:
        """Get all messages in memory.

        Returns:
            List[Message]: All stored messages
        """
        return self.messages

    def get_last(self, n: int = 1) -> List[Message]:
        """Get the last n messages.

        Args:
            n (int): Number of messages to return

        Returns:
            List[Message]: Last n messages
        """
        return self.messages[-n:]

    def get_by_role(self, role: Role) -> List[Message]:
        """Get all messages with specified role.

        Args:
            role (Role): Role to filter by

        Returns:
            List[Message]: Messages matching role
        """
        return [msg for msg in self.messages if msg.role == role]

    def clear(self) -> None:
        """Clear all messages from memory."""
        self.messages = []

    def get_token_count(self) -> int:
        """Get total token count of stored messages.

        Returns:
            int: Total token count
        """
        token_count = 0
        for message in self.messages:
            msg_dict = asdict(message)
            msg_str = str(msg_dict)
            token_count += len(self._encoding.encode(msg_str))
        return token_count

    def _truncate_to_token_limit(self) -> None:
        """Remove oldest messages until under token limit."""
        if not self.max_tokens:
            return

        while self.get_token_count() > self.max_tokens and self.messages:
            logger.debug(f"Memory over token limit, removing oldest message")
            self.messages.pop(0)

    def format_for_llm(self) -> List[Dict]:
        """Format messages for LLM API consumption.

        Returns:
            List[Dict]: Messages formatted for LLM
        """
        return [asdict(msg) for msg in self.messages]

    def search(self, query: str, limit: Optional[int] = None) -> List[Message]:
        """Search messages containing the query string.

        Args:
            query (str): String to search for
            limit (Optional[int]): Max results to return

        Returns:
            List[Message]: Messages containing query
        """
        results = [msg for msg in self.messages if query.lower() in msg.content.lower()]
        if limit:
            results = results[:limit]
        return results

    def add_system_message(self, content: str) -> None:
        """Add a system message.

        Args:
            content (str): System message content
        """
        self.add(Message(role=Role.SYSTEM, content=content))

    def add_user_message(self, content: str) -> None:
        """Add a user message.

        Args:
            content (str): User message content
        """
        self.add(Message(role=Role.USER, content=content))

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message.

        Args:
            content (str): Assistant message content
        """
        self.add(Message(role=Role.ASSISTANT, content=content))
