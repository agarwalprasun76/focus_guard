"""
FocusGuard – Adaptive Focus & Distraction Monitor with Calendar and Domain Integration
This demo shows how to integrate calendar-based domain allowance with the activity monitor.
"""
import sys
import os
import time
import datetime
import re
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from core.task_manager import TaskManager
from core.activity_monitor.activity_monitor import ActivityMonitor
from core.distraction_detector.distraction_detector import DistractionDetector
from core.calendar.calendar_integration import GoogleCalendarClient
from core.calendar.calendar_context import get_current_context, get_current_event
from core.calendar.calendar_domain_allowance import CalendarDomainAllowance, get_calendar_domain_allowance
from core.domain_classifier.domain_classifier import classify_domain
from core.domain_classifier.filter_domain import filter_domain
from utils.time_utils import get_current_time

def safe_print(msg):
    """Print safely, handling encoding issues."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', errors='replace').decode())

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
        r'(\w+\.[a-z]{2,})(?:\s|$)',  # Simple domain.tld pattern
    ]
    
    for pattern in patterns:
        match = re.search(pattern, window_title.lower())
        if match:
            return match.group(1).lower()
    
    return None

def get_browser_domains() -> Dict[str, str]:
    """Return a dictionary mapping browser process names to their common names."""
    return {
        'chrome.exe': 'Google Chrome',
        'firefox.exe': 'Mozilla Firefox',
        'msedge.exe': 'Microsoft Edge',
        'safari.exe': 'Safari',
        'opera.exe': 'Opera',
        'brave.exe': 'Brave',
        'vivaldi.exe': 'Vivaldi',
        'iexplore.exe': 'Internet Explorer',
    }

class CalendarDomainMonitor:
    """
    Monitors active windows and checks them against calendar-based domain allowances.
    """
    
    def __init__(self, calendar_id: str = 'primary', test_domains: bool = False):
        # Initialize calendar client
        try:
            self.calendar_client = GoogleCalendarClient(calendar_id=calendar_id)
            self.calendar_enabled = True
            safe_print(f"[INFO] Calendar integration enabled for calendar: {calendar_id}")
        except Exception as e:
            safe_print(f"[WARNING] Calendar integration failed: {str(e)}")
            self.calendar_enabled = False
            self.calendar_client = None
            
        # Test domains flag
        self.test_domains = test_domains
        
        # Initialize calendar domain allowance if calendar is enabled
        if self.calendar_enabled:
            self.domain_allowance = get_calendar_domain_allowance(self.calendar_client)
            safe_print("[INFO] Calendar domain allowance system initialized")
        else:
            self.domain_allowance = None
        
        # Initialize core components
        self.activity_monitor = ActivityMonitor()
        
        # Default allowed apps (fallback if no calendar context)
        self.allowed_apps = ['code.exe', 'explorer.exe', 'chrome.exe', 'firefox.exe']
        self.distraction_detector = DistractionDetector(self.allowed_apps)
        
        # Browser identification
        self.browsers = get_browser_domains()
    
    def extract_domain_from_window(self, window_info: Dict[str, str]) -> Optional[str]:
        """
        Extract domain from window info if it's a browser window.
        Returns the domain or None if not a browser or no domain found.
        """
        app_name = window_info.get('app_name', '').lower()
        window_title = window_info.get('window_title', '')
        
        # Check if this is a browser app
        if any(browser in app_name for browser in self.browsers.keys()):
            return extract_domain_from_title(window_title)
        
        return None
    
    def check_window(self, window_info: Dict[str, str]) -> Tuple[bool, str, Optional[str]]:
        """
        Check if a window is allowed based on calendar context and domain.
        
        Returns:
            Tuple of (is_allowed, reason, domain)
        """
        app_name = window_info.get('app_name', '').lower()
        window_title = window_info.get('window_title', '')
        
        # Extract domain if it's a browser
        domain = self.extract_domain_from_window(window_info)
        
        # If no domain found or calendar not enabled, use traditional app-based check
        if not domain or not self.calendar_enabled or not self.domain_allowance:
            is_distraction = self.distraction_detector.is_distracted(window_info)
            return (not is_distraction, 
                    "App allowed" if not is_distraction else "App not in allowed list", 
                    domain)
        
        # Check domain allowance based on calendar context
        proactive_allowed, proactive_reason = self.domain_allowance.is_domain_allowed_proactive(domain)
        reactive_allowed, reactive_reason = self.domain_allowance.is_domain_allowed_reactive(domain, window_title)
        
        # Use reactive mode for final decision
        return reactive_allowed, reactive_reason, domain
    
    def run_monitoring_loop(self, check_interval: int = 10, duration: int = 60):
        """
        Run the monitoring loop for the specified duration.
        
        Args:
            check_interval: Time between checks in seconds
            duration: Total monitoring duration in seconds
        """
        safe_print(f"[FocusGuard] Monitoring started. Will check every {check_interval} seconds for {duration} seconds.")
        checks = 0
        max_checks = duration // check_interval
        
        try:
            while checks < max_checks:
                safe_print(f"[DEBUG] Loop iteration {checks+1}/{max_checks}")
                
                # Update calendar context if enabled
                if self.calendar_enabled and self.domain_allowance:
                    try:
                        # Update calendar context and domain allowances
                        self.domain_allowance.update_context(force=True)
                        current_context = self.domain_allowance._current_context
                        current_event = self.domain_allowance._current_event
                        
                        safe_print(f"[CALENDAR] Current context: {current_context}")
                        
                        if current_event:
                            event_summary = current_event.get('summary', 'No title')
                            safe_print(f"[CALENDAR] Current event: {event_summary}")
                            
                            if self.domain_allowance._semantic_contexts:
                                semantic_contexts = [f"{ctx}({score:.2f})" for ctx, score in self.domain_allowance._semantic_contexts[:3]]
                                safe_print(f"[CALENDAR] Semantic contexts: {', '.join(semantic_contexts)}")
                        
                    except Exception as e:
                        safe_print(f"[WARNING] Error updating calendar context: {str(e)}")
                
                # Get active window info
                window_info = self.activity_monitor.get_active_window()
                if not window_info:
                    safe_print("[INFO] No active window detected.")
                    time.sleep(check_interval)
                    checks += 1
                    continue
                
                # Check if window is allowed
                is_allowed, reason, domain = self.check_window(window_info)
                
                # Display results
                app_name = window_info.get('app_name', '').lower()
                window_title = window_info.get('window_title', '')
                
                if is_allowed:
                    safe_print(f"[FOCUS] {app_name}: '{window_title}' (ACTIVE)")
                    if domain:
                        safe_print(f"[FOCUS] Domain '{domain}' is allowed: {reason}")
                else:
                    if domain:
                        safe_print(f"[DISTRACTION] {app_name}: '{window_title}' - Domain '{domain}' not allowed: {reason}")
                    else:
                        safe_print(f"[DISTRACTION] {app_name}: '{window_title}' (ACTIVE)")
                
                # Get top windows for additional distraction detection
                windows = self.activity_monitor.get_top_windows(top_region=200)
                active_hwnd = window_info.get('hwnd') if window_info else None
                
                for w in windows:
                    area = w.get('area', 0)
                    hwnd = w.get('hwnd', None)
                    is_behind_active = (hwnd != active_hwnd and hwnd is not None and active_hwnd is not None)
                    percent = f"{w.get('percent', 0) * 100:.1f}%"
                    safe_print(f"[TOP WINDOW] {w.get('app_name','')}: '{w.get('window_title','')}', area={area}, percent={percent}")
                
                # Hybrid stateful + rule-based distraction detection
                distraction_events = self.distraction_detector.update_and_detect(window_info, windows)
                if distraction_events:
                    for event in distraction_events:
                        safe_print(f"[DISTRACTION EVENT] {event}")
                else:
                    safe_print("[FOCUS - RULES] No distraction events detected.")
                
                time.sleep(check_interval)
                checks += 1
                
            safe_print(f"[FocusGuard] {duration} second monitoring complete.")
            
        except KeyboardInterrupt:
            safe_print("\n[FocusGuard] Monitoring stopped by user.")

def test_domains_mode(domain_allowance):
    """Run in test domains mode to check specific domains against calendar context."""
    safe_print("\n[TEST DOMAINS MODE] Enter domains to test (or 'quit' to exit)")
    safe_print("Example domains: youtube.com, github.com, facebook.com, netflix.com\n")
    
    try:
        # Update context first - with memory usage tracking
        safe_print("[MEMORY] Updating calendar context...")
        import gc
        gc.collect()  # Force garbage collection before update
        
        # Limit time range for calendar events to reduce memory usage
        now = datetime.datetime.now(datetime.timezone.utc)
        start_time = now - datetime.timedelta(hours=1)
        end_time = now + datetime.timedelta(hours=24)
        domain_allowance.update_context(force=True, start_time=start_time, end_time=end_time)
        
        current_context = domain_allowance._current_context
        safe_print(f"[CALENDAR] Current context: {current_context}")
        
        if domain_allowance._current_event:
            event_summary = domain_allowance._current_event.get('summary', 'No title')
            safe_print(f"[CALENDAR] Current event: {event_summary}")
            
            if domain_allowance._semantic_contexts:
                # Limit to top 3 contexts to avoid memory issues
                semantic_contexts = [f"{ctx}({score:.2f})" for ctx, score in domain_allowance._semantic_contexts[:3]]
                safe_print(f"[CALENDAR] Semantic contexts: {', '.join(semantic_contexts)}")
    except Exception as e:
        safe_print(f"[ERROR] Failed to update calendar context: {str(e)}")
    
    # Test loop
    while True:
        try:
            domain = input("\nEnter domain to test (or 'quit'): ").strip().lower()
            if domain == 'quit':
                break
            
            if not domain:
                continue
                
            # Add domain suffix if not provided
            if '.' not in domain:
                domain += '.com'
            
            # Run garbage collection before each test to prevent memory buildup
            gc.collect()
            
            # Test both modes with timeout protection
            try:
                # Set a timeout for domain checks to prevent hanging
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("Domain check timed out")
                
                # Set 5-second timeout
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(5)
                
                proactive_allowed, proactive_reason = domain_allowance.is_domain_allowed_proactive(domain)
                reactive_allowed, reactive_reason = domain_allowance.is_domain_allowed_reactive(domain)
                
                # Cancel the alarm
                signal.alarm(0)
                
                # Display results
                safe_print(f"\n[DOMAIN] Testing: {domain}")
                safe_print(f"[DOMAIN] Category: {filter_domain(domain)}")
                safe_print(f"[PROACTIVE] {'ALLOWED' if proactive_allowed else 'BLOCKED'}: {proactive_reason}")
                safe_print(f"[REACTIVE] {'ALLOWED' if reactive_allowed else 'BLOCKED'}: {reactive_reason}")
                
            except TimeoutError:
                safe_print(f"\n[ERROR] Domain check for {domain} timed out")
            except Exception as e:
                safe_print(f"\n[ERROR] Failed to check domain {domain}: {str(e)}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            safe_print(f"[ERROR] {str(e)}")
    
    safe_print("\n[TEST DOMAINS MODE] Exiting")

def main() -> None:
    """Main entry point for FocusGuard with calendar and domain integration."""
    # Configure logging to track memory usage
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Import memory_profiler if available
    try:
        import psutil
        def log_memory_usage():
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            safe_print(f"[MEMORY] Current usage: {mem_info.rss / 1024 / 1024:.1f} MB")
    except ImportError:
        def log_memory_usage():
            safe_print("[MEMORY] psutil not available for memory tracking")
    
    # Log initial memory usage
    log_memory_usage()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='FocusGuard with Calendar and Domain Integration')
    parser.add_argument('--calendar-id', type=str, default='primary',
                        help='Calendar ID to use (default: primary)')
    parser.add_argument('--test-domains', action='store_true',
                        help='Run in test domains mode instead of monitoring')
    parser.add_argument('--check-interval', type=int, default=10,
                        help='Time between checks in seconds (default: 10)')
    parser.add_argument('--duration', type=int, default=60,
                        help='Total monitoring duration in seconds (default: 60)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode with additional logging')
    
    args = parser.parse_args()
    
    # Set memory limits
    try:
        import resource
        # Set soft limit to 1GB
        resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, -1))
        safe_print("[MEMORY] Set memory limit to 1GB")
    except (ImportError, AttributeError):
        safe_print("[MEMORY] Could not set memory limits")
    
    # Force garbage collection
    import gc
    gc.collect()
    
    try:
        # Initialize monitor with memory tracking
        safe_print("[MEMORY] Initializing monitor...")
        monitor = CalendarDomainMonitor(calendar_id=args.calendar_id, test_domains=args.test_domains)
        log_memory_usage()
        
        # Run in test domains mode or monitoring mode
        if args.test_domains and monitor.calendar_enabled and monitor.domain_allowance:
            test_domains_mode(monitor.domain_allowance)
        else:
            monitor.run_monitoring_loop(check_interval=args.check_interval, duration=args.duration)
    except MemoryError:
        safe_print("\n[ERROR] Out of memory error occurred. Try limiting the calendar date range or reducing the monitoring duration.")
    except Exception as e:
        safe_print(f"\n[ERROR] An error occurred: {str(e)}")
    
    # Final memory usage
    log_memory_usage()

if __name__ == "__main__":
    main()
