"""
Simplified RollingWindowMemory class enhancements.
This adds message prioritization to the existing implementation.
"""
from typing import List, Optional, Dict, Any
import time
from app.schema.models import Message
from app.schema.types import Role

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

# The methods to add to the existing RollingWindowMemory class:

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

def add_message_with_priority(self, message: Message, priority: int = None) -> None:
    """
    Add a message to memory with specified priority.
    
    Args:
        message: Message object to add
        priority: Priority level (use MessagePriority constants)
    """
    # Use the existing add_message method first
    self.add_message(message)
    
    # Then add priority metadata
    if priority is None:
        priority = MessagePriority.get_default_priority(message)
        
    msg_id = self._get_message_id(message)
    self.message_metadata[msg_id] = {
        "message": message,
        "priority": priority,
        "time_added": time.time()
    }

def _prioritized_truncate(self) -> None:
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
            
        # Clean up metadata
        if msg_id in self.message_metadata:
            del self.message_metadata[msg_id]

def get_prioritized_messages(self, min_priority: int = MessagePriority.MEDIUM) -> List[Message]:
    """
    Get all messages with at least the specified priority level.
    
    Args:
        min_priority: Minimum priority level to include
        
    Returns:
        List of messages matching or exceeding the priority level
    """
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
