from typing import Dict, Any, Optional
import uuid


class ContextManager:
    """
    Manages context for different sessions in the application.
    
    The ContextManager class provides methods to create, retrieve,
    and delete contexts associated with specific session IDs.
    """

    def __init__(self):
        """Initialize an empty context storage."""
        self._contexts: Dict[str, Dict[str, Any]] = {}

    def get_or_create_context(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get an existing context or create a new one if it doesn't exist.
        
        Args:
            session_id: The session ID to get or create context for.
                      If None, a new UUID will be generated.
        
        Returns:
            The context dictionary associated with the session ID.
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
            
        if session_id not in self._contexts:
            self._contexts[session_id] = {}
            
        return self._contexts[session_id]
    
    def delete_context(self, session_id: str) -> bool:
        """
        Delete the context associated with the given session ID.
        
        Args:
            session_id: The session ID whose context should be deleted.
            
        Returns:
            True if the context was deleted, False if it didn't exist.
        """
        if session_id in self._contexts:
            del self._contexts[session_id]
            return True
        return False
    
    def get_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the context for a specific session ID.
        
        Args:
            session_id: The session ID to get context for.
            
        Returns:
            The context dictionary if found, None otherwise.
        """
        return self._contexts.get(session_id)
    
    def update_context(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update the context for a specific session ID with new values.
        
        Args:
            session_id: The session ID to update context for.
            updates: The dictionary of values to replace the entire context.
            
        Returns:
            The updated context dictionary.
        """
        context = self.get_or_create_context(session_id)
        context.clear()  # Clear existing context
        context.update(updates)  # Add new values
        return context

    def list_contexts(self) -> list[str]:
        """
        Return a list of all session IDs that have contexts.
        
        Returns:
            A list of session IDs (strings) for which contexts exist.
        """
        return list(self._contexts.keys())
