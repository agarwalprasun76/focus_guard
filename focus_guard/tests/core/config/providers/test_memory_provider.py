"""
Unit tests for memory configuration provider.

This module contains unit tests for the memory configuration provider.
"""

import unittest
from typing import Any, Dict, Optional, Set

from focus_guard.core.config.interfaces import ConfigPath, ConfigScope
from focus_guard.core.config.providers.memory_provider import MemoryConfigProvider


class TestMemoryConfigProvider(unittest.TestCase):
    """Test cases for MemoryConfigProvider."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.provider = MemoryConfigProvider()
    
    def test_init(self):
        """Test initialization."""
        # Check properties
        self.assertEqual(self.provider.get_name(), "memory")
        self.assertEqual(self.provider.get_scope(), ConfigScope.MEMORY)
    
    def test_get_set_value(self):
        """Test getting and setting values."""
        # Set values
        self.assertTrue(self.provider.set_value("path1", "value1"))
        self.assertTrue(self.provider.set_value("path2", 42))
        self.assertTrue(self.provider.set_value("path3.nested", True))
        
        # Get values
        self.assertEqual(self.provider.get_value("path1"), "value1")
        self.assertEqual(self.provider.get_value("path2"), 42)
        self.assertEqual(self.provider.get_value("path3.nested"), True)
        
        # Get non-existent value
        self.assertIsNone(self.provider.get_value("nonexistent"))
        self.assertEqual(self.provider.get_value("nonexistent", default="default"), "default")
    
    def test_has_value(self):
        """Test checking if values exist."""
        # Set values
        self.provider.set_value("path1", "value1")
        self.provider.set_value("path2.nested", "value2")
        
        # Check if values exist
        self.assertTrue(self.provider.has_value("path1"))
        self.assertTrue(self.provider.has_value("path2.nested"))
        self.assertFalse(self.provider.has_value("nonexistent"))
        self.assertFalse(self.provider.has_value("path2.nonexistent"))
    
    def test_delete_value(self):
        """Test deleting values."""
        # Set values
        self.provider.set_value("path1", "value1")
        self.provider.set_value("path2.nested", "value2")
        
        # Delete values
        self.assertTrue(self.provider.delete_value("path1"))
        self.assertTrue(self.provider.delete_value("path2.nested"))
        
        # Check if values exist
        self.assertFalse(self.provider.has_value("path1"))
        self.assertFalse(self.provider.has_value("path2.nested"))
        
        # Try to delete non-existent value
        self.assertFalse(self.provider.delete_value("nonexistent"))
    
    def test_get_all_paths(self):
        """Test getting all paths."""
        # Set values
        self.provider.set_value("path1", "value1")
        self.provider.set_value("path2.nested1", "value2")
        self.provider.set_value("path2.nested2", "value3")
        self.provider.set_value("path3", "value4")
        
        # Get all paths
        paths = self.provider.get_all_paths()
        self.assertEqual(paths, {"path1", "path2.nested1", "path2.nested2", "path3"})
        
        # Get paths with prefix
        paths = self.provider.get_all_paths(prefix="path2")
        self.assertEqual(paths, {"path2.nested1", "path2.nested2"})
    
    def test_clear(self):
        """Test clearing all values."""
        # Set values
        self.provider.set_value("path1", "value1")
        self.provider.set_value("path2", "value2")
        
        # Clear values
        self.assertTrue(self.provider.clear())
        
        # Check if values exist
        self.assertFalse(self.provider.has_value("path1"))
        self.assertFalse(self.provider.has_value("path2"))
        self.assertEqual(self.provider.get_all_paths(), set())
    
    def test_load_save(self):
        """Test loading and saving."""
        # Set values
        self.provider.set_value("path1", "value1")
        self.provider.set_value("path2", "value2")
        
        # Save and load should always return True for memory provider
        self.assertTrue(self.provider.save())
        self.assertTrue(self.provider.load())
        
        # Values should still exist
        self.assertEqual(self.provider.get_value("path1"), "value1")
        self.assertEqual(self.provider.get_value("path2"), "value2")
    
    def test_nested_paths(self):
        """Test nested paths."""
        # Set nested values
        self.provider.set_value("parent.child1", "value1")
        self.provider.set_value("parent.child2", "value2")
        self.provider.set_value("parent.grandchild.value", "value3")
        
        # Get nested values
        self.assertEqual(self.provider.get_value("parent.child1"), "value1")
        self.assertEqual(self.provider.get_value("parent.child2"), "value2")
        self.assertEqual(self.provider.get_value("parent.grandchild.value"), "value3")
        
        # Delete nested value
        self.assertTrue(self.provider.delete_value("parent.child1"))
        self.assertFalse(self.provider.has_value("parent.child1"))
        self.assertTrue(self.provider.has_value("parent.child2"))
        
        # Get all paths
        paths = self.provider.get_all_paths()
        self.assertEqual(paths, {"parent.child2", "parent.grandchild.value"})
        
        # Get paths with prefix
        paths = self.provider.get_all_paths(prefix="parent")
        self.assertEqual(paths, {"parent.child2", "parent.grandchild.value"})
        
        paths = self.provider.get_all_paths(prefix="parent.grandchild")
        self.assertEqual(paths, {"parent.grandchild.value"})


if __name__ == "__main__":
    unittest.main()
