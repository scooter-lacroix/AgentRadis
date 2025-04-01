"""
Adaptive timeout functionality for tool execution.
This enhances the tool execution in the agent's _execute_single_tool_call method.
"""
import time
import asyncio
from typing import Dict, Any, Optional

def get_adaptive_timeout(self, tool, args: Dict[str, Any]) -> float:
    """
    Determine an appropriate timeout for a tool based on complexity and history.
    
    Args:
        tool: The tool to execute
        args: The arguments being passed to the tool
        
    Returns:
        Timeout value in seconds
    """
    # Start with a default timeout
    base_timeout = getattr(tool, "timeout", 30)  # Default 30 seconds if not specified
    
    # Check tool stats for history-based adjustment
    if hasattr(tool, "get_stats"):
        stats = tool.get_stats()
        avg_time = stats.get("avg_execution_time", 0)
        
        if avg_time > 0:
            # Use history to inform the timeout, but with a safety margin
            history_based_timeout = avg_time * 2.0  # 2x average as a buffer
            
            # Don't go below half the default or above 1.5x the default
            base_timeout = max(base_timeout / 2, min(base_timeout * 1.5, history_based_timeout))
    
    # Adjust based on complexity heuristics
    complexity_factor = 1.0
    
    # Size-based adjustments - more data means more time needed
    if "size" in args and isinstance(args["size"], int):
        if args["size"] > 1000:
            complexity_factor += min(1.0, args["size"] / 5000)  # Max +100% for large sizes
    
    # Depth/recursion adjustments
    if "depth" in args and isinstance(args["depth"], int):
        if args["depth"] > 3:
            complexity_factor += 0.2 * min(5, args["depth"] - 3)  # +20% per depth level beyond 3
    
    # Content length adjustments
    for arg_name, arg_value in args.items():
        if isinstance(arg_value, str) and len(arg_value) > 5000:
            complexity_factor += min(0.5, len(arg_value) / 20000)  # Max +50% for very long strings
    
    # Apply complexity factor
    timeout = base_timeout * complexity_factor
    
    # Ensure we have reasonable bounds
    MIN_TIMEOUT = 5    # Don't go below 5 seconds
    MAX_TIMEOUT = 180  # Don't go above 3 minutes
    timeout = max(MIN_TIMEOUT, min(MAX_TIMEOUT, timeout))
    
    # Round to a clean number for logging
    timeout = round(timeout, 1)
    
    return timeout

async def execute_with_adaptive_timeout(self, tool, args: Dict[str, Any]) -> Any:
    """
    Execute a tool with adaptive timeout based on complexity and history.
    
    Args:
        tool: The tool to execute
        args: Tool arguments
        
    Returns:
        The result of tool execution
        
    Raises:
        asyncio.TimeoutError: If execution times out
        Exception: Any exceptions from the tool execution
    """
    # Get appropriate timeout for this tool and arguments
    timeout = self.get_adaptive_timeout(tool, args)
    
    # Start execution timer
    start_time = time.time()
    
    try:
        # Execute with timeout
        result = await asyncio.wait_for(
            tool.run(**args),
            timeout=timeout
        )
        
        # Record execution time for future timeout calculations
        execution_time = time.time() - start_time
        
        # Update tool statistics if available
        if hasattr(tool, "_update_stats"):
            tool._update_stats(execution_time=execution_time)
            
        return result
        
    except asyncio.TimeoutError:
        # Record the timeout in stats if available
        if hasattr(tool, "_update_stats"):
            tool._update_stats(timeout=True)
            
        # Try to recover from timeout if possible
        recovery_result = await self._try_timeout_recovery(tool, args, timeout)
        if recovery_result is not None:
            return recovery_result
            
        # Re-raise if no recovery
        raise
        
    except Exception as e:
        # Record the error in stats if available
        if hasattr(tool, "_update_stats"):
            tool._update_stats(error=True)
            
        # Try to recover from error if possible
        recovery_result = await self._try_error_recovery(tool, args, e)
        if recovery_result is not None:
            return recovery_result
            
        # Re-raise if no recovery
        raise

