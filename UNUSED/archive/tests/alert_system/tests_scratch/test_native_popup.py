"""
Test script for native popup alerts.
This script tests the platform-native popup alert functionality.
"""
import sys
import os
import time

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.alert_system.alert_system import AlertSystem
from core.alert_system.popup_alert import PopupAlertProvider

def main():
    """Test the native popup alert functionality."""
    print("Starting native popup alert test...")
    
    # Create a window_info dictionary similar to what would come from activity_monitor
    window_info = {
        "app_name": "TestApp.exe",
        "window_title": "Test Distracting Application",
        "pid": "12345",
        "timestamp": "2025-07-03T12:45:00"
    }
    
    # Create alert system with only popup provider
    alert_system = AlertSystem(config={
        "cooldown_period": 1  # Short cooldown for testing
    })
    
    # Add popup provider with debug settings
    popup_config = {
        "popup_duration": 5  # Short duration for testing
    }
    popup_provider = PopupAlertProvider(popup_config)
    alert_system.add_provider(popup_provider)
    
    # Remove all other providers to isolate popup testing
    alert_system.providers = [popup_provider]
    
    print("Alert system configured with only popup provider")
    print("Sending test alert...")
    
    # Send a test alert
    success = alert_system.alert(
        window_info=window_info,
        message="This is a test alert using native notifications.\nYou should see this popup notification."
    )
    
    if success:
        print("Alert sent successfully. You should see a native notification.")
        print("Waiting for 6 seconds...")
        time.sleep(6)
        print("Test completed.")
    else:
        print("Failed to send alert.")

if __name__ == "__main__":
    main()
