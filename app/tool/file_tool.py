"""
File Tool - Handle file operations
"""

import os
import json
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import shutil

from app.tool.base import BaseTool
from app.logger import logger

class FileTool(BaseTool):
    """
    Tool for file system operations like reading, writing, and managing files.
    """
    
    name = "file"
    description = """
    Perform file system operations.
    This tool can read, write, list, and manage files on the system.
    """
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "write", "append", "list", "exists", "delete", "move", "copy"],
                "description": "The file action to perform"
            },
            "path": {
                "type": "string",
                "description": "Path to the file or directory"
            },
            "content": {
                "type": "string",
                "description": "Content to write (for write/append actions)"
            },
            "target": {
                "type": "string",
                "description": "Target path (for move/copy actions)"
            },
            "encoding": {
                "type": "string", 
                "description": "File encoding (default: utf-8)"
            }
        },
        "required": ["action", "path"]
    }
    
    def __init__(self, **kwargs):
        """Initialize the file tool."""
        super().__init__(**kwargs)
        self.base_dir = os.getcwd()
        
    def _resolve_path(self, path: str) -> str:
        """
        Resolve a path safely, preventing access outside of allowed directories.
        
        Args:
            path: The path to resolve
            
        Returns:
            The resolved absolute path
        """
        if os.path.isabs(path):
            # For absolute paths, ensure they're within user's home directory
            resolved = os.path.normpath(path)
            if not resolved.startswith(os.path.expanduser("~")):
                # Path is outside of user's home directory, so use base_dir instead
                logger.warning(f"Attempted to access path outside home directory: {path}")
                resolved = os.path.join(self.base_dir, os.path.basename(path))
        else:
            # For relative paths, resolve relative to base_dir
            resolved = os.path.normpath(os.path.join(self.base_dir, path))
            
        return resolved
        
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute a file operation.
        
        Args:
            action: The file action to perform
            path: Path to the file or directory
            content: Content to write (for write/append actions)
            target: Target path (for move/copy actions)
            encoding: File encoding (default: utf-8)
            
        Returns:
            Dictionary with action results
        """
        action = kwargs.get("action", "")
        path = kwargs.get("path", "")
        
        if not action:
            return {
                "status": "error",
                "error": "No action specified"
            }
            
        if not path:
            return {
                "status": "error",
                "error": "No file path specified"
            }
            
        # Resolve path safely
        resolved_path = self._resolve_path(path)
        
        # Execute the requested action
        if action == "read":
            return await self._read_file(resolved_path, kwargs.get("encoding", "utf-8"))
        elif action == "write":
            return await self._write_file(resolved_path, kwargs.get("content", ""), kwargs.get("encoding", "utf-8"))
        elif action == "append":
            return await self._append_file(resolved_path, kwargs.get("content", ""), kwargs.get("encoding", "utf-8"))
        elif action == "list":
            return await self._list_directory(resolved_path)
        elif action == "exists":
            return await self._check_exists(resolved_path)
        elif action == "delete":
            return await self._delete_file(resolved_path)
        elif action == "move":
            target = kwargs.get("target", "")
            if not target:
                return {
                    "status": "error",
                    "error": "No target path specified for move action"
                }
            resolved_target = self._resolve_path(target)
            return await self._move_file(resolved_path, resolved_target)
        elif action == "copy":
            target = kwargs.get("target", "")
            if not target:
                return {
                    "status": "error",
                    "error": "No target path specified for copy action"
                }
            resolved_target = self._resolve_path(target)
            return await self._copy_file(resolved_path, resolved_target)
        else:
            return {
                "status": "error",
                "error": f"Unknown action: {action}"
            }
            
    async def _read_file(self, path: str, encoding: str) -> Dict[str, Any]:
        """Read the contents of a file."""
        try:
            if not os.path.exists(path):
                return {
                    "status": "error",
                    "error": f"File does not exist: {path}",
                    "path": path
                }
                
            if not os.path.isfile(path):
                return {
                    "status": "error",
                    "error": f"Path is not a file: {path}",
                    "path": path
                }
                
            async with aiofiles.open(path, 'r', encoding=encoding) as f:
                content = await f.read()
                
            return {
                "status": "success",
                "path": path,
                "content": content,
                "size": len(content),
                "encoding": encoding
            }
            
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return {
                "status": "error",
                "error": f"Failed to read file: {str(e)}",
                "path": path
            }
            
    async def _write_file(self, path: str, content: str, encoding: str) -> Dict[str, Any]:
        """Write content to a file, creating if it doesn't exist."""
        try:
            # Ensure the directory exists
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                
            async with aiofiles.open(path, 'w', encoding=encoding) as f:
                await f.write(content)
                
            return {
                "status": "success",
                "path": path,
                "size": len(content),
                "action": "write"
            }
            
        except Exception as e:
            logger.error(f"Error writing to file {path}: {e}")
            return {
                "status": "error",
                "error": f"Failed to write file: {str(e)}",
                "path": path
            }
            
    async def _append_file(self, path: str, content: str, encoding: str) -> Dict[str, Any]:
        """Append content to an existing file."""
        try:
            # Ensure the directory exists
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                
            async with aiofiles.open(path, 'a', encoding=encoding) as f:
                await f.write(content)
                
            return {
                "status": "success",
                "path": path,
                "appended_size": len(content),
                "action": "append"
            }
            
        except Exception as e:
            logger.error(f"Error appending to file {path}: {e}")
            return {
                "status": "error",
                "error": f"Failed to append to file: {str(e)}",
                "path": path
            }
            
    async def _list_directory(self, path: str) -> Dict[str, Any]:
        """List the contents of a directory."""
        try:
            if not os.path.exists(path):
                return {
                    "status": "error",
                    "error": f"Path does not exist: {path}",
                    "path": path
                }
                
            if not os.path.isdir(path):
                return {
                    "status": "error",
                    "error": f"Path is not a directory: {path}",
                    "path": path
                }
                
            # Get directory contents
            items = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                stat_info = os.stat(item_path)
                
                items.append({
                    "name": item,
                    "path": item_path,
                    "is_dir": os.path.isdir(item_path),
                    "size": stat_info.st_size,
                    "modified": stat_info.st_mtime
                })
                
            return {
                "status": "success",
                "path": path,
                "items": items,
                "count": len(items)
            }
            
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            return {
                "status": "error",
                "error": f"Failed to list directory: {str(e)}",
                "path": path
            }
            
    async def _check_exists(self, path: str) -> Dict[str, Any]:
        """Check if a file or directory exists."""
        try:
            exists = os.path.exists(path)
            
            if exists:
                stat_info = os.stat(path)
                is_dir = os.path.isdir(path)
                
                return {
                    "status": "success",
                    "exists": True,
                    "path": path,
                    "is_dir": is_dir,
                    "size": stat_info.st_size if not is_dir else None,
                    "modified": stat_info.st_mtime
                }
            else:
                return {
                    "status": "success",
                    "exists": False,
                    "path": path
                }
                
        except Exception as e:
            logger.error(f"Error checking existence of {path}: {e}")
            return {
                "status": "error",
                "error": f"Failed to check if path exists: {str(e)}",
                "path": path
            }
            
    async def _delete_file(self, path: str) -> Dict[str, Any]:
        """Delete a file or directory."""
        try:
            if not os.path.exists(path):
                return {
                    "status": "error",
                    "error": f"Path does not exist: {path}",
                    "path": path
                }
                
            is_dir = os.path.isdir(path)
            
            if is_dir:
                shutil.rmtree(path)
            else:
                os.remove(path)
                
            return {
                "status": "success",
                "path": path,
                "deleted": True,
                "was_dir": is_dir
            }
            
        except Exception as e:
            logger.error(f"Error deleting {path}: {e}")
            return {
                "status": "error",
                "error": f"Failed to delete: {str(e)}",
                "path": path
            }
            
    async def _move_file(self, source: str, target: str) -> Dict[str, Any]:
        """Move a file or directory to a new location."""
        try:
            if not os.path.exists(source):
                return {
                    "status": "error",
                    "error": f"Source path does not exist: {source}",
                    "source": source,
                    "target": target
                }
                
            # Ensure target directory exists
            target_dir = os.path.dirname(target)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
                
            # Move the file or directory
            shutil.move(source, target)
            
            return {
                "status": "success",
                "source": source,
                "target": target,
                "action": "move"
            }
            
        except Exception as e:
            logger.error(f"Error moving {source} to {target}: {e}")
            return {
                "status": "error",
                "error": f"Failed to move: {str(e)}",
                "source": source,
                "target": target
            }
            
    async def _copy_file(self, source: str, target: str) -> Dict[str, Any]:
        """Copy a file or directory to a new location."""
        try:
            if not os.path.exists(source):
                return {
                    "status": "error",
                    "error": f"Source path does not exist: {source}",
                    "source": source,
                    "target": target
                }
                
            # Ensure target directory exists
            target_dir = os.path.dirname(target)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
                
            # Copy the file or directory
            if os.path.isdir(source):
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
                
            return {
                "status": "success",
                "source": source,
                "target": target,
                "action": "copy"
            }
            
        except Exception as e:
            logger.error(f"Error copying {source} to {target}: {e}")
            return {
                "status": "error",
                "error": f"Failed to copy: {str(e)}",
                "source": source,
                "target": target
            } 