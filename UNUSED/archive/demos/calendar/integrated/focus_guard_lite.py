"""
FocusGuard – Adaptive Focus & Distraction Monitor with Calendar Integration
This demo shows how to integrate calendar awareness into the main application.
"""
import sys
import os
import time
import datetime
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from core.task_manager import TaskManager
from core.activity_monitor.activity_monitor import ActivityMonitor
from core.distraction_detector.distraction_detector import DistractionDetector
from core.calendar.calendar_integration import GoogleCalendarClient
from core.calendar.calendar_context import get_current_context, get_next_context_change
from core.calendar.distraction_policy import get_policy_for_context
from utils.time_utils import get_current_time

def safe_print(msg):
    """Print safely, handling encoding issues."""
    print(msg.encode('ascii', errors='replace').decode())

def main() -> None:
    """
    Main entry point for FocusGuard with calendar integration.
    """
    # Initialize calendar client
    try:
        calendar_client = GoogleCalendarClient()
        calendar_enabled = True
        safe_print("[INFO] Calendar integration enabled")
    except Exception as e:
        safe_print(f"[WARNING] Calendar integration failed: {str(e)}")
        calendar_enabled = False
    
    # Initialize core components
    activity_monitor = ActivityMonitor()
    
    # Default allowed apps (fallback if no calendar context)
    allowed_apps = ['code.exe', 'explorer.exe', 'chrome.exe', 'firefox.exe']
    distraction_detector = DistractionDetector(allowed_apps)
    
    # Monitoring loop
    safe_print("[FocusGuard] Monitoring started. Will check every 10 seconds for 1 minute.")
    checks = 0
    max_checks = 6  # 1 minute / 10 seconds
    
    try:
        while checks < max_checks:
            print(f"[DEBUG] Loop iteration {checks+1}/{max_checks}")
            
            # Get current calendar context if enabled
            if calendar_enabled:
                try:
                    current_context = get_current_context(calendar_client)
                    safe_print(f"[CALENDAR] Current context: {current_context}")
                    
                    # Get policy for current context
                    policy = get_policy_for_context(current_context)
                    safe_print(f"[POLICY] Using policy for context '{current_context}' with strictness: {policy['strictness']}")
                    
                    # Update distraction detector with policy
                    distraction_detector.allowed_apps = policy.get('allow_apps', [])
                    # In a full implementation, we would also update other aspects of the detector
                    
                    # Get next context change
                    next_change = get_next_context_change(calendar_client)
                    time_until_change = next_change['time'] - datetime.datetime.utcnow()
                    minutes_until_change = time_until_change.total_seconds() / 60
                    
                    if minutes_until_change < 60:
                        safe_print(f"[CALENDAR] Next context change in {minutes_until_change:.1f} minutes to '{next_change['context']}'")
                    
                except Exception as e:
                    safe_print(f"[WARNING] Error getting calendar context: {str(e)}")
            
            # Get active window info
            window_info = activity_monitor.get_active_window()
            if not window_info:
                safe_print("[INFO] No active window detected.")
            else:
                # Active window distraction logic
                is_distraction = distraction_detector.is_distracted(window_info)
                app_name = window_info.get('app_name', '').lower()
                window_title = window_info.get('window_title', '').lower()
                
                if is_distraction:
                    safe_print(f"[DISTRACTION] {app_name}: '{window_title}' (ACTIVE)")
                    
                    # If we have calendar context, provide more specific feedback
                    if calendar_enabled and 'current_context' in locals():
                        if current_context == "meeting":
                            safe_print("[CALENDAR] You're in a meeting! Focus on the discussion.")
                        elif current_context == "focus":
                            safe_print("[CALENDAR] This is your focus time! Stay on task.")
                        elif current_context == "break":
                            safe_print("[CALENDAR] You're on a break, but you might want to avoid this distraction.")
                else:
                    safe_print(f"[FOCUS] {app_name}: '{window_title}' (ACTIVE)")
            
            # Get top windows for additional distraction detection
            windows = activity_monitor.get_top_windows(top_region=200)
            active_hwnd = window_info.get('hwnd') if window_info else None
            
            for w in windows:
                area = w.get('area', 0)
                hwnd = w.get('hwnd', None)
                is_behind_active = (hwnd != active_hwnd and hwnd is not None and active_hwnd is not None)
                percent = f"{w.get('percent', 0) * 100:.1f}%"
                safe_print(f"[TOP WINDOW] {w.get('app_name','')}: '{w.get('window_title','')}', area={area}, percent={percent}")
            
            # Hybrid stateful + rule-based distraction detection
            distraction_events = distraction_detector.update_and_detect(window_info, windows)
            if distraction_events:
                for event in distraction_events:
                    safe_print(f"[DISTRACTION EVENT] {event}")
            else:
                safe_print("[FOCUS - RULES] No distraction events detected.")
            
            time.sleep(10)
            checks += 1
            
        safe_print("[FocusGuard] 1 minute monitoring complete.")
        
    except KeyboardInterrupt:
        safe_print("\n[FocusGuard] Monitoring stopped by user.")

if __name__ == "__main__":
    main()
