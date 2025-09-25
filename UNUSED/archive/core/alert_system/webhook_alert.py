"""
Webhook alert provider for FocusGuard.
Sends webhook notifications when distractions are detected.
"""
from datetime import datetime
from typing import Dict, Any, Optional

from .alert_provider import AlertProvider
from core.logger.logger import get_logger

class WebhookAlertProvider(AlertProvider):
    """
    Alert provider that sends webhook notifications when distractions are detected.
    
    This provider sends JSON payloads to a configured webhook URL, which can be
    used to integrate with services like Slack, Discord, or custom applications.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the webhook alert provider.
        
        Args:
            config: Configuration dictionary with required keys:
                - webhook_url: URL to send webhook notifications to
                
                Optional keys:
                - include_app_info: Whether to include app details (default: True)
                - include_timestamp: Whether to include timestamp (default: True)
                - custom_headers: Additional HTTP headers to include
                - timeout: Request timeout in seconds (default: 5)
        """
        super().__init__(config or {})
        self.logger = get_logger("alert_system.webhook")
        self.enabled = True
        
        # Check if we have the required configuration
        if not self.config.get("webhook_url"):
            self.logger.warning("Webhook alert provider is missing webhook_url - provider will be disabled")
            self.enabled = False
    
    def send_alert(self, window_info: Dict[str, Any], message: str, level: str = "normal") -> bool:
        """
        Send a webhook notification.
        
        Args:
            window_info: Information about the window causing the distraction
            message: Alert message
            level: Alert level ("normal", "warning", or "critical")
            
        Returns:
            bool: True if alert was successfully sent
        """
        if not self.enabled:
            self.logger.debug("Webhook alert provider is disabled, skipping alert")
            return False
            
        webhook_url = self.config.get("webhook_url")
        if not webhook_url:
            self.logger.warning("No webhook URL configured, skipping alert")
            return False
            
        try:
            import requests
            
            # Prepare payload
            payload = {
                "level": level,
                "message": message,
                "timestamp": window_info.get("timestamp", datetime.now().isoformat())
            }
            
            # Include app info if configured (default: True)
            if self.config.get("include_app_info", True):
                payload.update({
                    "app_name": window_info.get("app_name", "Unknown"),
                    "window_title": window_info.get("window_title", "")
                })
            
            # Add custom fields if specified
            custom_fields = self.config.get("custom_fields", {})
            if custom_fields:
                payload.update(custom_fields)
            
            # Prepare headers
            headers = {"Content-Type": "application/json"}
            
            # Add custom headers if specified
            custom_headers = self.config.get("custom_headers", {})
            if custom_headers:
                headers.update(custom_headers)
            
            # Send the webhook request
            timeout = self.config.get("timeout", 5)  # Default timeout: 5 seconds
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            # Check if the request was successful
            if response.status_code >= 200 and response.status_code < 300:
                self.logger.info(f"Webhook alert sent successfully (status: {response.status_code})")
                return True
            else:
                self.logger.warning(
                    f"Webhook request failed with status code {response.status_code}: {response.text}"
                )
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {e}", exc_info=True)
            return False
