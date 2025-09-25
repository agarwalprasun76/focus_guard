"""
Parses calendar events and determines the current user context (e.g., meeting, focus, break).
"""
from typing import List, Dict, Optional, Any, Union
import datetime
import re
from dataclasses import dataclass

# Import logger
from core.logger.logger import get_logger

# Initialize logger
logger = get_logger("calendar_context")

@dataclass
class CalendarEvent:
    """Represents a calendar event with start and end times."""
    id: str
    summary: str
    description: str
    start: Dict[str, str]  # {'dateTime': isoformat string}
    end: Dict[str, str]    # {'dateTime': isoformat string}
    
    def is_now(self) -> bool:
        """Check if the current time is within this event's time range."""
        now = datetime.datetime.now(datetime.timezone.utc)
        start = datetime.datetime.fromisoformat(self.start['dateTime'].replace('Z', '+00:00'))
        end = datetime.datetime.fromisoformat(self.end['dateTime'].replace('Z', '+00:00'))
        return start <= now <= end

# Context types
CONTEXT_MEETING = "meeting"
CONTEXT_FOCUS = "focus"
CONTEXT_BREAK = "break"
CONTEXT_NONE = "none"

# Keywords for context detection
MEETING_KEYWORDS = [
    'meeting', 'call', 'sync', 'discussion', 'interview', 'review', 
    'standup', 'retrospective', '1:1', 'one-on-one', 'workshop'
]

FOCUS_KEYWORDS = [
    'focus', 'deep work', 'no interruptions', 'do not disturb', 
    'coding', 'writing', 'research', 'planning', 'work time'
]

BREAK_KEYWORDS = [
    'break', 'lunch', 'dinner', 'breakfast', 'coffee', 'rest', 
    'walk', 'gym', 'workout', 'exercise', 'personal'
]

def determine_context(events: List[Dict[str, Any]], current_time: Optional[datetime.datetime] = None) -> str:
    """
    Given a list of events and the current time, returns the context string.
    E.g., 'meeting', 'focus', 'break', or 'none' if no relevant event.
    
    Args:
        events: List of calendar events in the standardized format
        current_time: The time to check for context (defaults to now)
        
    Returns:
        Context string: 'meeting', 'focus', 'break', or 'none'
    """
    if not events:
        return CONTEXT_NONE
    
    if current_time is None:
        # Use timezone-aware UTC datetime
        try:
            # Python 3.9+
            current_time = datetime.datetime.now(datetime.UTC)
        except AttributeError:
            # Python 3.8 and earlier
            current_time = datetime.datetime.now(datetime.timezone.utc)
    
    # Find events that are happening right now
    current_events = []
    for event in events:
        if event['start_time'] <= current_time <= event['end_time']:
            current_events.append(event)
    
    if not current_events:
        return CONTEXT_NONE
    
    # Determine context based on event properties
    for event in current_events:
        # Check if the event is a meeting based on keywords in summary or description
        summary = event.get('summary', '').lower()
        description = event.get('description', '').lower() if event.get('description') else ''
        
        # Check for meeting indicators
        if (any(keyword in summary for keyword in MEETING_KEYWORDS) or 
            any(keyword in description for keyword in MEETING_KEYWORDS) or
            len(event.get('attendees', [])) > 1):  # If there are multiple attendees, likely a meeting
            return CONTEXT_MEETING
        
        # Check for focus time indicators
        if any(keyword in summary for keyword in FOCUS_KEYWORDS) or any(keyword in description for keyword in FOCUS_KEYWORDS):
            return CONTEXT_FOCUS
        
        # Check for break indicators
        if any(keyword in summary for keyword in BREAK_KEYWORDS) or any(keyword in description for keyword in BREAK_KEYWORDS):
            return CONTEXT_BREAK
    
    # Default to meeting if there's a calendar event but no specific context detected
    # This is because most calendar events tend to be meetings
    return CONTEXT_MEETING

def _parse_datetime(dt_input) -> datetime.datetime:
    """
    Parse a datetime input from Google Calendar API to a timezone-aware datetime object.
    Handles various formats including those with and without timezone information,
    as well as dictionary inputs with dateTime or date fields.
    
    Args:
        dt_input: Datetime string or dictionary from Google Calendar API
        
    Returns:
        Timezone-aware datetime object
    """
    try:
        # Handle dictionary input (common in Google Calendar API responses)
        if isinstance(dt_input, dict):
            # Try both lowercase and uppercase key variations
            dt_str = (dt_input.get('dateTime') or dt_input.get('date') or 
                      dt_input.get('DateTime') or dt_input.get('Date') or
                      dt_input.get('start_time') or dt_input.get('end_time'))
            
            # Print the keys for debugging
            if not dt_str:
                logger.debug(f"Event dict keys: {list(dt_input.keys())}")
                # Return a default datetime in the past
                return datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)
        else:
            dt_str = dt_input
            
        # Handle dateTime format with 'Z' (UTC)
        if dt_str.endswith('Z'):
            return datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        
        # Handle dateTime format with timezone offset
        if 'T' in dt_str and ('+' in dt_str or '-' in dt_str and dt_str.rfind('-') > 10):
            return datetime.datetime.fromisoformat(dt_str)
        
        # Handle dateTime format without timezone (assume local time)
        if 'T' in dt_str:
            # Get local timezone
            local_tz = datetime.datetime.now().astimezone().tzinfo
            local_dt = datetime.datetime.fromisoformat(dt_str)
            aware_dt = local_dt.replace(tzinfo=local_tz)
            return aware_dt
        
        # Handle date-only format (all-day event)
        local_tz = datetime.datetime.now().astimezone().tzinfo
        local_dt = datetime.datetime.fromisoformat(f"{dt_str}T00:00:00")
        aware_dt = local_dt.replace(tzinfo=local_tz)
        return aware_dt
    except Exception as e:
        logger.error(f"Error parsing datetime '{dt_input}': {e}", exc_info=True)
        # Return a default datetime in the past
        return datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)

