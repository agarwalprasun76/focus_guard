"""
Test script to verify the refactored alert system functionality.
This script tests:
1. Sound alerts with level-specific sound files
2. Popup alerts with platform-specific implementations
3. Alert escalation based on frequency
"""
import sys
import os
import time
from datetime import datetime

# Add parent directory to path to import from core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.alert_system.alert_system import AlertSystem
from core.alert_system.popup_alert import PopupAlertProvider
from core.alert_system.sound_alert import SoundAlertProvider

def test_alert_system():
    """Test the refactored alert system."""
    print("Testing refactored alert system...")
    
    # Create alert system with popup and sound providers
    config = {
        "cooldown_period": 0,  # No cooldown for testing
        "escalation_threshold": 2,  # Escalate after 2 alerts
        "escalation_window": 60,  # Within 1 minute
        "popup_alert": {
            "enabled": True,
            "popup_duration": 3  # Reduced to 3 seconds for faster testing
        },
        "sound_alert": {
            "enabled": True,
            "volume": 0.7,
            "repeat_count": 1
        },
        # Use a temporary directory for alert history to avoid persistence between runs
        "data_directory": os.path.join(os.path.dirname(__file__), "temp_test_data")
    }
    
    # Clear any existing alert history
    temp_dir = os.path.join(os.path.dirname(__file__), "temp_test_data")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    history_file = os.path.join(temp_dir, "alert_history.json")
    if os.path.exists(history_file):
        os.remove(history_file)
    
    # Create alert system and explicitly add providers
    alert_system = AlertSystem(config=config)
    
    # Debug: Print the providers that were initialized
    print("Initialized providers:")
    for provider in alert_system.providers:
        print(f"  - {provider.__class__.__name__} (enabled: {provider.enabled})")
    
    # Explicitly add providers to ensure they're present
    popup_provider = PopupAlertProvider(config.get("popup_alert", {}))
    sound_provider = SoundAlertProvider(config.get("sound_alert", {}))
    
    # Make sure providers are enabled
    popup_provider.enabled = True
    sound_provider.enabled = True
    
    # Add providers to alert system
    alert_system.add_provider(popup_provider)
    alert_system.add_provider(sound_provider)
    
    # Test window info - ensure ASCII-only characters to avoid encoding issues
    window_info = {
        "app_name": "TestApp",
        "window_title": "Test Window - Alert System Test",
        "pid": 12345,
        "timestamp": datetime.now().isoformat()
    }
    
    # Test normal alert
    print("\n1. Testing normal alert...")
    # First alert should be normal level
    level = alert_system._determine_alert_level(window_info['app_name'])
    print(f"Current alert level: {level}")
    print("Debug: Popup provider enabled:", popup_provider.enabled)
    print("Debug: Sound provider enabled:", sound_provider.enabled)
    result = alert_system.alert(window_info, "This is a normal test alert")
    print(f"Alert sent successfully: {result}")
    print("Waiting for 1 second...")
    time.sleep(1)  # Reduced wait time for faster testing
    
    # Test warning alert (second alert should escalate to warning)
    print("\n2. Testing warning alert (escalation)...")
    # Force a warning level by adding another alert to history
    alert_system._track_alert(window_info['app_name'])  # Add another alert to history
    level = alert_system._determine_alert_level(window_info['app_name'])
    print(f"Current alert level: {level}")
    result = alert_system.alert(window_info, "This is a warning test alert")
    print(f"Alert sent successfully: {result}")
    print("Waiting for 1 second...")
    time.sleep(1)  # Reduced wait time for faster testing
    
    # Test critical alert (third alert should escalate to critical)
    print("\n3. Testing critical alert (escalation)...")
    # Force a critical level by adding more alerts to history
    alert_system._track_alert(window_info['app_name'])  # Add another alert to history
    alert_system._track_alert(window_info['app_name'])  # Add another alert to history
    level = alert_system._determine_alert_level(window_info['app_name'])
    print(f"Current alert level: {level}")
    result = alert_system.alert(window_info, "This is a critical test alert")
    print(f"Alert sent successfully: {result}")
    
    # Wait a bit longer to allow popups to be visible
    print("Waiting for 5 seconds to allow popups to be visible...")
    time.sleep(5)
    
    print("\nAlert test completed. Check if you received the alerts with proper escalation.")
    print("You should have seen:")
    print("1. Normal alert (blue/default color)")
    print("2. Warning alert (orange/yellow color)")
    print("3. Critical alert (red color)")
    print("\nIf all alerts were displayed with proper escalation, the refactoring was successful.")

if __name__ == "__main__":
    test_alert_system()
