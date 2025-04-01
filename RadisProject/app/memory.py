from typing import List, Optional
import tiktoken
from app.logger import get_logger
from app.schema.models import Message
from app.schema.types import Role

logger = get_logger(__name__)


class RollingWindowMemory:
    def __init__(self, model: str = "gpt-4", max_tokens: int = 16000, 
                  preserve_system_prompt: bool = False, preserve_first_user_message: bool = False,
                  model_name: str = None):
        """Initialize a rolling window memory with token counting.

        Args:
            model: The model name to use for token counting
            max_tokens: Maximum number of tokens to retain in memory
            preserve_system_prompt: Whether to preserve the system prompt
            preserve_first_user_message: Whether to preserve the first user message
            model_name: Alternative name for model parameter
        """
        # Use model_name if provided, otherwise use model
        model_to_use = model_name if model_name is not None else model
        
        try:
            self.encoding = tiktoken.encoding_for_model(model_to_use)
        except KeyError:
            # Fallback for models not supported by tiktoken
            logger.warning(f"Model {model_to_use} not supported by tiktoken, using cl100k_base encoding")
            self.encoding = tiktoken.get_encoding("cl100k_base")
        self.max_tokens = max_tokens
        self.messages: List[Message] = []
        self.system_message: Optional[Message] = None
        self.first_user_message: Optional[Message] = None
        self.preserve_system_prompt = preserve_system_prompt
        self.preserve_first_user_message = preserve_first_user_message

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        return len(self.encoding.encode(text))

    def count_message_tokens(self, message: Message) -> int:
        """Count tokens in a message including role and content."""
        tokens = self.count_tokens(isinstance(message.role, str) and message.role or message.role.value)
        tokens += self.count_tokens(message.content or "")
        if message.name:
            tokens += self.count_tokens(message.name)
        return tokens

    def get_current_token_count(self) -> int:
        """Get total token count for all messages in memory."""
        return sum(self.count_message_tokens(msg) for msg in self.messages)

    def add_message(self, message: Optional[Message] = None, role: Optional[str] = None, content: Optional[str] = None) -> None:
        """Add a message to memory, preserving system and first user messages.
        
        Supports two usage patterns:
        1. Single Message object: add_message(message=Message(...))
        2. Separate parameters: add_message(role="user", content="hello")
        
        Args:
            message: A Message object containing role and content
            role: The role of the message (used if message is None)
            content: The content of the message (used if message is None)
        """
        if message is None:
            if role is None or content is None:
                raise ValueError("Must provide either a Message object or both role and content")
            message = Message(role=Role(role), content=content)
            
        if message.role == Role.SYSTEM:
            self.system_message = message
            return

        if message.role == Role.USER and not self.first_user_message:
            self.first_user_message = message

        self.messages.append(message)
        self._truncate_if_needed()

        logger.debug(f"Added message. Total messages: {len(self.messages)}")
        logger.debug(f"Current token count: {self.get_current_token_count()}")

    def _truncate_if_needed(self) -> None:
        """Truncate memory if token count exceeds maximum, preserving key messages."""
        while (
            self.get_current_token_count() > self.max_tokens and len(self.messages) > 2
        ):
            # Keep most recent messages, remove oldest non-preserved messages
            for i, msg in enumerate(self.messages):
                should_preserve = False
                
                # Check if we should preserve system messages
                if self.preserve_system_prompt and msg == self.system_message:
                    should_preserve = True
                    
                # Check if we should preserve first user message
                if self.preserve_first_user_message and msg == self.first_user_message:
                    should_preserve = True
                    
                if not should_preserve:
                    logger.debug(
                        f"Removing message at index {i} to stay within token limit"
                    )
                    self.messages.pop(i)
                    break

    def get_messages(self) -> List[Message]:
        """Get all messages in chronological order."""
        messages = []
        if self.system_message:
            messages.append(self.system_message)
        messages.extend(self.messages)
        return messages

    def clear(self) -> None:
        """Clear all messages except system message."""
        preserved_system = self.system_message
        self.messages = []
        self.first_user_message = None
        self.system_message = preserved_system
        logger.debug("Memory cleared, preserved system message if present")

    def load_messages(self, messages: List[Message]) -> None:
        """Load a list of messages, respecting special message types."""
        self.clear()
        for message in messages:
            self.add_message(message)

    def get_recent_messages(self, n: int) -> List[Message]:
        """Get the n most recent messages."""
        return self.messages[-n:] if n > 0 else []
