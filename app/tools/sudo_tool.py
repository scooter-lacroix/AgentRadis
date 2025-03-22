"""
Tool for executing sudo commands
"""

import logging
from typing import Dict, Any, Callable, Awaitable

logger = logging.getLogger(__name__)

class SudoTool:
    """Tool for executing sudo commands"""
    
    def __init__(self, run_sudo_command: Callable[[str, bool], Awaitable[Dict[str, Any]]]):
        """
        Initialize SudoTool
        
        Args:
            run_sudo_command: Function to execute sudo commands
        """
        self.run_sudo_command = run_sudo_command
        
    async def execute(self, command: str, require_password: bool = True) -> Dict[str, Any]:
        """
        Execute a command with sudo privileges
        
        Args:
            command: The command to execute
            require_password: Whether to require password input
            
        Returns:
            Dict containing command output and status
        """
        try:
            result = await self.run_sudo_command(command, require_password)
            return result
        except Exception as e:
            logger.error(f"Error executing sudo command: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'code': -1
            } 