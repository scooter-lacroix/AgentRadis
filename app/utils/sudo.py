"""
Sudo command utilities
"""

import os
import time
import asyncio
import subprocess
from typing import Dict, Any

# Global state
_sudo_password = None
_sudo_timestamp = None
_sudo_timeout = 300  # 5 minute timeout

async def run_sudo_command(cmd: str, require_password: bool = True) -> Dict[str, Any]:
    """
    Run a command with sudo privileges.
    
    Args:
        cmd: The command to run
        require_password: Whether to require password input
        
    Returns:
        Dict containing command output and status
    """
    global _sudo_password, _sudo_timestamp
    
    # First check if sudo is available and we have permissions
    try:
        # Check if we already have sudo privileges without password
        test_process = await asyncio.create_subprocess_shell(
            "sudo -n true",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await test_process.communicate()
        has_sudo_access = test_process.returncode == 0
    except Exception:
        has_sudo_access = False

    # If we need password but don't have cached access
    current_time = time.time()
    if require_password and not has_sudo_access and (not _sudo_timestamp or current_time - _sudo_timestamp > _sudo_timeout):
        # Prompt for sudo password
        import getpass
        print("\nSudo privileges required. Please enter your password:")
        _sudo_password = getpass.getpass()
        _sudo_timestamp = current_time
    
    try:
        # Prepare the command
        if require_password and _sudo_password and not has_sudo_access:
            # Use a more secure way to provide the password
            process = await asyncio.create_subprocess_shell(
                f"sudo -S {cmd}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate(input=f"{_sudo_password}\n".encode())
        else:
            # If we have sudo access or don't need password
            process = await asyncio.create_subprocess_shell(
                f"sudo {cmd}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
        
        # Check for password failure
        error_text = stderr.decode() if stderr else ''
        if "incorrect password attempt" in error_text.lower():
            _sudo_password = None  # Clear invalid password
            _sudo_timestamp = None
            return {
                'success': False,
                'error': "Incorrect sudo password",
                'code': 1
            }
            
        return {
            'success': process.returncode == 0,
            'output': stdout.decode() if stdout else '',
            'error': error_text,
            'code': process.returncode
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'code': -1
        }

def clear_sudo_cache():
    """Clear cached sudo password"""
    global _sudo_password, _sudo_timestamp
    _sudo_password = None
    _sudo_timestamp = None 