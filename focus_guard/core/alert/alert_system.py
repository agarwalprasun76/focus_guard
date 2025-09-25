"""
Core alert system implementation.

This module provides the main AlertSystem class that integrates all alert
components and manages alert history, escalation, and cooldown.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union, Set, Type
from dataclasses import asdict

from focus_guard.core.alert.models import AlertInfo, AlertLevel, AlertHistoryEntry
from focus_guard.core.alert.providers.base import AlertProvider, CompositeAlertProvider
from focus_guard.core.alert.providers.popup import PopupAlertProvider
from focus_guard.core.alert.providers.sound import SoundAlertProvider
from focus_guard.core.alert.providers.blocking import BlockingAlertProvider
from focus_guard.core.alert.config import AlertConfigManager, AlertConfigKeys, get_default_alert_config
from focus_guard.core.config.interfaces import ConfigurationManager

# Configure logging
logger = logging.getLogger(__name__)


class AlertSystem:
    """
    Core alert system that manages providers and alert history.
    
    This class is the main entry point for the alert system. It manages
    alert providers, alert history, escalation logic, and cooldown periods.
    """
    
    def __init__(self, config_manager: Optional[ConfigurationManager] = None, history_file: Optional[str] = None):
        """
        Initialize the alert system.
        
        Args:
            config_manager: Configuration manager instance
            history_file: Path to the alert history file
        """
        self.config_manager = config_manager
        self.alert_config = None
        self.providers: Dict[str, AlertProvider] = {}
        self.composite_provider = CompositeAlertProvider()
        self.alert_history: List[AlertHistoryEntry] = []
        self.cooldown_timers: Dict[str, datetime] = {}  # app_name -> last_alert_time
        self.history_path = history_file  # Can be overridden by config
        
        # Initialize configuration
        if self.config_manager:
            self.alert_config = AlertConfigManager(config_manager)
            self._initialize_from_config()
        else:
            # Use default configuration
            self._initialize_default()
        
        # Load alert history
        self._load_history()
    
    def _initialize_from_config(self) -> None:
        """Initialize alert system from configuration."""
        # Get alert system configuration
        config = self.alert_config.get_alert_system_config()
        if not config:
            # No configuration found, initialize with defaults
            config = get_default_alert_config()
            # Handle different config manager interfaces
            if hasattr(self.config_manager, 'set_config_value'):
                self.config_manager.set_config_value(AlertConfigKeys.ALERTS_ROOT, config)
            elif hasattr(self.config_manager, 'set_value'):
                self.config_manager.set_value(AlertConfigKeys.ALERTS_ROOT, config)
            else:
                self.config_manager.set(AlertConfigKeys.ALERTS_ROOT, config)
        
        # Initialize providers
        self._initialize_providers(config.get(AlertConfigKeys.PROVIDERS_ROOT, {}))
        
        # Subscribe to configuration changes
        self.alert_config.subscribe(
            f"{AlertConfigKeys.ALERTS_ROOT}.{AlertConfigKeys.PROVIDERS_ROOT}",
            self._on_provider_config_changed
        )
        
        # Set cooldown period
        self.cooldown_period = self.alert_config.get_cooldown_period()
        
        # Set history size
        self.max_history_size = self.alert_config.get_history_size()
        
        # Set history file path only if not already set (allows tests to inject a path)
        if not hasattr(self, 'history_path') or self.history_path is None:
            history_file = self.alert_config.get_history_file()
            if history_file:
                self.history_path = history_file
            else:
                self.history_path = os.path.expanduser("~/.focus_guard/alert_history.json")
    
    def _initialize_default(self) -> None:
        """Initialize alert system with default configuration."""
        # Get default configuration
        config = get_default_alert_config()
        
        # Initialize providers
        self._initialize_providers(config.get(AlertConfigKeys.PROVIDERS_ROOT, {}))
        
        # Set cooldown period
        self.cooldown_period = config.get(AlertConfigKeys.COOLDOWN_PERIOD, 60)
        
        # Set history size
        self.max_history_size = config.get(AlertConfigKeys.HISTORY_SIZE, 100)
    
    def _initialize_providers(self, providers_config: Dict[str, Dict[str, Any]]) -> None:
        """
        Initialize alert providers from configuration.
        
        Args:
            providers_config: Provider configuration dictionary
        """
        # Clear existing providers
        self.providers = {}
        self.composite_provider = CompositeAlertProvider()
        
        # Initialize standard providers
        if AlertConfigKeys.POPUP_PROVIDER in providers_config:
            self.providers[AlertConfigKeys.POPUP_PROVIDER] = PopupAlertProvider(
                providers_config[AlertConfigKeys.POPUP_PROVIDER]
            )
        else:
            self.providers[AlertConfigKeys.POPUP_PROVIDER] = PopupAlertProvider()
        
        if AlertConfigKeys.SOUND_PROVIDER in providers_config:
            self.providers[AlertConfigKeys.SOUND_PROVIDER] = SoundAlertProvider(
                providers_config[AlertConfigKeys.SOUND_PROVIDER]
            )
        else:
            self.providers[AlertConfigKeys.SOUND_PROVIDER] = SoundAlertProvider()
        
        if AlertConfigKeys.BLOCKING_PROVIDER in providers_config:
            self.providers[AlertConfigKeys.BLOCKING_PROVIDER] = BlockingAlertProvider(
                providers_config[AlertConfigKeys.BLOCKING_PROVIDER]
            )
        else:
            self.providers[AlertConfigKeys.BLOCKING_PROVIDER] = BlockingAlertProvider()
        
        # Add all providers to composite provider
        for provider in self.providers.values():
            self.composite_provider.add_provider(provider)
    
    def _on_provider_config_changed(self, key: str, value: Any) -> None:
        """
        Handle changes to provider configuration.
        
        Args:
            key: Configuration key that changed (e.g., 'alerts.providers.popup')
            value: New configuration value (dict of provider config or specific setting)
        """
        # Extract provider name from key (e.g., 'popup' from 'alerts.providers.popup')
        provider_name = key.split('.')[-1] if '.' in key else key
        
        # If this is a specific provider's config
        if provider_name in self.providers:
            # If we got a full provider config dict
            if isinstance(value, dict):
                # Update the existing provider's config
                if 'enabled' in value:
                    self.providers[provider_name].enabled = value['enabled']
                # Update other config values
                self.providers[provider_name].update_config(value)
            # If we got just the enabled state
            elif isinstance(value, bool):
                self.providers[provider_name].enabled = value
        # If this is the entire providers config
        elif provider_name == 'providers' and isinstance(value, dict):
            # Update all providers with their new configs
            for name, config in value.items():
                if name in self.providers:
                    if isinstance(config, dict):
                        if 'enabled' in config:
                            self.providers[name].enabled = config['enabled']
                        self.providers[name].update_config(config)
    
    def alert(self, app_name: str, message: str, level: Optional[AlertLevel] = None,
              window_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send an alert.
        
        Args:
            app_name: Name of the application causing the alert
            message: Alert message
            level: Alert level
            window_info: Information about the window causing the alert
            
        Returns:
            bool: True if alert was successfully sent
        """
        # Get default level if not specified
        if level is None:
            if self.alert_config:
                level = self.alert_config.get_default_alert_level()
            else:
                level = AlertLevel.NORMAL
        
        # Create alert info
        alert_info = AlertInfo(
            app_name=app_name,
            message=message,
            level=level,
            timestamp=datetime.now(),
            window_rect=window_info.get("rect") if window_info else None,
            window_title=window_info.get("title") if window_info else None,
            window_url=window_info.get("url") if window_info else None
        )
        
        # Use the common send_alert method
        return self.send_alert(alert_info)

    def send_alert(self, alert_info: AlertInfo) -> bool:
        """
        Send an alert using AlertInfo object.
        
        This is an alias for the alert method to maintain compatibility with tests.
        
        Args:
            alert_info: Alert information object
            
        Returns:
            bool: True if alert was successfully sent
        """
        # Check cooldown period
        if not self._check_cooldown(alert_info.app_name):
            logger.debug(f"Alert for {alert_info.app_name} skipped due to cooldown period")
            return False
        
        # Record alert in history
        self._add_alert_to_history(alert_info)
        
        # Update cooldown timer
        self.cooldown_timers[alert_info.app_name] = datetime.now()
        
        # Send alert to each provider directly (to match test expectations)
        for provider in self.providers.values():
            if provider.enabled:
                provider.send_alert(alert_info)
        
        return True
    
    def _check_cooldown(self, app_name: str) -> bool:
        """
        Check if an app is in cooldown period.
        
        Args:
            app_name: Name of the application
            
        Returns:
            bool: True if not in cooldown period
        """
        current_time = datetime.now()
        
        if app_name in self.cooldown_timers:
            last_alert_time = self.cooldown_timers[app_name]
            time_since_last = (current_time - last_alert_time).total_seconds()
            
            if time_since_last < self.cooldown_period:
                return False
        
        # Update cooldown timer
        self.cooldown_timers[app_name] = current_time
        return True
    
    def _record_alert(self, alert_info: AlertInfo) -> None:
        """
        Record an alert in the history.
        
        Args:
            alert_info: Information about the alert
        """
        # Delegate to _add_alert_to_history for consistency
        self._add_alert_to_history(alert_info)
    
    def _add_alert_to_history(self, alert_info: AlertInfo) -> None:
        """
        Add an alert to history.
        
        Args:
            alert_info: Information about the alert
        """
        # Create a history entry
        entry = AlertHistoryEntry(
            alert_info=alert_info,
            timestamp=alert_info.timestamp,
            providers_used=[]
        )
        
        # Add to history
        self.alert_history.append(entry)
        
        # Trim history if needed
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size:]
            
        # Save history to disk
        self._save_history()
    
    def _save_history(self) -> None:
        """Save alert history to disk."""
        try:
            # Convert history to JSON-serializable format
            history_data = [entry.to_dict() for entry in self.alert_history]
            logger.debug(f"Saving {len(history_data)} history entries")
            
            # Get history file path from config or use default
            history_path = self.history_path
            logger.debug(f"Using history path: {history_path}")
            if not history_path:
                history_path = os.path.expanduser("~/.focus_guard/alert_history.json")
                logger.debug(f"Using default history path: {history_path}")
            
            # Ensure directory exists
            dir_path = os.path.dirname(history_path)
            logger.debug(f"Creating directory: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
            
            # Write to file
            logger.debug(f"Writing to file: {history_path}")
            with open(history_path, "w") as f:
                json.dump(history_data, f, indent=2)
            logger.debug(f"Successfully wrote history to {history_path}")
                
        except Exception as e:
            logger.error(f"Failed to save alert history: {e}", exc_info=True)
    
    def _load_history(self) -> None:
        """Load alert history from disk."""
        try:
            # Get history file path from config or use default
            history_path = self.history_path
            if not history_path:
                history_path = os.path.expanduser("~/.focus_guard/alert_history.json")
            
            if os.path.exists(history_path):
                # Read from file
                with open(history_path, "r") as f:
                    history_data = json.load(f)
                
                # Convert to AlertHistoryEntry objects
                self.alert_history = [
                    AlertHistoryEntry.from_dict(entry) for entry in history_data
                ]
                
                # Trim history if needed
                if len(self.alert_history) > self.max_history_size:
                    self.alert_history = self.alert_history[-self.max_history_size:]
                    
        except Exception as e:
            logger.error(f"Failed to load alert history: {e}", exc_info=True)
            self.alert_history = []
    
    def get_alert_history(self, limit: Optional[int] = None) -> List[AlertHistoryEntry]:
        """
        Get alert history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List[AlertHistoryEntry]: Alert history entries
        """
        if limit is None:
            return self.alert_history
        else:
            return self.alert_history[-limit:]
    
    def clear_alert_history(self) -> None:
        """Clear alert history."""
        self.alert_history = []
        self._save_history()
    
    def get_provider(self, provider_name: str) -> AlertProvider:
        """
        Get a specific provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            AlertProvider: Provider instance
            
        Raises:
            KeyError: If provider not found
        """
        if provider_name not in self.providers:
            raise KeyError(f"Provider '{provider_name}' not found")
        return self.providers[provider_name]
    
    def add_provider(self, name: str, provider: AlertProvider) -> None:
        """
        Add a provider to the alert system.
        
        Args:
            name: Provider name (must be a non-empty string)
            provider: Provider instance (cannot be None)
            
        Raises:
            ValueError: If name is empty/None or provider is None
        """
        # Validate inputs
        if not name:
            raise ValueError("Provider name cannot be empty or None")
        if provider is None:
            raise ValueError("Provider instance cannot be None")
            
        # Debug: Log the initial state of the provider
        logger.debug(f"Adding provider '{name}'. Initial enabled state: {getattr(provider, 'enabled', 'N/A')}")
        
        # If provider with this name already exists, remove it first
        if name in self.providers:
            old_provider = self.providers[name]
            logger.debug(f"Replacing existing provider '{name}'. Old enabled state: {getattr(old_provider, 'enabled', 'N/A')}")
            if hasattr(old_provider, 'cleanup'):
                old_provider.cleanup()
        
        # Add the new provider
        self.providers[name] = provider
        
        # If we have a config manager, update the provider's config
        if hasattr(self, 'alert_config'):
            # Get the provider's initial config
            initial_config = getattr(provider, 'config', {}).copy()
            logger.debug(f"Initial config from provider '{name}': {initial_config}")
            
            # Get the config from the config manager
            provider_config = self.alert_config.get_provider_config(name)
            logger.debug(f"Provider config for '{name}': {provider_config}")
            
            if provider_config:
                # Merge provider config with initial config (initial config takes precedence)
                merged_config = {**provider_config, **initial_config}
                logger.debug(f"Merged config for '{name}': {merged_config}")
                
                if hasattr(provider, 'update_config'):
                    logger.debug(f"Updating provider '{name}' with config: {merged_config}")
                    provider.update_config(merged_config)
            # If no provider config exists, use the initial config
            elif hasattr(provider, 'enabled') and initial_config:
                logger.debug(f"No provider config found for '{name}'. Using initial config: {initial_config}")
                if 'enabled' in initial_config:
                    provider.enabled = initial_config['enabled']
        
        # Debug: Log the final state of the provider
        logger.debug(f"Final enabled state for provider '{name}': {getattr(provider, 'enabled', 'N/A')}")
        
        # Rebuild the composite provider with all providers
        self.composite_provider = CompositeAlertProvider()
        for p in self.providers.values():
            self.composite_provider.add_provider(p)
        
    def enable_providers(self, enabled: bool) -> None:
        """
        Enable or disable all providers.
        
        Args:
            enabled: Whether to enable or disable providers
        """
        for provider in self.providers.values():
            provider.enabled = enabled
    
    def remove_provider(self, provider_name: str) -> bool:
        """
        Remove a provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            bool: True if provider was removed
        """
        if provider_name in self.providers:
            provider = self.providers.pop(provider_name)
            self.composite_provider.remove_provider(provider.get_name())
            return True
        return False
    
    def configure_provider(self, provider_name: str, config: Dict[str, Any]) -> bool:
        """
        Configure a provider.
        
        Args:
            provider_name: Name of the provider
            config: Provider configuration
            
        Returns:
            bool: True if provider was configured
        """
        if provider_name in self.providers:
            self.providers[provider_name].configure(config)
            
            # Update configuration if using config manager
            if self.alert_config:
                self.alert_config.update_provider_config(provider_name, config)
                
            return True
        return False
    
    def set_cooldown_period(self, seconds: int) -> None:
        """
        Set the cooldown period.
        
        Args:
            seconds: Cooldown period in seconds
        """
        self.cooldown_period = max(0, seconds)
        
        # Update configuration if using config manager
        if self.alert_config:
            # Handle different config manager interfaces
            key = f"{AlertConfigKeys.ALERTS_ROOT}.{AlertConfigKeys.COOLDOWN_PERIOD}"
            if hasattr(self.config_manager, 'set_config_value'):
                self.config_manager.set_config_value(key, self.cooldown_period)
            elif hasattr(self.config_manager, 'set_value'):
                self.config_manager.set_value(key, self.cooldown_period)
            else:
                self.config_manager.set(key, self.cooldown_period)
    
    def reset_cooldown(self, app_name: Optional[str] = None) -> None:
        """
        Reset cooldown timer for an app or all apps.
        
        Args:
            app_name: Name of the application or None for all apps
        """
        if app_name is None:
            self.cooldown_timers = {}
        elif app_name in self.cooldown_timers:
            del self.cooldown_timers[app_name]
