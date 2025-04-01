import ast
import io
import math
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict, List, Optional

import jsonschema
from app.tool.base import BaseTool


class PythonTool(BaseTool):
    @staticmethod
    def factorial(n: int) -> int:
        """Calculate factorial of a non-negative integer."""
        if not isinstance(n, int) or n < 0:
            raise ValueError("Factorial requires a non-negative integer")
        if n == 0:
            return 1
        result = 1
        for i in range(1, n + 1):
            result *= i
        return result

    @staticmethod
    def fibonacci(n: int) -> List[int]:
        """Generate Fibonacci sequence of n numbers."""
        if not isinstance(n, int) or n < 0:
            raise ValueError("Fibonacci requires a non-negative integer")
        if n == 0:
            return []
        if n == 1:
            return [0]
        sequence = [0, 1]
        while len(sequence) < n:
            sequence.append(sequence[-1] + sequence[-2])
        return sequence
    """Tool for safely executing Python code in a restricted environment.

    This tool allows users to execute Python code with proper security measures
    to prevent unauthorized access to system resources. It supports maintaining
    execution context between multiple runs.

    Attributes:
        _context (dict): Dictionary to store variables between executions
        _max_execution_time (int): Maximum time allowed for code execution in seconds
    """

    def __init__(self, max_execution_time: int = 5):
        """Initialize the Python execution tool.

        Args:
            max_execution_time: Maximum time (in seconds) allowed for code execution
        """
        self._context = {
            # Add math module
            'math': math,
            # Add utility functions
            'factorial': self.factorial,
            'fibonacci': self.fibonacci,
            # Add common built-ins
            'min': min,
            'max': max,
            'sum': sum,
            'abs': abs,
            'len': len,
            'round': round,
            'sorted': sorted,
        }
        self._max_execution_time = max_execution_time

    @property
    def name(self) -> str:
        """The name of the tool."""
        return "python_execute"

    @property
    def description(self) -> str:
        """A human-readable description of what the tool does."""
        return (
            "Executes Python code in a secure, sandboxed environment. "
            "Can maintain an execution context across multiple calls for stateful operations. "
            "Captures standard output, standard error, and return values."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        """JSON schema describing the tool's parameters."""
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
                "maintain_context": {
                    "type": "boolean",
                    "description": "Whether to maintain the execution context between calls",
                    "default": True,
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds (overrides default)",
                    "minimum": 1,
                    "maximum": 30,
                    "default": 5,
                },
                "description": {
                    "type": "string",
                    "description": "Optional description of what the code does (for logging)",
                    "default": "",
                },
            },
            "required": ["code"],
        }

    def _is_safe_code(self, code: str) -> bool:
        """Check if the code is safe to execute.

        Performs a basic security check to prevent dangerous operations.

        Args:
            code: Python code to check

        Returns:
            True if the code appears safe, False otherwise
        """
        # List of potentially dangerous modules/functions
        dangerous_imports = [
            "subprocess",
            "os.system",
            "shutil.rmtree",
            "os.remove",
            "sys.modules",
            "importlib",
            "__import__",
            "eval",
            "exec",
        ]

        try:
            # Parse the code to check for potentially dangerous imports/calls
            parsed = ast.parse(code)

            for node in ast.walk(parsed):
                # Check for imports
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if any(
                            name.name.startswith(dangerous)
                            for dangerous in dangerous_imports
                        ):
                            return False

                # Check for import from
                elif isinstance(node, ast.ImportFrom):
                    if any(
                        node.module.startswith(dangerous)
                        for dangerous in dangerous_imports
                    ):
                        return False
                    for name in node.names:
                        if any(
                            name.name.startswith(dangerous)
                            for dangerous in dangerous_imports
                        ):
                            return False

                # Check for potentially dangerous function calls
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in [
                        "eval",
                        "exec",
                        "__import__",
                    ]:
                        return False
                    elif isinstance(node.func, ast.Attribute):
                        full_name = self._get_attribute_name(node.func)
                        if any(
                            dangerous in full_name for dangerous in dangerous_imports
                        ):
                            return False

            return True
        except SyntaxError:
            # If we can't parse the code, it's either invalid or potentially malicious
            return False

    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Recursively build the full attribute name (e.g., 'os.path.join').

        Args:
            node: AST Attribute node

        Returns:
            Full attribute name as string
        """
        if isinstance(node.value, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        elif isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        return node.attr

    async def run(self, **kwargs) -> Dict[str, Any]:
        """Execute Python code in a restricted environment.

        Args:
            code (str): Python code to execute
            maintain_context (bool, optional): Whether to maintain variables between calls
            timeout (int, optional): Maximum execution time in seconds
            description (str, optional): Description of what the code does (for logging)

        Returns:
            Dict with stdout, stderr, result, and error information

        Raises:
            ValueError: If the code fails safety checks
            jsonschema.ValidationError: If parameters are invalid
        """
        # Validate parameters
        params = self.validate_parameters(kwargs)
        code = params["code"]
        maintain_context = params.get("maintain_context", True)
        timeout = params.get("timeout", self._max_execution_time)
        description = params.get("description", "")

        # Check if the code is safe to execute
        if not self._is_safe_code(code):
            raise ValueError(
                "Code contains potentially unsafe operations. "
                "For security reasons, this code cannot be executed."
            )

        # Prepare result container
        result = {
            "stdout": "",
            "stderr": "",
            "result": None,
            "error": None,
            "execution_successful": False,
        }

        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        # Save original globals to restore restricted environment
        original_globals = dict(globals())

        # Prepare execution globals - either from context or a fresh dict
        exec_globals = self._context.copy() if maintain_context else {}

        try:
            # Execute the code with captured stdout/stderr
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # First compile the code to support return values
                compiled_code = compile(code, "<string>", "exec")

                # Prepare locals dict to catch return values
                local_vars = {}

                # Execute with timeout (basic implementation - for more robust timeout,
                # consider using threading or signal-based approaches)
                exec(compiled_code, exec_globals, local_vars)

                # If the execution returns a value (using the last expression), capture it
                if "result" in local_vars:
                    result["result"] = local_vars["result"]

            # Update result information
            result["stdout"] = stdout_capture.getvalue()
            result["stderr"] = stderr_capture.getvalue()
            result["execution_successful"] = True

            # Update context if requested
            if maintain_context:
                self._context.update(exec_globals)
                # Also add any local variables defined
                self._context.update(local_vars)

        except Exception as e:
            # Capture error information
            result["error"] = {
                "type": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc(),
            }
            result["stderr"] = f"{stderr_capture.getvalue()}\n{traceback.format_exc()}"

        finally:
            # Clean up and return
            return result

    async def cleanup(self) -> None:
        """Clean up any resources used by the tool."""
        # For this tool, we just clear the context
        self._context.clear()

    async def reset(self) -> None:
        """Reset the tool to its initial state."""
        # Reset the context and any other state
        self._context.clear()

    def get_context(self) -> Dict[str, Any]:
        """Get the current execution context.

        Returns:
            Dictionary containing all variables in the current context
        """
        return self._context.copy()

    def set_context(self, context: Dict[str, Any]) -> None:
        """Set the execution context.

        Args:
            context: Dictionary of variables to set in the context
        """
        self._context = context.copy()
