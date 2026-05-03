"""Override management for temporary access to blocked sites.

This module tracks temporary overrides that allow users to access blocked sites
for a limited time. All overrides are logged for accountability.

Now supports classification-aware overrides: content is classified (via LLM or rules)
and different budgets are applied based on content type (educational vs distracting).
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class OverrideRequest:
    """A request to override a block."""
    domain: str
    url: str
    reason: str
    browser: str
    timestamp: float = field(default_factory=time.time)
    

@dataclass
class ActiveOverride:
    """An active temporary override allowing access to a blocked domain.
    
    Override expiry is now usage-based, not wall-clock based.
    The override expires when effective_time_used >= duration_seconds.
    Effective time = actual active time + fragmentation penalty.
    """
    id: str
    domain: str
    original_url: str
    start_time: float
    duration_seconds: int  # This is now the USAGE budget, not wall-clock
    browser: str
    block_reason: str
    request_reason: str = ""  # Why user requested override
    # Track usage within this override session
    usage_seconds: float = 0.0  # Actual active time used in this override
    
    def is_expired_with_usage(self, effective_time_used: float, time_budget: float) -> bool:
        """Check if override is expired based on effective time used.
        
        Args:
            effective_time_used: Total effective time used today (from DomainUsageTracker)
            time_budget: Total time budget for the day
        """
        return effective_time_used >= time_budget
    
    @property
    def is_expired(self) -> bool:
        """Wall-clock expiry check based on the granted duration.

        Keep the wall-clock boundary aligned with user-visible messaging
        (e.g. a 60-second override expires after ~60 seconds), while
        usage-based checks still run in check_override.
        """
        elapsed = time.time() - self.start_time
        return elapsed >= self.duration_seconds
    
    def remaining_seconds_with_usage(self, effective_time_used: float, time_budget: float) -> float:
        """Get remaining seconds based on effective time used."""
        return max(0, time_budget - effective_time_used)
    
    @property
    def remaining_seconds(self) -> float:
        """Legacy property - returns duration as placeholder."""
        # Actual remaining is calculated via check_override
        return self.duration_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "original_url": self.original_url,
            "start_time": self.start_time,
            "duration_seconds": self.duration_seconds,
            "usage_seconds": self.usage_seconds,
            "browser": self.browser,
            "block_reason": self.block_reason,
        }


@dataclass
class OverrideLogEntry:
    """Log entry for override activity."""
    timestamp: float
    event_type: str  # 'requested', 'granted', 'expired', 'revoked', 'accessed'
    domain: str
    override_id: Optional[str]
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "event_type": self.event_type,
            "domain": self.domain,
            "override_id": self.override_id,
            "details": self.details,
        }


class OverrideManager:
    """Manages temporary overrides for blocked sites.
    
    Features:
    - Time-limited access (configurable duration)
    - Server-side tracking (prevents client-side tampering)
    - Comprehensive logging for accountability
    - Domain-based tracking (not per-URL, so subpages don't reset timer)
    - Configurable rules per domain or globally
    """
    
    DEFAULT_DURATION = 300  # 5 minutes
    MAX_DURATION = 1800  # 30 minutes max
    MIN_DURATION = 60  # 1 minute min
    
    def __init__(
        self,
        log_file: Optional[Path] = None,
        default_duration: int = DEFAULT_DURATION,
        max_overrides_per_domain: int = 3,  # Max overrides per domain per day
    ):
        self._lock = threading.RLock()
        self._active_overrides: Dict[str, ActiveOverride] = {}  # domain -> override
        self._override_log: List[OverrideLogEntry] = []
        # Legacy per-domain daily counts (kept for compatibility with tests and UI).
        # The authoritative limits are enforced by DomainUsageTracker.
        self._daily_counts: Dict[str, int] = {}  # domain -> count today
        # Track which overrides have already had usage started today so we don't
        # double-count when a tab is closed and reopened within the same override.
        self._usage_started_overrides: set[str] = set()
        self._last_count_reset: float = time.time()
        
        self.default_duration = max(self.MIN_DURATION, min(default_duration, self.MAX_DURATION))
        self.max_overrides_per_domain = max_overrides_per_domain
        self.log_file = log_file or Path.home() / ".focus_guard" / "override_log.json"
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing log
        self._load_log()
        
        logger.info("OverrideManager initialized with %ds default duration", self.default_duration)
    
    def _load_log(self) -> None:
        """Load existing override log entries from file.

        Note: We intentionally do NOT hydrate _daily_counts from historical log
        data. Daily limits are enforced by DomainUsageTracker, and tests expect
        _daily_counts to start at 0 for a fresh manager instance.
        """
        try:
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                    self._override_log = [
                        OverrideLogEntry(
                            timestamp=e.get("timestamp", 0.0),
                            event_type=e.get("event_type", ""),
                            domain=e.get("domain", ""),
                            override_id=e.get("override_id"),
                            details=e.get("details") or {},
                        )
                        for e in data.get("log", [])
                    ]
                logger.debug("Loaded %d override log entries", len(self._override_log))
        except Exception as e:
            logger.warning("Could not load override log: %s", e)
    
    def _save_log_entry(self, entry: OverrideLogEntry) -> None:
        """Append a log entry to the file."""
        try:
            # Load existing
            data = {"log": []}
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
            
            # Append new entry
            data["log"].append(entry.to_dict())
            
            # Keep only last 30 days of logs
            cutoff = time.time() - (30 * 24 * 60 * 60)
            data["log"] = [e for e in data["log"] if e.get("timestamp", 0) > cutoff]
            
            # Save
            with open(self.log_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error("Failed to save override log: %s", e)
    
    def _log_event(
        self,
        event_type: str,
        domain: str,
        override_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an override event."""
        entry = OverrideLogEntry(
            timestamp=time.time(),
            event_type=event_type,
            domain=domain,
            override_id=override_id,
            details=details or {},
        )
        
        with self._lock:
            self._override_log.append(entry)
        
        self._save_log_entry(entry)
        logger.info("Override event: %s for %s (id=%s)", event_type, domain, override_id)
    
    def _reset_daily_counts_if_needed(self) -> None:
        """Reset daily counts at midnight."""
        now = time.time()
        today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
        
        if self._last_count_reset < today_start:
            self._daily_counts = {}
            self._last_count_reset = now
            logger.debug("Reset daily override counts")
    
    def request_override(
        self,
        domain: str,
        url: str,
        block_reason: str,
        browser: str = "unknown",
        duration: Optional[int] = None,
        request_reason: str = "",
        tab_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Request a temporary override for a blocked domain.
        
        Args:
            domain: The domain to allow temporarily
            url: The original URL that was blocked
            block_reason: Why the site was blocked
            browser: Which browser made the request
            duration: Override duration in seconds (uses default if not specified)
            request_reason: User's reason for requesting override
            tab_id: The tab ID requesting the override (for usage tracking)
            
        Returns:
            Dict with 'granted', 'override' (if granted), 'message', and 'remaining_today'
        """
        with self._lock:
            self._reset_daily_counts_if_needed()
            
            # Check if already has active override
            if domain in self._active_overrides:
                existing = self._active_overrides[domain]
                if not existing.is_expired:
                    self._log_event("accessed", domain, existing.id, {
                        "remaining_seconds": existing.remaining_seconds,
                        "url": url,
                    })
                    return {
                        "granted": True,
                        "override": existing.to_dict(),
                        "message": f"Existing override active. {int(existing.remaining_seconds)}s remaining.",
                        "remaining_today": self.max_overrides_per_domain - self._daily_counts.get(domain, 0),
                    }
                else:
                    # Clean up expired - end the usage session
                    del self._active_overrides[domain]
                    self._log_event("expired", domain, existing.id)
                    self._end_usage_session(domain)
            
            # Check with DomainUsageTracker for enhanced limits
            usage_check = self._check_usage_limits(domain)
            if not usage_check["can_override"]:
                self._log_event("denied", domain, None, {
                    "reason": usage_check["reason"],
                    "effective_time_used": usage_check.get("effective_time_used", 0),
                })
                return {
                    "granted": False,
                    "override": None,
                    "message": usage_check["reason"],
                    "remaining_today": usage_check.get("remaining_overrides", 0),
                    "effective_time_used": usage_check.get("effective_time_used", 0),
                }
            
            # Note: We no longer use the legacy _daily_counts here.
            # The DomainUsageTracker's check_can_override handles all limit checks.
            
            # Create new override with duration capped by usage tracker
            actual_duration = duration or self.default_duration
            max_allowed_duration = usage_check.get("max_duration", self.MAX_DURATION)
            actual_duration = max(self.MIN_DURATION, min(actual_duration, max_allowed_duration))
            
            override_id = str(uuid.uuid4())[:8]
            now = time.time()
            
            override = ActiveOverride(
                id=override_id,
                domain=domain,
                original_url=url,
                start_time=now,
                duration_seconds=actual_duration,
                browser=browser,
                block_reason=block_reason,
                request_reason=request_reason,
            )
            
            self._active_overrides[domain] = override
            # Don't increment daily_counts here - it will be incremented when session actually starts
            # Don't start usage session here - it starts when user navigates to the site
            
            self._log_event("granted", domain, override_id, {
                "duration_seconds": actual_duration,
                "url": url,
                "block_reason": block_reason,
                "request_reason": request_reason,
                "browser": browser,
                "effective_time_used": usage_check.get("effective_time_used", 0),
            })
            
            remaining = usage_check.get("remaining_overrides", self.max_overrides_per_domain)
            remaining_time = usage_check.get("remaining_time_seconds", actual_duration)
            # Cap session duration to max_duration from rule and remaining budget
            session_duration = min(actual_duration, remaining_time)
            
            return {
                "granted": True,
                "override": override.to_dict(),
                "message": f"Override granted for {int(session_duration / 60)} min. {remaining} overrides remaining today.",
                "remaining_today": remaining,
                "remaining_time_seconds": remaining_time,
                "session_duration_seconds": session_duration,
                "effective_time_used": usage_check.get("effective_time_used", 0),
            }
    
    def request_override_with_classification(
        self,
        domain: str,
        url: str,
        block_reason: str,
        browser: str = "unknown",
        duration: Optional[int] = None,
        request_reason: str = "",
        tab_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Request a temporary override with content classification.
        
        This method classifies the content (using LLM or rules) and applies
        classification-aware budgets. Educational content gets more generous
        limits than distracting content.
        
        Args:
            domain: The domain to allow temporarily
            url: The original URL that was blocked
            block_reason: Why the site was blocked
            browser: Which browser made the request
            duration: Override duration in seconds (uses default if not specified)
            request_reason: User's reason for requesting override
            tab_id: The tab ID requesting the override (for usage tracking)
            context: Additional context for classification (title, description, etc.)
            
        Returns:
            Dict with 'granted', 'override', 'classification', 'message', etc.
        """
        context = context or {}
        
        # Step 1: Classify the content
        classification = self._classify_content(domain, url, context)
        
        with self._lock:
            self._reset_daily_counts_if_needed()
            
            # Check if already has active override
            if domain in self._active_overrides:
                existing = self._active_overrides[domain]
                if not existing.is_expired:
                    self._log_event("accessed", domain, existing.id, {
                        "remaining_seconds": existing.remaining_seconds,
                        "url": url,
                        "classification": classification,
                    })
                    return {
                        "granted": True,
                        "override": existing.to_dict(),
                        "classification": classification,
                        "message": f"Existing override active. {int(existing.remaining_seconds)}s remaining.",
                        "remaining_today": self.max_overrides_per_domain - self._daily_counts.get(domain, 0),
                    }
                else:
                    # Clean up expired
                    del self._active_overrides[domain]
                    self._log_event("expired", domain, existing.id)
                    self._end_usage_session(domain)
            
            # Step 2: Check master distraction budget first (for distraction content)
            category = classification.get("category", "UNKNOWN")
            usefulness = classification.get("usefulness", "NEUTRAL")
            master_budget_status = self._check_master_distraction_budget(category, usefulness)
            
            if not master_budget_status["allowed"]:
                self._log_event("denied", domain, None, {
                    "reason": master_budget_status["reason"],
                    "classification": classification,
                    "master_budget_exhausted": True,
                })
                self._log_to_audit(
                    domain=domain,
                    url=url,
                    classification=classification,
                    granted=False,
                    denial_reason=master_budget_status["reason"],
                    request_reason=request_reason,
                    browser=browser,
                    tab_id=tab_id,
                )
                return {
                    "granted": False,
                    "override": None,
                    "classification": classification,
                    "message": master_budget_status["reason"],
                    "remaining_today": 0,
                    "master_budget_exhausted": True,
                    "master_budget": master_budget_status.get("status", {}),
                }
            
            # Step 3: Check per-domain limits using classification-aware budgets
            usage_check = self._check_usage_limits_with_classification(
                domain,
                category,
                usefulness,
            )
            
            if not usage_check["can_override"]:
                self._log_event("denied", domain, None, {
                    "reason": usage_check["reason"],
                    "classification": classification,
                    "effective_time_used": usage_check.get("effective_time_used", 0),
                })
                # Log denial to audit logger
                self._log_to_audit(
                    domain=domain,
                    url=url,
                    classification=classification,
                    granted=False,
                    denial_reason=usage_check["reason"],
                    request_reason=request_reason,
                    browser=browser,
                    tab_id=tab_id,
                )
                return {
                    "granted": False,
                    "override": None,
                    "classification": classification,
                    "message": usage_check["reason"],
                    "remaining_today": usage_check.get("remaining_overrides", 0),
                    "effective_time_used": usage_check.get("effective_time_used", 0),
                    "require_screenshot": usage_check.get("require_screenshot", False),
                    "notify_parent": usage_check.get("notify_parent", False),
                }
            
            # Step 3: Take screenshot if required for distracting content
            screenshot_record = None
            if usage_check.get("require_screenshot", False):
                screenshot_record = self._capture_screenshot(
                    domain=domain,
                    url=url,
                    classification=classification,
                    override_id=None,  # Will update after creating override
                )
            
            # Step 4: Create override with classification-aware duration
            actual_duration = duration or self.default_duration
            max_allowed_duration = usage_check.get("max_duration", self.MAX_DURATION)
            actual_duration = max(self.MIN_DURATION, min(actual_duration, max_allowed_duration))
            
            override_id = str(uuid.uuid4())[:8]
            now = time.time()
            
            override = ActiveOverride(
                id=override_id,
                domain=domain,
                original_url=url,
                start_time=now,
                duration_seconds=actual_duration,
                browser=browser,
                block_reason=block_reason,
                request_reason=request_reason,
            )
            
            self._active_overrides[domain] = override
            
            # Log with classification info
            log_details = {
                "duration_seconds": actual_duration,
                "url": url,
                "block_reason": block_reason,
                "request_reason": request_reason,
                "browser": browser,
                "classification": classification,
                "effective_time_used": usage_check.get("effective_time_used", 0),
                "budget": usage_check.get("budget", {}),
            }
            if screenshot_record:
                log_details["screenshot_id"] = screenshot_record.get("id")
            
            self._log_event("granted", domain, override_id, log_details)
            
            remaining = usage_check.get("remaining_overrides", self.max_overrides_per_domain)
            remaining_time = usage_check.get("remaining_time_seconds", actual_duration)
            
            # Step 5: Log to audit logger for accountability
            self._log_to_audit(
                domain=domain,
                url=url,
                classification=classification,
                granted=True,
                override_id=override_id,
                duration_seconds=actual_duration,
                remaining_budget_seconds=remaining_time,
                screenshot_id=screenshot_record.get("id") if screenshot_record else None,
                parent_notified=usage_check.get("notify_parent", False),
                request_reason=request_reason,
                browser=browser,
                tab_id=tab_id,
            )
            
            # Step 6: Notify parent if required
            if usage_check.get("notify_parent", False):
                self._notify_parent(domain, url, classification, override_id, screenshot_record)
            
            session_duration = min(actual_duration, remaining_time)
            
            # Build message based on classification
            category = classification.get("category", "UNKNOWN")
            usefulness = classification.get("usefulness", "NEUTRAL")
            if usefulness == "EDUCATIONAL":
                msg_prefix = "Educational content detected. "
            elif usefulness == "DISTRACTION":
                msg_prefix = "Distracting content detected. "
            else:
                msg_prefix = ""
            
            return {
                "granted": True,
                "override": override.to_dict(),
                "classification": classification,
                "message": f"{msg_prefix}Override granted for {int(session_duration / 60)} min. {remaining} overrides remaining.",
                "remaining_today": remaining,
                "remaining_time_seconds": remaining_time,
                "session_duration_seconds": session_duration,
                "effective_time_used": usage_check.get("effective_time_used", 0),
                "budget": usage_check.get("budget", {}),
                "require_screenshot": usage_check.get("require_screenshot", False),
                "notify_parent": usage_check.get("notify_parent", False),
                "screenshot_taken": screenshot_record is not None,
            }
    
    def _classify_content(self, domain: str, url: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Classify content using the classification service."""
        try:
            from .classification_service import get_classification_service
            service = get_classification_service()
            result = service.classify(domain, url, context)
            return result.to_dict()
        except Exception as e:
            logger.warning("Classification failed, using fallback: %s", e)
            return {
                "domain": domain,
                "url": url,
                "category": "UNKNOWN",
                "usefulness": "neutral",
                "confidence": 0.0,
                "classifier_used": "fallback",
                "is_distracting": False,
            }
    
    def _check_usage_limits_with_classification(
        self, 
        domain: str, 
        category: str, 
        usefulness: str
    ) -> Dict[str, Any]:
        """Check usage limits using classification-aware budgets."""
        try:
            from .domain_usage_tracker import get_domain_usage_tracker
            tracker = get_domain_usage_tracker()
            return tracker.check_can_override_with_classification(domain, category, usefulness.upper())
        except ImportError:
            return {"can_override": True, "remaining_overrides": self.max_overrides_per_domain}
        except Exception as e:
            logger.warning("Error checking classification-aware limits: %s", e)
            return {"can_override": True, "remaining_overrides": self.max_overrides_per_domain}
    
    def _capture_screenshot(
        self,
        domain: str,
        url: str,
        classification: Dict[str, Any],
        override_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Capture screenshot for accountability."""
        try:
            from .screenshot_service import get_screenshot_service
            service = get_screenshot_service()
            record = service.capture(
                domain=domain,
                url=url,
                classification_category=classification.get("category", "UNKNOWN"),
                classification_usefulness=classification.get("usefulness", "NEUTRAL"),
                override_id=override_id,
                save_to_file=True,
                include_base64=True,  # For email attachment
                metadata={"classification": classification},
            )
            if record:
                return record.to_dict()
        except Exception as e:
            logger.warning("Screenshot capture failed: %s", e)
        return None
    
    def _log_to_audit(
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
    ) -> None:
        """Log override event to the audit logger for accountability."""
        try:
            from .audit_logger import get_audit_logger
            audit = get_audit_logger()
            audit.log_override_request(
                domain=domain,
                url=url,
                classification=classification,
                granted=granted,
                override_id=override_id,
                duration_seconds=duration_seconds,
                remaining_budget_seconds=remaining_budget_seconds,
                screenshot_id=screenshot_id,
                parent_notified=parent_notified,
                request_reason=request_reason,
                denial_reason=denial_reason,
                browser=browser,
                tab_id=tab_id,
            )
        except Exception as e:
            logger.warning("Failed to log to audit: %s", e)
    
    def _notify_parent(
        self,
        domain: str,
        url: str,
        classification: Dict[str, Any],
        override_id: str,
        screenshot_record: Optional[Dict[str, Any]],
    ) -> None:
        """Send notification to parent/accountability buddy about distracting content."""
        try:
            # Log to audit that parent was notified
            from .audit_logger import get_audit_logger
            audit = get_audit_logger()
            audit.log_parent_notification(
                domain=domain,
                url=url,
                classification=classification,
                override_id=override_id,
                screenshot_id=screenshot_record.get("id") if screenshot_record else None,
            )
            
            logger.info(
                "Parent notification queued: domain=%s, category=%s, usefulness=%s, override=%s",
                domain, classification.get("category"), classification.get("usefulness"), override_id
            )
            # TODO: Integrate with email_integration.py to send actual notification
            # For now, just log it - the email will be sent in the daily summary
        except Exception as e:
            logger.warning("Failed to queue parent notification: %s", e)
    
    def _check_usage_limits(self, domain: str) -> Dict[str, Any]:
        """Check usage limits via DomainUsageTracker."""
        try:
            from .domain_usage_tracker import get_domain_usage_tracker
            tracker = get_domain_usage_tracker()
            return tracker.check_can_override(domain)
        except ImportError:
            # Fallback if tracker not available
            return {"can_override": True, "remaining_overrides": self.max_overrides_per_domain}
        except Exception as e:
            logger.warning("Error checking usage limits: %s", e)
            return {"can_override": True, "remaining_overrides": self.max_overrides_per_domain}
    
    def _check_master_distraction_budget(self, category: str, usefulness: str) -> Dict[str, Any]:
        """Check master distraction budget for distraction content.
        
        This enforces a global limit across ALL distraction sites combined.
        
        Args:
            category: Content category (ENTERTAINMENT, GAMING, etc.)
            usefulness: Content usefulness (DISTRACTION, NEUTRAL, etc.)
            
        Returns:
            Dict with 'allowed', 'reason', 'remaining_seconds', 'status'
        """
        try:
            from .domain_usage_tracker import get_master_distraction_budget
            budget = get_master_distraction_budget()
            
            # Check if this is distraction content
            if not budget.is_distraction_category(category, usefulness):
                # Not distraction content, allow without checking master budget
                return {"allowed": True, "reason": "", "remaining_seconds": float('inf')}
            
            # Check master budget
            return budget.can_access_distraction()
            
        except ImportError:
            logger.warning("MasterDistractionBudget not available")
            return {"allowed": True, "reason": "", "remaining_seconds": float('inf')}
        except Exception as e:
            logger.warning("Error checking master distraction budget: %s", e)
            return {"allowed": True, "reason": "", "remaining_seconds": float('inf')}
    
    def _start_usage_session(self, domain: str, tab_id: str, override_id: str) -> None:
        """Start a usage tracking session."""
        try:
            from .domain_usage_tracker import get_domain_usage_tracker
            tracker = get_domain_usage_tracker()
            tracker.start_session(domain, tab_id, override_id)
        except Exception as e:
            logger.warning("Error starting usage session: %s", e)
    
    def start_override_usage(self, domain: str, tab_id: str) -> Dict[str, Any]:
        """Start using an override - called when user actually navigates to the site.
        
        This increments the override count and starts the usage tracking session.
        Should be called when the user navigates to an overridden domain.
        """
        with self._lock:
            if domain not in self._active_overrides:
                return {"started": False, "reason": "No active override for domain"}
            
            override = self._active_overrides[domain]

            # Check if a usage session is already active for this domain.
            # If so, don't start a new one or increment counts again.
            try:
                from .domain_usage_tracker import get_domain_usage_tracker
                tracker = get_domain_usage_tracker()
                if tracker.has_active_session(domain):
                    # Get current count from tracker
                    stats = tracker.get_daily_stats(domain)
                    return {"started": True, "reason": "Session already active", "daily_count": stats.get("override_count", 0)}
            except Exception:
                pass

            # Decide whether this is the first usage for this override today.
            first_usage_for_override = override.id not in self._usage_started_overrides

            # For the first usage of a given override, start a session with override_id
            # so DomainUsageTracker increments override_count. For subsequent sessions
            # (e.g., tab closed and reopened within the same override window), start
            # a session without override_id so we track time but do not increment
            # override_count again.
            override_id_for_tracker = override.id if first_usage_for_override else None
            self._start_usage_session(domain, tab_id, override_id_for_tracker)

            # Update legacy daily_counts for compatibility with existing tests/UI.
            if first_usage_for_override:
                self._usage_started_overrides.add(override.id)
                self._daily_counts[domain] = self._daily_counts.get(domain, 0) + 1

            # Get the actual count from the tracker (authoritative for budgets)
            try:
                from .domain_usage_tracker import get_domain_usage_tracker
                tracker = get_domain_usage_tracker()
                stats = tracker.get_daily_stats(domain)
                daily_count = stats.get("override_count", 1)
            except Exception:
                daily_count = 1
            
            self._log_event("usage_started", domain, override.id, {
                "tab_id": tab_id,
                "daily_count": daily_count,
            })
            
            return {"started": True, "override_id": override.id, "daily_count": daily_count}
    
    def _end_usage_session(self, domain: str) -> None:
        """End a usage tracking session."""
        try:
            from .domain_usage_tracker import get_domain_usage_tracker
            tracker = get_domain_usage_tracker()
            tracker.end_session(domain)
        except Exception as e:
            logger.warning("Error ending usage session: %s", e)
    
    def check_override(self, domain: str) -> Dict[str, Any]:
        """Check if a domain has an active override.
        
        Override expiry is now usage-based: expires when effective_time >= budget.
        
        Returns:
            Dict with 'has_override', 'override' (if active), 'remaining_seconds',
            'effective_time_used', 'actual_time_used'
        """
        with self._lock:
            if domain not in self._active_overrides:
                return {
                    "has_override": False,
                    "override": None,
                    "remaining_seconds": 0,
                }
            
            override = self._active_overrides[domain]
            
            # Wall-clock hard cap: expire if elapsed > 2x duration
            if override.is_expired:
                del self._active_overrides[domain]
                self._log_event("expired", domain, override.id, {
                    "reason": "wall_clock_expired",
                    "elapsed": time.time() - override.start_time,
                    "duration": override.duration_seconds,
                })
                self._end_usage_session(domain)
                return {
                    "has_override": False,
                    "override": None,
                    "remaining_seconds": 0,
                    "expired_reason": "Override time expired",
                }
            
            # Check usage-based expiry via DomainUsageTracker
            usage_check = self._check_usage_limits(domain)
            effective_time = usage_check.get("effective_time_used", 0)
            time_budget = usage_check.get("time_budget", override.duration_seconds)
            remaining = usage_check.get("remaining_time_seconds", 0)
            
            # Check if budget exhausted
            if not usage_check.get("can_override", True) or effective_time >= time_budget:
                del self._active_overrides[domain]
                self._log_event("expired", domain, override.id, {
                    "reason": "usage_budget_exhausted",
                    "effective_time_used": effective_time,
                    "time_budget": time_budget,
                })
                self._end_usage_session(domain)
                return {
                    "has_override": False,
                    "override": None,
                    "remaining_seconds": 0,
                    "effective_time_used": effective_time,
                    "expired_reason": "Time budget exhausted",
                }
            
            return {
                "has_override": True,
                "override": override.to_dict(),
                "remaining_seconds": remaining,
                "effective_time_used": effective_time,
                "actual_time_used": usage_check.get("actual_time_used", 0),
            }
    
    def revoke_override(self, domain: str) -> bool:
        """Revoke an active override."""
        with self._lock:
            if domain in self._active_overrides:
                override = self._active_overrides[domain]
                del self._active_overrides[domain]
                self._log_event("revoked", domain, override.id)
                self._end_usage_session(domain)
                return True
            return False
    
    def get_active_overrides(self) -> List[Dict[str, Any]]:
        """Get all active (non-expired) overrides."""
        with self._lock:
            # Clean up expired
            expired = [d for d, o in self._active_overrides.items() if o.is_expired]
            for domain in expired:
                override = self._active_overrides.pop(domain)
                self._log_event("expired", domain, override.id)
            
            return [o.to_dict() for o in self._active_overrides.values()]
    
    def get_log(
        self,
        limit: int = 100,
        domain: Optional[str] = None,
        since_ts: Optional[float] = None,
        until_ts: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent override log entries, optionally filtered by timestamp range."""
        with self._lock:
            entries = self._override_log
            if domain:
                entries = [e for e in entries if e.domain == domain]
            if since_ts is not None:
                entries = [e for e in entries if e.timestamp >= since_ts]
            if until_ts is not None:
                entries = [e for e in entries if e.timestamp <= until_ts]
            return [e.to_dict() for e in entries[-limit:]]
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """Get daily override statistics."""
        with self._lock:
            self._reset_daily_counts_if_needed()
            return {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "overrides_by_domain": dict(self._daily_counts),
                "total_overrides": sum(self._daily_counts.values()),
                "max_per_domain": self.max_overrides_per_domain,
            }


# Singleton instance
_override_manager: Optional[OverrideManager] = None
_manager_lock = threading.Lock()


def get_override_manager() -> OverrideManager:
    """Get or create the singleton OverrideManager instance."""
    global _override_manager
    with _manager_lock:
        if _override_manager is None:
            _override_manager = OverrideManager()
        return _override_manager


def reset_override_manager() -> None:
    """Reset the singleton (for testing)."""
    global _override_manager
    with _manager_lock:
        _override_manager = None
