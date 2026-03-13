"""Domain usage tracking for enhanced blocking rules.

This module tracks time spent on domains, distinguishing between active and
inactive window states, and implements non-linear scaling for override limits.

Now supports classification-aware budgets: different time limits based on
content type (EDUCATION vs ENTERTAINMENT vs GAMING, etc.)
"""

from __future__ import annotations

import json
import logging
import math
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

logger = logging.getLogger(__name__)


@dataclass
class ClassificationBudget:
    """Budget configuration for a specific content classification.
    
    Allows different time limits based on content type:
    - EDUCATION:EDUCATIONAL gets generous budget (60 min)
    - ENTERTAINMENT:DISTRACTION gets strict budget (10 min)
    """
    category: str  # EDUCATION, ENTERTAINMENT, GAMING, etc.
    usefulness: str  # EDUCATIONAL, ENRICHMENT, NEUTRAL, DISTRACTION
    
    max_cumulative_time_seconds: int = 900  # 15 min default
    max_overrides_per_day: int = 3
    max_override_duration_seconds: int = 300  # 5 min per session
    penalty_per_extra_override_seconds: int = 60
    
    # Audit settings for accountability
    require_screenshot: bool = False
    notify_parent: bool = False
    
    @property
    def budget_key(self) -> str:
        """Key for looking up this budget."""
        return f"{self.category}:{self.usefulness}"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClassificationBudget':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# Default classification budgets for common content types
DEFAULT_CLASSIFICATION_BUDGETS: Dict[str, ClassificationBudget] = {
    # Educational content - generous budgets
    "EDUCATION:EDUCATIONAL": ClassificationBudget(
        category="EDUCATION",
        usefulness="EDUCATIONAL",
        max_cumulative_time_seconds=3600,  # 60 min
        max_overrides_per_day=10,
        max_override_duration_seconds=600,  # 10 min per session
        penalty_per_extra_override_seconds=0,  # No penalty
        require_screenshot=False,
        notify_parent=False,
    ),
    "EDUCATION:ENRICHMENT": ClassificationBudget(
        category="EDUCATION",
        usefulness="ENRICHMENT",
        max_cumulative_time_seconds=1800,  # 30 min
        max_overrides_per_day=5,
        max_override_duration_seconds=600,
        penalty_per_extra_override_seconds=30,
        require_screenshot=False,
        notify_parent=False,
    ),
    # Productivity - similar to education
    "PRODUCTIVITY:EDUCATIONAL": ClassificationBudget(
        category="PRODUCTIVITY",
        usefulness="EDUCATIONAL",
        max_cumulative_time_seconds=3600,
        max_overrides_per_day=10,
        max_override_duration_seconds=600,
        penalty_per_extra_override_seconds=0,
        require_screenshot=False,
        notify_parent=False,
    ),
    # Entertainment - moderate budgets
    "ENTERTAINMENT:NEUTRAL": ClassificationBudget(
        category="ENTERTAINMENT",
        usefulness="NEUTRAL",
        max_cumulative_time_seconds=900,  # 15 min
        max_overrides_per_day=3,
        max_override_duration_seconds=300,
        penalty_per_extra_override_seconds=60,
        require_screenshot=False,
        notify_parent=False,
    ),
    "ENTERTAINMENT:DISTRACTION": ClassificationBudget(
        category="ENTERTAINMENT",
        usefulness="DISTRACTION",
        max_cumulative_time_seconds=600,  # 10 min
        max_overrides_per_day=2,
        max_override_duration_seconds=300,
        penalty_per_extra_override_seconds=120,  # 2 min penalty
        require_screenshot=True,  # Audit
        notify_parent=True,  # Alert parent
    ),
    # Gaming - strict budgets
    "GAMING:NEUTRAL": ClassificationBudget(
        category="GAMING",
        usefulness="NEUTRAL",
        max_cumulative_time_seconds=600,  # 10 min
        max_overrides_per_day=2,
        max_override_duration_seconds=300,
        penalty_per_extra_override_seconds=90,
        require_screenshot=False,
        notify_parent=False,
    ),
    "GAMING:DISTRACTION": ClassificationBudget(
        category="GAMING",
        usefulness="DISTRACTION",
        max_cumulative_time_seconds=300,  # 5 min
        max_overrides_per_day=1,
        max_override_duration_seconds=300,
        penalty_per_extra_override_seconds=180,  # 3 min penalty
        require_screenshot=True,
        notify_parent=True,
    ),
    # Social media - strict
    "SOCIAL_MEDIA:DISTRACTION": ClassificationBudget(
        category="SOCIAL_MEDIA",
        usefulness="DISTRACTION",
        max_cumulative_time_seconds=600,  # 10 min
        max_overrides_per_day=2,
        max_override_duration_seconds=300,
        penalty_per_extra_override_seconds=120,
        require_screenshot=True,
        notify_parent=True,
    ),
    # Unknown - moderate default
    "UNKNOWN:NEUTRAL": ClassificationBudget(
        category="UNKNOWN",
        usefulness="NEUTRAL",
        max_cumulative_time_seconds=900,  # 15 min
        max_overrides_per_day=3,
        max_override_duration_seconds=300,
        penalty_per_extra_override_seconds=60,
        require_screenshot=False,
        notify_parent=False,
    ),
}


