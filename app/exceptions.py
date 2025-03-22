"""
Exceptions module for AgentRadis.

This module defines all custom exceptions used throughout the application
to provide consistent error handling and reporting.
"""
from typing import Any, Dict, List, Optional, Union


class AgentRadisException(Exception):
    """Base exception for all AgentRadis errors."""
    
    def __init__(self, message: str, *args, **kwargs):
        self.message = message
        super().__init__(message, *args, **kwargs)

    def __str__(self) -> str:
        return self.message


# LLM-related exceptions

class LLMException(AgentRadisException):
    """Base exception for LLM-related errors."""
    pass


class ModelUnavailableException(LLMException):
    """Exception raised when an LLM model is unavailable."""
    
    def __init__(self, model_name: str, reason: Optional[str] = None):
        self.model_name = model_name
        self.reason = reason
        message = f"Model '{model_name}' is unavailable"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class APILimitException(LLMException):
    """Exception raised when hitting API rate or token limits."""
    
    def __init__(self, api_name: str, limit_type: str, retry_after: Optional[int] = None):
        self.api_name = api_name
        self.limit_type = limit_type
        self.retry_after = retry_after
        message = f"{api_name} {limit_type} limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message)


class APIConnectionException(LLMException):
    """Exception raised when connection to an API fails."""
    
    def __init__(self, api_name: str, reason: str):
        self.api_name = api_name
        self.reason = reason
        message = f"Failed to connect to {api_name}: {reason}"
        super().__init__(message)


class InvalidPromptException(LLMException):
    """Exception raised when a prompt is invalid."""
    pass


class TokenLimitExceededException(LLMException):
    """Exception raised when the token limit is exceeded."""
    
    def __init__(self, token_count: int, token_limit: int):
        self.token_count = token_count
        self.token_limit = token_limit
        message = f"Token limit exceeded: {token_count} tokens (limit: {token_limit})"
        super().__init__(message)


class EmptyResponseException(LLMException):
    """Exception raised when the LLM returns an empty response."""
    
    def __init__(self, model_name: str, prompt_length: Optional[int] = None):
        self.model_name = model_name
        self.prompt_length = prompt_length
        message = f"Received empty response from {model_name}"
        if prompt_length:
            message += f" (prompt length: {prompt_length} tokens)"
        super().__init__(message)


# Tool-related exceptions

class ToolException(AgentRadisException):
    """Base exception for tool-related errors."""
    pass


class ToolExecutionException(ToolException):
    """Exception raised when a tool execution fails."""
    
    def __init__(self, tool_name: str, reason: str, details: Optional[Dict[str, Any]] = None):
        self.tool_name = tool_name
        self.reason = reason
        self.details = details or {}
        message = f"Tool '{tool_name}' execution failed: {reason}"
        super().__init__(message)


class InvalidToolArgumentException(ToolException):
    """Exception raised when a tool argument is invalid."""
    
    def __init__(self, tool_name: str, argument_name: str, value: Any, reason: str):
        self.tool_name = tool_name
        self.argument_name = argument_name
        self.value = value
        self.reason = reason
        message = f"Invalid argument '{argument_name}' for tool '{tool_name}': {reason}"
        super().__init__(message)


class ToolTimeoutException(ToolException):
    """Exception raised when a tool execution times out."""
    
    def __init__(self, tool_name: str, timeout: float):
        self.tool_name = tool_name
        self.timeout = timeout
        message = f"Tool '{tool_name}' execution timed out after {timeout} seconds"
        super().__init__(message)


class ToolNotFoundException(ToolException):
    """Exception raised when a requested tool is not found."""
    
    def __init__(self, tool_name: str, available_tools: Optional[List[str]] = None):
        self.tool_name = tool_name
        self.available_tools = available_tools
        message = f"Tool '{tool_name}' not found"
        if available_tools:
            message += f". Available tools: {', '.join(available_tools)}"
        super().__init__(message)


# Alias for backward compatibility
ToolError = ToolException


# Web and Browser exceptions

class WebException(AgentRadisException):
    """Base exception for web-related errors."""
    pass


class BrowserException(WebException):
    """Exception raised when a browser operation fails."""
    
    def __init__(self, operation: str, reason: str, url: Optional[str] = None):
        self.operation = operation
        self.reason = reason
        self.url = url
        message = f"Browser operation '{operation}' failed: {reason}"
        if url:
            message += f" (URL: {url})"
        super().__init__(message)


class WebSearchException(WebException):
    """Exception raised when a web search fails."""
    
    def __init__(self, engine: str, query: str, reason: str):
        self.engine = engine
        self.query = query
        self.reason = reason
        message = f"Web search with '{engine}' for '{query}' failed: {reason}"
        super().__init__(message)


class PageLoadException(BrowserException):
    """Exception raised when a page fails to load."""
    
    def __init__(self, url: str, reason: str, status_code: Optional[int] = None):
        self.url = url
        self.reason = reason
        self.status_code = status_code
        message = f"Failed to load page {url}: {reason}"
        if status_code:
            message += f" (status code: {status_code})"
        super().__init__("page_load", reason, url)


# Agent-related exceptions

class AgentException(AgentRadisException):
    """Base exception for agent-related errors."""
    pass


class AgentStateException(AgentException):
    """Exception raised when an agent's state is invalid."""
    pass


class LoopDetectedException(AgentException):
    """Exception raised when an agent is detected to be in a loop."""
    
    def __init__(self, iteration_count: int, pattern: Optional[str] = None):
        self.iteration_count = iteration_count
        self.pattern = pattern
        message = f"Loop detected after {iteration_count} iterations"
        if pattern:
            message += f": {pattern}"
        super().__init__(message)


class AgentTimeoutException(AgentRadisException):
    """
    Exception raised when an agent execution times out.
    
    This can be due to LLM response timing out, tool execution timeout,
    or the entire agent execution taking too long.
    
    Attributes:
        message: The error message
        steps_completed: Optional number of steps completed before timeout
    """
    def __init__(self, message: str, steps_completed: int = 0):
        self.steps_completed = steps_completed
        super().__init__(message)


# Other exceptions

class ConfigurationException(AgentRadisException):
    """Exception raised when there is a configuration error."""
    pass


class ResourceCleanupException(AgentRadisException):
    """Exception raised when resource cleanup fails."""
    
    def __init__(self, resource_type: str, resource_id: str, reason: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.reason = reason
        message = f"Failed to clean up {resource_type} '{resource_id}': {reason}"
        super().__init__(message)


class PermissionException(AgentRadisException):
    """Exception raised when there is a permission error."""
    
    def __init__(self, operation: str, resource: str, reason: str):
        self.operation = operation
        self.resource = resource
        self.reason = reason
        message = f"Permission denied for {operation} on {resource}: {reason}"
        super().__init__(message)


class ServerException(AgentRadisException):
    """Exception raised when there is a server error."""
    
    def __init__(self, status_code: int, reason: str):
        self.status_code = status_code
        self.reason = reason
        message = f"Server error ({status_code}): {reason}"
        super().__init__(message)
