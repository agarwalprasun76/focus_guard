"""
Integration matrix: representative Google / YouTube URLs × enforcement modes.

The product pipeline is:

1. ``ClassificationBlocker.check_blocking`` runs the ordered pipeline (override →
   always-allowed → search-context → immediate domain rule → **classification**
   → fallback domain → **policy_from_classification**). Classification runs
   before the policy step decides ``should_block`` from category rules.

2. ``TabServerContext.check_blocking`` applies deployment **enforcement_mode**:
   TRACKING / ADVISORY force ``should_block=False`` while preserving audit
   ``reason`` prefixes when the pipeline would have blocked.

These tests use a **mock classification service** (no network, no OpenAI) so
outcomes are deterministic. Domain-config-driven steps are isolated so the
decision comes from **synthetic classification + policy**, matching the intent
“classify with rules/policy, then enforce.”

Run::

    python -m pytest focus_guard/tests/integration/tab_server/test_classification_enforcement_matrix.py -q
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from focus_guard.core.browser_v2.tab_server.api_models import CommandResult, TabsSnapshot
from focus_guard.core.browser_v2.tab_server.classification_blocker import ClassificationBlocker
from focus_guard.core.browser_v2.tab_server.classification_service import (
    ClassificationResult,
    ContentUsefulness,
)
from focus_guard.core.browser_v2.tab_server.server import TabServerContext


def _youtube_entertainment_result(url: str) -> ClassificationResult:
    return ClassificationResult(
        domain="www.youtube.com",
        url=url,
        category="ENTERTAINMENT",
        usefulness=ContentUsefulness.DISTRACTION,
        confidence=0.9,
        reason="Synthetic entertainment",
        classifier_used="synthetic_youtube",
        is_distracting=True,
        content_type="video",
    )


def _google_education_result(url: str) -> ClassificationResult:
    return ClassificationResult(
        domain="www.google.com",
        url=url,
        category="EDUCATION",
        usefulness=ContentUsefulness.EDUCATIONAL,
        confidence=0.88,
        reason="Synthetic education search",
        classifier_used="synthetic_google",
        is_distracting=False,
        content_type="search",
    )


def _google_entertainment_result(url: str) -> ClassificationResult:
    return ClassificationResult(
        domain="www.google.com",
        url=url,
        category="ENTERTAINMENT",
        usefulness=ContentUsefulness.DISTRACTION,
        confidence=0.87,
        reason="Synthetic entertainment query",
        classifier_used="synthetic_google",
        is_distracting=True,
        content_type="search",
    )


@pytest.fixture
def pipeline_isolation(monkeypatch):
    """Avoid domain-config short-circuits; neutral override and file-sharing checks."""
    monkeypatch.setattr(
        "focus_guard.core.browser_v2.tab_server.blocking_steps._get_config_manager",
        lambda: None,
    )

    ov = MagicMock()
    ov.check_override.return_value = {"has_override": False, "remaining_seconds": 0}
    monkeypatch.setattr(
        "focus_guard.core.browser_v2.tab_server.override_manager.get_override_manager",
        lambda: ov,
    )

    tr = MagicMock()
    tr.check_should_block_file_sharing.return_value = {
        "should_block": False,
        "reason": "",
        "is_file_sharing": False,
    }
    monkeypatch.setattr(
        "focus_guard.core.browser_v2.tab_server.search_context_tracker.get_search_context_tracker",
        lambda: tr,
    )

    log_mock = MagicMock()
    monkeypatch.setattr(
        "focus_guard.core.browser_v2.tab_server.blocking_decision_log.get_blocking_decision_log",
        lambda: log_mock,
    )


@pytest.fixture
def tab_ctx_with_blocker(pipeline_isolation, monkeypatch):
    """TabServerContext + ClassificationBlocker with injected mock classifier."""

    def _factory(classify_fn):
        mock_svc = MagicMock()
        mock_svc.classify_async = AsyncMock(side_effect=classify_fn)

        blocker = ClassificationBlocker(
            blocked_categories={"ENTERTAINMENT", "GAMING", "SOCIAL_MEDIA", "ADULT"},
            block_distracting=True,
            log_activity=True,
            low_confidence_threshold=0.5,
            escalate_uncertain_to_llm=False,
            uncertain_policy="allow",
        )
        blocker._classification_service = mock_svc
        blocker._activity_logger = MagicMock()

        ctx = TabServerContext(
            health_provider=lambda: {"ok": True},
            tabs_provider=lambda: TabsSnapshot(tabs=[], browsers=[], generated_at=time.time()),
            command_handler=lambda req: CommandResult(success=True, action=req.action),
            blocking_checker=blocker.check_blocking,
        )
        return ctx, blocker, mock_svc

    return _factory


@patch("focus_guard.deployment.config.DeploymentConfig.load")
@pytest.mark.parametrize(
    "mode,expect_block",
    [
        ("enforcing", True),
        ("advisory", False),
        ("tracking", False),
    ],
)
def test_youtube_synthetic_entertainment_respects_enforcement_mode(
    mock_deploy, tab_ctx_with_blocker, mode: str, expect_block: bool
) -> None:
    url = "https://www.youtube.com/watch?v=synthetic_matrix_1"
    mock_deploy.return_value = MagicMock(enforcement_mode=mode)

    def classify_side_effect(domain: str, url_arg: str, context: dict):
        return _youtube_entertainment_result(url_arg)

    ctx, blocker, _ = tab_ctx_with_blocker(classify_side_effect)

    decision = ctx.check_blocking(url, "www.youtube.com", "Funny clips", 1)

    assert decision.classification is not None
    assert decision.classification.get("category") == "ENTERTAINMENT"
    assert decision.should_block is expect_block
    if expect_block:
        assert "ENTERTAINMENT" in (decision.reason or "") or "block" in (decision.reason or "").lower()
    elif mode == "advisory":
        assert decision.reason and "[ADVISORY]" in decision.reason
    else:
        assert decision.reason and "[TRACKING]" in decision.reason
    assert decision.enforcement_mode == mode

    blocker._activity_logger.log_block.assert_called_once()
    blocker._activity_logger.log_classification.assert_not_called()


@patch("focus_guard.deployment.config.DeploymentConfig.load")
@pytest.mark.parametrize("mode", ["enforcing", "advisory", "tracking"])
def test_google_synthetic_education_never_blocks(
    mock_deploy, tab_ctx_with_blocker, mode: str
) -> None:
    url = "https://www.google.com/search?q=calculus+tutorial&matrix=edu"
    mock_deploy.return_value = MagicMock(enforcement_mode=mode)

    def classify_side_effect(domain: str, url_arg: str, context: dict):
        assert "url" in context or url_arg
        return _google_education_result(url_arg)

    ctx, blocker, mock_svc = tab_ctx_with_blocker(classify_side_effect)

    decision = ctx.check_blocking(url, "www.google.com", "calculus tutorial - Google Search", 2)

    assert decision.should_block is False
    assert decision.classification is not None
    assert decision.classification.get("category") == "EDUCATION"
    mock_svc.classify_async.assert_awaited()
    blocker._activity_logger.log_classification.assert_called_once()
    blocker._activity_logger.log_block.assert_not_called()


@patch("focus_guard.deployment.config.DeploymentConfig.load")
@pytest.mark.parametrize(
    "mode,expect_block",
    [
        ("enforcing", True),
        ("advisory", False),
        ("tracking", False),
    ],
)
def test_google_synthetic_entertainment_query_enforcement_overlay(
    mock_deploy, tab_ctx_with_blocker, mode: str, expect_block: bool
) -> None:
    url = "https://www.google.com/search?q=movies+streaming&matrix=ent"
    mock_deploy.return_value = MagicMock(enforcement_mode=mode)

    def classify_side_effect(domain: str, url_arg: str, context: dict):
        return _google_entertainment_result(url_arg)

    ctx, _, _ = tab_ctx_with_blocker(classify_side_effect)
    decision = ctx.check_blocking(url, "www.google.com", "movies streaming - Google Search", 3)

    assert decision.classification is not None
    assert decision.classification.get("category") == "ENTERTAINMENT"
    assert decision.should_block is expect_block
    assert decision.enforcement_mode == mode


@patch("focus_guard.deployment.config.DeploymentConfig.load")
def test_classification_runs_before_enforcement_all_modes(
    mock_deploy, tab_ctx_with_blocker,
) -> None:
    """Same mock classifier: pipeline classification step runs; modes only change final flag."""

    url = "https://www.youtube.com/watch?v=synthetic_matrix_2"
    calls: list[tuple[str, str, dict]] = []

    def classify_side_effect(domain: str, url_arg: str, context: dict):
        calls.append((domain, url_arg, context))
        return _youtube_entertainment_result(url_arg)

    ctx, _, mock_svc = tab_ctx_with_blocker(classify_side_effect)

    for mode, expect in [("enforcing", True), ("advisory", False), ("tracking", False)]:
        calls.clear()
        mock_deploy.return_value = MagicMock(enforcement_mode=mode)
        decision = ctx.check_blocking(url, "www.youtube.com", "Test", 9)
        assert mock_svc.classify_async.await_count >= 1
        assert decision.classification.get("category") == "ENTERTAINMENT"
        assert decision.should_block is expect


@pytest.mark.usefixtures("pipeline_isolation")
@patch("focus_guard.deployment.config.DeploymentConfig.load")
def test_context_passed_to_classifier_matches_extension_query_params(mock_deploy, monkeypatch):
    """Mirrors GET /api/should_block: url, title, tab_id appear in classify context."""
    mock_deploy.return_value = MagicMock(enforcement_mode="tracking")

    captured: dict = {}

    async def classify_async(domain: str, url_arg: str, context: dict):
        captured.clear()
        captured.update(context)
        return _google_education_result(url_arg)

    mock_svc = MagicMock()
    mock_svc.classify_async = AsyncMock(side_effect=classify_async)

    blocker = ClassificationBlocker(
        blocked_categories={"ENTERTAINMENT"},
        escalate_uncertain_to_llm=False,
    )
    blocker._classification_service = mock_svc
    blocker._activity_logger = MagicMock()

    tctx = TabServerContext(
        health_provider=lambda: {"ok": True},
        tabs_provider=lambda: TabsSnapshot(tabs=[], browsers=[], generated_at=time.time()),
        command_handler=lambda req: CommandResult(success=True, action=req.action),
        blocking_checker=blocker.check_blocking,
    )
    u = "https://www.google.com/search?q=physics+problem&q_matrix=1"
    tctx.check_blocking(u, "www.google.com", "physics problem - Google Search", 42)

    assert captured.get("url") == u
    assert captured.get("title") == "physics problem - Google Search"
    assert captured.get("tab_id") == 42


@patch("focus_guard.deployment.config.DeploymentConfig.load")
@pytest.mark.parametrize("mode,prefix", [("advisory", "[ADVISORY]"), ("tracking", "[TRACKING]")])
def test_non_enforcing_modes_preserve_classification_and_response_contract(
    mock_deploy, tab_ctx_with_blocker, mode: str, prefix: str
) -> None:
    """When pipeline would block, advisory/tracking must still carry classification + mode in response dict."""
    url = "https://www.youtube.com/watch?v=synthetic_contract_1"
    mock_deploy.return_value = MagicMock(enforcement_mode=mode)

    def classify_side_effect(domain: str, url_arg: str, context: dict):
        return _youtube_entertainment_result(url_arg)

    ctx, _, _ = tab_ctx_with_blocker(classify_side_effect)
    decision = ctx.check_blocking(url, "www.youtube.com", "gaming montage", 10)
    payload = decision.to_dict()

    assert decision.should_block is False
    assert decision.classification is not None
    assert decision.classification.get("category") == "ENTERTAINMENT"
    assert decision.reason and prefix in decision.reason
    assert payload.get("should_block") is False
    assert payload.get("enforcement_mode") == mode
    assert isinstance(payload.get("classification"), dict)
    assert payload["classification"].get("category") == "ENTERTAINMENT"


@patch("focus_guard.deployment.config.DeploymentConfig.load")
def test_enforcing_mode_response_contains_rule_and_block_basis(
    mock_deploy, tab_ctx_with_blocker
) -> None:
    """Enforcing responses should include rule + block basis when classification policy blocks."""
    url = "https://www.google.com/search?q=movies+streaming+contract=1"
    mock_deploy.return_value = MagicMock(enforcement_mode="enforcing")

    def classify_side_effect(domain: str, url_arg: str, context: dict):
        return _google_entertainment_result(url_arg)

    ctx, _, _ = tab_ctx_with_blocker(classify_side_effect)
    decision = ctx.check_blocking(url, "www.google.com", "movies stream", 11)
    payload = decision.to_dict()

    assert decision.should_block is True
    assert payload.get("should_block") is True
    assert payload.get("enforcement_mode") == "enforcing"
    assert isinstance(payload.get("rule"), dict)
    assert payload["rule"].get("category") == "ENTERTAINMENT"
    assert isinstance(payload.get("classification"), dict)
    assert payload["classification"].get("block_basis") in {"category_rule", "distracting_content"}
