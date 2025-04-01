import logging
import os
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, Union, Dict, Any
from functools import wraps

from app.schema.enums import LogLevel

"""
Radis logging module providing centralized logging functionality.

This module provides a comprehensive logging system with the following features:
- Consistent log formatting across console and file outputs
- Debug logging capabilities with easy enable/disable functions
- Support for both console and file handlers
- Log rotation for file handlers
- Integration with LogLevel enum for type-safe level management
- ISO 8601 timestamp format (YYYY-MM-DD HH:MM:SS)
"""


@dataclass
class SecurityContext:
    """Security context for enhanced logging."""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    operation: Optional[str] = None
    resource: Optional[str] = None


class SecurityFormatter(logging.Formatter):
    """Enhanced formatter for security events."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | [SECURITY] | User: %(user_id)s | Session: %(session_id)s | Operation: %(operation)s | Resource: %(resource)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record):
        # Add security context if not present
        if not hasattr(record, "user_id"):
            record.user_id = "UNKNOWN"
        if not hasattr(record, "session_id"):
            record.session_id = "UNKNOWN"
        if not hasattr(record, "operation"):
            record.operation = "UNKNOWN"
        if not hasattr(record, "resource"):
            record.resource = "UNKNOWN"
        return super().format(record)


class RadisFormatter(logging.Formatter):
    """Standard formatter for regular logs."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


class ErrorFormatter(logging.Formatter):
    """Enhanced formatter for error logs with stack traces."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s\nStack Trace:\n%(stack_trace)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record):
        if not hasattr(record, "stack_trace"):
            record.stack_trace = "".join(traceback.format_stack())
        return super().format(record)


class ToolExecutionFormatter(logging.Formatter):
    """Formatter for tool execution tracking."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | TOOL | Name: %(tool_name)s | Duration: %(duration).3fs | Status: %(status)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_root_logger() -> logging.Logger:
    """Configure the root logger with both console and file handlers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Clear existing handlers to prevent duplicates
    root_logger.handlers.clear()

    formatter = RadisFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    log_dir = os.path.expanduser("~/.agentradis/logs")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "root.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return root_logger


def log_security_event(
    logger: logging.Logger, message: str, context: SecurityContext
) -> None:
    """Log a security event with context."""
    extra = {
        "user_id": context.user_id,
        "session_id": context.session_id,
        "operation": context.operation,
        "resource": context.resource,
    }
    logger.info(message, extra=extra)


def log_error_with_trace(
    logger: logging.Logger, message: str, exc_info: Optional[Exception] = None
) -> None:
    """Log an error with full stack trace."""
    if exc_info:
        trace = "".join(
            traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__)
        )
    else:
        trace = "".join(traceback.format_stack())
    logger.error(message, extra={"stack_trace": trace})


def track_tool_execution(logger: logging.Logger):
    """Decorator to track tool execution time and status."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            tool_name = func.__name__
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    f"Tool execution completed",
                    extra={
                        "tool_name": tool_name,
                        "duration": duration,
                        "status": "SUCCESS",
                    },
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Tool execution failed: {str(e)}",
                    extra={
                        "tool_name": tool_name,
                        "duration": duration,
                        "status": "FAILED",
                    },
                )
                raise

        return wrapper

    return decorator


def setup_logger(
    name: str,
    level: Union[int, str] = logging.INFO,
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """Configure and return a logger instance with both console and optional file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # Prevent propagation to root logger

    # Create formatter
    formatter = RadisFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file is specified)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def set_log_level(logger: Union[str, logging.Logger], level: Union[int, str]) -> None:
    """Set the log level for a specific logger."""
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    logger.setLevel(level)


def get_log_level(logger: Union[str, logging.Logger]) -> int:
    """Get the current log level of a logger."""
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    return logger.level


def get_logger(
    name: str, level: Union[int, str] = logging.INFO, log_file: Optional[str] = None
) -> logging.Logger:
    """Get a configured logger instance for the given name."""
    return setup_logger(name, level, log_file)


def enable_debug_logging() -> None:
    """Enable debug logging for all loggers."""
    logging.getLogger().setLevel(logging.DEBUG)
    for handler in logging.getLogger().handlers:
        handler.setLevel(logging.DEBUG)


def disable_debug_logging() -> None:
    """Disable debug logging for all loggers."""
    logging.getLogger().setLevel(logging.INFO)
    for handler in logging.getLogger().handlers:
        handler.setLevel(logging.INFO)


# Initialize root logger at module load
root_logger = setup_root_logger()

# Default logger instance for general use
logger = get_logger(
    "radis",
    level=logging.INFO,
    log_file=os.path.expanduser("~/.agentradis/logs/radis.log"),
)

# Export commonly used functions and logger instance
__all__ = [
    "logger",  # Default logger instance
    "setup_logger",
    "set_log_level",
    "get_log_level",
    "get_logger",
    "enable_debug_logging",
    "disable_debug_logging",
    "log_security_event",
    "log_error_with_trace",
    "track_tool_execution",
    "SecurityContext",
]
