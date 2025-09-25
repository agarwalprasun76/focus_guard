"""
Desktop notification provider for FocusGuard.
Shows desktop notifications when distractions are detected.
"""
import os
import sys
import subprocess
from typing import Dict, Any, Optional

from .alert_provider import AlertProvider
from core.logger.logger import get_logger

class DesktopNotificationProvider(AlertProvider):
    """
    Alert provider that shows desktop notifications when distractions are detected.
    Uses platform-specific methods to display notifications.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the desktop notification provider.
        
        Args:
            config: Configuration dictionary with optional keys:
                - notification_duration: How long notifications should stay visible (in seconds)
                - include_app_name: Whether to include the app name in notifications
                - include_timestamp: Whether to include the timestamp in notifications
        """
        super().__init__(config or {})
        self.logger = get_logger("alert_system.desktop")
        self.enabled = True
    
    def send_alert(self, window_info: Dict[str, Any], message: str, level: str = "normal") -> bool:
        """
        Show a desktop notification.
        
        Args:
            window_info: Information about the window causing the distraction
            message: Alert message
            level: Alert level ("normal", "warning", or "critical")
            
        Returns:
            bool: True if alert was successfully sent
        """
        if not self.enabled:
            self.logger.debug("Desktop notification provider is disabled, skipping alert")
            return False
            
        app_name = window_info.get("app_name", "Unknown App")
        title = f"FocusGuard - {level.capitalize()}"
        
        try:
            if sys.platform == "win32":
                # Windows notification using PowerShell
                script = f"""
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

                $APP_ID = 'FocusGuard'
                $template = @"
                <toast>
                    <visual>
                        <binding template="ToastText02">
                            <text id="1">{title}</text>
                            <text id="2">{message}</text>
                        </binding>
                    </visual>
                </toast>
                "@

                $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
                $xml.LoadXml($template)
                $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($APP_ID).Show($toast)
                """
                
                # Use PowerShell to display notification
                subprocess.run(["powershell", "-Command", script], 
                               capture_output=True, text=True, check=False)
                return True
                
            elif sys.platform == "darwin":
                # macOS notification
                message = message.replace('"', '\\"')
                subprocess.run([
                    "osascript", "-e", 
                    f'display notification "{message}" with title "{title}"'
                ], capture_output=True, check=False)
                return True
                
            elif sys.platform == "linux":
                # Linux notification (requires notify-send)
                subprocess.run([
                    "notify-send", title, message, "--icon=dialog-information"
                ], capture_output=True, check=False)
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to send desktop notification: {e}", exc_info=True)
            return False
