"""
Time-based blocking policies.

This module implements blocking policies that are based on time constraints.
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Set, Union

from .base import BlockingPolicy, BlockingPolicyConfig, BlockingPolicyType
from focus_guard.core.domain.models import Domain


@dataclass
class TimeRange:
    """A time range with start and end times."""
    start: time
    end: time
    
    def contains(self, check_time: time) -> bool:
        """Check if the given time is within this range."""
        if self.start < self.end:
            return self.start <= check_time < self.end
        else:  # Overnight range
            return check_time >= self.start or check_time < self.end


@dataclass
class TimeBasedBlockingConfig(BlockingPolicyConfig):
    """Configuration for time-based blocking policies."""
    time_ranges: List[Dict[str, str]] = field(default_factory=list)
    days_of_week: Set[int] = field(default_factory=set)  # 0=Monday, 6=Sunday
    timezone: str = "UTC"
    
    def __post_init__(self):
        """Initialize the time ranges from string representations."""
        self._parsed_ranges = []
        for tr in self.time_ranges:
            start = datetime.strptime(tr['start'], '%H:%M').time()
            end = datetime.strptime(tr['end'], '%H:%M').time()
            self._parsed_ranges.append(TimeRange(start, end))
    
    def is_active(self, check_time: Optional[datetime] = None) -> bool:
        """Check if the policy is active at the given time."""
        if not self._parsed_ranges:
            return False
            
        check_time = check_time or datetime.now()
        current_time = check_time.time()
        current_weekday = check_time.weekday()
        
        # Check day of week
        if self.days_of_week and current_weekday not in self.days_of_week:
            return False
            
        # Check time ranges
        for time_range in self._parsed_ranges:
            if time_range.contains(current_time):
                return True
                
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "time_ranges": self.time_ranges,
            "days_of_week": list(self.days_of_week),
            "timezone": self.timezone,
        })
        return base_dict


class TimeBasedBlockingPolicy(BlockingPolicy):
    """
    A blocking policy that enforces time-based restrictions.
    
    This policy blocks resources during specific time ranges on specific days.
    """
    
    def __init__(self, config: TimeBasedBlockingConfig):
        """Initialize the time-based blocking policy."""
        if not isinstance(config, TimeBasedBlockingConfig):
            raise ValueError("config must be an instance of TimeBasedBlockingConfig")
        super().__init__(config)
        self._config = config
    
    def should_block(self, resource: Union[Domain, str], context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if the resource should be blocked based on time."""
        if not self._enabled:
            return False
            
        # Get the current time in the configured timezone
        check_time = context.get('timestamp') if context else None
        return self._config.is_active(check_time)
    
    def get_block_reason(self, resource: Union[Domain, str], context: Optional[Dict[str, Any]] = None) -> str:
        """Get the reason for blocking."""
        if not self._enabled:
            return ""
            
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        active_days = ", ".join(days[i] for i in sorted(self._config.days_of_week)) if self._config.days_of_week else "Every day"
        
        time_ranges = []
        for tr in self._config.time_ranges:
            time_ranges.append(f"{tr['start']} to {tr['end']}")
        
        return (
            f"Access restricted during {', '.join(time_ranges)} "
            f"on {active_days} (timezone: {self._config.timezone})."
        )
    
    @classmethod
    def create(
        cls,
        name: str,
        time_ranges: List[Dict[str, str]],
        days_of_week: Optional[Set[int]] = None,
        timezone: str = "UTC",
        enabled: bool = True,
        description: str = "",
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'TimeBasedBlockingPolicy':
        """Create a new time-based blocking policy."""
        config = TimeBasedBlockingConfig(
            policy_type=BlockingPolicyType.TIME_BASED,
            name=name,
            description=description,
            enabled=enabled,
            priority=priority,
            metadata=metadata or {},
            time_ranges=time_ranges,
            days_of_week=days_of_week or set(range(7)),
            timezone=timezone
        )
        return cls(config)
