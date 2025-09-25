"""
Calendar-based domain allowance system for Focus Guard.

This module determines which domains/apps are allowed based on calendar context.
It supports both proactive mode (pre-defined allowances) and reactive mode (on-demand evaluation).
"""
from typing import Dict, List, Optional, Set, Tuple
import datetime
from dataclasses import dataclass

from core.calendar.calendar_context import (
    get_current_context, get_current_event,
    CONTEXT_MEETING, CONTEXT_FOCUS, CONTEXT_BREAK, CONTEXT_NONE
)
from core.calendar.context_detector import get_context_detector
from core.domain_classifier.domain_classifier import classify_domain
from core.domain_classifier.filter_domain import filter_domain

# Define domain categories allowed for each calendar context
CONTEXT_DOMAIN_ALLOWANCES = {
    CONTEXT_MEETING: {
        "allowed_categories": ["work", "education"],
        "blocked_categories": ["social", "entertainment", "shopping"],
        # Always blocked: adult, gambling, etc. via domain_excluder
    },
    CONTEXT_FOCUS: {
        "allowed_categories": ["work", "education"],
        "blocked_categories": ["social", "entertainment", "shopping", "news"],
    },
    CONTEXT_BREAK: {
        "allowed_categories": ["work", "education", "news", "music"],
        "blocked_categories": [],
    },
    CONTEXT_NONE: {
        "allowed_categories": ["work", "education"],
        "blocked_categories": [],
    }
}

# Domain allowances for specific semantic contexts detected by ContextDetector
SEMANTIC_CONTEXT_DOMAIN_ALLOWANCES = {
    "meeting": {
        "allowed_categories": ["work", "education"],
        "allowed_domains": ["zoom.us", "teams.microsoft.com", "meet.google.com", "webex.com"]
    },
    "focus_work": {
        "allowed_categories": ["work"],
        "allowed_domains": ["github.com", "gitlab.com", "bitbucket.org", "stackoverflow.com", "aops.com "]
    },
    "math_science": {
        "allowed_categories": ["education"],
        "allowed_domains": ["khanacademy.org", "wolframalpha.com", "desmos.com", "mathway.com", "aops.com"]
    },
    "break": {
        "allowed_categories": ["entertainment", "news"],
        "allowed_domains": []
    },
    "after_hours": {
        "allowed_categories": ["entertainment", "social", "news", "shopping"],
        "allowed_domains": []
    }
}

