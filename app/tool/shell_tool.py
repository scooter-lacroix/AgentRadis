"""
Shell Tool - Execute shell commands
"""

import os
import asyncio
import shutil
from typing import Dict, Any, Optional, List

from app.tool.base import BaseTool
from app.logger import logger

class ShellTool(BaseTool):
    """
    Tool for executing shell commands.
    This tool allows executing system commands in a shell.
    """
    
    name = "shell"
    description = """
    Execute shell commands on the system.
    This tool can run any command that would be valid in a shell.
    Use with caution as it has full access to the system.
    """
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute"
            },
            "timeout": {
                "type": "number",
                "description": "Maximum execution time in seconds"
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for command execution"
            }
        },
        "required": ["command"]
    }
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute a shell command.
        
        Args:
            command: The shell command to execute
            timeout: Maximum execution time in seconds (default: 30)
            cwd: Working directory for command execution (default: current directory)
            
        Returns:
            Dictionary with command output and status
        """
        command = kwargs.get("command", "")
        timeout = kwargs.get("timeout", 30)
        cwd = kwargs.get("cwd", os.getcwd())
        
        if not command:
            return {
                "status": "error",
                "error": "No command provided"
            }
            
        logger.info(f"Executing shell command: {command}")
        
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            # Wait for command to complete with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                
                stdout_text = stdout.decode("utf-8", errors="replace").strip()
                stderr_text = stderr.decode("utf-8", errors="replace").strip()
                
                return {
                    "status": "success" if process.returncode == 0 else "error",
                    "returncode": process.returncode,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "command": command
                }
                
            except asyncio.TimeoutError:
                # Try to kill the process
                try:
                    process.kill()
                except:
                    pass
                    
                return {
                    "status": "timeout",
                    "error": f"Command execution timed out after {timeout} seconds",
                    "command": command
                }
                
        except Exception as e:
            logger.error(f"Error executing shell command: {e}")
            return {
                "status": "error",
                "error": f"Failed to execute command: {str(e)}",
                "command": command
            } 