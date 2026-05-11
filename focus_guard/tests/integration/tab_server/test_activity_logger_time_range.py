"""ActivityLogger UTC range queries (Day 10): calendar windows, empty ranges, legacy timestamps."""

from __future__ import annotations

import sqlite3

from focus_guard.core.browser_v2.tab_server.activity_logger import ActivityLogger


def _set_ts(db_path: str, row_id: int, ts: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE activity_log SET timestamp = ? WHERE id = ?", (ts, row_id))


def test_calendar_range_counts_only_matching_utc_days(tmp_path) -> None:
    db_path = tmp_path / "a.db"
    logger = ActivityLogger(db_path=str(db_path))
    r_inside = logger.log_visit(domain="in.example", url="https://in.example/", title="")
    r_before = logger.log_visit(domain="bf.example", url="https://bf.example/", title="")
    r_after = logger.log_visit(domain="af.example", url="https://af.example/", title="")
    assert r_inside is not None and r_before is not None and r_after is not None

    _set_ts(str(db_path), r_before, "2026-05-09T23:59:59Z")
    _set_ts(str(db_path), r_inside, "2026-05-10T12:00:00Z")
    _set_ts(str(db_path), r_after, "2026-05-11T00:00:00Z")

    stats = logger.get_activity_stats(start_date="2026-05-10", end_date="2026-05-10")
    assert stats["total_events"] == 1
    assert stats["blocked_count"] == 0
    q = stats["query"]
    assert q["since"] == "2026-05-10T00:00:00Z"
    assert q["until_exclusive"] == "2026-05-11T00:00:00Z"
    assert q["range_swapped"] is False

    entries = logger.get_recent_activity(
        limit=50,
        start_date="2026-05-10",
        end_date="2026-05-10",
    )
    assert len(entries) == 1
    assert entries[0].domain == "in.example"


def test_empty_range_returns_zeros_with_query_meta(tmp_path) -> None:
    db_path = tmp_path / "b.db"
    logger = ActivityLogger(db_path=str(db_path))
    rid = logger.log_visit(domain="x.example", url="https://x.example/", title="")
    assert rid is not None
    _set_ts(str(db_path), rid, "2020-01-01T12:00:00Z")

    stats = logger.get_activity_stats(start_date="2030-01-01", end_date="2030-01-07")
    assert stats["total_events"] == 0
    assert stats["blocked_percentage"] == 0
    assert stats["query"]["until_exclusive"] == "2030-01-08T00:00:00Z"


def test_swapped_start_end_dates_are_normalized(tmp_path) -> None:
    db_path = tmp_path / "c.db"
    logger = ActivityLogger(db_path=str(db_path))
    stats = logger.get_activity_stats(start_date="2026-05-03", end_date="2026-05-01")
    assert stats["query"]["range_swapped"] is True
    assert stats["query"]["since"] == "2026-05-01T00:00:00Z"
    assert stats["query"]["until_exclusive"] == "2026-05-04T00:00:00Z"


def test_since_until_half_open_legacy_space_timestamp(tmp_path) -> None:
    db_path = tmp_path / "d.db"
    logger = ActivityLogger(db_path=str(db_path))
    rid = logger.log_visit(domain="leg.example", url="https://leg.example/", title="")
    assert rid is not None
    _set_ts(str(db_path), rid, "2026-06-01 14:30:45")

    stats = logger.get_activity_stats(since="2026-06-01", until="2026-06-02")
    assert stats["total_events"] == 1
    counts = logger.get_recent_activity(limit=10, since="2026-06-01", until="2026-06-02")
    assert len(counts) == 1
