"""
Tool for executing privileged commands with sudo.
"""

import os
import asyncio
from typing import Dict, Any, Optional

from app.tool.base import BaseTool
from app.logger import logger
from app.utils.sudo import run_sudo_command

class SudoTool(BaseTool):
    """Tool for executing privileged commands with sudo."""
    
    name = "sudo"
    description = """
    Execute commands with sudo privileges. This tool requires explicit user consent and password input.
    The sudo password will be cached for 5 minutes to avoid repeated prompts.
    Use this tool only for commands that absolutely require elevated privileges.
    """
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The command to execute with sudo privileges"
            },
            "require_password": {
                "type": "boolean",
                "description": "Whether to require password input",
                "default": True
            }
        },
        "required": ["command"]
    }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute a sudo command."""
        if "command" not in kwargs:
            return {
                'status': 'error',
                'error': 'Missing required parameter: command'
            }
        require_password = kwargs.get('require_password', True)
        return await self.run(kwargs['command'], require_password)
    
    async def run(self, command: str, require_password: bool = True) -> Dict[str, Any]:
        """
        Execute a command with sudo privileges.
        
        Args:
            command: The command to execute with sudo
            require_password: Whether to require password input
            
        Returns:
            Dict containing command output and status
        """
        try:
            # Run the command with sudo
            result = await run_sudo_command(command, require_password)
            
            if not result['success']:
                logger.error(f"Sudo command failed: {result['error']}")
                return {
                    'status': 'error',
                    'error': f"Command failed: {result['error']}"
                }
                
            return {
                'status': 'success',
                'output': result['output'],
                'code': result['code']
            }
            
        except Exception as e:
            logger.error(f"Error executing sudo command: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
            
    async def cleanup(self):
        """Clean up any resources."""
        # Nothing to clean up for this tool
        pass 