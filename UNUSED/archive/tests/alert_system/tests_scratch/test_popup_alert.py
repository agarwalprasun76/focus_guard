"""
Test script for popup alerts.
This script tests the popup alert functionality in isolation.
"""
import sys
import os
import time

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.alert_system.alert_system import AlertSystem
from core.alert_system.popup_alert import PopupAlertProvider

def main():
    """Test the popup alert functionality."""
    print("Starting popup alert test...")
    
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
        "popup_duration": 0,  # 0 means don't auto-close
        "popup_width": 500,
        "popup_height": 200
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
        message="This is a test alert. You should see this popup window.\n\nPlease click 'Dismiss' when you see this."
    )
    
    if success:
        print("Alert sent successfully. You should see a popup window.")
        print("The popup will stay open until you dismiss it.")
        print("Press Ctrl+C to exit this test.")
        
        # Keep the script running until user interrupts
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nTest completed.")
    else:
        print("Failed to send alert.")

if __name__ == "__main__":
    main()
