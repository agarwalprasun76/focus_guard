"""Audit logger for accountability tracking.

This module provides structured logging for override events with classification
details, screenshots, and parent notification tracking. Designed for accountability
and generating reports.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    OVERRIDE_REQUESTED = "override_requested"
    OVERRIDE_GRANTED = "override_granted"
    OVERRIDE_DENIED = "override_denied"
    OVERRIDE_EXPIRED = "override_expired"
    OVERRIDE_REVOKED = "override_revoked"
    SCREENSHOT_CAPTURED = "screenshot_captured"
    PARENT_NOTIFIED = "parent_notified"
    BUDGET_EXHAUSTED = "budget_exhausted"
    CLASSIFICATION_CHANGED = "classification_changed"


@dataclass
class AuditEvent:
    """A single audit event for accountability tracking."""
    id: str
    timestamp: float
    event_type: str  # AuditEventType value
    domain: str
    url: str
    
    # Classification info
    category: str = "UNKNOWN"
    usefulness: str = "NEUTRAL"
    confidence: float = 0.0
    classifier_used: str = "unknown"
    
    # Override info
    override_id: Optional[str] = None
    duration_seconds: Optional[int] = None
    remaining_budget_seconds: Optional[float] = None
    
    # Accountability
    screenshot_id: Optional[str] = None
    parent_notified: bool = False
    request_reason: str = ""
    denial_reason: str = ""
    
    # Context
    browser: str = "unknown"
    tab_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "event_type": self.event_type,
            "domain": self.domain,
            "url": self.url,
            "category": self.category,
            "usefulness": self.usefulness,
            "confidence": self.confidence,
            "classifier_used": self.classifier_used,
            "override_id": self.override_id,
            "duration_seconds": self.duration_seconds,
            "remaining_budget_seconds": self.remaining_budget_seconds,
            "screenshot_id": self.screenshot_id,
            "parent_notified": self.parent_notified,
            "request_reason": self.request_reason,
            "denial_reason": self.denial_reason,
            "browser": self.browser,
            "tab_id": self.tab_id,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditEvent':
        # Remove datetime field if present (it's computed)
        data = {k: v for k, v in data.items() if k != "datetime"}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class AuditLogger:
    """Structured audit logger for accountability tracking.
    
    Features:
    - Logs all override events with classification details
    - Tracks screenshots and parent notifications
    - Provides daily summaries for email reports
    - Persists to JSON for durability
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize the audit logger.
        
        Args:
            storage_dir: Directory to store audit logs
        """
        self._lock = threading.Lock()
        self._storage_dir = storage_dir or Path.home() / ".focus_guard" / "audit"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory buffer for current day
        self._current_date: str = ""
        self._events: List[AuditEvent] = []
        self._event_count: int = 0
        
        # Load today's events
        self._load_today()
        
        logger.info("AuditLogger initialized, storage: %s", self._storage_dir)
    
    def _get_log_file(self, date_str: str) -> Path:
        """Get the log file path for a given date."""
        return self._storage_dir / f"audit_{date_str}.json"
    
    def _load_today(self) -> None:
        """Load today's events from disk."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._current_date != today:
            self._save_current()  # Save previous day if any
            self._current_date = today
            self._events = []
            
            log_file = self._get_log_file(today)
            if log_file.exists():
                try:
                    with open(log_file, "r") as f:
                        data = json.load(f)
                        self._events = [AuditEvent.from_dict(e) for e in data.get("events", [])]
                        self._event_count = len(self._events)
                except Exception as e:
                    logger.warning("Failed to load audit log: %s", e)
    
    def _save_current(self) -> None:
        """Save current day's events to disk."""
        if not self._current_date or not self._events:
            return
        
        log_file = self._get_log_file(self._current_date)
        try:
            data = {
                "date": self._current_date,
                "event_count": len(self._events),
                "events": [e.to_dict() for e in self._events],
            }
            with open(log_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save audit log: %s", e)
    
    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        import uuid
        return str(uuid.uuid4())[:12]
    
    def log_override_request(
        self,
        domain: str,
        url: str,
        classification: Dict[str, Any],
        granted: bool,
        override_id: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        remaining_budget_seconds: Optional[float] = None,
        screenshot_id: Optional[str] = None,
        parent_notified: bool = False,
        request_reason: str = "",
        denial_reason: str = "",
        browser: str = "unknown",
        tab_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log an override request event.
        
        Args:
            domain: Domain being accessed
            url: Full URL
            classification: Classification result dict
            granted: Whether override was granted
            override_id: ID of the override (if granted)
            duration_seconds: Override duration (if granted)
            remaining_budget_seconds: Remaining budget after this override
            screenshot_id: ID of captured screenshot (if any)
            parent_notified: Whether parent was notified
            request_reason: User's reason for requesting
            denial_reason: Reason for denial (if denied)
            browser: Browser making the request
            tab_id: Tab ID
            metadata: Additional metadata
            
        Returns:
            The created AuditEvent
        """
        with self._lock:
            self._load_today()
            
            event_type = (
                AuditEventType.OVERRIDE_GRANTED.value if granted 
                else AuditEventType.OVERRIDE_DENIED.value
            )
            
            event = AuditEvent(
                id=self._generate_event_id(),
                timestamp=time.time(),
                event_type=event_type,
                domain=domain,
                url=url,
                category=classification.get("category", "UNKNOWN"),
                usefulness=classification.get("usefulness", "NEUTRAL"),
                confidence=classification.get("confidence", 0.0),
                classifier_used=classification.get("classifier_used", "unknown"),
                override_id=override_id,
                duration_seconds=duration_seconds,
                remaining_budget_seconds=remaining_budget_seconds,
                screenshot_id=screenshot_id,
                parent_notified=parent_notified,
                request_reason=request_reason,
                denial_reason=denial_reason,
                browser=browser,
                tab_id=tab_id,
                metadata=metadata or {},
            )
            
            self._events.append(event)
            self._event_count += 1
            self._save_current()
            
            logger.debug(
                "Audit: %s for %s (category=%s, usefulness=%s)",
                event_type, domain, event.category, event.usefulness
            )
            
            return event
    
    def log_screenshot(
        self,
        domain: str,
        url: str,
        screenshot_id: str,
        classification: Dict[str, Any],
        override_id: Optional[str] = None,
    ) -> AuditEvent:
        """Log a screenshot capture event."""
        with self._lock:
            self._load_today()
            
            event = AuditEvent(
                id=self._generate_event_id(),
                timestamp=time.time(),
                event_type=AuditEventType.SCREENSHOT_CAPTURED.value,
                domain=domain,
                url=url,
                category=classification.get("category", "UNKNOWN"),
                usefulness=classification.get("usefulness", "NEUTRAL"),
                screenshot_id=screenshot_id,
                override_id=override_id,
            )
            
            self._events.append(event)
            self._save_current()
            
            return event
    
    def log_parent_notification(
        self,
        domain: str,
        url: str,
        classification: Dict[str, Any],
        override_id: str,
        screenshot_id: Optional[str] = None,
    ) -> AuditEvent:
        """Log a parent notification event."""
        with self._lock:
            self._load_today()
            
            event = AuditEvent(
                id=self._generate_event_id(),
                timestamp=time.time(),
                event_type=AuditEventType.PARENT_NOTIFIED.value,
                domain=domain,
                url=url,
                category=classification.get("category", "UNKNOWN"),
                usefulness=classification.get("usefulness", "NEUTRAL"),
                override_id=override_id,
                screenshot_id=screenshot_id,
                parent_notified=True,
            )
            
            self._events.append(event)
            self._save_current()
            
            return event
    
    def get_daily_summary(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Get a summary of audit events for a given day.
        
        Args:
            date_str: Date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            Summary dict with counts by category, usefulness, etc.
        """
        with self._lock:
            if date_str is None or date_str == self._current_date:
                self._load_today()
                events = self._events
            else:
                # Load from file
                log_file = self._get_log_file(date_str)
                if not log_file.exists():
                    return {"date": date_str, "no_data": True}
                try:
                    with open(log_file, "r") as f:
                        data = json.load(f)
                        events = [AuditEvent.from_dict(e) for e in data.get("events", [])]
                except Exception:
                    return {"date": date_str, "error": "Failed to load"}
            
            # Build summary
            summary = {
                "date": date_str or self._current_date,
                "total_events": len(events),
                "overrides_granted": 0,
                "overrides_denied": 0,
                "screenshots_captured": 0,
                "parent_notifications": 0,
                "by_category": {},
                "by_usefulness": {},
                "by_domain": {},
                "distracting_content_accessed": [],
            }
            
            for event in events:
                if event.event_type == AuditEventType.OVERRIDE_GRANTED.value:
                    summary["overrides_granted"] += 1
                elif event.event_type == AuditEventType.OVERRIDE_DENIED.value:
                    summary["overrides_denied"] += 1
                elif event.event_type == AuditEventType.SCREENSHOT_CAPTURED.value:
                    summary["screenshots_captured"] += 1
                elif event.event_type == AuditEventType.PARENT_NOTIFIED.value:
                    summary["parent_notifications"] += 1
                
                # Count by category
                cat = event.category
                summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1
                
                # Count by usefulness
                use = event.usefulness
                summary["by_usefulness"][use] = summary["by_usefulness"].get(use, 0) + 1
                
                # Count by domain
                dom = event.domain
                summary["by_domain"][dom] = summary["by_domain"].get(dom, 0) + 1
                
                # Track distracting content
                if event.usefulness.upper() == "DISTRACTION" and event.event_type == AuditEventType.OVERRIDE_GRANTED.value:
                    summary["distracting_content_accessed"].append({
                        "domain": event.domain,
                        "url": event.url,
                        "category": event.category,
                        "timestamp": event.timestamp,
                        "screenshot_id": event.screenshot_id,
                    })
            
            return summary
    
    def get_events(
        self,
        date_str: Optional[str] = None,
        event_type: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit events with optional filtering.
        
        Args:
            date_str: Date to query (defaults to today)
            event_type: Filter by event type
            domain: Filter by domain
            limit: Maximum events to return
            
        Returns:
            List of event dicts
        """
        with self._lock:
            if date_str is None or date_str == self._current_date:
                self._load_today()
                events = self._events
            else:
                log_file = self._get_log_file(date_str)
                if not log_file.exists():
                    return []
                try:
                    with open(log_file, "r") as f:
                        data = json.load(f)
                        events = [AuditEvent.from_dict(e) for e in data.get("events", [])]
                except Exception:
                    return []
            
            # Apply filters
            filtered = events
            if event_type:
                filtered = [e for e in filtered if e.event_type == event_type]
            if domain:
                filtered = [e for e in filtered if e.domain == domain]
            
            # Return most recent first, limited
            return [e.to_dict() for e in reversed(filtered[-limit:])]


# Singleton instance
_audit_logger: Optional[AuditLogger] = None
_logger_lock = threading.Lock()


def get_audit_logger() -> AuditLogger:
    """Get or create the singleton AuditLogger instance."""
    global _audit_logger
    with _logger_lock:
        if _audit_logger is None:
            _audit_logger = AuditLogger()
        return _audit_logger


def reset_audit_logger() -> None:
    """Reset the singleton (for testing)."""
    global _audit_logger
    with _logger_lock:
        _audit_logger = None
