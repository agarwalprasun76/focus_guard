"""Tests for LLM classification audit log."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from focus_guard.core.browser_v2.tab_server.llm_classification_log import (
    LLMClassificationLog,
    log_llm_classification,
)


class TestLLMClassificationLog:
    def test_log_and_read(self, tmp_path):
        """Log one LLM classification and verify it is persisted."""
        db_path = tmp_path / "llm_log.db"
        log = LLMClassificationLog(db_path=db_path)
        log.log(
            url="https://example.com/video",
            domain="example.com",
            title="Test",
            category="EDUCATION",
            usefulness="EDUCATIONAL",
            confidence=0.9,
            reason="Educational content",
            classifier_used="llm",
            is_distracting=False,
            llm_escalation_attempted=True,
            llm_escalation_applied=True,
            request_context={"title": "Test"},
        )
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT url, domain, category, usefulness, confidence, classifier_used, "
                "llm_cost_usd, prompt_tokens, completion_tokens, total_tokens, "
                "llm_escalation_attempted, llm_escalation_applied FROM llm_classification_log LIMIT 1"
            ).fetchone()
        assert row is not None
        assert row["url"] == "https://example.com/video"
        assert row["domain"] == "example.com"
        assert row["category"] == "EDUCATION"
        assert row["confidence"] == 0.9
        assert row["llm_cost_usd"] is None
        assert row["prompt_tokens"] is None
        assert row["llm_escalation_attempted"] == 1
        assert row["llm_escalation_applied"] == 1

    def test_log_llm_classification_convenience(self, tmp_path, monkeypatch):
        """log_llm_classification() accepts a result-like object and writes via singleton."""
        db_path = tmp_path / "conv.db"
        log = LLMClassificationLog(db_path=db_path)
        monkeypatch.setattr(
            "focus_guard.core.browser_v2.tab_server.llm_classification_log._instance",
            log,
        )
        class FakeResult:
            category = "ENTERTAINMENT"
            usefulness = type("Usefulness", (), {"value": "DISTRACTION"})()
            confidence = 0.85
            reason = "Streaming content"
            classifier_used = "llm"
            is_distracting = True
            content_type = "video"
            classification_time_ms = 120.0
            metadata = {
                "llm_cost_usd": 0.0123,
                "prompt_tokens": 321,
                "completion_tokens": 44,
                "total_tokens": 365,
            }

        log_llm_classification(
            url="https://stream.com/",
            domain="stream.com",
            result=FakeResult(),
            title="Stream",
            llm_escalation_attempted=False,
            llm_escalation_applied=False,
        )
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT llm_cost_usd, prompt_tokens, completion_tokens, total_tokens "
                "FROM llm_classification_log LIMIT 1"
            ).fetchone()
        assert row is not None
        assert row["llm_cost_usd"] == pytest.approx(0.0123)
        assert row["prompt_tokens"] == 321
        assert row["completion_tokens"] == 44
        assert row["total_tokens"] == 365
