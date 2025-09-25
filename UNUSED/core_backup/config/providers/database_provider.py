"""
Database-based configuration provider.

This module provides a database-backed configuration provider implementation.
"""

from typing import Any, Dict, Optional, Set, List, Tuple
import copy
import json
import threading
import sqlite3
import os
import logging
from pathlib import Path

from core_v2.config.interfaces import ConfigPath, ConfigProvider, ConfigScope


class DatabaseConfigProvider(ConfigProvider):
    """
    Database-based configuration provider.
    
    This provider stores configuration data in a SQLite database, which is useful
    for persistent storage with better performance and reliability than file-based
    storage for complex configurations.
    """
    
    def __init__(
        self, 
        database_path: str,
        table_name: str = "configuration",
        scope: ConfigScope = ConfigScope.USER
    ):
        """
        Initialize the database provider.
        
        Args:
            database_path: Path to the SQLite database file.
            table_name: Name of the configuration table.
            scope: The configuration scope.
        """
        self._database_path = database_path
        self._table_name = table_name
        self._scope = scope
        self._lock = threading.RLock()
        self._cache: Dict[str, Any] = {}
        self._logger = logging.getLogger(__name__)
        
        # Ensure the database directory exists
        os.makedirs(os.path.dirname(database_path), exist_ok=True)
        
        # Initialize the database
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Initialize the database schema."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Create the configuration table if it doesn't exist
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self._table_name} (
                        path TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        type TEXT NOT NULL,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
        except sqlite3.Error as e:
            self._logger.error(f"Failed to initialize database: {e}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection.
        
        Returns:
            A database connection.
        """
        conn = sqlite3.connect(self._database_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_name(self) -> str:
        """
        Get the provider name.
        
        Returns:
            The provider name.
        """
        return "database"
    
    def get_value(self, path: ConfigPath, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            path: The configuration path.
            default: The default value to return if the path does not exist.
            
        Returns:
            The configuration value, or the default value if the path does not exist.
        """
        with self._lock:
            # Check if the value is in the cache
            if path in self._cache:
                return copy.deepcopy(self._cache[path])
            
            # Check if this is a compound path that might need to retrieve a section
            if '.' in path:
                # Split the path into parts
                parts = path.split('.')
                root_path = parts[0]
                
                # Try to get the root object
                root_value = self.get_value(root_path)
                if root_value is not None and isinstance(root_value, dict):
                    # Navigate through the data
                    current = root_value
                    for part in parts[1:]:
                        if not isinstance(current, dict) or part not in current:
                            return default
                        current = current[part]
                    
                    return current
                
                return default
            
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Query the database
                    cursor.execute(
                        f"SELECT value, type FROM {self._table_name} WHERE path = ?",
                        (path,)
                    )
                    
                    row = cursor.fetchone()
                    if row:
                        value_str = row['value']
                        value_type = row['type']
                        
                        # Parse the value based on its type
                        value = self._parse_value(value_str, value_type)
                        
                        # Cache the value
                        self._cache[path] = value
                        
                        return copy.deepcopy(value)
            except sqlite3.Error as e:
                self._logger.error(f"Failed to get value for path '{path}': {e}")
            
            return default
    
    def set_value(self, path: ConfigPath, value: Any) -> bool:
        """
        Set a configuration value.
        
        Args:
            path: The configuration path.
            value: The value to set.
            
        Returns:
            True if the value was set successfully, False otherwise.
        """
        with self._lock:
            # Handle compound paths
            if '.' in path:
                # Split the path into parts
                parts = path.split('.')
                root_path = parts[0]
                
                # Get the root object
                root_value = self.get_value(root_path, {})
                if not isinstance(root_value, dict):
                    root_value = {}
                
                # Navigate through the data, creating dictionaries as needed
                current = root_value
                for i, part in enumerate(parts[1:-1]):
                    if part not in current or not isinstance(current[part], dict):
                        current[part] = {}
                    current = current[part]
                
                # Set the value
                current[parts[-1]] = value
                
                # Save the root object
                return self.set_value(root_path, root_value)
            
            try:
                # Determine the value type
                value_type = self._get_value_type(value)
                
                # Convert the value to a string
                value_str = self._serialize_value(value)
                
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Insert or update the value
                    cursor.execute(
                        f"""
                        INSERT OR REPLACE INTO {self._table_name} (path, value, type, last_updated)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        (path, value_str, value_type)
                    )
                    
                    conn.commit()
                
                # Update the cache
                self._cache[path] = copy.deepcopy(value)
                
                return True
            except sqlite3.Error as e:
                self._logger.error(f"Failed to set value for path '{path}': {e}")
                return False
    
    def delete_value(self, path: ConfigPath) -> bool:
        """
        Delete a configuration value.
        
        Args:
            path: The configuration path.
            
        Returns:
            True if the value was deleted successfully, False otherwise.
        """
        with self._lock:
            # Handle compound paths
            if '.' in path:
                # Split the path into parts
                parts = path.split('.')
                root_path = parts[0]
                
                # Get the root object
                root_value = self.get_value(root_path)
                if not isinstance(root_value, dict):
                    return False
                
                # Navigate through the data
                current = root_value
                parent_path = []
                parent = None
                
                for part in parts[1:-1]:
                    parent_path.append(part)
                    parent = current
                    if not isinstance(current, dict) or part not in current:
                        return False
                    current = current[part]
                
                # Delete the value
                if isinstance(current, dict) and parts[-1] in current:
                    del current[parts[-1]]
                    
                    # Clean up empty parent dictionaries
                    for i in range(len(parent_path) - 1, -1, -1):
                        check_path = '.'.join([root_path] + parent_path[:i+1])
                        check_dict = self.get_value(check_path, {})
                        
                        if not check_dict:
                            # This dictionary is empty, delete it
                            parent_of_empty = self.get_value('.'.join([root_path] + parent_path[:i]), {})
                            if isinstance(parent_of_empty, dict):
                                del parent_of_empty[parent_path[i]]
                    
                    # Save the root object
                    return self.set_value(root_path, root_value)
                
                return False
            
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Delete the value
                    cursor.execute(
                        f"DELETE FROM {self._table_name} WHERE path = ?",
                        (path,)
                    )
                    
                    conn.commit()
                    
                    # Remove from cache
                    if path in self._cache:
                        del self._cache[path]
                    
                    return cursor.rowcount > 0
            except sqlite3.Error as e:
                self._logger.error(f"Failed to delete value for path '{path}': {e}")
                return False
    
    def has_value(self, path: ConfigPath) -> bool:
        """
        Check if a configuration path exists.
        
        Args:
            path: The configuration path.
            
        Returns:
            True if the path exists, False otherwise.
        """
        with self._lock:
            # Check if the value is in the cache
            if path in self._cache:
                return True
            
            # Handle compound paths
            if '.' in path:
                # Split the path into parts
                parts = path.split('.')
                root_path = parts[0]
                
                # Get the root object
                root_value = self.get_value(root_path)
                if not isinstance(root_value, dict):
                    return False
                
                # Navigate through the data
                current = root_value
                for part in parts[1:]:
                    if not isinstance(current, dict) or part not in current:
                        return False
                    current = current[part]
                
                return True
            
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Query the database
                    cursor.execute(
                        f"SELECT COUNT(*) FROM {self._table_name} WHERE path = ?",
                        (path,)
                    )
                    
                    count = cursor.fetchone()[0]
                    return count > 0
            except sqlite3.Error as e:
                self._logger.error(f"Failed to check if path '{path}' exists: {e}")
                return False
    
    def get_all_paths(self, prefix: Optional[str] = None) -> Set[ConfigPath]:
        """
        Get all configuration paths.
        
        Args:
            prefix: Optional prefix to filter paths.
            
        Returns:
            A set of configuration paths.
        """
        paths = set()
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Query the database
                if prefix:
                    cursor.execute(
                        f"SELECT path FROM {self._table_name} WHERE path LIKE ?",
                        (f"{prefix}%",)
                    )
                else:
                    cursor.execute(f"SELECT path FROM {self._table_name}")
                
                # Collect paths
                for row in cursor.fetchall():
                    path = row['path']
                    paths.add(path)
                    
                    # Add paths for nested values
                    value = self.get_value(path)
                    if isinstance(value, dict):
                        self._collect_nested_paths(path, value, paths)
        except sqlite3.Error as e:
            self._logger.error(f"Failed to get all paths: {e}")
        
        return paths
    
    def _collect_nested_paths(self, base_path: str, data: Dict[str, Any], paths: Set[str]) -> None:
        """
        Collect nested paths from a dictionary.
        
        Args:
            base_path: The base path.
            data: The dictionary to collect paths from.
            paths: The set to add paths to.
        """
        for key, value in data.items():
            path = f"{base_path}.{key}"
            paths.add(path)
            
            if isinstance(value, dict):
                self._collect_nested_paths(path, value, paths)
    
    def get_scope(self) -> ConfigScope:
        """
        Get the provider scope.
        
        Returns:
            The provider scope.
        """
        return self._scope
    
    def load(self) -> bool:
        """
        Load the configuration data.
        
        Returns:
            True if the data was loaded successfully, False otherwise.
        """
        with self._lock:
            # Clear the cache
            self._cache = {}
            
            try:
                # Check if the database file exists
                if not os.path.exists(self._database_path):
                    return False
                
                # Database is already initialized, so just return success
                return True
            except Exception as e:
                self._logger.error(f"Failed to load configuration data: {e}")
                return False
    
    def save(self) -> bool:
        """
        Save the configuration data.
        
        Returns:
            True if the data was saved successfully, False otherwise.
        """
        # Database provider saves data immediately, so this is a no-op
        return True
    
    def clear(self) -> bool:
        """
        Clear the configuration data.
        
        Returns:
            True if the data was cleared successfully, False otherwise.
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Delete all data
                    cursor.execute(f"DELETE FROM {self._table_name}")
                    
                    conn.commit()
                
                # Clear the cache
                self._cache = {}
                
                return True
            except sqlite3.Error as e:
                self._logger.error(f"Failed to clear configuration data: {e}")
                return False
    
    def _get_value_type(self, value: Any) -> str:
        """
        Get the type of a value.
        
        Args:
            value: The value.
            
        Returns:
            The value type as a string.
        """
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "string"
    
    def _serialize_value(self, value: Any) -> str:
        """
        Serialize a value to a string.
        
        Args:
            value: The value to serialize.
            
        Returns:
            The serialized value.
        """
        if value is None:
            return "null"
        elif isinstance(value, (bool, int, float, str, list, dict)):
            return json.dumps(value)
        else:
            return json.dumps(str(value))
    
    def _parse_value(self, value_str: str, value_type: str) -> Any:
        """
        Parse a value from a string.
        
        Args:
            value_str: The serialized value.
            value_type: The value type.
            
        Returns:
            The parsed value.
        """
        if value_type == "null":
            return None
        elif value_str == "null":
            return None
        else:
            try:
                return json.loads(value_str)
            except json.JSONDecodeError:
                return value_str
