"""
Direct test for the alert system.
This script directly triggers alerts without the full FocusGuard application.
"""
import sys
import os
import time
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.alert_system.alert_system import AlertSystem
from core.alert_system.popup_alert import PopupAlertProvider

def main():
    """Test the alert system directly."""
    print("Starting direct alert test...")
    
    # Create a window_info dictionary similar to what would come from activity_monitor
    window_info = {
        "app_name": "DistractingApp.exe",
        "window_title": "Very Distracting Application",
        "pid": "12345",
        "timestamp": datetime.now().isoformat()
    }
    
    # Create alert system with only popup provider
    alert_system = AlertSystem(config={
        "cooldown_period": 1  # Short cooldown for testing
    })
    
    # Add popup provider
    popup_provider = PopupAlertProvider()
    alert_system.add_provider(popup_provider)
    
    # Remove all other providers to isolate popup testing
    alert_system.providers = [popup_provider]
    
    print("Alert system configured with only popup provider")
    print("Sending test alert...")
    
    # Send a direct alert
    success = alert_system.alert(
        window_info=window_info,
        message="This is a direct test alert.\nYou should see this popup notification."
    )
    
    if success:
        print("Alert sent successfully. You should see a popup.")
        print("Waiting for 5 seconds...")
        time.sleep(5)
        print("Test completed.")
    else:
        print("Failed to send alert.")

if __name__ == "__main__":
    main()
