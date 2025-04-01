import asyncio
import os
import re
import shlex
import subprocess
import tempfile
from typing import Dict, Any, List, Optional, Tuple

import time
from app.logger import get_logger
from app.tool.base import BaseTool

logger = get_logger(__name__)


class BashTool(BaseTool):
    """Tool for executing shell commands securely with proper session management.

    This tool allows executing bash commands with safety checks, timeout functionality,
    and proper error handling. It captures command output, exit codes, and manages sessions.
    """

    # Dangerous commands and patterns that should be blocked
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/",  # Remove root
        r"dd\s+if=.*\s+of=/dev",  # Writing to devices
        r"mkfs",  # Format filesystems
        r"wget.*\s+\|\s+bash",  # Download and execute
        r"curl.*\s+\|\s+bash",  # Download and execute
        r"chmod\s+-R\s+777",  # Excessively permissive
        r"chown\s+-R\s+root",  # Changing ownership to root
        r":(){ :\|:& };:",  # Fork bomb
        r">\s+/etc/passwd",  # Overwrite passwd
    ]

    def __init__(self, working_dir: Optional[str] = None, max_output_size: int = 10000):
        """Initialize the BashTool.

        Args:
            working_dir: Directory to use as the working directory for commands.
                         If None, the current directory is used.
            max_output_size: Maximum size of command output to capture (in bytes)
        """
        self._working_dir = working_dir or os.getcwd()
        self._max_output_size = max_output_size
        self._env = os.environ.copy()
        self._temp_dir = None  # Will be created on first use

    @property
    def name(self) -> str:
        """The name of the tool."""
        return "bash"

    @property
    def description(self) -> str:
        """A human-readable description of what the tool does."""
        return (
            "Execute shell commands and return the output. "
            "Commands are executed in a controlled environment with safety checks. "
            "Use this tool to run system commands, file operations, and other shell tasks."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        """JSON schema describing the tool's parameters."""
        return {
            "type": "object",
            "required": ["command"],
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "timeout": {
                    "type": "number",
                    "description": "Maximum execution time in seconds",
                    "default": 30,
                },
                "working_dir": {
                    "type": "string",
                    "description": "Directory to run the command in. If not provided, uses the tool's default.",
                },
                "env_vars": {
                    "type": "object",
                    "description": "Additional environment variables to set for the command execution",
                    "additionalProperties": {"type": "string"},
                },
            },
        }

    def _ensure_temp_dir(self) -> str:
        """Ensure that a temporary directory exists for the session.

        Returns:
            Path to the temporary directory
        """
        if self._temp_dir is None or not os.path.exists(self._temp_dir):
            self._temp_dir = tempfile.mkdtemp(prefix="radis_bash_")
        return self._temp_dir

    def _check_command_safety(self, command: str) -> bool:
        """Check if the command passes safety checks.

        Args:
            command: The command to check

        Returns:
            True if the command is safe, False otherwise

        Raises:
            ValueError: If the command contains dangerous patterns
        """
        # Check against dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                raise ValueError(f"Command contains dangerous pattern: {pattern}")

        # Check for other risky commands or syntax
        if "|" in command and ("bash" in command or "sh" in command):
            raise ValueError("Piping to shell executables is not allowed")

        # Check for commands that modify sensitive system files
        if any(
            path in command for path in ["/etc/passwd", "/etc/shadow", "/etc/sudoers"]
        ):
            if any(
                cmd in command for cmd in ["write", "edit", ">", "nano", "vim", "emacs"]
            ):
                raise ValueError("Modifying sensitive system files is not allowed")

        return True

    async def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the shell command.

        Args:
            command: The shell command to execute
            timeout: Maximum execution time in seconds (default: 30)
            working_dir: Directory to run the command in (optional)
            env_vars: Additional environment variables (optional)

        Returns:
            Dictionary containing command output, exit code, and execution info

        Raises:
            ValueError: If the command fails safety checks
            TimeoutError: If the command execution exceeds the timeout
            RuntimeError: If command execution fails
        """
        # Validate and extract parameters
        params = self.validate_parameters(kwargs)
        command = params["command"]
        timeout = params.get("timeout", 30)
        working_dir = params.get("working_dir", self._working_dir)
        env_vars = params.get("env_vars", {})

        # Safety check
        self._check_command_safety(command)

        # Prepare environment
        env = self._env.copy()
        env.update(env_vars)

        # Ensure the working directory exists
        if not os.path.exists(working_dir):
            raise ValueError(f"Working directory does not exist: {working_dir}")

        # Capture start time
        start_time = asyncio.get_event_loop().time()

        try:
            # Run the command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=env,
                limit=self._max_output_size,
            )

            # Wait for the command to complete with timeout
            logger.debug(f"Running command with timeout {timeout}s: {command}")
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                # Decode and truncate output if necessary
                stdout_str = stdout.decode("utf-8", errors="replace")
                stderr_str = stderr.decode("utf-8", errors="replace")

                if len(stdout_str) > self._max_output_size:
                    stdout_str = (
                        stdout_str[: self._max_output_size] + "\n... [output truncated]"
                    )
                if len(stderr_str) > self._max_output_size:
                    stderr_str = (
                        stderr_str[: self._max_output_size] + "\n... [output truncated]"
                    )

                # Calculate execution time
                execution_time = asyncio.get_event_loop().time() - start_time

                return {
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "exit_code": process.returncode,
                    "execution_time": execution_time,
                    "command": command,
                    "working_dir": working_dir,
                }

            except asyncio.TimeoutError:
                # Log the timeout occurrence
                logger.warning(f"Command timed out after {timeout}s: {command}")
                pid = process.pid if process and hasattr(process, 'pid') else 'unknown'
                
                # Try to terminate the process gracefully first
                try:
                    logger.debug(f"Attempting to terminate process {pid}")
                    process.terminate()
                    
                    # Wait a short time for graceful termination
                    await asyncio.sleep(0.1)
                    
                    # Check if process is still running
                    if process.returncode is None:
                        logger.warning(f"Process {pid} did not terminate gracefully, attempting to kill")
                        process.kill()
                        await asyncio.sleep(0.1)  # Give kill a moment to take effect
                        
                        # Final check if process is still running
                        if process.returncode is None:
                            logger.error(f"Failed to kill process {pid} after timeout")
                        else:
                            logger.debug(f"Process {pid} successfully killed")
                    else:
                        logger.debug(f"Process {pid} terminated gracefully")
                except Exception as e:
                    logger.error(f"Error while terminating process {pid}: {str(e)}")
                
                # Get any partial output that might be available
                partial_output = ""
                try:
                    if hasattr(process, 'stdout') and process.stdout:
                        partial_output_bytes = await process.stdout.read()
                        if partial_output_bytes:
                            partial_output = partial_output_bytes.decode('utf-8', errors='replace')
                except Exception as e:
                    logger.error(f"Error retrieving partial output: {str(e)}")

                timeout_info = {
                    "pid": pid,
                    "command": command,
                    "timeout_seconds": timeout,
                    "working_dir": working_dir,
                    "partial_output": partial_output if partial_output else "No partial output available"
                }
                
                logger.error(f"Timeout details: {timeout_info}")
                
                raise TimeoutError(
                    f"Command execution timed out after {timeout} seconds: {command}"
                )

        except Exception as e:
            if isinstance(e, TimeoutError):
                logger.error(f"Command timeout error: {str(e)}")
                raise
            logger.error(f"Command execution error: {str(e)}")
            raise RuntimeError(f"Command execution failed: {str(e)}")

    async def cleanup(self) -> None:
        """Clean up temporary resources."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            import shutil

            try:
                shutil.rmtree(self._temp_dir)
                self._temp_dir = None
            except Exception as e:
                logger.error(f"Failed to clean up temporary directory: {str(e)}")

    async def reset(self) -> None:
        """Reset the tool to its initial state."""
        # Clean up temporary directory
        await self.cleanup()

        # Reset working directory to initial value
        self._working_dir = os.getcwd()

        # Reset environment variables
        self._env = os.environ.copy()
