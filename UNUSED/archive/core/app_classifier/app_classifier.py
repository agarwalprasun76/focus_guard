"""
Main application classifier that integrates with calendar context.
"""
from typing import Dict, Optional, List, Tuple
from datetime import datetime, time
import logging

from ..calendar.calendar_context import get_current_event, get_next_context_change
from ..calendar.context_detector import get_context_detector
from .app_categories import get_app_category
from .context_rules import ContextRules

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppClassifier:
    """
    Classifies applications and determines if they should be allowed based on
    the current calendar context and predefined rules.
    """
    
    def __init__(self, calendar_client=None):
        """
        Initialize the app classifier with context detector and rules.
        
        Args:
            calendar_client: Optional calendar client instance for calendar integration
        """
        self.context_detector = get_context_detector()
        self.rules = ContextRules()
        self.calendar_client = calendar_client
        self._current_context = None
        self._last_update = None
        self._context_cache_ttl = 300  # 5 minutes in seconds
        
    def _get_time_based_context(self) -> Optional[str]:
        """Determine context based on time of day."""
        now = datetime.now().time()
        
        # Define time ranges
        morning = time(6, 0)
        work_start = time(9, 0)
        lunch_start = time(12, 0)
        lunch_end = time(13, 0)
        work_end = time(17, 0)
        evening = time(20, 0)
        
        if morning <= now < work_start:
            return "morning"
        elif lunch_start <= now < lunch_end:
            return "lunch_break"
        elif now >= evening or now < time(6, 0):
            return "after_hours"
        return None
    
    def _get_calendar_context(self) -> Tuple[Optional[str], Dict]:
        """
        Get the current context from calendar events.
        
        Returns:
            Tuple of (context, event_info) where context is the detected context
            and event_info contains event details.
        """
        try:
            if not self.calendar_client:
                logger.warning("No calendar client available for getting current event")
                return None, {}
                
            current_event = get_current_event(self.calendar_client)
            if not current_event:
                return None, {}
                
            # Use the context detector to determine the most relevant context
            event_text = f"{current_event.get('summary', '')} {current_event.get('description', '')}"
            context = self.context_detector.get_primary_context(event_text)
            
            return context, {
                "event_id": current_event.get("id"),
                "summary": current_event.get("summary"),
                "start": current_event.get("start", {}).get("dateTime"),
                "end": current_event.get("end", {}).get("dateTime")
            }
            
        except Exception as e:
            logger.error(f"Error getting calendar context: {e}")
            return None, {}
    
    def get_current_context(self, force_update: bool = False) -> Dict:
        """
        Get the current context, using cached value if recent.
        
        Args:
            force_update: If True, force update the context
            
        Returns:
            Dict containing context information
        """
        now = datetime.now()
        
        # Return cached context if it's recent enough
        if not force_update and self._last_update and \
           (now - self._last_update).total_seconds() < self._context_cache_ttl:
            return self._current_context
            
        # Get context from calendar
        calendar_context, event_info = self._get_calendar_context()
        
        # Fall back to time-based context if no calendar context
        if not calendar_context:
            calendar_context = self._get_time_based_context() or "default"
        
        # Get next context change time
        next_change = get_next_context_change(self.calendar_client) if hasattr(self, 'calendar_client') else None
        
        # Prepare context info
        self._current_context = {
            "context": calendar_context,
            "event": event_info,
            "next_change": next_change,
            "timestamp": now.isoformat(),
            "source": "calendar" if event_info else "time_based"
        }
        
        self._last_update = now
        return self._current_context
    
    def check_app(self, process_name: str, window_title: str = "") -> Dict:
        """
        Check if an application should be allowed based on current context.
        
        Args:
            process_name: Name of the process (e.g., 'chrome.exe')
            window_title: Optional window title for more specific categorization
            
        Returns:
            Dict with 'allowed' (bool), 'reason' (str), and 'context' (str)
        """
        # Get the app category
        category = get_app_category(process_name, window_title)
        
        # Get current context
        context_info = self.get_current_context()
        context = context_info["context"]
        
        # Check rules for this context
        result = self.rules.is_allowed(category, context)
        
        # Add context information to result
        result.update({
            "category": category,
            "context": context,
            "context_info": context_info
        })
        
        return result
    
    def get_allowed_apps(self) -> List[str]:
        """Get list of allowed app categories for current context."""
        context_info = self.get_current_context()
        return list(self.rules.get_allowed_categories(context_info["context"]))
    
    def get_blocked_apps(self) -> List[str]:
        """Get list of blocked app categories for current context."""
        context_info = self.get_current_context()
        return list(self.rules.get_blocked_categories(context_info["context"]))


# Singleton instance
_app_classifier = None

def get_app_classifier(calendar_client=None):
    """
    Get or create the singleton app classifier instance.
    
    Args:
        calendar_client: Optional calendar client instance for calendar integration
    """
    global _app_classifier
    if _app_classifier is None:
        _app_classifier = AppClassifier(calendar_client=calendar_client)
    # Update calendar client if provided
    elif calendar_client is not None:
        _app_classifier.calendar_client = calendar_client
    return _app_classifier
