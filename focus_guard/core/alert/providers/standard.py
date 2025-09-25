"""
Standard alert provider implementation.

This module provides a standard alert provider that combines multiple
alert channels (popup, sound, etc.) into a single provider.
"""

from typing import Dict, Any, Optional

from focus_guard.core.alert.models import AlertInfo, AlertLevel
from focus_guard.core.alert.providers.base import CompositeAlertProvider
from focus_guard.core.alert.providers.popup import PopupAlertProvider
from focus_guard.core.alert.providers.sound import SoundAlertProvider


class StandardAlertProvider(CompositeAlertProvider):
    """
    Standard alert provider that combines multiple alert channels.
    
    This provider combines popup and sound alerts by default, but can be
    configured to use any combination of alert providers.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the standard alert provider.
        
        Args:
            config: Configuration dictionary with options:
                - enabled: Whether this provider is enabled
                - providers: List of provider configurations to use
        """
        config = config or {}
        
        # Create default providers if none specified
        if "providers" not in config:
            config["providers"] = [
                {"type": "popup", "enabled": True},
                {"type": "sound", "enabled": True}
            ]
        
        # Initialize with no providers - we'll add them in _setup_providers
        super().__init__(config, providers=[])
        
        # Set up the configured providers
        self._setup_providers()
    
    def _setup_providers(self):
        """Set up the configured alert providers."""
        from focus_guard.core.alert.provider_factory import create_alert_provider
        
        # Clear any existing providers
        self.providers = []
        
        # Create each configured provider
        for provider_config in self.config.get("providers", []):
            try:
                provider_type = provider_config.get("type")
                if not provider_type:
                    continue
                    
                # Create the provider
                provider = create_alert_provider(provider_type, provider_config)
                if provider:
                    self.add_provider(provider)
            except Exception as e:
                print(f"Error creating alert provider {provider_config.get('type')}: {e}")
                continue
