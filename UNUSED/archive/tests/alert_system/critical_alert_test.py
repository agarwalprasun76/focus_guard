"""
Test script for sending critical alerts with screenshots.
This script demonstrates how to send critical alerts with screenshots when distractions are detected.

Usage:
    python critical_alert_test.py
"""
import os
import sys
import time
import base64
from datetime import datetime
from pathlib import Path
from PIL import ImageGrab

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import the logger and alert system
from core.logger.logger import get_logger, setup_logger
from core.alert_system.alert_system import AlertSystem
from core.alert_system.email_alert import EmailAlertProvider

def take_screenshot():
    """Take a screenshot and return it as base64 encoded string."""
    try:
        # Capture the screen
        screenshot = ImageGrab.grab()
        
        # Save to a temporary file
        temp_file = Path("temp_screenshot.png")
        screenshot.save(temp_file)
        
        # Read the file and encode as base64
        with open(temp_file, "rb") as f:
            screenshot_data = base64.b64encode(f.read()).decode("utf-8")
            
        # Clean up the temporary file
        temp_file.unlink()
        
        return screenshot_data
    except Exception as e:
        print(f"Failed to take screenshot: {e}")
        return None

def main():
    """Send a critical alert with screenshot."""
    # Set up the logger
    setup_logger({
        "log_level": "INFO",
        "log_to_file": False,
        "console_format": "[%(levelname)s] %(message)s"
    })
    
    # Get a logger for this test script
    logger = get_logger("tests.critical_alert")
    
    # Configure the email provider with the FocusGuard app email account
    email_config = {
        "email_recipient": "agarwalprasun@gmail.com",  # Parent's email address
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "focusguardapp@gmail.com",  # App's email address
        "smtp_password": "nokbxpigonsffodo",  # App password for focusguardapp@gmail.com
        "use_tls": True,
        "from_name": "FocusGuard App",
        "subject_prefix": "FocusGuard CRITICAL Alert",
        "max_emails_per_day": 5,
        "include_screenshot": True  # Enable screenshot attachments
    }
    
    # Create the email alert provider directly
    email_provider = EmailAlertProvider(email_config)
    logger.info("Email alert provider initialized for critical alerts with screenshots")
    
    # Take a screenshot
    logger.info("Taking screenshot...")
    screenshot_data = take_screenshot()
    
    if not screenshot_data:
        logger.error("Failed to take screenshot, continuing without it")
    
    # Create window info for the test
    window_info = {
        "app_name": "Distraction App",
        "window_title": "Inappropriate Content",
        "pid": 12345,
        "timestamp": datetime.now().isoformat(),
        "url": "https://example.com/inappropriate",
        "duration": 120,  # 2 minutes
        "screenshot": screenshot_data
    }
    
    # Send critical alert with screenshot
    logger.info("Sending critical alert with screenshot...")
    
    # Send email directly with critical level
    message = "CRITICAL ALERT: Inappropriate content detected on child's device!"
    success = email_provider.send_alert(window_info, message, level="critical")
    
    if success:
        logger.info("Critical alert with screenshot sent successfully!")
    else:
        logger.error("Failed to send critical alert with screenshot.")
    
    logger.info("\nTest complete!")
    logger.info(f"Check your inbox at {email_config['email_recipient']} for the critical alert with screenshot.")

if __name__ == "__main__":
    main()
