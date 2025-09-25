"""
Configuration plugin registry.

This module provides a registry for configuration plugins.
"""

from typing import Any, Dict, List, Optional, Set, Type, TypeVar, Generic, Callable
import importlib
import logging
import os
import sys
import threading
import pkgutil
import inspect

from core_v2.config.plugins.interfaces import (
    ConfigPlugin, SchemaPlugin, ValidatorPlugin, 
    ProviderPlugin, UIPlugin, PluginHookRegistry
)


class PluginRegistry:
    """
    Registry for configuration plugins.
    
    This class provides a centralized way to register and access configuration plugins.
    """
    
    def __init__(self):
        """Initialize the plugin registry."""
        self._plugins: Dict[str, ConfigPlugin] = {}
        self._schema_plugins: Dict[str, SchemaPlugin] = {}
        self._validator_plugins: Dict[str, ValidatorPlugin] = {}
        self._provider_plugins: Dict[str, ProviderPlugin] = {}
        self._ui_plugins: Dict[str, UIPlugin] = {}
        self._lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        self._hook_registry = PluginHookRegistry()
    
    def register_plugin(self, plugin: ConfigPlugin) -> bool:
        """
        Register a plugin.
        
        Args:
            plugin: The plugin to register.
            
        Returns:
            True if the plugin was registered successfully, False otherwise.
        """
        with self._lock:
            name = plugin.get_name()
            
            # Check if the plugin is already registered
            if name in self._plugins:
                self._logger.warning(f"Plugin '{name}' is already registered")
                return False
            
            # Initialize the plugin
            if not plugin.initialize():
                self._logger.error(f"Failed to initialize plugin '{name}'")
                return False
            
            # Register the plugin
            self._plugins[name] = plugin
            
            # Register the plugin in the appropriate category
            if isinstance(plugin, SchemaPlugin):
                self._schema_plugins[name] = plugin
            
            if isinstance(plugin, ValidatorPlugin):
                self._validator_plugins[name] = plugin
            
            if isinstance(plugin, ProviderPlugin):
                self._provider_plugins[name] = plugin
            
            if isinstance(plugin, UIPlugin):
                self._ui_plugins[name] = plugin
            
            self._logger.info(f"Registered plugin '{name}' (version {plugin.get_version()})")
            
            return True
    
    def unregister_plugin(self, name: str) -> bool:
        """
        Unregister a plugin.
        
        Args:
            name: The plugin name.
            
        Returns:
            True if the plugin was unregistered successfully, False otherwise.
        """
        with self._lock:
            # Check if the plugin is registered
            if name not in self._plugins:
                self._logger.warning(f"Plugin '{name}' is not registered")
                return False
            
            # Get the plugin
            plugin = self._plugins[name]
            
            # Shutdown the plugin
            if not plugin.shutdown():
                self._logger.error(f"Failed to shutdown plugin '{name}'")
                return False
            
            # Unregister the plugin
            del self._plugins[name]
            
            # Unregister the plugin from the appropriate category
            if name in self._schema_plugins:
                del self._schema_plugins[name]
            
            if name in self._validator_plugins:
                del self._validator_plugins[name]
            
            if name in self._provider_plugins:
                del self._provider_plugins[name]
            
            if name in self._ui_plugins:
                del self._ui_plugins[name]
            
            self._logger.info(f"Unregistered plugin '{name}'")
            
            return True
    
    def get_plugin(self, name: str) -> Optional[ConfigPlugin]:
        """
        Get a plugin by name.
        
        Args:
            name: The plugin name.
            
        Returns:
            The plugin, or None if the plugin is not registered.
        """
        with self._lock:
            return self._plugins.get(name)
    
    def get_all_plugins(self) -> List[ConfigPlugin]:
        """
        Get all registered plugins.
        
        Returns:
            A list of all registered plugins.
        """
        with self._lock:
            return list(self._plugins.values())
    
    def get_schema_plugins(self) -> List[SchemaPlugin]:
        """
        Get all registered schema plugins.
        
        Returns:
            A list of all registered schema plugins.
        """
        with self._lock:
            return list(self._schema_plugins.values())
    
    def get_validator_plugins(self) -> List[ValidatorPlugin]:
        """
        Get all registered validator plugins.
        
        Returns:
            A list of all registered validator plugins.
        """
        with self._lock:
            return list(self._validator_plugins.values())
    
    def get_provider_plugins(self) -> List[ProviderPlugin]:
        """
        Get all registered provider plugins.
        
        Returns:
            A list of all registered provider plugins.
        """
        with self._lock:
            return list(self._provider_plugins.values())
    
    def get_ui_plugins(self) -> List[UIPlugin]:
        """
        Get all registered UI plugins.
        
        Returns:
            A list of all registered UI plugins.
        """
        with self._lock:
            return list(self._ui_plugins.values())
    
    def get_hook_registry(self) -> PluginHookRegistry:
        """
        Get the plugin hook registry.
        
        Returns:
            The plugin hook registry.
        """
        return self._hook_registry
    
    def discover_plugins(self, plugin_dirs: List[str]) -> int:
        """
        Discover and register plugins from the specified directories.
        
        Args:
            plugin_dirs: List of directories to search for plugins.
            
        Returns:
            The number of plugins registered.
        """
        count = 0
        
        for plugin_dir in plugin_dirs:
            # Check if the directory exists
            if not os.path.isdir(plugin_dir):
                self._logger.warning(f"Plugin directory '{plugin_dir}' does not exist")
                continue
            
            # Add the directory to the Python path
            if plugin_dir not in sys.path:
                sys.path.append(plugin_dir)
            
            # Discover plugins
            for _, name, is_pkg in pkgutil.iter_modules([plugin_dir]):
                if not is_pkg:
                    continue
                
                try:
                    # Import the module
                    module = importlib.import_module(name)
                    
                    # Find plugin classes
                    for _, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, ConfigPlugin) and 
                            obj is not ConfigPlugin and 
                            obj is not SchemaPlugin and 
                            obj is not ValidatorPlugin and 
                            obj is not ProviderPlugin and 
                            obj is not UIPlugin
                        ):
                            # Create an instance of the plugin
                            plugin = obj()
                            
                            # Register the plugin
                            if self.register_plugin(plugin):
                                count += 1
                except Exception as e:
                    self._logger.error(f"Failed to load plugin module '{name}': {e}")
        
        return count
    
    def initialize(self) -> bool:
        """
        Initialize the plugin registry.
        
        Returns:
            True if the registry was initialized successfully, False otherwise.
        """
        with self._lock:
            # Run startup hooks
            self._hook_registry.run_startup_hooks()
            
            return True
    
    def shutdown(self) -> bool:
        """
        Shutdown the plugin registry.
        
        Returns:
            True if the registry was shut down successfully, False otherwise.
        """
        with self._lock:
            # Run shutdown hooks
            self._hook_registry.run_shutdown_hooks()
            
            # Unregister all plugins
            for name in list(self._plugins.keys()):
                self.unregister_plugin(name)
            
            return True


# Singleton instance of the plugin registry
_plugin_registry = PluginRegistry()

def get_plugin_registry() -> PluginRegistry:
    """
    Get the plugin registry singleton instance.
    
    Returns:
        The plugin registry.
    """
    return _plugin_registry
