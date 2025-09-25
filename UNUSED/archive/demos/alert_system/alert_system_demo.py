"""
Demo script to test the alert system functionality.
Shows how to integrate the alert system with the distraction detector.
"""
import sys
import time
from datetime import datetime
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.alert_system.alert_system import AlertSystem, DesktopNotificationProvider
from core.alert_system.popup_alert import PopupAlertProvider
from core.activity_monitor.activity_monitor import ActivityMonitor
from core.distraction_detector.distraction_detector import DistractionDetector

def safe_print(msg):
    """Print a message safely, handling encoding errors."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', errors='replace').decode())

def main():
    """
    Run a demo of the alert system integrated with distraction detection.
    """
    safe_print("[FocusGuard] Alert System Demo")
    
    # Configure the alert system
    alert_config = {
        "cooldown_period": 10,  # 10 seconds between alerts for the same app
        "escalation_threshold": 2,  # 2 alerts before escalation
        "escalation_window": 60,  # 60 seconds for escalation window
        "desktop_notification": {
            "enabled": True
        },
        "sound_alert": {
            "enabled": True,
            # Sound files would be configured here
        },
        "enable_app_blocking": False  # Set to True to enable app blocking
    }
    
    # Create alert system with desktop notifications and popup alerts
    alert_system = AlertSystem(config=alert_config)
    alert_system.add_provider(PopupAlertProvider({"popup_duration": 15}))
    
    # Define allowed apps (only Windsurf.exe is allowed in this demo)
    allowed_apps = ['Windsurf.exe']
    
    # Create activity monitor and distraction detector
    activity_monitor = ActivityMonitor()
    
    # Create distraction detector with alert callback
    distraction_detector = DistractionDetector(
        allowed_apps=allowed_apps,
        alert_callback=alert_system.alert  # Connect the alert system
    )
    
    safe_print("[FocusGuard] Monitoring started. Will check every 5 seconds for 1 minute.")
    safe_print("[FocusGuard] Only 'Windsurf.exe' is allowed. All other apps will trigger alerts.")
    
    # Simple monitoring loop
    checks = 0
    max_checks = 12  # 1 minute / 5 seconds
    
    try:
        while checks < max_checks:
            safe_print(f"[DEBUG] Loop iteration {checks+1}/{max_checks}")
            
            # Get active window
            window_info = activity_monitor.get_active_window()
            if not window_info:
                safe_print("[INFO] No active window detected.")
                time.sleep(5)
                checks += 1
                continue
                
            # Print window info
            app_name = window_info.get('app_name', '').lower()
            window_title = window_info.get('window_title', '').lower()
            safe_print(f"[ACTIVE] {app_name}: '{window_title}'")
            
            # Check if it's a distraction
            if distraction_detector.is_distracted(window_info):
                safe_print(f"[DISTRACTION] {app_name}: '{window_title}'")
                
                # This will trigger the alert system via the callback
                distraction_detector.update_activity(window_info)
                
                # You could also trigger alerts directly:
                # alert_system.alert(
                #     window_info, 
                #     f"You're distracted by {app_name}! Return to your task."
                # )
            else:
                safe_print(f"[FOCUS] {app_name}: '{window_title}'")
            
            # Get top windows for additional monitoring
            top_windows = activity_monitor.get_top_windows(top_region=200)
            
            # Check for distractions in top windows
            for w in top_windows:
                if w.get('hwnd') != window_info.get('hwnd') and distraction_detector.is_distracted(w):
                    safe_print(f"[DISTRACTION] {w.get('app_name','')}: '{w.get('window_title','')}' (TOP WINDOW)")
                    
                    # For top windows, we might want to alert only if they take up significant screen space
                    if w.get('percent', 0) > 0.3:  # More than 30% of screen
                        alert_system.alert(
                            w, 
                            f"Distracting window visible: {w.get('app_name','')}. Minimize it to stay focused."
                        )
            
            # Wait before next check
            time.sleep(5)
            checks += 1
            
        safe_print("[FocusGuard] Demo completed.")
        
    except KeyboardInterrupt:
        safe_print("\n[FocusGuard] Demo stopped by user.")

if __name__ == "__main__":
    main()
