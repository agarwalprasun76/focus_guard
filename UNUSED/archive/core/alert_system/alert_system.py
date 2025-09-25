"""
AlertSystem: Notifies user when distractions are detected.
Provides multiple notification methods and escalation strategies.
"""
from typing import Dict, Any, List, Optional, Callable, Union
import time
import threading
import subprocess
import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

from .alert_provider import AlertProvider
from .sound_alert import SoundAlertProvider
from .email_alert import EmailAlertProvider
from .popup_alert import PopupAlertProvider
from .desktop_notification import DesktopNotificationProvider
from .webhook_alert import WebhookAlertProvider
from .app_blocker import AppBlockerProvider
from core.logger.logger import get_logger





class AlertSystem:
    """
    Main alert system that manages multiple alert providers and escalation strategies.
    
    The AlertSystem is responsible for:
    1. Managing multiple alert providers (popup, sound, email, etc.)
    2. Tracking alert history for applications
    3. Implementing escalation strategies based on distraction frequency
    4. Handling cooldown periods between alerts
    5. Persisting alert history between sessions
    
    Example usage:
    ```python
    # Create an alert system with default providers
    alert_system = AlertSystem()
    
    # Create an alert system with custom configuration
    config = {
        "cooldown_period": 60,  # seconds
        "escalation_threshold": 3,  # alerts before escalation
        "escalation_window": 300,  # seconds
        "desktop_notification": {"enabled": True},
        "sound_alert": {"volume": 0.7, "repeat_count": 2}
    }
    alert_system = AlertSystem(config=config)
    
    # Send an alert when a distraction is detected
    window_info = {
        "app_name": "SocialMedia.exe",
        "window_title": "Social Media - Home",
        "pid": "12345",
        "timestamp": datetime.now().isoformat()
    }
    alert_system.alert(window_info, "You're getting distracted!")
    ```
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        providers: Optional[List[AlertProvider]] = None
    ):
        """
        Initialize the alert system.
        
        Args:
            config: Configuration dictionary
            providers: List of alert providers to use
        """
        self.config = config or {}
        self.providers = providers or []
        self.alert_history = {}  # app_name -> list of alert times
        self.escalation_levels = ["normal", "warning", "critical"]
        self.cooldown_period = self.config.get("cooldown_period", 60)  # seconds
        self.escalation_threshold = self.config.get("escalation_threshold", 3)  # alerts before escalation
        self.escalation_window = self.config.get("escalation_window", 300)  # seconds
        
        # Initialize logger
        self.logger = get_logger("alert_system")
        
        # Initialize default providers if none provided
        if not self.providers:
            self._init_default_providers()
            
        # Load persistent alert history
        self._load_history()
            
    def _init_default_providers(self):
        """Initialize default alert providers."""
        self.providers = [
            DesktopNotificationProvider(self.config.get("desktop_notification", {})),
            SoundAlertProvider(self.config.get("sound_alert", {}))
        ]
        
        # Add webhook provider if configured
        if "webhook" in self.config:
            self.providers.append(WebhookAlertProvider(self.config.get("webhook")))
            
        # Add email provider if configured
        if "email" in self.config:
            self.providers.append(EmailAlertProvider(self.config.get("email")))
            
        # Add app blocker if enabled
        if self.config.get("enable_app_blocking", False):
            self.providers.append(AppBlockerProvider(self.config.get("app_blocker", {})))
    
    def add_provider(self, provider: AlertProvider):
        """Add an alert provider."""
        self.providers.append(provider)
        
    def remove_provider(self, provider_type: type):
        """Remove all providers of a specific type."""
        self.providers = [p for p in self.providers if not isinstance(p, provider_type)]
        
    def alert(self, window_info: Dict[str, Any], message: str) -> bool:
        """
        Send an alert through all enabled providers with automatic escalation.
        
        This method is the main entry point for sending alerts. It handles:
        - Checking cooldown periods to avoid alert fatigue
        - Determining the appropriate alert level based on distraction history
        - Tracking the alert in history for future escalation
        - Distributing the alert to all enabled providers
        
        The alert level will automatically escalate from "normal" to "warning" to "critical"
        based on the frequency of alerts for the same application within the escalation window.
        
        Args:
            window_info: Dictionary containing information about the window causing the distraction.
                Must contain at least an "app_name" key. Other useful keys include:
                - "window_title": Title of the window
                - "pid": Process ID
                - "timestamp": When the distraction was detected
                - "screenshot": Optional base64 encoded screenshot
            message: Alert message to display to the user
            
        Returns:
            bool: True if at least one alert was sent successfully
            
        Example:
        ```python
        # Basic alert
        alert_system.alert({"app_name": "YouTube"}, "YouTube is distracting you from work!")
        
        # Detailed alert
        alert_system.alert({
            "app_name": "Chrome",
            "window_title": "Social Media | Home",
            "pid": 1234,
            "timestamp": "2025-07-03T13:45:22"
        }, "Social media is distracting you from your current task.")
        ```
        """
        # Skip if we're in cooldown for this app
        app_name = window_info.get("app_name", "Unknown App")
        if self._is_in_cooldown(app_name):
            self.logger.debug(f"Skipping alert for {app_name} (in cooldown)")
            return False
            
        # Determine alert level based on history
        level = self._determine_alert_level(app_name)
        
        # Track this alert in history
        self._track_alert(app_name)
        
        # Save history periodically
        self._save_history()
        
        # Send alerts through all providers
        success = False
        for provider in self.providers:
            if provider.send_alert(window_info, message, level):
                success = True
                
        return success
    
    def _is_in_cooldown(self, app_name: str) -> bool:
        """
        Check if an application is currently in cooldown period.
        
        Args:
            app_name: Name of the application
            
        Returns:
            bool: True if the application is in cooldown period
        """
        if app_name not in self.alert_history or not self.alert_history[app_name]:
            return False
            
        current_time = datetime.now()
        last_alert_time = self.alert_history[app_name][-1]
        time_since_last = (current_time - last_alert_time).total_seconds()
        
        return time_since_last < self.cooldown_period
    
    def _track_alert(self, app_name: str) -> None:
        """
        Record an alert in the history for the given application.
        
        Args:
            app_name: Name of the application
        """
        current_time = datetime.now()
        
        if app_name not in self.alert_history:
            self.alert_history[app_name] = []
            
        self.alert_history[app_name].append(current_time)
    
    def _count_recent_alerts(self, app_name: str) -> int:
        """
        Count the number of alerts for an application within the escalation window.
        
        Args:
            app_name: Name of the application
            
        Returns:
            int: Number of recent alerts
        """
        if app_name not in self.alert_history:
            return 0
            
        current_time = datetime.now()
        escalation_time = current_time - timedelta(seconds=self.escalation_window)
        recent_alerts = [t for t in self.alert_history[app_name] if t > escalation_time]
        
        return len(recent_alerts)
    
    def _determine_alert_level(self, app_name: str) -> str:
        """
        Determine the escalation level based on alert history.
        
        The level escalates from "normal" to "warning" to "critical" based on
        the number of recent alerts within the escalation window:
        - normal: first alert
        - warning: second alert within the window
        - critical: third or more alerts within the window
        
        Args:
            app_name: Name of the application
            
        Returns:
            str: Escalation level ("normal", "warning", or "critical")
        """
        # Count recent alerts and determine level
        count = self._count_recent_alerts(app_name)
        
        # More aggressive escalation - escalate after just 1 or 2 alerts
        if count >= self.escalation_threshold:
            return "critical"
        elif count >= 1:
            return "warning"
        else:
            return "normal"
    
    def _get_history_file(self) -> Path:
        """Get the path to the alert history file."""
        data_dir = Path(self.config.get("data_directory", os.path.expanduser("~/.focusguard")))
        data_dir.mkdir(exist_ok=True)
        return data_dir / "alert_history.json"
    
    def _save_history(self):
        """Save alert history to file."""
        try:
            history_file = self._get_history_file()
            
            # Convert datetime objects to strings
            serializable_history = {}
            for app_name, times in self.alert_history.items():
                serializable_history[app_name] = [t.isoformat() for t in times]
                
            with open(history_file, "w") as f:
                json.dump(serializable_history, f)
                
        except Exception as e:
            self.logger.error(f"Failed to save alert history: {e}", exc_info=True)
    
    def _load_history(self):
        """Load alert history from file."""
        try:
            history_file = self._get_history_file()
            if not history_file.exists():
                return
                
            with open(history_file, "r") as f:
                serialized_history = json.load(f)
                
            # Convert string timestamps back to datetime objects
            for app_name, times in serialized_history.items():
                self.alert_history[app_name] = [datetime.fromisoformat(t) for t in times]
                
            # Clean up old history entries
            self._cleanup_history()
                
        except Exception as e:
            self.logger.error(f"Failed to load alert history: {e}", exc_info=True)
    
    def _cleanup_history(self):
        """Remove old history entries."""
        cutoff_time = datetime.now() - timedelta(days=7)  # Keep 7 days of history
        
        for app_name in list(self.alert_history.keys()):
            # Filter out old timestamps
            self.alert_history[app_name] = [
                t for t in self.alert_history[app_name] 
                if t > cutoff_time
            ]
            
            # Remove empty entries
            if not self.alert_history[app_name]:
                del self.alert_history[app_name]
    
    def is_app_blocked(self, app_name: str) -> bool:
        """Check if an application is currently blocked."""
        for provider in self.providers:
            if isinstance(provider, AppBlockerProvider) and provider.is_blocked(app_name):
                return True
        return False
    
    def configure(self, config: Dict[str, Any]):
        """Update configuration."""
        self.config.update(config)
        
        # Update internal settings
        self.cooldown_period = self.config.get("cooldown_period", self.cooldown_period)
        self.escalation_threshold = self.config.get("escalation_threshold", self.escalation_threshold)
        self.escalation_window = self.config.get("escalation_window", self.escalation_window)
        
        # Update providers
        for provider in self.providers:
            provider_type = provider.__class__.__name__.lower().replace("provider", "")
            if provider_type in self.config:
                provider.config.update(self.config[provider_type])
