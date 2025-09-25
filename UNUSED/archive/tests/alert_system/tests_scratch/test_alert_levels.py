"""
Test script for demonstrating different alert levels with visual styling.
This script directly triggers alerts with specific levels to show the visual differences.
"""
import sys
import os
import time
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.alert_system.alert_system import AlertSystem
from core.alert_system.popup_alert import PopupAlertProvider
from core.alert_system.sound_alert import SoundAlertProvider

def main():
    """Test different alert levels with direct level specification."""
    print("Starting alert levels test...")
    
    # Create alert system with popup and sound providers
    alert_system = AlertSystem(config={
        "cooldown_period": 1  # Short cooldown for testing
    })
    
    # Add providers
    popup_provider = PopupAlertProvider(config={
        "popup_duration": 0  # 0 means no auto-close
    })
    
    sound_provider = SoundAlertProvider(config={
        "volume": 0.8,
        "repeat_count": 2,
        "repeat_interval": 0.5
    })
    
    # Add providers to alert system
    alert_system.add_provider(popup_provider)
    alert_system.add_provider(sound_provider)
    
    # Test different alert levels
    test_alerts = [
        {
            "app_name": "SocialMedia.exe",
            "window_title": "Social Media Distraction",
            "level": "normal",
            "message": "NORMAL ALERT\nYou're getting distracted by social media.\nTry to focus on your work."
        },
        {
            "app_name": "YouTube.exe",
            "window_title": "YouTube - Entertainment Videos",
            "level": "warning",
            "message": "WARNING ALERT\nYou've spent too much time on YouTube!\nReturn to your task immediately."
        },
        {
            "app_name": "Games.exe",
            "window_title": "Online Game - Battle Arena",
            "level": "critical",
            "message": "CRITICAL ALERT\nYou should not be playing games during work hours.\nClose this application now!"
        }
    ]
    
    # Send test alerts with different levels
    for test in test_alerts:
        print(f"\nSending {test['level']} alert for {test['app_name']}...")
        
        # Create window_info dictionary
        window_info = {
            "app_name": test["app_name"],
            "window_title": test["window_title"],
            "pid": "12345",
            "timestamp": datetime.now().isoformat()
        }
        
        # Directly send alert with specific level
        for provider in alert_system.providers:
            provider.send_alert(window_info, test["message"], test["level"])
            print(f"Alert sent via {provider.__class__.__name__}")
        
        print(f"Alert sent with level: {test['level']}")
        print("Waiting for user to dismiss the alert...")
        time.sleep(10)  # Wait between alerts
    
    print("\nTest completed. All alert levels have been demonstrated.")

if __name__ == "__main__":
    main()
