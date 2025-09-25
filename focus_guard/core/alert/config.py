"""
Configuration interface for the alert system.

This module provides interfaces and utilities for integrating the alert system
with the configuration management framework.
"""

import logging
from typing import Dict, Any, Optional, List, Callable, Set, Type

from focus_guard.core.config.interfaces import ConfigProvider, ConfigurationManager
from focus_guard.core.alert.models import AlertLevel

# Configure logging
logger = logging.getLogger(__name__)


class AlertConfigKeys:
    """Constants for alert system configuration keys."""
    
    # Root keys
    ALERTS_ROOT = "alerts"
    PROVIDERS_ROOT = "providers"
    PLATFORM_ROOT = "platform"
    
    # General settings
    ENABLED = "enabled"
    HISTORY_SIZE = "history_size"
    ALERT_HISTORY_MAX_SIZE = "alert_history_max_size"
    COOLDOWN_PERIOD = "cooldown_period"
    ALERT_COOLDOWN_PERIOD = "cooldown_period"  # Alias for COOLDOWN_PERIOD for test compatibility
    ALERT_PROVIDERS_ENABLED = "providers_enabled"  # Whether all providers are enabled
    ALERT_PROVIDERS_DEFAULT_CONFIG = "providers_default_config"  # Default configuration for providers
    DEFAULT_LEVEL = "default_level"
    
    # Provider-specific keys
    POPUP_PROVIDER = "popup"
    SOUND_PROVIDER = "sound"
    BLOCKING_PROVIDER = "blocking"
    NOTIFICATION_PROVIDER = "notification"
    EMAIL_PROVIDER = "email"
    WEBHOOK_PROVIDER = "webhook"
    
    # Platform-specific keys
    WINDOWS_PLATFORM = "windows"
    MACOS_PLATFORM = "macos"
    LINUX_PLATFORM = "linux"


