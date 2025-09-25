"""
Email alert provider implementation.

This module provides an email alert provider that sends email notifications
for alerts using SMTP.
"""

import smtplib
import ssl
import threading
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List

from focus_guard.core.alert.models import AlertInfo, AlertLevel
from focus_guard.core.alert.providers.base import AlertProvider

# Configure logging
logger = logging.getLogger(__name__)


class EmailAlertProvider(AlertProvider):
    """
    Sends email alerts using SMTP.
    
    This provider sends email notifications for alerts to configured
    recipients using SMTP.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize with optional configuration.
        
        Args:
            config: Configuration dictionary with options:
                - enabled: Whether this provider is enabled
                - smtp_server: SMTP server address
                - smtp_port: SMTP server port
                - use_tls: Whether to use TLS
                - username: SMTP username
                - password: SMTP password
                - sender: Sender email address
                - recipients: List of recipient email addresses
                - subject_prefix: Prefix for email subjects
                - min_level: Minimum alert level to send emails for
                - cooldown_period: Minimum time between emails (seconds)
        """
        super().__init__(config)
        self.smtp_server = self.config.get("smtp_server", "")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.use_tls = self.config.get("use_tls", True)
        self.username = self.config.get("username", "")
        self.password = self.config.get("password", "")
        self.sender = self.config.get("sender", "")
        self.recipients = self.config.get("recipients", [])
        self.subject_prefix = self.config.get("subject_prefix", "[FocusGuard Alert]")
        self.min_level = AlertLevel.from_string(self.config.get("min_level", "warning"))
        self.cooldown_period = self.config.get("cooldown_period", 300)  # 5 minutes
        
        # Track last email time to prevent email spam
        self.last_email_time = None
        self.email_lock = threading.Lock()
    
    def send_alert(self, alert_info: AlertInfo) -> bool:
        """
        Send an email alert.
        
        Args:
            alert_info: Information about the alert to send
            
        Returns:
            bool: True if email was successfully sent
        """
        if not self.enabled:
            return False
        
        # Check if SMTP is configured
        if not self._is_configured():
            logger.warning("Email provider not properly configured")
            return False
        
        # Check if recipients are configured
        if not self.recipients:
            logger.warning("No email recipients configured")
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
            logger.debug(f"Alert level {level.name} below minimum {self.min_level.name}, not sending email")
            return False
        
        # Check cooldown period
        with self.email_lock:
            current_time = alert_info.timestamp
            
            if self.last_email_time is not None:
                time_since_last = (current_time - self.last_email_time).total_seconds()
                
                if time_since_last < self.cooldown_period:
                    logger.debug(f"Email alert in cooldown period, skipping")
                    return False
            
            # Update last email time
            self.last_email_time = current_time
        
        # Send email in a separate thread to avoid blocking
        thread = threading.Thread(
            target=self._send_email,
            args=(alert_info,),
            daemon=True
        )
        thread.start()
        
        self._log_alert(alert_info, True)
        return True
    
    def _is_configured(self) -> bool:
        """
        Check if the email provider is properly configured.
        
        Returns:
            bool: True if configured
        """
        return (
            self.smtp_server and
            self.smtp_port and
            self.username and
            self.password and
            self.sender
        )
    
    def _send_email(self, alert_info: AlertInfo) -> None:
        """
        Send an email using SMTP.
        
        Args:
            alert_info: Information about the alert to send
        """
        try:
            # Convert AlertLevel to string if needed
            level = alert_info.level.to_string() if isinstance(alert_info.level, AlertLevel) else alert_info.level
            
            # Create subject with level
            subject = f"{self.subject_prefix} [{level.upper()}] {alert_info.app_name}"
            
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.sender
            msg["To"] = ", ".join(self.recipients)
            msg["Subject"] = subject
            
            # Create message body with alert details
            body = f"""
            <html>
            <body>
                <h2>FocusGuard Alert</h2>
                <p><strong>Application:</strong> {alert_info.app_name}</p>
                <p><strong>Level:</strong> {level.upper()}</p>
                <p><strong>Message:</strong> {alert_info.message}</p>
                <p><strong>Time:</strong> {alert_info.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
            """
            
            # Add window information if available
            if alert_info.window_title:
                body += f"<p><strong>Window Title:</strong> {alert_info.window_title}</p>"
            if alert_info.window_url:
                body += f"<p><strong>URL:</strong> {alert_info.window_url}</p>"
            
            body += """
            </body>
            </html>
            """
            
            # Attach body to message
            msg.attach(MIMEText(body, "html"))
            
            # Connect to SMTP server and send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent to {len(self.recipients)} recipients")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
    
    def add_recipient(self, email: str) -> None:
        """
        Add an email recipient.
        
        Args:
            email: Email address to add
        """
        if email not in self.recipients:
            self.recipients.append(email)
            self.config["recipients"] = self.recipients
    
    def remove_recipient(self, email: str) -> bool:
        """
        Remove an email recipient.
        
        Args:
            email: Email address to remove
            
        Returns:
            bool: True if recipient was removed
        """
        if email in self.recipients:
            self.recipients.remove(email)
            self.config["recipients"] = self.recipients
            return True
        return False
    
    def set_smtp_credentials(self, server: str, port: int, username: str, password: str, use_tls: bool = True) -> None:
        """
        Set SMTP server credentials.
        
        Args:
            server: SMTP server address
            port: SMTP server port
            username: SMTP username
            password: SMTP password
            use_tls: Whether to use TLS
        """
        self.smtp_server = server
        self.smtp_port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        
        # Update configuration
        self.config["smtp_server"] = server
        self.config["smtp_port"] = port
        self.config["username"] = username
        self.config["password"] = password
        self.config["use_tls"] = use_tls
