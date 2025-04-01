#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Any
import time
import tiktoken
from app.logger import get_logger
from app.schema.models import Message
from app.schema.types import Role

logger = get_logger(__name__)


class MessagePriority(Enum):
    """Defines priority levels for memory messages."""
    HIGH = 100    # Critical messages that should be preserved longest
    NORMAL = 50   # Standard messages with default priority
    LOW = 10      # Low-priority messages that can be removed first
    
    def __int__(self) -> int:
        return self.value


class RollingWindowMemory:
    def __init__(self, model: str = "gpt-4", max_tokens: int = 16000, 
                preserve_system_prompt: bool = False, preserve_first_user_message: bool = False,
                model_name: str = None):
        """Initialize a rolling window memory with token counting and message prioritization.

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
        
        # Enhancement: Message prioritization
        self.message_metadata: Dict[int, Dict[str, Any]] = {}
        self._next_message_id = 1

    def _get_message_id(self) -> int:
        """Get a unique ID for a message and increment the counter."""
        message_id = self._next_message_id
        self._next_message_id += 1
        return message_id
        
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

    def add_message(self, message: Optional[Message] = None, role: Optional[str] = None, 
                    content: Optional[str] = None, priority: MessagePriority = MessagePriority.NORMAL) -> None:
        """Add a message to memory with priority, preserving system and first user messages.
        
        Supports two usage patterns:
        1. Single Message object: add_message(message=Message(...))
        2. Separate parameters: add_message(role="user", content="hello")
        
        Args:
            message: A Message object containing role and content
            role: The role of the message (used if message is None)
            content: The content of the message (used if message is None)
            priority: Priority level for this message (affects memory retention)
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
            # Automatically assign HIGH priority to first user message
            priority = MessagePriority.HIGH

        # Assign a unique ID to the message for tracking
        message_id = self._get_message_id()
        
        # Store metadata including priority and timestamp
        self.message_metadata[message_id] = {
            "priority": priority,
            "added_time": time.time(),
            "token_count": self.count_message_tokens(message),
            "message_index": len(self.messages)
        }
        
        self.messages.append(message)
        self._prioritized_truncate()

        logger.debug(f"Added message with priority {priority}. Total messages: {len(self.messages)}")
        logger.debug(f"Current token count: {self.get_current_token_count()}")

    def _get_message_priority(self, index: int) -> Tuple[MessagePriority, float]:
        """Get the priority and timestamp of a message by its index in the messages list."""
        for message_id, metadata in self.message_metadata.items():
            if metadata.get("message_index") == index:
                return (metadata.get("priority", MessagePriority.NORMAL), 
                        metadata.get("added_time", 0))
        return (MessagePriority.NORMAL, 0)  # Default priority if not found
        
    def _prioritized_truncate(self) -> None:
        """Truncate memory if token count exceeds maximum, respecting message priorities."""
        while self.get_current_token_count() > self.max_tokens and len(self.messages) > 2:
            # Create a list of candidate messages that can be removed
            candidates = []
            for i, msg in enumerate(self.messages):
                # Skip messages that should always be preserved
                if self.preserve_system_prompt and msg == self.system_message:
                    continue
                if self.preserve_first_user_message and msg == self.first_user_message:
                    continue
                    
                # Get message priority and timestamp
                priority, timestamp = self._get_message_priority(i)
                
                # Add to candidates list
                candidates.append((i, int(priority), timestamp))
                
            if not candidates:
                # No removable candidates, we reached minimum 
                break
                
            # Sort by priority (ascending), then by timestamp (oldest first)
            candidates.sort(key=lambda x: (x[1], x[2]))
            
            # Remove the lowest priority, oldest message
            index_to_remove = candidates[0][0]
            removed_message = self.messages.pop(index_to_remove)
            
            # Clean up metadata and update indexes
            self._update_metadata_after_removal(index_to_remove)
            
            logger.debug(f"Removed message at index {index_to_remove} based on priority")
            
    def _update_metadata_after_removal(self, removed_index: int) -> None:
        """Update message metadata after removing a message."""
        # Find and remove the metadata for the removed message
        metadata_to_remove = None
        for message_id, metadata in list(self.message_metadata.items()):
            if metadata.get("message_index") == removed_index:
                metadata_to_remove = message_id
            elif metadata.get("message_index") > removed_index:
                # Update indexes that are after the removed message
                self.message_metadata[message_id]["message_index"] -= 1
                
        # Remove the metadata entry
        if metadata_to_remove is not None:
            self.message_metadata.pop(metadata_to_remove, None)

    def get_messages(self) -> List[Message]:
        """Get all messages in chronological order."""
        messages = []
        if self.system_message:
            messages.append(self.system_message)
        messages.extend(self.messages)
        return messages
        
    def get_prioritized_messages(self, min_priority: MessagePriority = None) -> List[Message]:
        """
        Get messages filtered by minimum priority level.
        
        Args:
            min_priority: Minimum priority level to include (None returns all)
            
        Returns:
            List of messages with priority >= min_priority
        """
        if min_priority is None:
            return self.get_messages()
            
        filtered_messages = []
        if self.system_message:
            filtered_messages.append(self.system_message)
            
        for i, message in enumerate(self.messages):
            priority, _ = self._get_message_priority(i)
            if int(priority) >= int(min_priority):
                filtered_messages.append(message)
                
        return filtered_messages

    def clear(self) -> None:
        """Clear all messages except system message."""
        preserved_system = self.system_message
        self.messages = []
        self.first_user_message = None
        self.system_message = preserved_system
        
        # Clear metadata
        self.message_metadata = {}
        self._next_message_id = 1
        
        logger.debug("Memory cleared, preserved system message if present")

    def load_messages(self, messages: List[Message]) -> None:
        """Load a list of messages, respecting special message types."""
        self.clear()
        for message in messages:
            self.add_message(message)

    def get_recent_messages(self, n: int) -> List[Message]:
        """Get the n most recent messages."""
        return self.messages[-n:] if n > 0 else []
