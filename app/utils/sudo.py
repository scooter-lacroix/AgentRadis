"""
Sudo command utilities
"""

import os
import time
import asyncio
from typing import Dict, Any

# Global state
_sudo_password = None
_sudo_timestamp = None

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
    
    # Check if we need a new sudo password
    current_time = time.time()
    if require_password and (not _sudo_timestamp or current_time - _sudo_timestamp > 300):  # 5 minute timeout
        # Prompt for sudo password
        import getpass
        print("\nSudo privileges required. Please enter your password:")
        _sudo_password = getpass.getpass()
        _sudo_timestamp = current_time
    
    try:
        # Prepare the command
        if require_password and _sudo_password:
            full_cmd = f'echo "{_sudo_password}" | sudo -S {cmd}'
        else:
            full_cmd = f'sudo {cmd}'
            
        # Run the command
        process = await asyncio.create_subprocess_shell(
            full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            'success': process.returncode == 0,
            'output': stdout.decode() if stdout else '',
            'error': stderr.decode() if stderr else '',
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