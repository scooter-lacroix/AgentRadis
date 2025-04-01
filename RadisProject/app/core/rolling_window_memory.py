from collections import deque
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Deque, List, Optional, TypeVar, Generic

from .context_manager import ContextManager

T = TypeVar('T')

@dataclass
class MemoryEntry(Generic[T]):
    """Represents a single entry in the conversation memory."""
    content: T
    timestamp: datetime
    metadata: dict

class RollingWindowMemory(Generic[T]):
    """
    A thread-safe implementation of a fixed-size rolling window memory for conversation history.
    
    This class maintains a fixed-size window of conversation history, automatically removing
    older entries when the window size is exceeded. It is designed to be thread-safe and
    integrates with the ContextManager for persistent storage.
    
    Attributes:
        window_size (int): Maximum number of entries to keep in memory
        context_manager (ContextManager): Reference to the context manager for persistent storage
    """
    
    def __init__(self, window_size: int, context_manager: Optional[ContextManager] = None):
        """
        Initialize the RollingWindowMemory with a fixed window size.
        
        Args:
            window_size (int): Maximum number of entries to keep in memory
            context_manager (Optional[ContextManager]): Context manager for persistent storage
        
        Raises:
            ValueError: If window_size is less than 1
        """
        if window_size < 1:
            raise ValueError("Window size must be at least 1")
            
        self._window_size = window_size
        self._memory: Deque[MemoryEntry[T]] = deque(maxlen=window_size)
        self._lock = Lock()
        self._context_manager = context_manager

    def add_entry(self, content: T, metadata: Optional[dict] = None) -> None:
        """
        Add a new entry to the memory window.
        
        Args:
            content (T): The content to store
            metadata (Optional[dict]): Additional metadata for the entry
        """
        entry = MemoryEntry(
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        with self._lock:
            self._memory.append(entry)
            if self._context_manager:
                self._context_manager.update_context('memory_window', list(self._memory))

    def get_entries(self, count: Optional[int] = None) -> List[MemoryEntry[T]]:
        """
        Retrieve entries from the memory window.
        
        Args:
            count (Optional[int]): Number of most recent entries to retrieve.
                                If None, returns all entries.
        
        Returns:
            List[MemoryEntry[T]]: List of memory entries
        """
        with self._lock:
            if count is None:
                return list(self._memory)
            return list(self._memory)[-count:]

    def clear(self) -> None:
        """Clear all entries from the memory window."""
        with self._lock:
            self._memory.clear()
            if self._context_manager:
                self._context_manager.update_context('memory_window', [])

    def get_window_size(self) -> int:
        """
        Get the current window size setting.
        
        Returns:
            int: Maximum number of entries that can be stored
        """
        return self._window_size

    def set_window_size(self, new_size: int) -> None:
        """
        Update the window size, truncating oldest entries if necessary.
        
        Args:
            new_size (int): New maximum window size
            
        Raises:
            ValueError: If new_size is less than 1
        """
        if new_size < 1:
            raise ValueError("Window size must be at least 1")
            
        with self._lock:
            # Create new deque with new size
            new_memory: Deque[MemoryEntry[T]] = deque(maxlen=new_size)
            # Transfer most recent entries that fit in new window
            entries = list(self._memory)[-new_size:]
            new_memory.extend(entries)
            
            self._window_size = new_size
            self._memory = new_memory
            
            if self._context_manager:
                self._context_manager.update_context('memory_window', list(self._memory))

    def get_entry_count(self) -> int:
        """
        Get the current number of entries in memory.
        
        Returns:
            int: Number of entries currently stored
        """
        return len(self._memory)

    def restore_from_context(self) -> None:
        """
        Restore memory state from the context manager if available.
        """
        if not self._context_manager:
            return
            
        with self._lock:
            saved_memory = self._context_manager.get_context('memory_window')
            if saved_memory:
                # Clear current memory and restore from saved state
                self._memory.clear()
                self._memory.extend(saved_memory)

