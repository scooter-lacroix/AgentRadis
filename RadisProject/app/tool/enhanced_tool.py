#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import asyncio
import inspect
from functools import wraps
from typing import Any, Dict, Optional, List, Union, Callable, Awaitable

from app.tool.base import BaseTool
from app.utils.caching import ToolCache, get_global_cache, CacheStats

class CacheableTool(BaseTool):
    """
    Enhanced BaseTool that supports result caching with TTL.
    
    This class extends BaseTool with caching capabilities and execution statistics.
    """
    
    def __init__(self, cache_ttl: Optional[int] = None, use_global_cache: bool = False):
        """
        Initialize a CacheableTool with optional caching configuration.
        
        Args:
            cache_ttl: Default Time-To-Live for cached results in seconds (None=disabled)
            use_global_cache: Whether to use the global cache instance instead of a tool-specific one
        """
        self._use_caching = cache_ttl is not None
        self._default_cache_ttl = cache_ttl
        
        # Initialize cache - either use global cache or create tool-specific cache
        if use_global_cache:
            self._cache = get_global_cache()
        else:
            self._cache = ToolCache(default_ttl=cache_ttl or 300)
            
        # Track execution statistics
        self._execution_stats: Dict[str, Any] = {
            "total_calls": 0,
            "cached_hits": 0,
            "total_execution_time": 0,
            "last_execution_time": 0,
            "avg_execution_time": 0,
            "error_count": 0,
            "last_error": None,
            "last_execution": None
        }
    
    def enable_caching(self, ttl: Optional[int] = None) -> None:
        """
        Enable caching for this tool.
        
        Args:
            ttl: Time-To-Live for cached results (uses default if None)
        """
        self._use_caching = True
        if ttl is not None:
            self._default_cache_ttl = ttl
            
    def disable_caching(self) -> None:
        """Disable caching for this tool."""
        self._use_caching = False
        
    def clear_cache(self) -> None:
        """Clear all cached results for this tool."""
        if hasattr(self, "_cache"):
            self._cache.invalidate(self.name)
            
    def get_cache_stats(self) -> CacheStats:
        """Get statistics about the cache performance."""
        if hasattr(self, "_cache"):
            return self._cache.get_stats()
        return CacheStats()
        
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get statistics about tool execution."""
        return dict(self._execution_stats)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics about tool execution and caching."""
        cache_stats = {}
        if hasattr(self, "_cache"):
            stats = self._cache.get_stats()
            cache_stats = {
                "hits": stats.hits,
                "misses": stats.misses,
                "hit_rate": stats.hit_rate,
                "entries": stats.entries
            }
            
        return {
            "execution": self.get_execution_stats(),
            "cache": cache_stats,
            "caching_enabled": self._use_caching
        }
        
    def _update_execution_stats(self, execution_time: float, error: Optional[Exception] = None) -> None:
        """
        Update execution statistics after a tool run.
        
        Args:
            execution_time: Time taken for execution in seconds
            error: Exception object if an error occurred
        """
        self._execution_stats["total_calls"] += 1
        self._execution_stats["last_execution_time"] = execution_time
        self._execution_stats["total_execution_time"] += execution_time
        self._execution_stats["avg_execution_time"] = (
            self._execution_stats["total_execution_time"] / 
            self._execution_stats["total_calls"]
        )
        self._execution_stats["last_execution"] = time.time()
        
        if error:
            self._execution_stats["error_count"] += 1
            self._execution_stats["last_error"] = str(error)
        
    def cached_run(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with caching if enabled.
        
        Args:
            func: The function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            The function result, either from cache or fresh execution
        """
        start_time = time.time()
        
        try:
            # Check if caching is enabled
            if self._use_caching:
                # Generate params dict
                params = {**dict(zip(inspect.signature(func).parameters.keys(), args)), **kwargs}
                
                # Try to get from cache
                hit, cached_result = self._cache.get(func.__name__, params)
                if hit:
                    self._execution_stats["cached_hits"] += 1
                    return cached_result
                
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache if enabled
            if self._use_caching:
                self._cache.set(func.__name__, params, result, self._default_cache_ttl)
                
            # Update statistics
            execution_time = time.time() - start_time
            self._update_execution_stats(execution_time)
            
            return result
            
        except Exception as e:
            # Update statistics with error
            execution_time = time.time() - start_time
            self._update_execution_stats(execution_time, error=e)
            raise
            
    async def cached_run_async(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """
        Execute an async function with caching if enabled.
        
        Args:
            func: The async function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            The function result, either from cache or fresh execution
        """
        start_time = time.time()
        
        try:
            # Check if caching is enabled
            if self._use_caching:
                # Generate params dict
                params = {**dict(zip(inspect.signature(func).parameters.keys(), args)), **kwargs}
                
                # Try to get from cache
                hit, cached_result = self._cache.get(func.__name__, params)
                if hit:
                    self._execution_stats["cached_hits"] += 1
                    return cached_result
                
            # Execute async function
            result = await func(*args, **kwargs)
            
            # Store in cache if enabled
            if self._use_caching:
                self._cache.set(func.__name__, params, result, self._default_cache_ttl)
                
            # Update statistics
            execution_time = time.time() - start_time
            self._update_execution_stats(execution_time)
            
            return result
            
        except Exception as e:
            # Update statistics with error
            execution_time = time.time() - start_time
            self._update_execution_stats(execution_time, error=e)
            raise


def cacheable(ttl: Optional[int] = None):
    """
    Decorator to make a tool method cacheable.
    
    This decorator works for both regular and async methods in CacheableTool.
    
    Args:
        ttl: Optional specific TTL for this method (overrides tool default)
        
    Returns:
        Decorated method with caching capability
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Only apply caching for CacheableTool instances
            if not isinstance(self, CacheableTool):
                return func(self, *args, **kwargs)
                
            # Override TTL if specified
            old_ttl = None
            if ttl is not None and hasattr(self, "_default_cache_ttl"):
                old_ttl = self._default_cache_ttl
                self._default_cache_ttl = ttl
                
            try:
                if asyncio.iscoroutinefunction(func):
                    return self.cached_run_async(func, self, *args, **kwargs)
                else:
                    return self.cached_run(func, self, *args, **kwargs)
            finally:
                # Restore original TTL if needed
                if old_ttl is not None:
                    self._default_cache_ttl = old_ttl
                    
        return wrapper
    return decorator


# Example usage:
"""
class WeatherTool(CacheableTool):
    @property
    def name(self) -> str:
        return "weather_tool"
        
    @property
    def description(self) -> str:
        return "Get weather information for a location"
        
    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "units": {"type": "string", "enum": ["metric", "imperial"]}
            },
            "required": ["location"]
        }
        
    @cacheable(ttl=300)  # Cache weather results for 5 minutes
    async def run(self, location: str, units: str = "metric") -> Dict[str, Any]:
        # This would normally call a weather API
        # Results will be automatically cached
        ...
"""
