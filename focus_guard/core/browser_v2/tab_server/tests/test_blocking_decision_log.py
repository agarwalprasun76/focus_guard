"""Tests for blocking decision log (4.3)."""

import json
import sqlite3

import pytest

from focus_guard.core.browser_v2.tab_server.blocking_decision_log import (
    BlockingDecisionLog,
    step_trace_to_json_safe,
    get_blocking_decision_log,
)
from focus_guard.core.browser_v2.tab_server.blocking_pipeline import StepTraceEntry


class TestStepTraceToJsonSafe:
    def test_serializes_trace(self):
        trace = [
            StepTraceEntry(step_name="always_allowed_domain", terminal=True, should_block=False, reason="allowed", details={"classification": {"category": "EDUCATION"}}),
        ]
        out = step_trace_to_json_safe(trace)
        assert len(out) == 1
        assert out[0]["step_name"] == "always_allowed_domain"
        assert out[0]["terminal"] is True
        assert out[0]["details"]["classification"]["category"] == "EDUCATION"


class TestBlockingDecisionLog:
    def test_write_and_read(self, tmp_path):
        db = BlockingDecisionLog(db_path=tmp_path / "bdl.db")
        trace = [{"step_name": "policy", "terminal": True, "should_block": True, "reason": "blocked", "details": {}}]
        row_id = db.write(
            url="https://example.com/",
            domain="example.com",
            final_decision="block",
            reason="Category ENTERTAINMENT is blocked",
            step_trace=trace,
            classification_snapshot={"category": "ENTERTAINMENT", "confidence": 0.9},
            latency_ms=12.5,
        )
        assert row_id is not None
        with sqlite3.connect(str(tmp_path / "bdl.db")) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT url, domain, final_decision, reason, step_trace_json, classification_snapshot_json, latency_ms FROM blocking_decision_log WHERE id = ?",
                (row_id,),
            ).fetchone()
        assert row["url"] == "https://example.com/"
        assert row["final_decision"] == "block"
        assert row["latency_ms"] == 12.5
        step_trace = json.loads(row["step_trace_json"])
        assert step_trace[0]["step_name"] == "policy"
        snap = json.loads(row["classification_snapshot_json"])
        assert snap["category"] == "ENTERTAINMENT"

    def test_exists_checks_row_presence(self, tmp_path):
        db = BlockingDecisionLog(db_path=tmp_path / "bdl_exists.db")
        row_id = db.write(
            url="https://exists.example/",
            domain="exists.example",
            final_decision="allow",
            reason="allowed",
            step_trace=[{"step_name": "policy", "terminal": True, "should_block": False, "reason": "", "details": {}}],
            classification_snapshot={"category": "PRODUCTIVITY"},
            latency_ms=5.0,
        )
        assert row_id is not None
        assert db.exists(row_id) is True
        assert db.exists(999999) is False
        assert db.exists(0) is False
