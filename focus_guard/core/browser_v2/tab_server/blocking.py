"""Blocking decision logic for browser_v2 tab server."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class BlockingRule:
    """A rule for blocking domains or URLs."""

    domain: str
    reason: str = "blocked"
    category: Optional[str] = None
    enabled: bool = True
    created_at: float = field(default_factory=time.time)


@dataclass
class BlockingDecision:
    """Result of a blocking check."""

    should_block: bool
    reason: Optional[str] = None
    rule: Optional[BlockingRule] = None
    cached: bool = False
    
    # Classification info (for blocked page display)
    classification: Optional[Dict[str, Any]] = None  # category, usefulness, confidence
    
    # Budget info (for blocked page display)
    budget_status: Optional[Dict[str, Any]] = None  # time_used, time_budget, remaining
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result = {
            "should_block": self.should_block,
            "reason": self.reason,
            "cached": self.cached,
        }
        if self.rule:
            result["rule"] = {
                "domain": self.rule.domain,
                "reason": self.rule.reason,
                "category": self.rule.category,
            }
        if self.classification:
            result["classification"] = self.classification
        if self.budget_status:
            result["budget_status"] = self.budget_status
        return result


class BlockingManager:
    """Manages blocking rules and decisions for browser tabs.

    Provides thread-safe rule management and fast domain lookups with caching.
    """

    def __init__(
        self,
        cache_ttl_seconds: float = 30.0,
        external_checker: Optional[Callable[[str, str], BlockingDecision]] = None,
    ) -> None:
        """Initialize the blocking manager.

        Args:
            cache_ttl_seconds: How long to cache blocking decisions.
            external_checker: Optional callback to delegate blocking decisions
                to an external system (e.g., Focus Guard's domain classifier).
        """
        self._lock = threading.RLock()
        self._rules: Dict[str, BlockingRule] = {}
        self._cache: Dict[str, tuple[BlockingDecision, float]] = {}
        self._cache_ttl = cache_ttl_seconds
        self._external_checker = external_checker

    def add_rule(self, rule: BlockingRule) -> None:
        """Add or update a blocking rule."""
        with self._lock:
            self._rules[rule.domain.lower()] = rule
            # Invalidate cache for this domain
            self._invalidate_cache_for_domain(rule.domain)

    def remove_rule(self, domain: str) -> bool:
        """Remove a blocking rule. Returns True if rule existed."""
        with self._lock:
            domain_lower = domain.lower()
            if domain_lower in self._rules:
                del self._rules[domain_lower]
                self._invalidate_cache_for_domain(domain)
                return True
            return False

    def get_rules(self) -> List[BlockingRule]:
        """Get all active blocking rules."""
        with self._lock:
            return [rule for rule in self._rules.values() if rule.enabled]

    def set_rules(self, rules: List[BlockingRule]) -> None:
        """Replace all rules with a new set."""
        with self._lock:
            self._rules.clear()
            self._cache.clear()
            for rule in rules:
                self._rules[rule.domain.lower()] = rule

    def set_external_checker(
        self, checker: Callable[[str, str], BlockingDecision]
    ) -> None:
        """Set an external checker for blocking decisions."""
        with self._lock:
            self._external_checker = checker
            self._cache.clear()

    def should_block(self, url: str, domain: Optional[str] = None) -> BlockingDecision:
        """Check if a URL should be blocked.

        Args:
            url: The full URL to check.
            domain: Optional pre-extracted domain. If not provided, extracted from URL.

        Returns:
            BlockingDecision with the result.
        """
        if not url:
            return BlockingDecision(should_block=False)

        # Extract domain if not provided
        if domain is None:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
            except Exception:
                return BlockingDecision(should_block=False)

        if not domain:
            return BlockingDecision(should_block=False)

        domain = domain.lower()
        cache_key = f"{domain}:{url}"

        with self._lock:
            # Check cache first
            if cache_key in self._cache:
                decision, timestamp = self._cache[cache_key]
                if time.time() - timestamp < self._cache_ttl:
                    return BlockingDecision(
                        should_block=decision.should_block,
                        reason=decision.reason,
                        rule=decision.rule,
                        cached=True,
                    )

            # Check local rules
            decision = self._check_local_rules(domain)
            if decision.should_block:
                self._cache[cache_key] = (decision, time.time())
                return decision

            # Check external checker if available
            if self._external_checker is not None:
                try:
                    decision = self._external_checker(url, domain)
                    self._cache[cache_key] = (decision, time.time())
                    return decision
                except Exception as e:
                    logger.warning("External blocking check failed: %s", e)

            # Default: don't block
            decision = BlockingDecision(should_block=False)
            self._cache[cache_key] = (decision, time.time())
            return decision

    def _check_local_rules(self, domain: str) -> BlockingDecision:
        """Check domain against local rules."""
        # Exact match
        if domain in self._rules:
            rule = self._rules[domain]
            if rule.enabled:
                return BlockingDecision(
                    should_block=True,
                    reason=rule.reason,
                    rule=rule,
                )

        # Subdomain matching (e.g., www.facebook.com matches facebook.com rule)
        parts = domain.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[i:])
            if parent in self._rules:
                rule = self._rules[parent]
                if rule.enabled:
                    return BlockingDecision(
                        should_block=True,
                        reason=rule.reason,
                        rule=rule,
                    )

        return BlockingDecision(should_block=False)

    def _invalidate_cache_for_domain(self, domain: str) -> None:
        """Invalidate all cache entries for a domain."""
        domain_lower = domain.lower()
        keys_to_remove = [
            key for key in self._cache if key.startswith(f"{domain_lower}:")
        ]
        for key in keys_to_remove:
            del self._cache[key]

    def clear_cache(self) -> None:
        """Clear the decision cache."""
        with self._lock:
            self._cache.clear()

    def cleanup_cache(self) -> int:
        """Remove expired cache entries. Returns count of removed entries."""
        now = time.time()
        with self._lock:
            expired = [
                key
                for key, (_, timestamp) in self._cache.items()
                if now - timestamp >= self._cache_ttl
            ]
            for key in expired:
                del self._cache[key]
            return len(expired)


# Global singleton instance
_blocking_manager: Optional[BlockingManager] = None
_blocking_lock = threading.Lock()


def get_blocking_manager() -> BlockingManager:
    """Get the global BlockingManager singleton."""
    global _blocking_manager
    if _blocking_manager is None:
        with _blocking_lock:
            if _blocking_manager is None:
                _blocking_manager = BlockingManager()
    return _blocking_manager
