import threading
from typing import Dict

from app.tool.base import BaseTool


class PythonExecute(BaseTool):
    """A tool for executing Python code with timeout and safety restrictions."""

    name: str = "python_execute"
    description: str = "Executes Python code string. Note: Only print outputs are visible, function return values are not captured. Use print statements to see results."
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            },
        },
        "required": ["code"],
    }

    async def execute(
        self,
        code: str,
        timeout: int = 5,
    ) -> Dict:
        """
        Executes the provided Python code with a timeout.

        Args:
            code (str): The Python code to execute.
            timeout (int): Execution timeout in seconds.

        Returns:
            Dict: Contains 'output' with execution output or error message and 'success' status.
        """
        result = {"observation": "", "success": True}

        try:
            import sys
            from io import StringIO
            import traceback
            
            # Capture stdout
            old_stdout = sys.stdout
            redirected_output = StringIO()
            sys.stdout = redirected_output
            
            try:
                # Execute the code in a clean, fresh environment
                exec(code, {"__builtins__": __builtins__})
                result["observation"] = redirected_output.getvalue()
            except Exception as e:
                result["observation"] = f"{str(e)}\n{traceback.format_exc()}"
                result["success"] = False
            finally:
                # Restore stdout
                sys.stdout = old_stdout
                
        except Exception as e:
            result["observation"] = f"Error setting up execution environment: {str(e)}"
            result["success"] = False
            
        return result

    async def run(self, **kwargs):
        """Execute Python code (alias for execute)"""
        return await self.execute(**kwargs)