@dataclass
class DomainRuleConfig:
    """Per-domain blocking rule configuration.
    
    Budget system: Users get max_cumulative_time_seconds (e.g., 15 mins) to use.
    They can split it into up to max_overrides_per_day visits.
    If they use more visits than max_overrides_per_day, a penalty is applied.
    
    Now supports classification-aware budgets: different limits based on
    content type (EDUCATION vs ENTERTAINMENT, etc.)
    
    Example with 15 min budget and 3 baseline overrides:
    - 3 visits × 5 mins = 15 mins effective (no penalty)
    - 5 visits × 3 mins = 15 + 2*60 = 17 mins effective
    - 10 visits × 1.5 mins = 15 + 7*60 = 22 mins effective
    """
    domain: str
    max_overrides_per_day: int = 3  # Baseline number of overrides (no penalty up to this)
    max_override_duration_seconds: int = 300  # 5 minutes per override
    max_cumulative_time_seconds: int = 900  # 15 minutes total budget per day
    
    # Penalty for exceeding baseline overrides (seconds per extra override)
    penalty_per_extra_override_seconds: int = 60  # 1 minute penalty per extra override
    
    # If True, apply penalty for visits beyond max_overrides_per_day
    use_fragmentation_penalty: bool = True
    min_override_duration_seconds: int = 60  # 1 minute minimum per override
    
    # If True, time in inactive windows doesn't count toward cumulative limit
    only_count_active_window: bool = True
    
    # Classification-specific budgets (overrides defaults when content is classified)
    # Key format: "CATEGORY:USEFULNESS" e.g., "EDUCATION:EDUCATIONAL"
    classification_budgets: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Whether to use classification-aware budgets
    use_classification_budgets: bool = True
    
    def get_budget_for_classification(
        self, 
        category: str, 
        usefulness: str
    ) -> ClassificationBudget:
        """Get the budget for a specific classification.
        
        Lookup order:
        1. Domain-specific classification budget
        2. Global default classification budget
        3. Fallback to domain's default settings
        """
        budget_key = f"{category}:{usefulness}"
        
        # Check domain-specific budgets first
        if budget_key in self.classification_budgets:
            return ClassificationBudget.from_dict(self.classification_budgets[budget_key])
        
        # Check global defaults
        if budget_key in DEFAULT_CLASSIFICATION_BUDGETS:
            return DEFAULT_CLASSIFICATION_BUDGETS[budget_key]
        
        # Try category-only match with NEUTRAL usefulness
        neutral_key = f"{category}:NEUTRAL"
        if neutral_key in DEFAULT_CLASSIFICATION_BUDGETS:
            return DEFAULT_CLASSIFICATION_BUDGETS[neutral_key]
        
        # Fallback to domain's default settings
        return ClassificationBudget(
            category=category,
            usefulness=usefulness,
            max_cumulative_time_seconds=self.max_cumulative_time_seconds,
            max_overrides_per_day=self.max_overrides_per_day,
            max_override_duration_seconds=self.max_override_duration_seconds,
            penalty_per_extra_override_seconds=self.penalty_per_extra_override_seconds,
            require_screenshot=False,
            notify_parent=False,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        # Convert classification_budgets to serializable format
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainRuleConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class DomainUsageSession:
    """A single usage session for a domain."""
    session_id: str
    domain: str
    start_time: float
    end_time: Optional[float] = None
    active_seconds: float = 0.0  # Time in active window
    inactive_seconds: float = 0.0  # Time in inactive window
    override_id: Optional[str] = None
    
    @property
    def total_seconds(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def is_active(self) -> bool:
        return self.end_time is None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "domain": self.domain,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "active_seconds": self.active_seconds,
            "inactive_seconds": self.inactive_seconds,
            "total_seconds": self.total_seconds,
            "override_id": self.override_id,
        }


@dataclass
class DomainDailyStats:
    """Daily statistics for a domain."""
    domain: str
    date: str  # YYYY-MM-DD
    override_count: int = 0
    total_active_seconds: float = 0.0
    total_inactive_seconds: float = 0.0
    session_count: int = 0
    sessions: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def total_seconds(self) -> float:
        return self.total_active_seconds + self.total_inactive_seconds
    
    def get_effective_time_used(
        self, 
        baseline_overrides: int = 3, 
        penalty_per_extra: int = 60
    ) -> float:
        """Calculate effective time with penalty for frequent short visits.
        
        The idea is users get a time budget (e.g., 15 mins from 3 overrides × 5 mins).
        They can split it however they want, but more visits incur a penalty.
        
        Formula: total_active_seconds + penalty
        Where penalty = (override_count - baseline_overrides) * penalty_per_extra
        
        Example with 15 min budget and baseline 3 overrides:
        - 3 visits × 5 mins = 15 mins actual → 15 mins effective (no penalty)
        - 5 visits × 3 mins = 15 mins actual → 15 + (5-3)*60 = 17 mins effective
        - 10 visits × 1.5 mins = 15 mins actual → 15 + (10-3)*60 = 22 mins effective
        
        This allows flexibility while discouraging excessive fragmentation.
        
        Args:
            baseline_overrides: Number of overrides before penalty kicks in
            penalty_per_extra: Seconds of penalty per override beyond baseline
        """
        if self.override_count == 0:
            return self.total_active_seconds
        
        # Only penalize if more overrides than baseline
        extra_overrides = max(0, self.override_count - baseline_overrides)
        penalty = extra_overrides * penalty_per_extra
        
        return self.total_active_seconds + penalty
    
    @property
    def effective_time_used(self) -> float:
        """Calculate effective time with default penalty settings."""
        return self.get_effective_time_used()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "date": self.date,
            "override_count": self.override_count,
            "total_active_seconds": self.total_active_seconds,
            "total_inactive_seconds": self.total_inactive_seconds,
            "total_seconds": self.total_seconds,
            "effective_time_used": self.effective_time_used,
            "session_count": self.session_count,
            "sessions": self.sessions,
        }


