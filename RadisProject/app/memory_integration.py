"""
Memory integration module for RadisAgent.

This module provides functions for upgrading and monitoring memory usage in RadisAgent.
"""

from typing import Dict, Any, Optional, Union
import logging

from app.memory import RollingWindowMemory
from app.agent.memory import AgentMemory as AgentMemoryImplementation
from app.schema.memory import AgentMemory as AgentMemorySchema
from app.logger import get_logger

logger = get_logger(__name__)

def upgrade_memory(memory: Union[RollingWindowMemory, AgentMemoryImplementation, AgentMemorySchema]) -> Union[RollingWindowMemory, AgentMemoryImplementation]:
    """
    Upgrade memory from one implementation to another if needed.
    
    Args:
        memory: The memory instance to upgrade
        
    Returns:
        Upgraded memory instance
    """
    logger.debug(f"Upgrading memory of type {type(memory).__name__}")
    
    # If it's already a RollingWindowMemory, no need to upgrade
    if isinstance(memory, RollingWindowMemory):
        return memory
        
    # If it's an AgentMemoryImplementation, no need to upgrade
    if isinstance(memory, AgentMemoryImplementation):
        return memory
        
    # If it's an AgentMemorySchema, convert to implementation
    if isinstance(memory, AgentMemorySchema):
        new_memory = AgentMemoryImplementation()
        # Transfer messages
        for message in memory.messages:
            new_memory.add(message)
        logger.info(f"Upgraded AgentMemorySchema to AgentMemoryImplementation")
        return new_memory
        
    # If it's None or another type, create a new default memory
    logger.warning(f"Unknown memory type {type(memory).__name__}, creating new RollingWindowMemory")
    return RollingWindowMemory()

def get_memory_stats(memory: Union[RollingWindowMemory, AgentMemoryImplementation, AgentMemorySchema]) -> Dict[str, Any]:
    """
    Get statistics about memory usage.
    
    Args:
        memory: Memory instance to analyze
        
    Returns:
        Dictionary with memory statistics
    """
    stats = {
        "type": type(memory).__name__,
        "message_count": 0,
        "token_count": 0,
        "has_system_message": False
    }
    
    if isinstance(memory, RollingWindowMemory):
        stats["message_count"] = len(memory.messages)
        stats["token_count"] = memory.get_current_token_count()
        stats["has_system_message"] = memory.system_message is not None
        stats["max_tokens"] = memory.max_tokens
        
    elif isinstance(memory, AgentMemoryImplementation):
        stats["message_count"] = len(memory.messages)
        stats["token_count"] = memory.get_token_count()
        stats["has_system_message"] = any(msg.role.value == "system" for msg in memory.messages)
        stats["max_tokens"] = memory.max_tokens if hasattr(memory, "max_tokens") else None
        
    elif isinstance(memory, AgentMemorySchema):
        stats["message_count"] = len(memory.messages)
        stats["has_system_message"] = any(msg.get("role") == "system" for msg in memory.messages)
        
    logger.debug(f"Memory stats: {stats}")
    return stats
