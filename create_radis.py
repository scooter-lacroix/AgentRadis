#!/usr/bin/env python3

content = """
\"\"\"
Radis Agent Module

This module provides the Radis agent, a versatile agent capable of
handling complex tasks through tool usage and reasoning.
\"\"\"

from typing import Dict, List, Optional, Any
import asyncio
import json
import time
import traceback
import os
from datetime import datetime
from pathlib import Path
import importlib.util
import logging
import pytz

from app.agent.base import BaseAgent
from app.schema import AgentMemory, Message, Role, AgentState, ToolChoice
from app.logger import logger
from app.tool.base import BaseTool
from app.tool.web_search import WebSearch
from app.tool.file_saver import FileSaver
from app.tool.terminal import Terminal
from app.tool.bash import Bash
from app.tool.python_execute import PythonExecute
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.terminate import Terminate
from app.tool.mcp_installer import MCPInstaller
from app.tool.sudo_tool import SudoTool
from app.tool.file_handler import FileHandler
from app.config import config
from app.utils.sudo import run_sudo_command, clear_sudo_cache

logger = logging.getLogger(__name__)

# System prompt for agent initialization
SYSTEM_PROMPT = \"\"\"You are Radis, an AI agent designed to help users with their tasks.
You have access to various tools that allow you to interact with the system and external services.
IMPORTANT: For any factual information or claims, you MUST use your web search tool to verify and provide up-to-date information.
Never rely on your training data without verification. Always show your sources.
Be concise but informative in your responses.\"\"\"

# Prompt to guide the agent toward the next step
NEXT_STEP_PROMPT = \"\"\"Consider your progress so far. Choose the most appropriate action:
1. If you have enough information, return the FINAL ANSWER
2. If you need information, use the appropriate TOOL with correct parameters
3. If stuck, try a DIFFERENT APPROACH using different tools or methods\"\"\"

class Radis(BaseAgent):
    \"\"\"
    Radis is a versatile agent that can use tools to assist users with various tasks.
    \"\"\"

    name: str = "Radis"
    system_prompt: Optional[str] = SYSTEM_PROMPT
    next_step_prompt: Optional[str] = NEXT_STEP_PROMPT
    tools: List[BaseTool] = []

    def __init__(self, tools: Optional[List[BaseTool]] = None, api_base: Optional[str] = None, **kwargs):
        \"\"\"Initialize the agent with memory, state tracking, and tools\"\"\"
        super().__init__(**kwargs)
        
        # Core components
        self.memory = AgentMemory()
        self.state = AgentState.IDLE
        self._active_resources = []
        self.iteration_count = 0
        
        # Initialize tools
        self.tools = tools or []
        self.api_base = api_base

    async def run(self, prompt: str, mode: str = "action") -> Dict[str, Any]:
        \"\"\"
        Run the agent with the given prompt
        
        Args:
            prompt: The input prompt
            mode: The agent mode ("action" or "plan")
            
        Returns:
            Dict containing the agent's response
        \"\"\"
        # Add user prompt to memory
        self.memory.messages.append(Message(role=Role.USER, content=prompt))
        
        # Generate a simple response
        return {
            "response": f"Received your prompt: {prompt}. Mode: {mode}",
            "status": "success"
        }

    async def reset(self) -> None:
        \"\"\"Reset the agent state for a new conversation\"\"\"
        self.memory = AgentMemory()
        self.state = AgentState.IDLE
        self.iteration_count = 0

    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        \"\"\"
        Get tools formatted for LLM consumption
        
        Returns:
            List of tool descriptions
        \"\"\"
        tool_descriptions = []
        for tool in self.tools:
            tool_descriptions.append({
                'type': 'function',
                'function': {
                    'name': tool.name,
                    'description': tool.description.strip(),
                    'parameters': getattr(tool, 'parameters', {})
                }
            })
        return tool_descriptions

def create_radis_agent(api_base: Optional[str] = None) -> 'Radis':
    \"\"\"Create a new Radis agent instance with all available tools.\"\"\"
    return Radis(api_base=api_base)
"""

with open('app/agent/radis.py', 'w') as f:
    f.write(content)

print("Created minimal radis.py file") 