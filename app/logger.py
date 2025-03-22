"""
Centralized logging module for Agent Radis.

This module provides consistent logging functionality throughout the application.
"""
import logging
import os
import sys
import traceback
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, Union, List, Type
from pathlib import Path

# Ensure log directory exists
log_dir = os.path.expanduser("~/.agentradis/logs")
os.makedirs(log_dir, exist_ok=True)

# Configure logging
logger = logging.getLogger("radis")
logger.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
console_handler.setFormatter(console_format)

# Create file handler
file_handler = logging.FileHandler(
    os.path.join(log_dir, "radis.log"),
    mode="a"
)
file_handler.setLevel(logging.DEBUG)
file_format = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(file_format)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Prevent propagation to root logger
logger.propagate = False

# Custom log levels
VERBOSE = 15
logging.addLevelName(VERBOSE, "VERBOSE")


def verbose(self, message, *args, **kwargs):
    """Log 'msg % args' with severity 'VERBOSE'."""
    if self.isEnabledFor(VERBOSE):
        self._log(VERBOSE, message, args, **kwargs)


# Add verbose method to the Logger class
logging.Logger.verbose = verbose


class ToolLogger:
    """Logger for tool executions with context tracking"""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.logger = logging.getLogger(f"agentradis.tool.{tool_name}")
        self.execution_id = None
        self.execution_start = None

    def start_execution(self, **kwargs) -> str:
        """Start tracking a tool execution"""
        self.execution_id = datetime.now().strftime("%Y%m%d%H%M%S") + f"-{self.tool_name}"
        self.execution_start = datetime.now()
        args_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.info(f"Starting tool execution [{self.execution_id}]: {args_str}")
        return self.execution_id

    def end_execution(self, success: bool, message: Optional[str] = None) -> None:
        """End tracking a tool execution"""
        if not self.execution_id:
            return

        duration = datetime.now() - self.execution_start if self.execution_start else None
        duration_str = f" (duration: {duration.total_seconds():.2f}s)" if duration else ""
        status = "SUCCESS" if success else "FAILURE"

        if message:
            self.logger.info(f"Tool execution [{self.execution_id}] ended: {status}{duration_str} - {message}")
        else:
            self.logger.info(f"Tool execution [{self.execution_id}] ended: {status}{duration_str}")

        self.execution_id = None
        self.execution_start = None

    def info(self, message: str) -> None:
        """Log an info message, including execution context if available"""
        if self.execution_id:
            self.logger.info(f"[{self.execution_id}] {message}")
        else:
            self.logger.info(message)

    def error(self, message: str, exc_info: Union[bool, Exception] = False) -> None:
        """Log an error message, including execution context if available"""
        if self.execution_id:
            self.logger.error(f"[{self.execution_id}] {message}", exc_info=exc_info)
        else:
            self.logger.error(message, exc_info=exc_info)

    def warning(self, message: str) -> None:
        """Log a warning message, including execution context if available"""
        if self.execution_id:
            self.logger.warning(f"[{self.execution_id}] {message}")
        else:
            self.logger.warning(message)

    def debug(self, message: str) -> None:
        """Log a debug message, including execution context if available"""
        if self.execution_id:
            self.logger.debug(f"[{self.execution_id}] {message}")
        else:
            self.logger.debug(message)

    def verbose(self, message: str) -> None:
        """Log a verbose message, including execution context if available"""
        if self.execution_id:
            self.logger.verbose(f"[{self.execution_id}] {message}")
        else:
            self.logger.verbose(message)


