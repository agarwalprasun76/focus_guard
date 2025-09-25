"""
Window Monitor

Core functionality for monitoring active windows and extracting window information.
This module provides cross-platform window monitoring capabilities.

Features:
- Captures active window information
- Handles different window managers across platforms
- Provides window title and process information
- Lightweight and efficient implementation
"""
import sys
import os
import time
import datetime
import argparse
import re
import gc
from pathlib import Path

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
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import activity monitor modules
try:
    from core.activity_monitor.window_info import get_active_window_info
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

# Domain categories for classification
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

# Calendar context rules (which domain categories are allowed in which contexts)
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

def classify_domain(domain):
    """Classify a domain without external API calls"""
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

def is_domain_allowed(domain, context="none"):
    """Check if a domain is allowed in the given calendar context"""
    if not domain:
        return True, "No domain to check"
        
    category = classify_domain(domain)
    
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

def get_calendar_context(calendar_id=None):
    """Get calendar context from Google Calendar or fallback to time-based simulation"""
    try:
        # Try to import calendar modules
        from core.calendar.calendar_integration import GoogleCalendarClient
        from core.calendar.calendar_domain_allowance import get_semantic_context_from_events
        
        # Get current time
        now = datetime.datetime.now()
        start_time = now - datetime.timedelta(minutes=5)  # Look at current and recent events
        end_time = now + datetime.timedelta(minutes=5)    # Look at upcoming events too
        
        # Initialize calendar client
        try:
            calendar_client = GoogleCalendarClient()
            
            # Get events
            events = calendar_client.get_events(start_time, end_time)
            
            # Get semantic context from events
            if events:
                context = get_semantic_context_from_events(events)
                return context, f"Calendar event: {events[0].get('summary', 'Untitled event')}"
        except Exception as e:
            print(f"Calendar integration error: {e}")
    except ImportError:
        print("Calendar integration not available, using time-based simulation")
    
    # Fallback to time-based simulation
    current_hour = datetime.datetime.now().hour
    
    # Simulate different contexts based on time of day
    if 9 <= current_hour < 12:
        return "focus", "Morning focus time"
    elif 12 <= current_hour < 13:
        return "break", "Lunch break"
    elif 13 <= current_hour < 17:
        return "meeting", "Afternoon meetings"
    elif 17 <= current_hour < 19:
        return "break", "Evening break"
    else:
        return "none", "No scheduled activity"

def monitor_activity(context=None, interval=1, verbose=False, calendar_id=None):
    """Monitor active windows and check domains against calendar context"""
    # Get calendar context if not provided
    if context is None:
        context, context_source = get_calendar_context(calendar_id)
    else:
        context_source = "command-line argument"
    
    # Initialize memory tracking
    start_memory = get_memory_usage()
    last_gc_time = time.time()
    gc_interval = 60  # Run garbage collection every 60 seconds
        
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
                category = classify_domain(domain)
                is_allowed, reason = is_domain_allowed(domain, context)
                
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
    """Main function for activity monitor with calendar domain integration"""
    parser = argparse.ArgumentParser(description='Activity Monitor with Calendar Domain Integration')
    parser.add_argument('--context', type=str, choices=['focus', 'meeting', 'break', 'none'],
                        help='Calendar context to use (default: auto-detect based on time)')
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
