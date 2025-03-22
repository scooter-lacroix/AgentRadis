import asyncio
import os
import shlex
from typing import Optional, Dict, Any

from app.tool.base import BaseTool


class Terminal(BaseTool):
    name: str = "execute_command"
    description: str = """Request to execute a CLI command on the system.
Use this when you need to perform system operations or run specific commands to accomplish any step in the user's task.
You must tailor your command to the user's system and provide a clear explanation of what the command does.
Prefer to execute complex CLI commands over creating executable scripts, as they are more flexible and easier to run.
Commands will be executed in the current working directory.
Note: You MUST append a `sleep 0.05` to the end of the command for commands that will complete in under 50ms, as this will circumvent a known issue with the terminal tool where it will sometimes not return the output when the command completes too quickly.
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "(required) The CLI command to execute. This should be valid for the current operating system. Ensure the command is properly formatted and does not contain any harmful instructions.",
            }
        },
        "required": ["command"],
    }
    process: Optional[asyncio.subprocess.Process] = None
    current_path: str = os.getcwd()
    lock: asyncio.Lock = asyncio.Lock()

    async def run(self, **kwargs) -> Dict[str, Any]:
        """Execute a terminal command based on the provided arguments.
        
        Args:
            command: The CLI command to execute
            
        Returns:
            Dictionary with the command output
        """
        command = kwargs.get("command", "")
        if not command:
            return {
                "status": "error",
                "error": "No command provided"
            }
            
        return await self._execute_command(command)
    
    async def _execute_command(self, command: str) -> Dict[str, Any]:
        """Execute a terminal command and return the result."""
        async with self.lock:
            # Check if the command is a cd command
            if command.strip().startswith("cd "):
                return await self._handle_cd_command(command)
                
            # Sanitize the command
            sanitized_command = self._sanitize_command(command)
            
            try:
                # Use shell=True to allow for commands like cd, etc.
                self.process = await asyncio.create_subprocess_shell(
                    sanitized_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.current_path
                )
                
                stdout, stderr = await self.process.communicate()
                returncode = self.process.returncode
                
                # Update process
                self.process = None
                
                # Convert bytes to strings
                stdout_str = stdout.decode("utf-8", errors="replace")
                stderr_str = stderr.decode("utf-8", errors="replace")
                
                return {
                    "status": "success" if returncode == 0 else "error",
                    "output": stdout_str,
                    "error": stderr_str,
                    "code": returncode,
                    "cwd": self.current_path
                }
                
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "code": -1,
                    "cwd": self.current_path
                }

    async def execute_in_env(self, env_name: str, command: str) -> Dict[str, Any]:
        """Execute a command in a specific environment."""
        if env_name == "bash":
            activate_cmd = f"source {env_name}/bin/activate && {command}"
            return await self._execute_command(activate_cmd)
        else:
            # For Windows or other environments
            return {
                "status": "error",
                "error": f"Environment activation for {env_name} not supported yet",
                "code": -1
            }

    async def _handle_cd_command(self, command: str) -> Dict[str, Any]:
        """Handle cd commands by updating the current path."""
        # Extract the directory from the cd command
        try:
            parts = shlex.split(command)
            if len(parts) < 2:
                return {
                    "status": "error",
                    "error": "No directory specified for cd command",
                    "code": 1,
                    "cwd": self.current_path
                }
                
            directory = parts[1]
            
            # Handle relative paths
            if not os.path.isabs(directory):
                new_path = os.path.join(self.current_path, directory)
            else:
                new_path = directory
                
            # Normalize the path
            new_path = os.path.normpath(new_path)
            
            # Check if the path exists
            if not os.path.exists(new_path):
                return {
                    "status": "error",
                    "error": f"Directory not found: {new_path}",
                    "code": 1,
                    "cwd": self.current_path
                }
                
            # Update the current path
            self.current_path = new_path
            
            return {
                "status": "success",
                "output": f"Changed directory to {new_path}",
                "error": "",
                "code": 0,
                "cwd": self.current_path
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error handling cd command: {str(e)}",
                "code": 1,
                "cwd": self.current_path
            }

    @staticmethod
    def _sanitize_command(command: str) -> str:
        """Sanitize the command to prevent security issues."""
        # Basic sanitization, can be expanded
        return command.strip()

    async def close(self):
        """Close any active process."""
        if self.process and self.process.returncode is None:
            try:
                self.process.terminate()
                await asyncio.sleep(0.1)
                if self.process.returncode is None:
                    self.process.kill()
            except Exception as e:
                print(f"Error closing process: {e}")
                
    async def cleanup(self):
        """Clean up resources."""
        await self.close()

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    def to_param(self) -> Dict[str, Any]:
        """Return the tool parameters as a dict."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The CLI command to execute. This should be valid for the current operating system."
                        }
                    },
                    "required": ["command"]
                }
            }
        }
