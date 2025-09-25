"""
Detailed Activity Tracking

Advanced activity tracking with calendar integration.
Monitors active windows and checks domains against real calendar context.

Features:
- Real-time window activity monitoring
- Calendar context awareness
- Domain classification and filtering
- Memory-efficient implementation
- Detailed logging and reporting

Usage:
    python -m demos.calendar.features.activity_tracking.detailed_tracking [--calendar-id CALENDAR_ID]
"""
import sys
import os
import time
import datetime
import argparse
import re
import gc
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

# Try to import psutil for memory tracking
try:
    import psutil
    def get_memory_usage():
        """Get current memory usage in MB"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
except ImportError:
    def get_memory_usage():
        """Fallback when psutil is not available"""
        return 0

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Import activity monitor modules with absolute imports
try:
    from core.activity_monitor.window_info import get_foreground_window_title, get_foreground_window_process
    
    def get_active_window_info():
        """Get active window info using the actual window_info module"""
        title = get_foreground_window_title()
        process = get_foreground_window_process()
        return {"title": title, "app_name": process}
        
except ImportError:
    print("Warning: Could not import window_info module. Using mock implementation.")
    def get_active_window_info():
        return {"title": "Mock Browser - youtube.com", "app_name": "MockBrowser"}

# Import calendar modules
try:
    from focus_guard.core.calendar.calendar_integration import GoogleCalendarClient
    from focus_guard.core.calendar.calendar_context import get_current_context, get_current_event
    from focus_guard.core.calendar.calendar_domain_allowance import CalendarDomainAllowance, get_calendar_domain_allowance
    from focus_guard.core.domain_classifier.domain_classifier import classify_domain
    from focus_guard.core.domain_classifier.filter_domain import filter_domain
    from focus_guard.utils.time_utils import get_current_time
    CALENDAR_AVAILABLE = True
except ImportError:
    print("Warning: Could not import calendar modules. Using simplified implementation.")
    CALENDAR_AVAILABLE = False

# Browser patterns to extract domains
BROWSER_PATTERNS = [
    r"(?:https?://)?((?:[\w-]+\.)+[\w-]+)",  # Matches domain.com or subdomain.domain.com
    r"(?:[\w-]+\.)+[\w-]+",                  # Fallback pattern
]

# Common browser process names
BROWSER_PROCESSES = [
    "chrome", "firefox", "msedge", "iexplore", "safari", "opera", 
    "brave", "vivaldi", "chromium", "browser", "mozilla"
]

# Domain categories for classification (fallback if domain_classifier not available)
DOMAIN_CATEGORIES = {
    "work": ["office.com", "slack.com", "zoom.us", "github.com", "atlassian.com", "microsoft.com"],
    "social": ["facebook.com", "twitter.com", "instagram.com", "tiktok.com", "snapchat.com", "reddit.com", "linkedin.com"],
    "news": ["cnn.com", "bbc.com", "nytimes.com", "theguardian.com", "reuters.com", "foxnews.com"],
    "shopping": ["amazon.com", "ebay.com", "aliexpress.com", "walmart.com", "etsy.com"],
    "entertainment": ["youtube.com", "netflix.com", "hulu.com", "spotify.com", "twitch.tv"],
    "education": ["khanacademy.org", "coursera.org", "edx.org", "udemy.com", "wikipedia.org"],
}

# Whitelist of always-allowed domains
WHITELIST = ["google.com", "docs.google.com", "drive.google.com", "calendar.google.com"]

# Calendar context rules (fallback if calendar_domain_allowance not available)
CONTEXT_RULES = {
    "focus": {
        "allowed": ["work", "education"],
        "blocked": ["social", "entertainment", "shopping"]
    },
    "meeting": {
        "allowed": ["work", "education"],
        "blocked": ["social", "entertainment", "shopping"]
    },
    "break": {
        "allowed": ["work", "education", "news", "entertainment"],
        "blocked": []
    },
    "none": {
        "allowed": ["work", "education", "news"],
        "blocked": ["social"]
    }
}

def extract_domain_from_title(title):
    """Extract domain from browser window title using regex patterns"""
    if not title:
        return None
        
    title = title.lower()
    
    for pattern in BROWSER_PATTERNS:
        matches = re.search(pattern, title)
        if matches:
            return matches.group(1)
    
    return None

def fallback_classify_domain(domain):
    """Classify a domain without external API calls (fallback implementation)"""
    if not domain:
        return "unknown"
        
    domain = domain.lower().strip()
    
    # Check whitelist
    if domain in WHITELIST:
        return "whitelisted"
        
    # Check categories
    for category, domains in DOMAIN_CATEGORIES.items():
        for known in domains:
            if domain == known or domain.endswith('.' + known):
                return category
                
    return "unknown"

def fallback_is_domain_allowed(domain, context="none"):
    """Check if a domain is allowed in the given calendar context (fallback implementation)"""
    if not domain:
        return True, "No domain to check"
        
    category = fallback_classify_domain(domain)
    
    # Whitelisted domains are always allowed
    if category == "whitelisted":
        return True, f"Domain is whitelisted"
    
    # Get context rules
    rules = CONTEXT_RULES.get(context, CONTEXT_RULES["none"])
    
    # Check if category is explicitly allowed
    if category in rules["allowed"]:
        return True, f"Category '{category}' is allowed in context '{context}'"
    
    # Check if category is explicitly blocked
    if category in rules["blocked"]:
        return False, f"Category '{category}' is blocked in context '{context}'"
    
    # Default behavior for unknown categories
    if category == "unknown":
        return True, f"Unknown domain category"
    
    # For other categories not explicitly allowed or blocked
    return True, f"Category '{category}' is not restricted in context '{context}'"

def get_calendar_context_and_event(calendar_id=None) -> Tuple[str, Dict[str, Any], str]:
    """
    Get calendar context, current event, and source description
    
    Args:
        calendar_id: Optional calendar ID to use
        
    Returns:
        Tuple of (context, event_dict, source_description)
    """
    if not CALENDAR_AVAILABLE:
        # Fallback to time-based simulation
        current_hour = datetime.datetime.now().hour
        
        # Simulate different contexts based on time of day
        if 9 <= current_hour < 12:
            return "focus", None, "Time-based simulation (morning focus time)"
        elif 12 <= current_hour < 13:
            return "break", None, "Time-based simulation (lunch break)"
        elif 13 <= current_hour < 17:
            return "meeting", None, "Time-based simulation (afternoon meetings)"
        elif 17 <= current_hour < 19:
            return "break", None, "Time-based simulation (evening break)"
        else:
            return "none", None, "Time-based simulation (no scheduled activity)"
    
    try:
        # Get cached calendar client
        calendar_client = get_cached_calendar_client(calendar_id)
        
        if not calendar_client:
            return "none", None, "Calendar client not available"
        
        # Get current context and event
        context = get_current_context(calendar_client)
        event = get_current_event(calendar_client)
        
        if event:
            source = f"Calendar event: {event.get('summary', 'Untitled event')}"
        else:
            source = "No active calendar event"
            
        return context, event, source
    except Exception as e:
        print(f"Error getting calendar context: {e}")
        return "none", None, f"Error: {str(e)}"

# Global calendar client cache
_calendar_client = None
_domain_allowance = None

def get_cached_calendar_client(calendar_id=None):
    """Get or create a cached calendar client"""
    global _calendar_client
    
    if _calendar_client is None and CALENDAR_AVAILABLE:
        try:
            _calendar_client = GoogleCalendarClient(calendar_id=calendar_id)
            print("Created and cached calendar client")
        except Exception as e:
            print(f"Error creating calendar client: {e}")
    
    return _calendar_client

def get_cached_domain_allowance():
    """Get or create a cached domain allowance instance"""
    global _domain_allowance, _calendar_client
    
    if _domain_allowance is None and CALENDAR_AVAILABLE and _calendar_client is not None:
        try:
            _domain_allowance = get_calendar_domain_allowance(_calendar_client)
            print("Created and cached domain allowance")
        except Exception as e:
            print(f"Error creating domain allowance: {e}")
    
    return _domain_allowance

def check_domain_allowed(domain: str, context: str, event: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Check if a domain is allowed in the current context
    
    Args:
        domain: Domain to check
        context: Calendar context
        event: Calendar event dictionary
        
    Returns:
        Tuple of (is_allowed, reason)
    """
    if not domain:
        return True, "No domain to check"
    
    try:
        if CALENDAR_AVAILABLE:
            # Try to use the real domain allowance system
            from core.domain_classifier.filter_domain import filter_domain
            
            # Get cached domain allowance
            domain_allowance = get_cached_domain_allowance()
            
            if domain_allowance:
                # Update context with latest info (but not too frequently)
                domain_allowance.update_context(force=False)
                
                # Check domain allowance (both proactive and reactive)
                is_allowed_proactive, reason_proactive = domain_allowance.is_domain_allowed_proactive(domain)
                
                # If proactively allowed, double-check with reactive check
                if is_allowed_proactive:
                    is_allowed, reason = domain_allowance.is_domain_allowed_reactive(domain)
                    return is_allowed, reason
                else:
                    return is_allowed_proactive, reason_proactive
            else:
                # Fallback if domain allowance isn't available
                return fallback_is_domain_allowed(domain, context)
        else:
            # Use fallback implementation
            return fallback_is_domain_allowed(domain, context)
    except Exception as e:
        print(f"Error checking domain allowance: {e}")
        # Fallback to simple implementation
        return fallback_is_domain_allowed(domain, context)