def get_current_event(calendar_client) -> Optional[Dict]:
    """
    Get the current calendar event.
    
    Args:
        calendar_client: An instance of a CalendarClient or MockCalendarClient
        
    Returns:
        Current calendar event as a dictionary, or None if no current event
    """
    try:
        # Use timezone-aware UTC datetime
        try:
            # Python 3.9+
            now = datetime.datetime.now(datetime.UTC)
        except AttributeError:
            # Python 3.8 and earlier
            now = datetime.datetime.now(datetime.timezone.utc)
            
        time_min = now - datetime.timedelta(hours=1)
        time_max = now + datetime.timedelta(hours=1)
        
        # First try the direct method if available (for mock client)
        if hasattr(calendar_client, 'get_current_event'):
            try:
                return calendar_client.get_current_event()
            except Exception as e:
                logger.warning(f"get_current_event() failed: {e}", exc_info=True)
        
        # Try to get events using the get_events method if it exists
        if hasattr(calendar_client, 'get_events'):
            try:
                # Try with time range parameters
                events = calendar_client.get_events(time_min, time_max)
            except TypeError:
                try:
                    # Fall back to getting all events if time range not supported
                    all_events = calendar_client.get_events()
                    # Filter events to the time range
                    events = [
                        e for e in all_events 
                        if 'start' in e and ('dateTime' in e['start'] or 'date' in e['start'])
                        and 'end' in e and ('dateTime' in e['end'] or 'date' in e['end'])
                    ]
                except Exception as e:
                    logger.error(f"Error getting events: {e}", exc_info=True)
                    return None
            
            # Find the current event
            for event in events:
                try:
                    # Debug - print event keys
                    if len(events) > 0 and event == events[0]:
                        logger.debug(f"Event keys: {list(event.keys())}")
                    
                    # Handle the correct keys based on the event structure
                    if 'start_time' in event and 'end_time' in event:
                        # Direct datetime objects
                        start = event.get('start_time')
                        end = event.get('end_time')
                        
                        # Convert to datetime objects if they're strings
                        if isinstance(start, str):
                            start = _parse_datetime(start)
                        if isinstance(end, str):
                            end = _parse_datetime(end)
                    else:
                        # Standard Google Calendar API format
                        start_dict = event.get('start') or event.get('Start')
                        end_dict = event.get('end') or event.get('End')
                        
                        # Use our helper function to parse datetime directly from event dictionaries
                        start = _parse_datetime(start_dict)
                        end = _parse_datetime(end_dict)
                    
                    if start <= now <= end:
                        return event
                        
                except (KeyError, ValueError) as e:
                    logger.error(f"Error parsing event time: {e}", exc_info=True)
                    continue
        
        # If we get here, try the Google Calendar API style
        try:
            # Check if the calendar_client has a service attribute (Google Calendar API client)
            if hasattr(calendar_client, 'service'):
                events_result = calendar_client.service.events().list(
                    calendarId=getattr(calendar_client, 'calendarId', 'primary'),
                    timeMin=time_min.isoformat(),
                    timeMax=time_max.isoformat(),
                    maxResults=10,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
            else:
                # If no service attribute, we can't use this method
                return None
            
            # Find the current event
            for event in events:
                try:
                    start_str = event['start'].get('dateTime') or event['start'].get('date')
                    end_str = event['end'].get('dateTime') or event['end'].get('date')
                    
                    if not start_str or not end_str:
                        continue
                    
                    # Use our helper function to parse datetime strings
                    start = _parse_datetime(start_str)
                    end = _parse_datetime(end_str)
                    
                    if start <= now <= end:
                        return event
                        
                except (KeyError, ValueError) as e:
                    logger.error(f"Error parsing event time: {e}", exc_info=True)
                    continue
                    
        except (AttributeError, TypeError) as e:
            logger.error(f"Error accessing calendar API: {e}", exc_info=True)
                
    except Exception as e:
        logger.error(f"Error getting current event: {e}", exc_info=True)
    
    return None

def get_current_context(calendar_client) -> str:
    """
    Get the current context using the calendar client.
    
    Args:
        calendar_client: An instance of a CalendarClient
        
    Returns:
        Current context string
    """
    current_event = get_current_event(calendar_client)
    if current_event:
        return determine_context([current_event])
    return CONTEXT_NONE

def get_next_context_change(calendar_client, hours_ahead: int = 24) -> Dict[str, Any]:
    """
    Get the time and context of the next context change.
    
    Args:
        calendar_client: An instance of a CalendarClient or MockCalendarClient
        hours_ahead: Number of hours to look ahead for context changes
        
    Returns:
        A dictionary containing:
        - time: datetime of the next context change
        - context: The new context after the change
        - event: The event causing the change (if any)
    """
    try:
        now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        end_time = now + datetime.timedelta(hours=hours_ahead)
        
        # Get current context
        current_context = get_current_context(calendar_client)
        
        # Try to get events using the get_events method if it exists
        if hasattr(calendar_client, 'get_events'):
            try:
                # Try with time range parameters
                events = calendar_client.get_events(now, end_time)
                
                # Process events to find the next context change
                next_change = None
                
                for event in events:
                    try:
                        # Handle both dateTime and date fields
                        start = None
                        if 'start' in event:
                            if 'dateTime' in event['start']:
                                start_str = event['start']['dateTime']
                                start = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00')).replace(tzinfo=datetime.timezone.utc)
                            elif 'date' in event['start']:
                                start_str = event['start']['date']
                                start = datetime.datetime.fromisoformat(start_str).replace(tzinfo=datetime.timezone.utc)
                        
                        if not start or start <= now:
                            continue
                            
                        # Get the context for this event
                        event_context = determine_context([event])
                        
                        # If this is a context change and it's earlier than our current next change
                        if event_context != current_context and (next_change is None or start < next_change['time']):
                            next_change = {
                                'time': start,
                                'context': event_context,
                                'event': event
                            }
                            
                    except (KeyError, ValueError) as e:
                        print(f"Error processing event: {e}")
                        continue
                
                # If we found a context change, return it
                if next_change is not None:
                    return next_change
                    
            except TypeError:
                # Fall back to getting all events if time range not supported
                try:
                    all_events = calendar_client.get_events()
                    # Filter events to the time range
                    future_events = []
                    
                    for event in all_events:
                        try:
                            start = None
                            if 'start' in event:
                                if 'dateTime' in event['start']:
                                    start_str = event['start']['dateTime']
                                    start = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00')).replace(tzinfo=datetime.timezone.utc)
                                elif 'date' in event['start']:
                                    start_str = event['start']['date']
                                    start = datetime.datetime.fromisoformat(start_str).replace(tzinfo=datetime.timezone.utc)
                            
                            if start and start > now and start <= end_time:
                                future_events.append((start, event))
                                
                        except (KeyError, ValueError) as e:
                            logger.error(f"Error parsing event time: {e}", exc_info=True)
                            continue
                    
                    # Sort events by start time
                    future_events.sort(key=lambda x: x[0])
                    
                    # Find the first event with a different context
                    for start, event in future_events:
                        event_context = determine_context([event])
                        if event_context != current_context:
                            return {
                                'time': start,
                                'context': event_context,
                                'event': event
                            }
                            
                except Exception as e:
                    logger.error(f"Error getting events: {e}", exc_info=True)
        
        # If we get here, try the Google Calendar API style
        try:
            events_result = calendar_client.events().list(
                calendarId=getattr(calendar_client, 'calendarId', 'primary'),
                timeMin=now.isoformat(),
                timeMax=end_time.isoformat(),
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Process events to find the next context change
            next_change = None
            
            for event in events:
                try:
                    start = None
                    if 'start' in event:
                        if 'dateTime' in event['start']:
                            start_str = event['start']['dateTime']
                            start = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00')).replace(tzinfo=datetime.timezone.utc)
                        elif 'date' in event['start']:
                            start_str = event['start']['date']
                            start = datetime.datetime.fromisoformat(start_str).replace(tzinfo=datetime.timezone.utc)
                    
                    if not start or start <= now:
                        continue
                        
                    # Get the context for this event
                    event_context = determine_context([event])
                    
                    # If this is a context change and it's earlier than our current next change
                    if event_context != current_context and (next_change is None or start < next_change['time']):
                        next_change = {
                            'time': start,
                            'context': event_context,
                            'event': event
                        }
                        
                except (KeyError, ValueError) as e:
                    logger.error(f"Error processing event: {e}", exc_info=True)
                    continue
            
            # If we found a context change, return it
            if next_change is not None:
                return next_change
                    
        except (AttributeError, TypeError) as e:
            logger.error(f"Error accessing calendar API: {e}", exc_info=True)
        
        # If no context change found, return end of lookahead period
        return {
            'time': end_time,
            'context': current_context,
            'event': None
        }
                
    except Exception as e:
        logger.error(f"Error in get_next_context_change: {e}", exc_info=True)
        # Return default values in case of error
        return {
            'time': (datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc) + datetime.timedelta(hours=1)).isoformat(),
            'context': CONTEXT_NONE,
            'event': None
        }