"""
Multi-level caching system for classification results.

This module provides a sophisticated caching system that combines memory and disk
caching with intelligent cache warming and background refresh capabilities.
"""

import asyncio
import json
import logging
import os
import pickle
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union, Callable, List, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading

from focus_guard.core.cache.memory_cache import MemoryCache
from focus_guard.core.domain.models import Classification, Domain, Category

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    ttl: float
    source: str  # 'memory', 'disk', 'background'
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() > (self.created_at + self.ttl)
    
    def update_access(self) -> None:
        """Update access statistics."""
        self.last_accessed = time.time()
        self.access_count += 1


class MultiLevelCache:
    """
    Multi-level cache with memory, disk persistence, and background refresh.
    
    Features:
    - L1: Fast in-memory cache using MemoryCache
    - L2: Persistent disk cache for restart survival
    - Background refresh for popular entries
    - Cache warming from configuration
    - Smart eviction policies
    - Performance monitoring
    """
    
    def __init__(
        self,
        cache_dir: str,
        memory_ttl: int = 3600,
        disk_ttl: int = 86400,  # 24 hours
        max_memory_size: int = 1000,
        max_disk_size: int = 10000,
        background_refresh_interval: int = 300,  # 5 minutes
        enable_background_refresh: bool = True
    ):
        """
        Initialize multi-level cache.
        
        Args:
            cache_dir: Directory for disk cache storage
            memory_ttl: TTL for memory cache entries (seconds)
            disk_ttl: TTL for disk cache entries (seconds)
            max_memory_size: Maximum entries in memory cache
            max_disk_size: Maximum entries in disk cache
            background_refresh_interval: Interval for background refresh (seconds)
            enable_background_refresh: Whether to enable background refresh
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache configuration
        self.memory_ttl = memory_ttl
        self.disk_ttl = disk_ttl
        self.max_memory_size = max_memory_size
        self.max_disk_size = max_disk_size
        self.background_refresh_interval = background_refresh_interval
        self.enable_background_refresh = enable_background_refresh
        
        # L1: Memory cache
        self.memory_cache = MemoryCache[CacheEntry](default_ttl=memory_ttl)
        
        # L2: Disk cache metadata
        self.disk_cache_file = self.cache_dir / "classification_cache.pkl"
        self.disk_metadata_file = self.cache_dir / "cache_metadata.json"
        
        # Background refresh
        self.background_refresh_task = None
        self.refresh_queue = asyncio.Queue()
        self.popular_domains = set()
        
        # Thread pool for disk I/O
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cache")
        
        # Statistics
        self.stats = {
            'memory_hits': 0,
            'disk_hits': 0,
            'misses': 0,
            'background_refreshes': 0,
            'cache_warmings': 0
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Load existing disk cache
        self._load_disk_cache()
    
    async def get(
        self, 
        key: str, 
        default: Optional[Any] = None,
        classifier_func: Optional[Callable] = None
    ) -> Optional[Any]:
        """
        Get value from cache with fallback chain: Memory -> Disk -> Classifier.
        
        Args:
            key: Cache key
            default: Default value if not found
            classifier_func: Optional function to compute value if cache miss
            
        Returns:
            Cached value or default
        """
        # Try L1: Memory cache
        entry = self.memory_cache.get(key)
        if entry and not entry.is_expired():
            entry.update_access()
            self.stats['memory_hits'] += 1
            logger.debug(f"Memory cache hit for key: {key}")
            return entry.value
        
        # Try L2: Disk cache
        entry = await self._get_from_disk(key)
        if entry and not entry.is_expired():
            entry.update_access()
            # Promote to memory cache
            self.memory_cache.set(key, entry, ttl=self.memory_ttl)
            self.stats['disk_hits'] += 1
            logger.debug(f"Disk cache hit for key: {key}")
            return entry.value
        
        # Cache miss - try classifier if provided
        if classifier_func:
            try:
                value = await classifier_func()
                if value is not None:
                    await self.set(key, value, source='classifier')
                    return value
            except Exception as e:
                logger.error(f"Classifier function failed for key {key}: {e}")
        
        self.stats['misses'] += 1
        return default
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        source: str = 'manual'
    ) -> None:
        """
        Set value in both memory and disk cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live (uses default if None)
            source: Source of the cache entry
        """
        ttl = ttl or self.memory_ttl
        
        entry = CacheEntry(
            value=value,
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=1,
            ttl=ttl,
            source=source
        )
        
        # Set in memory cache
        self.memory_cache.set(key, entry, ttl=ttl)
        
        # Set in disk cache asynchronously
        await self._set_to_disk(key, entry)
        
        # Track popular domains for background refresh
        if entry.access_count > 5:  # Arbitrary threshold
            self.popular_domains.add(key)
        
        logger.debug(f"Cached value for key: {key} (source: {source})")
    
    async def warm_cache(self, domains: List[str], classifier_func: Callable) -> int:
        """
        Warm cache with popular domains.
        
        Args:
            domains: List of domains to warm
            classifier_func: Function to classify domains
            
        Returns:
            Number of domains successfully warmed
        """
        warmed_count = 0
        
        for domain in domains:
            try:
                # Skip if already cached and not expired
                existing = await self.get(domain)
                if existing is not None:
                    continue
                
                # Classify and cache
                result = await classifier_func(domain)
                if result is not None:
                    await self.set(domain, result, source='warming')
                    warmed_count += 1
                    logger.debug(f"Warmed cache for domain: {domain}")
                
                # Small delay to avoid overwhelming the classifier
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Failed to warm cache for domain {domain}: {e}")
        
        self.stats['cache_warmings'] += warmed_count
        logger.info(f"Cache warming completed: {warmed_count}/{len(domains)} domains")
        return warmed_count
    
    async def start_background_refresh(self, classifier_func: Callable) -> None:
        """
        Start background refresh task for popular domains.
        
        Args:
            classifier_func: Function to refresh classifications
        """
        if not self.enable_background_refresh or self.background_refresh_task:
            return
        
        self.background_refresh_task = asyncio.create_task(
            self._background_refresh_loop(classifier_func)
        )
        logger.info("Background cache refresh started")
    
    async def stop_background_refresh(self) -> None:
        """Stop background refresh task."""
        if self.background_refresh_task:
            self.background_refresh_task.cancel()
            try:
                await self.background_refresh_task
            except asyncio.CancelledError:
                pass
            self.background_refresh_task = None
            logger.info("Background cache refresh stopped")
    
    async def cleanup(self) -> Dict[str, int]:
        """
        Clean up expired entries from both memory and disk cache.
        
        Returns:
            Cleanup statistics
        """
        # Cleanup memory cache
        memory_cleaned = self.memory_cache.cleanup()
        
        # Cleanup disk cache
        disk_cleaned = await self._cleanup_disk_cache()
        
        return {
            'memory_cleaned': memory_cleaned,
            'disk_cleaned': disk_cleaned
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        memory_stats = self.memory_cache.stats()
        
        return {
            **self.stats,
            'memory_size': memory_stats['size'],
            'memory_valid_entries': memory_stats['valid_entries'],
            'popular_domains_count': len(self.popular_domains),
            'hit_rate': (
                (self.stats['memory_hits'] + self.stats['disk_hits']) /
                max(1, sum(self.stats.values()))
            )
        }
    
    async def _get_from_disk(self, key: str) -> Optional[CacheEntry]:
        """Get entry from disk cache."""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                self.executor, self._sync_get_from_disk, key
            )
        except Exception as e:
            logger.error(f"Error reading from disk cache: {e}")
            return None
    
    def _sync_get_from_disk(self, key: str) -> Optional[CacheEntry]:
        """Synchronous disk cache read."""
        with self._lock:
            if not self.disk_cache_file.exists():
                return None
            
            try:
                with open(self.disk_cache_file, 'rb') as f:
                    disk_cache = pickle.load(f)
                    return disk_cache.get(key)
            except Exception as e:
                logger.error(f"Error loading disk cache: {e}")
                return None
    
    async def _set_to_disk(self, key: str, entry: CacheEntry) -> None:
        """Set entry to disk cache."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                self.executor, self._sync_set_to_disk, key, entry
            )
        except Exception as e:
            logger.error(f"Error writing to disk cache: {e}")
    
    def _sync_set_to_disk(self, key: str, entry: CacheEntry) -> None:
        """Synchronous disk cache write."""
        with self._lock:
            # Load existing cache
            disk_cache = {}
            if self.disk_cache_file.exists():
                try:
                    with open(self.disk_cache_file, 'rb') as f:
                        disk_cache = pickle.load(f)
                except Exception as e:
                    logger.warning(f"Could not load existing disk cache: {e}")
            
            # Add/update entry
            disk_cache[key] = entry
            
            # Enforce size limits
            if len(disk_cache) > self.max_disk_size:
                # Remove oldest entries
                sorted_entries = sorted(
                    disk_cache.items(),
                    key=lambda x: x[1].last_accessed
                )
                # Keep only the most recent entries
                disk_cache = dict(sorted_entries[-self.max_disk_size:])
            
            # Write back to disk
            try:
                with open(self.disk_cache_file, 'wb') as f:
                    pickle.dump(disk_cache, f)
            except Exception as e:
                logger.error(f"Error saving disk cache: {e}")
    
    def _load_disk_cache(self) -> None:
        """Load existing disk cache on startup."""
        if self.disk_cache_file.exists():
            try:
                with open(self.disk_cache_file, 'rb') as f:
                    disk_cache = pickle.load(f)
                    logger.info(f"Loaded {len(disk_cache)} entries from disk cache")
            except Exception as e:
                logger.warning(f"Could not load disk cache: {e}")
    
    async def _cleanup_disk_cache(self) -> int:
        """Clean up expired entries from disk cache."""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                self.executor, self._sync_cleanup_disk_cache
            )
        except Exception as e:
            logger.error(f"Error cleaning up disk cache: {e}")
            return 0
    
    def _sync_cleanup_disk_cache(self) -> int:
        """Synchronous disk cache cleanup."""
        with self._lock:
            if not self.disk_cache_file.exists():
                return 0
            
            try:
                with open(self.disk_cache_file, 'rb') as f:
                    disk_cache = pickle.load(f)
                
                # Remove expired entries
                original_size = len(disk_cache)
                disk_cache = {
                    k: v for k, v in disk_cache.items()
                    if not v.is_expired()
                }
                
                # Write back cleaned cache
                with open(self.disk_cache_file, 'wb') as f:
                    pickle.dump(disk_cache, f)
                
                cleaned_count = original_size - len(disk_cache)
                if cleaned_count > 0:
                    logger.info(f"Cleaned {cleaned_count} expired entries from disk cache")
                
                return cleaned_count
                
            except Exception as e:
                logger.error(f"Error during disk cache cleanup: {e}")
                return 0
    
    async def _background_refresh_loop(self, classifier_func: Callable) -> None:
        """Background loop to refresh popular cache entries."""
        while True:
            try:
                await asyncio.sleep(self.background_refresh_interval)
                
                # Refresh popular domains
                for domain in list(self.popular_domains):
                    try:
                        # Check if entry needs refresh (older than half TTL)
                        entry = self.memory_cache.get(domain)
                        if entry and (time.time() - entry.created_at) > (self.memory_ttl / 2):
                            # Refresh in background
                            result = await classifier_func(domain)
                            if result is not None:
                                await self.set(domain, result, source='background')
                                self.stats['background_refreshes'] += 1
                                logger.debug(f"Background refreshed: {domain}")
                    
                    except Exception as e:
                        logger.warning(f"Background refresh failed for {domain}: {e}")
                
            except asyncio.CancelledError:
                logger.info("Background refresh loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background refresh loop: {e}")
    
    async def close(self) -> None:
        """Clean shutdown of cache system."""
        await self.stop_background_refresh()
        self.executor.shutdown(wait=True)
        logger.info("Multi-level cache closed")
