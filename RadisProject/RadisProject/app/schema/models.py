from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from app.schema.types import Role


@dataclass
class Message:
    """A class representing a message in a conversation."""
    role: Role
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __eq__(self, other):
        if not isinstance(other, Message):
            return False
        return (self.role == other.role and 
                self.content == other.content)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary representation."""
        return {
            "role": self.role.value,
            "content": self.content,
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create a Message object from a dictionary."""
        role_value = data.get("role")
        role = Role(role_value) if isinstance(role_value, str) else role_value
        return cls(
            role=role,
            content=data.get("content", ""),
            metadata=data.get("metadata", {})
        )

from dataclasses import dataclass
from typing import Optional, Any

from app.schema.types import Role


@dataclass
class Message:
    """
    Represents a message in a conversation.
    
    Attributes:
        role: The role of the entity that created the message (e.g. USER, ASSISTANT)
        content: The content of the message
    """
    role: Role
    content: str
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Message):
            return False
        return self.role == other.role and self.content == other.content

