"""
Memory and state management for the Radis agent.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional


class AgentMemory(BaseModel):
    """Memory for an agent that persists across conversations."""
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Conversation history")
    context: Dict[str, Any] = Field(default_factory=dict, description="Contextual information")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    scratch: Dict[str, Any] = Field(default_factory=dict, description="Temporary scratch space")
