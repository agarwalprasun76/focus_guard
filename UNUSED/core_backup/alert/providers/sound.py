"""
Sound alert provider implementation.

This module provides a sound alert provider that plays audio alerts
using the platform-specific implementation.
"""

import time
import threading
import logging
from typing import Dict, Any, Optional

from core_v2.alert.models import AlertInfo, AlertLevel
from core_v2.alert.providers.base import AlertProvider

# Configure logging
logger = logging.getLogger(__name__)


class SoundAlertProvider(AlertProvider):
    """
    Plays sound alerts using platform-specific methods.
    
    This provider plays audio alerts to notify the user of distractions
    or other events.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize with optional configuration.
        
        Args:
            config: Configuration dictionary with options:
                - enabled: Whether this provider is enabled
                - volume: Sound volume (0.0 to 1.0)
                - repeat_count: Number of times to repeat the sound
                - sound_files: Dictionary mapping alert levels to sound files
                - cooldown_period: Minimum time between sounds (seconds)
        """
        super().__init__(config)
        self.volume = self.config.get("volume", 0.7)
        self.repeat_count = self.config.get("repeat_count", 1)
        self.sound_files = self.config.get("sound_files", {})
        self.cooldown_period = self.config.get("cooldown_period", 5)  # seconds
        
        # Track last sound time to prevent sound spam
        self.last_sound_time = 0
        self.sound_lock = threading.Lock()
    
    def send_alert(self, alert_info: AlertInfo) -> bool:
        """
        Play a sound alert.
        
        Args:
            alert_info: Information about the alert to send
            
        Returns:
            bool: True if alert was successfully sent
        """
        if not self.enabled:
            return False
        
        # Check cooldown period
        with self.sound_lock:
            current_time = time.time()
            time_since_last = current_time - self.last_sound_time
            
            if time_since_last < self.cooldown_period:
                logger.debug(f"Sound alert in cooldown period, skipping")
                return False
            
            # Update last sound time
            self.last_sound_time = current_time
        
        # Convert AlertLevel to string if needed
        level = alert_info.level.to_string() if isinstance(alert_info.level, AlertLevel) else alert_info.level
        
        # Create options dictionary for platform implementation
        options = {
            "volume": self.volume,
            "repeat_count": self.repeat_count
        }
        
        # Add custom sound file if configured
        if level in self.sound_files and self.sound_files[level]:
            options["custom_sound"] = self.sound_files[level]
        
        # Play sound in a separate thread to avoid blocking
        thread = threading.Thread(
            target=self._play_sound,
            args=(level, options),
            daemon=True
        )
        thread.start()
        
        self._log_alert(alert_info, True)
        return True
    
    def _play_sound(self, level: str, options: Dict[str, Any]) -> None:
        """
        Play a sound using platform-specific methods.
        
        Args:
            level: Alert level ("normal", "warning", "critical")
            options: Sound options
        """
        try:
            self.platform.play_sound(level, options)
        except Exception as e:
            logger.error(f"Failed to play sound: {e}", exc_info=True)
    
    def set_volume(self, volume: float) -> None:
        """
        Set the sound volume.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.volume = max(0.0, min(1.0, volume))
        self.config["volume"] = self.volume
    
    def set_repeat_count(self, repeat_count: int) -> None:
        """
        Set the number of times to repeat sounds.
        
        Args:
            repeat_count: Number of repetitions
        """
        self.repeat_count = max(1, repeat_count)
        self.config["repeat_count"] = self.repeat_count
