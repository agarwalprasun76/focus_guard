"""
Integration-style tests for enforcement modes on TabServerContext.check_blocking.

Run with pytest (collection runs tests; executing this file with ``python path/to/file.py`` does not):

    python -m pytest focus_guard/tests/integration/tab_server/test_enforcement_modes_tab_server.py -q

Or use ``python scripts/run_release_integration_tests.py``.

These tests pin the contract documented in server.TabServerContext.check_blocking:
TRACKING / ADVISORY must not surface should_block=True when the pipeline would
block under ENFORCING (reason is rewritten for audit).

Run as part of ``scripts/run_release_integration_tests.py`` before releases.
Expand with real ClassificationBlocker + temp domain_config as Day 8 Part B hardens.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from focus_guard.core.browser_v2.tab_server.api_models import (
    CommandRequest,
    CommandResult,
    TabsSnapshot,
)
from focus_guard.core.browser_v2.tab_server.blocking import BlockingDecision
from focus_guard.core.browser_v2.tab_server.server import TabServerContext


def _minimal_tab_context(blocking_checker):
    return TabServerContext(
        health_provider=lambda: {"ok": True},
        tabs_provider=lambda: TabsSnapshot(tabs=[], browsers=[], generated_at=time.time()),
        command_handler=lambda req: CommandResult(success=True, action=req.action),
        blocking_checker=blocking_checker,
    )


def _checker_always_blocks():
    def _fn(url: str, domain: str, title: str = "", tab_id=None):
        return BlockingDecision(should_block=True, reason="policy:test_block")

    return _fn


def _checker_always_allows():
    def _fn(url: str, domain: str, title: str = "", tab_id=None):
        return BlockingDecision(should_block=False, reason="allowed")

    return _fn


@pytest.mark.parametrize(
    "mode,expect_block,prefix",
    [
        ("enforcing", True, None),
        ("advisory", False, "[ADVISORY]"),
        ("tracking", False, "[TRACKING]"),
    ],
)
@patch("focus_guard.deployment.config.DeploymentConfig.load")
def test_enforcement_modes_when_pipeline_would_block(
    mock_load, mode: str, expect_block: bool, prefix: str | None
) -> None:
    mock_load.return_value = MagicMock(enforcement_mode=mode)
    ctx = _minimal_tab_context(_checker_always_blocks())
    decision = ctx.check_blocking("https://youtube.com/watch?v=1", "youtube.com", "Video", 1)

    assert decision.should_block is expect_block
    if expect_block:
        assert decision.reason == "policy:test_block"
    else:
        assert prefix and decision.reason and prefix in decision.reason
        assert "policy:test_block" in decision.reason


@pytest.mark.parametrize("mode", ["enforcing", "advisory", "tracking"])
@patch("focus_guard.deployment.config.DeploymentConfig.load")
def test_enforcement_modes_preserve_allow_when_pipeline_allows(mock_load, mode: str) -> None:
    mock_load.return_value = MagicMock(enforcement_mode=mode)
    ctx = _minimal_tab_context(_checker_always_allows())
    decision = ctx.check_blocking("https://example.org/", "example.org")

    assert decision.should_block is False
    assert decision.reason == "allowed"


@patch("focus_guard.deployment.config.DeploymentConfig.load")
def test_enforcement_load_failure_defaults_to_enforcing(mock_load) -> None:
    mock_load.side_effect = RuntimeError("no config")
    ctx = _minimal_tab_context(_checker_always_blocks())
    decision = ctx.check_blocking("https://blocked.test/", "blocked.test")

    assert decision.should_block is True
