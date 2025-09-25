"""
Manual test script for alert system components.
This script provides interactive tests for visual and audio verification of alerts.

Usage:
    python test_manual_alerts.py [test_type]
    
    test_type options:
    - basic: Basic popup and sound test
    - levels: Test different alert levels
    - escalation: Test alert escalation
    - all: Run all tests sequentially
"""
import sys
import os
import time
import argparse
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.alert_system.alert_system import AlertSystem
from core.alert_system.popup_alert import PopupAlertProvider
from core.alert_system.sound_alert import SoundAlertProvider

def setup_alert_system(cooldown=0):
    """Create and configure an alert system for testing."""
    config = {
        "cooldown_period": cooldown,
        "escalation_threshold": 2,
        "escalation_window": 60,
        "popup_alert": {
            "enabled": True,
            "popup_duration": 5
        },
        "sound_alert": {
            "enabled": True,
            "volume": 0.7,
            "repeat_count": 1
        }
    }
    
    # Create alert system
    alert_system = AlertSystem(config=config)
    
    # Explicitly add providers to ensure they're present
    popup_provider = PopupAlertProvider(config.get("popup_alert", {}))
    sound_provider = SoundAlertProvider(config.get("sound_alert", {}))
    
    # Make sure providers are enabled
    popup_provider.enabled = True
    sound_provider.enabled = True
    
    # Add providers to alert system
    alert_system.add_provider(popup_provider)
    alert_system.add_provider(sound_provider)
    
    # Debug: Print the providers that were initialized
    print("Initialized providers:")
    for provider in alert_system.providers:
        print(f"  - {provider.__class__.__name__} (enabled: {provider.enabled})")
    
    return alert_system

def create_test_window_info(app_name="TestApp"):
    """Create a test window info dictionary."""
    return {
        "app_name": app_name,
        "window_title": "Test Window",
        "pid": 12345,
        "timestamp": datetime.now().isoformat()
    }

def test_basic_alerts():
    """Test basic popup and sound alerts."""
    print("\n=== Running Basic Alert Test ===")
    alert_system = setup_alert_system(cooldown=1)
    window_info = create_test_window_info()
    
    print("\nTesting normal popup and sound...")
    result = alert_system.alert(window_info, "This is a basic test alert")
    print(f"Alert sent successfully: {result}")
    
    # Wait for alert to be visible
    print("Waiting for 3 seconds...")
    time.sleep(3)
    
    print("Basic alert test completed.")

def test_alert_levels():
    """Test different alert levels."""
    print("\n=== Running Alert Levels Test ===")
    alert_system = setup_alert_system(cooldown=1)
    
    # Test normal alert
    print("\n1. Testing normal alert level...")
    window_info = create_test_window_info("NormalApp")
    alert_system.alert(window_info, "This is a NORMAL level alert", level="normal")
    print("Waiting for 3 seconds...")
    time.sleep(3)
    
    # Test warning alert
    print("\n2. Testing warning alert level...")
    window_info = create_test_window_info("WarningApp")
    alert_system.alert(window_info, "This is a WARNING level alert", level="warning")
    print("Waiting for 3 seconds...")
    time.sleep(3)
    
    # Test critical alert
    print("\n3. Testing critical alert level...")
    window_info = create_test_window_info("CriticalApp")
    alert_system.alert(window_info, "This is a CRITICAL level alert", level="critical")
    print("Waiting for 3 seconds...")
    time.sleep(3)
    
    print("Alert levels test completed.")

def test_alert_escalation():
    """Test alert escalation based on frequency."""
    print("\n=== Running Alert Escalation Test ===")
    alert_system = setup_alert_system(cooldown=0)  # No cooldown for testing
    window_info = create_test_window_info("EscalatingApp")
    
    # Test normal alert
    print("\n1. Testing normal alert...")
    level = alert_system._determine_alert_level(window_info['app_name'])
    print(f"Current alert level: {level}")
    result = alert_system.alert(window_info, "This is a normal test alert")
    print(f"Alert sent successfully: {result}")
    print("Waiting for 3 seconds...")
    time.sleep(3)
    
    # Test warning alert (second alert should escalate to warning)
    print("\n2. Testing warning alert (escalation)...")
    # Force a warning level by adding another alert to history
    alert_system._track_alert(window_info['app_name'])
    level = alert_system._determine_alert_level(window_info['app_name'])
    print(f"Current alert level: {level}")
    result = alert_system.alert(window_info, "This is a warning test alert")
    print(f"Alert sent successfully: {result}")
    print("Waiting for 3 seconds...")
    time.sleep(3)
    
    # Test critical alert (third alert should escalate to critical)
    print("\n3. Testing critical alert (escalation)...")
    # Force a critical level by adding more alerts to history
    alert_system._track_alert(window_info['app_name'])
    alert_system._track_alert(window_info['app_name'])
    level = alert_system._determine_alert_level(window_info['app_name'])
    print(f"Current alert level: {level}")
    result = alert_system.alert(window_info, "This is a critical test alert")
    print(f"Alert sent successfully: {result}")
    
    # Wait a bit longer to allow popups to be visible
    print("Waiting for 5 seconds to allow popups to be visible...")
    time.sleep(5)
    
    print("\nAlert escalation test completed.")
    print("You should have seen:")
    print("1. Normal alert (blue/default color)")
    print("2. Warning alert (orange/yellow color)")
    print("3. Critical alert (red color)")
    print("If all alerts were displayed with proper escalation, the test was successful.")

def main():
    """Run the selected manual tests."""
    parser = argparse.ArgumentParser(description="Run manual alert system tests")
    parser.add_argument("test_type", nargs="?", default="all", 
                        choices=["basic", "levels", "escalation", "all"],
                        help="Type of test to run")
    args = parser.parse_args()
    
    print("=== FocusGuard Alert System Manual Tests ===")
    
    if args.test_type == "basic" or args.test_type == "all":
        test_basic_alerts()
    
    if args.test_type == "levels" or args.test_type == "all":
        test_alert_levels()
    
    if args.test_type == "escalation" or args.test_type == "all":
        test_alert_escalation()
    
    print("\nAll manual tests completed.")

if __name__ == "__main__":
    main()
