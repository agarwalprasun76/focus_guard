"""Classification-based blocking integration.

Connects the domain classifier to the blocking system, allowing
blocking decisions to be made based on content classification.

As of Section 7 consolidation, blocked/allowed categories and domains
are read from DomainConfigManager (domain_config.json). The hardcoded
values below are kept as **fallback defaults** only.
"""

import logging
from typing import Dict, Any, Optional, Set

from .blocking import BlockingDecision, BlockingRule

logger = logging.getLogger(__name__)


def _get_config_manager():
    """Lazy import to avoid circular dependencies."""
    try:
        from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
        return get_domain_config_manager()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Fallback defaults (used only when DomainConfigManager is unavailable)
# ---------------------------------------------------------------------------

_FALLBACK_BLOCKED_CATEGORIES: Set[str] = {
    "ENTERTAINMENT",
    "GAMING", 
    "SOCIAL_MEDIA",
    "ADULT",
}

_FALLBACK_ALLOWED_CATEGORIES: Set[str] = {
    "EDUCATION",
    "PRODUCTIVITY",
}

_FALLBACK_ALLOWED_DOMAINS: Set[str] = {
    # Email
    "mail.google.com",
    "outlook.live.com",
    "outlook.office.com",
    "outlook.office365.com",
    "mail.yahoo.com",
    "mail.proton.me",
    "mail.zoho.com",
    # Productivity suites (excluding Drive which can host entertainment)
    "calendar.google.com",
    "docs.google.com",
    "sheets.google.com",
    "slides.google.com",
    "meet.google.com",
    "teams.microsoft.com",
    "notion.so",
    "www.notion.so",
    # Developer tools
    "github.com",
    "www.github.com",
    "gitlab.com",
    "www.gitlab.com",
    "stackoverflow.com",
    "www.stackoverflow.com",
}


# ---------------------------------------------------------------------------
# Public API — reads from DomainConfigManager, falls back to hardcoded
# ---------------------------------------------------------------------------

def _get_blocked_categories() -> Set[str]:
    mgr = _get_config_manager()
    if mgr:
        return mgr.get_blocked_categories()
    return _FALLBACK_BLOCKED_CATEGORIES


def _get_allowed_categories() -> Set[str]:
    mgr = _get_config_manager()
    if mgr:
        return mgr.get_always_allowed_categories()
    return _FALLBACK_ALLOWED_CATEGORIES


def _get_allowed_domains() -> Set[str]:
    mgr = _get_config_manager()
    if mgr:
        return mgr.get_always_allowed_domains()
    return _FALLBACK_ALLOWED_DOMAINS


# Module-level names kept for backward compatibility
DEFAULT_BLOCKED_CATEGORIES: Set[str] = _get_blocked_categories()
ALWAYS_ALLOWED_CATEGORIES: Set[str] = _get_allowed_categories()
ALWAYS_ALLOWED_DOMAINS: Set[str] = _get_allowed_domains()


