"""
Core interfaces for the configuration system.

This module defines the interfaces that form the foundation of the configuration
system. These interfaces provide a contract for how configuration components
interact with each other and with the rest of the application.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Type, Union, Callable, TypeVar, Generic, Set

# Type aliases
ConfigPath = str  # Dot-notation path to a configuration value (e.g., "alert_system.providers.email.enabled")
ConfigValue = Any  # Any valid configuration value (str, int, bool, list, dict, etc.)
ConfigChangeCallback = Callable[[ConfigPath, ConfigValue], None]  # Callback for configuration changes


class ConfigScope(Enum):
    """Configuration scope.
    
    Defines the scope of a configuration provider, which determines where
    configuration values are stored and who can access them.
    """
    
    SYSTEM = auto()  # System-wide configuration, applies to all users
    USER = auto()    # User-specific configuration
    SESSION = auto() # Session-specific configuration, temporary for current session
    MEMORY = auto()  # In-memory configuration, not persisted

# Generic type for configuration schemas
T = TypeVar('T')


class ConfigObserver(ABC):
    """Interface for objects that observe configuration changes."""
    
    @abstractmethod
    def on_config_changed(self, path: ConfigPath, value: ConfigValue) -> None:
        """
        Called when a configuration value changes.
        
        Args:
            path: The path to the configuration value that changed.
            value: The new value of the configuration.
        """
        pass


class ConfigProvider(ABC):
    """Interface for configuration storage providers."""
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of the provider.
        
        Returns:
            The name of the provider.
        """
        pass
    
    @abstractmethod
    def get_scope(self) -> ConfigScope:
        """
        Get the scope of the provider.
        
        Returns:
            The scope of the provider.
        """
        pass
    
    @abstractmethod
    def load(self) -> bool:
        """
        Load configuration from the provider.
        
        Returns:
            True if the load was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def save(self) -> bool:
        """
        Save configuration to the provider.
        
        Returns:
            True if the save was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_value(self, path: ConfigPath, default: Any = None) -> Any:
        """
        Get a configuration value by path.
        
        Args:
            path: The path to the configuration value.
            default: The default value to return if the path doesn't exist.
            
        Returns:
            The configuration value, or the default if not found.
        """
        pass
    
    @abstractmethod
    def set_value(self, path: ConfigPath, value: Any) -> bool:
        """
        Set a configuration value by path.
        
        Args:
            path: The path to the configuration value.
            value: The value to set.
            
        Returns:
            True if the value was set successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def delete_value(self, path: ConfigPath) -> bool:
        """
        Delete a configuration value by path.
        
        Args:
            path: The path to the configuration value.
            
        Returns:
            True if the value was deleted successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def has_value(self, path: ConfigPath) -> bool:
        """
        Check if a configuration path exists.
        
        Args:
            path: The path to check.
            
        Returns:
            True if the path exists, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_all_paths(self, prefix: Optional[str] = None) -> Set[ConfigPath]:
        """
        Get all configuration paths.
        
        Args:
            prefix: Optional prefix to filter paths.
            
        Returns:
            A set of configuration paths.
        """
        pass
        
    @abstractmethod
    def clear(self) -> bool:
        """
        Clear all configuration values.
        
        Returns:
            True if the configuration was cleared successfully, False otherwise.
        """
        pass


class ConfigValidator(ABC):
    """Interface for configuration validators."""
    
    @abstractmethod
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a configuration value.
        
        Args:
            value: The value to validate.
            
        Returns:
            A tuple of (is_valid, error_message). If is_valid is False,
            error_message contains a description of the validation error.
        """
        pass


class ConfigSchema(ABC, Generic[T]):
    """Interface for configuration schemas."""
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of the schema.
        
        Returns:
            The name of the schema.
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        Get the description of the schema.
        
        Returns:
            The description of the schema.
        """
        pass
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> tuple[bool, Dict[str, str]]:
        """
        Validate a configuration against this schema.
        
        Args:
            config: The configuration to validate.
            
        Returns:
            A tuple of (is_valid, error_dict). If is_valid is False,
            error_dict contains paths and error messages for invalid values.
        """
        pass
    
    @abstractmethod
    def get_defaults(self) -> Dict[str, Any]:
        """
        Get the default values for this schema.
        
        Returns:
            A dictionary of default values.
        """
        pass
    
    @abstractmethod
    def create_instance(self, config: Dict[str, Any]) -> T:
        """
        Create a typed instance from a configuration dictionary.
        
        Args:
            config: The configuration dictionary.
            
        Returns:
            A typed instance representing the configuration.
        """
        pass


class ConfigurationManager(ABC):
    """Interface for the central configuration manager."""
    
    @abstractmethod
    def register_provider(self, name: str, provider: ConfigProvider) -> None:
        """
        Register a configuration provider.
        
        Args:
            name: The name of the provider.
            provider: The provider instance.
        """
        pass
    
    @abstractmethod
    def register_schema(self, schema: ConfigSchema) -> None:
        """
        Register a configuration schema.
        
        Args:
            schema: The schema to register.
        """
        pass
    
    @abstractmethod
    def get_value(self, path: ConfigPath, default: Any = None) -> Any:
        """
        Get a configuration value by path.
        
        Args:
            path: The path to the configuration value.
            default: The default value to return if the path doesn't exist.
            
        Returns:
            The configuration value, or the default if not found.
        """
        pass
    
    @abstractmethod
    def set_value(self, path: ConfigPath, value: Any) -> bool:
        """
        Set a configuration value by path.
        
        Args:
            path: The path to the configuration value.
            value: The value to set.
            
        Returns:
            True if the value was set successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def subscribe(self, path: ConfigPath, callback: ConfigChangeCallback) -> None:
        """
        Subscribe to changes in a configuration value.
        
        Args:
            path: The path to the configuration value.
            callback: The callback to call when the value changes.
        """
        pass
    
    @abstractmethod
    def unsubscribe(self, path: ConfigPath, callback: ConfigChangeCallback) -> None:
        """
        Unsubscribe from changes in a configuration value.
        
        Args:
            path: The path to the configuration value.
            callback: The callback to unsubscribe.
        """
        pass
    
    @abstractmethod
    def save(self) -> bool:
        """
        Save all configuration changes.
        
        Returns:
            True if all changes were saved successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def reload(self) -> bool:
        """
        Reload configuration from all providers.
        
        Returns:
            True if the configuration was reloaded successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_section(self, schema_type: Type[T]) -> Optional[T]:
        """
        Get a typed configuration section.
        
        Args:
            schema_type: The type of the schema to get.
            
        Returns:
            A typed configuration section, or None if not found.
        """
        pass
