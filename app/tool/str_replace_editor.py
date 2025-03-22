"""
String replacement editor tool for text manipulation.
"""
import os
import re
from typing import Any, Dict, List, Optional

from app.logger import logger
from app.tool.base import BaseTool

class StrReplaceEditor(BaseTool):
    """
    Tool for replacing text in files using string or regex patterns.
    """
    
    name = "str_replace_editor"
    description = """
    Replace text in files using string or regex patterns.
    This tool allows for simple text replacement or more complex regex-based substitutions.
    """
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit"
            },
            "search": {
                "type": "string",
                "description": "Text or pattern to search for"
            },
            "replace": {
                "type": "string",
                "description": "Text to replace the search pattern with"
            },
            "use_regex": {
                "type": "boolean",
                "description": "Whether to interpret the search pattern as a regex (default: false)"
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether the search should be case sensitive (default: true)"
            },
            "occurrence": {
                "type": "integer",
                "description": "Which occurrence to replace (0 for all, 1 for first, etc., default: 0)"
            }
        },
        "required": ["file_path", "search", "replace"]
    }
    
    def __init__(self, **kwargs):
        """Initialize the string replacement editor tool."""
        super().__init__(**kwargs)
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute a string replacement.
        
        Args:
            file_path: Path to the file to edit
            search: Text or pattern to search for
            replace: Text to replace the search pattern with
            use_regex: Whether to interpret the search pattern as a regex
            case_sensitive: Whether the search should be case sensitive
            occurrence: Which occurrence to replace (0 for all)
            
        Returns:
            Dictionary with replacement results
        """
        file_path = kwargs.get("file_path")
        search = kwargs.get("search")
        replace = kwargs.get("replace")
        use_regex = kwargs.get("use_regex", False)
        case_sensitive = kwargs.get("case_sensitive", True)
        occurrence = kwargs.get("occurrence", 0)
        
        if not file_path:
            return {
                "status": "error",
                "error": "No file path provided"
            }
        
        if not search:
            return {
                "status": "error",
                "error": "No search pattern provided"
            }
        
        if replace is None:
            return {
                "status": "error",
                "error": "No replacement text provided"
            }
        
        # Normalize and validate file path
        file_path = os.path.expanduser(file_path)
        if not os.path.isfile(file_path):
            return {
                "status": "error",
                "error": f"File not found: {file_path}"
            }
        
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            count = 0
            
            # Perform the replacement
            if use_regex:
                # Regex replacement
                flags = 0 if case_sensitive else re.IGNORECASE
                
                if occurrence > 0:
                    # Replace specific occurrence
                    parts = []
                    last_end = 0
                    curr_occurrence = 0
                    
                    for match in re.finditer(search, content, flags):
                        curr_occurrence += 1
                        if curr_occurrence == occurrence:
                            parts.append(content[last_end:match.start()])
                            parts.append(replace)
                            last_end = match.end()
                            count = 1
                            break
                    
                    if count == 1:
                        parts.append(content[last_end:])
                        content = ''.join(parts)
                else:
                    # Replace all occurrences
                    content, count = re.subn(search, replace, content, flags=flags)
            else:
                # Simple string replacement
                if not case_sensitive:
                    def repl_func(match):
                        nonlocal count
                        count += 1
                        return replace
                    
                    if occurrence > 0:
                        # Replace specific occurrence
                        pattern = re.escape(search)
                        parts = []
                        last_end = 0
                        curr_occurrence = 0
                        
                        for match in re.finditer(pattern, content, re.IGNORECASE):
                            curr_occurrence += 1
                            if curr_occurrence == occurrence:
                                parts.append(content[last_end:match.start()])
                                parts.append(replace)
                                last_end = match.end()
                                count = 1
                                break
                        
                        if count == 1:
                            parts.append(content[last_end:])
                            content = ''.join(parts)
                    else:
                        # Replace all occurrences
                        pattern = re.escape(search)
                        content = re.sub(pattern, repl_func, content, flags=re.IGNORECASE)
                else:
                    if occurrence > 0:
                        # Replace specific occurrence
                        parts = content.split(search)
                        if len(parts) > occurrence:
                            content = search.join(parts[:occurrence]) + replace + search.join(parts[occurrence:])
                            count = 1
                    else:
                        # Replace all occurrences
                        content = content.replace(search, replace)
                        count = content.count(replace) if search != replace else content.count(search)
            
            # Write back to the file if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return {
                    "status": "success",
                    "file_path": file_path,
                    "replacements": count,
                    "message": f"Made {count} replacements in the file"
                }
            else:
                return {
                    "status": "success",
                    "file_path": file_path,
                    "replacements": 0,
                    "message": "No replacements made (pattern not found)"
                }
                
        except Exception as e:
            logger.error(f"Error replacing text in {file_path}: {str(e)}")
            return {
                "status": "error",
                "file_path": file_path,
                "error": f"Failed to replace text: {str(e)}"
            }
    
    async def cleanup(self):
        """Clean up resources."""
        pass
    
    async def reset(self):
        """Reset the tool state."""
        pass 