class ClassificationBlocker:
    """Integrates classification with blocking decisions.
    
    Uses the ClassificationService to classify URLs and makes blocking
    decisions based on the classification result.
    """
    
    def __init__(
        self,
        blocked_categories: Optional[Set[str]] = None,
        block_distracting: bool = True,
        log_activity: bool = True,
        low_confidence_threshold: float = 0.6,
        escalate_uncertain_to_llm: bool = True,
        uncertain_policy: str = "allow",
    ):
        """Initialize the classification blocker.
        
        Args:
            blocked_categories: Set of category names to block.
            block_distracting: If True, block content marked as DISTRACTION.
            log_activity: If True, log all classification/blocking events.
            low_confidence_threshold: Below this confidence, treat result as uncertain.
            escalate_uncertain_to_llm: Try an explicit LLM pass for uncertain non-LLM results.
            uncertain_policy: Policy for uncertain outcomes: "allow" or "block".
        """
        self.blocked_categories = blocked_categories or DEFAULT_BLOCKED_CATEGORIES
        self.block_distracting = block_distracting
        self.log_activity = log_activity
        self.low_confidence_threshold = max(0.0, min(1.0, low_confidence_threshold))
        self.escalate_uncertain_to_llm = escalate_uncertain_to_llm
        self.uncertain_policy = "block" if str(uncertain_policy).lower() == "block" else "allow"
        self._classification_service = None
        self._activity_logger = None
    
    def _get_classification_service(self):
        """Lazy-load classification service."""
        if self._classification_service is None:
            try:
                from .classification_service import get_classification_service
                self._classification_service = get_classification_service()
            except Exception as e:
                logger.warning("Could not load classification service: %s", e)
        return self._classification_service
    
    def _get_activity_logger(self):
        """Lazy-load activity logger."""
        if self._activity_logger is None and self.log_activity:
            try:
                from .activity_logger import get_activity_logger
                self._activity_logger = get_activity_logger()
            except Exception as e:
                logger.warning("Could not load activity logger: %s", e)
        return self._activity_logger
    
    def _get_budget_status(self, domain: str, category: str, usefulness: str) -> Optional[Dict[str, Any]]:
        """Get current budget status for the domain and classification.
        
        Returns dict with time_used, time_budget, remaining_seconds, etc.
        """
        try:
            from .domain_usage_tracker import get_domain_usage_tracker
            tracker = get_domain_usage_tracker()
            return tracker.get_budget_status_for_classification(domain, category, usefulness)
        except Exception as e:
            logger.debug("Could not get budget status: %s", e)
            return None

    def _decision_source_from_classifier(self, classifier_used: str) -> str:
        """Map raw classifier name to normalized decision source."""
        source = (classifier_used or "").lower()
        if "llm" in source:
            return "llm"
        if source in {"whitelist", "search_context", "domain_fallback"}:
            return "override"
        if "rule" in source or "domain" in source:
            return "rule"
        return "hybrid"
    
    def _get_pipeline(self):
        """Build or return the blocking pipeline with all steps (lazy, once per blocker)."""
        if getattr(self, "_pipeline", None) is None:
            from .blocking_pipeline import BlockingPipeline
            from .blocking_steps import STEP_ORDER
            self._pipeline = BlockingPipeline()
            for name, step_fn in STEP_ORDER:
                self._pipeline.add_step(name, step_fn)
        return self._pipeline

    def check_blocking(
        self, 
        url: str, 
        domain: str,
        title: str = "",
        tab_id: Optional[int] = None,
    ) -> BlockingDecision:
        """Check if a URL should be blocked based on classification.
        
        Runs the modular blocking pipeline (override → always-allowed → search
        context → immediate domain block → schedule → classification → fallback
        domain rule → policy). First terminal step wins; full step_trace is
        available for auditing. LLM classifications are persisted for auditability.
        
        This is the callback for BlockingManager.external_checker.
        
        Args:
            url: The URL to check.
            domain: The domain of the URL.
            title: The page title (if available).
            tab_id: The browser tab ID (if available).
            
        Returns:
            BlockingDecision with the result, including classification and budget info.
        """
        from .blocking_pipeline import BlockingRequest, BlockingContext

        request = BlockingRequest(url=url, domain=domain, title=title, tab_id=tab_id)

        def context_initializer(req: BlockingRequest) -> BlockingContext:
            ctx = BlockingContext()
            ctx.set("_blocker", self)
            return ctx

        pipeline = self._get_pipeline()
        decision, step_trace = pipeline.run(request, context_initializer=context_initializer)
        # TODO (4.3): write decision log row with step_trace here
        return decision
    
    def _log_classification_event(
        self,
        domain: str,
        url: str,
        result: Any,
        is_blocked: bool,
        block_reason: str,
    ) -> None:
        """Log classification and blocking event."""
        activity_logger = self._get_activity_logger()
        if activity_logger is None:
            return
        
        try:
            if is_blocked:
                activity_logger.log_block(
                    domain=domain,
                    url=url,
                    block_reason=block_reason,
                    classification_category=result.category,
                    classification_usefulness=result.usefulness.value,
                    classification_confidence=result.confidence,
                )
            else:
                activity_logger.log_classification(
                    domain=domain,
                    url=url,
                    classification_category=result.category,
                    classification_usefulness=result.usefulness.value,
                    classification_confidence=result.confidence,
                    is_distracting=result.is_distracting,
                    classifier_used=result.classifier_used,
                )
        except Exception as e:
            logger.warning("Failed to log classification event: %s", e)
    
    def _fallback_to_domain_rules(
        self,
        domain: str,
        url: str,
        title: str,
    ) -> BlockingDecision:
        """Fall back to domain-level rules when intelligent classification fails.
        
        This is used when:
        1. Classification service is unavailable
        2. Classification returns None
        3. Classification returns low-confidence UNKNOWN
        
        Domain rules are a safety net, not the primary blocking mechanism.
        """
        try:
            mgr = _get_config_manager()
            if mgr:
                known_cat = mgr.get_category_for_domain(domain)
                if known_cat:
                    from focus_guard.core.domain.domain_config_manager import CATEGORY_TO_ENUM
                    enum_cat = CATEGORY_TO_ENUM.get(known_cat, known_cat.upper())
                    
                    if enum_cat in self.blocked_categories:
                        block_reason = f"Domain {domain} is in blocked category {enum_cat} (fallback rule)"
                        budget_status = self._get_budget_status(domain, enum_cat, "DISTRACTION")
                        logger.info("Fallback domain block: %s → %s", domain, enum_cat)
                        return BlockingDecision(
                            should_block=True,
                            reason=block_reason,
                            rule=BlockingRule(domain=domain, reason=block_reason, category=enum_cat),
                            classification={
                                "category": enum_cat,
                                "usefulness": "DISTRACTION",
                                "confidence": 0.7,  # Lower confidence for fallback
                                "reason": block_reason,
                                "classifier_used": "domain_fallback",
                                "decision_source": "override",
                                "block_basis": "explicit_domain_rule",
                                "is_distracting": True,
                            },
                            budget_status=budget_status,
                        )
                    elif enum_cat in _get_allowed_categories():
                        return BlockingDecision(
                            should_block=False,
                            classification={
                                "category": enum_cat,
                                "usefulness": "NEUTRAL",
                                "confidence": 0.7,
                                "reason": f"Known {known_cat} domain (allowed)",
                                "classifier_used": "domain_fallback",
                                "decision_source": "override",
                                "block_basis": "explicit_domain_rule_allow",
                                "is_distracting": False,
                            },
                            budget_status=self._get_budget_status(domain, enum_cat, "NEUTRAL"),
                        )
        except Exception as e:
            logger.debug("Fallback domain rules check failed: %s", e)
        
        # No matching domain rule - allow by default
        return BlockingDecision(should_block=False)
    
    def update_blocked_categories(self, categories: Set[str]) -> None:
        """Update the set of blocked categories."""
        self.blocked_categories = categories
        logger.info("Updated blocked categories: %s", categories)


# Singleton instance
_classification_blocker: Optional[ClassificationBlocker] = None


def get_classification_blocker() -> ClassificationBlocker:
    """Get the singleton ClassificationBlocker instance."""
    global _classification_blocker
    if _classification_blocker is None:
        _classification_blocker = ClassificationBlocker()
    return _classification_blocker


def create_classification_blocking_checker():
    """Create a blocking checker function for BlockingManager.
    
    Returns a callable that can be passed to BlockingManager.set_external_checker().
    """
    blocker = get_classification_blocker()
    return blocker.check_blocking


def setup_classification_blocking():
    """Set up classification-based blocking on the global BlockingManager.
    
    Call this during application startup to enable classification-based blocking.
    """
    from .blocking import get_blocking_manager
    
    blocking_manager = get_blocking_manager()
    checker = create_classification_blocking_checker()
    blocking_manager.set_external_checker(checker)
    
    logger.info("Classification-based blocking enabled")
