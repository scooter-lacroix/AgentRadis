import os
import aiofiles
from app.tool.base import BaseTool, ToolResult, ToolFailure
from pathlib import Path
import platform
from typing import ClassVar, Optional
import logging

# Define default save directories for each platform
DEFAULT_SAVE_DIRS = {
    "Windows": os.path.expanduser("~/Documents/AgentRadis_Saves"),
    "Linux": os.path.expanduser("~/AgentRadis_Saves"),
    "Darwin": os.path.expanduser("~/Library/AgentRadis_Saves")
}

class FileSaver(BaseTool):
    DEFAULT_SAVE_DIR: ClassVar[str] = DEFAULT_SAVE_DIRS.get(platform.system(), "./saved_files")

    name: str = "file_saver"
    description: str = """Save content to a file. 
Files are stored in user-specific locations by default but can save to specified paths with proper permissions.
Use this tool to save code, text, or data to a file on the user's system."""

    parameters: dict = {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Content to save to the file"},
            "file_path": {"type": "string", "description": "Path to save the file (relative or absolute)"},
            "mode": {"type": "string", "enum": ["w", "a"], "default": "w", "description": "Write mode: 'w' to overwrite, 'a' to append"},
            "create_dirs": {"type": "boolean", "default": True, "description": "Create parent directories if they don't exist"}
        },
        "required": ["content", "file_path"]
    }

    async def execute(self, 
                     content: str, 
                     file_path: str, 
                     mode: str = "w", 
                     create_dirs: bool = True) -> str:
        """
        Save content to a file with proper error handling and directory creation.
        
        Args:
            content: Text content to save
            file_path: Target file path (relative or absolute)
            mode: File open mode ('w' for write, 'a' for append)
            create_dirs: Whether to create parent directories
            
        Returns:
            Success or error message
        """
        # Determine the full path
        try:
            # Check if absolute path
            if os.path.isabs(file_path):
                full_path = Path(file_path)
            else:
                # Use default directory for relative paths
                full_path = Path(self.DEFAULT_SAVE_DIR) / file_path
            
            # Create parent directories if needed
            if create_dirs and not full_path.parent.exists():
                try:
                    # Create with secure permissions
                    full_path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                    logging.info(f"Created directory: {full_path.parent}")
                except PermissionError as e:
                    return ToolFailure(error=f"Permission denied creating directory: {e}")
                except Exception as e:
                    return ToolFailure(error=f"Failed to create directory: {str(e)}")
            
            # Write the file
            try:
                async with aiofiles.open(full_path, mode, encoding="utf-8") as f:
                    await f.write(content)
                
                # Verify file was written
                file_size = os.path.getsize(full_path)
                return f"Successfully saved {file_size} bytes to {full_path}"
            except PermissionError:
                return ToolFailure(error=f"Permission denied when writing to {full_path}")
            except IsADirectoryError:
                return ToolFailure(error=f"Cannot write to {full_path}: It's a directory")
            except Exception as e:
                return ToolFailure(error=f"Failed to write file: {type(e).__name__} - {str(e)}")
                
        except Exception as e:
            return ToolFailure(error=f"Unexpected error: {type(e).__name__} - {str(e)}")

    async def run(self, **kwargs):
        """Save file (alias for execute)"""
        return await self.execute(**kwargs)