def monitor_activity(context=None, interval=1, verbose=False, calendar_id=None):
    """Monitor active windows and check domains against calendar context"""
    # Initialize memory tracking
    start_memory = get_memory_usage()
    last_gc_time = time.time()
    gc_interval = 60  # Run garbage collection every 60 seconds
    
    # Initialize calendar client cache if calendar integration is available
    if CALENDAR_AVAILABLE and calendar_id:
        # Initialize the calendar client once at startup
        calendar_client = get_cached_calendar_client(calendar_id)
        if calendar_client:
            # Initialize domain allowance
            domain_allowance = get_cached_domain_allowance()
    
    # Initialize context update tracking
    last_context_update = time.time()
    context_update_interval = 60  # Update calendar context every 60 seconds
    
    # Get initial calendar context if not provided
    if context is None:
        context, event, context_source = get_calendar_context_and_event(calendar_id)
    else:
        event = None
        context_source = "command-line argument"
        
    print(f"Starting activity monitor with calendar context: {context} ({context_source})")
    print(f"Initial memory usage: {start_memory:.2f} MB")
    print("Press Ctrl+C to exit")
    print("-" * 50)
    
    try:
        while True:
            # Periodic garbage collection to prevent memory growth
            current_time = time.time()
            if current_time - last_gc_time > gc_interval:
                gc.collect()
                last_gc_time = current_time
                if verbose:
                    current_memory = get_memory_usage()
                    print(f"Memory usage: {current_memory:.2f} MB (change: {current_memory - start_memory:.2f} MB)")
            
            # Periodic context update if using calendar integration
            if context is None and current_time - last_context_update > context_update_interval:
                context, event, context_source = get_calendar_context_and_event(calendar_id)
                last_context_update = current_time
                print(f"Updated calendar context: {context} ({context_source})")
            
            # Get active window info
            window_info = get_active_window_info()
            window_title = window_info.get("title", "")
            app_name = window_info.get("app_name", "")
            
            # Extract domain if it's a browser
            domain = None
            app_name_lower = app_name.lower() if app_name else ""
            
            is_browser = any(browser in app_name_lower for browser in BROWSER_PROCESSES)
            
            if is_browser:
                domain = extract_domain_from_title(window_title)
            
            # Check if domain is allowed
            if domain:
                is_allowed, reason = check_domain_allowed(domain, context, event)
                
                # Get domain category
                if CALENDAR_AVAILABLE:
                    try:
                        from core.domain_classifier.domain_classifier import classify_domain
                        category = classify_domain(domain) or "unknown"
                    except Exception:
                        category = fallback_classify_domain(domain)
                else:
                    category = fallback_classify_domain(domain)
                
                # Print status
                print(f"Time: {datetime.datetime.now().strftime('%H:%M:%S')}")
                print(f"App: {app_name}")
                print(f"Domain: {domain}")
                print(f"Category: {category}")
                print(f"Context: {context}")
                print(f"Allowed: {'YES' if is_allowed else 'NO'}")
                print(f"Reason: {reason}")
                
                # Alert if domain is not allowed
                if not is_allowed:
                    print("\n⚠️ DISTRACTION ALERT ⚠️")
                    print(f"Domain '{domain}' is not allowed in context '{context}'")
                    print(f"Reason: {reason}")
                
                print("-" * 50)
            elif verbose:
                # Print non-browser activity if verbose
                print(f"Time: {datetime.datetime.now().strftime('%H:%M:%S')}")
                print(f"App: {app_name}")
                print(f"Title: {window_title}")
                print(f"Context: {context}")
                print("-" * 50)
            
            # Sleep for interval
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nActivity monitor stopped")

def main():
    """Main function for calendar-integrated activity monitor"""
    parser = argparse.ArgumentParser(description='Calendar-Integrated Activity Monitor')
    parser.add_argument('--context', type=str, choices=['focus', 'meeting', 'break', 'none'],
                        help='Calendar context to use (default: auto-detect from calendar)')
    parser.add_argument('--interval', type=float, default=2.0,
                        help='Polling interval in seconds (default: 2.0)')
    parser.add_argument('--verbose', action='store_true',
                        help='Show all window activity, not just browser domains')
    parser.add_argument('--calendar-id', type=str,
                        help='Google Calendar ID to use for context detection')
    args = parser.parse_args()
    
    # Start monitoring
    monitor_activity(context=args.context, interval=args.interval, 
                    verbose=args.verbose, calendar_id=args.calendar_id)

if __name__ == "__main__":
    main()
