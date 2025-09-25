"""
Test script for enhanced popup alerts with sound effects.
This script demonstrates the improved popup alerts with different severity levels.
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
    """Test the enhanced alert system with different severity levels."""
    print("Starting enhanced alert test...")
    
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
            "message": "You're getting distracted by social media.\nTry to focus on your work."
        },
        {
            "app_name": "YouTube.exe",
            "window_title": "YouTube - Entertainment Videos",
            "message": "You've spent too much time on YouTube!\nReturn to your task immediately."
        },
        {
            "app_name": "Games.exe",
            "window_title": "Online Game - Battle Arena",
            "message": "CRITICAL DISTRACTION DETECTED!\nYou should not be playing games during work hours."
        }
    ]
    
    # Send test alerts with increasing severity
    for i, test in enumerate(test_alerts):
        level_names = ["normal", "warning", "critical"]
        current_level = level_names[i]
        print(f"\nSending {current_level} alert ({i+1}/{len(test_alerts)})...")
        
        # Create window_info dictionary
        window_info = {
            "app_name": test["app_name"],
            "window_title": test["window_title"],
            "pid": "12345",
            "timestamp": datetime.now().isoformat()
        }
        
        # Force escalation level for testing
        # We'll manually set the escalation level by manipulating the alert history
        app_name = test["app_name"]
        
        # Clear any existing history for this app
        if app_name in alert_system.alert_history:
            del alert_system.alert_history[app_name]
            
        # For warning level (second test), add one previous alert
        # For critical level (third test), add two previous alerts
        if i == 1:  # Warning level
            # Add one alert from 5 minutes ago
            five_min_ago = datetime.now()
            five_min_ago = five_min_ago.replace(minute=five_min_ago.minute - 5)
            alert_system.alert_history[app_name] = [five_min_ago]
            print(f"  Set up history for WARNING level with 1 previous alert")
        elif i == 2:  # Critical level
            # Add two alerts from recent history
            five_min_ago = datetime.now()
            five_min_ago = five_min_ago.replace(minute=five_min_ago.minute - 5)
            three_min_ago = datetime.now()
            three_min_ago = three_min_ago.replace(minute=three_min_ago.minute - 3)
            alert_system.alert_history[app_name] = [five_min_ago, three_min_ago]
            print(f"  Set up history for CRITICAL level with 2 previous alerts")
        
        # Send alert
        success = alert_system.alert(
            window_info=window_info,
            message=test["message"]
        )
        
        if success:
            print(f"Alert sent successfully: {current_level} for {test['app_name']}")
            print("Waiting for user to dismiss the alert...")
            time.sleep(5)  # Wait between alerts
        else:
            print(f"Failed to send alert for {test['app_name']}")
            
        # Give some time for the alert to be shown and dismissed
        print("Waiting for 5 seconds before next alert...")
        time.sleep(5)
    
    print("\nTest completed. All alerts have been demonstrated.")

if __name__ == "__main__":
    main()
