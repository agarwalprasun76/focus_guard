"""
Distraction Policy Manager

This module provides functionality to determine what applications and domains should be
blocked or allowed based on the current calendar context (meeting, focus, break, etc.).

It integrates with the domain classifier to provide intelligent blocking based on
categories and specific domain rules.
"""
from enum import Enum
from typing import Dict, List, Any, Set, Optional, Union, TypedDict

from core.domain_classifier import (
    classify_domain,
    domain_whitelist,
    is_valid_domain,
    normalize_domain,
    get_all_categories
)

class ContextType(Enum):
    """Enumeration of different context types."""
    MEETING = "meeting"
    FOCUS = "focus"
    BREAK = "break"
    NONE = "none"


class StrictnessLevel(Enum):
    """Enumeration of policy strictness levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Policy(TypedDict, total=False):
    """Type definition for policy configuration."""
    block_categories: List[str]
    allow_categories: List[str]
    block_apps: List[str]
    allow_apps: List[str]
    block_domains: List[str]
    allow_domains: List[str]
    strictness: str

def get_default_policies() -> Dict[str, Policy]:
    """Return the default policies for different contexts.
    
    Returns:
        Dict mapping context types to their default policies.
    """
    return {
        ContextType.MEETING.value: {
            'block_categories': ['entertainment', 'social_media', 'gaming', 'shopping'],
            'allow_categories': ['productivity', 'communication', 'development'],
            'block_apps': [],
            'allow_apps': ['zoom.exe', 'teams.exe', 'slack.exe', 'chrome.exe', 'firefox.exe', 'edge.exe'],
            'block_domains': ['youtube.com', 'facebook.com', 'twitter.com', 'instagram.com', 'reddit.com'],
            'allow_domains': ['docs.google.com', 'drive.google.com', 'github.com', 'office.com'],
            'strictness': StrictnessLevel.MEDIUM.value
        },
        ContextType.FOCUS.value: {
            'block_categories': ['entertainment', 'social_media', 'gaming', 'shopping', 'news'],
            'allow_categories': ['productivity', 'development'],
            'block_apps': ['outlook.exe'],  # Block email during focus time
            'allow_apps': ['code.exe', 'notepad.exe', 'word.exe', 'excel.exe', 'powerpnt.exe'],
            'block_domains': [
                'youtube.com', 'facebook.com', 'twitter.com', 'instagram.com', 
                'reddit.com', 'news.com', 'cnn.com', 'bbc.com'
            ],
            'allow_domains': ['github.com', 'stackoverflow.com', 'docs.python.org'],
            'strictness': StrictnessLevel.HIGH.value
        },
        ContextType.BREAK.value: {
            'block_categories': [],  # Don't block anything during breaks
            'allow_categories': ['entertainment', 'social_media', 'news'],
            'block_apps': [],
            'allow_apps': [],
            'block_domains': [],
            'allow_domains': [],
            'strictness': StrictnessLevel.LOW.value
        },
        ContextType.NONE.value: {
            'block_categories': ['gaming'],  # Minimal blocking when no specific context
            'allow_categories': ['productivity', 'development', 'communication'],
            'block_apps': [],
            'allow_apps': [],
            'block_domains': [],
            'allow_domains': [],
            'strictness': StrictnessLevel.LOW.value
        }
    }

# Cache the default policies
DEFAULT_POLICIES = get_default_policies()

def get_policy_for_context(context: Union[str, ContextType]) -> Policy:
    """Get the policy for the given context.
    
    Args:
        context: The current context (must be one of ContextType values or their string representations)
        
    Returns:
        A copy of the policy dictionary for the given context
        
    Raises:
        ValueError: If the context is invalid
    """
    # Convert ContextType enum to string if needed
    if isinstance(context, ContextType):
        context = context.value
    
    # Normalize the context string
    context = context.lower().strip() if context else ContextType.NONE.value
    
    # Get the policy or default to NONE context
    try:
        policy = DEFAULT_POLICIES.get(context, DEFAULT_POLICIES[ContextType.NONE.value])
        return policy.copy()
    except KeyError:
        raise ValueError(f"Invalid context: {context}")

def should_block_domain(domain: str, policy: Optional[Policy] = None) -> bool:
    """Determine if a domain should be blocked based on the given policy.
    
    Args:
        domain: The domain to check
        policy: The policy to use (defaults to NONE context policy if None)
        
    Returns:
        bool: True if the domain should be blocked, False otherwise
    """
    if not domain:
        return False
        
    # Get default policy if none provided
    if policy is None:
        policy = get_policy_for_context(ContextType.NONE)
    
    # Normalize the domain
    normalized_domain = normalize_domain(domain)
    if not normalized_domain:
        return False  # Invalid domain, can't make a decision
    
    # Check if domain is explicitly allowed
    if any(normalized_domain == normalize_domain(d) for d in policy.get('allow_domains', [])):
        return False
        
    # Check if domain is explicitly blocked
    if any(normalized_domain == normalize_domain(d) for d in policy.get('block_domains', [])):
        return True
    
    # Check domain categories if needed
    domain_category = classify_domain(normalized_domain)
    if domain_category in policy.get('block_categories', []):
        return True
        
    # Check if we're in allowlist-only mode (high strictness)
    if policy.get('strictness') == StrictnessLevel.HIGH.value:
        return domain_category not in policy.get('allow_categories', [])
    
    return False

def get_policy_for_event(event: Dict[str, Any]) -> Policy:
    """Determine policy based on a specific calendar event.
    
    This allows for more fine-grained control based on event properties.
    
    Args:
        event: Calendar event dictionary with at least 'summary' and 'description' keys
        
    Returns:
        Policy dictionary with rules based on the event
    """
    # Start with the default policy for this event's context
    context = determine_event_context(event)
    policy = get_policy_for_context(context)
    
    # Make a copy to avoid modifying the default policy
    policy = policy.copy()
    
    # Example: Make meetings with "Interview" in title more strict
    if context == ContextType.MEETING.value and 'interview' in event.get('summary', '').lower():
        policy['strictness'] = StrictnessLevel.HIGH.value
        policy['block_categories'] = list(set(policy.get('block_categories', []) + 
                                           ['social_media', 'news', 'shopping']))
    
    # Example: Allow specific domains for certain meetings
    description = event.get('description', '').lower()
    if 'github' in description:
        policy['allow_domains'] = list(set(policy.get('allow_domains', []) + 
                                        ['github.com', 'githubusercontent.com']))
    
    # Example: Block social media during focus sessions with specific keywords
    if context == ContextType.FOCUS.value and any(
        kw in description for kw in ['deep work', 'no distractions']
    ):
        policy['block_categories'] = list(set(policy.get('block_categories', []) + 
                                           ['social_media', 'news', 'entertainment']))
    
    return policy

def determine_event_context(event: Dict[str, Any]) -> str:
    """Determine the context type for a specific calendar event.
    
    Args:
        event: Calendar event dictionary with at least 'summary' and 'description' keys
        
    Returns:
        str: The determined context (one of ContextType values)
    """
    # Default to meeting context
    context = ContextType.MEETING
    
    # Get event details (case-insensitive)
    summary = event.get('summary', '').lower()
    description = event.get('description', '').lower()
    full_text = f"{summary} {description}"
    
    # Check for focus time
    focus_terms = ['focus', 'deep work', 'concentration', 'coding', 'development']
    if any(term in full_text for term in focus_terms):
        return ContextType.FOCUS.value
        
    # Check for break time
    break_terms = ['break', 'lunch', 'coffee', 'rest', 'break time', 'coffee break']
    if any(term in full_text for term in break_terms):
        return ContextType.BREAK.value
        
    # Check for no-meeting time
    no_meeting_terms = ['no meetings', 'no calls', 'do not disturb', 'focus time', 'heads down']
    if any(term in full_text for term in no_meeting_terms):
        return ContextType.FOCUS.value
        
    # Check for personal time
    personal_terms = ['personal', 'time off', 'vacation', 'ooo', 'out of office']
    if any(term in full_text for term in personal_terms):
        return ContextType.BREAK.value
    
    # If it's a short meeting, treat it as a focus block
    start = event.get('start', {}).get('dateTime')
    end = event.get('end', {}).get('dateTime')
    
    if start and end:
        try:
            from datetime import datetime
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            duration = (end_dt - start_dt).total_seconds() / 60  # in minutes
            
            # Meetings shorter than 15 minutes might be quick syncs
            if duration < 15:
                return ContextType.FOCUS.value
                
        except (ValueError, AttributeError):
            pass
    
    # Default to none if we can't determine
    return ContextType.NONE.value
