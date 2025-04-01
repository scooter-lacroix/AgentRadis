"""Custom exceptions for the RadisProject.

This module contains custom exceptions used throughout the application,
particularly for handling ROCm GPU processing, memory management, and
batch processing errors.
"""


class RadisBaseError(Exception):
    """Base exception class for all RadisProject custom exceptions."""

    pass


class ROCmNotAvailableError(RadisBaseError):
    """Raised when ROCm GPU acceleration is not available.

    This exception is raised when attempting to use ROCm acceleration
    features but the system either doesn't have ROCm installed or
    the GPU is not properly configured/detected.
    """

    pass


class GPUMemoryError(RadisBaseError):
    """Raised when GPU memory operations fail.

    This exception is raised in situations such as:
    - Insufficient GPU memory for the requested operation
    - Memory allocation failures
    - Memory cleanup failures
    """

    pass


class BatchProcessingError(RadisBaseError):
    """Raised when batch processing operations fail.

    This exception is raised when there are issues during batch processing:
    - Individual items in the batch fail to process
    - Batch size validation failures
    - Batch scheduling issues
    """

    pass


class ToolExecutionError(Exception):
    """Exception raised when a tool execution fails."""

    pass
