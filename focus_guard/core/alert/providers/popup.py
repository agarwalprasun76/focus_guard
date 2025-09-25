"""
Popup alert provider implementation.

This module provides a popup alert provider that shows visual popup alerts
using the platform-specific implementation.
"""

import time
import threading
import logging
from typing import Dict, Any, Optional, List

from focus_guard.core.alert.models import AlertInfo, AlertLevel
from focus_guard.core.alert.providers.base import AlertProvider

# Configure logging
logger = logging.getLogger(__name__)


class PopupAlertProvider(AlertProvider):
    """
    Shows popup alerts using platform-specific methods.
    
    This provider displays visual popup alerts that appear on the screen
    to notify the user of distractions or other events.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize with optional configuration.
        
        Args:
            config: Configuration dictionary with options:
                - enabled: Whether this provider is enabled
                - popup_duration: How long to show popups (seconds)
                - overlay_on_distraction: Whether to show popups over the distraction
                - show_app_name: Whether to include app name in popup
                - max_popups: Maximum number of popups to show at once
        """
        super().__init__(config)
        self.popup_duration = self.config.get("popup_duration", 10)  # seconds
        self.overlay_on_distraction = self.config.get("overlay_on_distraction", False)
        self.show_app_name = self.config.get("show_app_name", True)
        self.max_popups = self.config.get("max_popups", 3)
        
        # Track active and recent alerts to prevent duplicates
        self.active_alerts = []
        self.recent_alerts = {}  # Track recent alerts to prevent duplicates
        self.alert_lock = threading.Lock()
    
    def send_alert(self, alert_info: AlertInfo) -> bool:
        """
        Show a popup alert.
        
        Args:
            alert_info: Information about the alert to send
            
        Returns:
            bool: True if alert was successfully sent
        """
        if not self.enabled:
            return False
        
        # Check for duplicate alerts
        with self.alert_lock:
            current_time = time.time()
            alert_key = f"{alert_info.app_name}-{alert_info.level.to_string() if isinstance(alert_info.level, AlertLevel) else alert_info.level}"
            
            if alert_key in self.recent_alerts:
                last_alert_time = self.recent_alerts[alert_key]
                time_since_last = current_time - last_alert_time
                
                # If we've shown this exact alert recently, skip it
                if time_since_last < self.popup_duration:
                    logger.debug(f"Skipping duplicate alert for {alert_info.app_name}")
                    return True
            
            # Track this alert to prevent duplicates
            self.recent_alerts[alert_key] = current_time
            
            # Check if we have too many active alerts
            if len(self.active_alerts) >= self.max_popups:
                logger.debug(f"Too many active alerts ({len(self.active_alerts)}), skipping")
                return False
        
        # Start popup in a separate thread to avoid blocking
        thread = threading.Thread(
            target=self._show_popup,
            args=(alert_info,),
            daemon=True
        )
        thread.start()
        
        self._log_alert(alert_info, True)
        return True
    
    def _show_popup(self, alert_info: AlertInfo) -> None:
        """
        Show a popup using platform-specific methods.
        
        Args:
            alert_info: Information about the alert to show
        """
        # Convert AlertLevel to string if needed
        level = alert_info.level.to_string() if isinstance(alert_info.level, AlertLevel) else alert_info.level
        
        # Create title with optional app name
        if self.show_app_name:
            title = f"FocusGuard Alert - {alert_info.app_name}"
        else:
            title = f"FocusGuard Alert"
        
        # Create options dictionary for platform implementation
        options = {
            "app_name": "FocusGuard",
            "duration": self.popup_duration
        }
        
        # Add window position if overlay_on_distraction is enabled
        if self.overlay_on_distraction and alert_info.window_rect:
            options["window_rect"] = alert_info.window_rect
        
        # Track this alert
        alert_id = f"{alert_info.app_name}-{time.time()}"
        with self.alert_lock:
            self.active_alerts.append(alert_id)
        
        # Show notification using platform implementation
        try:
            self.platform.show_notification(title, alert_info.message, level, options)
        except Exception as e:
            logger.error(f"Failed to show popup: {e}", exc_info=True)
        
        # Remove from active alerts after duration
        if self.popup_duration > 0:
            time.sleep(self.popup_duration)
            with self.alert_lock:
                if alert_id in self.active_alerts:
                    self.active_alerts.remove(alert_id)
