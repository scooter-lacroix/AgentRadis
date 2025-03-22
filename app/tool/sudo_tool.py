"""
Tool for executing privileged commands with sudo.
"""

import os
import asyncio
from typing import Dict, Any, Optional

from app.tool.base import BaseTool
from app.logger import logger
from app.utils.sudo import run_sudo_command, clear_sudo_cache

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
    
    # Cache for sudo password and timestamp
    _sudo_password: Optional[str] = None
    _sudo_timestamp: Optional[float] = None
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute a command with sudo privileges.
        
        Args:
            command: The command to execute with sudo
            require_password: Whether to require password input (default: True)
            
        Returns:
            Dictionary containing command output and status
        """
        command = kwargs.get("command", "")
        require_password = kwargs.get("require_password", True)
        
        if not command:
            return {
                "status": "error",
                "error": "No command provided"
            }
            
        # Inform user and check consent
        logger.info(f"Executing privileged command: {command}")
        
        try:
            # Execute the command with sudo
            result = await run_sudo_command(command, require_password)
            
            status_msg = "Command executed successfully" if result.get("success") else "Command execution failed"
            logger.info(status_msg)
            
            return {
                "status": "success" if result.get("success") else "error",
                "output": result.get("output", ""),
                "error": result.get("error", ""),
                "code": result.get("code", -1)
            }
            
        except asyncio.TimeoutError:
            return {
                "status": "error",
                "error": "Command execution timed out",
                "code": -1
            }
        except Exception as e:
            logger.error(f"Error executing sudo command: {e}")
            return {
                "status": "error",
                "error": f"Error: {str(e)}",
                "code": -1
            }
    
    async def cleanup(self):
        """Clean up resources and clear any cached sudo password."""
        clear_sudo_cache() 