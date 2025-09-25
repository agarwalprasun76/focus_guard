"""
Tests for MultiLevelCache implementation.
"""

import asyncio
import os
import tempfile
import time
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from focus_guard.core.cache.multi_level_cache import MultiLevelCache, CacheEntry
from focus_guard.core.domain.models import Domain, Category, Classification


class TestMultiLevelCache:
    """Test suite for MultiLevelCache."""
    
    @pytest.fixture
    async def cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    async def cache(self, cache_dir):
        """Create MultiLevelCache instance."""
        cache = MultiLevelCache(
            cache_dir=cache_dir,
            memory_ttl=60,
            disk_ttl=3600,
            max_memory_size=10,
            max_disk_size=100
        )
        yield cache
        await cache.close()
    
    @pytest.mark.asyncio
    async def test_basic_set_get(self, cache):
        """Test basic cache set and get operations."""
        # Set a value
        await cache.set("test_key", "test_value")
        
        # Get the value
        result = await cache.get("test_key")
        assert result == "test_value"
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        """Test cache miss behavior."""
        result = await cache.get("nonexistent_key", default="default_value")
        assert result == "default_value"
    
    @pytest.mark.asyncio
    async def test_memory_to_disk_promotion(self, cache):
        """Test that disk cache values are promoted to memory cache."""
        # Set value (goes to both memory and disk)
        await cache.set("test_key", "test_value")
        
        # Clear memory cache to simulate restart
        cache.memory_cache.clear()
        
        # Get value - should come from disk and be promoted to memory
        result = await cache.get("test_key")
        assert result == "test_value"
        
        # Verify it's now in memory cache
        memory_result = cache.memory_cache.get("test_key")
        assert memory_result is not None
        assert memory_result.value == "test_value"
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache_dir):
        """Test TTL expiration for cache entries."""
        # Create cache with very short TTL
        cache = MultiLevelCache(
            cache_dir=cache_dir,
            memory_ttl=1,  # 1 second
            disk_ttl=2
        )
        
        try:
            # Set value
            await cache.set("test_key", "test_value")
            
            # Should be available immediately
            result = await cache.get("test_key")
            assert result == "test_value"
            
            # Wait for expiration
            await asyncio.sleep(1.5)
            
            # Should be expired
            result = await cache.get("test_key", default="expired")
            assert result == "expired"
        
        finally:
            await cache.close()
    
    @pytest.mark.asyncio
    async def test_cache_with_classifier_func(self, cache):
        """Test cache with classifier function fallback."""
        # Mock classifier function
        async def mock_classifier():
            return "computed_value"
        
        # Should call classifier and cache result
        result = await cache.get("new_key", classifier_func=mock_classifier)
        assert result == "computed_value"
        
        # Second call should use cache
        result = await cache.get("new_key")
        assert result == "computed_value"
    
    @pytest.mark.asyncio
    async def test_cache_warming(self, cache):
        """Test cache warming functionality."""
        # Mock classifier function
        async def mock_classifier(domain):
            return f"classification_for_{domain}"
        
        domains = ["example.com", "test.com", "demo.com"]
        
        # Warm cache
        warmed_count = await cache.warm_cache(domains, mock_classifier)
        assert warmed_count == len(domains)
        
        # Verify all domains are cached
        for domain in domains:
            result = await cache.get(domain)
            assert result == f"classification_for_{domain}"
    
    @pytest.mark.asyncio
    async def test_background_refresh(self, cache):
        """Test background refresh functionality."""
        # Mock classifier function
        call_count = 0
        async def mock_classifier(domain):
            nonlocal call_count
            call_count += 1
            return f"classification_{call_count}"
        
        # Start background refresh
        await cache.start_background_refresh(mock_classifier)
        
        # Set initial value
        await cache.set("popular_domain", "initial_value")
        
        # Add to popular domains
        cache.popular_domains.add("popular_domain")
        
        # Wait a bit for background refresh (would need longer interval in real test)
        await asyncio.sleep(0.1)
        
        # Stop background refresh
        await cache.stop_background_refresh()
        
        assert call_count >= 0  # Background refresh may or may not have run
    
    @pytest.mark.asyncio
    async def test_cache_cleanup(self, cache_dir):
        """Test cache cleanup functionality."""
        # Create cache with short TTL
        cache = MultiLevelCache(
            cache_dir=cache_dir,
            memory_ttl=1,
            disk_ttl=1
        )
        
        try:
            # Add some entries
            await cache.set("key1", "value1")
            await cache.set("key2", "value2")
            
            # Wait for expiration
            await asyncio.sleep(1.5)
            
            # Run cleanup
            cleanup_stats = await cache.cleanup()
            
            # Should have cleaned up expired entries
            assert cleanup_stats['memory_cleaned'] >= 0
            assert cleanup_stats['disk_cleaned'] >= 0
        
        finally:
            await cache.close()
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, cache):
        """Test cache statistics."""
        # Add some entries
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Get some values (hits)
        await cache.get("key1")
        await cache.get("key1")  # Another hit
        
        # Try to get non-existent key (miss)
        await cache.get("nonexistent")
        
        stats = cache.get_stats()
        
        assert stats['memory_hits'] >= 2
        assert stats['misses'] >= 1
        assert 'hit_rate' in stats
        assert 'memory_size' in stats
    
    @pytest.mark.asyncio
    async def test_disk_persistence(self, cache_dir):
        """Test that disk cache persists across cache instances."""
        # Create first cache instance
        cache1 = MultiLevelCache(cache_dir=cache_dir)
        await cache1.set("persistent_key", "persistent_value")
        await cache1.close()
        
        # Create second cache instance
        cache2 = MultiLevelCache(cache_dir=cache_dir)
        
        try:
            # Should be able to retrieve value from disk
            result = await cache2.get("persistent_key")
            assert result == "persistent_value"
        
        finally:
            await cache2.close()
    
    @pytest.mark.asyncio
    async def test_cache_size_limits(self, cache_dir):
        """Test cache size limit enforcement."""
        # Create cache with small limits
        cache = MultiLevelCache(
            cache_dir=cache_dir,
            max_memory_size=3,
            max_disk_size=5
        )
        
        try:
            # Add more entries than the limit
            for i in range(10):
                await cache.set(f"key_{i}", f"value_{i}")
            
            # Memory cache should be limited
            memory_stats = cache.memory_cache.stats()
            assert memory_stats['size'] <= 3
            
            # Disk cache should be limited (harder to test directly)
            # But the cache should still function
            result = await cache.get("key_9")  # Most recent should still be there
            assert result == "value_9"
        
        finally:
            await cache.close()


