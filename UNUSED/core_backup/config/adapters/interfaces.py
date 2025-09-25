"""
Configuration adapter interfaces.

This module defines interfaces for configuration adapters that bridge
between legacy and new configuration systems.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Set, List

from core_v2.config.interfaces import ConfigPath, ConfigScope


class LegacyConfigAdapter(ABC):
    """
    Base interface for legacy configuration adapters.
    
    Legacy configuration adapters provide a bridge between legacy and new
    configuration systems, allowing for smooth migration.
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the adapter name.
        
        Returns:
            The adapter name.
        """
        pass
    
    @abstractmethod
    def get_legacy_value(self, legacy_path: str, default: Any = None) -> Any:
        """
        Get a value from the legacy configuration.
        
        Args:
            legacy_path: The legacy configuration path.
            default: The default value to return if the path does not exist.
            
        Returns:
            The configuration value, or the default value if the path does not exist.
        """
        pass
    
    @abstractmethod
    def set_legacy_value(self, legacy_path: str, value: Any) -> bool:
        """
        Set a value in the legacy configuration.
        
        Args:
            legacy_path: The legacy configuration path.
            value: The value to set.
            
        Returns:
            True if the value was set successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def delete_legacy_value(self, legacy_path: str) -> bool:
        """
        Delete a value from the legacy configuration.
        
        Args:
            legacy_path: The legacy configuration path.
            
        Returns:
            True if the value was deleted successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def has_legacy_value(self, legacy_path: str) -> bool:
        """
        Check if a legacy configuration path exists.
        
        Args:
            legacy_path: The legacy configuration path.
            
        Returns:
            True if the path exists, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_all_legacy_paths(self, prefix: Optional[str] = None) -> Set[str]:
        """
        Get all legacy configuration paths.
        
        Args:
            prefix: Optional prefix to filter paths.
            
        Returns:
            A set of legacy configuration paths.
        """
        pass
    
    @abstractmethod
    def translate_legacy_path(self, legacy_path: str) -> Optional[ConfigPath]:
        """
        Translate a legacy path to a new path.
        
        Args:
            legacy_path: The legacy configuration path.
            
        Returns:
            The new configuration path, or None if the path cannot be translated.
        """
        pass
    
    @abstractmethod
    def translate_new_path(self, new_path: ConfigPath) -> Optional[str]:
        """
        Translate a new path to a legacy path.
        
        Args:
            new_path: The new configuration path.
            
        Returns:
            The legacy configuration path, or None if the path cannot be translated.
        """
        pass
    
    @abstractmethod
    def get_path_mappings(self) -> Dict[str, ConfigPath]:
        """
        Get all path mappings from legacy to new paths.
        
        Returns:
            A dictionary mapping legacy paths to new paths.
        """
        pass
    
    @abstractmethod
    def migrate_value(self, legacy_path: str, new_path: ConfigPath) -> Any:
        """
        Migrate a value from legacy to new configuration.
        
        Args:
            legacy_path: The legacy configuration path.
            new_path: The new configuration path.
            
        Returns:
            The migrated value, or None if the value cannot be migrated.
        """
        pass
    
    @abstractmethod
    def migrate_all(self) -> Dict[ConfigPath, Any]:
        """
        Migrate all values from legacy to new configuration.
        
        Returns:
            A dictionary mapping new paths to migrated values.
        """
        pass
    
    @abstractmethod
    def save_legacy(self) -> bool:
        """
        Save the legacy configuration.
        
        Returns:
            True if the configuration was saved successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def load_legacy(self) -> bool:
        """
        Load the legacy configuration.
        
        Returns:
            True if the configuration was loaded successfully, False otherwise.
        """
        pass
