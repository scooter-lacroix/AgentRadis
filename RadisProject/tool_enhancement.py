"""
Enhanced BaseTool class with result caching and timeout functionality.
This extends the existing implementation in app/tool/base.py.
"""
import json
import time
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, Callable, Awaitable
from functools import wraps

import jsonschema


class ToolCache:
    """Simple in-memory cache for tool results with TTL support."""
    
    def __init__(self):
        self._cache: Dict[str, Tuple[Any, float]] = {}  # {cache_key: (result, expiry_time)}
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache if it exists and hasn't expired.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value or None if not found or expired
        """
        if key not in self._cache:
            return None
            
        result, expiry_time = self._cache[key]
        
        # Check if the cached item has expired
        if time.time() > expiry_time:
            # Expired, remove it
            del self._cache[key]
            return None
            
        return result
        
    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """
        Store a value in the cache with an expiry time.
        
        Args:
            key: The cache key
            value: The value to store
            ttl_seconds: Time-to-live in seconds
        """
        expiry_time = time.time() + ttl_seconds
        self._cache[key] = (value, expiry_time)
        
    def invalidate(self, key: str) -> None:
        """
        Remove a specific item from the cache.
        
        Args:
            key: The cache key to remove
        """
        if key in self._cache:
            del self._cache[key]
            
    def clear(self) -> None:
        """Clear all items from the cache."""
        self._cache.clear()
        
    def clean_expired(self) -> int:
        """
        Remove all expired items from the cache.
        
        Returns:
            The number of items removed
        """
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._cache.items() if now > exp]
        
        for key in expired_keys:
            del self._cache[key]
            
        return len(expired_keys)


class BaseTool(ABC):
    """Abstract base class for all tools in the Radis system with caching and timeout support.

    All tools must inherit from this class and implement the required methods.

    Attributes:
        name (str): The name of the tool, used for identification
        description (str): A human-readable description of what the tool does
        parameters (dict): JSON schema describing the tool's parameters
        
    Class attributes:
        DEFAULT_TIMEOUT (int): Default execution timeout in seconds
        DEFAULT_CACHE_TTL (int): Default time-to-live for cached results in seconds
        global_cache (ToolCache): Shared cache across all tool instances
    """
    # Class-level constants and shared cache
    DEFAULT_TIMEOUT = 30  # 30 seconds default timeout
    DEFAULT_CACHE_TTL = 300  # 5 minutes default cache TTL
    global_cache = ToolCache()
    
    def __init__(self, timeout: Optional[int] = None, cache_ttl: Optional[int] = None, 
                enable_caching: bool = True):
        """
        Initialize the tool with timeout and caching settings.
        
        Args:
            timeout: Custom timeout in seconds for this tool instance
            cache_ttl: Custom cache TTL in seconds for this tool instance
            enable_caching: Whether to enable result caching for this instance
        """
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._cache_ttl = cache_ttl or self.DEFAULT_CACHE_TTL
        self._enable_caching = enable_caching
        self._instance_cache = ToolCache()  # For instance-specific caching
        
        # Statistics for monitoring
        self._stats = {
            "calls": 0,
            "cache_hits": 0,
            "timeouts": 0,
            "errors": 0,
            "total_execution_time": 0,
            "last_execution_time": 0,
        }

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A human-readable description of what the tool does."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON schema describing the tool's parameters."""
        pass
        
    @property
    def timeout(self) -> int:
        """Get the current timeout setting for this tool."""
        return self._timeout
        
    @timeout.setter
    def timeout(self, value: int) -> None:
        """Set a new timeout value for this tool."""
        if value <= 0:
            raise ValueError("Timeout must be a positive integer")
        self._timeout = value

    @abstractmethod
    async def _execute(self, **kwargs) -> Any:
        """
        Execute the tool's main functionality. To be implemented by subclasses.
        
        This is the actual implementation that will be called by the run method.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            The result of tool execution
        """
        pass
        
    def _generate_cache_key(self, **kwargs) -> str:
        """
        Generate a unique cache key based on the tool name and parameters.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            A string cache key
        """
        # Sort kwargs to ensure consistent key generation
        sorted_kwargs = {k: kwargs[k] for k in sorted(kwargs.keys())}
        
        # Create a unique key from tool name and serialized parameters
        key_parts = [self.name, json.dumps(sorted_kwargs, sort_keys=True)]
        return ":".join(key_parts)

    async def run(self, **kwargs) -> Any:
        """
        Execute the tool with timeout and caching support.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            The result of tool execution
            
        Raises:
            asyncio.TimeoutError: If execution exceeds the timeout
            Exception: Any exceptions from the tool's _execute method
        """
        start_time = time.time()
        self._stats["calls"] += 1
        
        try:
            # Check cache if caching is enabled
            if self._enable_caching:
                cache_key = self._generate_cache_key(**kwargs)
                
                # Try instance cache first
                cached_result = self._instance_cache.get(cache_key)
                if cached_result is not None:
                    self._stats["cache_hits"] += 1
                    return cached_result
                    
                # Try global cache next
                cached_result = self.global_cache.get(cache_key)
                if cached_result is not None:
                    self._stats["cache_hits"] += 1
                    return cached_result
            
            # Execute with timeout
            try:
                result = await asyncio.wait_for(self._execute(**kwargs), timeout=self._timeout)
            except asyncio.TimeoutError:
                self._stats["timeouts"] += 1
                raise
                
            # Cache the result if caching is enabled
            if self._enable_caching:
                cache_key = self._generate_cache_key(**kwargs)
                self._instance_cache.set(cache_key, result, self._cache_ttl)
                self.global_cache.set(cache_key, result, self._cache_ttl)
                
            return result
            
        except Exception as e:
            self._stats["errors"] += 1
            raise
        finally:
            execution_time = time.time() - start_time
            self._stats["total_execution_time"] += execution_time
            self._stats["last_execution_time"] = execution_time

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up any resources used by the tool."""
        pass

    @abstractmethod
    async def reset(self) -> None:
        """Reset the tool to its initial state."""
        # Clear instance cache on reset
        self._instance_cache.clear()
        pass
        
    def clear_cache(self, global_cache: bool = False) -> None:
        """
        Clear the tool's cache.
        
        Args:
            global_cache: Whether to clear the global cache for all tools
        """
        self._instance_cache.clear()
        
        if global_cache:
            self.global_cache.clear()
            
    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters against the tool's schema.
        
        Args:
            params: Parameters to validate
            
        Returns:
            The validated parameters
            
        Raises:
            ValueError: If parameters do not match the schema
        """
        try:
            jsonschema.validate(instance=params, schema=self.parameters)
            return params
        except jsonschema.exceptions.ValidationError as e:
            raise ValueError(f"Parameter validation error: {str(e)}")
            
    def get_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics for this tool.
        
        Returns:
            Dictionary of statistics
        """
        # Add derived stats
        stats = self._stats.copy()
        
        # Calculate average execution time if there were any calls
        if stats["calls"] > 0:
            stats["avg_execution_time"] = stats["total_execution_time"] / stats["calls"]
        else:
            stats["avg_execution_time"] = 0
            
        # Calculate cache hit rate
        if stats["calls"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["calls"]
        else:
            stats["cache_hit_rate"] = 0
            
        # Add configuration info
        stats["timeout"] = self._timeout
        stats["cache_ttl"] = self._cache_ttl
        stats["caching_enabled"] = self._enable_caching
        
        return stats
        
    def reset_stats(self) -> None:
        """Reset the tool's execution statistics."""
        self._stats = {
            "calls": 0,
            "cache_hits": 0,
            "timeouts": 0,
            "errors": 0,
            "total_execution_time": 0,
            "last_execution_time": 0,
        }
