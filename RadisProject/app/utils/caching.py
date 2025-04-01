#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import hashlib
import json
from typing import Dict, Any, Optional, Tuple, Callable, List
import threading
from dataclasses import dataclass, field

@dataclass
class CacheStats:
    """Statistics for cache performance."""
    hits: int = 0
    misses: int = 0
    entries: int = 0
    evictions: int = 0
    
    @property
    def total_requests(self) -> int:
        """Total number of cache requests."""
        return self.hits + self.misses
        
    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100


class ToolCache:
    """
    Implements a time-to-live (TTL) cache for tool execution results.
    
    Features:
    - Caching based on tool name and parameters
    - Configurable TTL for each cache entry
    - Statistics tracking
    - Thread-safe operations
    """
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize the cache.
        
        Args:
            default_ttl: Default time-to-live for cache entries in seconds
        """
        self._cache: Dict[str, Tuple[Any, float]] = {}  # {key: (value, expiry_time)}
        self._default_ttl = default_ttl
        self._stats = CacheStats()
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        
    def _generate_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        """
        Generate a cache key based on tool name and parameters.
        
        Args:
            tool_name: Name of the tool
            params: Dictionary of tool parameters
            
        Returns:
            A string key for cache lookup
        """
        # Sort params to ensure consistent key generation regardless of dict order
        serialized_params = json.dumps(params, sort_keys=True)
        key_data = f"{tool_name}:{serialized_params}"
        return hashlib.md5(key_data.encode()).hexdigest()
        
    def get(self, tool_name: str, params: Dict[str, Any]) -> Tuple[bool, Any]:
        """
        Get a value from the cache if it exists and is not expired.
        
        Args:
            tool_name: Name of the tool
            params: Dictionary of tool parameters
            
        Returns:
            A tuple of (hit, value) where hit is a boolean indicating cache hit/miss
        """
        key = self._generate_key(tool_name, params)
        
        with self._lock:
            if key in self._cache:
                value, expiry_time = self._cache[key]
                
                # Check if entry is expired
                if time.time() < expiry_time:
                    self._stats.hits += 1
                    return True, value
                else:
                    # Entry expired, remove it
                    self._cache.pop(key)
                    self._stats.evictions += 1
            
            self._stats.misses += 1
            return False, None
            
    def set(self, tool_name: str, params: Dict[str, Any], value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache with an expiration time.
        
        Args:
            tool_name: Name of the tool
            params: Dictionary of tool parameters
            value: Result value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        key = self._generate_key(tool_name, params)
        expiry_time = time.time() + (ttl if ttl is not None else self._default_ttl)
        
        with self._lock:
            self._cache[key] = (value, expiry_time)
            self._stats.entries = len(self._cache)
            
    def invalidate(self, tool_name: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        Invalidate cache entries for a specific tool or tool+params combination.
        
        Args:
            tool_name: Name of the tool
            params: Dictionary of tool parameters or None to invalidate all entries for the tool
            
        Returns:
            Number of entries invalidated
        """
        invalidated_count = 0
        
        with self._lock:
            if params is not None:
                # Invalidate specific entry
                key = self._generate_key(tool_name, params)
                if key in self._cache:
                    self._cache.pop(key)
                    invalidated_count = 1
            else:
                # Invalidate all entries for this tool
                # Need to create a list of keys to avoid modifying dict during iteration
                keys_to_remove = []
                
                # Find all keys for this tool (starting with the hash of the tool name)
                for key, _ in self._cache.items():
                    # We need to check each key by regenerating test keys for this tool
                    # This is inefficient but necessary without storing raw key info
                    test_params = {'_tool_check': True}
                    test_key = self._generate_key(tool_name, test_params)
                    
                    # If the first N chars of test_key match the key in cache,
                    # it's likely from this tool (not guaranteed, but close enough)
                    test_key_prefix = test_key[:8]  # First 8 chars as a heuristic
                    if key.startswith(test_key_prefix):
                        keys_to_remove.append(key)
                
                # Remove the identified keys
                for key in keys_to_remove:
                    self._cache.pop(key, None)
                    invalidated_count += 1
                    
            self._stats.entries = len(self._cache)
            self._stats.evictions += invalidated_count
            
        return invalidated_count
        
    def cleanup(self) -> int:
        """
        Remove all expired entries from the cache.
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        removed_count = 0
        
        with self._lock:
            # Collect keys to remove
            expired_keys = [key for key, (_, expiry) in self._cache.items() if expiry <= now]
            
            # Remove expired entries
            for key in expired_keys:
                self._cache.pop(key)
                removed_count += 1
                
            self._stats.entries = len(self._cache)
            self._stats.evictions += removed_count
            
        return removed_count
        
    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            evicted = len(self._cache)
            self._cache.clear()
            self._stats.entries = 0
            self._stats.evictions += evicted
            
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            # Return a copy to avoid external modification
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                entries=self._stats.entries,
                evictions=self._stats.evictions
            )


# Global instance for shared caching across tools
_global_cache = ToolCache()

def get_global_cache() -> ToolCache:
    """Get the global cache instance."""
    return _global_cache


def cached(ttl: Optional[int] = None):
    """
    Decorator to cache tool execution results.
    
    Args:
        ttl: Time-to-live in seconds (uses default if None)
        
    Returns:
        Decorated function with caching
    """
    def decorator(func: Callable):
        def wrapper(self, *args, **kwargs):
            # Get cache instance - prefer instance cache if available, fall back to global
            cache = getattr(self, "_cache", _global_cache)
            
            # Generate params dict from args and kwargs
            params = {**dict(zip(func.__code__.co_varnames[1:], args)), **kwargs}
            
            # Check cache
            hit, cached_result = cache.get(func.__name__, params)
            if hit:
                return cached_result
                
            # Run function if cache miss
            result = func(self, *args, **kwargs)
            
            # Store in cache
            cache.set(func.__name__, params, result, ttl)
            
            return result
        return wrapper
    return decorator
