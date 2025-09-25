"""
Parallel configuration provider.

This module provides a configuration provider that operates both legacy and new
configuration systems in parallel, enabling a smooth migration path.
"""

import logging
from typing import Any, Dict, Optional, Set, List, Tuple

from focus_guard.core.config.interfaces import ConfigPath, ConfigProvider, ConfigScope
from focus_guard.core.config.adapters.interfaces import LegacyConfigAdapter


class ParallelConfigProvider(ConfigProvider):
    """
    Parallel configuration provider.
    
    This provider operates both legacy and new configuration systems in parallel,
    allowing for a smooth migration path. Changes are written to both systems,
    but reads prioritize the new system.
    """
    
    def __init__(
        self,
        new_provider: ConfigProvider,
        legacy_adapter: LegacyConfigAdapter,
        write_to_legacy: bool = True,
        write_to_new: bool = True,
        read_legacy_fallback: bool = True
    ):
        """
        Initialize the parallel configuration provider.
        
        Args:
            new_provider: The new configuration provider.
            legacy_adapter: The legacy configuration adapter.
            write_to_legacy: Whether to write changes to the legacy system.
            write_to_new: Whether to write changes to the new system.
            read_legacy_fallback: Whether to fall back to legacy system for reads.
        """
        self._new_provider = new_provider
        self._legacy_adapter = legacy_adapter
        self._write_to_legacy = write_to_legacy
        self._write_to_new = write_to_new
        self._read_legacy_fallback = read_legacy_fallback
        self._logger = logging.getLogger(__name__)
    
    def get_name(self) -> str:
        """
        Get the provider name.
        
        Returns:
            The provider name.
        """
        return f"parallel_{self._new_provider.get_name()}"
    
    def get_value(self, path: ConfigPath, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            path: The configuration path.
            default: The default value to return if the path does not exist.
            
        Returns:
            The configuration value, or the default value if the path does not exist.
        """
        # Try to get the value from the new system
        if self._new_provider.has_value(path):
            return self._new_provider.get_value(path, default)
        
        # Fall back to legacy system if enabled
        if self._read_legacy_fallback:
            legacy_path = self._legacy_adapter.translate_new_path(path)
            if legacy_path and self._legacy_adapter.has_legacy_value(legacy_path):
                value = self._legacy_adapter.get_legacy_value(legacy_path)
                
                # Migrate the value to the new system if writing to new is enabled
                if self._write_to_new:
                    migrated_value = self._legacy_adapter.migrate_value(legacy_path, path)
                    if migrated_value is not None:
                        self._new_provider.set_value(path, migrated_value)
                
                return value
        
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
        success = True
        
        # Write to the new system if enabled
        if self._write_to_new:
            if not self._new_provider.set_value(path, value):
                success = False
                self._logger.error(f"Failed to set value for path '{path}' in new provider")
        
        # Write to the legacy system if enabled
        if self._write_to_legacy:
            legacy_path = self._legacy_adapter.translate_new_path(path)
            if legacy_path:
                if not self._legacy_adapter.set_legacy_value(legacy_path, value):
                    success = False
                    self._logger.error(f"Failed to set value for path '{legacy_path}' in legacy adapter")
        
        return success
    
    def delete_value(self, path: ConfigPath) -> bool:
        """
        Delete a configuration value.
        
        Args:
            path: The configuration path.
            
        Returns:
            True if the value was deleted successfully, False otherwise.
        """
        success = True
        
        # Delete from the new system if enabled
        if self._write_to_new:
            if not self._new_provider.delete_value(path):
                success = False
                self._logger.error(f"Failed to delete value for path '{path}' in new provider")
        
        # Delete from the legacy system if enabled
        if self._write_to_legacy:
            legacy_path = self._legacy_adapter.translate_new_path(path)
            if legacy_path:
                if not self._legacy_adapter.delete_legacy_value(legacy_path):
                    success = False
                    self._logger.error(f"Failed to delete value for path '{legacy_path}' in legacy adapter")
        
        return success
    
    def has_value(self, path: ConfigPath) -> bool:
        """
        Check if a configuration path exists.
        
        Args:
            path: The configuration path.
            
        Returns:
            True if the path exists, False otherwise.
        """
        # Check the new system
        if self._new_provider.has_value(path):
            return True
        
        # Fall back to legacy system if enabled
        if self._read_legacy_fallback:
            legacy_path = self._legacy_adapter.translate_new_path(path)
            if legacy_path and self._legacy_adapter.has_legacy_value(legacy_path):
                return True
        
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
        
        # Get paths from the new system
        paths.update(self._new_provider.get_all_paths(prefix))
        
        # Get paths from the legacy system if enabled
        if self._read_legacy_fallback:
            legacy_prefix = None
            if prefix:
                legacy_prefix = self._legacy_adapter.translate_new_path(prefix)
            
            legacy_paths = self._legacy_adapter.get_all_legacy_paths(legacy_prefix)
            for legacy_path in legacy_paths:
                new_path = self._legacy_adapter.translate_legacy_path(legacy_path)
                if new_path:
                    if prefix is None or new_path.startswith(prefix):
                        paths.add(new_path)
        
        return paths
    
    def get_scope(self) -> ConfigScope:
        """
        Get the provider scope.
        
        Returns:
            The provider scope.
        """
        return self._new_provider.get_scope()
    
    def load(self) -> bool:
        """
        Load the configuration data.
        
        Returns:
            True if the data was loaded successfully, False otherwise.
        """
        success = True
        
        # Load the new system
        if not self._new_provider.load():
            success = False
            self._logger.error("Failed to load new provider")
        
        # Load the legacy system
        if not self._legacy_adapter.load_legacy():
            success = False
            self._logger.error("Failed to load legacy adapter")
        
        return success
    
    def save(self) -> bool:
        """
        Save the configuration data.
        
        Returns:
            True if the data was saved successfully, False otherwise.
        """
        success = True
        
        # Save the new system
        if self._write_to_new:
            if not self._new_provider.save():
                success = False
                self._logger.error("Failed to save new provider")
        
        # Save the legacy system
        if self._write_to_legacy:
            if not self._legacy_adapter.save_legacy():
                success = False
                self._logger.error("Failed to save legacy adapter")
        
        return success
    
    def clear(self) -> bool:
        """
        Clear the configuration data.
        
        Returns:
            True if the data was cleared successfully, False otherwise.
        """
        success = True
        
        # Clear the new system
        if self._write_to_new:
            if not self._new_provider.clear():
                success = False
                self._logger.error("Failed to clear new provider")
        
        # We don't clear the legacy system to avoid data loss
        
        return success
    
    def migrate_all_to_new(self) -> bool:
        """
        Migrate all values from the legacy system to the new system.
        
        Returns:
            True if the migration was successful, False otherwise.
        """
        if not self._write_to_new:
            self._logger.warning("Cannot migrate to new system when write_to_new is disabled")
            return False
        
        try:
            # Get all migrated values
            migrated_values = self._legacy_adapter.migrate_all()
            
            # Set all values in the new system
            for path, value in migrated_values.items():
                if not self._new_provider.set_value(path, value):
                    self._logger.error(f"Failed to set migrated value for path '{path}'")
            
            # Save the new system
            if not self._new_provider.save():
                self._logger.error("Failed to save new provider after migration")
                return False
            
            return True
        except Exception as e:
            self._logger.error(f"Error migrating to new system: {e}")
            return False
    
    def get_new_provider(self) -> ConfigProvider:
        """
        Get the new configuration provider.
        
        Returns:
            The new configuration provider.
        """
        return self._new_provider
    
    def get_legacy_adapter(self) -> LegacyConfigAdapter:
        """
        Get the legacy configuration adapter.
        
        Returns:
            The legacy configuration adapter.
        """
        return self._legacy_adapter
