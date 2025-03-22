"""
Tool for handling file uploads and processing.
"""

import os
import shutil
import mimetypes
import magic
from typing import Dict, Any, Optional, List
from pathlib import Path

from app.tool.base import BaseTool
from app.logger import logger

class FileHandler(BaseTool):
    """Tool for handling file uploads and processing."""
    
    name = "file_handler"
    description = """
    Handle file uploads and processing. Can:
    - Process uploaded files
    - Read file contents
    - Extract text from documents
    - Handle various file types including PDFs, images, and text files
    """
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "The action to perform ('upload', 'read', 'extract_text')",
                "enum": ["upload", "read", "extract_text"]
            },
            "file_path": {
                "type": "string",
                "description": "Path to the file (for local files)"
            },
            "file_content": {
                "type": "string",
                "description": "Base64 encoded content of the file (for uploaded files)"
            },
            "file_name": {
                "type": "string",
                "description": "Name of the file (for uploaded files)"
            }
        },
        "required": ["action"]
    }
    
    def __init__(self):
        """Initialize the file handler tool."""
        super().__init__()
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)
        
    async def run(self, 
                  action: str,
                  file_path: Optional[str] = None,
                  file_content: Optional[bytes] = None,
                  file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute file handling operations.
        
        Args:
            action: The action to perform ('upload', 'read', 'extract_text')
            file_path: Path to the file (for local files)
            file_content: Binary content of the file (for uploaded files)
            file_name: Name of the file (for uploaded files)
            
        Returns:
            Dict containing operation results
        """
        try:
            if action == "upload":
                return await self._handle_upload(file_path, file_content, file_name)
            elif action == "read":
                return await self._read_file(file_path or file_name)
            elif action == "extract_text":
                return await self._extract_text(file_path or file_name)
            else:
                raise ValueError(f"Unknown action: {action}")
                
        except Exception as e:
            logger.error(f"Error in file handler: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
            
    async def _handle_upload(self, 
                           file_path: Optional[str] = None,
                           file_content: Optional[bytes] = None,
                           file_name: Optional[str] = None) -> Dict[str, Any]:
        """Handle file upload from either path or content."""
        try:
            if file_path:
                # Copy local file to uploads directory
                src_path = Path(file_path)
                if not src_path.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                    
                dest_path = self.upload_dir / src_path.name
                shutil.copy2(src_path, dest_path)
                
                return {
                    "status": "success",
                    "message": f"File uploaded: {src_path.name}",
                    "path": str(dest_path),
                    "size": dest_path.stat().st_size,
                    "mime_type": self._get_mime_type(dest_path)
                }
                
            elif file_content and file_name:
                # Save uploaded content to file
                dest_path = self.upload_dir / file_name
                dest_path.write_bytes(file_content)
                
                return {
                    "status": "success",
                    "message": f"File uploaded: {file_name}",
                    "path": str(dest_path),
                    "size": len(file_content),
                    "mime_type": self._get_mime_type(dest_path)
                }
                
            else:
                raise ValueError("Either file_path or (file_content, file_name) must be provided")
                
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
            
    async def _read_file(self, file_path: str) -> Dict[str, Any]:
        """Read file contents."""
        try:
            path = Path(file_path)
            if not path.is_absolute():
                path = self.upload_dir / path
                
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
                
            mime_type = self._get_mime_type(path)
            
            # Handle different file types
            if mime_type.startswith('text/'):
                content = path.read_text()
            else:
                content = f"Binary file: {mime_type}"
                
            return {
                "status": "success",
                "content": content,
                "mime_type": mime_type
            }
            
        except Exception as e:
            logger.error(f"Read error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
            
    async def _extract_text(self, file_path: str) -> Dict[str, Any]:
        """Extract text from document files."""
        try:
            path = Path(file_path)
            if not path.is_absolute():
                path = self.upload_dir / path
                
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
                
            mime_type = self._get_mime_type(path)
            
            # Handle different document types
            if mime_type == 'application/pdf':
                # Use PyPDF2 for PDF text extraction
                import PyPDF2
                with open(path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                        
            elif mime_type.startswith('text/'):
                text = path.read_text()
                
            else:
                raise ValueError(f"Unsupported file type for text extraction: {mime_type}")
                
            return {
                "status": "success",
                "text": text,
                "mime_type": mime_type
            }
            
        except Exception as e:
            logger.error(f"Text extraction error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
            
    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type of a file."""
        try:
            # Try using python-magic first for more accurate detection
            mime = magic.Magic(mime=True)
            return mime.from_file(str(file_path))
        except:
            # Fall back to mimetypes module
            mime_type, _ = mimetypes.guess_type(str(file_path))
            return mime_type or 'application/octet-stream'
            
    async def cleanup(self):
        """Clean up uploaded files."""
        try:
            if self.upload_dir.exists():
                shutil.rmtree(self.upload_dir)
        except Exception as e:
            logger.error(f"Error cleaning up uploads: {e}")

    async def execute(self, path: str, operation: str = "read", content: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a file operation
        
        Args:
            path: Path to the file
            operation: Operation to perform (read, write, type)
            content: Content to write (for write operation)
            
        Returns:
            Dict containing operation result
        """
        try:
            if operation == "read":
                if not os.path.exists(path):
                    return {
                        'status': 'error',
                        'error': f"File not found: {path}"
                    }
                    
                with open(path, 'r') as f:
                    content = f.read()
                    
                return {
                    'status': 'success',
                    'content': content
                }
                
            elif operation == "write":
                if content is None:
                    return {
                        'status': 'error',
                        'error': "No content provided for write operation"
                    }
                    
                with open(path, 'w') as f:
                    f.write(content)
                    
                return {
                    'status': 'success',
                    'message': f"Successfully wrote to {path}"
                }
                
            elif operation == "type":
                if not os.path.exists(path):
                    return {
                        'status': 'error',
                        'error': f"File not found: {path}"
                    }
                    
                mime = magic.Magic(mime=True)
                file_type = mime.from_file(path)
                
                return {
                    'status': 'success',
                    'type': file_type
                }
                
            else:
                return {
                    'status': 'error',
                    'error': f"Unsupported operation: {operation}"
                }
                
        except Exception as e:
            logger.error(f"Error handling file operation: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            } 