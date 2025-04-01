"""
Tool result caching functionality for BaseTool class.
This adds caching with TTL support to tools.
"""
import time
from typing import Dict, Any, Optional, Tuple

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

# The following methods should be added to BaseTool class:

def _init_cache(self, ttl_seconds: int = 300, enable_caching: bool = True):
    """
    Initialize caching for this tool.
    
    Args:
        ttl_seconds: Default TTL for cached results
        enable_caching: Whether caching is enabled by default
    """
    self._cache = ToolCache()
    self._cache_ttl = ttl_seconds
    self._enable_caching = enable_caching
    
    # Statistics for monitoring
    self._cache_stats = {
        "hits": 0,
        "misses": 0,
        "total_calls": 0
    }
    
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
    import json
    key_parts = [self.name, json.dumps(sorted_kwargs, sort_keys=True)]
    return ":".join(key_parts)
    
def _get_from_cache(self, **kwargs) -> Tuple[bool, Any]:
    """
    Try to get a result from the cache.
    
    Args:
        **kwargs: Tool parameters
        
    Returns:
        Tuple of (cache_hit, result)
    """
    if not self._enable_caching:
        return False, None
        
    self._cache_stats["total_calls"] += 1
    
    # Generate cache key
    cache_key = self._generate_cache_key(**kwargs)
    
    # Try to get from cache
    result = self._cache.get(cache_key)
    if result is not None:
        self._cache_stats["hits"] += 1
        return True, result
        
    self._cache_stats["misses"] += 1
    return False, None
    
def _store_in_cache(self, result: Any, **kwargs) -> None:
    """
    Store a result in the cache.
    
    Args:
        result: The result to cache
        **kwargs: The parameters that generated this result
    """
    if not self._enable_caching:
        return
        
    cache_key = self._generate_cache_key(**kwargs)
    self._cache.set(cache_key, result, self._cache_ttl)
    
def clear_cache(self) -> None:
    """Clear all cached results for this tool."""
    self._cache.clear()
    
def get_cache_stats(self) -> Dict[str, Any]:
    """
    Get statistics about the cache usage.
    
    Returns:
        Dictionary with cache statistics
    """
    stats = self._cache_stats.copy()
    
    # Calculate hit rate
    if stats["total_calls"] > 0:
        stats["hit_rate"] = stats["hits"] / stats["total_calls"]
    else:
        stats["hit_rate"] = 0
        
    return stats
