"""
Webhook alert provider implementation.

This module provides a webhook alert provider that sends HTTP requests
to configured webhook endpoints.
"""

import json
import threading
import logging
import time
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, Optional, List, Union

from focus_guard.core.alert.models import AlertInfo, AlertLevel
from focus_guard.core.alert.providers.base import AlertProvider

# Configure logging
logger = logging.getLogger(__name__)


class WebhookAlertProvider(AlertProvider):
    """
    Sends alerts to webhook endpoints.
    
    This provider sends HTTP requests to configured webhook endpoints
    when alerts are triggered.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize with optional configuration.
        
        Args:
            config: Configuration dictionary with options:
                - enabled: Whether this provider is enabled
                - urls: List of webhook URLs to send requests to
                - method: HTTP method to use (GET, POST, PUT)
                - headers: Dictionary of HTTP headers to include
                - include_window_info: Whether to include window info in payload
                - timeout: Request timeout in seconds
                - min_level: Minimum alert level to send webhooks for
                - cooldown_period: Minimum time between webhook calls (seconds)
        """
        super().__init__(config)
        self.urls = self.config.get("urls", [])
        self.method = self.config.get("method", "POST")
        self.headers = self.config.get("headers", {"Content-Type": "application/json"})
        self.include_window_info = self.config.get("include_window_info", True)
        self.timeout = self.config.get("timeout", 5)
        self.min_level = AlertLevel.from_string(self.config.get("min_level", "normal"))
        self.cooldown_period = self.config.get("cooldown_period", 10)  # seconds
        
        # Track last webhook time to prevent webhook spam
        self.last_webhook_times: Dict[str, float] = {}  # url -> last_time
        self.webhook_lock = threading.Lock()
    
    def send_alert(self, alert_info: AlertInfo) -> bool:
        """
        Send a webhook alert.
        
        Args:
            alert_info: Information about the alert to send
            
        Returns:
            bool: True if webhook was successfully sent to at least one endpoint
        """
        if not self.enabled:
            return False
        
        # Check if URLs are configured
        if not self.urls:
            logger.warning("No webhook URLs configured")
            return False
        
        # Convert AlertLevel to AlertLevel enum if it's a string
        level = alert_info.level
        if isinstance(level, str):
            try:
                level = AlertLevel.from_string(level)
            except ValueError:
                level = AlertLevel.NORMAL
        
        # Check if alert level is high enough
        if level.value < self.min_level.value:
            logger.debug(f"Alert level {level.name} below minimum {self.min_level.name}, not sending webhook")
            return False
        
        # Create payload
        payload = self._create_payload(alert_info)
        
        # Send webhook to each URL
        success = False
        current_time = time.time()
        
        for url in self.urls:
            # Check cooldown period for this URL
            with self.webhook_lock:
                if url in self.last_webhook_times:
                    time_since_last = current_time - self.last_webhook_times[url]
                    if time_since_last < self.cooldown_period:
                        logger.debug(f"Webhook to {url} in cooldown period, skipping")
                        continue
                
                # Update last webhook time
                self.last_webhook_times[url] = current_time
            
            # Send webhook in a separate thread to avoid blocking
            thread = threading.Thread(
                target=self._send_webhook,
                args=(url, payload),
                daemon=True
            )
            thread.start()
            success = True
        
        if success:
            self._log_alert(alert_info, True)
        
        return success
    
    def _create_payload(self, alert_info: AlertInfo) -> Dict[str, Any]:
        """
        Create webhook payload from alert info.
        
        Args:
            alert_info: Information about the alert
            
        Returns:
            Dict[str, Any]: Webhook payload
        """
        # Convert AlertLevel to string if needed
        level = alert_info.level.to_string() if isinstance(alert_info.level, AlertLevel) else alert_info.level
        
        # Create base payload
        payload = {
            "app_name": alert_info.app_name,
            "message": alert_info.message,
            "level": level,
            "timestamp": alert_info.timestamp,
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(alert_info.timestamp))
        }
        
        # Add window information if available and enabled
        if self.include_window_info:
            window_info = {}
            
            if alert_info.window_title:
                window_info["title"] = alert_info.window_title
            
            if alert_info.window_url:
                window_info["url"] = alert_info.window_url
            
            if alert_info.window_rect:
                window_info["rect"] = alert_info.window_rect
            
            if window_info:
                payload["window_info"] = window_info
        
        return payload
    
    def _send_webhook(self, url: str, payload: Dict[str, Any]) -> None:
        """
        Send a webhook request.
        
        Args:
            url: Webhook URL
            payload: Request payload
        """
        try:
            # Convert payload to JSON
            data = json.dumps(payload).encode("utf-8")
            
            # Create request
            req = urllib.request.Request(
                url,
                data=data,
                headers=self.headers,
                method=self.method
            )
            
            # Send request
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status = response.status
                logger.info(f"Webhook sent to {url}, status: {status}")
                
        except urllib.error.URLError as e:
            logger.error(f"Failed to send webhook to {url}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error sending webhook to {url}: {e}", exc_info=True)
    
    def add_url(self, url: str) -> None:
        """
        Add a webhook URL.
        
        Args:
            url: Webhook URL to add
        """
        if url not in self.urls:
            self.urls.append(url)
            self.config["urls"] = self.urls
    
    def remove_url(self, url: str) -> bool:
        """
        Remove a webhook URL.
        
        Args:
            url: Webhook URL to remove
            
        Returns:
            bool: True if URL was removed
        """
        if url in self.urls:
            self.urls.remove(url)
            self.config["urls"] = self.urls
            return True
        return False
    
    def set_headers(self, headers: Dict[str, str]) -> None:
        """
        Set HTTP headers for webhook requests.
        
        Args:
            headers: Dictionary of HTTP headers
        """
        self.headers = headers
        self.config["headers"] = headers
    
    def set_method(self, method: str) -> None:
        """
        Set HTTP method for webhook requests.
        
        Args:
            method: HTTP method (GET, POST, PUT)
        """
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        method = method.upper()
        
        if method in valid_methods:
            self.method = method
            self.config["method"] = method
        else:
            logger.warning(f"Invalid HTTP method: {method}, using POST")
            self.method = "POST"
            self.config["method"] = "POST"
