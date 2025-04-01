from enum import Enum

class Role(Enum):
    """
    Enum representing different roles in a conversation.
    
    Attributes:
        USER: Role representing the user
        ASSISTANT: Role representing the assistant
        SYSTEM: Role representing system messages
    """
    USER = "user"
    ASSISTANT = "assistant" 
    SYSTEM = "system"