class DomainUsageTracker:
    """Tracks domain usage with active/inactive window distinction.
    
    Features:
    - Per-domain rule configuration
    - Active vs inactive window time tracking
    - Non-linear scaling for override limits
    - Daily statistics and history
    - Integration with activity monitor for summary reports
    """
    
    DEFAULT_RULE = DomainRuleConfig(
        domain="*",
        max_overrides_per_day=3,
        max_override_duration_seconds=300,
        max_cumulative_time_seconds=900,
    )
    
    def __init__(
        self,
        data_file: Optional[Path] = None,
        rules_file: Optional[Path] = None,
    ):
        self._lock = threading.RLock()
        self._data_file = data_file or Path.home() / ".focus_guard" / "domain_usage.json"
        self._rules_file = rules_file or Path.home() / ".focus_guard" / "domain_rules.json"
        
        # Per-domain rules
        self._domain_rules: Dict[str, DomainRuleConfig] = {}
        
        # Active sessions (domain -> session)
        self._active_sessions: Dict[str, DomainUsageSession] = {}
        
        # Daily stats (domain -> stats)
        self._daily_stats: Dict[str, DomainDailyStats] = {}
        self._current_date: str = ""
        
        # Track which tabs are in active windows
        self._active_tabs: Set[str] = set()  # tab_id
        self._tab_domains: Dict[str, str] = {}  # tab_id -> domain
        
        # Auto-save tracking
        self._usage_dirty: bool = False
        self._autosave_interval: float = 60.0  # seconds
        self._autosave_timer: Optional[threading.Timer] = None
        
        # Ensure directories exist
        self._data_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load data
        self._load_rules()
        self._load_daily_stats()
        
        # Start periodic auto-save
        self._start_autosave()
        
        logger.info("DomainUsageTracker initialized (auto-save every %.0fs)", self._autosave_interval)
    
    def _load_rules(self) -> None:
        """Load domain rules from file."""
        try:
            if self._rules_file.exists():
                with open(self._rules_file, 'r') as f:
                    data = json.load(f)
                    for rule_data in data.get("rules", []):
                        rule = DomainRuleConfig.from_dict(rule_data)
                        self._domain_rules[rule.domain] = rule
                logger.debug("Loaded %d domain rules", len(self._domain_rules))
        except Exception as e:
            logger.warning("Could not load domain rules: %s", e)
    
    def _save_rules(self) -> None:
        """Save domain rules to file."""
        try:
            data = {"rules": [r.to_dict() for r in self._domain_rules.values()]}
            with open(self._rules_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save domain rules: %s", e)
    
    def _load_daily_stats(self) -> None:
        """Load today's stats from file."""
        try:
            today = date.today().isoformat()
            self._current_date = today
            
            if self._data_file.exists():
                with open(self._data_file, 'r') as f:
                    data = json.load(f)
                    # Only load today's stats
                    for domain, stats_data in data.get("daily_stats", {}).items():
                        if stats_data.get("date") == today:
                            self._daily_stats[domain] = DomainDailyStats(
                                domain=domain,
                                date=today,
                                override_count=stats_data.get("override_count", 0),
                                total_active_seconds=stats_data.get("total_active_seconds", 0),
                                total_inactive_seconds=stats_data.get("total_inactive_seconds", 0),
                                session_count=stats_data.get("session_count", 0),
                                sessions=stats_data.get("sessions", []),
                            )
                logger.debug("Loaded daily stats for %d domains", len(self._daily_stats))
        except Exception as e:
            logger.warning("Could not load daily stats: %s", e)
    
    def _save_daily_stats(self) -> None:
        """Save daily stats to file."""
        try:
            data = {
                "daily_stats": {d: s.to_dict() for d, s in self._daily_stats.items()},
                "schema_version": 1,
                "last_updated": time.time(),
            }
            with open(self._data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save daily stats: %s", e)
    
    def _start_autosave(self) -> None:
        """Start the periodic auto-save timer."""
        self._autosave_timer = threading.Timer(self._autosave_interval, self._autosave_tick)
        self._autosave_timer.daemon = True
        self._autosave_timer.start()

    def _autosave_tick(self) -> None:
        """Periodic auto-save callback."""
        try:
            with self._lock:
                if self._usage_dirty:
                    self._save_daily_stats()
                    self._usage_dirty = False
                    logger.debug("Auto-saved domain usage stats")
        except Exception as e:
            logger.warning("Auto-save failed: %s", e)
        finally:
            # Reschedule
            self._autosave_timer = threading.Timer(self._autosave_interval, self._autosave_tick)
            self._autosave_timer.daemon = True
            self._autosave_timer.start()

    def stop_autosave(self) -> None:
        """Stop the auto-save timer and flush any pending data."""
        if self._autosave_timer:
            self._autosave_timer.cancel()
            self._autosave_timer = None
        with self._lock:
            if self._usage_dirty:
                self._save_daily_stats()
                self._usage_dirty = False
                logger.info("Flushed domain usage stats on shutdown")

    def _reset_daily_if_needed(self) -> None:
        """Reset daily stats if it's a new day."""
        today = date.today().isoformat()
        if self._current_date != today:
            # Archive old stats before reset
            self._archive_daily_stats()
            self._daily_stats = {}
            self._current_date = today
            logger.info("Reset daily stats for new day: %s", today)
    
    def _archive_daily_stats(self) -> None:
        """Archive daily stats to history file."""
        if not self._daily_stats:
            return
        try:
            history_file = self._data_file.parent / "domain_usage_history.json"
            history = {"history": []}
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
            
            # Add today's stats
            for stats in self._daily_stats.values():
                history["history"].append(stats.to_dict())
            
            # Keep only last 90 days
            cutoff_date = (datetime.now().date().toordinal() - 90)
            history["history"] = [
                h for h in history["history"]
                if datetime.strptime(h["date"], "%Y-%m-%d").date().toordinal() > cutoff_date
            ]
            
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error("Failed to archive daily stats: %s", e)
    
    def get_rule(self, domain: str) -> DomainRuleConfig:
        """Get the rule for a domain, falling back to default."""
        with self._lock:
            # Check exact match
            if domain in self._domain_rules:
                return self._domain_rules[domain]
            
            # Check parent domain (e.g., www.facebook.com -> facebook.com)
            parts = domain.split('.')
            for i in range(1, len(parts)):
                parent = '.'.join(parts[i:])
                if parent in self._domain_rules:
                    return self._domain_rules[parent]
            
            # Check wildcard
            if "*" in self._domain_rules:
                return self._domain_rules["*"]
            
            return self.DEFAULT_RULE
    
    def set_rule(self, rule: DomainRuleConfig) -> None:
        """Set a rule for a domain."""
        with self._lock:
            self._domain_rules[rule.domain] = rule
            self._save_rules()
            logger.info("Set rule for domain %s: max_overrides=%d, max_duration=%ds, max_cumulative=%ds",
                       rule.domain, rule.max_overrides_per_day, 
                       rule.max_override_duration_seconds, rule.max_cumulative_time_seconds)
    
    def remove_rule(self, domain: str) -> bool:
        """Remove a rule for a domain."""
        with self._lock:
            if domain in self._domain_rules:
                del self._domain_rules[domain]
                self._save_rules()
                return True
            return False
    
    def get_all_rules(self) -> List[DomainRuleConfig]:
        """Get all domain rules."""
        with self._lock:
            return list(self._domain_rules.values())
    
    def start_session(
        self,
        domain: str,
        tab_id: str,
        override_id: Optional[str] = None,
        is_active_window: bool = True,
    ) -> str:
        """Start a usage session for a domain.
        
        Returns:
            Session ID
        """
        import uuid
        
        with self._lock:
            self._reset_daily_if_needed()
            
            session_id = str(uuid.uuid4())[:8]
            session = DomainUsageSession(
                session_id=session_id,
                domain=domain,
                start_time=time.time(),
                override_id=override_id,
            )
            
            self._active_sessions[domain] = session
            self._tab_domains[tab_id] = domain
            
            if is_active_window:
                self._active_tabs.add(tab_id)
            
            # Update daily stats
            if domain not in self._daily_stats:
                self._daily_stats[domain] = DomainDailyStats(
                    domain=domain,
                    date=self._current_date,
                )
            self._daily_stats[domain].session_count += 1
            
            if override_id:
                self._daily_stats[domain].override_count += 1
            
            self._usage_dirty = True
            
            logger.debug("Started session %s for %s (tab=%s, active=%s)",
                        session_id, domain, tab_id, is_active_window)
            return session_id
    
    def has_active_session(self, domain: str) -> bool:
        """Check if a domain has an active usage session."""
        with self._lock:
            return domain in self._active_sessions
    
    def end_session(self, domain: str) -> Optional[DomainUsageSession]:
        """End a usage session for a domain."""
        with self._lock:
            if domain not in self._active_sessions:
                return None
            
            session = self._active_sessions.pop(domain)
            session.end_time = time.time()
            
            # Update daily stats
            if domain in self._daily_stats:
                stats = self._daily_stats[domain]
                stats.total_active_seconds += session.active_seconds
                stats.total_inactive_seconds += session.inactive_seconds
                stats.sessions.append(session.to_dict())
            
            # Clean up tab tracking
            tabs_to_remove = [t for t, d in self._tab_domains.items() if d == domain]
            for tab_id in tabs_to_remove:
                self._tab_domains.pop(tab_id, None)
                self._active_tabs.discard(tab_id)
            
            self._usage_dirty = True
            
            logger.debug("Ended session %s for %s (active=%0.1fs, inactive=%0.1fs)",
                        session.session_id, domain, session.active_seconds, session.inactive_seconds)
            return session
    
    def update_tab_active_state(self, tab_id: str, is_active: bool) -> None:
        """Update whether a tab is in an active window."""
        with self._lock:
            if is_active:
                self._active_tabs.add(tab_id)
            else:
                self._active_tabs.discard(tab_id)
    
    def tick(self, interval_seconds: float = 1.0) -> None:
        """Update active session times. Call this periodically."""
        with self._lock:
            for domain, session in self._active_sessions.items():
                # Find if any tab for this domain is active
                is_active = any(
                    self._tab_domains.get(tab_id) == domain
                    for tab_id in self._active_tabs
                )
                
                if is_active:
                    session.active_seconds += interval_seconds
                else:
                    session.inactive_seconds += interval_seconds
    
    def check_can_override(self, domain: str) -> Dict[str, Any]:
        """Check if an override can be granted for a domain.
        
        Returns dict with:
        - can_override: bool
        - reason: str (if denied)
        - remaining_overrides: int
        - remaining_time_seconds: float
        - effective_time_used: float
        """
        with self._lock:
            self._reset_daily_if_needed()
            
            rule = self.get_rule(domain)
            stats = self._daily_stats.get(domain, DomainDailyStats(domain=domain, date=self._current_date))
            
            # Calculate effective time based on rule settings
            # Include BOTH saved stats AND current active session time
            if rule.only_count_active_window:
                time_used = stats.total_active_seconds
            else:
                time_used = stats.total_seconds
            
            # Add current active session time (not yet saved to stats)
            if domain in self._active_sessions:
                session = self._active_sessions[domain]
                if rule.only_count_active_window:
                    time_used += session.active_seconds
                else:
                    time_used += session.active_seconds + session.inactive_seconds
            
            # Apply fragmentation penalty if enabled
            # Penalty is added for each override beyond the baseline
            if rule.use_fragmentation_penalty:
                extra_overrides = max(0, stats.override_count - rule.max_overrides_per_day)
                penalty = extra_overrides * rule.penalty_per_extra_override_seconds
                effective_time = time_used + penalty
            else:
                effective_time = time_used
            
            # Check cumulative time budget
            if effective_time >= rule.max_cumulative_time_seconds:
                return {
                    "can_override": False,
                    "reason": f"Daily time budget exhausted (used: {self._format_duration(effective_time)} of {self._format_duration(rule.max_cumulative_time_seconds)})",
                    "remaining_overrides": 0,
                    "remaining_time_seconds": 0,
                    "effective_time_used": effective_time,
                    "actual_time_used": time_used,
                    "penalty_seconds": effective_time - time_used,
                }
            
            remaining_time = rule.max_cumulative_time_seconds - effective_time
            
            return {
                "can_override": True,
                "reason": "",
                "remaining_overrides": rule.max_overrides_per_day - stats.override_count,
                "remaining_time_seconds": remaining_time,
                "effective_time_used": effective_time,
                "actual_time_used": time_used,
                "time_budget": rule.max_cumulative_time_seconds,
                "max_duration": min(rule.max_override_duration_seconds, remaining_time),
            }
    
    def check_can_override_with_classification(
        self,
        domain: str,
        category: str,
        usefulness: str,
    ) -> Dict[str, Any]:
        """Check if an override can be granted using classification-aware budgets.
        
        This method uses the content classification to determine the appropriate
        budget limits. Educational content gets more generous limits than
        distracting content.
        
        Args:
            domain: The domain being accessed
            category: Content category (EDUCATION, ENTERTAINMENT, GAMING, etc.)
            usefulness: Content usefulness (EDUCATIONAL, ENRICHMENT, NEUTRAL, DISTRACTION)
            
        Returns dict with:
        - can_override: bool
        - reason: str (if denied)
        - remaining_overrides: int
        - remaining_time_seconds: float
        - effective_time_used: float
        - budget: ClassificationBudget info
        - require_screenshot: bool
        - notify_parent: bool
        """
        with self._lock:
            self._reset_daily_if_needed()
            
            rule = self.get_rule(domain)
            stats = self._daily_stats.get(domain, DomainDailyStats(domain=domain, date=self._current_date))
            
            # Get classification-specific budget
            budget = rule.get_budget_for_classification(category, usefulness)
            
            # Calculate effective time based on rule settings
            if rule.only_count_active_window:
                time_used = stats.total_active_seconds
            else:
                time_used = stats.total_seconds
            
            # Add current active session time (not yet saved to stats)
            if domain in self._active_sessions:
                session = self._active_sessions[domain]
                if rule.only_count_active_window:
                    time_used += session.active_seconds
                else:
                    time_used += session.active_seconds + session.inactive_seconds
            
            # Apply fragmentation penalty using classification-specific settings
            if rule.use_fragmentation_penalty:
                extra_overrides = max(0, stats.override_count - budget.max_overrides_per_day)
                penalty = extra_overrides * budget.penalty_per_extra_override_seconds
                effective_time = time_used + penalty
            else:
                effective_time = time_used
            
            # Check cumulative time budget (using classification-specific limit)
            if effective_time >= budget.max_cumulative_time_seconds:
                return {
                    "can_override": False,
                    "reason": f"Daily {category.lower()} budget exhausted (used: {self._format_duration(effective_time)} of {self._format_duration(budget.max_cumulative_time_seconds)})",
                    "remaining_overrides": 0,
                    "remaining_time_seconds": 0,
                    "effective_time_used": effective_time,
                    "actual_time_used": time_used,
                    "penalty_seconds": effective_time - time_used,
                    "budget": budget.to_dict(),
                    "require_screenshot": budget.require_screenshot,
                    "notify_parent": budget.notify_parent,
                    "classification": {"category": category, "usefulness": usefulness},
                }
            
            remaining_time = budget.max_cumulative_time_seconds - effective_time
            
            return {
                "can_override": True,
                "reason": "",
                "remaining_overrides": max(0, budget.max_overrides_per_day - stats.override_count),
                "remaining_time_seconds": remaining_time,
                "effective_time_used": effective_time,
                "actual_time_used": time_used,
                "time_budget": budget.max_cumulative_time_seconds,
                "max_duration": min(budget.max_override_duration_seconds, remaining_time),
                "budget": budget.to_dict(),
                "require_screenshot": budget.require_screenshot,
                "notify_parent": budget.notify_parent,
                "classification": {"category": category, "usefulness": usefulness},
            }
    
    def get_budget_status_for_classification(
        self,
        domain: str,
        category: str,
        usefulness: str,
    ) -> Dict[str, Any]:
        """Get current budget status for a domain based on content classification.
        
        This is used by the blocked page to show users their current usage
        and remaining budget. Unlike check_can_override_with_classification(),
        this doesn't check if an override can be granted - it just returns
        the current status.
        
        Args:
            domain: The domain being accessed
            category: Content category (EDUCATION, ENTERTAINMENT, GAMING, etc.)
            usefulness: Content usefulness (EDUCATIONAL, ENRICHMENT, NEUTRAL, DISTRACTION)
            
        Returns dict with:
        - time_used_seconds: float - actual time used today
        - time_budget_seconds: int - total budget for this classification
        - remaining_seconds: float - remaining budget
        - time_used_formatted: str - human-readable time used
        - time_budget_formatted: str - human-readable budget
        - remaining_formatted: str - human-readable remaining
        - percentage_used: float - 0-100
        - override_count: int - number of overrides used today
        - max_overrides: int - max overrides allowed
        - classification: dict - category and usefulness
        """
        with self._lock:
            self._reset_daily_if_needed()
            
            rule = self.get_rule(domain)
            stats = self._daily_stats.get(domain, DomainDailyStats(domain=domain, date=self._current_date))
            
            # Get classification-specific budget
            budget = rule.get_budget_for_classification(category, usefulness)
            
            # Calculate effective time based on rule settings
            if rule.only_count_active_window:
                time_used = stats.total_active_seconds
            else:
                time_used = stats.total_seconds
            
            # Add current active session time (not yet saved to stats)
            if domain in self._active_sessions:
                session = self._active_sessions[domain]
                if rule.only_count_active_window:
                    time_used += session.active_seconds
                else:
                    time_used += session.active_seconds + session.inactive_seconds
            
            # Apply fragmentation penalty using classification-specific settings
            if rule.use_fragmentation_penalty:
                extra_overrides = max(0, stats.override_count - budget.max_overrides_per_day)
                penalty = extra_overrides * budget.penalty_per_extra_override_seconds
                effective_time = time_used + penalty
            else:
                effective_time = time_used
            
            remaining_time = max(0, budget.max_cumulative_time_seconds - effective_time)
            percentage_used = min(100, (effective_time / budget.max_cumulative_time_seconds * 100)) if budget.max_cumulative_time_seconds > 0 else 0
            
            return {
                "time_used_seconds": effective_time,
                "time_budget_seconds": budget.max_cumulative_time_seconds,
                "remaining_seconds": remaining_time,
                "time_used_formatted": self._format_duration(effective_time),
                "time_budget_formatted": self._format_duration(budget.max_cumulative_time_seconds),
                "remaining_formatted": self._format_duration(remaining_time),
                "percentage_used": round(percentage_used, 1),
                "override_count": stats.override_count,
                "max_overrides": budget.max_overrides_per_day,
                "remaining_overrides": max(0, budget.max_overrides_per_day - stats.override_count),
                "classification": {"category": category, "usefulness": usefulness},
                "budget_exhausted": effective_time >= budget.max_cumulative_time_seconds,
            }
    
    def get_daily_stats(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """Get daily statistics for one or all domains."""
        with self._lock:
            self._reset_daily_if_needed()
            
            if domain:
                stats = self._daily_stats.get(domain)
                if stats:
                    return stats.to_dict()
                return {"domain": domain, "date": self._current_date, "no_data": True}
            
            return {
                "date": self._current_date,
                "domains": {d: s.to_dict() for d, s in self._daily_stats.items()},
                "total_domains": len(self._daily_stats),
                "total_overrides": sum(s.override_count for s in self._daily_stats.values()),
                "total_active_seconds": sum(s.total_active_seconds for s in self._daily_stats.values()),
                "total_inactive_seconds": sum(s.total_inactive_seconds for s in self._daily_stats.values()),
            }
    
    def get_summary_for_email(self) -> Dict[str, Any]:
        """Get a summary suitable for the activity monitor email.
        
        Returns:
            Dict with domain usage summary for email report.
        """
        with self._lock:
            self._reset_daily_if_needed()
            
            # Sort domains by total active time
            sorted_domains = sorted(
                self._daily_stats.values(),
                key=lambda s: s.total_active_seconds,
                reverse=True,
            )
            
            summary = {
                "date": self._current_date,
                "total_domains_visited": len(self._daily_stats),
                "total_overrides_used": sum(s.override_count for s in self._daily_stats.values()),
                "total_active_time_seconds": sum(s.total_active_seconds for s in self._daily_stats.values()),
                "total_inactive_time_seconds": sum(s.total_inactive_seconds for s in self._daily_stats.values()),
                "domains": [],
            }
            
            for stats in sorted_domains:
                rule = self.get_rule(stats.domain)
                summary["domains"].append({
                    "domain": stats.domain,
                    "active_time_seconds": stats.total_active_seconds,
                    "active_time_formatted": self._format_duration(stats.total_active_seconds),
                    "inactive_time_seconds": stats.total_inactive_seconds,
                    "override_count": stats.override_count,
                    "session_count": stats.session_count,
                    "effective_time_used": stats.effective_time_used,
                    "limit_percentage": (stats.effective_time_used / rule.max_cumulative_time_seconds * 100)
                        if rule.max_cumulative_time_seconds > 0 else 0,
                })
            
            return summary
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format seconds as human-readable duration."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"


# Singleton instance
_tracker: Optional[DomainUsageTracker] = None
_tracker_lock = threading.Lock()


def get_domain_usage_tracker() -> DomainUsageTracker:
    """Get or create the singleton DomainUsageTracker instance."""
    global _tracker
    with _tracker_lock:
        if _tracker is None:
            _tracker = DomainUsageTracker()
        return _tracker


def reset_domain_usage_tracker() -> None:
    """Reset the singleton (for testing)."""
    global _tracker
    with _tracker_lock:
        _tracker = None


# =============================================================================
# Master Distraction Budget
# =============================================================================

@dataclass
class MasterDistractionBudgetConfig:
    """Configuration for the master distraction budget.
    
    This limits total time across ALL distraction sites combined,
    preventing users from gaming the system by visiting many different
    distraction sites for short periods.
    """
    max_total_distraction_seconds: int = 2700  # 45 minutes default
    warning_threshold_percent: float = 70.0  # Show warning at 70% used
    categories_to_track: Set[str] = field(default_factory=lambda: {
        "ENTERTAINMENT", "GAMING", "SOCIAL_MEDIA", "ADULT"
    })
    usefulness_to_track: Set[str] = field(default_factory=lambda: {
        "DISTRACTION", "NEUTRAL"  # Track neutral entertainment too
    })
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_total_distraction_seconds": self.max_total_distraction_seconds,
            "warning_threshold_percent": self.warning_threshold_percent,
            "categories_to_track": list(self.categories_to_track),
            "usefulness_to_track": list(self.usefulness_to_track),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MasterDistractionBudgetConfig':
        result = cls()
        if "max_total_distraction_seconds" in data:
            result.max_total_distraction_seconds = data["max_total_distraction_seconds"]
        if "warning_threshold_percent" in data:
            result.warning_threshold_percent = data["warning_threshold_percent"]
        if "categories_to_track" in data:
            result.categories_to_track = set(data["categories_to_track"])
        if "usefulness_to_track" in data:
            result.usefulness_to_track = set(data["usefulness_to_track"])
        return result


@dataclass
class DistractionSiteVisit:
    """Record of a visit to a distraction site."""
    domain: str
    category: str
    usefulness: str
    active_seconds: float
    override_count: int
    first_visit_time: float
    last_visit_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "category": self.category,
            "usefulness": self.usefulness,
            "active_seconds": self.active_seconds,
            "active_time_formatted": DomainUsageTracker._format_duration(self.active_seconds),
            "override_count": self.override_count,
            "first_visit_time": self.first_visit_time,
            "last_visit_time": self.last_visit_time,
        }


class MasterDistractionBudget:
    """Tracks cumulative time across all distraction sites.
    
    This prevents users from gaming per-domain limits by visiting
    many different distraction sites. Once the master budget is
    exhausted, ALL distraction sites are blocked for the day.
    """
    
    def __init__(
        self,
        config: Optional[MasterDistractionBudgetConfig] = None,
        data_file: Optional[Path] = None,
    ):
        self._lock = threading.RLock()
        self._config = config or MasterDistractionBudgetConfig()
        self._data_file = data_file or Path.home() / ".focus_guard" / "master_distraction_budget.json"
        
        # Daily tracking
        self._current_date: str = ""
        self._distraction_sites: Dict[str, DistractionSiteVisit] = {}  # domain -> visit
        self._total_distraction_seconds: float = 0.0
        self._blocks_today: int = 0
        
        # Auto-save tracking
        self._budget_dirty: bool = False
        self._autosave_interval: float = 60.0
        self._autosave_timer: Optional[threading.Timer] = None
        
        # Ensure directory exists
        self._data_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load today's data
        self._load_data()
        
        # Start periodic auto-save
        self._start_autosave()
        
        logger.info(
            "MasterDistractionBudget initialized: %d min limit, tracking %s (auto-save every %.0fs)",
            self._config.max_total_distraction_seconds // 60,
            self._config.categories_to_track,
            self._autosave_interval,
        )
    
    def _load_data(self) -> None:
        """Load today's distraction data."""
        try:
            today = date.today().isoformat()
            self._current_date = today
            
            if self._data_file.exists():
                with open(self._data_file, 'r') as f:
                    data = json.load(f)
                    
                    # Only load if it's today's data
                    if data.get("date") == today:
                        self._total_distraction_seconds = data.get("total_seconds", 0.0)
                        self._blocks_today = data.get("blocks_today", 0)
                        for site_data in data.get("sites", []):
                            visit = DistractionSiteVisit(
                                domain=site_data["domain"],
                                category=site_data.get("category", "UNKNOWN"),
                                usefulness=site_data.get("usefulness", "NEUTRAL"),
                                active_seconds=site_data.get("active_seconds", 0.0),
                                override_count=site_data.get("override_count", 0),
                                first_visit_time=site_data.get("first_visit_time", 0),
                                last_visit_time=site_data.get("last_visit_time", 0),
                            )
                            self._distraction_sites[visit.domain] = visit
                        logger.debug(
                            "Loaded master budget: %.1f min used across %d sites",
                            self._total_distraction_seconds / 60,
                            len(self._distraction_sites),
                        )
        except Exception as e:
            logger.warning("Could not load master distraction budget: %s", e)
    
    def _save_data(self) -> None:
        """Save today's distraction data."""
        try:
            data = {
                "date": self._current_date,
                "schema_version": 1,
                "total_seconds": self._total_distraction_seconds,
                "blocks_today": self._blocks_today,
                "sites": [v.to_dict() for v in self._distraction_sites.values()],
                "config": self._config.to_dict(),
                "last_updated": time.time(),
            }
            with open(self._data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save master distraction budget: %s", e)
    
    def _start_autosave(self) -> None:
        """Start the periodic auto-save timer."""
        self._autosave_timer = threading.Timer(self._autosave_interval, self._autosave_tick)
        self._autosave_timer.daemon = True
        self._autosave_timer.start()

    def _autosave_tick(self) -> None:
        """Periodic auto-save callback."""
        try:
            with self._lock:
                if self._budget_dirty:
                    self._save_data()
                    self._budget_dirty = False
                    logger.debug("Auto-saved master distraction budget")
        except Exception as e:
            logger.warning("Master budget auto-save failed: %s", e)
        finally:
            self._autosave_timer = threading.Timer(self._autosave_interval, self._autosave_tick)
            self._autosave_timer.daemon = True
            self._autosave_timer.start()

    def stop_autosave(self) -> None:
        """Stop the auto-save timer and flush any pending data."""
        if self._autosave_timer:
            self._autosave_timer.cancel()
            self._autosave_timer = None
        with self._lock:
            if self._budget_dirty:
                self._save_data()
                self._budget_dirty = False
                logger.info("Flushed master distraction budget on shutdown")

    def _reset_if_new_day(self) -> None:
        """Reset if it's a new day."""
        today = date.today().isoformat()
        if self._current_date != today:
            self._distraction_sites = {}
            self._total_distraction_seconds = 0.0
            self._blocks_today = 0
            self._current_date = today
            logger.info("Reset master distraction budget for new day: %s", today)
    
    def record_block(self, domain: str = "") -> int:
        """Record a blocking event. Returns the new blocks_today count."""
        with self._lock:
            self._reset_if_new_day()
            self._blocks_today += 1
            self._budget_dirty = True
            logger.debug("Recorded block #%d (domain=%s)", self._blocks_today, domain)
            return self._blocks_today

    def is_distraction_category(self, category: str, usefulness: str) -> bool:
        """Check if a category/usefulness combo should be tracked."""
        return (
            category.upper() in self._config.categories_to_track or
            usefulness.upper() in self._config.usefulness_to_track
        )
    
    def record_distraction_time(
        self,
        domain: str,
        seconds: float,
        category: str = "UNKNOWN",
        usefulness: str = "NEUTRAL",
    ) -> None:
        """Record time spent on a distraction site."""
        with self._lock:
            self._reset_if_new_day()
            
            now = time.time()
            
            if domain in self._distraction_sites:
                visit = self._distraction_sites[domain]
                visit.active_seconds += seconds
                visit.last_visit_time = now
            else:
                visit = DistractionSiteVisit(
                    domain=domain,
                    category=category.upper(),
                    usefulness=usefulness.upper(),
                    active_seconds=seconds,
                    override_count=1,
                    first_visit_time=now,
                    last_visit_time=now,
                )
                self._distraction_sites[domain] = visit
            
            self._total_distraction_seconds += seconds
            self._budget_dirty = True
    
    def record_override(
        self,
        domain: str,
        category: str = "UNKNOWN",
        usefulness: str = "NEUTRAL",
    ) -> None:
        """Record an override for a distraction site."""
        with self._lock:
            self._reset_if_new_day()
            
            now = time.time()
            
            if domain in self._distraction_sites:
                self._distraction_sites[domain].override_count += 1
                self._distraction_sites[domain].last_visit_time = now
            else:
                visit = DistractionSiteVisit(
                    domain=domain,
                    category=category.upper(),
                    usefulness=usefulness.upper(),
                    active_seconds=0.0,
                    override_count=1,
                    first_visit_time=now,
                    last_visit_time=now,
                )
                self._distraction_sites[domain] = visit
            
            self._budget_dirty = True
    
    def check_budget(self) -> Dict[str, Any]:
        """Check the master distraction budget status.
        
        Returns:
            Dict with budget status including:
            - budget_exhausted: bool
            - total_limit_seconds: int
            - total_used_seconds: float
            - remaining_seconds: float
            - usage_percent: float
            - warning: bool (if over warning threshold)
            - sites_visited: list of visited distraction sites
        """
        with self._lock:
            self._reset_if_new_day()
            
            limit = self._config.max_total_distraction_seconds
            used = self._total_distraction_seconds
            remaining = max(0, limit - used)
            percent = (used / limit * 100) if limit > 0 else 0
            
            # Sort sites by time spent (descending)
            sorted_sites = sorted(
                self._distraction_sites.values(),
                key=lambda v: v.active_seconds,
                reverse=True,
            )
            
            return {
                "budget_exhausted": used >= limit,
                "total_limit_seconds": limit,
                "total_limit_formatted": DomainUsageTracker._format_duration(limit),
                "total_used_seconds": used,
                "total_used_formatted": DomainUsageTracker._format_duration(used),
                "remaining_seconds": remaining,
                "remaining_formatted": DomainUsageTracker._format_duration(remaining),
                "usage_percent": round(percent, 1),
                "warning": percent >= self._config.warning_threshold_percent,
                "sites_visited": [s.to_dict() for s in sorted_sites],
                "sites_count": len(self._distraction_sites),
                "total_overrides": sum(s.override_count for s in self._distraction_sites.values()),
                "blocks_today": self._blocks_today,
                "date": self._current_date,
            }
    
    def can_access_distraction(self) -> Dict[str, Any]:
        """Check if user can access any more distraction sites today.
        
        Returns:
            Dict with:
            - allowed: bool
            - reason: str (if denied)
            - remaining_seconds: float
        """
        status = self.check_budget()
        
        if status["budget_exhausted"]:
            return {
                "allowed": False,
                "reason": f"Daily distraction limit exhausted ({status['total_limit_formatted']}). Try again tomorrow.",
                "remaining_seconds": 0,
                "status": status,
            }
        
        return {
            "allowed": True,
            "reason": "",
            "remaining_seconds": status["remaining_seconds"],
            "status": status,
        }
    
    def update_config(self, config: MasterDistractionBudgetConfig) -> None:
        """Update the budget configuration."""
        with self._lock:
            self._config = config
            self._save_data()
            logger.info("Updated master distraction budget config: %d min limit", 
                       config.max_total_distraction_seconds // 60)
    
    def get_config(self) -> MasterDistractionBudgetConfig:
        """Get the current configuration."""
        return self._config


# Singleton for master distraction budget
_master_budget: Optional[MasterDistractionBudget] = None
_master_budget_lock = threading.Lock()


def get_master_distraction_budget() -> MasterDistractionBudget:
    """Get or create the singleton MasterDistractionBudget instance."""
    global _master_budget
    with _master_budget_lock:
        if _master_budget is None:
            _master_budget = MasterDistractionBudget()
        return _master_budget


def reset_master_distraction_budget() -> None:
    """Reset the singleton (for testing)."""
    global _master_budget
    with _master_budget_lock:
        _master_budget = None