class AlertConfigManager:
    """
    Configuration manager for the alert system.
    
    This class provides methods for accessing and updating alert system
    configuration using the configuration management framework.
    """
    
    # Default values
    DEFAULT_MAX_HISTORY_SIZE = 100
    DEFAULT_COOLDOWN_PERIOD = 60
    
    def __init__(self, config_manager: ConfigurationManager):
        """
        Initialize with a configuration manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.subscribers: Dict[str, List[Callable[[str, Any], None]]] = {}
        self._register_subscribers()
    
    def _register_subscribers(self) -> None:
        """Register subscribers for alert configuration changes."""
        # Register for changes to the entire alerts section
        self.config_manager.subscribe(
            AlertConfigKeys.ALERTS_ROOT,
            self._on_alerts_config_changed
        )
    
    def _on_alerts_config_changed(self, key: str, value: Any) -> None:
        """
        Handle changes to alert configuration.
        
        Args:
            key: Configuration key that changed
            value: New configuration value
        """
        logger.debug(f"Alert configuration changed: {key}")
        
        # Notify subscribers for this specific key
        if key in self.subscribers:
            for callback in self.subscribers[key]:
                try:
                    callback(key, value)
                except Exception as e:
                    logger.error(f"Error in alert config subscriber: {e}", exc_info=True)
    
    def subscribe(self, key: str, callback: Callable[[str, Any], None]) -> None:
        """
        Subscribe to changes in a specific alert configuration key.
        
        Args:
            key: Configuration key to subscribe to
            callback: Function to call when the configuration changes
        """
        if key not in self.subscribers:
            self.subscribers[key] = []
        self.subscribers[key].append(callback)
        
    def subscribe_to_config_changes(self, callback: Callable[[str, Any], None]) -> None:
        """
        Subscribe to all alert configuration changes.
        
        Args:
            callback: Function to call when any alert configuration changes
        """
        # Subscribe to all relevant configuration keys
        keys = [
            AlertConfigKeys.ALERT_HISTORY_MAX_SIZE,
            AlertConfigKeys.ALERT_COOLDOWN_PERIOD,
            AlertConfigKeys.ALERT_PROVIDERS_ENABLED,
            AlertConfigKeys.ALERT_PROVIDERS_DEFAULT_CONFIG
        ]
        
        # Subscribe to each key using the config manager's subscribe method
        for key in keys:
            # Pass the callback directly to the config manager
            self.config_manager.subscribe(key, callback)
    
    def unsubscribe(self, key: str, callback: Callable[[str, Any], None]) -> bool:
        """
        Unsubscribe from changes in a specific alert configuration key.
        
        Args:
            key: Configuration key to unsubscribe from
            callback: Function to remove from subscribers
            
        Returns:
            bool: True if the callback was removed
        """
        if key in self.subscribers and callback in self.subscribers[key]:
            self.subscribers[key].remove(callback)
            return True
        return False
    
    def get_alert_system_config(self) -> Dict[str, Any]:
        """
        Get the complete alert system configuration.
        
        Returns:
            Dict[str, Any]: Alert system configuration
        """
        # Handle different config manager interfaces
        if hasattr(self.config_manager, 'get_value'):
            return self.config_manager.get_value(AlertConfigKeys.ALERTS_ROOT, {})
        elif hasattr(self.config_manager, 'get_config_value'):
            return self.config_manager.get_config_value(AlertConfigKeys.ALERTS_ROOT, {})
        else:
            return self.config_manager.get(AlertConfigKeys.ALERTS_ROOT, {})
    
    def get_provider_config(self, provider_name: str, default_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get configuration for a specific provider.
        
        Args:
            provider_name: Name of the provider
            default_config: Default configuration to use if not found
            
        Returns:
            Dict[str, Any]: Provider configuration
        """
        providers_config = self.config_manager.get(
            AlertConfigKeys.ALERT_PROVIDERS_DEFAULT_CONFIG,
            {}
        )
        
        provider_config = providers_config.get(provider_name, {})
        
        # Merge with default config if provided
        if default_config:
            return {**default_config, **provider_config}
        return provider_config
    
    def get_platform_config(self, platform_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific platform.
        
        Args:
            platform_name: Name of the platform
            
        Returns:
            Dict[str, Any]: Platform configuration
        """
        # Handle different config manager interfaces
        key = f"{AlertConfigKeys.ALERTS_ROOT}.{AlertConfigKeys.PLATFORM_ROOT}"
        if hasattr(self.config_manager, 'get_value'):
            platform_config = self.config_manager.get_value(key, {})
        elif hasattr(self.config_manager, 'get_config_value'):
            platform_config = self.config_manager.get_config_value(key, {})
        else:
            platform_config = self.config_manager.get(key, {})
        return platform_config.get(platform_name, {})
    
    def update_provider_config(self, provider_name: str, config: Dict[str, Any]) -> None:
        """
        Update configuration for a specific provider.
        
        Args:
            provider_name: Name of the provider
            config: New provider configuration
        """
        # Use the implementation from set_provider_config
        self.set_provider_config(provider_name, config)
        
    # Alias for update_provider_config to maintain compatibility with tests
    def set_provider_config(self, provider_name: str, config: Dict[str, Any]) -> None:
        """
        Set configuration for a specific provider. Alias for update_provider_config.
        
        Args:
            provider_name: Name of the provider
            config: New provider configuration
        """
        # Handle different config manager interfaces
        if hasattr(self.config_manager, 'get_value'):
            providers_config = self.config_manager.get_value(AlertConfigKeys.ALERT_PROVIDERS_DEFAULT_CONFIG, {})
        elif hasattr(self.config_manager, 'get_config_value'):
            providers_config = self.config_manager.get_config_value(AlertConfigKeys.ALERT_PROVIDERS_DEFAULT_CONFIG, {})
        else:
            providers_config = self.config_manager.get(AlertConfigKeys.ALERT_PROVIDERS_DEFAULT_CONFIG, {})
        
        # Create a copy to avoid modifying the original
        updated_config = providers_config.copy() if providers_config else {}
        updated_config[provider_name] = config
        
        # Update the configuration - handle different config manager interfaces
        if hasattr(self.config_manager, 'set_config_value'):
            self.config_manager.set_config_value(AlertConfigKeys.ALERT_PROVIDERS_DEFAULT_CONFIG, updated_config)
        elif hasattr(self.config_manager, 'set_value'):
            self.config_manager.set_value(AlertConfigKeys.ALERT_PROVIDERS_DEFAULT_CONFIG, updated_config)
        else:
            self.config_manager.set(AlertConfigKeys.ALERT_PROVIDERS_DEFAULT_CONFIG, updated_config)
    
    def update_platform_config(self, platform_name: str, config: Dict[str, Any]) -> None:
        """
        Update configuration for a specific platform.
        
        Args:
            platform_name: Name of the platform
            config: New platform configuration
        """
        config_path = f"{AlertConfigKeys.ALERTS_ROOT}.{AlertConfigKeys.PLATFORM_ROOT}.{platform_name}"
        self.config_manager.set_config_value(config_path, config)
    
    def is_provider_enabled(self, provider_name: str) -> bool:
        """
        Check if a provider is enabled.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            bool: True if the provider is enabled
        """
        # First check the providers_enabled dictionary
        # Handle different config manager interfaces
        if hasattr(self.config_manager, 'get_value'):
            providers_enabled = self.config_manager.get_value(AlertConfigKeys.ALERT_PROVIDERS_ENABLED, {})
        elif hasattr(self.config_manager, 'get_config_value'):
            providers_enabled = self.config_manager.get_config_value(AlertConfigKeys.ALERT_PROVIDERS_ENABLED, {})
        else:
            providers_enabled = self.config_manager.get(AlertConfigKeys.ALERT_PROVIDERS_ENABLED, {})
        
        # If the provider is explicitly set in providers_enabled, return that value
        if provider_name in providers_enabled:
            return bool(providers_enabled[provider_name])
            
        # Get the default config for all providers
        # Handle different config manager interfaces
        if hasattr(self.config_manager, 'get_value'):
            default_config = self.config_manager.get_value(AlertConfigKeys.ALERT_PROVIDERS_DEFAULT_CONFIG, {})
        elif hasattr(self.config_manager, 'get_config_value'):
            default_config = self.config_manager.get_config_value(AlertConfigKeys.ALERT_PROVIDERS_DEFAULT_CONFIG, {})
        else:
            default_config = self.config_manager.get(AlertConfigKeys.ALERT_PROVIDERS_DEFAULT_CONFIG, {})
        
        # If the provider is not in the default config, it doesn't exist
        if provider_name not in default_config:
            return False
            
        # Otherwise, check the provider's own config
        provider_config = default_config[provider_name]
        return bool(provider_config.get(AlertConfigKeys.ENABLED, True))
        
    def get_alert_history_max_size(self) -> int:
        """
        Get the maximum size of the alert history.
        
        Returns:
            int: Maximum size of the alert history, or default if invalid
        """
        # Handle different config manager interfaces
        if hasattr(self.config_manager, 'get_value'):
            size = self.config_manager.get_value(AlertConfigKeys.ALERT_HISTORY_MAX_SIZE, AlertConfigManager.DEFAULT_MAX_HISTORY_SIZE)
        elif hasattr(self.config_manager, 'get_config_value'):
            size = self.config_manager.get_config_value(AlertConfigKeys.ALERT_HISTORY_MAX_SIZE, AlertConfigManager.DEFAULT_MAX_HISTORY_SIZE)
        else:
            size = self.config_manager.get(AlertConfigKeys.ALERT_HISTORY_MAX_SIZE, AlertConfigManager.DEFAULT_MAX_HISTORY_SIZE)
        
        # Validate the size is positive, return default if invalid
        if not isinstance(size, int) or size <= 0:
            return AlertConfigManager.DEFAULT_MAX_HISTORY_SIZE
            
        return size
    
    def set_provider_enabled(self, provider_name: str, enabled: bool) -> None:
        """
        Enable or disable a provider.
        
        Args:
            provider_name: Name of the provider
            enabled: Whether the provider should be enabled
        """
        provider_config = self.get_provider_config(provider_name)
        provider_config[AlertConfigKeys.ENABLED] = enabled
        self.update_provider_config(provider_name, provider_config)
    
    def get_default_alert_level(self) -> AlertLevel:
        """
        Get the default alert level.
        
        Returns:
            AlertLevel: Default alert level
        """
        alert_config = self.get_alert_system_config()
        level_str = alert_config.get(AlertConfigKeys.DEFAULT_LEVEL, AlertLevel.INFO.name)
        return AlertLevel[level_str]
        
    def get_cooldown_period(self) -> int:
        """
        Get the alert cooldown period.
        
        Returns:
            int: Cooldown period in seconds, or default if invalid
        """
        # First try direct key (for test compatibility)
        # Handle different config manager interfaces
        if hasattr(self.config_manager, 'get_value'):
            value = self.config_manager.get_value(AlertConfigKeys.COOLDOWN_PERIOD, None)
        elif hasattr(self.config_manager, 'get_config_value'):
            value = self.config_manager.get_config_value(AlertConfigKeys.COOLDOWN_PERIOD, None)
        else:
            value = self.config_manager.get(AlertConfigKeys.COOLDOWN_PERIOD, None)
        
        # If not found, try with alerts root prefix
        if value is None:
            key = f"{AlertConfigKeys.ALERTS_ROOT}.{AlertConfigKeys.COOLDOWN_PERIOD}"
            if hasattr(self.config_manager, 'get_value'):
                value = self.config_manager.get_value(key, AlertConfigManager.DEFAULT_COOLDOWN_PERIOD)
            elif hasattr(self.config_manager, 'get_config_value'):
                value = self.config_manager.get_config_value(key, AlertConfigManager.DEFAULT_COOLDOWN_PERIOD)
            else:
                value = self.config_manager.get(key, AlertConfigManager.DEFAULT_COOLDOWN_PERIOD)
        
        # Validate the cooldown period is non-negative, return default if invalid
        if not isinstance(value, (int, float)) or value < 0:
            return AlertConfigManager.DEFAULT_COOLDOWN_PERIOD
            
        return int(value)
        
    # Alias for get_cooldown_period to maintain compatibility with tests
    def get_alert_cooldown_period(self) -> int:
        """
        Alias for get_cooldown_period to maintain compatibility with tests.
        
        Returns:
            int: Cooldown period in seconds
        """
        return self.get_cooldown_period()
    
    def get_history_size(self) -> int:
        """
        Get the maximum alert history size.
        
        Returns:
            int: Maximum number of alerts to keep in history
        """
        key = f"{AlertConfigKeys.ALERTS_ROOT}.{AlertConfigKeys.HISTORY_SIZE}"
        if hasattr(self.config_manager, 'get_value'):
            return self.config_manager.get_value(key, 100)
        elif hasattr(self.config_manager, 'get_config_value'):
            return self.config_manager.get_config_value(key, 100)
        else:
            return self.config_manager.get(key, 100)
        
    def get_history_file(self) -> str:
        """
        Get the path to the alert history file.
        
        Returns:
            str: Path to the alert history file
        """
        key = f"{AlertConfigKeys.ALERTS_ROOT}.history_file"
        if hasattr(self.config_manager, 'get_value'):
            return self.config_manager.get_value(key, None)
        elif hasattr(self.config_manager, 'get_config_value'):
            return self.config_manager.get_config_value(key, None)
        else:
            return self.config_manager.get(key, None)


def get_default_alert_config() -> Dict[str, Any]:
    """
    Get the default alert system configuration.
    
    Returns:
        Dict[str, Any]: Default configuration
    """
    return {
        AlertConfigKeys.ENABLED: True,
        AlertConfigKeys.HISTORY_SIZE: 100,
        AlertConfigKeys.COOLDOWN_PERIOD: 60,
        AlertConfigKeys.DEFAULT_LEVEL: "normal",
        AlertConfigKeys.PROVIDERS_ROOT: {
            AlertConfigKeys.POPUP_PROVIDER: {
                AlertConfigKeys.ENABLED: True,
                "popup_duration": 10,
                "overlay_on_distraction": True,
                "show_app_name": True,
                "max_popups": 3
            },
            AlertConfigKeys.SOUND_PROVIDER: {
                AlertConfigKeys.ENABLED: True,
                "volume": 0.7,
                "repeat_count": 1,
                "cooldown_period": 5
            },
            AlertConfigKeys.BLOCKING_PROVIDER: {
                AlertConfigKeys.ENABLED: True,
                "timeout": 0,
                "buttons": ["OK"],
                "default_button": 0,
                "escalation_threshold": 3,
                "min_level": "warning"
            },
            AlertConfigKeys.NOTIFICATION_PROVIDER: {
                AlertConfigKeys.ENABLED: True
            },
            AlertConfigKeys.EMAIL_PROVIDER: {
                AlertConfigKeys.ENABLED: False,
                "recipients": [],
                "min_level": "critical"
            },
            AlertConfigKeys.WEBHOOK_PROVIDER: {
                AlertConfigKeys.ENABLED: False,
                "urls": [],
                "min_level": "warning"
            }
        },
        AlertConfigKeys.PLATFORM_ROOT: {
            AlertConfigKeys.WINDOWS_PLATFORM: {
                "use_powershell": True
            },
            AlertConfigKeys.MACOS_PLATFORM: {
                "use_notification_center": True
            },
            AlertConfigKeys.LINUX_PLATFORM: {
                "use_libnotify": True
            }
        }
    }
