from __future__ import annotations

from datetime import datetime, timedelta

from focus_guard.core.browser_v2.tab_server.activity_logger import ActivityLogger


def test_get_activity_stats_with_since_includes_by_category_without_sql_error(tmp_path) -> None:
    db_path = tmp_path / "activity_log.db"
    logger = ActivityLogger(db_path=str(db_path))

    logger.log_classification(
        domain="www.youtube.com",
        url="https://www.youtube.com/watch?v=abc",
        title="video",
        classification_category="ENTERTAINMENT",
        classification_usefulness="DISTRACTION",
        classification_confidence=0.9,
        is_distracting=True,
        classifier_used="youtube_rule_based",
    )

    since = (datetime.now() - timedelta(minutes=1)).isoformat()
    stats = logger.get_activity_stats(since=since)

    assert isinstance(stats, dict)
    assert stats.get("total_events", 0) >= 1
    by_category = stats.get("by_category", {})
    assert isinstance(by_category, dict)
    assert by_category.get("ENTERTAINMENT", 0) >= 1
