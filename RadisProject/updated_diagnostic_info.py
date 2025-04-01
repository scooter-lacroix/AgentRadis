"""
Enhanced DiagnosticInfo class implementation for app/agent/radis.py
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any
import time

class SeverityLevel(Enum):
    """Defines severity levels for diagnostics."""
    INFO = auto()
    WARNING = auto()
    ERROR = auto() 
    CRITICAL = auto()
    
    def __str__(self) -> str:
        return self.name

class ErrorCode(Enum):
    """Standard error codes for the Radis system."""
    # General errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    CONFIGURATION_ERROR = "CONFIG_ERROR"
    
    # Runtime errors
    EXECUTION_ERROR = "EXEC_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    MEMORY_ERROR = "MEMORY_ERROR"
    
    # Tool-related errors
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_EXECUTION_ERROR = "TOOL_EXEC_ERROR"
    TOOL_PARAMETER_ERROR = "TOOL_PARAM_ERROR"
    
    # LLM-related errors
    LLM_API_ERROR = "LLM_API_ERROR"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT" 
    LLM_CONTEXT_OVERFLOW = "LLM_CTX_OVERFLOW"
    
    # State-related errors
    INVALID_STATE_TRANSITION = "INVALID_STATE"
    
    def __str__(self) -> str:
        return self.value

@dataclass
class DiagnosticInfo:
    """Tracks runtime diagnostic information for the agent with enhanced error reporting."""

    errors: List[Dict[str, Any]] = field(default_factory=list)
    last_llm_request: Optional[Dict[str, Any]] = None
    last_tool_execution: Optional[Dict[str, Any]] = None
    runtime_states: List[Dict[str, Any]] = field(default_factory=list)

    def add_error(
        self, 
        error_type: str, 
        error_msg: str, 
        severity: SeverityLevel = SeverityLevel.ERROR,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Add an error entry with timestamp, severity level, and error code.
        
        Args:
            error_type: Type of error (e.g., "llm_error", "tool_error")
            error_msg: Descriptive error message
            severity: Severity level from SeverityLevel enum
            error_code: Standardized error code from ErrorCode enum
            context: Additional contextual information
        """
        self.errors.append(
            {
                "type": error_type,
                "message": error_msg,
                "severity": str(severity),
                "code": str(error_code),
                "context": context or {},
                "timestamp": time.time()
            }
        )
        
    def add_state(self, state: str, context: Optional[Dict[str, Any]] = None):
        """Track runtime state changes."""
        self.runtime_states.append(
            {"state": state, "context": context or {}, "timestamp": time.time()}
        )
        
    def get_errors_by_severity(self, severity: Optional[SeverityLevel] = None) -> List[Dict[str, Any]]:
        """
        Get errors filtered by severity level.
        
        Args:
            severity: Optional severity level to filter by
            
        Returns:
            List of error entries matching the specified severity or all errors if None
        """
        if severity is None:
            return self.errors
            
        return [error for error in self.errors if error.get("severity") == str(severity)]
        
    def get_errors_by_code(self, error_code: ErrorCode) -> List[Dict[str, Any]]:
        """
        Get errors filtered by error code.
        
        Args:
            error_code: Error code to filter by
            
        Returns:
            List of error entries matching the specified error code
        """
        return [error for error in self.errors if error.get("code") == str(error_code)]
