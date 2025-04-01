"""Error classes for the agent module."""


class ToolNotFoundError(Exception):
    """Raised when a requested tool cannot be found in the agent's tool registry.
    
    This error occurs when attempting to use a tool that either hasn't been
    registered with the agent or isn't available in the current context.
    """
    pass


class ToolExecutionError(Exception):
    """Raised when a tool fails during execution.
    
    This error occurs when a tool encounters an error while performing its
    operation, such as file I/O failures, network errors, or invalid inputs.
    """
    pass


class SecurityError(Exception):
    """Raised when a security violation is detected.
    
    This error occurs when an operation attempts to violate security boundaries,
    such as accessing restricted paths or performing unauthorized actions.
    """
    pass

