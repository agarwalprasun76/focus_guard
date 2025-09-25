"""
Legacy JSON configuration adapter.

This module provides an adapter for legacy JSON configuration files.
"""

import os
import json
import logging
import copy
from typing import Any, Dict, Optional, Set, List, Tuple

from core_v2.config.interfaces import ConfigPath, ConfigScope
from core_v2.config.adapters.interfaces import LegacyConfigAdapter


class LegacyJsonConfigAdapter(LegacyConfigAdapter):
    """
    Adapter for legacy JSON configuration files.
    
    This adapter provides a bridge between legacy JSON configuration files
    and the new configuration system, allowing for smooth migration.
    """
    
    def __init__(
        self,
        legacy_file_path: str,
        path_mappings: Dict[str, ConfigPath],
        value_transformers: Optional[Dict[str, callable]] = None,
        auto_save: bool = False
    ):
        """
        Initialize the legacy JSON configuration adapter.
        
        Args:
            legacy_file_path: Path to the legacy JSON configuration file.
            path_mappings: Dictionary mapping legacy paths to new paths.
            value_transformers: Optional dictionary mapping legacy paths to value transformer functions.
            auto_save: Whether to automatically save changes to the legacy file.
        """
        self._legacy_file_path = legacy_file_path
        self._path_mappings = path_mappings
        self._reverse_mappings = {v: k for k, v in path_mappings.items()}
        self._value_transformers = value_transformers or {}
        self._auto_save = auto_save
        self._legacy_data: Dict[str, Any] = {}
        self._logger = logging.getLogger(__name__)
        
        # Load the legacy configuration
        self.load_legacy()
    
    def get_name(self) -> str:
        """
        Get the adapter name.
        
        Returns:
            The adapter name.
        """
        return "legacy_json"
    
    def get_legacy_value(self, legacy_path: str, default: Any = None) -> Any:
        """
        Get a value from the legacy configuration.
        
        Args:
            legacy_path: The legacy configuration path.
            default: The default value to return if the path does not exist.
            
        Returns:
            The configuration value, or the default value if the path does not exist.
        """
        if not legacy_path:
            return default
        
        # Split the path into components
        components = legacy_path.split(".")
        
        # Navigate through the nested dictionaries
        current = self._legacy_data
        for component in components:
            if not isinstance(current, dict) or component not in current:
                return default
            current = current[component]
        
        # Return a deep copy to avoid modifying the original data
        return copy.deepcopy(current)
    
    def set_legacy_value(self, legacy_path: str, value: Any) -> bool:
        """
        Set a value in the legacy configuration.
        
        Args:
            legacy_path: The legacy configuration path.
            value: The value to set.
            
        Returns:
            True if the value was set successfully, False otherwise.
        """
        if not legacy_path:
            return False
        
        # Split the path into components
        components = legacy_path.split(".")
        
        # Navigate through the nested dictionaries
        current = self._legacy_data
        for i, component in enumerate(components[:-1]):
            if component not in current:
                current[component] = {}
            elif not isinstance(current[component], dict):
                # If the component exists but is not a dictionary, create a new one
                current[component] = {}
            current = current[component]
        
        # Set the value
        current[components[-1]] = copy.deepcopy(value)
        
        # Save if auto-save is enabled
        if self._auto_save:
            self.save_legacy()
        
        return True
    
    def delete_legacy_value(self, legacy_path: str) -> bool:
        """
        Delete a value from the legacy configuration.
        
        Args:
            legacy_path: The legacy configuration path.
            
        Returns:
            True if the value was deleted successfully, False otherwise.
        """
        if not legacy_path or not self.has_legacy_value(legacy_path):
            return False
        
        # Split the path into components
        components = legacy_path.split(".")
        
        # Navigate through the nested dictionaries
        current = self._legacy_data
        path = []
        for component in components[:-1]:
            path.append((current, component))
            current = current[component]
        
        # Delete the value
        del current[components[-1]]
        
        # Clean up empty dictionaries
        for parent, component in reversed(path):
            if not parent[component]:
                del parent[component]
        
        # Save if auto-save is enabled
        if self._auto_save:
            self.save_legacy()
        
        return True
    
    def has_legacy_value(self, legacy_path: str) -> bool:
        """
        Check if a legacy configuration path exists.
        
        Args:
            legacy_path: The legacy configuration path.
            
        Returns:
            True if the path exists, False otherwise.
        """
        if not legacy_path:
            return False
        
        # Split the path into components
        components = legacy_path.split(".")
        
        # Navigate through the nested dictionaries
        current = self._legacy_data
        for component in components:
            if not isinstance(current, dict) or component not in current:
                return False
            current = current[component]
        
        # The path exists if we've reached this point
        # For dictionaries, they exist even if empty
        return True
    
    def get_all_legacy_paths(self, prefix: Optional[str] = None) -> Set[str]:
        """
        Get all legacy configuration paths.
        
        Args:
            prefix: Optional prefix to filter paths.
            
        Returns:
            A set of legacy configuration paths.
        """
        paths = set()
        self._collect_paths(self._legacy_data, "", paths)
        
        if prefix:
            return {path for path in paths if path.startswith(prefix)}
        else:
            return paths
    
    def _collect_paths(self, data: Any, path: str, paths: Set[str]) -> None:
        """
        Recursively collect all paths in a nested dictionary.
        
        Args:
            data: The data to collect paths from.
            path: The current path.
            paths: The set of paths to add to.
        """
        if not isinstance(data, dict):
            if path:
                paths.add(path)
            return
        
        if not data and path:
            paths.add(path)
            return
        
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                self._collect_paths(value, new_path, paths)
            else:
                paths.add(new_path)
    
    def translate_legacy_path(self, legacy_path: str) -> Optional[ConfigPath]:
        """
        Translate a legacy path to a new path.
        
        Args:
            legacy_path: The legacy configuration path.
            
        Returns:
            The new configuration path, or None if the path cannot be translated.
        """
        # Check for exact match
        if legacy_path in self._path_mappings:
            return self._path_mappings[legacy_path]
        
        # Check for prefix match
        for old_path, new_path in self._path_mappings.items():
            if legacy_path.startswith(f"{old_path}."):
                suffix = legacy_path[len(old_path) + 1:]
                return f"{new_path}.{suffix}"
        
        return None
    
    def translate_new_path(self, new_path: ConfigPath) -> Optional[str]:
        """
        Translate a new path to a legacy path.
        
        Args:
            new_path: The new configuration path.
            
        Returns:
            The legacy configuration path, or None if the path cannot be translated.
        """
        # Check for exact match
        if new_path in self._reverse_mappings:
            return self._reverse_mappings[new_path]
        
        # Check for prefix match
        for new_prefix, old_prefix in self._reverse_mappings.items():
            if new_path.startswith(f"{new_prefix}."):
                suffix = new_path[len(new_prefix) + 1:]
                return f"{old_prefix}.{suffix}"
        
        return None
    
    def get_path_mappings(self) -> Dict[str, ConfigPath]:
        """
        Get all path mappings from legacy to new paths.
        
        Returns:
            A dictionary mapping legacy paths to new paths.
        """
        return self._path_mappings.copy()
    
    def migrate_value(self, legacy_path: str, new_path: ConfigPath) -> Any:
        """
        Migrate a value from legacy to new configuration.
        
        Args:
            legacy_path: The legacy configuration path.
            new_path: The new configuration path.
            
        Returns:
            The migrated value, or None if the value cannot be migrated.
        """
        if not self.has_legacy_value(legacy_path):
            return None
        
        # Get the value
        value = self.get_legacy_value(legacy_path)
        
        # Apply transformer if available
        if legacy_path in self._value_transformers:
            try:
                value = self._value_transformers[legacy_path](value)
            except Exception as e:
                self._logger.error(f"Error transforming value for path '{legacy_path}': {e}")
                return None
        # Special handling for domains dictionary with nested categories
        elif legacy_path == "domains" and isinstance(value, dict):
            # Transform categories in each domain entry
            for domain_key, domain_data in value.items():
                if isinstance(domain_data, dict) and "category" in domain_data:
                    domain_data["category"] = self._transform_category(domain_data["category"])
        
        return value
    
    def migrate_all(self) -> Dict[ConfigPath, Any]:
        """
        Migrate all values from legacy to new configuration.
        
        Returns:
            A dictionary mapping new paths to migrated values.
        """
        result = {}
        
        # Migrate all mapped paths
        for legacy_path, new_path in self._path_mappings.items():
            if self.has_legacy_value(legacy_path):
                value = self.migrate_value(legacy_path, new_path)
                if value is not None:
                    result[new_path] = value
        
        return result
    
    def save_legacy(self) -> bool:
        """
        Save the legacy configuration.
        
        Returns:
            True if the configuration was saved successfully, False otherwise.
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self._legacy_file_path), exist_ok=True)
            
            # Write the configuration to file
            with open(self._legacy_file_path, "w") as f:
                json.dump(self._legacy_data, f, indent=2)
            
            return True
        except Exception as e:
            self._logger.error(f"Error saving legacy configuration: {e}")
            return False
    
    def load_legacy(self) -> bool:
        """
        Load the legacy configuration.
        
        Returns:
            True if the configuration was loaded successfully, False otherwise.
        """
        try:
            # Check if the file exists
            if not os.path.exists(self._legacy_file_path):
                self._legacy_data = {}
                return True
            
            # Read the configuration from file
            with open(self._legacy_file_path, "r") as f:
                self._legacy_data = json.load(f)
            
            return True
        except Exception as e:
            self._logger.error(f"Error loading legacy configuration: {e}")
            self._legacy_data = {}
            return False


class CategoryMappingAdapter(LegacyJsonConfigAdapter):
    """
    Adapter for legacy category mappings.
    
    This adapter provides a bridge between legacy category mappings
    and the new configuration system, with special handling for the
    hybrid approach used in Focus Guard for domain classification.
    """
    
    def __init__(
        self,
        legacy_file_path: str,
        path_mappings: Dict[str, ConfigPath],
        category_enum_mapping: Dict[str, Any],
        auto_save: bool = False
    ):
        """
        Initialize the category mapping adapter.
        
        Args:
            legacy_file_path: Path to the legacy JSON configuration file.
            path_mappings: Dictionary mapping legacy paths to new paths.
            category_enum_mapping: Dictionary mapping user-friendly category strings to enum values.
            auto_save: Whether to automatically save changes to the legacy file.
        """
        # Create transformers for category values
        value_transformers = {}
        
        for path in path_mappings.keys():
            if "category" in path.lower() or "domain" in path.lower():
                value_transformers[path] = self._transform_domain_categories
        
        super().__init__(legacy_file_path, path_mappings, value_transformers, auto_save)
        
        self._category_enum_mapping = category_enum_mapping
    
    def _transform_category(self, value: Any) -> Any:
        """
        Transform a category value from legacy to new format.
        
        Args:
            value: The legacy category value.
            
        Returns:
            The transformed category value.
        """
        if isinstance(value, str) and value in self._category_enum_mapping:
            return self._category_enum_mapping[value]
        return value
        
    def _transform_domain_categories(self, value: Any) -> Any:
        """
        Transform domain categories in a domains dictionary.
        
        Args:
            value: The domains dictionary.
            
        Returns:
            The transformed domains dictionary.
        """
        if not isinstance(value, dict):
            return value
            
        # Make a deep copy to avoid modifying the original
        result = copy.deepcopy(value)
        
        # Transform categories in each domain entry
        for domain_key, domain_data in result.items():
            if isinstance(domain_data, dict) and "category" in domain_data:
                domain_data["category"] = self._transform_category(domain_data["category"])
                
        return result
