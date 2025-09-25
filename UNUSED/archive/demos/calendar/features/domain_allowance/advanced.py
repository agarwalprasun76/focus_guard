"""
Advanced Domain Allowance

Implements advanced calendar-based domain allowance with full integration.
This demo shows how to integrate calendar-based domain allowance with the activity monitor.

Features:
- Full calendar integration for context awareness
- Domain classification and filtering
- Real-time activity monitoring
- Advanced distraction detection
- Calendar-based domain allowance rules
"""
import sys
import os
import time
import datetime
import re
from pathlib import Path
from typing import Optional, Dict, Any

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from focus_guard.core.task_manager import TaskManager
from focus_guard.core.activity_monitor.activity_monitor import ActivityMonitor
from focus_guard.core.distraction_detector.distraction_detector import DistractionDetector
from focus_guard.core.calendar.calendar_integration import GoogleCalendarClient
from focus_guard.core.calendar.calendar_context import get_current_context, get_next_context_change, get_current_event
from focus_guard.core.calendar.calendar_domain_allowance import CalendarDomainAllowance
from focus_guard.core.domain_classifier.domain_classifier import classify_domain
from focus_guard.core.domain_classifier.filter_domain import filter_domain
from focus_guard.utils.time_utils import get_current_time

def safe_print(msg):
    """Print safely, handling encoding issues."""
    print(msg.encode('ascii', errors='replace').decode())

## the following function should be moved to core\domain_classifier
def extract_domain_from_title(window_title: str) -> Optional[str]:
    """
    Extract domain from window title (usually from browser windows).
    Returns None if no domain is found.
    """
    # Common patterns in browser titles
    patterns = [
        r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)',  # Basic domain
        r'([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)(?:/|\s|$)',  # Domain followed by / or space
        r'(?:at|on)\s+([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)',  # "at domain.com" or "on domain.com"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, window_title)
        if match:
            return match.group(1).lower()
    
    return None

def main() -> None:
    """
    Main entry point for FocusGuard with calendar and domain integration.
    """
    # Initialize calendar client
    try:
        calendar_client = GoogleCalendarClient()
        calendar_enabled = True
        safe_print("[INFO] Calendar integration enabled")
    except Exception as e:
        safe_print(f"[WARNING] Calendar integration failed: {str(e)}")
        calendar_enabled = False
        calendar_client = None
    
    # Initialize calendar domain allowance if calendar is enabled
    if calendar_enabled:
        domain_allowance = CalendarDomainAllowance(calendar_client)
        safe_print("[INFO] Calendar domain allowance system initialized")
    
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
                    # Update calendar context and domain allowances
                    domain_allowance.update_context(force=True)
                    current_context = domain_allowance._current_context
                    current_event = domain_allowance._current_event
                    
                    safe_print(f"[CALENDAR] Current context: {current_context}")
                    
                    if current_event:
                        event_summary = current_event.get('summary', 'No title')
                        safe_print(f"[CALENDAR] Current event: {event_summary}")
                        
                        if domain_allowance._semantic_contexts:
                            semantic_contexts = [f"{ctx}({score:.2f})" for ctx, score in domain_allowance._semantic_contexts[:3]]
                            safe_print(f"[CALENDAR] Semantic contexts: {', '.join(semantic_contexts)}")
                    
                    # Get next context change
                    next_change = get_next_context_change(calendar_client)
                    if next_change:
                        time_until_change = next_change['time'] - datetime.datetime.now(datetime.timezone.utc)
                        minutes_until_change = time_until_change.total_seconds() / 60
                        
                        if minutes_until_change < 60:
                            safe_print(f"[CALENDAR] Next context change in {minutes_until_change:.1f} minutes to '{next_change['context']}'")
                    
                except Exception as e:
                    safe_print(f"[WARNING] Error getting calendar context: {str(e)}")
            
            # Get active window info
            window_info = activity_monitor.get_active_window()
            if not window_info:
                safe_print("[INFO] No active window detected.")
                time.sleep(10)
                checks += 1
                continue
            
            # Extract domain from window title if possible
            app_name = window_info.get('app_name', '').lower()
            window_title = window_info.get('window_title', '')
            domain = None
            
            # Check for browser apps and extract domain
            browsers = ['chrome.exe', 'firefox.exe', 'msedge.exe', 'safari.exe', 'opera.exe', 'brave.exe']
            if any(browser in app_name for browser in browsers):
                domain = extract_domain_from_title(window_title)
                if domain:
                    safe_print(f"[DOMAIN] Extracted domain: {domain}")
                    
                    # Classify domain
                    domain_category = filter_domain(domain)
                    safe_print(f"[DOMAIN] Category: {domain_category}")
            
            # Check if domain is allowed based on calendar context
            if calendar_enabled and domain:
                # Check both proactive and reactive modes
                proactive_allowed, proactive_reason = domain_allowance.is_domain_allowed_proactive(domain)
                reactive_allowed, reactive_reason = domain_allowance.is_domain_allowed_reactive(domain, window_title)
                
                safe_print(f"[DOMAIN ALLOWANCE] Proactive: {proactive_allowed} - {proactive_reason}")
                safe_print(f"[DOMAIN ALLOWANCE] Reactive: {reactive_allowed} - {reactive_reason}")
                
                # Use reactive mode for final decision
                is_domain_distraction = not reactive_allowed
            else:
                is_domain_distraction = False
            
            # Traditional distraction detection (app-based)
            is_app_distraction = distraction_detector.is_distracted(window_info)
            
            # Combined distraction detection
            is_distraction = is_app_distraction or is_domain_distraction
            
            if is_distraction:
                if is_domain_distraction:
                    safe_print(f"[DISTRACTION] {app_name}: '{window_title}' - Domain '{domain}' not allowed in current context")
                else:
                    safe_print(f"[DISTRACTION] {app_name}: '{window_title}' (ACTIVE)")
                
                # If we have calendar context, provide more specific feedback
                if calendar_enabled and current_context:
                    if current_context == "meeting":
                        safe_print("[CALENDAR] You're in a meeting! Focus on the discussion.")
                    elif current_context == "focus":
                        safe_print("[CALENDAR] This is your focus time! Stay on task.")
                    elif current_context == "break":
                        safe_print("[CALENDAR] You're on a break, but you might want to avoid this distraction.")
            else:
                safe_print(f"[FOCUS] {app_name}: '{window_title}' (ACTIVE)")
                if domain:
                    safe_print(f"[FOCUS] Domain '{domain}' is allowed in current context")
            
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
