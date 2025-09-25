"""
Test script to trigger critical email alerts with screenshots.
This script will simulate multiple distractions to trigger critical alerts.

Usage:
    python trigger_critical_email.py
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

# Import FocusGuard modules
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
    """Trigger critical email alerts with screenshots."""
    # Set up the logger
    setup_logger({
        "log_level": "INFO",
        "log_to_file": False,
        "console_format": "[%(levelname)s] %(message)s"
    })
    
    # Get a logger for this test script
    logger = get_logger("tests.trigger_critical_email")
    
    # Configure the email provider
    email_config = {
        "email_recipient": "agarwalprasun@gmail.com",  # Parent's email address
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "focusguardapp@gmail.com",  # App's email address
        "smtp_password": "nokbxpigonsffodo",  # App password for focusguardapp@gmail.com
        "use_tls": True,
        "from_name": "FocusGuard App",
        "subject_prefix": "FocusGuard Alert",
        "max_emails_per_day": 5,
        "include_screenshot": True  # Enable screenshot attachments
    }
    
    # Create the alert system with aggressive settings to quickly trigger critical alerts
    config = {
        "email": email_config,
        "cooldown_period": 1,  # 1 second cooldown for quick testing
        "escalation_threshold": 2,  # Escalate after 2 alerts
        "escalation_window": 30  # 30 second window for counting alerts
    }
    
    alert_system = AlertSystem(config=config)
    logger.info("Alert system initialized with email provider")
    
    # Create window info for the test
    window_info = {
        "app_name": "Inappropriate Website",
        "window_title": "Age-Restricted Content",
        "pid": 12345,
        "timestamp": datetime.now().isoformat(),
        "url": "https://example.com/inappropriate",
        "duration": 60  # 1 minute
    }
    
    # Send multiple alerts to trigger escalation to critical level
    logger.info("Sending multiple alerts to trigger escalation...")
    
    for i in range(5):  # Send 5 alerts to ensure we reach critical level
        # Take a screenshot for the 5th alert (which should be critical)
        if i == 4:
            logger.info("Taking screenshot for critical alert...")
            screenshot_data = take_screenshot()
            if screenshot_data:
                window_info["screenshot"] = screenshot_data
                logger.info("Screenshot attached to alert")
        
        # Send the alert
        message = f"Alert {i+1}: Inappropriate content detected!"
        success = alert_system.alert(window_info, message)
        
        if success:
            logger.info(f"Alert {i+1} sent successfully!")
        else:
            logger.error(f"Failed to send alert {i+1}")
        
        # Wait a bit between alerts
        if i < 4:
            logger.info("Waiting 2 seconds before sending next alert...")
            time.sleep(2)
    
    logger.info("\nTest complete!")
    logger.info("Check your inbox for critical alerts with screenshots.")

if __name__ == "__main__":
    main()
