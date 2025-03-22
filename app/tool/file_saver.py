import os
import json
import base64
from typing import Dict, Any, Optional, List, Union

from app.tool.base import BaseTool
from app.logger import logger

class FileSaver(BaseTool):
    """Tool for saving files to the local system."""
    
    name = "file_saver"
    description = """
    Save files to the local filesystem.
    This tool can save text content, binary data (base64-encoded), and JSON data to files.
    It will create directories in the path if they don't exist.
    """
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path where the file should be saved (relative to the working directory)"
            },
            "content": {
                "type": "string",
                "description": "The content to save to the file"
            },
            "format": {
                "type": "string",
                "enum": ["text", "binary", "json"],
                "description": "The format of the content: text (default), binary (base64-encoded), or json"
            },
            "append": {
                "type": "boolean",
                "description": "Whether to append to the file instead of overwriting it"
            }
        },
        "required": ["path", "content"]
    }
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Save a file to the local filesystem.
        
        Args:
            path: Path where the file should be saved
            content: Content to save
            format: Format of the content (text, binary, json)
            append: Whether to append to the file
            
        Returns:
            Dictionary with the result of the operation
        """
        path = kwargs.get("path")
        content = kwargs.get("content", "")
        format_type = kwargs.get("format", "text").lower()
        append = kwargs.get("append", False)
        
        if not path:
            return {
                "status": "error",
                "error": "No path provided"
            }
            
        try:
            # Ensure directory exists
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                
            # Handle different content formats
            if format_type == "binary":
                return await self._save_binary(path, content, append)
            elif format_type == "json":
                return await self._save_json(path, content, append)
            else:
                return await self._save_text(path, content, append)
                
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return {
                "status": "error",
                "error": f"Failed to save file: {str(e)}"
            }
            
    async def _save_text(self, path: str, content: str, append: bool) -> Dict[str, Any]:
        """Save text content to a file."""
        mode = "a" if append else "w"
        
        try:
            with open(path, mode, encoding="utf-8") as f:
                f.write(content)
                
            logger.info(f"Saved text file: {path}")
            return {
                "status": "success",
                "path": path,
                "bytes_written": len(content.encode('utf-8')),
                "message": f"File saved successfully at {path}"
            }
            
        except Exception as e:
            logger.error(f"Error saving text file: {e}")
            return {
                "status": "error",
                "error": f"Failed to save text file: {str(e)}"
            }
            
    async def _save_binary(self, path: str, content: str, append: bool) -> Dict[str, Any]:
        """Save binary content (base64-encoded) to a file."""
        try:
            # Decode base64 content
            try:
                binary_data = base64.b64decode(content)
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Invalid base64 encoding: {str(e)}"
                }
                
            # Write binary data
            mode = "ab" if append else "wb"
            with open(path, mode) as f:
                f.write(binary_data)
                
            logger.info(f"Saved binary file: {path}")
            return {
                "status": "success",
                "path": path,
                "bytes_written": len(binary_data),
                "message": f"Binary file saved successfully at {path}"
            }
            
        except Exception as e:
            logger.error(f"Error saving binary file: {e}")
            return {
                "status": "error",
                "error": f"Failed to save binary file: {str(e)}"
            }
            
    async def _save_json(self, path: str, content: Union[str, Dict], append: bool) -> Dict[str, Any]:
        """Save JSON content to a file."""
        try:
            # Parse JSON if string
            if isinstance(content, str):
                try:
                    json_content = json.loads(content)
                except json.JSONDecodeError as e:
                    return {
                        "status": "error",
                        "error": f"Invalid JSON content: {str(e)}"
                    }
            else:
                json_content = content
                
            # Write JSON with proper formatting
            mode = "a" if append else "w"
            with open(path, mode, encoding="utf-8") as f:
                if append:
                    f.write("\n")
                json.dump(json_content, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved JSON file: {path}")
            return {
                "status": "success",
                "path": path,
                "message": f"JSON file saved successfully at {path}"
            }
            
        except Exception as e:
            logger.error(f"Error saving JSON file: {e}")
            return {
                "status": "error",
                "error": f"Failed to save JSON file: {str(e)}"
            }