class AgentLogger:
    """Logger for agent executions with state tracking"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"agentradis.agent.{agent_name}")
        self.session_id = None
        self.step_count = 0
        self.states = []

    def start_session(self) -> str:
        """Start a new agent session"""
        self.session_id = datetime.now().strftime("%Y%m%d%H%M%S") + f"-{self.agent_name}"
        self.step_count = 0
        self.states = []
        self.logger.info(f"Starting agent session [{self.session_id}]")
        return self.session_id

    def end_session(self, status: str, reason: Optional[str] = None) -> None:
        """End the current agent session"""
        if not self.session_id:
            return

        message = f"Ending agent session [{self.session_id}]: {status}"
        if reason:
            message += f" - {reason}"
        self.logger.info(message)
        self.logger.info(f"Session [{self.session_id}] completed {self.step_count} steps")
        self.session_id = None

    def log_step(self, action: str, state: Dict[str, Any]) -> None:
        """Log an agent step"""
        if not self.session_id:
            return

        self.step_count += 1
        self.states.append(state)
        self.logger.info(f"Step {self.step_count} [{self.session_id}]: {action}")

    def log_tool_use(self, tool_name: str, args: Dict[str, Any], result: Any) -> None:
        """Log tool usage within the agent"""
        if not self.session_id:
            return

        args_str = ", ".join(f"{k}={v}" for k, v in args.items())
        result_summary = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
        self.logger.info(f"Tool use [{self.session_id}]: {tool_name}({args_str}) -> {result_summary}")

    def log_error(self, error: Union[str, Exception], context: Optional[Dict[str, Any]] = None) -> None:
        """Log an error with context"""
        if isinstance(error, Exception):
            error_str = f"{type(error).__name__}: {str(error)}"
            tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        else:
            error_str = error
            tb = None

        if self.session_id:
            self.logger.error(f"Error in session [{self.session_id}]: {error_str}")
        else:
            self.logger.error(f"Error: {error_str}")

        if tb:
            self.logger.debug(f"Traceback: {tb}")

        if context:
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            self.logger.debug(f"Error context: {context_str}")

    def info(self, message: str) -> None:
        """Log an info message with session context"""
        if self.session_id:
            self.logger.info(f"[{self.session_id}] {message}")
        else:
            self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log a warning message with session context"""
        if self.session_id:
            self.logger.warning(f"[{self.session_id}] {message}")
        else:
            self.logger.warning(message)

    def debug(self, message: str) -> None:
        """Log a debug message with session context"""
        if self.session_id:
            self.logger.debug(f"[{self.session_id}] {message}")
        else:
            self.logger.debug(message)


def log_execution_time(func: Callable) -> Callable:
    """Decorator to log execution time of a function"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        module_name = func.__module__
        logger.debug(f"Starting execution of {module_name}.{func_name}")
        start_time = datetime.now()
        try:
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Completed {module_name}.{func_name} in {execution_time:.4f}s")
            return result
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Failed {module_name}.{func_name} after {execution_time:.4f}s: {str(e)}")
            raise
    return wrapper


def configure_logging(
    level: int = logging.INFO,
    filename: Optional[str] = None,
    console: bool = True,
    format_str: Optional[str] = None,
) -> None:
    """Configure global logging settings"""
    global logger

    # Reset handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Set log level
    logger.setLevel(level)
    
    # Default format string
    if not format_str:
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(format_str)
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add file handler if filename is provided
    if filename:
        try:
            # Ensure the directory exists
            log_dir = os.path.dirname(filename)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            file_handler = logging.FileHandler(filename)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            sys.stderr.write(f"Error setting up file logging: {str(e)}\n")


def get_tool_logger(tool_name: str) -> ToolLogger:
    """Get a tool-specific logger"""
    return ToolLogger(tool_name)


def get_agent_logger(agent_name: str) -> AgentLogger:
    """Get an agent-specific logger"""
    return AgentLogger(agent_name)


# Handle any initialization from environment variables or configuration
log_level_name = os.environ.get("AGENTRADIS_LOG_LEVEL", "INFO")
log_level = getattr(logging, log_level_name, logging.INFO)
log_file = os.environ.get("AGENTRADIS_LOG_FILE")

if log_file or log_level != logging.INFO:
    configure_logging(level=log_level, filename=log_file)

def set_log_level(level: Optional[str] = None):
    """Set the logging level."""
    if level is None:
        return
    
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    logger.setLevel(numeric_level)
    for handler in logger.handlers:
        handler.setLevel(numeric_level)

# Custom debug function that logs with extra context
def debug_with_context(message, context=None):
    """Log a debug message with optional context dictionary"""
    if context:
        logger.debug(f"{message} | Context: {context}")
    else:
        logger.debug(message)
