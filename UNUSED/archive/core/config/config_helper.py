"""
ConfigHelper: Provides easy access to configuration values with dot notation.
"""
from typing import Dict, Any, Optional, List, Union
import os
from pathlib import Path

class ConfigHelper:
    """
    Helper class for accessing configuration values with dot notation.
    
    Example usage:
    ```python
    # Initialize with a configuration dict
    config = ConfigHelper(user_config)
    
    # Access values with dot notation
    email_enabled = config.alert_system.providers.email.enabled
    
    # Access values with get() method (with default value)
    check_interval = config.get("monitoring.check_interval", 30)
    
    # Set values with dot notation
    config.alert_system.cooldown_period = 30
    
    # Get the underlying dict
    config_dict = config.to_dict()
    ```
    """
    
    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize with a configuration dictionary.
        
        Args:
            config_dict: Configuration dictionary
        """
        self._config = config_dict
        
    def __getattr__(self, name: str) -> Any:
        """
        Get a configuration value by attribute name.
        
        Args:
            name: Attribute name
            
        Returns:
            Configuration value, or ConfigHelper if the value is a dict
            
        Raises:
            AttributeError: If the attribute doesn't exist
        """
        if name not in self._config:
            raise AttributeError(f"Configuration has no attribute '{name}'")
            
        value = self._config[name]
        if isinstance(value, dict):
            return ConfigHelper(value)
        return value
        
    def __setattr__(self, name: str, value: Any) -> None:
        """
        Set a configuration value by attribute name.
        
        Args:
            name: Attribute name
            value: Value to set
        """
        if name == "_config":
            super().__setattr__(name, value)
        else:
            self._config[name] = value
            
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value by path.
        
        Args:
            path: Path to the configuration value (e.g., "alert_system.providers.email.enabled")
            default: Default value to return if the path doesn't exist
            
        Returns:
            Configuration value, or default if the path doesn't exist
        """
        parts = path.split(".")
        current = self._config
        
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
            
        return current
        
    def set(self, path: str, value: Any) -> None:
        """
        Set a configuration value by path.
        
        Args:
            path: Path to the configuration value (e.g., "alert_system.providers.email.enabled")
            value: Value to set
        """
        parts = path.split(".")
        current = self._config
        
        # Navigate to the parent of the target
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
            
        # Set the value
        current[parts[-1]] = value
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Get the underlying configuration dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self._config
        
    def __contains__(self, name: str) -> bool:
        """
        Check if a configuration value exists.
        
        Args:
            name: Attribute name
            
        Returns:
            True if the attribute exists, False otherwise
        """
        return name in self._config
        
    def __repr__(self) -> str:
        """
        Get a string representation of the configuration.
        
        Returns:
            String representation
        """
        return f"ConfigHelper({self._config})"