class CalendarDomainAllowance:
    """
    Determines which domains are allowed based on calendar context.
    """
    
    def __init__(self, calendar_client):
        """
        Initialize with a calendar client.
        
        Args:
            calendar_client: An instance of a calendar client (e.g., GoogleCalendarClient)
        """
        self.calendar_client = calendar_client
        self.context_detector = get_context_detector()
        self._current_context = None
        self._current_event = None
        self._semantic_contexts = None
        self._last_update = None
        self._update_interval = datetime.timedelta(minutes=5)
        
    def update_context(self, force: bool = False) -> None:
        """
        Update the current context and event information.
        
        Args:
            force: If True, force update even if the update interval hasn't elapsed
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Only update if forced or if the update interval has elapsed
        if (force or self._last_update is None or 
                now - self._last_update > self._update_interval):
            self._current_context = get_current_context(self.calendar_client)
            self._current_event = get_current_event(self.calendar_client)
            
            # Extract semantic contexts if we have an event
            self._semantic_contexts = []
            if self._current_event:
                event_text = self._current_event.get('summary', '')
                if 'description' in self._current_event and self._current_event['description']:
                    event_text += " " + self._current_event['description']
                
                # Get semantic contexts with scores
                self._semantic_contexts = self.context_detector.detect_context(event_text)
            
            self._last_update = now
    
    def is_domain_allowed_proactive(self, domain: str) -> Tuple[bool, str]:
        """
        Proactively determine if a domain is allowed based on current calendar context.
        
        Args:
            domain: The domain to check
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        self.update_context()
        
        # First check if the domain is excluded (e.g., adult content)
        domain_category = filter_domain(domain)
        if domain_category == "excluded":
            return False, "Domain is in exclusion list"
        
        if domain_category == "whitelisted":
            return True, "Domain is whitelisted"
        
        # Check if we have a current context
        if not self._current_context or self._current_context == CONTEXT_NONE:
            return True, "No active calendar context"
        
        # Get allowances for the current calendar context
        context_allowances = CONTEXT_DOMAIN_ALLOWANCES.get(self._current_context, {})
        allowed_categories = context_allowances.get("allowed_categories", [])
        blocked_categories = context_allowances.get("blocked_categories", [])
        
        # Check if the domain category is explicitly allowed or blocked
        if domain_category in allowed_categories:
            return True, f"Domain category '{domain_category}' is allowed in {self._current_context} context"
        
        if domain_category in blocked_categories:
            return False, f"Domain category '{domain_category}' is blocked in {self._current_context} context"
        
        # If we have semantic contexts, check those
        if self._semantic_contexts:
            for semantic_context, score in self._semantic_contexts:
                # Only consider contexts with reasonable confidence
                if score < 0.4:
                    continue
                    
                semantic_allowances = SEMANTIC_CONTEXT_DOMAIN_ALLOWANCES.get(semantic_context, {})
                
                # Check if domain is explicitly allowed for this semantic context
                allowed_domains = semantic_allowances.get("allowed_domains", [])
                for allowed_domain in allowed_domains:
                    if domain == allowed_domain or domain.endswith("." + allowed_domain):
                        return True, f"Domain is allowed for '{semantic_context}' context"
                
                # Check if domain category is allowed for this semantic context
                allowed_categories = semantic_allowances.get("allowed_categories", [])
                if domain_category in allowed_categories:
                    return True, f"Domain category '{domain_category}' is allowed for '{semantic_context}' context"
        
        # Default to allowing unknown domains
        return True, "Domain not specifically blocked"
    
    def is_domain_allowed_reactive(self, domain: str, app_title: str = None) -> Tuple[bool, str]:
        """
        Reactively determine if a domain is allowed based on current context and domain/app content.
        
        Args:
            domain: The domain to check
            app_title: Optional title of the application window
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        # First check the proactive rules
        is_allowed, reason = self.is_domain_allowed_proactive(domain)
        if not is_allowed:
            return False, reason
            
        # If we don't have a current event or semantic context, just use proactive result
        if not self._current_event or not self._semantic_contexts:
            return is_allowed, reason
        
        # For reactive mode, we need to check if the domain/app is relevant to the current event
        combined_text = domain
        if app_title:
            combined_text += " " + app_title
            
        # Get the top semantic context
        top_context = self._semantic_contexts[0][0] if self._semantic_contexts else None
        
        if top_context:
            # Check if domain or app title has any semantic similarity to the event context
            event_text = self._current_event.get('summary', '')
            if 'description' in self._current_event and self._current_event['description']:
                event_text += " " + self._current_event['description']
                
            # Use the context detector to check similarity between domain/app and event
            domain_contexts = self.context_detector.detect_context(combined_text)
            
            # If the domain context matches the event context, allow it
            for domain_context, score in domain_contexts:
                if domain_context == top_context and score >= 0.3:
                    return True, f"Domain appears relevant to '{top_context}' context"
        
        # If we got here, the domain passed proactive checks but didn't match reactively
        # Default to the proactive result
        return is_allowed, reason

# Singleton instance
_calendar_domain_allowance = None

def get_calendar_domain_allowance(calendar_client) -> CalendarDomainAllowance:
    """Get or create the singleton calendar domain allowance instance."""
    global _calendar_domain_allowance
    if _calendar_domain_allowance is None:
        _calendar_domain_allowance = CalendarDomainAllowance(calendar_client)
    return _calendar_domain_allowance
