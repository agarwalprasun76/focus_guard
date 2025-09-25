"""
Enhanced test script for calendar-based domain allowance.
This script demonstrates how to use calendar context to determine which domains are allowed.
"""
import sys
import os
import datetime
import argparse
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from core.calendar.calendar_integration import GoogleCalendarClient
from core.calendar.calendar_context import get_current_context, get_current_event
from core.calendar.calendar_domain_allowance import get_calendar_domain_allowance
from core.domain_classifier.filter_domain import filter_domain

# Define context-specific domain allowances
CONTEXT_DOMAIN_MAPPING = {
    "meeting": {
        "allowed_domains": ["zoom.us", "teams.microsoft.com", "meet.google.com", "slack.com", "github.com"],
        "allowed_categories": ["work", "education"]
    },
    "focus": {
        "allowed_domains": ["github.com", "stackoverflow.com", "docs.python.org", "khanacademy.org"],
        "allowed_categories": ["work", "education"]
    },
    "break": {
        "allowed_domains": ["youtube.com", "spotify.com", "netflix.com"],
        "allowed_categories": ["entertainment", "news"]
    },
    "none": {
        "allowed_domains": [],
        "allowed_categories": ["work", "education", "entertainment", "news"]
    }
}

def test_calendar_domain_allowance(calendar_id: str, test_domains: list):
    """Test calendar-based domain allowance."""
    print("\n" + "="*60)
    print("CALENDAR-BASED DOMAIN ALLOWANCE TEST")
    print("="*60)
    
    try:
        # Initialize the Google Calendar client
        print(f"Initializing Google Calendar client with calendar ID: {calendar_id}")
        client = GoogleCalendarClient(calendar_id=calendar_id)
        
        # Get current time (local time)
        local_now = datetime.datetime.now()
        print(f"Current local time: {local_now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get current event
        print("\nFetching current calendar event...")
        current_event = get_current_event(client)
        
        if current_event:
            print(f"Current event: {current_event.get('summary', 'No title')}")
            start_time = current_event.get('start_time', current_event.get('start', {}))
            end_time = current_event.get('end_time', current_event.get('end', {}))
            
            if isinstance(start_time, dict):
                start_str = start_time.get('dateTime', start_time.get('date', 'Unknown'))
            else:
                start_str = str(start_time)
                
            if isinstance(end_time, dict):
                end_str = end_time.get('dateTime', end_time.get('date', 'Unknown'))
            else:
                end_str = str(end_time)
                
            print(f"Event time: {start_str} to {end_str}")
            
            if 'attendees' in current_event:
                print(f"Attendees: {len(current_event['attendees'])}")
        else:
            print("No current event found")
        
        # Get current context
        print("\nDetermining current calendar context...")
        current_context = get_current_context(client)
        print(f"Current context: {current_context}")
        
        # Initialize calendar domain allowance
        domain_allowance = get_calendar_domain_allowance(client)
        
        # Test domains
        print("\nTesting domains based on current calendar context:")
        print("-" * 80)
        print(f"{'Domain':30s} | {'Category':15s} | {'Allowed':8s} | Reason")
        print("-" * 80)
        
        for domain in test_domains:
            # Get domain category
            category = filter_domain(domain)
            if category == "excluded":
                category = "blocked"
            elif category == "whitelisted":
                category = "whitelisted"
            elif category == "unknown":
                category = "unknown"
            
            # Check if domain is allowed
            is_allowed, reason = domain_allowance.is_domain_allowed_proactive(domain)
            
            # Print result
            print(f"{domain:30s} | {category:15s} | {str(is_allowed):8s} | {reason}")
        
        # Test with app titles (reactive mode)
        print("\nTesting domains with app titles (reactive mode):")
        print("-" * 80)
        print(f"{'Domain + App Title':50s} | {'Allowed':8s} | Reason")
        print("-" * 80)
        
        app_titles = {
            "zoom.us": "Zoom Meeting - Team Standup",
            "slack.com": "Slack - Project Discussion",
            "github.com": "GitHub - Pull Request Review",
            "facebook.com": "Facebook - News Feed",
            "twitter.com": "Twitter - Home",
            "youtube.com": "YouTube - Educational Videos",
            "netflix.com": "Netflix - Movies",
            "khanacademy.org": "Khan Academy - Math Lessons",
            "coursera.org": "Coursera - Machine Learning Course",
            "amazon.com": "Amazon - Shopping Cart"
        }
        
        for domain in test_domains:
            app_title = app_titles.get(domain, None)
            is_allowed, reason = domain_allowance.is_domain_allowed_reactive(domain, app_title)
            
            # Print result
            domain_app = f"{domain} ({app_title})" if app_title else domain
            print(f"{domain_app:50s} | {str(is_allowed):8s} | {reason}")
        
        print("\nCalendar domain allowance test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error testing calendar domain allowance: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Test calendar-based domain allowance')
    parser.add_argument('--calendar-id', type=str, default='primary',
                        help='Calendar ID to use (default: primary)')
    args = parser.parse_args()
    
    # Default test domains
    test_domains = [
        "zoom.us",
        "slack.com",
        "github.com",
        "facebook.com",
        "twitter.com",
        "youtube.com",
        "netflix.com",
        "khanacademy.org",
        "coursera.org",
        "amazon.com"
    ]
    
    # Run the test
    test_calendar_domain_allowance(args.calendar_id, test_domains)
