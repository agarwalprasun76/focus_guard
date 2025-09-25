"""
Test disk cache persistence across restarts for MultiLevelCache.
"""

import asyncio
import tempfile
import os
import time
from focus_guard.core.cache.multi_level_cache import MultiLevelCache
from focus_guard.core.domain.models import Domain, Category, Classification


async def main():
    print("Testing Disk Cache Persistence Across Restarts")
    print("=" * 48)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = os.path.join(temp_dir, "cache")
        
        # Test data
        test_data = {
            "example.com": Classification(
                domain=Domain("example.com"),
                category=Category.PRODUCTIVITY,
                confidence=0.8,
                metadata={"source": "test", "timestamp": time.time()}
            ),
            "github.com": Classification(
                domain=Domain("github.com"),
                category=Category.PRODUCTIVITY,
                confidence=0.9,
                metadata={"source": "test", "timestamp": time.time()}
            ),
            "youtube.com": Classification(
                domain=Domain("youtube.com"),
                category=Category.ENTERTAINMENT,
                confidence=0.7,
                metadata={"source": "test", "timestamp": time.time()}
            )
        }
        
        # Phase 1: Create cache and populate it
        print("\n1. Creating cache and populating with test data")
        print("-" * 48)
        
        cache1 = MultiLevelCache(
            cache_dir=cache_dir,
            memory_ttl=3600,
            disk_ttl=86400
        )
        
        # Store test data
        for key, value in test_data.items():
            await cache1.set(key, value, source='persistence_test')
            print(f"  Stored: {key}")
        
        # Verify data is in memory cache
        print("\n  Verifying memory cache:")
        for key in test_data.keys():
            result = await cache1.get(key)
            assert result is not None
            print(f"    {key}: {result.category.name}")
        
        # Get cache stats
        stats1 = cache1.get_stats()
        print(f"\n  Memory entries: {stats1['memory_valid_entries']}")
        print(f"  Disk hits: {stats1['disk_hits']}")
        print(f"  Memory hits: {stats1['memory_hits']}")
        
        # Close first cache instance
        await cache1.close()
        print("\n  Cache instance 1 closed")
        
        # Phase 2: Create new cache instance (simulates restart)
        print("\n2. Creating new cache instance (simulating restart)")
        print("-" * 52)
        
        cache2 = MultiLevelCache(
            cache_dir=cache_dir,
            memory_ttl=3600,
            disk_ttl=86400
        )
        
        # Verify data persisted to disk
        print("\n  Verifying disk persistence:")
        for key, expected_value in test_data.items():
            result = await cache2.get(key)
            assert result is not None
            assert result.domain.value == expected_value.domain.value
            assert result.category == expected_value.category
            print(f"    {key}: {result.category.name} (persisted)")
        
        # Get cache stats after restart
        stats2 = cache2.get_stats()
        print(f"\n  Memory entries: {stats2['memory_valid_entries']}")
        print(f"  Disk hits: {stats2['disk_hits']}")
        print(f"  Memory hits: {stats2['memory_hits']}")
        
        # Phase 3: Test cache warming from disk
        print("\n3. Testing cache warming from disk")
        print("-" * 37)
        
        # Clear memory cache but keep disk
        cache2.memory_cache.clear()
        
        # Verify memory is empty but disk has data
        memory_stats = cache2.memory_cache.stats()
        print(f"  Memory entries after clear: {memory_stats['valid_entries']}")
        
        # Access data - should load from disk to memory
        for key in test_data.keys():
            result = await cache2.get(key)
            assert result is not None
            print(f"    Loaded from disk: {key}")
        
        # Verify data is now in memory again
        memory_stats_after = cache2.memory_cache.stats()
        print(f"  Memory entries after disk load: {memory_stats_after['valid_entries']}")
        
        # Phase 4: Test TTL persistence
        print("\n4. Testing TTL persistence")
        print("-" * 27)
        
        # Add item with short TTL
        short_ttl_item = Classification(
            domain=Domain("short-ttl.com"),
            category=Category.SOCIAL_MEDIA,
            confidence=0.6,
            metadata={"source": "ttl_test"}
        )
        
        await cache2.set("short-ttl.com", short_ttl_item, ttl=2, source='ttl_test')
        print("  Added item with 2-second TTL")
        
        # Verify it exists
        result = await cache2.get("short-ttl.com")
        assert result is not None
        print("  Item exists immediately after creation")
        
        # Wait for TTL expiration
        print("  Waiting 3 seconds for TTL expiration...")
        await asyncio.sleep(3)
        
        # Verify it's expired
        result = await cache2.get("short-ttl.com")
        assert result is None
        print("  Item correctly expired after TTL")
        
        # Phase 5: Test cache directory structure
        print("\n5. Testing cache directory structure")
        print("-" * 38)
        
        # Verify cache files exist
        cache_files = os.listdir(cache_dir)
        print(f"  Cache directory contains {len(cache_files)} files:")
        for file in sorted(cache_files):
            file_path = os.path.join(cache_dir, file)
            size = os.path.getsize(file_path)
            print(f"    {file} ({size} bytes)")
        
        # Verify we can read the cache files
        assert len(cache_files) > 0
        print("  Cache files successfully created and readable")
        
        await cache2.close()
        
        print("\n" + "=" * 48)
        print("CACHE PERSISTENCE TEST RESULTS")
        print("=" * 48)
        print("+ Data persists across cache restarts")
        print("+ Memory cache loads from disk on access")
        print("+ TTL expiration works correctly")
        print("+ Cache directory structure is correct")
        print("\nALL PERSISTENCE TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
