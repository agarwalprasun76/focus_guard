"""
Base classes for alert providers.

This module defines the base classes for alert providers, which are responsible
for sending alerts through different channels (popup, sound, email, etc.).
"""

from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, Optional, List

from focus_guard.core.alert.models import AlertInfo, AlertLevel
from focus_guard.core.alert.platform import get_platform_implementation

# Configure logging
logger = logging.getLogger(__name__)


class AlertProvider(ABC):
    """
    Base class for all alert providers.
    
    Alert providers are responsible for sending alerts through different channels,
    such as popup notifications, sounds, emails, etc. Each provider implements
    a specific alert channel.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the alert provider.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.platform = get_platform_implementation()
        self.name = self.__class__.__name__
    
    @abstractmethod
    def send_alert(self, alert_info: AlertInfo) -> bool:
        """
        Send an alert.
        
        Args:
            alert_info: Information about the alert to send
            
        Returns:
            bool: True if alert was successfully sent
        """
        pass
    
    def get_name(self) -> str:
        """
        Get the name of the alert provider.
        
        Returns:
            str: Name of the alert provider
        """
        return self.name
    
    def is_enabled(self) -> bool:
        """
        Check if the provider is enabled.
        
        Returns:
            bool: True if the provider is enabled
        """
        return self.enabled
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Update the provider configuration.
        
        Args:
            config: New configuration dictionary
        """
        self.config.update(config)
        self.enabled = self.config.get("enabled", self.enabled)
    
    def _log_alert(self, alert_info: AlertInfo, success: bool) -> None:
        """
        Log an alert attempt.
        
        Args:
            alert_info: Information about the alert
            success: Whether the alert was successfully sent
        """
        level_name = alert_info.level.name if isinstance(alert_info.level, AlertLevel) else alert_info.level
        status = "SUCCESS" if success else "FAILED"
        logger.info(
            f"[{self.name}] [{status}] [{level_name}] {alert_info.app_name}: {alert_info.message}"
        )


class CompositeAlertProvider(AlertProvider):
    """
    Composite alert provider that delegates to multiple child providers.
    
    This provider allows grouping multiple providers together and treating
    them as a single provider. It delegates alert requests to all of its
    child providers.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, providers: Optional[List[AlertProvider]] = None):
        """
        Initialize the composite provider.
        
        Args:
            config: Configuration dictionary
            providers: List of child providers
        """
        super().__init__(config)
        self.providers = providers or []
        self.name = self.config.get("name", "CompositeAlertProvider")
    
    def add_provider(self, provider: AlertProvider) -> None:
        """
        Add a child provider.
        
        Args:
            provider: Provider to add
        """
        self.providers.append(provider)
    
    def remove_provider(self, provider_name: str) -> bool:
        """
        Remove a child provider by name.
        
        Args:
            provider_name: Name of the provider to remove
            
        Returns:
            bool: True if a provider was removed
        """
        initial_count = len(self.providers)
        self.providers = [p for p in self.providers if p.get_name() != provider_name]
        return len(self.providers) < initial_count
    
    def send_alert(self, alert_info: AlertInfo) -> bool:
        """
        Send an alert through all child providers.
        
        Args:
            alert_info: Information about the alert to send
            
        Returns:
            bool: True if at least one provider successfully sent the alert
        """
        if not self.enabled:
            return False
        
        success = False
        for provider in self.providers:
            if provider.is_enabled():
                if provider.send_alert(alert_info):
                    success = True
        
        self._log_alert(alert_info, success)
        return success
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Update the provider configuration and propagate to child providers.
        
        Args:
            config: New configuration dictionary
        """
        super().configure(config)
        
        # Propagate configuration to child providers
        provider_configs = self.config.get("providers", {})
        for provider in self.providers:
            provider_name = provider.get_name()
            if provider_name in provider_configs:
                provider.configure(provider_configs[provider_name])


class ConditionalAlertProvider(AlertProvider):
    """
    Alert provider that only sends alerts if certain conditions are met.
    
    This provider wraps another provider and only forwards alerts if
    the specified conditions are met.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, provider: Optional[AlertProvider] = None):
        """
        Initialize the conditional provider.
        
        Args:
            config: Configuration dictionary
            provider: Provider to wrap
        """
        super().__init__(config)
        self.provider = provider
        self.name = self.config.get("name", "ConditionalAlertProvider")
        
        # Condition configuration
        self.min_level = AlertLevel.from_string(self.config.get("min_level", "normal"))
        self.app_whitelist = self.config.get("app_whitelist", [])
        self.app_blacklist = self.config.get("app_blacklist", [])
        self.time_restrictions = self.config.get("time_restrictions", {})
    
    def set_provider(self, provider: AlertProvider) -> None:
        """
        Set the wrapped provider.
        
        Args:
            provider: Provider to wrap
        """
        self.provider = provider
    
    def send_alert(self, alert_info: AlertInfo) -> bool:
        """
        Send an alert if conditions are met.
        
        Args:
            alert_info: Information about the alert to send
            
        Returns:
            bool: True if alert was successfully sent
        """
        if not self.enabled or not self.provider:
            return False
        
        # Check conditions
        if not self._check_conditions(alert_info):
            return False
        
        # Forward to wrapped provider
        success = self.provider.send_alert(alert_info)
        self._log_alert(alert_info, success)
        return success
    
    def _check_conditions(self, alert_info: AlertInfo) -> bool:
        """
        Check if the alert meets the conditions.
        
        Args:
            alert_info: Information about the alert
            
        Returns:
            bool: True if conditions are met
        """
        # Check alert level
        if isinstance(alert_info.level, AlertLevel):
            if alert_info.level.value < self.min_level.value:
                return False
        elif isinstance(alert_info.level, str):
            try:
                level = AlertLevel.from_string(alert_info.level)
                if level.value < self.min_level.value:
                    return False
            except ValueError:
                pass
        
        # Check app whitelist/blacklist
        app_name = alert_info.app_name.lower()
        
        if self.app_whitelist and app_name not in [a.lower() for a in self.app_whitelist]:
            return False
            
        if self.app_blacklist and app_name in [a.lower() for a in self.app_blacklist]:
            return False
        
        # Check time restrictions (could be implemented based on time of day, day of week, etc.)
        # This would require additional logic based on the specific requirements
        
        return True
