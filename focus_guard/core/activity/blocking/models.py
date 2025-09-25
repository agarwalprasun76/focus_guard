"""
Data models for application blocking system.

This module defines the core data models used by the application blocking system,
including blocking policies, decisions, and events.
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional, List, Dict, Any, Union
from enum import Enum


class BlockingAction(Enum):
    """Actions that can be taken when a blocking rule is triggered."""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    REDIRECT = "redirect"


class TimeRestrictionType(Enum):
    """Types of time-based restrictions."""
    DAILY_HOURS = "daily_hours"  # Specific hours of the day
    DAILY_LIMIT = "daily_limit"  # Maximum time per day
    WEEKLY_LIMIT = "weekly_limit"  # Maximum time per week
    BREAK_INTERVAL = "break_interval"  # Mandatory breaks


@dataclass
class TimeRestriction:
    """Represents a time-based restriction for application usage."""
    type: TimeRestrictionType
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    max_duration_minutes: Optional[int] = None
    break_duration_minutes: Optional[int] = None
    days_of_week: List[int] = field(default_factory=list)  # 0=Monday, 6=Sunday
    
    def is_active_at(self, check_time: datetime) -> bool:
        """Check if this restriction is active at the given time."""
        if self.type == TimeRestrictionType.DAILY_HOURS:
            if self.start_time and self.end_time:
                current_time = check_time.time()
                if self.start_time <= self.end_time:
                    return self.start_time <= current_time <= self.end_time
                else:  # Crosses midnight
                    return current_time >= self.start_time or current_time <= self.end_time
        
        if self.days_of_week:
            weekday = check_time.weekday()
            return weekday in self.days_of_week
        
        return True


@dataclass
class BlockingPolicy:
    """
    Represents a blocking policy with rules for applications and domains.
    """
    name: str
    description: str = ""
    enabled: bool = True
    priority: int = 0  # Higher numbers = higher priority
    
    # Application patterns to match
    app_patterns: List[str] = field(default_factory=list)
    app_blacklist: List[str] = field(default_factory=list)
    app_whitelist: List[str] = field(default_factory=list)
    
    # Domain patterns to match
    domain_patterns: List[str] = field(default_factory=list)
    domain_blacklist: List[str] = field(default_factory=list)
    domain_whitelist: List[str] = field(default_factory=list)
    
    # Time-based restrictions
    time_restrictions: List[TimeRestriction] = field(default_factory=list)
    
    # Blocking behavior
    action: BlockingAction = BlockingAction.BLOCK
    grace_period_seconds: int = 30
    warning_message: str = "This application is blocked by Focus Guard policy."
    redirect_url: Optional[str] = None
    
    # Override settings
    override_allowed: bool = True
    override_duration_minutes: int = 15
    override_requires_reason: bool = False
    override_password: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def matches_application(self, app_name: str) -> bool:
        """Check if this policy matches the given application name."""
        app_lower = app_name.lower()
        
        # Check whitelist first (if exists, only allow whitelisted apps)
        if self.app_whitelist:
            return any(pattern.lower() in app_lower for pattern in self.app_whitelist)
        
        # Check blacklist
        if self.app_blacklist:
            if any(pattern.lower() in app_lower for pattern in self.app_blacklist):
                return True
        
        # Check patterns
        if self.app_patterns:
            return any(pattern.lower() in app_lower for pattern in self.app_patterns)
        
        return False
    
    def matches_domain(self, domain: str) -> bool:
        """Check if this policy matches the given domain."""
        if not domain:
            return False
        
        domain_lower = domain.lower()
        
        # Check whitelist first
        if self.domain_whitelist:
            return not any(pattern.lower() in domain_lower for pattern in self.domain_whitelist)
        
        # Check blacklist
        if self.domain_blacklist:
            if any(pattern.lower() in domain_lower for pattern in self.domain_blacklist):
                return True
        
        # Check patterns
        if self.domain_patterns:
            return any(pattern.lower() in domain_lower for pattern in self.domain_patterns)
        
        return False
    
    def is_time_restricted(self, check_time: datetime = None) -> bool:
        """Check if this policy is time-restricted at the given time."""
        if not self.time_restrictions:
            return False
        
        if check_time is None:
            check_time = datetime.now()
        
        return any(restriction.is_active_at(check_time) for restriction in self.time_restrictions)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary for serialization."""
        return {
            'name': self.name,
            'description': self.description,
            'enabled': self.enabled,
            'priority': self.priority,
            'app_patterns': self.app_patterns,
            'app_blacklist': self.app_blacklist,
            'app_whitelist': self.app_whitelist,
            'domain_patterns': self.domain_patterns,
            'domain_blacklist': self.domain_blacklist,
            'domain_whitelist': self.domain_whitelist,
            'time_restrictions': [
                {
                    'type': tr.type.value,
                    'start_time': tr.start_time.isoformat() if tr.start_time else None,
                    'end_time': tr.end_time.isoformat() if tr.end_time else None,
                    'max_duration_minutes': tr.max_duration_minutes,
                    'break_duration_minutes': tr.break_duration_minutes,
                    'days_of_week': tr.days_of_week
                }
                for tr in self.time_restrictions
            ],
            'action': self.action.value,
            'grace_period_seconds': self.grace_period_seconds,
            'warning_message': self.warning_message,
            'redirect_url': self.redirect_url,
            'override_allowed': self.override_allowed,
            'override_duration_minutes': self.override_duration_minutes,
            'override_requires_reason': self.override_requires_reason,
            'override_password': self.override_password,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlockingPolicy':
        """Create policy from dictionary."""
        # Parse time restrictions
        time_restrictions = []
        for tr_data in data.get('time_restrictions', []):
            restriction = TimeRestriction(
                type=TimeRestrictionType(tr_data['type']),
                start_time=time.fromisoformat(tr_data['start_time']) if tr_data.get('start_time') else None,
                end_time=time.fromisoformat(tr_data['end_time']) if tr_data.get('end_time') else None,
                max_duration_minutes=tr_data.get('max_duration_minutes'),
                break_duration_minutes=tr_data.get('break_duration_minutes'),
                days_of_week=tr_data.get('days_of_week', [])
            )
            time_restrictions.append(restriction)
        
        return cls(
            name=data['name'],
            description=data.get('description', ''),
            enabled=data.get('enabled', True),
            priority=data.get('priority', 0),
            app_patterns=data.get('app_patterns', []),
            app_blacklist=data.get('app_blacklist', []),
            app_whitelist=data.get('app_whitelist', []),
            domain_patterns=data.get('domain_patterns', []),
            domain_blacklist=data.get('domain_blacklist', []),
            domain_whitelist=data.get('domain_whitelist', []),
            time_restrictions=time_restrictions,
            action=BlockingAction(data.get('action', 'block')),
            grace_period_seconds=data.get('grace_period_seconds', 30),
            warning_message=data.get('warning_message', 'This application is blocked by Focus Guard policy.'),
            redirect_url=data.get('redirect_url'),
            override_allowed=data.get('override_allowed', True),
            override_duration_minutes=data.get('override_duration_minutes', 15),
            override_requires_reason=data.get('override_requires_reason', False),
            override_password=data.get('override_password'),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        )


@dataclass
class BlockingDecision:
    """Represents a decision made by the policy engine."""
    policy_name: str
    action: BlockingAction
    reason: str
    app_name: str
    domain: Optional[str] = None
    window_title: Optional[str] = None
    grace_period_seconds: int = 0
    warning_message: str = ""
    redirect_url: Optional[str] = None
    override_allowed: bool = True
    timestamp: datetime = field(default_factory=datetime.now)
    
    def should_block(self) -> bool:
        """Check if this decision requires blocking the application."""
        return self.action == BlockingAction.BLOCK
    
    def should_warn(self) -> bool:
        """Check if this decision requires showing a warning."""
        return self.action in [BlockingAction.WARN, BlockingAction.BLOCK]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary."""
        return {
            'policy_name': self.policy_name,
            'action': self.action.value,
            'reason': self.reason,
            'app_name': self.app_name,
            'domain': self.domain,
            'window_title': self.window_title,
            'grace_period_seconds': self.grace_period_seconds,
            'warning_message': self.warning_message,
            'redirect_url': self.redirect_url,
            'override_allowed': self.override_allowed,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class BlockingEvent:
    """Represents an event in the blocking system."""
    event_type: str  # 'blocked', 'warned', 'overridden', 'allowed'
    app_name: str
    domain: Optional[str] = None
    window_title: Optional[str] = None
    policy_name: Optional[str] = None
    reason: Optional[str] = None
    override_reason: Optional[str] = None
    override_duration_minutes: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'event_type': self.event_type,
            'app_name': self.app_name,
            'domain': self.domain,
            'window_title': self.window_title,
            'policy_name': self.policy_name,
            'reason': self.reason,
            'override_reason': self.override_reason,
            'override_duration_minutes': self.override_duration_minutes,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class OverrideRequest:
    """Represents a request to override a blocking decision."""
    app_name: str
    domain: Optional[str] = None
    policy_name: str = ""
    reason: str = ""
    duration_minutes: int = 15
    password: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert override request to dictionary."""
        return {
            'app_name': self.app_name,
            'domain': self.domain,
            'policy_name': self.policy_name,
            'reason': self.reason,
            'duration_minutes': self.duration_minutes,
            'password': self.password,
            'timestamp': self.timestamp.isoformat()
        }