async def _try_timeout_recovery(self, tool, args: Dict[str, Any], original_timeout: float) -> Optional[Any]:
    """
    Try to recover from a tool timeout.
    
    Args:
        tool: The tool that timed out
        args: Original arguments
        original_timeout: The timeout that was exceeded
        
    Returns:
        Recovery result or None if recovery failed
    """
    # Strategy 1: If the tool has a custom recovery method, use it
    if hasattr(tool, "recover_from_timeout") and asyncio.iscoroutinefunction(tool.recover_from_timeout):
        try:
            return await tool.recover_from_timeout(args)
        except Exception:
            pass  # Continue to other strategies if custom recovery fails
    
    # Strategy 2: Try with simplified arguments
    simplified_args = self._simplify_args(args)
    if simplified_args != args:
        try:
            # Use a shorter timeout for the recovery attempt
            return await asyncio.wait_for(
                tool.run(**simplified_args),
                timeout=original_timeout * 0.75  # 75% of original timeout
            )
        except Exception:
            pass  # Continue to other strategies
    
    # No recovery was possible
    return None

def _simplify_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attempt to simplify tool arguments to make execution more likely to succeed.
    
    Args:
        args: Original arguments
        
    Returns:
        Simplified arguments
    """
    simplified = args.copy()
    
    # Strategy 1: Reduce sizes/limits
    for key in simplified:
        # Reduce list lengths
        if isinstance(simplified[key], list) and len(simplified[key]) > 5:
            simplified[key] = simplified[key][:5]
            
        # Reduce page sizes
        if key in ["limit", "max_results", "size", "count"] and isinstance(simplified[key], int):
            simplified[key] = min(simplified[key], 5)
            
        # Truncate long strings
        if isinstance(simplified[key], str) and len(simplified[key]) > 1000:
            simplified[key] = simplified[key][:1000]
            
    return simplified

async def _try_error_recovery(self, tool, args: Dict[str, Any], error: Exception) -> Optional[Any]:
    """
    Try to recover from a tool error.
    
    Args:
        tool: The tool that had an error
        args: Original arguments
        error: The exception that occurred
        
    Returns:
        Recovery result or None if recovery failed
    """
    # Strategy 1: If the tool has a custom recovery method, use it
    if hasattr(tool, "recover_from_error") and asyncio.iscoroutinefunction(tool.recover_from_error):
        try:
            return await tool.recover_from_error(args, error)
        except Exception:
            pass  # Continue to other strategies if custom recovery fails
    
    # Strategy 2: For certain errors, try again with adjusted parameters
    error_str = str(error).lower()
    
    # For network/timeout errors, try again with longer timeout
    if ("connection" in error_str or "timeout" in error_str or 
        isinstance(error, (ConnectionError, TimeoutError))):
        try:
            return await asyncio.wait_for(
                tool.run(**args),
                timeout=60  # Fixed longer timeout for retry
            )
        except Exception:
            pass
    
    # For parameter errors, try to fix common issues
    if "parameter" in error_str or "argument" in error_str or "invalid" in error_str:
        fixed_args = self._fix_common_arg_errors(args, error_str)
        if fixed_args != args:
            try:
                return await tool.run(**fixed_args)
            except Exception:
                pass
    
    # No recovery was possible
    return None

def _fix_common_arg_errors(self, args: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
    """Fix common argument errors based on error message."""
    fixed_args = args.copy()
    
    # Type conversion errors
    if "int" in error_msg and "str" in error_msg:
        # Try to convert string to int where appropriate
        for key, value in fixed_args.items():
            if isinstance(value, str) and value.isdigit():
                fixed_args[key] = int(value)
    
    # Required fields
    if "required" in error_msg:
        import re
        missing_field = re.search(r"'([^']+)' is a required property", error_msg)
        if missing_field:
            field = missing_field.group(1)
            fixed_args[field] = ""  # Add empty string as default
    
    return fixed_args
