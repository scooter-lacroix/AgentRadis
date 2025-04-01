from typing import Dict, List, Optional, Any, Union, Tuple
import uuid
import json
import time
import logging
import warnings
import signal
from app.schema.models import Message, ToolCall, ToolResponse, Function
from app.schema.types import Role, AgentState, ToolChoice
import asyncio
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import traceback
from app.agent.radis import RadisAgent
from app.config import RadisConfig
from app.logger import logger
from app.memory import RollingWindowMemory
from app.core.tool_registry import get_tool_registry, ToolNotFoundError
from app.core.context_manager import ContextManager
from app.memory_integration import upgrade_memory, get_memory_stats
from app.tool.base import BaseTool
from .base import BaseAgent
from .response_processor import ResponseProcessor
from .identity_context import RadisIdentityContext, CommandHistory
from .security_config import SecurityConfig
from .errors import ToolNotFoundError, SecurityError

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, module="your_deprecated_module"
)


class EnhancedRadis(RadisAgent):
    """Enhanced Radis agent with security boundaries and identity management.
    Inherits from BaseAgent and adds security features, response processing."""
    def __init__(
        self,
        mode: str = "act",
        tools: Optional[List[Union[BaseTool, str]]] = None,
        api_base: Optional[str] = None,
        **kwargs
    ):
        super().__init__(mode=mode, api_base=api_base, **kwargs)

        self.tool_registry = get_tool_registry()
        self.tools: List[BaseTool] = []

        if tools:
            for tool in tools:
                if isinstance(tool, str):
                    try:
                        tool_instance = self.tool_registry.get_tool(tool)
                        if tool_instance:
                            self.tools.append(tool_instance)
                        else:
                            logger.warning(f"Tool '{tool}' not found in registry.")
                    except ToolNotFoundError as e:
                        logger.warning(f"Tool '{tool}' not found in registry: {e}")
                elif isinstance(tool, BaseTool):
                    self.tools.append(tool)
                else:
                    logger.warning(f"Invalid tool type: {type(tool)}. Skipping.")

        self.response_processor = ResponseProcessor()
        self.identity_context = RadisIdentityContext()
        self.command_history = CommandHistory()
        self.security_config = SecurityConfig()
        self.context_manager = ContextManager()

        # Set the system prompt using the identity context enhancement text
        system_prompt_text = self.identity_context.get_identity_enhancement_text()
        self.set_system_prompt(system_prompt_text)

    def get_tools(self) -> List[BaseTool]:
        return self.tools
