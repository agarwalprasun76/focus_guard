"""
Example script showing how to integrate critical email alerts with screenshots
into the FocusGuard application workflow.

This demonstrates how to:
1. Configure the alert system with email alerts enabled
2. Take screenshots when distractions are detected
3. Send critical alerts with screenshots for serious distractions
"""
import os
import sys
import time
import base64
from datetime import datetime
from pathlib import Path
from PIL import ImageGrab

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import FocusGuard modules
from core.logger.logger import get_logger, setup_logger
from core.alert_system.alert_system import AlertSystem

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
    """
    Example of integrating critical email alerts with screenshots.
    
    This shows how to:
    1. Configure the AlertSystem with email alerts
    2. Detect distractions and determine severity
    3. Take screenshots for critical alerts
    4. Send alerts through the alert system
    """
    # Set up the logger
    setup_logger({
        "log_level": "INFO",
        "log_to_file": False,
        "console_format": "[%(levelname)s] %(message)s"
    })
    
    # Get a logger for this example
    logger = get_logger("examples.critical_alert")
    
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
    
    # Create the alert system with email provider enabled
    config = {
        "email": email_config,
        "cooldown_period": 60,  # 1 minute cooldown between alerts for the same app
        "escalation_threshold": 3,  # Number of alerts before escalation
        "escalation_window": 300,  # 5 minute window for counting alerts
        "data_directory": os.path.expanduser("~/.focusguard"),  # Where to store alert history
        "enable_app_blocking": False  # Set to True to enable app blocking for critical alerts
    }
    
    # Initialize the alert system
    alert_system = AlertSystem(config=config)
    logger.info("Alert system initialized with email provider")
    
    # Simulate detecting a distraction
    logger.info("Simulating distraction detection...")
    
    # List of simulated distractions with increasing severity
    distractions = [
        {
            "app_name": "Social Media",
            "window_title": "Social Media - Feed",
            "severity": "low",
            "message": "Social media detected during study time"
        },
        {
            "app_name": "Gaming App",
            "window_title": "Online Game",
            "severity": "medium",
            "message": "Gaming detected during school hours"
        },
        {
            "app_name": "Inappropriate Website",
            "window_title": "Age-Restricted Content",
            "severity": "high",
            "message": "CRITICAL: Inappropriate content detected"
        }
    ]
    
    # Process each distraction
    for distraction in distractions:
        logger.info(f"Detected: {distraction['app_name']} - {distraction['window_title']}")
        logger.info(f"Severity: {distraction['severity']}")
        
        # Create window info
        window_info = {
            "app_name": distraction["app_name"],
            "window_title": distraction["window_title"],
            "pid": 12345,
            "timestamp": datetime.now().isoformat(),
            "duration": 60  # 1 minute
        }
        
        # For high severity distractions, take a screenshot
        if distraction["severity"] == "high":
            logger.info("Taking screenshot for critical alert...")
            screenshot_data = take_screenshot()
            if screenshot_data:
                window_info["screenshot"] = screenshot_data
                logger.info("Screenshot attached to alert")
        
        # Send the alert
        success = alert_system.alert(window_info, distraction["message"])
        
        if success:
            logger.info(f"Alert sent for {distraction['app_name']}")
        else:
            logger.error(f"Failed to send alert for {distraction['app_name']}")
        
        # Wait between alerts to demonstrate escalation
        time.sleep(3)
    
    logger.info("\nExample complete!")
    logger.info("The alert system has sent alerts with automatic escalation.")
    logger.info("Check your inbox for any critical alerts with screenshots.")

if __name__ == "__main__":
    main()
