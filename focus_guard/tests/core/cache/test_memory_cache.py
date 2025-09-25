"""
Tests for the memory cache in core.

This module contains unit tests for the MemoryCache class, which provides an in-memory
caching mechanism with TTL (time-to-live) support, hit/miss tracking, and statistics.

The tests cover:
- Basic cache operations (set, get, delete, clear)
- TTL expiration functionality
- Cache statistics and hit/miss tracking
- Edge cases and error handling
"""

import unittest
import time
import pytest
from unittest.mock import patch, MagicMock

from focus_guard.core.cache.memory_cache import MemoryCache


class TestMemoryCache(unittest.TestCase):
    """Tests for the MemoryCache class.
    
    This test suite verifies the functionality of the MemoryCache class,
    including its caching behavior, TTL handling, and statistics tracking.
    """
    
    def setUp(self):
        """Set up test fixtures.
        
        Creates a cache instance with a short default TTL for faster testing.
        """
        # Create a cache with a short TTL for testing
        self.cache = MemoryCache(default_ttl=0.1)
    
    def test_set_and_get(self):
        """Test setting and getting cache items."""
        # Set a cache item
        self.cache.set("test_key", "test_value")
        
        # Get the cache item
        value = self.cache.get("test_key")
        
        # Verify the value
        self.assertEqual(value, "test_value")
    
    def test_get_nonexistent_key(self):
        """Test getting a nonexistent key."""
        # Get a nonexistent key
        value = self.cache.get("nonexistent_key")
        
        # Verify that None is returned
        self.assertIsNone(value)
    
    def test_get_with_default(self):
        """Test getting a nonexistent key with a default value."""
        # Get a nonexistent key with a default value
        value = self.cache.get("nonexistent_key", default="default_value")
        
        # Verify that the default value is returned
        self.assertEqual(value, "default_value")
    
    def test_set_with_custom_ttl(self):
        """Test setting a cache item with a custom TTL."""
        # Set a cache item with a custom TTL
        self.cache.set("test_key", "test_value", ttl=0.2)
        
        # Get the cache item
        value = self.cache.get("test_key")
        
        # Verify the value
        self.assertEqual(value, "test_value")
        
        # Wait for the TTL to expire
        time.sleep(0.3)
        
        # Get the cache item again
        value = self.cache.get("test_key")
        
        # Verify that None is returned
        self.assertIsNone(value)
    
    def test_delete(self):
        """Test deleting a cache item."""
        # Set a cache item
        self.cache.set("test_key", "test_value")
        
        # Delete the cache item
        result = self.cache.delete("test_key")
        
        # Verify that True is returned when key exists
        self.assertTrue(result)
        
        # Get the cache item
        value = self.cache.get("test_key")
        
        # Verify that None is returned
        self.assertIsNone(value)
        
    def test_delete_nonexistent_key(self):
        """Test deleting a nonexistent cache item.
        
        This test verifies that attempting to delete a key that doesn't exist
        in the cache returns False and doesn't raise an exception.
        """
        # Delete a nonexistent key
        result = self.cache.delete("nonexistent_key")
        
        # Verify that False is returned
        self.assertFalse(result)
    
    def test_clear(self):
        """Test clearing the cache."""
        # Set multiple cache items
        self.cache.set("test_key1", "test_value1")
        self.cache.set("test_key2", "test_value2")
        
        # Clear the cache
        self.cache.clear()
        
        # Get the cache items
        value1 = self.cache.get("test_key1")
        value2 = self.cache.get("test_key2")
        
        # Verify that None is returned for both
        self.assertIsNone(value1)
        self.assertIsNone(value2)
    
    def test_cleanup(self):
        """Test cleaning up expired cache items."""
        # Set multiple cache items with different TTLs
        self.cache.set("test_key1", "test_value1", ttl=0.05)
        self.cache.set("test_key2", "test_value2", ttl=0.2)
        
        # Wait for the first item to expire
        time.sleep(0.1)
        
        # Clean up expired items
        self.cache.cleanup()
        
        # Get the cache items
        value1 = self.cache.get("test_key1")
        value2 = self.cache.get("test_key2")
        
        # Verify that the first item is None and the second item is still there
        self.assertIsNone(value1)
        self.assertEqual(value2, "test_value2")
    
    def test_get_or_set(self):
        """Test getting or setting a cache item."""
        # Define a function that returns a value
        def get_value():
            return "computed_value"
        
        # Get or set a nonexistent key
        value = self.cache.get_or_set("test_key", get_value)
        
        # Verify that the computed value is returned
        self.assertEqual(value, "computed_value")
        
        # Get or set the same key again
        value = self.cache.get_or_set("test_key", lambda: "different_value")
        
        # Verify that the original value is returned
        self.assertEqual(value, "computed_value")
    
    def test_stats(self):
        """Test getting cache statistics."""
        # Set multiple cache items
        self.cache.set("test_key1", "test_value1")
        self.cache.set("test_key2", "test_value2")
        
        # Get the cache stats
        stats = self.cache.stats()
        
        # Verify the stats
        self.assertEqual(stats["size"], 2)
        self.assertIn("hits", stats)
        self.assertIn("misses", stats)
    
    def test_ttl_expiration(self):
        """Test that cache items expire after their TTL."""
        # Set a cache item with a short TTL
        self.cache.set("test_key", "test_value", ttl=0.1)
        
        # Get the cache item
        value = self.cache.get("test_key")
        
        # Verify the value
        self.assertEqual(value, "test_value")
        
        # Wait for the TTL to expire
        time.sleep(0.2)
        
        # Get the cache item again
        value = self.cache.get("test_key")
        
        # Verify that None is returned
        self.assertIsNone(value)
    
    @patch('time.time')
    def test_hit_and_miss_tracking(self, mock_time):
        """Test that cache hits and misses are tracked correctly.
        
        This test verifies that the cache properly tracks hits (successful retrievals)
        and misses (failed retrievals) in its statistics.
        """
        # Set up the mock time
        mock_time.return_value = 1000
        
        # Create a new cache
        cache = MemoryCache(default_ttl=60)
        
        # Set a cache item
        cache.set("test_key", "test_value")
        
        # Get the cache item (hit)
        cache.get("test_key")
        
        # Get a nonexistent key (miss)
        cache.get("nonexistent_key")
        
        # Get the cache stats
        stats = cache.stats()
        
        # Verify the stats
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        
        # Additional hits and misses
        cache.get("test_key")  # Another hit
        cache.get("test_key")  # Another hit
        cache.get("another_missing_key")  # Another miss
        
        # Verify updated stats
        stats = cache.stats()
        self.assertEqual(stats["hits"], 3)
        self.assertEqual(stats["misses"], 2)


    def test_set_and_get_different_types(self):
        """Test setting and getting different types of values.
        
        This test verifies that the cache can store and retrieve
        different types of values correctly, including strings,
        integers, lists, dictionaries, and None.
        """
        test_cases = [
            ("string_key", "string_value", "string_value"),
            ("int_key", 42, 42),
            ("list_key", [1, 2, 3], [1, 2, 3]),
            ("dict_key", {"a": 1, "b": 2}, {"a": 1, "b": 2}),
            ("none_key", None, None),
        ]
        
        for key, value, expected in test_cases:
            with self.subTest(key=key, value=value):
                # Set the cache item
                self.cache.set(key, value)
                
                # Get the cache item
                result = self.cache.get(key)
                
                # Verify the value
                self.assertEqual(result, expected)
    
    def test_set_default_ttl(self):
        """Test setting the default TTL for the cache.
        
        This test verifies that changing the default TTL affects new cache entries
        but not existing ones.
        """
        # Set a cache item with the original default TTL
        self.cache.set("test_key1", "test_value1")
        
        # Change the default TTL
        self.cache.set_default_ttl(0.3)
        
        # Set another cache item with the new default TTL
        self.cache.set("test_key2", "test_value2")
        
        # Verify both values are initially present
        self.assertEqual(self.cache.get("test_key1"), "test_value1")
        self.assertEqual(self.cache.get("test_key2"), "test_value2")
        
        # Wait for the original TTL to expire
        time.sleep(0.2)
        
        # Verify the first item has expired but the second hasn't
        self.assertIsNone(self.cache.get("test_key1"))
        self.assertEqual(self.cache.get("test_key2"), "test_value2")
        
        # Wait for the new TTL to expire
        time.sleep(0.2)
        
        # Verify the second item has now expired
        self.assertIsNone(self.cache.get("test_key2"))
    
    def test_edge_case_zero_ttl(self):
        """Test edge case with zero TTL.
        
        This test verifies that items with a TTL of 0 expire immediately.
        """
        # Set a cache item with zero TTL
        self.cache.set("test_key", "test_value", ttl=0)
        
        # Verify the item is not in the cache
        self.assertIsNone(self.cache.get("test_key"))


if __name__ == "__main__":
    unittest.main()
