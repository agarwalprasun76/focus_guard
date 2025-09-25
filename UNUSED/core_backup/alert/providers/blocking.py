"""
Blocking alert provider implementation.

This module provides a blocking alert provider that shows alerts requiring
user acknowledgment using the platform-specific implementation.
"""

import time
import logging
from typing import Dict, Any, Optional, List

from core_v2.alert.models import AlertInfo, AlertLevel
from core_v2.alert.providers.base import AlertProvider

# Configure logging
logger = logging.getLogger(__name__)


class BlockingAlertProvider(AlertProvider):
    """
    Shows blocking alerts requiring user acknowledgment.
    
    This provider displays alerts that block the user interface and require
    explicit acknowledgment before the user can continue.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize with optional configuration.
        
        Args:
            config: Configuration dictionary with options:
                - enabled: Whether this provider is enabled
                - timeout: Timeout in seconds (0 for no timeout)
                - buttons: List of button labels to show
                - default_button: Index of default button
                - escalation_threshold: Number of alerts before escalating
                - min_level: Minimum alert level to show blocking alerts
        """
        super().__init__(config)
        self.timeout = self.config.get("timeout", 0)  # seconds, 0 = no timeout
        self.buttons = self.config.get("buttons", ["OK"])
        self.default_button = self.config.get("default_button", 0)
        self.escalation_threshold = self.config.get("escalation_threshold", 3)
        self.min_level = AlertLevel.from_string(self.config.get("min_level", "warning"))
        
        # Track alert counts for escalation
        self.alert_counts = {}  # app_name -> count
        self.last_reset_time = time.time()
        self.reset_interval = self.config.get("reset_interval", 3600)  # 1 hour
    
    def send_alert(self, alert_info: AlertInfo) -> bool:
        """
        Show a blocking alert.
        
        Args:
            alert_info: Information about the alert to send
            
        Returns:
            bool: True if alert was successfully shown and acknowledged
        """
        if not self.enabled:
            return False
        
        # Check if we should reset alert counts
        current_time = time.time()
        if current_time - self.last_reset_time > self.reset_interval:
            self.alert_counts = {}
            self.last_reset_time = current_time
        
        # Convert AlertLevel to AlertLevel enum if it's a string
        level = alert_info.level
        if isinstance(level, str):
            try:
                level = AlertLevel.from_string(level)
            except ValueError:
                level = AlertLevel.NORMAL
        
        # Check if alert level is high enough
        if level.value < self.min_level.value:
            logger.debug(f"Alert level {level.name} below minimum {self.min_level.name}, not showing blocking alert")
            return False
        
        # Update alert count for this app
        app_name = alert_info.app_name
        self.alert_counts[app_name] = self.alert_counts.get(app_name, 0) + 1
        
        # Create title with app name
        title = f"FocusGuard Alert - {app_name}"
        
        # Create options dictionary for platform implementation
        options = {
            "app_name": "FocusGuard",
            "timeout": self.timeout,
            "buttons": self.buttons,
            "default_button": self.default_button
        }
        
        # Escalate message if threshold exceeded
        message = alert_info.message
        if self.alert_counts[app_name] > self.escalation_threshold:
            message = f"[ESCALATED] {message}\n\nThis is alert #{self.alert_counts[app_name]} for {app_name}."
        
        # Show blocking alert using platform implementation
        try:
            result = self.platform.show_blocking_alert(
                title, 
                message, 
                level.to_string() if isinstance(level, AlertLevel) else level,
                options
            )
            self._log_alert(alert_info, result)
            return result
        except Exception as e:
            logger.error(f"Failed to show blocking alert: {e}", exc_info=True)
            return False
    
    def reset_alert_counts(self) -> None:
        """
        Reset all alert counts.
        """
        self.alert_counts = {}
        self.last_reset_time = time.time()
    
    def get_alert_count(self, app_name: str) -> int:
        """
        Get the current alert count for an app.
        
        Args:
            app_name: Name of the application
            
        Returns:
            int: Number of alerts shown for this app
        """
        return self.alert_counts.get(app_name, 0)
