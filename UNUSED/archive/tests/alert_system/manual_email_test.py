"""
Manual test script for the email alert provider.
This script sends a real test email to verify the email alert functionality.

Usage:
    python manual_email_test.py

You'll need to configure your SMTP settings in this file before running.
"""
import os
import sys
import time
from datetime import datetime

# Import the logger module
from core.logger.logger import get_logger, setup_logger

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.alert_system.email_alert import EmailAlertProvider

def main():
    """Send a test email using the EmailAlertProvider."""
    # Set up the logger
    setup_logger({
        "log_level": "INFO",
        "log_to_file": False,
        "console_format": "[%(levelname)s] %(message)s"
    })
    
    # Get a logger for this test script
    logger = get_logger("tests.email_alert")
    
    # Configure the email provider with the FocusGuard app email account
    config = {
        "email_recipient": "agarwalprasun@gmail.com",  # Parent's email address
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "focusguardapp@gmail.com",  # App's email address
        "smtp_password": "nokbxpigonsffodo",  # App password for focusguardapp@gmail.com
        "use_tls": True,
        "from_name": "FocusGuard App",
        "subject_prefix": "FocusGuard Alert",
        "max_emails_per_day": 5,
        "include_screenshot": False
    }
    
    # Check if password is provided
    if not config["smtp_password"]:
        logger.error("You must set the smtp_password in the script before running.")
        logger.info("\nFor Gmail, you'll need to create an App Password:")
        logger.info("1. Go to your Google Account > Security")
        logger.info("2. Under 'Signing in to Google', select 'App passwords'")
        logger.info("3. Generate a new app password for 'Mail' and your device")
        logger.info("4. Copy the 16-character password (no spaces) and paste it in this script")
        logger.info("\nNOTE: Regular passwords won't work if 2FA is enabled on the account.")
        logger.info("App passwords are required when using Gmail with 2FA enabled.")
        logger.info("\nVisit: https://myaccount.google.com/apppasswords to create one.")
        return
    
    # Create the email provider
    provider = EmailAlertProvider(config)
    logger.info("Email alert provider initialized")
    
    # Create window info for the test
    window_info = {
        "app_name": "Manual Test Script",
        "window_title": "Email Alert Test",
        "pid": 12345,
        "timestamp": datetime.now().isoformat(),
        "url": "https://example.com/test",
        "duration": 60  # 1 minute
    }
    
    # Send test emails for each alert level
    levels = ["normal", "warning", "critical"]
    
    for level in levels:
        logger.info(f"Sending {level} test email...")
        message = f"This is a {level} test email from FocusGuard."
        
        # Send the email
        success = provider.send_alert(window_info, message, level)
        
        if success:
            logger.info(f"SUCCESS: {level.upper()} email sent successfully!")
        else:
            logger.error(f"Failed to send {level} email.")
        
        # Wait a bit between emails
        if level != levels[-1]:
            logger.info("Waiting 2 seconds before sending next email...")
            time.sleep(2)
    
    logger.info("\nTest complete!")
    logger.info(f"Check your inbox at {config['email_recipient']} for the test emails.")

if __name__ == "__main__":
    main()
