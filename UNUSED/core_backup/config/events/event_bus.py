"""
Event bus for configuration changes.

This module provides an event bus implementation for handling configuration
change events and notifying observers when configuration values change.
"""

from typing import Dict, List, Any, Callable
import threading
from collections import defaultdict

from core_v2.config.interfaces import ConfigPath, ConfigValue, ConfigChangeCallback


class ConfigEventBus:
    """
    Event bus for configuration change events.
    
    This class manages subscriptions to configuration change events and
    dispatches events to subscribers when configuration values change.
    """
    
    def __init__(self):
        """Initialize the configuration event bus."""
        self._subscribers: Dict[ConfigPath, List[ConfigChangeCallback]] = defaultdict(list)
        self._wildcard_subscribers: List[ConfigChangeCallback] = []
        self._lock = threading.RLock()
    
    def subscribe(self, path: ConfigPath, callback: ConfigChangeCallback) -> None:
        """
        Subscribe to changes in a configuration value.
        
        Args:
            path: The path to the configuration value. Use "*" to subscribe to all changes.
            callback: The callback to call when the value changes.
        """
        with self._lock:
            if path == "*":
                if callback not in self._wildcard_subscribers:
                    self._wildcard_subscribers.append(callback)
            else:
                if callback not in self._subscribers[path]:
                    self._subscribers[path].append(callback)
    
    def unsubscribe(self, path: ConfigPath, callback: ConfigChangeCallback) -> None:
        """
        Unsubscribe from changes in a configuration value.
        
        Args:
            path: The path to the configuration value. Use "*" to unsubscribe from all changes.
            callback: The callback to unsubscribe.
        """
        with self._lock:
            if path == "*":
                if callback in self._wildcard_subscribers:
                    self._wildcard_subscribers.remove(callback)
            else:
                if path in self._subscribers and callback in self._subscribers[path]:
                    self._subscribers[path].remove(callback)
                    if not self._subscribers[path]:
                        del self._subscribers[path]
    
    def publish(self, path: ConfigPath, value: ConfigValue) -> None:
        """
        Publish a configuration change event.
        
        Args:
            path: The path to the configuration value that changed.
            value: The new value of the configuration.
        """
        # Make a copy of the subscribers to avoid modification during iteration
        path_subscribers = []
        wildcard_subscribers = []
        
        with self._lock:
            # Get direct path subscribers
            if path in self._subscribers:
                path_subscribers = list(self._subscribers[path])
            
            # Get parent path subscribers (for hierarchical paths)
            parts = path.split('.')
            for i in range(1, len(parts)):
                parent_path = '.'.join(parts[:-i])
                if parent_path in self._subscribers:
                    path_subscribers.extend(self._subscribers[parent_path])
            
            # Get wildcard subscribers
            wildcard_subscribers = list(self._wildcard_subscribers)
        
        # Notify path subscribers
        for callback in path_subscribers:
            try:
                callback(path, value)
            except Exception as e:
                print(f"Error in configuration change callback: {e}")
        
        # Notify wildcard subscribers
        for callback in wildcard_subscribers:
            try:
                callback(path, value)
            except Exception as e:
                print(f"Error in configuration change callback: {e}")
