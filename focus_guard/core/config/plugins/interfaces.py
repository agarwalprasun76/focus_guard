"""
Configuration plugin interfaces.

This module defines interfaces for configuration system plugins.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Type, TypeVar, Generic, Callable

from focus_guard.core.config.interfaces import ConfigSchema, ConfigValidator


class ConfigPlugin(ABC):
    """
    Base interface for all configuration plugins.
    
    Configuration plugins extend the functionality of the configuration system.
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the plugin name.
        
        Returns:
            The plugin name.
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        Get the plugin description.
        
        Returns:
            The plugin description.
        """
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """
        Get the plugin version.
        
        Returns:
            The plugin version.
        """
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if the plugin was initialized successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """
        Shutdown the plugin.
        
        Returns:
            True if the plugin was shut down successfully, False otherwise.
        """
        pass


class SchemaPlugin(ConfigPlugin):
    """
    Plugin interface for custom schema types.
    
    Schema plugins provide custom schema types for the configuration system.
    """
    
    @abstractmethod
    def get_schema_types(self) -> List[Type[ConfigSchema]]:
        """
        Get the schema types provided by this plugin.
        
        Returns:
            A list of schema types.
        """
        pass


class ValidatorPlugin(ConfigPlugin):
    """
    Plugin interface for custom validators.
    
    Validator plugins provide custom validators for the configuration system.
    """
    
    @abstractmethod
    def get_validators(self) -> List[Type[ConfigValidator]]:
        """
        Get the validators provided by this plugin.
        
        Returns:
            A list of validator types.
        """
        pass


class ProviderPlugin(ConfigPlugin):
    """
    Plugin interface for custom configuration providers.
    
    Provider plugins provide custom configuration providers for the configuration system.
    """
    
    @abstractmethod
    def get_provider_types(self) -> List[str]:
        """
        Get the provider types provided by this plugin.
        
        Returns:
            A list of provider type names.
        """
        pass
    
    @abstractmethod
    def create_provider(self, provider_type: str, **kwargs) -> Any:
        """
        Create a provider instance.
        
        Args:
            provider_type: The provider type.
            **kwargs: Additional arguments for the provider.
            
        Returns:
            A provider instance.
        """
        pass


class UIPlugin(ConfigPlugin):
    """
    Plugin interface for custom UI components.
    
    UI plugins provide custom UI components for the configuration system.
    """
    
    @abstractmethod
    def get_component_types(self) -> List[str]:
        """
        Get the component types provided by this plugin.
        
        Returns:
            A list of component type names.
        """
        pass
    
    @abstractmethod
    def create_component(self, component_type: str, **kwargs) -> Any:
        """
        Create a component instance.
        
        Args:
            component_type: The component type.
            **kwargs: Additional arguments for the component.
            
        Returns:
            A component instance.
        """
        pass


# Type variable for plugin hooks
T = TypeVar('T')

# Plugin hook types
PluginHook = Callable[[], None]
PluginFilterHook = Callable[[T], T]
PluginActionHook = Callable[[T], None]


class PluginHookRegistry:
    """
    Registry for plugin hooks.
    
    Plugin hooks allow plugins to extend the functionality of the configuration system
    by registering callbacks for various events.
    """
    
    def __init__(self):
        """Initialize the plugin hook registry."""
        self._startup_hooks: List[PluginHook] = []
        self._shutdown_hooks: List[PluginHook] = []
        self._pre_load_hooks: List[PluginHook] = []
        self._post_load_hooks: List[PluginHook] = []
        self._pre_save_hooks: List[PluginHook] = []
        self._post_save_hooks: List[PluginHook] = []
        self._value_filter_hooks: List[PluginFilterHook] = []
        self._schema_filter_hooks: List[PluginFilterHook] = []
        self._validation_hooks: List[PluginActionHook] = []
    
    def register_startup_hook(self, hook: PluginHook) -> None:
        """
        Register a startup hook.
        
        Args:
            hook: The hook function.
        """
        self._startup_hooks.append(hook)
    
    def register_shutdown_hook(self, hook: PluginHook) -> None:
        """
        Register a shutdown hook.
        
        Args:
            hook: The hook function.
        """
        self._shutdown_hooks.append(hook)
    
    def register_pre_load_hook(self, hook: PluginHook) -> None:
        """
        Register a pre-load hook.
        
        Args:
            hook: The hook function.
        """
        self._pre_load_hooks.append(hook)
    
    def register_post_load_hook(self, hook: PluginHook) -> None:
        """
        Register a post-load hook.
        
        Args:
            hook: The hook function.
        """
        self._post_load_hooks.append(hook)
    
    def register_pre_save_hook(self, hook: PluginHook) -> None:
        """
        Register a pre-save hook.
        
        Args:
            hook: The hook function.
        """
        self._pre_save_hooks.append(hook)
    
    def register_post_save_hook(self, hook: PluginHook) -> None:
        """
        Register a post-save hook.
        
        Args:
            hook: The hook function.
        """
        self._post_save_hooks.append(hook)
    
    def register_value_filter_hook(self, hook: PluginFilterHook) -> None:
        """
        Register a value filter hook.
        
        Args:
            hook: The hook function.
        """
        self._value_filter_hooks.append(hook)
    
    def register_schema_filter_hook(self, hook: PluginFilterHook) -> None:
        """
        Register a schema filter hook.
        
        Args:
            hook: The hook function.
        """
        self._schema_filter_hooks.append(hook)
    
    def register_validation_hook(self, hook: PluginActionHook) -> None:
        """
        Register a validation hook.
        
        Args:
            hook: The hook function.
        """
        self._validation_hooks.append(hook)
    
    def run_startup_hooks(self) -> None:
        """Run all startup hooks."""
        for hook in self._startup_hooks:
            try:
                hook()
            except Exception as e:
                print(f"Error running startup hook: {e}")
    
    def run_shutdown_hooks(self) -> None:
        """Run all shutdown hooks."""
        for hook in self._shutdown_hooks:
            try:
                hook()
            except Exception as e:
                print(f"Error running shutdown hook: {e}")
    
    def run_pre_load_hooks(self) -> None:
        """Run all pre-load hooks."""
        for hook in self._pre_load_hooks:
            try:
                hook()
            except Exception as e:
                print(f"Error running pre-load hook: {e}")
    
    def run_post_load_hooks(self) -> None:
        """Run all post-load hooks."""
        for hook in self._post_load_hooks:
            try:
                hook()
            except Exception as e:
                print(f"Error running post-load hook: {e}")
    
    def run_pre_save_hooks(self) -> None:
        """Run all pre-save hooks."""
        for hook in self._pre_save_hooks:
            try:
                hook()
            except Exception as e:
                print(f"Error running pre-save hook: {e}")
    
    def run_post_save_hooks(self) -> None:
        """Run all post-save hooks."""
        for hook in self._post_save_hooks:
            try:
                hook()
            except Exception as e:
                print(f"Error running post-save hook: {e}")
    
    def apply_value_filters(self, value: T) -> T:
        """
        Apply all value filter hooks.
        
        Args:
            value: The value to filter.
            
        Returns:
            The filtered value.
        """
        filtered_value = value
        
        for hook in self._value_filter_hooks:
            try:
                filtered_value = hook(filtered_value)
            except Exception as e:
                print(f"Error applying value filter: {e}")
        
        return filtered_value
    
    def apply_schema_filters(self, schema: T) -> T:
        """
        Apply all schema filter hooks.
        
        Args:
            schema: The schema to filter.
            
        Returns:
            The filtered schema.
        """
        filtered_schema = schema
        
        for hook in self._schema_filter_hooks:
            try:
                filtered_schema = hook(filtered_schema)
            except Exception as e:
                print(f"Error applying schema filter: {e}")
        
        return filtered_schema
    
    def run_validation_hooks(self, value: Any) -> None:
        """
        Run all validation hooks.
        
        Args:
            value: The value to validate.
        """
        for hook in self._validation_hooks:
            try:
                hook(value)
            except Exception as e:
                print(f"Error running validation hook: {e}")
