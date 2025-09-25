"""
Calendar Test

Core functionality for testing Google Calendar integration.
This module provides utilities for verifying calendar connectivity and event retrieval.

Features:
- Tests Google Calendar API connection
- Fetches and displays upcoming events
- Verifies calendar context functionality
- Validates calendar event parsing
"""
import sys
import os
import datetime
from pathlib import Path
import argparse

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from focus_guard.core.calendar.calendar_integration import GoogleCalendarClient
from focus_guard.core.calendar.calendar_context import get_current_context, get_next_context_change

def test_calendar_connection(calendar_id: str, test_domains=None):
    """Test connection to Google Calendar API and fetch events."""
    print("Testing Google Calendar connection...")
    print(f"Using calendar ID: {calendar_id}")
    
    try:
        # Initialize the Google Calendar client with the specified calendar ID
        # For service accounts, we need to use the calendar ID of a calendar that's been shared with the service account
        client = GoogleCalendarClient(calendar_id=calendar_id)
        
        # Get current time in UTC (timezone-aware)
        try:
            # Python 3.9+
            now = datetime.datetime.now(datetime.UTC)
        except AttributeError:
            # Python 3.8 and earlier
            now = datetime.datetime.now(datetime.timezone.utc)
        print(f"Current time (UTC): {now}")
        
        # Get events for today
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + datetime.timedelta(days=1)
        
        print(f"Fetching events from {start_time} to {end_time}...")
        events = client.get_events(start_time, end_time)
        
        # Print events
        print(f"Found {len(events)} events for today:")
        for i, event in enumerate(events, 1):
            print(f"\nEvent {i}:")
            print(f"  Summary: {event['summary']}")
            print(f"  Start: {event['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  End: {event['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Location: {event.get('location', 'N/A')}")
            print(f"  Attendees: {len(event.get('attendees', []))}")
        
        # Get current context
        current_context = get_current_context(client)
        print(f"\nCurrent context: {current_context}")
        
        # Get next context change
        next_change = get_next_context_change(client)
        print("\nNext context change:")
        
        # Handle the time (it might be a datetime object or ISO string)
        next_time = next_change['time']
        if isinstance(next_time, str):
            try:
                next_time = datetime.datetime.fromisoformat(next_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
                
        time_str = next_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(next_time, 'strftime') else str(next_time)
        print(f"  Time: {time_str}")
        print(f"  New context: {next_change.get('context', 'none')}")
        
        event = next_change.get('event', {})
        if event:
            print(f"  Event: {event.get('summary', 'No title')}")
            
            # Print event details if available
            event_start = event.get('start', {})
            event_end = event.get('end', {})
            
            if 'dateTime' in event_start:
                print(f"  Start: {event_start['dateTime']}")
            if 'dateTime' in event_end:
                print(f"  End: {event_end['dateTime']}")
        
        # Test domain allowance if domains are provided
        if test_domains:
            from core.calendar.calendar_domain_allowance import get_calendar_domain_allowance
            
            print("\n\nTesting domain allowance based on calendar context...")
            print(f"Current context: {current_context}")
            
            # Get the calendar domain allowance instance
            domain_allowance = get_calendar_domain_allowance(client)
            
            print("\nProactive mode results:")
            print("-" * 60)
            print(f"{'Domain':30s} | {'Allowed':8s} | Reason")
            print("-" * 60)
            
            for domain in test_domains:
                is_allowed, reason = domain_allowance.is_domain_allowed_proactive(domain)
                print(f"{domain:30s} | {str(is_allowed):8s} | {reason}")
            
            print("\nReactive mode results:")
            print("-" * 60)
            print(f"{'Domain':30s} | {'Allowed':8s} | Reason")
            print("-" * 60)
            
            # For reactive mode, simulate some app titles
            app_titles = {
                "zoom.us": "Zoom Meeting - Team Standup",
                "slack.com": "Slack - General",
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
                print(f"{domain:30s} | {str(is_allowed):8s} | {reason}")
        
        print("\nCalendar integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error testing calendar integration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Test Google Calendar integration')
    parser.add_argument('--calendar-id', type=str, default='primary',
                        help='Calendar ID to use (default: primary)')
    parser.add_argument('--test-domains', action='store_true',
                        help='Test domain allowance based on calendar context')
    args = parser.parse_args()
    
    # Default test domains
    test_domains = None
    if args.test_domains:
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
    
    # Run the test with the specified calendar ID
    test_calendar_connection(args.calendar_id, test_domains)
