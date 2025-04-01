"""
Context management system for RadisProject.

This module provides thread-safe context management for conversations and user sessions,
integrating with the broader RadisProject architecture for state management.
"""

from dataclasses import dataclass, field
import threading
from typing import Dict, Any, Optional, List, TypeVar, Generic
import logging
from datetime import datetime, timedelta
import json
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class RadisContextError(Exception):
    """Base exception for context-related errors."""
    pass

class SessionExpiredError(RadisContextError):
    """Raised when attempting to access an expired session."""
    pass

class ContextNotFoundError(RadisContextError):
    """Raised when attempting to access a non-existent context."""
    pass

T = TypeVar('T')

class BaseContext(Generic[T]):
    """Base class for all context types in RadisProject."""
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to a dictionary representation."""
        pass

    @abstractmethod
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Update context from a dictionary representation."""
        pass

@dataclass
class SessionContext(BaseContext['SessionContext']):
    """Represents the context data for a single session."""
    
    session_id: str
    user_id: Optional[str]
    conversation_id: str
    last_updated: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    max_history_size: int = 100

    def add_to_history(self, entry: Dict[str, Any]) -> None:
        """
        Add an entry to conversation history, maintaining max size limit.
        
        Args:
            entry: The conversation entry to add
        """
        self.conversation_history.append(entry)
        if len(self.conversation_history) > self.max_history_size:
            self.conversation_history = self.conversation_history[-self.max_history_size:]

    def to_dict(self) -> Dict[str, Any]:
        """Convert session context to a dictionary representation."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'conversation_id': self.conversation_id,
            'last_updated': self.last_updated.isoformat(),
            'metadata': self.metadata,
            'conversation_history': self.conversation_history,
            'max_history_size': self.max_history_size
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update session context from a dictionary representation.
        
        Args:
            data: Dictionary containing session context data
        """
        self.session_id = data['session_id']
        self.user_id = data['user_id']
        self.conversation_id = data['conversation_id']
        self.last_updated = datetime.fromisoformat(data['last_updated'])
        self.metadata = data['metadata']
        self.conversation_history = data['conversation_history']
        self.max_history_size = data['max_history_size']

class ContextManager:
    """Thread-safe manager for handling conversation context and user state."""
    
    def __init__(self, session_timeout: int = 3600):
        """
        Initialize the ContextManager.
        
        Args:
            session_timeout: Session timeout in seconds (default: 1 hour)
        """
        self._contexts: Dict[str, SessionContext] = {}
        self._lock = threading.RLock()  # Reentrant lock for nested access
        self._session_timeout = timedelta(seconds=session_timeout)

    def create_context(
        self, 
        session_id: str, 
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionContext:
        """
        Create a new context for the given session ID.
        
        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier
            metadata: Optional initial metadata
            
        Returns:
            SessionContext: Newly created session context
            
        Raises:
            RadisContextError: If context already exists for the session
        """
        with self._lock:
            if session_id in self._contexts:
                raise RadisContextError(f"Context already exists for session {session_id}")
                
            context = SessionContext(
                session_id=session_id,
                user_id=user_id,
                conversation_id=self._generate_conversation_id(),
                last_updated=datetime.now(),
                metadata=metadata or {},
                conversation_history=[]
            )
            self._contexts[session_id] = context
            logger.info(f"Created new context for session {session_id}")
            return context

    def get_context(self, session_id: str, raise_if_expired: bool = False) -> SessionContext:
        """
        Retrieve the context for a given session ID.
        
        Args:
            session_id: Session identifier
            raise_if_expired: Whether to raise an exception for expired sessions
            
        Returns:
            SessionContext: The session context
            
        Raises:
            ContextNotFoundError: If context doesn't exist
            SessionExpiredError: If session is expired and raise_if_expired is True
        """
        with self._lock:
            context = self._contexts.get(session_id)
            if not context:
                raise ContextNotFoundError(f"No context found for session {session_id}")

            if self._is_session_expired(context):
                if raise_if_expired:
                    raise SessionExpiredError(f"Session {session_id} has expired")
                self.clear_context(session_id)
                return None

            context.last_updated = datetime.now()
            return context

    def update_context(self, session_id: str, updates: Dict[str, Any]) -> None:
        """
        Update the context metadata for a given session.
        
        Args:
            session_id: Session identifier
            updates: Dictionary of updates to apply
            
        Raises:
            ContextNotFoundError: If context doesn't exist
        """
        with self._lock:
            context = self.get_context(session_id)
            context.metadata.update(updates)
            context.last_updated = datetime.now()
            logger.debug(f"Updated context for session {session_id}")

    def add_to_history(self, session_id: str, entry: Dict[str, Any]) -> None:
        """
        Add a new entry to the conversation history.
        
        Args:
            session_id: Session identifier
            entry: Conversation history entry
            
        Raises:
            ContextNotFoundError: If context doesn't exist
        """
        with self._lock:
            context = self.get_context(session_id)
            context.add_to_history(entry)
            context.last_updated = datetime.now()

    def clear_context(self, session_id: str) -> None:
        """
        Remove the context for a given session ID.
        
        Args:
            session_id: Session identifier
        """
        with self._lock:
            if session_id in self._contexts:
                del self._contexts[session_id]
                logger.info(f"Cleared context for session {session_id}")

    def cleanup_expired_sessions(self) -> None:
        """Remove all expired session contexts."""
        with self._lock:
            current_time = datetime.now()
            expired_sessions = [
                session_id for session_id, context in self._contexts.items()
                if current_time - context.last_updated > self._session_timeout
            ]
            for session_id in expired_sessions:
                self.clear_context(session_id)
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    def export_context(self, session_id: str) -> str:
        """
        Export context as a JSON string.
        
        Args:
            session_id: Session identifier
            
        Returns:
            str: JSON representation of the context
            
        Raises:
            ContextNotFoundError: If context doesn't exist
        """
        with self._lock:
            context = self.get_context(session_id)
            return json.dumps(context.to_dict())

    def import_context(self, context_data: str) -> None:
        """
        Import context from a JSON string.
        
        Args:
            context_data: JSON string containing context data
            
        Raises:
            RadisContextError: If context data is invalid
        """
        try:
            data = json.loads(context_data)
            context = SessionContext(
                session_id='',
                user_id=None,
                conversation_id='',
                last_updated=datetime.now()
            )
            context.from_dict(data)
            with self._lock:
                self._contexts[context.session_id] = context
        except (json.JSONDecodeError, KeyError) as e:
            raise RadisContextError(f"Invalid context data: {str(e)}")

    def _is_session_expired(self, context: SessionContext) -> bool:
        """
        Check if a session context has expired.
        
        Args:
            context: Session context to check
            
        Returns:
            bool: True if session has expired, False otherwise
        """
        return datetime.now() - context.last_updated > self._session_timeout

    def _generate_conversation_id(self) -> str:
        """
        Generate a unique conversation ID.
        
        Returns:
            str: Unique conversation identifier
        """
        return f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(threading.current_thread())}"

    def __len__(self) -> int:
        """
        Get the number of active contexts.
        
        Returns:
            int: Number of active contexts
        """
        return len(self._contexts)

