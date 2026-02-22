"""Classification-based blocking integration.

Connects the domain classifier to the blocking system, allowing
blocking decisions to be made based on content classification.

As of Section 7 consolidation, blocked/allowed categories and domains
are read from DomainConfigManager (domain_config.json). The hardcoded
values below are kept as **fallback defaults** only.
"""

import asyncio
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
    
    def check_blocking(
        self, 
        url: str, 
        domain: str,
        title: str = "",
        tab_id: Optional[int] = None,
    ) -> BlockingDecision:
        """Check if a URL should be blocked based on classification.
        
        This is the callback for BlockingManager.external_checker.
        
        Args:
            url: The URL to check.
            domain: The domain of the URL.
            title: The page title (if available).
            tab_id: The browser tab ID (if available).
            
        Returns:
            BlockingDecision with the result, including classification and budget info.
        """
        # Check if domain is in always-allowed list (core productivity tools)
        # Use subdomain-aware matching (e.g. stanfordohs.pronto.io matches pronto.io)
        from focus_guard.core.domain.domain_config_manager import find_matching_domain
        if find_matching_domain(domain, ALWAYS_ALLOWED_DOMAINS):
            logger.debug("Domain %s is in always-allowed list, skipping classification", domain)
            return BlockingDecision(
                should_block=False,
                classification={
                    "category": "PRODUCTIVITY",
                    "usefulness": "NEUTRAL",
                    "confidence": 1.0,
                    "reason": "Core productivity tool (always allowed)",
                    "classifier_used": "whitelist",
                    "decision_source": "override",
                    "block_basis": "explicit_allow_domain",
                    "is_distracting": False,
                },
                budget_status=self._get_budget_status(domain, "PRODUCTIVITY", "NEUTRAL"),
            )
        
        search_check: Dict[str, Any] = {}
        # First, check search context for file-sharing sites
        # This catches entertainment content on Google Drive, etc.
        try:
            from .search_context_tracker import get_search_context_tracker
            tracker = get_search_context_tracker()
            search_check = tracker.check_should_block_file_sharing(
                url=url,
                domain=domain,
                title=title,
                tab_id=tab_id,
            )
            
            if search_check.get("should_block"):
                reason = search_check.get("reason", "Entertainment content on file-sharing site")
                logger.info("Blocking file-sharing URL due to search context: %s", reason)
                # Get budget status for entertainment content
                budget_status = self._get_budget_status(domain, "ENTERTAINMENT", "DISTRACTION")
                return BlockingDecision(
                    should_block=True,
                    reason=reason,
                    rule=BlockingRule(
                        domain=domain,
                        reason=reason,
                        category="ENTERTAINMENT",
                    ),
                    classification={
                        "category": "ENTERTAINMENT",
                        "usefulness": "DISTRACTION",
                        "confidence": 0.9,
                        "reason": reason,
                        "classifier_used": "search_context",
                        "decision_source": "override",
                        "block_basis": "search_context_file_sharing",
                    },
                    budget_status=budget_status,
                )
        except Exception as e:
            logger.debug("Search context check failed (continuing): %s", e)
        
        # IMMEDIATE BLOCK: Adult/porn and pure entertainment sites - no classification needed
        # These should be blocked instantly without waiting for classification
        # Pure entertainment = sites that have NO educational content (unlike YouTube)
        ALWAYS_BLOCK_CATEGORIES = {"ADULT", "ENTERTAINMENT"}
        # Exception: sites with content-aware classifiers that CAN have educational content
        # Spotify included because it has educational podcasts
        CONTENT_AWARE_DOMAINS = {"youtube.com", "youtu.be", "reddit.com", "twitter.com", "x.com", "spotify.com"}
        domain_lower = domain.lower()
        has_content_aware_classifier = any(cad in domain_lower for cad in CONTENT_AWARE_DOMAINS)
        
        try:
            mgr = _get_config_manager()
            if mgr:
                known_cat = mgr.get_category_for_domain(domain)
                cat_upper = known_cat.upper() if known_cat else None
                
                # Immediate block for adult content (always) or entertainment (if no content-aware classifier)
                # Adult: always block immediately
                # Entertainment: block immediately UNLESS it has a content-aware classifier (YouTube, Reddit, etc.)
                should_immediate_block = False
                if cat_upper == "ADULT":
                    should_immediate_block = True
                    block_reason = "Adult content is blocked"
                elif cat_upper == "ENTERTAINMENT" and not has_content_aware_classifier:
                    should_immediate_block = True
                    block_reason = f"Entertainment site {domain} is blocked"
                
                if should_immediate_block:
                    budget_status = self._get_budget_status(domain, cat_upper, "DISTRACTION")
                    logger.info("Immediate %s block: %s", cat_upper.lower(), domain)
                    return BlockingDecision(
                        should_block=True,
                        reason=block_reason,
                        rule=BlockingRule(domain=domain, reason=block_reason, category=cat_upper),
                        classification={
                            "category": cat_upper,
                            "usefulness": "DISTRACTION",
                            "confidence": 1.0,
                            "reason": block_reason,
                            "classifier_used": f"{cat_upper.lower()}_domain_block",
                            "decision_source": "override",
                            "block_basis": "explicit_domain_category",
                            "is_distracting": True,
                        },
                        budget_status=budget_status,
                    )
        except Exception as e:
            logger.debug("Adult content check failed: %s", e)
        
        # INTELLIGENT CLASSIFICATION FIRST
        # Always try content-aware classification before falling back to domain rules.
        # This ensures educational YouTube videos, productive Reddit threads, etc. are allowed.
        classification_service = self._get_classification_service()
        if classification_service is None:
            return BlockingDecision(should_block=False)
        
        try:
            # Run async classification in sync context
            # Include title in context for better classification
            context = {"url": url}
            if title:
                context["title"] = title
            if tab_id is not None:
                context["tab_id"] = tab_id
            if search_check.get("search_context"):
                context["search_context"] = search_check.get("search_context")
                context["search_matched_keywords"] = search_check.get("matched_keywords", [])
            
            result = asyncio.run(
                classification_service.classify_async(domain, url, context)
            )
            
            if result is None:
                # Classification failed - fall back to domain-level rules
                return self._fallback_to_domain_rules(domain, url, title)

            llm_escalation_attempted = False
            llm_escalation_applied = False
            initial_decision_source = self._decision_source_from_classifier(result.classifier_used)
            if (
                self.escalate_uncertain_to_llm
                and result.confidence < self.low_confidence_threshold
                and initial_decision_source != "llm"
            ):
                llm_escalation_attempted = True
                llm_context = dict(context)
                llm_context["force_llm"] = True
                llm_context["rule_confidence_threshold"] = 1.1
                llm_result = asyncio.run(
                    classification_service.classify_async(domain, url, llm_context)
                )
                if llm_result is not None and self._decision_source_from_classifier(llm_result.classifier_used) == "llm":
                    result = llm_result
                    llm_escalation_applied = True
            
            # If classification returned UNKNOWN with low confidence, fall back to domain rules
            # This ensures we don't let obviously distracting sites through just because
            # the classifier couldn't determine the content type
            if result.category == "UNKNOWN" and result.confidence < 0.5:
                logger.info("Low-confidence UNKNOWN classification for %s, checking domain rules", domain)
                fallback = self._fallback_to_domain_rules(domain, url, title)
                if fallback.should_block:
                    return fallback
                # If domain rules don't block, continue with the UNKNOWN classification (allow)
            
            # Build classification dict for response
            classification_dict = {
                "category": result.category,
                "usefulness": result.usefulness.value if hasattr(result.usefulness, 'value') else str(result.usefulness),
                "confidence": result.confidence,
                "reason": result.reason,
                "classifier_used": result.classifier_used,
                "decision_source": self._decision_source_from_classifier(result.classifier_used),
                "content_type": getattr(result, 'content_type', 'unknown'),
                "is_distracting": result.is_distracting,
                "llm_escalation_attempted": llm_escalation_attempted,
                "llm_escalation_applied": llm_escalation_applied,
            }
            
            # Get budget status based on classification
            usefulness_str = classification_dict["usefulness"].upper()
            budget_status = self._get_budget_status(domain, result.category, usefulness_str)
            
            # Determine if should block
            should_block = False
            block_reason = ""
            block_basis = "none"
            
            # Check if category is in blocked list
            if result.category in self.blocked_categories:
                should_block = True
                block_reason = f"Category {result.category} is blocked"
                block_basis = "category_rule"
            
            # Check if marked as distraction
            if self.block_distracting and result.is_distracting:
                should_block = True
                block_reason = f"Content classified as distracting ({result.category})"
                block_basis = "distracting_content"
            
            # Never block educational/productivity content
            if result.category in ALWAYS_ALLOWED_CATEGORIES:
                should_block = False
                block_reason = ""
                block_basis = "always_allowed_category"

            if budget_status and budget_status.get("budget_exhausted"):
                classification_dict["budget_exhausted"] = True

            if result.confidence < self.low_confidence_threshold:
                classification_dict["is_uncertain"] = True
                classification_dict["uncertain_policy"] = self.uncertain_policy
                if self.uncertain_policy == "allow":
                    should_block = False
                    block_reason = ""
                    block_basis = "uncertain_low_confidence_allow"
                else:
                    should_block = True
                    block_reason = (
                        block_reason
                        or f"Low-confidence classification ({result.confidence:.2f}) treated as block"
                    )
                    block_basis = "uncertain_low_confidence_block"

            classification_dict["block_basis"] = block_basis
            classification_dict["block_reason"] = block_reason
            
            # Log the activity
            if self.log_activity:
                self._log_classification_event(
                    domain=domain,
                    url=url,
                    result=result,
                    is_blocked=should_block,
                    block_reason=block_reason,
                )
            
            if should_block:
                return BlockingDecision(
                    should_block=True,
                    reason=block_reason,
                    rule=BlockingRule(
                        domain=domain,
                        reason=block_reason,
                        category=result.category,
                    ),
                    classification=classification_dict,
                    budget_status=budget_status,
                )
            
            # Even if not blocking, return classification info for transparency
            return BlockingDecision(
                should_block=False,
                classification=classification_dict,
                budget_status=budget_status,
            )
            
        except Exception as e:
            logger.warning("Classification-based blocking check failed: %s", e)
            return BlockingDecision(should_block=False)
    
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
