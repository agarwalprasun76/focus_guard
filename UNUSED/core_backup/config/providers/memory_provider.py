"""
Memory-based configuration provider.

This module provides an in-memory configuration provider implementation.
"""

from typing import Any, Dict, Optional, Set
import copy
import threading

from core_v2.config.interfaces import ConfigPath, ConfigProvider, ConfigScope


class MemoryConfigProvider(ConfigProvider):
    """
    Memory-based configuration provider.
    
    This provider stores configuration data in memory, which is useful for
    temporary configurations, testing, and as a cache for other providers.
    """
    
    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        """
        Initialize the memory provider.
        
        Args:
            initial_data: Optional initial configuration data.
        """
        self._data: Dict[str, Any] = {}
        self._lock = threading.RLock()
        
        # Initialize with data if provided
        if initial_data:
            self._data = copy.deepcopy(initial_data)
    
    def get_name(self) -> str:
        """
        Get the provider name.
        
        Returns:
            The provider name.
        """
        return "memory"
    
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
            # Split the path into parts
            parts = path.split('.')
            
            # Navigate through the data
            current = self._data
            for part in parts:
                if not isinstance(current, dict) or part not in current:
                    return default
                current = current[part]
            
            # Return a deep copy to prevent modification of internal data
            return copy.deepcopy(current)
            
    def get(self, path: ConfigPath, default: Any = None) -> Any:
        """
        Alias for get_value for backward compatibility with tests.
        
        Args:
            path: The configuration path.
            default: The default value to return if the path does not exist.
            
        Returns:
            The configuration value, or the default value if the path does not exist.
        """
        return self.get_value(path, default)
    
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
            # Split the path into parts
            parts = path.split('.')
            
            # Navigate through the data, creating dictionaries as needed
            current = self._data
            for i, part in enumerate(parts[:-1]):
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]
            
            # Set the value
            current[parts[-1]] = copy.deepcopy(value)
            
            return True
            
    def set(self, path: ConfigPath, value: Any) -> bool:
        """
        Alias for set_value for backward compatibility with tests.
        
        Args:
            path: The configuration path.
            value: The value to set.
            
        Returns:
            True if the value was set successfully, False otherwise.
        """
        return self.set_value(path, value)
    
    def delete_value(self, path: ConfigPath) -> bool:
        """
        Delete a configuration value.
        
        Args:
            path: The configuration path.
            
        Returns:
            True if the value was deleted successfully, False otherwise.
        """
        with self._lock:
            # Split the path into parts
            parts = path.split('.')
            
            # Navigate through the data
            current = self._data
            parent_path = []
            parent = None
            
            for part in parts[:-1]:
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
                    check_path = '.'.join(parent_path[:i+1])
                    check_dict = self.get_value(check_path, {})
                    
                    if not check_dict:
                        # This dictionary is empty, delete it
                        parent_of_empty = self.get_value('.'.join(parent_path[:i]), {})
                        if isinstance(parent_of_empty, dict):
                            del parent_of_empty[parent_path[i]]
                
                return True
            
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
            # Split the path into parts
            parts = path.split('.')
            
            # Navigate through the data
            current = self._data
            for part in parts:
                if not isinstance(current, dict) or part not in current:
                    return False
                current = current[part]
            
            return True
    
    def get_all_paths(self, prefix: Optional[str] = None) -> Set[ConfigPath]:
        """
        Get all configuration paths.
        
        Args:
            prefix: Optional prefix to filter paths.
            
        Returns:
            A set of configuration paths.
        """
        paths = set()
        
        with self._lock:
            self._collect_paths(self._data, "", paths)
            
            # Filter by prefix if provided
            if prefix:
                paths = {path for path in paths if path.startswith(prefix)}
            
            return paths
    
    def _collect_paths(self, data: Dict[str, Any], current_path: str, paths: Set[str]) -> None:
        """
        Collect all paths in the data.
        
        Args:
            data: The data to collect paths from.
            current_path: The current path.
            paths: The set to add paths to.
        """
        if not isinstance(data, dict):
            return
        
        for key, value in data.items():
            path = f"{current_path}.{key}" if current_path else key
            paths.add(path)
            
            if isinstance(value, dict):
                self._collect_paths(value, path, paths)
    
    def get_scope(self) -> ConfigScope:
        """
        Get the provider scope.
        
        Returns:
            The provider scope.
        """
        return ConfigScope.MEMORY
    
    def load(self) -> bool:
        """
        Load the configuration data.
        
        Returns:
            True if the data was loaded successfully, False otherwise.
        """
        # Memory provider doesn't need to load data
        return True
    
    def save(self) -> bool:
        """
        Save the configuration data.
        
        Returns:
            True if the data was saved successfully, False otherwise.
        """
        # Memory provider doesn't need to save data
        return True
    
    def clear(self) -> bool:
        """
        Clear the configuration data.
        
        Returns:
            True if the data was cleared successfully, False otherwise.
        """
        with self._lock:
            self._data = {}
            return True
    
    def get_data(self) -> Dict[str, Any]:
        """
        Get a copy of the configuration data.
        
        Returns:
            A copy of the configuration data.
        """
        with self._lock:
            return copy.deepcopy(self._data)
    
    def set_data(self, data: Dict[str, Any]) -> bool:
        """
        Set the configuration data.
        
        Args:
            data: The configuration data.
            
        Returns:
            True if the data was set successfully, False otherwise.
        """
        with self._lock:
            self._data = copy.deepcopy(data)
            return True
