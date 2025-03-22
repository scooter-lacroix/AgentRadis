"""
Python Tool - Execute Python code
"""

import os
import traceback
import json
import sys
import io
import asyncio
import importlib
import inspect
from typing import Dict, Any, Optional, List
from contextlib import redirect_stdout, redirect_stderr

from app.tool.base import BaseTool
from app.logger import logger

class PythonTool(BaseTool):
    """
    Tool for executing Python code and importing modules.
    """
    
    name = "python"
    description = """
    Execute Python code, import modules, and call functions.
    This tool can run Python code snippets, import modules, and execute functions.
    """
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["execute", "import", "inspect"],
                "description": "The Python action to perform"
            },
            "code": {
                "type": "string",
                "description": "Python code to execute (for execute action)"
            },
            "module": {
                "type": "string",
                "description": "Module name to import or inspect (for import/inspect actions)"
            },
            "function": {
                "type": "string",
                "description": "Function name to inspect (for inspect action)"
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum execution time in seconds (default: 5)"
            }
        },
        "required": ["action"]
    }
    
    def __init__(self, **kwargs):
        """Initialize the Python tool."""
        super().__init__(**kwargs)
        self.globals = {}
        self.locals = {}
        
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute a Python operation.
        
        Args:
            action: The Python action to perform
            code: Python code to execute (for execute action)
            module: Module name to import or inspect (for import/inspect actions)
            function: Function name to inspect (for inspect action)
            timeout: Maximum execution time in seconds
            
        Returns:
            Dictionary with action results
        """
        action = kwargs.get("action", "")
        
        if not action:
            return {
                "status": "error",
                "error": "No action specified"
            }
            
        # Execute the requested action
        if action == "execute":
            code = kwargs.get("code", "")
            if not code:
                return {
                    "status": "error",
                    "error": "No code provided for execution"
                }
            timeout = kwargs.get("timeout", 5)
            return await self._execute_code(code, timeout)
            
        elif action == "import":
            module_name = kwargs.get("module", "")
            if not module_name:
                return {
                    "status": "error",
                    "error": "No module name provided for import"
                }
            return await self._import_module(module_name)
            
        elif action == "inspect":
            module_name = kwargs.get("module", "")
            function_name = kwargs.get("function", "")
            
            if not module_name:
                return {
                    "status": "error",
                    "error": "No module name provided for inspection"
                }
                
            return await self._inspect_module(module_name, function_name)
            
        else:
            return {
                "status": "error",
                "error": f"Unknown action: {action}"
            }
            
    async def _execute_code(self, code: str, timeout: int) -> Dict[str, Any]:
        """Execute Python code with output capture."""
        # Create string IO objects to capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Set up the globals dictionary with access to our already imported modules
        if not self.globals:
            # Initialize with a fresh copy if empty
            self.globals = {
                "__builtins__": __builtins__,
                "json": json,
                "os": os,
                "sys": sys,
            }
            
        try:
            # Define an async function to execute the code with a timeout
            async def run_code_with_timeout():
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    try:
                        # Compile the code
                        compiled_code = compile(code, "<string>", "exec")
                        
                        # Execute in the context of our globals and locals
                        exec(compiled_code, self.globals, self.locals)
                        
                        # Merge locals back into globals for future calls
                        self.globals.update(self.locals)
                        
                        return True, None
                    except Exception as e:
                        tb = traceback.format_exc()
                        return False, tb
            
            # Execute with timeout
            try:
                success, error = await asyncio.wait_for(run_code_with_timeout(), timeout)
            except asyncio.TimeoutError:
                return {
                    "status": "error",
                    "error": f"Execution timed out after {timeout} seconds",
                    "stdout": stdout_capture.getvalue(),
                    "stderr": stderr_capture.getvalue()
                }
                
            # Get the captured output
            stdout = stdout_capture.getvalue()
            stderr = stderr_capture.getvalue()
            
            if success:
                return {
                    "status": "success",
                    "stdout": stdout,
                    "stderr": stderr,
                    "result": str(self.locals.get("result", "No result variable set"))
                }
            else:
                return {
                    "status": "error",
                    "error": "Execution failed",
                    "traceback": error,
                    "stdout": stdout,
                    "stderr": stderr
                }
                
        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            return {
                "status": "error",
                "error": f"Failed to execute code: {str(e)}",
                "traceback": traceback.format_exc()
            }
            
    async def _import_module(self, module_name: str) -> Dict[str, Any]:
        """Import a Python module and add it to globals."""
        try:
            # Attempt to import the module
            module = importlib.import_module(module_name)
            
            # Add it to our globals dictionary
            self.globals[module_name] = module
            
            # Get module members
            members = []
            for name, member in inspect.getmembers(module):
                if not name.startswith("_"):  # Skip private members
                    kind = type(member).__name__
                    members.append({
                        "name": name,
                        "type": kind
                    })
                    
            return {
                "status": "success",
                "module": module_name,
                "members": members[:50],  # Limit to 50 members to avoid huge responses
                "total_members": len(members)
            }
            
        except ImportError as e:
            logger.error(f"Error importing module {module_name}: {e}")
            return {
                "status": "error",
                "error": f"Module not found: {module_name}",
                "details": str(e)
            }
        except Exception as e:
            logger.error(f"Error importing module {module_name}: {e}")
            return {
                "status": "error",
                "error": f"Failed to import module: {str(e)}",
                "traceback": traceback.format_exc()
            }
            
    async def _inspect_module(self, module_name: str, function_name: str = "") -> Dict[str, Any]:
        """Inspect a module or a specific function within a module."""
        try:
            # Try to import the module if it's not already in globals
            if module_name not in self.globals:
                import_result = await self._import_module(module_name)
                if import_result["status"] != "success":
                    return import_result
                    
            module = self.globals[module_name]
            
            # If a function name is provided, inspect that function
            if function_name:
                if not hasattr(module, function_name):
                    return {
                        "status": "error",
                        "error": f"Function '{function_name}' not found in module '{module_name}'"
                    }
                    
                func = getattr(module, function_name)
                
                # Get function signature and docstring
                signature = str(inspect.signature(func))
                doc = inspect.getdoc(func) or "No documentation available"
                
                return {
                    "status": "success",
                    "module": module_name,
                    "function": function_name,
                    "signature": signature,
                    "documentation": doc,
                    "is_async": inspect.iscoroutinefunction(func)
                }
                
            else:
                # Inspect the module itself
                doc = inspect.getdoc(module) or "No module documentation available"
                
                # Get a list of functions and classes
                functions = []
                classes = []
                
                for name, member in inspect.getmembers(module):
                    if name.startswith("_"):
                        continue
                        
                    if inspect.isfunction(member):
                        functions.append({
                            "name": name,
                            "signature": str(inspect.signature(member)),
                            "is_async": inspect.iscoroutinefunction(member)
                        })
                    elif inspect.isclass(member):
                        classes.append({
                            "name": name,
                            "bases": [base.__name__ for base in member.__bases__]
                        })
                        
                return {
                    "status": "success",
                    "module": module_name,
                    "documentation": doc,
                    "functions": functions[:20],  # Limit to 20 entries
                    "classes": classes[:20],      # Limit to 20 entries
                    "total_functions": len(functions),
                    "total_classes": len(classes)
                }
                
        except Exception as e:
            logger.error(f"Error inspecting module {module_name}: {e}")
            return {
                "status": "error",
                "error": f"Failed to inspect module: {str(e)}",
                "traceback": traceback.format_exc()
            } 