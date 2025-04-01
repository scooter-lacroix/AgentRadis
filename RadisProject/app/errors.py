"""Error definitions for the Radis application.

This module defines the error hierarchy used throughout the Radis application.
It provides specialized error classes for different types of failures and
operations, each with appropriate error messages and context.
"""

from typing import Optional, Any, Dict


class RadisError(Exception):
    """Base exception class for all Radis-specific errors.

    Attributes:
        message: A user-friendly error message
        details: Additional context about the error
        cause: The underlying exception that caused this error
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        self.cause = cause
        super().__init__(self.message)


class IdentityError(RadisError):
    """Raised when identity-related operations fail.

    This includes model reference violations, context boundary issues,
    and identity rule violations.
    """

    def __init__(
        self,
        message: str,
        rule_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details = {"rule_name": rule_name, **kwargs}
        super().__init__(f"Identity violation: {message}", details)


class ConfigurationError(RadisError):
    """Raised when there are issues with application configuration.

    This includes invalid settings, missing required values, and
    configuration file issues.
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details = {"config_key": config_key, **kwargs}
        super().__init__(f"Configuration error: {message}", details)


class ToolError(RadisError):
    """Raised when tool operations fail.

    This includes tool initialization failures, execution errors,
    and invalid tool usage.
    """

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        command: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details = {"tool_name": tool_name, "command": command, **kwargs}
        super().__init__(f"Tool error: {message}", details)


class ResourceError(RadisError):
    """Raised when resource management operations fail.

    This includes file operations, memory management issues,
    and resource cleanup failures.
    """

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details = {"resource_type": resource_type, "resource_id": resource_id, **kwargs}
        super().__init__(f"Resource error: {message}", details)


