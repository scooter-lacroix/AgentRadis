"""
Enhanced RollingWindowMemory class with token-aware summarization and message prioritization.
This extends the existing implementation in app/memory.py.
"""
from typing import List, Optional, Dict, Any
import tiktoken
from app.logger import get_logger
from app.schema.models import Message
from app.schema.types import Role

logger = get_logger(__name__)

class MessagePriority:
    """Priority levels for messages in memory."""
    CRITICAL = 100  # Will never be summarized or removed (system instructions, critical context)
    HIGH = 80       # Important messages (key user requests, important insights)
    MEDIUM = 50     # Standard messages (normal conversation)
    LOW = 20        # Less important messages (can be summarized or removed first)
    
    @staticmethod
    def get_default_priority(message: Message) -> int:
        """Determine default priority based on message type and content."""
        if message.role == Role.SYSTEM:
            return MessagePriority.CRITICAL
        
        # First user message gets higher priority
        if message.role == Role.USER and message.content and len(message.content) > 0:
            return MessagePriority.HIGH
            
        # Messages with tool calls are important
        if message.tool_calls and len(message.tool_calls) > 0:
            return MessagePriority.HIGH
            
        # Tool responses are probably important context
        if message.role == Role.TOOL:
            return MessagePriority.HIGH
            
        # Default to medium priority
        return MessagePriority.MEDIUM

