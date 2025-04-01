from typing import Any, Dict, List, Optional
import uuid
import logging
from app.core.tool_registry import ToolRegistry
from app.core.context_manager import ContextManager
from app.core.rolling_window_memory import RollingWindowMemory
from app.schema.models import Message
from app.schema.types import Role


class EnhancedRadis:
    """
    EnhancedRadis is an agent that can use tools to process messages.
    It maintains conversation memory and context across multiple interactions.
    """

    def __init__(self):
        """Initialize the EnhancedRadis agent with required components."""
        self.tool_registry = ToolRegistry()
        self.context_manager = ContextManager()
        self.memory = RollingWindowMemory()
        self.session_id = str(uuid.uuid4())
        self.logger = logging.getLogger(__name__)

    def register_tools(self, tools: List[Any]) -> None:
        """
        Register multiple tools with the agent.

        Args:
            tools: A list of tool instances to register
        """
        for tool in tools:
            self.tool_registry.register_tool(tool.name, tool)

    async def run(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a message using registered tools and return a response.

        Args:
            message: The message content to process
            session_id: Optional session identifier for context continuity

        Returns:
            Dict containing the response and any relevant metadata
        """
        if session_id is None:
            session_id = self.session_id
            
        # Store the incoming message in memory
        user_message = Message(role=Role.USER, content=message)
        self.memory.add_message(user_message)
        
        # Get or create context for this session
        context = self.context_manager.get_or_create_context(session_id)
        
        # Prepare response
        response = {
            "message": "I've processed your request.",
            "session_id": session_id,
            "tools_available": list(self.tool_registry.list_tools().keys()),
            "context": context
        }
        
        # Store the response in memory
        assistant_message = Message(role=Role.ASSISTANT, content=response["message"])
        self.memory.add_message(assistant_message)
        
        return response
    
    def cleanup_resources(self, session_id: Optional[str] = None) -> None:
        """
        Clean up resources used by the agent for a specific session.
        
        Args:
            session_id: Optional session identifier to clean up
        """
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a tool by name with the given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Dictionary of parameters to pass to the tool
            
        Returns:
            The result of the tool execution
            
        Raises:
            ValueError: If the tool is not found or parameters are invalid
            Exception: Any exception raised during tool execution
        """
        self.logger.debug(f"Executing tool '{tool_name}' with parameters: {parameters}")
        
        # Try to get the tool from the registry
        try:
            tool = self.tool_registry.list_tools().get(tool_name)
        except Exception as e:
            self.logger.error(f"Error accessing tool registry: {str(e)}")
            tool = None
        
        if tool is None:
            self.logger.error(f"Tool '{tool_name}' not found")
            raise ValueError(f"Tool '{tool_name}' not found")
        
        success = False
        result = None
        error = None
        
        try:
            # Check if the tool has an execute method
            if hasattr(tool, 'execute') and callable(getattr(tool, 'execute')):
                result = tool.execute(**parameters)
            # Fall back to run method for backward compatibility
            elif hasattr(tool, 'run') and callable(getattr(tool, 'run')):
                result = tool.run(**parameters)
            else:
                self.logger.error(f"Tool '{tool_name}' does not have execute or run methods")
                raise ValueError(f"Tool '{tool_name}' is not executable")
            
            success = True
            self.logger.debug(f"Tool '{tool_name}' execution successful")
            return result
        
        except Exception as e:
            error = str(e)
            self.logger.error(f"Error executing tool '{tool_name}': {error}")
            raise
    
    async def cleanup(self, session_id: Optional[str] = None) -> None:
        """
        Clean up resources used by the agent.
        This method should be called when the agent is no longer needed.
        It cleans up tool resources, sessions, and any other temporary resources.
        
        Args:
            session_id: Optional session identifier to clean up
        """
        self.logger.debug("Cleaning up agent resources")
        
        if session_id is None:
            session_id = self.session_id
        
        # Reset any tools that need cleanup
        for tool_name, tool in self.tool_registry.list_tools().items():
            try:
                if hasattr(tool, "reset") and callable(tool.reset):
                    self.logger.debug(f"Resetting tool: {tool_name}")
                    tool.reset()
            except Exception as e:
                self.logger.error(f"Error cleaning up tool {tool_name}: {str(e)}")
        
        # Clear memory
        try:
            self.logger.debug("Cleaning up memory")
            self.memory.clear()
        except Exception as e:
            self.logger.error(f"Error cleaning up memory: {str(e)}")
        
        # Remove context(s)
        try:
            if session_id is None:
                # Clean up all contexts
                self.logger.debug("Cleaning up all contexts in context manager")
                all_sessions = self.context_manager.list_contexts()
                for sess_id in all_sessions:
                    self.logger.debug(f"Cleaning up context for session: {sess_id}")
                    self.context_manager.delete_context(sess_id)
            else:
                # Clean up specific session context
                self.logger.debug(f"Cleaning up context for session: {session_id}")
                self.context_manager.delete_context(session_id)
        except Exception as e:
            self.logger.error(f"Error cleaning up context(s): {str(e)}")
            
        self.logger.debug("Agent cleanup completed")
