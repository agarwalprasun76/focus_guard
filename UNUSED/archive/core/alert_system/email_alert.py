"""
Email alert provider for FocusGuard.
Sends email notifications when distractions are detected.
"""
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional

from .alert_provider import AlertProvider
from core.logger.logger import get_logger

class EmailAlertProvider(AlertProvider):
    """
    Alert provider that sends email notifications when distractions are detected.
    
    This provider requires SMTP configuration to send emails. It can be configured
    to use different email services like Gmail, Outlook, etc.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the email alert provider.
        
        Args:
            config: Configuration dictionary with required keys:
                - email_recipient: Email address to send alerts to
                - smtp_server: SMTP server address (e.g., smtp.gmail.com)
                - smtp_port: SMTP server port (e.g., 587 for TLS)
                - smtp_username: SMTP username/email
                - smtp_password: SMTP password or app password
                
                Optional keys:
                - use_tls: Whether to use TLS (default: True)
                - use_ssl: Whether to use SSL (default: False)
                - from_name: Name to show in the From field (default: "FocusGuard")
                - subject_prefix: Prefix for email subjects (default: "FocusGuard Alert")
                - include_screenshot: Whether to include screenshots (default: False)
                - max_emails_per_day: Maximum emails to send per day (default: 10)
                - critical_only: Only send emails for critical alerts (default: False)
                - alert_cooldown: Seconds to wait before sending another alert for the same app (default: 300)
        """
        super().__init__(config or {})
        self.logger = get_logger("alert_system.email")
        self.enabled = True
        
        # Track email count to prevent flooding
        self.email_count = 0
        self.last_reset_day = datetime.now().day
        self.max_emails_per_day = self.config.get("max_emails_per_day", 10)
        self.critical_only = self.config.get("critical_only", False)
        self.alert_cooldown = self.config.get("alert_cooldown", 300)  # 5 minutes default
        
        # Track recent alerts to prevent duplicates
        self.recent_alerts = {}  # Dictionary to track recent alerts by app and level
        
        # Check if we have the required configuration
        self._check_configuration()
        
    def _check_configuration(self) -> None:
        """
        Check if the provider has the required configuration.
        If not, log a warning and disable the provider.
        """
        required_keys = ["email_recipient", "smtp_server", "smtp_username", "smtp_password"]
        missing_keys = [key for key in required_keys if key not in self.config]
        
        if missing_keys:
            self.logger.warning(
                f"Email alert provider is missing required configuration: {', '.join(missing_keys)}"
                f" - provider will be disabled"
            )
            self.enabled = False
        
    def send_alert(self, window_info: Dict[str, Any], message: str, level: str = "normal") -> bool:
        """
        Send an email alert.
        
        Args:
            window_info: Information about the window causing the distraction
            message: Alert message
            level: Alert level ("normal", "warning", or "critical")
            
        Returns:
            bool: True if alert was successfully sent
        """
        if not self.enabled:
            self.logger.debug("Email alert provider is disabled, skipping alert")
            return False
            
        # Skip non-critical alerts if critical_only is enabled
        if self.critical_only and level != "critical":
            self.logger.debug(f"Skipping {level} alert because critical_only is enabled")
            return True  # Return True because we're handling this appropriately
        
        # Check for duplicate alerts
        app_name = window_info.get("app_name", "unknown")
        alert_key = f"{app_name}:{level}"
        current_time = time.time()
        
        if alert_key in self.recent_alerts:
            last_alert_time = self.recent_alerts[alert_key]
            time_since_last = current_time - last_alert_time
            
            if time_since_last < self.alert_cooldown:
                self.logger.debug(
                    f"Skipping duplicate alert for {app_name} (level: {level}), "
                    f"last sent {time_since_last:.1f} seconds ago"
                )
                return True  # Return True because we're handling this appropriately
        
        # Update the recent alerts dictionary
        self.recent_alerts[alert_key] = current_time
        
        # Reset email count if it's a new day
        current_day = datetime.now().day
        if current_day != self.last_reset_day:
            self.email_count = 0
            self.last_reset_day = current_day
        
        # Check if we've exceeded the daily email limit
        if self.email_count >= self.max_emails_per_day:
            self.logger.warning(
                f"Daily email limit reached ({self.max_emails_per_day}), skipping alert"
            )
            return False
        
        # Get configuration values
        recipient = self.config["email_recipient"]
        smtp_server = self.config["smtp_server"]
        smtp_port = self.config.get("smtp_port", 587)
        smtp_username = self.config["smtp_username"]
        smtp_password = self.config["smtp_password"]
        use_tls = self.config.get("use_tls", True)
        use_ssl = self.config.get("use_ssl", False)
        from_name = self.config.get("from_name", "FocusGuard")
        subject_prefix = self.config.get("subject_prefix", "FocusGuard Alert")
        
        try:
            import smtplib
            from email.message import EmailMessage
            from email.utils import formataddr
            
            # Create email message
            msg = EmailMessage()
            
            # Set email content
            msg.set_content(self._format_email_content(window_info, message, level))
            
            # Set email headers
            msg["Subject"] = f"{subject_prefix} - {level.capitalize()}"
            msg["From"] = formataddr((from_name, smtp_username))
            msg["To"] = recipient
            
            # Add timestamp header for tracking
            msg["X-FocusGuard-Timestamp"] = datetime.now().isoformat()
            msg["X-FocusGuard-Level"] = level
            
            # Include screenshot if available and enabled
            self.logger.debug(f"Screenshot config: include_screenshot={self.config.get('include_screenshot', False)}")
            self.logger.debug(f"Screenshot in window_info: {'screenshot' in window_info}")
            if 'screenshot' in window_info:
                self.logger.debug(f"Screenshot data length: {len(window_info.get('screenshot', ''))}")
                
            if (self.config.get("include_screenshot", False) and 
                "screenshot" in window_info and 
                window_info["screenshot"]):
                
                import base64
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText
                from email.mime.image import MIMEImage
                
                # Convert to multipart message
                multipart_msg = MIMEMultipart()
                multipart_msg["Subject"] = msg["Subject"]
                multipart_msg["From"] = msg["From"]
                multipart_msg["To"] = msg["To"]
                multipart_msg["X-FocusGuard-Timestamp"] = msg["X-FocusGuard-Timestamp"]
                multipart_msg["X-FocusGuard-Level"] = msg["X-FocusGuard-Level"]
                
                # Add text content
                text_part = MIMEText(self._format_email_content(window_info, message, level))
                multipart_msg.attach(text_part)
                
                # Add screenshot
                try:
                    # Decode the base64 image data
                    image_data = base64.b64decode(window_info["screenshot"])
                    
                    # Try to detect image format based on magic bytes
                    image_format = 'png'  # Default format
                    
                    # Check for common image signatures
                    if image_data.startswith(b'\xff\xd8'):  # JPEG
                        image_format = 'jpeg'
                    elif image_data.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
                        image_format = 'png'
                    elif image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a'):  # GIF
                        image_format = 'gif'
                    elif image_data.startswith(b'BM'):  # BMP
                        image_format = 'bmp'
                    else:
                        self.logger.warning("Could not detect image format, defaulting to PNG")
                    
                    # Create image attachment with explicit subtype
                    image = MIMEImage(image_data, _subtype=image_format)
                    image.add_header("Content-Disposition", "attachment", filename=f"distraction.{image_format}")
                    multipart_msg.attach(image)
                    
                    # Replace msg with multipart message
                    msg = multipart_msg
                    self.logger.debug(f"Screenshot attached successfully as {image_format} image")
                except KeyError:
                    self.logger.debug("No screenshot provided in window_info")
                except base64.binascii.Error as e:
                    self.logger.error(f"Invalid base64 data for screenshot: {e}")
                except Exception as e:
                    self.logger.error(f"Failed to attach screenshot: {e}", exc_info=True)
            
            # Connect to SMTP server and send email
            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                if use_tls:
                    server.starttls()
            
            try:
                # Attempt to login with provided credentials
                server.login(smtp_username, smtp_password)
                
                # If login successful, send the email
                server.send_message(msg)
                server.quit()
                
                # Increment email count
                self.email_count += 1
                
                self.logger.info(
                    f"Email alert sent to {recipient} (level: {level}, "
                    f"count: {self.email_count}/{self.max_emails_per_day})"
                )
                return True
                
            except smtplib.SMTPAuthenticationError as auth_error:
                # Specific handling for authentication errors
                self.logger.error(f"Email authentication failed: {auth_error}")
                self.logger.info("For Gmail accounts with 2FA enabled, you need to use an App Password instead of your regular password.")
                self.logger.info("Visit https://myaccount.google.com/apppasswords to generate an App Password.")
                
                # Make sure to close the connection
                try:
                    server.quit()
                except:
                    pass
                    
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}", exc_info=True)
            return False
    
    def _format_email_content(self, window_info: Dict[str, Any], message: str, level: str) -> str:
        """
        Format the email content.
        
        Args:
            window_info: Information about the window causing the distraction
            message: Alert message
            level: Alert level
            
        Returns:
            str: Formatted email content
        """
        app_name = window_info.get("app_name", "Unknown")
        window_title = window_info.get("window_title", "")
        timestamp = window_info.get("timestamp", datetime.now().isoformat())
        
        # Format timestamp if it's a string
        if isinstance(timestamp, str):
            try:
                timestamp_obj = datetime.fromisoformat(timestamp)
                timestamp = timestamp_obj.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pass
        elif isinstance(timestamp, datetime):
            timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
        # Create email content
        content = f"""
FocusGuard Distraction Alert
===========================

Level: {level.upper()}
Time: {timestamp}

Message: {message}

Distraction Details:
- Application: {app_name}
- Window Title: {window_title}
"""
        
        # Add additional window info if available
        if "url" in window_info:
            content += f"- URL: {window_info['url']}\n"
            
        if "duration" in window_info:
            duration_sec = window_info["duration"]
            if duration_sec < 60:
                duration_str = f"{duration_sec} seconds"
            else:
                minutes = duration_sec // 60
                seconds = duration_sec % 60
                duration_str = f"{minutes} minutes, {seconds} seconds"
            content += f"- Duration: {duration_str}\n"
            
        # Add footer
        content += """
---
This is an automated alert from your FocusGuard application.
To configure email alerts, update your FocusGuard settings.
"""
        
        return content
