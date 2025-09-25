"""
Handles connection and event fetching from Google Calendar (first), extendable to Office Calendar.
"""
import os
import datetime
from typing import List, Dict, Optional, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
from google.oauth2 import service_account

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

class CalendarClient:
    """Base class for calendar clients"""
    def get_events(self, start_time: datetime.datetime, end_time: datetime.datetime) -> List[Dict[str, Any]]:
        """
        Fetch events between start_time and end_time.
        Returns a list of event dicts.
        """
        raise NotImplementedError("Subclasses must implement this method")

class GoogleCalendarClient(CalendarClient):
    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None, 
                 service_account_path: Optional[str] = None, calendar_id: str = 'primary'):
        """
        Initialize Google Calendar API client with OAuth2 credentials or service account.
        
        Args:
            credentials_path: Path to the credentials.json file (from Google Cloud Console)
            token_path: Path to store/retrieve the token.pickle file
            service_account_path: Path to service account JSON file (alternative to OAuth)
            calendar_id: The calendar ID to use (default: 'primary')
        """
        self.credentials_path = credentials_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'config', 
            'credentials.json'
        )
        self.token_path = token_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'config', 
            'token.pickle'
        )
        self.service_account_path = service_account_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'config', 
            'service-account.json'
        )
        self.calendar_id = calendar_id
        self.service = None
        self._authenticate()
    
    def _authenticate(self) -> None:
        """
        Authenticate with Google Calendar API using OAuth2 or service account.
        First tries service account if the file exists, falls back to OAuth.
        """
        # Try service account authentication first (if file exists)
        if os.path.exists(self.service_account_path):
            try:
                print(f"Attempting to authenticate using service account: {self.service_account_path}")
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_path, scopes=SCOPES)
                self.service = build('calendar', 'v3', credentials=credentials)
                print("Successfully authenticated using service account")
                return
            except Exception as e:
                print(f"Service account authentication failed: {str(e)}")
                print("Falling back to OAuth authentication...")
        
        # Fall back to OAuth authentication
        creds = None
        
        # Check if token.pickle exists and load credentials from it
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If credentials don't exist or are invalid, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials file not found at {self.credentials_path}. "
                        "Please download credentials.json from Google Cloud Console "
                        "and place it in the config directory."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        # Build the service
        self.service = build('calendar', 'v3', credentials=creds)
    
    def get_events(self, start_time: datetime.datetime, end_time: datetime.datetime) -> List[Dict[str, Any]]:
        """
        Fetch events between start_time and end_time.
        
        Args:
            start_time: Start time for fetching events
            end_time: End time for fetching events
            
        Returns:
            A list of event dictionaries with standardized format:
            {
                'id': str,
                'summary': str,
                'description': str,
                'start_time': datetime,
                'end_time': datetime,
                'location': str,
                'attendees': List[str],
                'is_organizer': bool,
                'response_status': str,
                'calendar_id': str,
                'raw_event': Dict (original API response)
            }
        """
        if not self.service:
            self._authenticate()
        
        # Convert datetime objects to RFC3339 timestamp strings (required by Google Calendar API)
        # Remove timezone info from the string if it exists, then add Z
        start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')  # Format to RFC3339
        end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        all_events = []
        
        # Use the specified calendar ID directly
        calendar_id = self.calendar_id
        print(f"Fetching events from calendar: {calendar_id}")
        
        # Call the Calendar API
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_time_str,
                timeMax=end_time_str,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
        except Exception as e:
            print(f"Error fetching events from calendar {calendar_id}: {str(e)}")
            return []
        
        events = events_result.get('items', [])
        
        # Process and standardize each event
        for event in events:
            # Skip events without a summary (usually means they're free/busy info)
            if 'summary' not in event:
                continue
            
            # Extract start and end times
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # Convert string times to timezone-aware datetime objects
            if 'T' in start:  # This is a dateTime, not just a date
                # Make sure we have timezone info
                if 'Z' in start:
                    # UTC time
                    start_dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                elif '+' in start or '-' in start and start.rfind('-') > 10:  # Check if it has timezone offset
                    # Already has timezone info
                    start_dt = datetime.datetime.fromisoformat(start)
                else:
                    # No timezone info, assume UTC
                    start_dt = datetime.datetime.fromisoformat(start).replace(tzinfo=datetime.timezone.utc)
            else:
                # All-day event, use midnight as the time (UTC)
                start_dt = datetime.datetime.fromisoformat(f"{start}T00:00:00").replace(tzinfo=datetime.timezone.utc)
            
            if 'T' in end:
                # Make sure we have timezone info
                if 'Z' in end:
                    # UTC time
                    end_dt = datetime.datetime.fromisoformat(end.replace('Z', '+00:00'))
                elif '+' in end or '-' in end and end.rfind('-') > 10:  # Check if it has timezone offset
                    # Already has timezone info
                    end_dt = datetime.datetime.fromisoformat(end)
                else:
                    # No timezone info, assume UTC
                    end_dt = datetime.datetime.fromisoformat(end).replace(tzinfo=datetime.timezone.utc)
            else:
                # All-day event, use midnight as the time (UTC)
                end_dt = datetime.datetime.fromisoformat(f"{end}T00:00:00").replace(tzinfo=datetime.timezone.utc)
            
            # Extract attendees
            attendees = []
            is_organizer = False
            response_status = 'none'
            
            if 'attendees' in event:
                for attendee in event['attendees']:
                    attendees.append(attendee.get('email', ''))
                    
                    # Check if the current user is the organizer
                    if attendee.get('self', False) and attendee.get('organizer', False):
                        is_organizer = True
                    
                    # Get the current user's response status
                    if attendee.get('self', False):
                        response_status = attendee.get('responseStatus', 'none')
            
            # Create standardized event dict
            standardized_event = {
                'id': event.get('id', ''),
                'summary': event.get('summary', ''),
                'description': event.get('description', ''),
                'start_time': start_dt,
                'end_time': end_dt,
                'location': event.get('location', ''),
                'attendees': attendees,
                'is_organizer': is_organizer,
                'response_status': response_status,
                'calendar_id': calendar_id,
                'raw_event': event  # Store the original event data
            }
            
            all_events.append(standardized_event)
        
        return all_events
    
    def get_current_events(self) -> List[Dict[str, Any]]:
        """
        Get events happening right now.
        
        Returns:
            List of events currently in progress
        """
        now = datetime.datetime.utcnow()
        # Look at events in a small window around current time
        start = now - datetime.timedelta(minutes=1)
        end = now + datetime.timedelta(minutes=1)
        
        all_events = self.get_events(start, end)
        
        # Filter to only include events that are currently happening
        current_events = []
        for event in all_events:
            if event['start_time'] <= now <= event['end_time']:
                current_events.append(event)
        
        return current_events
    
    def get_upcoming_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get upcoming events within the specified time window.
        
        Args:
            hours: Number of hours to look ahead
            
        Returns:
            List of upcoming events
        """
        now = datetime.datetime.utcnow()
        end = now + datetime.timedelta(hours=hours)
        
        return self.get_events(now, end)

class OutlookCalendarClient(CalendarClient):
    """
    Placeholder for Microsoft Outlook/Office 365 Calendar integration.
    Would use Microsoft Graph API.
    """
    def __init__(self, credentials_path=None):
        # TODO: Implement Microsoft Graph API authentication
        pass
    
    def get_events(self, start_time: datetime.datetime, end_time: datetime.datetime) -> List[Dict[str, Any]]:
        # TODO: Implement Microsoft Graph API call
        return []