class ValidationError(RadisError):
    """Raised when input validation fails.

    This includes parameter validation, data format validation,
    and schema validation.
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        expected_type: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details = {"field_name": field_name, "expected_type": expected_type, **kwargs}
        super().__init__(f"Validation error: {message}", details)


class SecurityError(RadisError):
    """Raised when security-related operations fail.

    This includes permission issues, unsafe operations,
    and security boundary violations.
    """

    def __init__(
        self,
        message: str,
        security_context: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details = {"security_context": security_context, **kwargs}
        super().__init__(f"Security violation: {message}", details)


class StateError(RadisError):
    """Raised when the application enters an invalid state.

    This includes inconsistent state, invalid transitions,
    and corrupted state data.
    """

    def __init__(
        self,
        message: str,
        current_state: Optional[str] = None,
        expected_state: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details = {
            "current_state": current_state,
            "expected_state": expected_state,
            **kwargs,
        }
        super().__init__(f"State error: {message}", details)

class RadisAuthenticationError(RadisError):
    """Raised when authentication or authorization fails.
    
    This error is raised for authentication-related issues including
    invalid credentials, token expiration, or insufficient permissions.
    """
    
    def __init__(
        self,
        message: str,
        auth_type: Optional[str] = None,
        scope: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if auth_type:
            error_details["auth_type"] = auth_type
        if scope:
            error_details["scope"] = scope
        
        super().__init__(message, error_details)
        self.auth_type = auth_type
        self.scope = scope
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        parts = [self.message]
        if self.auth_type:
            parts.append(f"Auth Type: {self.auth_type}")
        if self.scope:
            parts.append(f"Scope: {self.scope}")
        return " | ".join(parts)

class RadisExecutionError(RadisError):
    """Raised when command execution or response processing fails.
    
    This error is raised for failures during command execution,
    response deserialization, or other runtime execution issues.
    """
    
    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        output: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if command:
            error_details["command"] = command
        if exit_code is not None:
            error_details["exit_code"] = exit_code
        if output:
            error_details["output"] = output
        
        super().__init__(message, error_details)
        self.command = command
        self.exit_code = exit_code
        self.output = output
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        parts = [self.message]
        if self.command:
            parts.append(f"Command: {self.command}")
        if self.exit_code is not None:
            parts.append(f"Exit Code: {self.exit_code}")
        if self.output:
            parts.append(f"Output: {self.output}")
        return " | ".join(parts)


class RadisToolError(RadisError):
    """Raised when a Radis tool operation fails.
    
    This error is raised for tool-specific failures including
    initialization, execution, and result processing issues.
    """
    
    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        operation: Optional[str] = None,
        result: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if tool_name:
            error_details["tool_name"] = tool_name
        if operation:
            error_details["operation"] = operation
        if result is not None:
            error_details["result"] = str(result)
        
        super().__init__(message, error_details)
        self.tool_name = tool_name
        self.operation = operation
        self.result = result
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        parts = [self.message]
        if self.tool_name:
            parts.append(f"Tool: {self.tool_name}")
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        if self.result is not None:
            parts.append(f"Result: {self.result}")
        return " | ".join(parts)

"""Error classes for the Radis project."""




class APIConnectionError(RadisError):
    """Raised when the application fails to connect to an API endpoint.

    This error is raised for failures during API connection attempts,
    such as timeouts, connection refusals, or unavailable hosts.
    """

    def __init__(self, message: str, host: Optional[str] = None, port: Optional[int] = None, timeout: Optional[float] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if host:
            error_details["host"] = host
        if port:
            error_details["port"] = port
        if timeout is not None:
            error_details["timeout"] = timeout
        super().__init__(f"API connection error: {message}", error_details)

    def __str__(self) -> str:
        return f"{self.message} (Details: {self.details})"
class PlanningError(ToolError):
    """Exception raised for errors during plan creation or execution."""

    def __init__(
        self,
        message: str,
        plan_id: Optional[str] = None,
        step_number: Optional[int] = None,
        plan_state: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the planning error.

        Args:
            message: Human-readable error message
            plan_id: Optional identifier for the plan that failed
            step_number: Optional step number where the error occurred
            plan_state: Optional dictionary containing the plan's state at time of error
            details: Additional error context as a dictionary
        """
        super().__init__(
            message=message,
            tool_name="planning",
            operation=f"step_{step_number}" if step_number is not None else None,
            details=details,
        )
        self.plan_id = plan_id
        self.step_number = step_number
        self.plan_state = plan_state or {}

    def __str__(self) -> str:
        """Return a string representation of the error."""
        parts = [self.message]
        if self.plan_id:
            parts.append(f"Plan ID: {self.plan_id}")
        if self.step_number is not None:
            parts.append(f"Step: {self.step_number}")
        if self.plan_state:
            parts.append(f"Plan State: {self.plan_state}")
        return " | ".join(parts)


class ConfigurationError(RadisError):
    """Raised when there's an error in the configuration."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {"config_key": config_key} if config_key else None
        super().__init__(message, details)
        self.config_key = config_key


class DisplayError(RadisError):
    """Raised when there's an error in display operations."""

    pass


class RadisValidationError(RadisError):
    """Raised when input validation fails.
    
    This error is raised for validation-related issues including
    invalid field types, format violations, or constraint failures.
    """
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        expected_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ):
        error_details = details or {}
        if field_name:
            error_details["field_name"] = field_name
        if expected_type:
            error_details["expected_type"] = expected_type
        # Add any additional kwargs to the details
        for key, value in kwargs.items():
            error_details[key] = value
        
        super().__init__(message, error_details)
        self.field_name = field_name
        self.expected_type = expected_type
        # Store additional kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __str__(self) -> str:
        """Return a string representation of the error."""
        parts = [self.message]
        if self.field_name:
            parts.append(f"Field: {self.field_name}")
        if self.expected_type:
            parts.append(f"Expected Type: {self.expected_type}")
        # Add any additional attributes set from kwargs
        for key, value in self.details.items():
            if key not in ["field_name", "expected_type"] and value is not None:
                parts.append(f"{key.replace('_', ' ').title()}: {value}")
        return " | ".join(parts)
