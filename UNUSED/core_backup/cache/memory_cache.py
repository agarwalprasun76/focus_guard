"""
In-memory caching implementation.

This module provides an in-memory cache with TTL (Time-To-Live) support for storing
and retrieving temporary data. It includes features like automatic expiration,
hit/miss tracking, and statistics.

The MemoryCache class is designed to be a lightweight, thread-safe caching solution
for temporarily storing computed values, API responses, or any other data that
might be expensive to generate but can be reused for a period of time.

Features:
- Generic typing support for type safety
- Configurable TTL (Time-To-Live) for cache entries
- Automatic expiration of stale entries
- Hit/miss tracking for performance monitoring
- Cache statistics for monitoring and debugging
- Support for default values when keys are not found

Example usage:
    # Create a cache with a default TTL of 60 seconds
    cache = MemoryCache[str](default_ttl=60)
    
    # Set a value with the default TTL
    cache.set("key1", "value1")
    
    # Set a value with a custom TTL
    cache.set("key2", "value2", ttl=10)
    
    # Get a value (returns None if not found or expired)
    value = cache.get("key1")
    
    # Get a value with a default
    value = cache.get("nonexistent_key", default="default_value")
    
    # Get or compute a value
    value = cache.get_or_set("key3", lambda: expensive_computation())
    
    # Get cache statistics
    stats = cache.stats()
"""

import time
from typing import Dict, Any, Optional, Tuple, Generic, TypeVar, Callable, Union

T = TypeVar('T')


class MemoryCache(Generic[T]):
    """
    In-memory cache with TTL support.
    
    This class provides a simple in-memory cache that automatically
    expires entries after a specified time-to-live (TTL). It tracks
    cache hits and misses for performance monitoring.
    
    The cache stores values with associated expiration times and automatically
    removes expired entries when they are accessed. It also provides methods
    for manually cleaning up expired entries and retrieving cache statistics.
    
    Attributes:
        _cache (Dict[str, Tuple[T, float]]): Internal dictionary storing cached values
            and their expiration timestamps.
        _default_ttl (Union[int, float]): Default time-to-live for cache entries in seconds.
        _hits (int): Counter for cache hits.
        _misses (int): Counter for cache misses.
    """
    
    def __init__(self, default_ttl: Union[int, float] = 3600):
        """
        Initialize the memory cache.
        
        Args:
            default_ttl: Default time-to-live for cache entries in seconds.
                         Can be an integer or float value.
        """
        self._cache: Dict[str, Tuple[T, float]] = {}
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key.
            default: Value to return if key is not found or expired.
            
        Returns:
            The cached value, or default if not found or expired.
        """
        if key not in self._cache:
            self._misses += 1
            return default
        
        value, expiry = self._cache[key]
        
        # Check if the entry has expired
        if time.time() > expiry:
            del self._cache[key]
            self._misses += 1
            return default
        
        self._hits += 1
        return value
    
    def set(self, key: str, value: T, ttl: Optional[Union[int, float]] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Time-to-live in seconds. If None, the default TTL is used.
        """
        ttl_value = ttl if ttl is not None else self._default_ttl
        expiry = time.time() + ttl_value
        self._cache[key] = (value, expiry)
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: The cache key.
            
        Returns:
            True if the key was found and deleted, False otherwise.
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._cache.clear()
    
    def cleanup(self) -> int:
        """
        Remove all expired entries from the cache.
        
        Returns:
            The number of entries removed.
        """
        now = time.time()
        expired_keys = [
            key for key, (_, expiry) in self._cache.items()
            if now > expiry
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)
    
    def get_or_set(self, key: str, value_func: Callable[[], T], ttl: Optional[Union[int, float]] = None) -> T:
        """
        Get a value from the cache, or set it if not found.
        
        Args:
            key: The cache key.
            value_func: A function that returns the value to cache if not found.
            ttl: Time-to-live in seconds. If None, the default TTL is used.
            
        Returns:
            The cached value, or the result of value_func if not found.
        """
        value = self.get(key)
        if value is None:
            value = value_func()
            self.set(key, value, ttl)
        return value
    
    def stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.
        
        Returns:
            A dictionary with cache statistics including size, hits, and misses.
        """
        now = time.time()
        total_entries = len(self._cache)
        expired_entries = sum(1 for _, expiry in self._cache.values() if now > expiry)
        valid_entries = total_entries - expired_entries
        
        return {
            "size": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "hits": self._hits,
            "misses": self._misses
        }
    
    def set_default_ttl(self, ttl_seconds: Union[int, float]) -> None:
        """
        Set the default TTL for new cache entries.
        
        Args:
            ttl_seconds: Default time-to-live in seconds. Can be an integer or float value.
        """
        self._default_ttl = ttl_seconds
