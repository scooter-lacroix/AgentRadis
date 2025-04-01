import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional, Union, List

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

Debug logging can be controlled using enable_debug_logging() and disable_debug_logging()
functions. When debug logging is enabled, detailed diagnostic information will be logged
through both console and file handlers.
"""

# Custom formatter with consistent output format
class RadisFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

def setup_root_logger() -> logging.Logger:
    """
    Configure the root logger with both console and file handlers.
    
    This function:
    - Gets the root logger
    - Sets default level to INFO
    - Configures RotatingFileHandler (10MB max size, 5 backups)
    - Configures StreamHandler
    - Prevents duplicate handlers
    - Uses RadisFormatter for consistent formatting
    
    Returns:
        Configured root logger instance
    """
def track_tool_execution(logger: logging.Logger):
    """Decorator to track tool execution time and status.
    
    Args:
        logger: Logger instance to use for tracking

    Returns:
        Decorator function that wraps tool execution

    Note:
        - Logs both successful and failed executions
        - Includes execution time and status
        - Preserves original function's return value and exceptions
        - Adds consistent error context for debugging
    """
    
    # Clear existing handlers to prevent duplicates
    root_logger.handlers.clear()
    
    formatter = RadisFormatter()
    
    # Configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure file handler
    log_dir = os.path.expanduser('~/.agentradis/logs')
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'root.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    return root_logger

def setup_logger(
    name: str,
    level: Union[int, str] = logging.INFO,
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    name: str,
    level: Union[int, str] = logging.INFO,
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """Configure and return a logger instance with both console and optional file handlers.
    
    Args:
        name: Logger name
        level: Logging level (default: INFO)
        log_file: Optional file path for log output
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
    
    Returns:
        logging.Logger: Configured logger instance
    
    Raises:
        ValueError: If invalid log level provided
        OSError: If unable to create log directory or files
        PermissionError: If lacking write permissions
    """
    # Validate log level
    if isinstance(level, str):
        try:
            level = getattr(logging, level.upper())
        except AttributeError:
            raise ValueError(f"Invalid log level: {level}")
        backup_count: Number of backup files to keep
    """
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
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def set_log_level(logger: Union[str, logging.Logger], level: Union[int, str]) -> None:
    """
    Set the log level for a specific logger.
    
    Args:
        logger: Logger name or instance
        level: New logging level
    """
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    logger.setLevel(level)

def get_log_level(logger: Union[str, logging.Logger]) -> int:
    """
def enable_debug_logging() -> None:
    """Enable debug logging for all loggers.
    
    Note:
        - Sets root logger and all handlers to DEBUG level
        - Affects both console and file output
        - Resource intensive - use judiciously
        - Console output may become verbose
    """
    Args:
        logger: Logger name or instance
    
    Returns:
        Current logging level
    """
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    return logger.level

def get_logger(name: str, level: Union[int, str] = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance for the given name.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Optional path to log file
        
    Returns:
        Configured logger instance
    """
    return setup_logger(name, level, log_file)

def enable_debug_logging() -> None:
    """
    Enable debug logging for the default Radis logger.
    
    This function:
    - Sets the log level to DEBUG for both console and file handlers
    - Ensures all debug messages are captured and logged
    - Affects both console output and log file
    
    Note: Debug logging provides detailed diagnostic information and may impact
    performance if left enabled in production environments.
    """
    logger = logging.getLogger('radis')
    logger.setLevel(LogLevel.DEBUG.value)
    
    # Update all handlers to DEBUG level
    for handler in logger.handlers:
        handler.setLevel(LogLevel.DEBUG.value)

def disable_debug_logging() -> None:
    """
    Disable debug logging for the default Radis logger.
    
    This function:
    - Sets the log level back to INFO for both console and file handlers
    - Reduces log verbosity to normal operational levels
    - Affects both console output and log file
    
    This is the recommended setting for production environments.
    """
    logger = logging.getLogger('radis')
    logger.setLevel(LogLevel.INFO.value)
    
    # Update all handlers to INFO level
    for handler in logger.handlers:
        handler.setLevel(LogLevel.INFO.value)

# Initialize root logger at module load
root_logger = setup_root_logger()

# Default Radis logger
logger = setup_logger(
    'radis',
    level=logging.INFO,
    log_file=os.path.expanduser('~/.agentradis/logs/radis.log')
)

# Export commonly used functions for convenient imports
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical

# Define what gets imported with "from app.logger import *"
__all__ = [
    "logger", "setup_logger", "set_log_level", "get_log_level", "get_logger",
    "debug", "info", "warning", "error", "critical",
    "enable_debug_logging", "disable_debug_logging"
]

