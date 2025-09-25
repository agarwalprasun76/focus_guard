"""
Notification alert handler implementation.

This module provides an alert handler that displays notifications
to the user when distractions are detected.
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from focus_guard.core.distraction.interfaces import AlertHandler
from focus_guard.core.distraction.models import DistractionAlert, AlertLevel
from focus_guard.core.alert.providers.base import AlertProvider
from focus_guard.core.alert.models import AlertInfo


class NotificationHandler(AlertHandler):
    """
    Alert handler that displays notifications to the user.
    
    This handler uses the notification service to display
    notifications when distractions are detected.
    """
    
    def __init__(
        self,
        alert_provider: AlertProvider,
        min_level: AlertLevel = AlertLevel.WARNING,
        cooldown_seconds: int = 60,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the notification handler.
        
        Args:
            alert_provider: The alert provider to use for sending notifications.
            min_level: Minimum alert level to trigger a notification.
            cooldown_seconds: Cooldown period between notifications.
            logger: Optional logger for logging.
        """
        self._alert_provider = alert_provider
        self._min_level = min_level
        self._cooldown_seconds = cooldown_seconds
        self._logger = logger or logging.getLogger(__name__)
        self._last_notification: Optional[datetime] = None
    
    @property
    def name(self) -> str:
        """Get the name of the handler."""
        return "Notification Handler"
    
    def can_handle(self, alert: DistractionAlert) -> bool:
        """
        Determine if the handler can handle the alert.
        
        Args:
            alert: The distraction alert to handle.
            
        Returns:
            True if the handler can handle the alert, False otherwise.
        """
        # Check if alert level is high enough
        if alert.level.value < self._min_level.value:
            return False
        
        # Check if we're in cooldown period
        if self._last_notification is not None:
            cooldown_end = self._last_notification + timedelta(seconds=self._cooldown_seconds)
            if datetime.now() < cooldown_end:
                return False
        
        return True
    
    def handle(self, alert: DistractionAlert) -> None:
        """
        Handle a distraction alert by displaying a notification.
        
        Args:
            alert: The distraction alert to handle.
        """
        try:
            # Create alert info
            alert_info = AlertInfo(
                app_name="Focus Guard",
                message=alert.message,
                level=self._get_notification_level(alert.level),
                context={
                    "rule_name": alert.rule_name,
                    "timestamp": alert.timestamp.isoformat(),
                    **alert.metadata
                }
            )
            
            # Send alert
            self._alert_provider.send_alert(alert_info)
            
            # Update last notification time
            self._last_notification = datetime.now()
            
            self._logger.info(f"Sent notification for alert: {alert.message}")
        except Exception as e:
            self._logger.error(f"Error sending notification: {e}")
    
    def _get_notification_level(self, alert_level: AlertLevel) -> str:
        """
        Convert alert level to notification level.
        
        Args:
            alert_level: The alert level.
            
        Returns:
            The corresponding notification level.
        """
        if alert_level == AlertLevel.INFO:
            return "info"
        elif alert_level == AlertLevel.WARNING:
            return "warning"
        elif alert_level == AlertLevel.CRITICAL:
            return "error"
        else:
            return "info"