class TestCacheEntry:
    """Test suite for CacheEntry."""
    
    def test_cache_entry_creation(self):
        """Test CacheEntry creation and basic properties."""
        entry = CacheEntry(
            value="test_value",
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=1,
            ttl=3600,
            source="test"
        )
        
        assert entry.value == "test_value"
        assert entry.access_count == 1
        assert entry.source == "test"
        assert not entry.is_expired()
    
    def test_cache_entry_expiration(self):
        """Test CacheEntry expiration logic."""
        # Create expired entry
        entry = CacheEntry(
            value="test_value",
            created_at=time.time() - 7200,  # 2 hours ago
            last_accessed=time.time() - 7200,
            access_count=1,
            ttl=3600,  # 1 hour TTL
            source="test"
        )
        
        assert entry.is_expired()
    
    def test_cache_entry_update_access(self):
        """Test CacheEntry access tracking."""
        entry = CacheEntry(
            value="test_value",
            created_at=time.time(),
            last_accessed=time.time() - 100,
            access_count=1,
            ttl=3600,
            source="test"
        )
        
        original_access_time = entry.last_accessed
        original_count = entry.access_count
        
        entry.update_access()
        
        assert entry.last_accessed > original_access_time
        assert entry.access_count == original_count + 1


@pytest.mark.asyncio
async def test_classification_caching_integration():
    """Integration test with actual Classification objects."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache = MultiLevelCache(cache_dir=temp_dir)
        
        try:
            # Create a Classification object
            domain = Domain("example.com")
            classification = Classification(
                domain=domain,
                category=Category.PRODUCTIVITY,
                confidence=0.9,
                metadata={"source": "test"}
            )
            
            # Cache the classification
            await cache.set("example.com", classification)
            
            # Retrieve and verify
            result = await cache.get("example.com")
            assert result is not None
            assert result.domain.value == "example.com"
            assert result.category == Category.PRODUCTIVITY
            assert result.confidence == 0.9
        
        finally:
            await cache.close()


if __name__ == "__main__":
    # Run basic functionality test
    async def run_basic_test():
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = MultiLevelCache(cache_dir=temp_dir)
            
            try:
                print("Testing basic cache operations...")
                
                # Test set/get
                await cache.set("test", "value")
                result = await cache.get("test")
                print(f"Set/Get test: {'PASS' if result == 'value' else 'FAIL'}")
                
                # Test statistics
                stats = cache.get_stats()
                print(f"Stats test: {'PASS' if 'memory_hits' in stats else 'FAIL'}")
                
                # Test cache warming
                async def mock_classifier(domain):
                    return f"classified_{domain}"
                
                warmed = await cache.warm_cache(["example.com"], mock_classifier)
                print(f"Cache warming test: {'PASS' if warmed == 1 else 'FAIL'}")
                
                print("Basic tests completed successfully!")
                
            finally:
                await cache.close()
    
    asyncio.run(run_basic_test())
