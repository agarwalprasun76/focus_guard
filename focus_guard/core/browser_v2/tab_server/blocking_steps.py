"""Pipeline step implementations for the blocking pipeline.

Each step corresponds to one check in the audit order (see
BLOCKING_CLASSIFICATION_PRIORITY_AND_DESIGN.md §3.2). Steps read _blocker
from context when they need ClassificationBlocker config or helpers.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from .blocking import BlockingRule
from .blocking_pipeline import BlockingContext, BlockingRequest, BlockingStepResult

logger = logging.getLogger(__name__)

# Domain lists and config are imported from classification_blocker to avoid duplication
from .classification_blocker import (
    ALWAYS_ALLOWED_CATEGORIES,
    ALWAYS_ALLOWED_DOMAINS,
    _get_allowed_categories,
    _get_config_manager,
    _get_allowed_domains,
)


def _blocker(request: BlockingRequest, ctx: BlockingContext):
    return ctx.get("_blocker")


def _llm_observability_enabled() -> bool:
    """Feature flag for non-essential LLM observability writes."""
    return os.getenv("FOCUS_GUARD_ENABLE_LLM_OBSERVABILITY", "1").strip().lower() in {
        "1",
        "true",
        "yes",
    }


# ---------------------------------------------------------------------------
# Step 1: active_override
# ---------------------------------------------------------------------------

def step_active_override(request: BlockingRequest, ctx: BlockingContext) -> Optional[BlockingStepResult]:
    """If domain has an active (non-expired) override, allow. Terminal when override present."""
    try:
        from .override_manager import get_override_manager
        status = get_override_manager().check_override(request.domain)
        if status.get("has_override"):
            remaining = status.get("remaining_seconds", 0)
            return BlockingStepResult(
                terminal=True,
                should_block=False,
                reason=f"Override active ({int(remaining)}s remaining)",
                step_name="active_override",
                details={"remaining_seconds": remaining},
            )
    except Exception as e:
        logger.debug("Override check failed (continuing): %s", e)
    return None


# ---------------------------------------------------------------------------
# Step 2: force_blocked_domain (guardian override of category allow)
# ---------------------------------------------------------------------------

def step_force_blocked_domain(request: BlockingRequest, ctx: BlockingContext) -> Optional[BlockingStepResult]:
    """Domain on guardian force-block list. Terminal block (overrides category allow)."""
    from focus_guard.core.domain.domain_config_manager import find_matching_domain

    mgr = _get_config_manager()
    if not mgr:
        return None
    force_blocked = mgr.get_force_blocked_domains()
    if not find_matching_domain(request.domain, force_blocked):
        return None
    logger.debug("Domain %s is force-blocked by guardian", request.domain)
    blocker = _blocker(request, ctx)
    cat = (mgr.get_category_for_domain(request.domain) or "ENTERTAINMENT").upper()
    budget = blocker._get_budget_status(request.domain, cat, "DISTRACTION") if blocker else None
    return BlockingStepResult(
        terminal=True,
        should_block=True,
        reason=f"Domain {request.domain} blocked by guardian",
        step_name="force_blocked_domain",
        details={
            "rule": BlockingRule(
                domain=request.domain,
                reason=f"Domain {request.domain} blocked by guardian",
                category=cat,
            ),
            "classification": {
                "category": cat,
                "usefulness": "DISTRACTION",
                "confidence": 1.0,
                "reason": "Guardian force-blocked this domain",
                "classifier_used": "guardian_override",
                "decision_source": "override",
                "block_basis": "force_blocked_domain",
                "is_distracting": True,
            },
            "budget_status": budget,
        },
    )


# ---------------------------------------------------------------------------
# Step 3: always_allowed_domain
# ---------------------------------------------------------------------------

def step_always_allowed_domain(request: BlockingRequest, ctx: BlockingContext) -> Optional[BlockingStepResult]:
    """Domain in ALWAYS_ALLOWED_DOMAINS (subdomain match). Terminal allow."""
    from focus_guard.core.domain.domain_config_manager import find_matching_domain
    if find_matching_domain(request.domain, ALWAYS_ALLOWED_DOMAINS):
        logger.debug("Domain %s is in always-allowed list", request.domain)
        blocker = _blocker(request, ctx)
        budget = blocker._get_budget_status(request.domain, "PRODUCTIVITY", "NEUTRAL") if blocker else None
        return BlockingStepResult(
            terminal=True,
            should_block=False,
            reason="Core productivity tool (always allowed)",
            step_name="always_allowed_domain",
            details={
                "classification": {
                    "category": "PRODUCTIVITY",
                    "usefulness": "NEUTRAL",
                    "confidence": 1.0,
                    "reason": "Core productivity tool (always allowed)",
                    "classifier_used": "whitelist",
                    "decision_source": "override",
                    "block_basis": "explicit_allow_domain",
                    "is_distracting": False,
                },
                "budget_status": budget,
            },
        )
    return None


# ---------------------------------------------------------------------------
# Step 3: search_context_block
# ---------------------------------------------------------------------------

def step_search_context_block(request: BlockingRequest, ctx: BlockingContext) -> Optional[BlockingStepResult]:
    """File-sharing / search context block (e.g. entertainment on Drive). Terminal when should_block."""
    try:
        from .search_context_tracker import get_search_context_tracker
        tracker = get_search_context_tracker()
        search_check = tracker.check_should_block_file_sharing(
            url=request.url,
            domain=request.domain,
            title=request.title,
            tab_id=request.tab_id,
        )
        ctx.set("search_check", search_check)
        if search_check.get("should_block"):
            reason = search_check.get("reason", "Entertainment content on file-sharing site")
            logger.info("Blocking file-sharing URL due to search context: %s", reason)
            blocker = _blocker(request, ctx)
            budget = blocker._get_budget_status(request.domain, "ENTERTAINMENT", "DISTRACTION") if blocker else None
            return BlockingStepResult(
                terminal=True,
                should_block=True,
                reason=reason,
                step_name="search_context_block",
                details={
                    "rule": BlockingRule(domain=request.domain, reason=reason, category="ENTERTAINMENT"),
                    "classification": {
                        "category": "ENTERTAINMENT",
                        "usefulness": "DISTRACTION",
                        "confidence": 0.9,
                        "reason": reason,
                        "classifier_used": "search_context",
                        "decision_source": "override",
                        "block_basis": "search_context_file_sharing",
                    },
                    "budget_status": budget,
                },
            )
    except Exception as e:
        logger.debug("Search context check failed (continuing): %s", e)
    return None


# ---------------------------------------------------------------------------
# Step 4: immediate_domain_block
# ---------------------------------------------------------------------------

def step_immediate_domain_block(request: BlockingRequest, ctx: BlockingContext) -> Optional[BlockingStepResult]:
    """Adult or pure entertainment domain (no content-aware classifier). Terminal when should_block."""
    CONTENT_AWARE_DOMAINS = {"youtube.com", "youtu.be", "reddit.com", "twitter.com", "x.com", "spotify.com"}
    domain_lower = request.domain.lower()
    has_content_aware = any(cad in domain_lower for cad in CONTENT_AWARE_DOMAINS)
    try:
        mgr = _get_config_manager()
        if mgr:
            known_cat = mgr.get_category_for_domain(request.domain)
            cat_upper = (known_cat or "").upper()
            should_block = False
            block_reason = ""
            if cat_upper == "ADULT":
                should_block = True
                block_reason = "Adult content is blocked"
            elif cat_upper == "ENTERTAINMENT" and not has_content_aware:
                should_block = True
                block_reason = f"Entertainment site {request.domain} is blocked"
            if should_block:
                blocker = _blocker(request, ctx)
                budget = blocker._get_budget_status(request.domain, cat_upper, "DISTRACTION") if blocker else None
                logger.info("Immediate %s block: %s", cat_upper.lower(), request.domain)
                return BlockingStepResult(
                    terminal=True,
                    should_block=True,
                    reason=block_reason,
                    step_name="immediate_domain_block",
                    details={
                        "rule": BlockingRule(domain=request.domain, reason=block_reason, category=cat_upper),
                        "classification": {
                            "category": cat_upper,
                            "usefulness": "DISTRACTION",
                            "confidence": 1.0,
                            "reason": block_reason,
                            "classifier_used": f"{cat_upper.lower()}_domain_block",
                            "decision_source": "override",
                            "block_basis": "explicit_domain_category",
                            "is_distracting": True,
                        },
                        "budget_status": budget,
                    },
                )
    except Exception as e:
        logger.debug("Adult content check failed: %s", e)
    return None


# ---------------------------------------------------------------------------
# Step 5: schedule_check (4.7 — no-op until schedule config exists)
# ---------------------------------------------------------------------------
# When 4.7 is implemented: read schedule profile (e.g. from context or
# get_schedule_config()), determine if current time allows this domain;
# return terminal allow/block when profile applies. Context keys for future use:
#   schedule_profile, schedule_decision (block/allow/neutral).

def step_schedule_check(request: BlockingRequest, ctx: BlockingContext) -> Optional[BlockingStepResult]:
    """Time-based access schedule (4.7). No-op until schedule config exists; then terminal when profile applies."""
    return None


# ---------------------------------------------------------------------------
# Step 6: classification (never terminal; stores result in context)
# ---------------------------------------------------------------------------

def step_classification(request: BlockingRequest, ctx: BlockingContext) -> Optional[BlockingStepResult]:
    """Run classification service (cache → classifier → LLM escalation). Store in context; never terminal."""
    blocker = _blocker(request, ctx)
    if not blocker:
        return None
    service = blocker._get_classification_service()
    if service is None:
        ctx.set("classification_result", None)
        return None

    classify_context: Dict[str, Any] = {"url": request.url}
    if request.title:
        classify_context["title"] = request.title
    if request.tab_id is not None:
        classify_context["tab_id"] = request.tab_id
    search_check = ctx.get("search_check") or {}
    if search_check.get("search_context"):
        classify_context["search_context"] = search_check.get("search_context")
        classify_context["search_matched_keywords"] = search_check.get("matched_keywords", [])

    try:
        result = asyncio.run(service.classify_async(request.domain, request.url, classify_context))
    except Exception as e:
        logger.warning("Classification failed: %s", e)
        ctx.set("classification_result", None)
        return None

    if result is None:
        ctx.set("classification_result", None)
        return None

    llm_escalation_attempted = False
    llm_escalation_applied = False
    initial_source = blocker._decision_source_from_classifier(result.classifier_used)
    if (
        blocker.escalate_uncertain_to_llm
        and result.confidence < blocker.low_confidence_threshold
        and initial_source != "llm"
    ):
        llm_escalation_attempted = True
        llm_context = dict(classify_context)
        llm_context["force_llm"] = True
        llm_context["rule_confidence_threshold"] = 1.1
        try:
            llm_result = asyncio.run(service.classify_async(request.domain, request.url, llm_context))
            if llm_result is not None and blocker._decision_source_from_classifier(llm_result.classifier_used) == "llm":
                result = llm_result
                llm_escalation_applied = True
        except Exception as e:
            logger.debug("LLM escalation failed: %s", e)

    ctx.set("llm_escalation_attempted", llm_escalation_attempted)
    ctx.set("llm_escalation_applied", llm_escalation_applied)

    # Persist LLM classifications for auditability (harder/more controversial decisions)
    final_source = blocker._decision_source_from_classifier(result.classifier_used)
    if final_source == "llm" and _llm_observability_enabled():
        try:
            from .llm_classification_log import log_llm_classification
            log_llm_classification(
                url=request.url,
                domain=request.domain,
                result=result,
                title=request.title,
                request_context=classify_context,
                step_trace=None,
                llm_escalation_attempted=llm_escalation_attempted,
                llm_escalation_applied=llm_escalation_applied,
            )
        except Exception as e:
            logger.warning("Failed to persist LLM classification log: %s", e)

    ctx.set("classification_result", result)
    # Non-terminal: next steps use context
    return BlockingStepResult(
        terminal=False,
        should_block=False,
        step_name="classification",
        details={},
    )


# ---------------------------------------------------------------------------
# Step 7: fallback_domain_rule
# ---------------------------------------------------------------------------

def step_fallback_domain_rule(request: BlockingRequest, ctx: BlockingContext) -> Optional[BlockingStepResult]:
    """If classification failed or low-confidence UNKNOWN, apply domain rule. Terminal when domain rule matches."""
    result = ctx.get("classification_result")
    blocker = _blocker(request, ctx)
    if not blocker:
        return None
    # Only fallback when no result or low-confidence UNKNOWN
    if result is not None and not (result.category == "UNKNOWN" and result.confidence < 0.5):
        return None

    try:
        mgr = _get_config_manager()
        if not mgr:
            return None
        known_cat = mgr.get_category_for_domain(request.domain)
        if not known_cat:
            return None
        from focus_guard.core.domain.domain_config_manager import CATEGORY_TO_ENUM
        enum_cat = CATEGORY_TO_ENUM.get(known_cat, known_cat.upper())
        if enum_cat in blocker.blocked_categories:
            block_reason = f"Domain {request.domain} is in blocked category {enum_cat} (fallback rule)"
            budget = blocker._get_budget_status(request.domain, enum_cat, "DISTRACTION")
            logger.info("Fallback domain block: %s → %s", request.domain, enum_cat)
            return BlockingStepResult(
                terminal=True,
                should_block=True,
                reason=block_reason,
                step_name="fallback_domain_rule",
                details={
                    "rule": BlockingRule(domain=request.domain, reason=block_reason, category=enum_cat),
                    "classification": {
                        "category": enum_cat,
                        "usefulness": "DISTRACTION",
                        "confidence": 0.7,
                        "reason": block_reason,
                        "classifier_used": "domain_fallback",
                        "decision_source": "override",
                        "block_basis": "explicit_domain_rule",
                        "is_distracting": True,
                    },
                    "budget_status": budget,
                },
            )
        if enum_cat in _get_allowed_categories():
            budget = blocker._get_budget_status(request.domain, enum_cat, "NEUTRAL")
            return BlockingStepResult(
                terminal=True,
                should_block=False,
                reason=f"Known {known_cat} domain (allowed)",
                step_name="fallback_domain_rule",
                details={
                    "classification": {
                        "category": enum_cat,
                        "usefulness": "NEUTRAL",
                        "confidence": 0.7,
                        "reason": f"Known {known_cat} domain (allowed)",
                        "classifier_used": "domain_fallback",
                        "decision_source": "override",
                        "block_basis": "explicit_domain_rule_allow",
                        "is_distracting": False,
                    },
                    "budget_status": budget,
                },
            )
    except Exception as e:
        logger.debug("Fallback domain rules check failed: %s", e)
    return None


# ---------------------------------------------------------------------------
# Step 8: policy_from_classification
# ---------------------------------------------------------------------------

def step_policy_from_classification(request: BlockingRequest, ctx: BlockingContext) -> Optional[BlockingStepResult]:
    """Apply policy from classification in context. Always terminal (block or allow)."""
    blocker = _blocker(request, ctx)
    result = ctx.get("classification_result")
    if not blocker:
        return BlockingStepResult(terminal=True, should_block=False, step_name="policy_from_classification", details={})
    if result is None:
        # No classification (service unavailable or failed and no fallback) -> allow
        return BlockingStepResult(terminal=True, should_block=False, step_name="policy_from_classification", details={})

    usefulness_str = result.usefulness.value if hasattr(result.usefulness, "value") else str(result.usefulness)
    classification_dict = {
        "category": result.category,
        "usefulness": usefulness_str,
        "confidence": result.confidence,
        "reason": result.reason,
        "classifier_used": result.classifier_used,
        "decision_source": blocker._decision_source_from_classifier(result.classifier_used),
        "content_type": getattr(result, "content_type", "unknown"),
        "is_distracting": result.is_distracting,
        "llm_escalation_attempted": ctx.get("llm_escalation_attempted", False),
        "llm_escalation_applied": ctx.get("llm_escalation_applied", False),
    }
    budget_status = blocker._get_budget_status(request.domain, result.category, usefulness_str.upper())
    if budget_status and budget_status.get("budget_exhausted"):
        classification_dict["budget_exhausted"] = True

    should_block = False
    block_reason = ""
    block_basis = "none"
    if result.category in blocker.blocked_categories:
        should_block = True
        block_reason = f"Category {result.category} is blocked"
        block_basis = "category_rule"
    if blocker.block_distracting and result.is_distracting:
        should_block = True
        block_reason = block_reason or f"Content classified as distracting ({result.category})"
        block_basis = "distracting_content"
    mgr = _get_config_manager()
    if mgr:
        from focus_guard.core.domain.domain_config_manager import find_matching_domain

        if find_matching_domain(request.domain, mgr.get_force_blocked_domains()):
            should_block = True
            block_reason = f"Domain {request.domain} blocked by guardian"
            block_basis = "force_blocked_domain"
    if not should_block and result.category in ALWAYS_ALLOWED_CATEGORIES:
        should_block = False
        block_reason = ""
        block_basis = "always_allowed_category"
    if result.confidence < blocker.low_confidence_threshold:
        classification_dict["is_uncertain"] = True
        classification_dict["uncertain_policy"] = blocker.uncertain_policy
        if blocker.uncertain_policy == "allow":
            should_block = False
            block_reason = ""
            block_basis = "uncertain_low_confidence_allow"
        else:
            should_block = True
            block_reason = block_reason or f"Low-confidence classification ({result.confidence:.2f}) treated as block"
            block_basis = "uncertain_low_confidence_block"
    classification_dict["block_basis"] = block_basis
    classification_dict["block_reason"] = block_reason

    if blocker.log_activity:
        try:
            blocker._log_classification_event(
                domain=request.domain,
                url=request.url,
                result=result,
                is_blocked=should_block,
                block_reason=block_reason,
            )
        except Exception as e:
            logger.warning("Failed to log classification event: %s", e)

    rule = BlockingRule(domain=request.domain, reason=block_reason, category=result.category) if should_block else None
    return BlockingStepResult(
        terminal=True,
        should_block=should_block,
        reason=block_reason or None,
        step_name="policy_from_classification",
        details={
            "rule": rule,
            "classification": classification_dict,
            "budget_status": budget_status,
        },
    )


# ---------------------------------------------------------------------------
# Step order for pipeline registration (audit names)
# ---------------------------------------------------------------------------

STEP_ORDER = [
    ("active_override", step_active_override),
    ("force_blocked_domain", step_force_blocked_domain),
    ("always_allowed_domain", step_always_allowed_domain),
    ("search_context_block", step_search_context_block),
    ("immediate_domain_block", step_immediate_domain_block),
    ("schedule_check", step_schedule_check),
    ("classification", step_classification),
    ("fallback_domain_rule", step_fallback_domain_rule),
    ("policy_from_classification", step_policy_from_classification),
]
