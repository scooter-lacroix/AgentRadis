"""
SWE (Software Engineer) Agent implementation.

This module implements a specialized software engineering agent designed to help with
coding tasks, leveraging tools like bash commands and code editing capabilities.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from app.agent.toolcall import ToolCallAgent
from app.core.tool_registry import get_tool
from app.prompt.swe import NEXT_STEP_TEMPLATE, SYSTEM_PROMPT
from app.schema.memory import AgentMemory
from app.schema.models import Message, MessageContent, ToolResponse
from app.schema.tools import Tool, ToolCall
from app.schema.types import ContentType, Role, AgentState, AgentResult
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from app.agent.toolcall import ToolCallAgent
from app.core.tool_registry import ToolRegistry

import json
                    logger = logging.getLogger(__name__)
                    
    such as writing, debugging, and modifying code. It supports working directory
    management and maintains a session context through AgentMemory.
    
    Attributes:
        system_prompt (str): System prompt for the agent
        next_step_template (str): Template for suggesting next steps
        working_dir (str): Current working directory for the agent
        memory (AgentMemory): Memory to maintain session context
    """
    
    @property
    def name(self) -> str:
        """The name of the agent."""
        return "SWEAgent"

    def __init__(self, 
                model: str = "gpt-4-turbo-preview", 
                temperature: float = 0.7,
                working_dir: Optional[str] = None):
        """Initialize the Software Engineer Agent.
        
        Args:
            model: The LLM model to use
            temperature: The temperature parameter for LLM responses
            working_dir: Optional working directory. Defaults to current directory.
        """
        super().__init__(model=model, temperature=temperature)
        self.system_prompt = SYSTEM_PROMPT
        self.next_step_template = NEXT_STEP_TEMPLATE
        self.working_dir = working_dir or os.getcwd()
        self.memory = AgentMemory()
        self._artifacts = []
                            \"\"\"\n                            registry = ToolRegistry()\n                            tools = [\n                                registry.get_tool("bash"),\n                                registry.get_tool("str_replace"),\n                                registry.get_tool("file"),\n                                registry.get_tool("web"),\n                                registry.get_tool("terminate"),\n                            ]\n
    async def async_setup(self) -> None:
        """Set up the agent and initialize available tools."""
        await super().async_setup()
        
        # Initialize memory and artifacts tracking
        self.memory.clear()
        self._artifacts = []
        self.state = AgentState.READY

    def get_default_tools(self) -> List[Tool]:
        """
        Return the default set of tools needed for software engineering tasks.
        
        Returns:
            List[Tool]: A list of tools specifically useful for code-related tasks.
        """
        tools = [
            get_tool("bash"),
            get_tool("str_replace"),
            get_tool("file"),
            get_tool("web"),
            get_tool("terminate"),
        ]
        return [t for t in tools if t is not None]

    def format_prompt(self, messages: List[Message]) -> List[Message]:
        """
        Format the prompt with specialized system instructions for software engineering.
        
        Args:
            messages (List[Message]): The conversation history.
            
        Returns:
            List[Message]: The formatted messages including the system prompt.
        """
        formatted_messages = []
        
        # Add system prompt
        formatted_messages.append(Message(
            role=Role.SYSTEM,
            content=[MessageContent(
                type=ContentType.TEXT,
                text=self.system_prompt
            )]
        ))
        
        # Add conversation history
        for message in messages:
            formatted_messages.append(message)
        
        return formatted_messages

    def process_tool_calls(
        self, 
        message: Message, 
        available_tools: Dict[str, Tool]
    ) -> List[Tuple[ToolCall, Any]]:
        """
        Process tool calls from the assistant's response.
        
        Args:
            message (Message): The message containing tool calls.
            available_tools (Dict[str, Tool]): Dictionary of available tools.
            
        Returns:
            List[Tuple[ToolCall, Any]]: List of tuples containing the tool calls and their results.
        """
        results = super().process_tool_calls(message, available_tools)
        
        # Track any artifacts created or modified by tool calls
        for tool_call, result in results:
            if tool_call.function.name == "file" and isinstance(result, dict):
                if "path" in result and "write" in result.get("operation", ""):
                    self._artifacts.append(result["path"])
        
        return results

    def format_next_step(self, thinking: str, next_step_1: str = "", next_step_2: str = "", next_step_3: str = "") -> str:
        """
        Format the next step instruction using the specialized template.
        
        Args:
            thinking (str): The thought process or reasoning
            next_step_1 (str): First suggested next step
            next_step_2 (str): Second suggested next step
            next_step_3 (str): Third suggested next step
            
        Returns:
            str: The formatted next step instruction.
        """
        if self.next_step_template:
            return self.next_step_template.format(
                thinking=thinking,
                next_step_1=next_step_1 or "Review the changes made",
                next_step_2=next_step_2 or "Test the implementation",
                next_step_3=next_step_3 or "Consider additional improvements"
            )
        return thinking
    
    async def run(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """Run the agent with the given input.
        
        Args:
            input_text: The input text to process
            **kwargs: Additional arguments including session_id
        
        Returns:
            Dict containing the results including any tool calls and artifacts
        """
        # Set up the working directory if specified in kwargs
        if "working_dir" in kwargs:
            self.working_dir = kwargs.pop("working_dir")
        
        # Get or create a session
        session_id = kwargs.pop("session_id", None)
        if session_id:
            # Retrieve existing session context if available
            session_data = self.memory.get(session_id)
            if session_data:
                # Restore session context
                if "working_dir" in session_data and not "working_dir" in kwargs:
                    self.working_dir = session_data["working_dir"]
                if "messages" in session_data:
                    self._messages = session_data["messages"]
        
        # Run the agent
        result = await super().run(input_text, **kwargs)
        
        # Store session data
        if session_id:
            self.memory.set(session_id, {
                "working_dir": self.working_dir,
                "messages": self._messages,
                "artifacts": self._artifacts
            })
        
        # Add artifacts to the result
        result["artifacts"] = self._artifacts
        return result
    
    async def reset(self) -> None:
        """Reset the agent to its initial state."""
        await super().reset()
        self._artifacts = []
        # Keep the working directory
    
    async def set_working_dir(self, path: str) -> bool:
        """
        Set the working directory for the agent.
        
        Args:
            path (str): The new working directory path
            
        Returns:
            bool: True if successfully set, False otherwise
        """
        if os.path.isdir(path):
            self.working_dir = path
            return True
        return False
    
    def get_working_dir(self) -> str:
        """
        Get the current working directory.
        
        Returns:
            str: The current working directory path
        """
        return self.working_dir
    
    def get_artifacts(self) -> List[str]:
        """
        Get the list of artifacts created or modified during the session.
        
        Returns:
            List[str]: List of artifact paths
        """
        return self._artifacts
