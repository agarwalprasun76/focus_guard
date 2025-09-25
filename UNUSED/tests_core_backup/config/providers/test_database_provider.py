"""
Unit tests for database configuration provider.

This module contains unit tests for the database configuration provider.
"""

import unittest
import os
import tempfile
import sqlite3
from typing import Any, Dict, Optional, Set

from core_v2.config.interfaces import ConfigPath, ConfigScope
from core_v2.config.providers.database_provider import DatabaseConfigProvider


class TestDatabaseConfigProvider(unittest.TestCase):
    """Test cases for DatabaseConfigProvider."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary database file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_config.db")
        
        # Create the provider
        self.provider = DatabaseConfigProvider(
            database_path=self.db_path,
            table_name="test_config",
            scope=ConfigScope.USER
        )
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Close the provider's database connection
        self.provider._conn.close()
        
        # Remove the temporary directory
        self.temp_dir.cleanup()
    
    def test_init(self):
        """Test initialization."""
        # Check properties
        self.assertEqual(self.provider.get_name(), "database")
        self.assertEqual(self.provider.get_scope(), ConfigScope.USER)
        
        # Check if the database file was created
        self.assertTrue(os.path.exists(self.db_path))
        
        # Check if the table was created
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_config'")
        self.assertIsNotNone(cursor.fetchone())
        conn.close()
    
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
        
        # Check if values are persisted in the database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM test_config WHERE path = ?", ("path1",))
        self.assertEqual(cursor.fetchone()[0], '"value1"')
        conn.close()
    
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
        
        # Check if values are deleted from the database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_config WHERE path = ?", ("path1",))
        self.assertEqual(cursor.fetchone()[0], 0)
        conn.close()
    
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
        
        # Check if values are cleared from the database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_config")
        self.assertEqual(cursor.fetchone()[0], 0)
        conn.close()
    
    def test_load_save(self):
        """Test loading and saving."""
        # Set values
        self.provider.set_value("path1", "value1")
        self.provider.set_value("path2", "value2")
        
        # Create a new provider with the same database
        new_provider = DatabaseConfigProvider(
            database_path=self.db_path,
            table_name="test_config",
            scope=ConfigScope.USER
        )
        
        # Load values
        self.assertTrue(new_provider.load())
        
        # Check if values were loaded
        self.assertEqual(new_provider.get_value("path1"), "value1")
        self.assertEqual(new_provider.get_value("path2"), "value2")
        
        # Modify values
        new_provider.set_value("path1", "new_value1")
        new_provider.set_value("path3", "value3")
        
        # Save values
        self.assertTrue(new_provider.save())
        
        # Close the new provider
        new_provider._conn.close()
        
        # Create another provider with the same database
        another_provider = DatabaseConfigProvider(
            database_path=self.db_path,
            table_name="test_config",
            scope=ConfigScope.USER
        )
        
        # Load values
        self.assertTrue(another_provider.load())
        
        # Check if values were saved
        self.assertEqual(another_provider.get_value("path1"), "new_value1")
        self.assertEqual(another_provider.get_value("path2"), "value2")
        self.assertEqual(another_provider.get_value("path3"), "value3")
        
        # Close the provider
        another_provider._conn.close()
    
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
    
    def test_transaction(self):
        """Test transaction support."""
        # Start a transaction
        self.provider._conn.execute("BEGIN TRANSACTION")
        
        # Set values
        self.provider.set_value("path1", "value1")
        self.provider.set_value("path2", "value2")
        
        # Rollback the transaction
        self.provider._conn.execute("ROLLBACK")
        
        # Check if values exist
        self.assertFalse(self.provider.has_value("path1"))
        self.assertFalse(self.provider.has_value("path2"))
        
        # Start another transaction
        self.provider._conn.execute("BEGIN TRANSACTION")
        
        # Set values
        self.provider.set_value("path1", "value1")
        self.provider.set_value("path2", "value2")
        
        # Commit the transaction
        self.provider._conn.execute("COMMIT")
        
        # Check if values exist
        self.assertTrue(self.provider.has_value("path1"))
        self.assertTrue(self.provider.has_value("path2"))


if __name__ == "__main__":
    unittest.main()