class TokenAwareRollingWindowMemory:
    def __init__(self, model: str = "gpt-4", max_tokens: int = 16000, 
                preserve_system_prompt: bool = True, preserve_first_user_message: bool = True,
                model_name: str = None, summarization_threshold: float = 0.85):
        """Initialize a token-aware rolling window memory with prioritization.

        Args:
            model: The model name to use for token counting
            max_tokens: Maximum number of tokens to retain in memory
            preserve_system_prompt: Whether to preserve the system prompt
            preserve_first_user_message: Whether to preserve the first user message
            model_name: Alternative name for model parameter
            summarization_threshold: Threshold (percentage of max_tokens) to trigger summarization
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
        self.message_metadata: Dict[int, Dict[str, Any]] = {}  # Store metadata by message id
        self.system_message: Optional[Message] = None
        self.first_user_message: Optional[Message] = None
        self.preserve_system_prompt = preserve_system_prompt
        self.preserve_first_user_message = preserve_first_user_message
        self.summarization_threshold = summarization_threshold
        
        # Counter for assigning unique IDs to messages
        self._next_message_id = 1

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

    def _get_message_id(self, message: Message) -> int:
        """Get or assign an ID for a message."""
        # Check if it already has an ID in our metadata
        for msg_id, metadata in self.message_metadata.items():
            if metadata.get("message") is message:
                return msg_id
                
        # Assign a new ID
        msg_id = self._next_message_id
        self._next_message_id += 1
        return msg_id

    def add_message(self, message: Optional[Message] = None, role: Optional[str] = None, 
                   content: Optional[str] = None, priority: Optional[int] = None) -> None:
        """Add a message to memory with optional priority metadata.
        
        Args:
            message: A Message object containing role and content
            role: The role of the message (used if message is None)
            content: The content of the message (used if message is None)
            priority: Priority level for this message (defaults to auto-detected priority)
        """
        if message is None:
            if role is None or content is None:
                raise ValueError("Must provide either a Message object or both role and content")
            message = Message(role=Role(role), content=content)
            
        if message.role == Role.SYSTEM:
            self.system_message = message
            msg_id = self._get_message_id(message)
            self.message_metadata[msg_id] = {
                "message": message,
                "priority": MessagePriority.CRITICAL,  # System messages are always critical
                "time_added": time.time()
            }
            return

        if message.role == Role.USER and not self.first_user_message:
            self.first_user_message = message
            
        # Add message to memory
        self.messages.append(message)
        
        # Set or auto-detect priority
        if priority is None:
            priority = MessagePriority.get_default_priority(message)
            
        # Store metadata
        msg_id = self._get_message_id(message)
        self.message_metadata[msg_id] = {
            "message": message,
            "priority": priority,
            "time_added": time.time()
        }
        
        # Check if we need to summarize or truncate
        current_tokens = self.get_current_token_count()
        if current_tokens > self.max_tokens * self.summarization_threshold:
            if current_tokens > self.max_tokens:
                # Over limit - must truncate
                self._truncate_messages()
            else:
                # Approaching limit - consider summarization
                self._summarize_low_priority_messages()

        logger.debug(f"Added message. Total messages: {len(self.messages)}")
        logger.debug(f"Current token count: {self.get_current_token_count()}")

    def _truncate_messages(self) -> None:
        """Truncate memory if token count exceeds maximum, respecting priorities."""
        # Skip if we don't have enough messages
        if len(self.messages) <= 2:
            return
            
        # Sort messages by priority (lower first) and then time (older first)
        sorted_messages = []
        for i, msg in enumerate(self.messages):
            msg_id = self._get_message_id(msg)
            metadata = self.message_metadata.get(msg_id, {})
            priority = metadata.get("priority", MessagePriority.MEDIUM)
            time_added = metadata.get("time_added", 0)
            
            # Skip preserved messages
            if (self.preserve_system_prompt and msg == self.system_message or
                self.preserve_first_user_message and msg == self.first_user_message):
                continue
                
            sorted_messages.append((msg, i, priority, time_added))
            
        # Sort by priority (lower first) and then by time (older first)
        sorted_messages.sort(key=lambda x: (x[2], x[3]))
        
        # Remove messages until we're under the token limit
        while self.get_current_token_count() > self.max_tokens and sorted_messages:
            msg, index, _, _ = sorted_messages.pop(0)
            msg_id = self._get_message_id(msg)
            
            # Remove message and its metadata
            if msg in self.messages:
                self.messages.remove(msg)
                logger.debug(f"Removed message at index {index} with priority {self.message_metadata[msg_id]['priority']} to stay within token limit")
                
            # Clean up metadata
            if msg_id in self.message_metadata:
                del self.message_metadata[msg_id]

    def _summarize_low_priority_messages(self) -> None:
        """Attempt to summarize low-priority messages to save token space."""
        # This is a placeholder for actual summarization logic
        # In a full implementation, you would:
        # 1. Identify groups of messages that can be summarized (e.g., sequential MEDIUM or LOW priority)
        # 2. Use an LLM to generate a summary
        # 3. Replace the original messages with the summary
        
        # For now, we'll just log that summarization would happen
        logger.info("Token count approaching limit, summarization would occur here")
        
        # As a simple implementation, we'll just remove some low-priority messages
        if self.get_current_token_count() > self.max_tokens * 0.9:
            to_remove = []
            for msg in self.messages:
                msg_id = self._get_message_id(msg)
                metadata = self.message_metadata.get(msg_id, {})
                priority = metadata.get("priority", MessagePriority.MEDIUM)
                
                if priority <= MessagePriority.LOW:
                    to_remove.append(msg)
                    
                # Don't remove too many at once
                if len(to_remove) >= 2:
                    break
                    
            for msg in to_remove:
                msg_id = self._get_message_id(msg)
                if msg in self.messages:
                    self.messages.remove(msg)
                    
                # Clean up metadata
                if msg_id in self.message_metadata:
                    del self.message_metadata[msg_id]
                    
            if to_remove:
                logger.debug(f"Removed {len(to_remove)} low-priority messages to save token space")
    
    def get_message_priority(self, message: Message) -> int:
        """Get the priority level for a specific message."""
        msg_id = self._get_message_id(message)
        metadata = self.message_metadata.get(msg_id, {})
        return metadata.get("priority", MessagePriority.MEDIUM)
        
    def set_message_priority(self, message: Message, priority: int) -> None:
        """Update the priority of a specific message."""
        msg_id = self._get_message_id(message)
        if msg_id in self.message_metadata:
            self.message_metadata[msg_id]["priority"] = priority
        else:
            # Message not in metadata, create entry
            self.message_metadata[msg_id] = {
                "message": message,
                "priority": priority,
                "time_added": time.time()
            }

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
        
        # Preserve system message metadata if it exists
        if preserved_system:
            sys_msg_id = next((msg_id for msg_id, metadata in self.message_metadata.items() 
                            if metadata.get("message") is preserved_system), None)
                
            # Clear metadata except for system message
            preserved_metadata = self.message_metadata.get(sys_msg_id, {}) if sys_msg_id else {}
            self.message_metadata = {}
            
            if sys_msg_id:
                self.message_metadata[sys_msg_id] = preserved_metadata
        else:
            self.message_metadata = {}
            
        self.first_user_message = None
        self.system_message = preserved_system
        logger.debug("Memory cleared, preserved system message if present")

    def get_recent_messages(self, n: int) -> List[Message]:
        """Get the n most recent messages."""
        return self.messages[-n:] if n > 0 else []
        
    def get_prioritized_messages(self, min_priority: int = MessagePriority.MEDIUM) -> List[Message]:
        """Get all messages with at least the specified priority level."""
        result = []
        
        # Include system message if it exists (always high priority)
        if self.system_message:
            result.append(self.system_message)
            
        # Filter messages by priority
        for msg in self.messages:
            msg_id = self._get_message_id(msg)
            metadata = self.message_metadata.get(msg_id, {})
            priority = metadata.get("priority", MessagePriority.MEDIUM)
            
            if priority >= min_priority:
                result.append(msg)
                
        return result
