"""
JSON configuration provider.

This module provides a simple JSON file-based configuration provider implementation.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Set

from core_v2.config.interfaces import ConfigProvider, ConfigPath
from core_v2.config.providers.file_provider import JsonFileProvider


class JsonConfigProvider(ConfigProvider):
    """
    Simple JSON configuration provider.
    
    This provider is a simplified version of JsonFileProvider for use in tests
    and basic configurations.
    """
    
    def __init__(self, file_path: str):
        """
        Initialize the JSON config provider.
        
        Args:
            file_path: Path to the JSON file.
        """
        # Initialize with the file path directly
        self.file_path = Path(file_path)
        self._config: Dict[str, Any] = {}
        self._last_modified_time = 0
        
        # Create parent directory if it doesn't exist
        os.makedirs(self.file_path.parent, exist_ok=True)
        
        # Load the configuration if the file exists
        self._load_config()
    
    def get_name(self) -> str:
        """
        Get the provider name.
        
        Returns:
            The provider name.
        """
        return "json"
    
    def get_scope(self) -> str:
        """
        Get the provider scope.
        
        Returns:
            The provider scope.
        """
        return "user"
    
    def get_value(self, path: ConfigPath, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            path: The configuration path.
            default: The default value to return if the path does not exist.
            
        Returns:
            The configuration value, or the default value if the path does not exist.
        """
        # Split the path into parts
        parts = path.split('.')
        
        # Navigate through the data
        current = self._config
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        
        return current
    
    def set_value(self, path: ConfigPath, value: Any) -> bool:
        """
        Set a configuration value.
        
        Args:
            path: The configuration path.
            value: The value to set.
            
        Returns:
            True if the value was set successfully, False otherwise.
        """
        # Split the path into parts
        parts = path.split('.')
        
        # Navigate through the data, creating dictionaries as needed
        current = self._config
        for i, part in enumerate(parts[:-1]):
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        
        # Set the value
        current[parts[-1]] = value
        
        # Save the configuration
        self._save_config()
        
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
        # Split the path into parts
        parts = path.split('.')
        
        # Navigate through the data
        current = self._config
        parent_stack = []
        for part in parts[:-1]:
            if not isinstance(current, dict) or part not in current:
                return False
            parent_stack.append((current, part))
            current = current[part]
        
        # Delete the value
        if isinstance(current, dict) and parts[-1] in current:
            del current[parts[-1]]
            
            # Clean up empty parent dictionaries
            for parent, key in reversed(parent_stack):
                if not parent[key]:
                    del parent[key]
            
            # Save the configuration
            self._save_config()
            
            return True
        
        return False
    
    def has_value(self, path: ConfigPath) -> bool:
        """
        Check if a configuration value exists.
        
        Args:
            path: The configuration path.
            
        Returns:
            True if the value exists, False otherwise.
        """
        # Split the path into parts
        parts = path.split('.')
        
        # Navigate through the data
        current = self._config
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        
        return True
    
    def clear(self) -> bool:
        """
        Clear all configuration values.
        
        Returns:
            True if the values were cleared successfully, False otherwise.
        """
        self._config = {}
        self._save_config()
        return True
    
    def get_all_paths(self) -> Set[ConfigPath]:
        """
        Get all configuration paths.
        
        Returns:
            A set of all configuration paths.
        """
        paths = set()
        self._collect_paths("", self._config, paths)
        return paths
    
    def _collect_paths(self, prefix: str, data: Dict[str, Any], paths: Set[str]) -> None:
        """
        Recursively collect all paths in the configuration.
        
        Args:
            prefix: The current path prefix.
            data: The current data dictionary.
            paths: The set to collect paths into.
        """
        if not isinstance(data, dict):
            return
        
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            paths.add(path)
            
            if isinstance(value, dict):
                self._collect_paths(path, value, paths)
    
    def _load_config(self) -> None:
        """
        Load the configuration from the file.
        """
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r') as f:
                    self._config = json.load(f)
                self._last_modified_time = os.path.getmtime(self.file_path)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading configuration: {e}")
    
    def _save_config(self) -> None:
        """
        Save the configuration to the file.
        """
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            self._last_modified_time = os.path.getmtime(self.file_path)
        except IOError as e:
            print(f"Error saving configuration: {e}")
    
    def load(self) -> Dict[str, Any]:
        """
        Load the configuration.
        
        Returns:
            The loaded configuration.
        """
        self._load_config()
        return self._config
    
    def save(self, config: Dict[str, Any]) -> bool:
        """
        Save the configuration.
        
        Args:
            config: The configuration to save.
            
        Returns:
            True if the configuration was saved successfully, False otherwise.
        """
        self._config = config
        self._save_config()
        return True
