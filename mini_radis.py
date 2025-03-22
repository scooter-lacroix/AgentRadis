#!/usr/bin/env python3

# Create a very minimal Radis implementation
content = """# Simple minimal version of Radis to get the API working
from typing import Dict, List, Optional, Any
import pytz
from datetime import datetime
from app.agent.base import BaseAgent
from app.schema import AgentMemory, Message, Role, AgentState, ToolChoice
from app.logger import logger
from app.tool.base import BaseTool

class Radis(BaseAgent):
    name: str = "Radis"
    system_prompt: Optional[str] = "You are Radis"
    tools: List[BaseTool] = []

    def __init__(self, tools: Optional[List[BaseTool]] = None, api_base: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.memory = AgentMemory()
        self.state = AgentState.IDLE
        self._active_resources = []
        self.iteration_count = 0
        self.tools = tools or []
        self.api_base = api_base

    async def run(self, prompt: str, mode: str = "action") -> Dict[str, Any]:
        await self.reset()
        self.memory.messages.append(Message(role=Role.USER, content=prompt))
        return {
            "response": f"Received: {prompt}. Mode: {mode}",
            "status": "success"
        }

    async def reset(self) -> None:
        self.memory = AgentMemory()
        self.state = AgentState.IDLE
        self.iteration_count = 0

def create_radis_agent(api_base: Optional[str] = None) -> 'Radis':
    return Radis(api_base=api_base)
"""

with open('app/agent/radis.py', 'w') as f:
    f.write(content)

print("Created minimal radis.py file") 