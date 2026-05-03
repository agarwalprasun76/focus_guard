"""Tests for blocking feedback persistence and retrieval."""

import sqlite3

from focus_guard.core.browser_v2.tab_server.blocking_feedback_log import BlockingFeedbackLog


class TestBlockingFeedbackLog:
    def test_write_and_list_recent(self, tmp_path):
        db_path = tmp_path / "feedback.db"
        log = BlockingFeedbackLog(db_path=db_path)

        first_id = log.write(
            url="https://example.com/video",
            domain="example.com",
            feedback_type="blocked_should_be_allowed",
            source="blocked_page",
            decision_id=10,
            comment="This was study content",
            extra={"category": "EDUCATION"},
        )
        second_id = log.write(
            url="https://example.com/social",
            domain="example.com",
            feedback_type="allowed_should_be_blocked",
            source="admin_ui",
            decision_id=11,
            comment=None,
            extra=None,
        )

        assert first_id is not None
        assert second_id is not None

        rows = log.list_recent(limit=10)
        assert len(rows) == 2
        assert rows[0]["id"] == second_id
        assert rows[1]["id"] == first_id
        assert rows[1]["extra"] == {"category": "EDUCATION"}

    def test_list_recent_filters_by_decision_id(self, tmp_path):
        db_path = tmp_path / "feedback_filter.db"
        log = BlockingFeedbackLog(db_path=db_path)

        log.write(
            url="https://a.example/",
            domain="a.example",
            feedback_type="other",
            source="api",
            decision_id=100,
        )
        log.write(
            url="https://b.example/",
            domain="b.example",
            feedback_type="other",
            source="api",
            decision_id=200,
        )

        rows = log.list_recent(decision_id=100, limit=10)
        assert len(rows) == 1
        assert rows[0]["decision_id"] == 100
        assert rows[0]["domain"] == "a.example"

    def test_schema_version_created(self, tmp_path):
        db_path = tmp_path / "feedback_schema.db"
        BlockingFeedbackLog(db_path=db_path)

        with sqlite3.connect(str(db_path)) as conn:
            row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        assert row is not None
        assert row[0] == 1

