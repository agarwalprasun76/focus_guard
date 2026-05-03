"""Regression tests for override expiry and hourly email report period stats."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from focus_guard.core.browser_v2.tab_server.override_manager import ActiveOverride
from focus_guard.deployment.config import DeploymentConfig, ScheduleConfig
from focus_guard.deployment.email_reporter import EmailReporter
from focus_guard.main import _resolve_usage_db_path


def test_active_override_expires_at_granted_duration_boundary() -> None:
    """A 60s override should be considered expired at the 60s boundary."""
    override = ActiveOverride(
        id="ovr-1",
        domain="youtube.com",
        original_url="https://youtube.com/watch?v=abc",
        start_time=100.0,
        duration_seconds=60,
        browser="chrome",
        block_reason="blocked",
    )

    with patch("focus_guard.core.browser_v2.tab_server.override_manager.time.time", return_value=160.0):
        assert override.is_expired is True



def test_hourly_period_stats_include_overlapping_sessions(tmp_path: Path) -> None:
    """Hourly report stats should include sessions that overlap the window."""
    db_path = tmp_path / "usage.db"

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE usage_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                domain TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                active_duration REAL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            INSERT INTO usage_sessions (app_name, domain, start_time, end_time, active_duration)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "Chrome",
                "youtube.com",
                "2026-02-15 10:50:00",
                "2026-02-15 11:10:00",
                1200.0,
            ),
        )
        conn.commit()

    reporter = EmailReporter(DeploymentConfig())
    start_time = datetime(2026, 2, 15, 11, 0, 0)
    end_time = datetime(2026, 2, 15, 12, 0, 0)

    stats = reporter._get_period_stats(db_path, start_time, end_time)

    assert stats["sessions_count"] == 1
    assert stats["total_active_time"] == 1200.0
    assert stats["top_applications"]
    assert stats["top_domains"]


def test_hourly_period_stats_fallback_to_visible_windows_when_sessions_missing(tmp_path: Path) -> None:
    """Hourly stats should infer activity from visible windows when sessions are absent."""
    db_path = tmp_path / "usage.db"

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE usage_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                domain TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                active_duration REAL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE visible_windows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                window_title TEXT,
                is_foreground BOOLEAN DEFAULT 0,
                screen_percent REAL DEFAULT 0,
                timestamp TIMESTAMP NOT NULL
            )
            """
        )

        # No usage_sessions rows in period; only visible foreground samples.
        conn.executemany(
            """
            INSERT INTO visible_windows (app_name, window_title, is_foreground, screen_percent, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("Code.exe", "editor", 1, 80.0, "2026-02-15 11:10:00"),
                ("Code.exe", "editor", 1, 82.0, "2026-02-15 11:10:05"),
                ("msedge.exe", "docs", 1, 70.0, "2026-02-15 11:10:10"),
            ],
        )
        conn.commit()

    config = DeploymentConfig()
    config.monitoring.sampling_interval = 5
    reporter = EmailReporter(config)
    start_time = datetime(2026, 2, 15, 11, 0, 0)
    end_time = datetime(2026, 2, 15, 12, 0, 0)

    stats = reporter._get_period_stats(db_path, start_time, end_time)

    # 3 foreground samples * 5 seconds interval = 15 seconds total active.
    assert stats["sessions_count"] == 1
    assert stats["total_active_time"] == 15.0
    assert stats["top_applications"]
    assert stats["top_applications"][0]["app_name"] == "Code.exe"


def test_resolve_usage_db_path_prefers_configured_path_when_valid(tmp_path: Path, monkeypatch) -> None:
    configured_dir = tmp_path / "programdata"
    local_dir = tmp_path / "localapp"
    configured_db = configured_dir / "usage.db"
    local_db = local_dir / "FocusGuard" / "usage.db"

    configured_dir.mkdir(parents=True, exist_ok=True)
    local_db.parent.mkdir(parents=True, exist_ok=True)

    for db in (configured_db, local_db):
        with sqlite3.connect(str(db)) as conn:
            conn.execute("CREATE TABLE usage_sessions (id INTEGER PRIMARY KEY)")

    monkeypatch.setenv("LOCALAPPDATA", str(local_dir))

    class _Storage:
        def get_data_directory(self) -> Path:
            return configured_dir

    config = SimpleNamespace(storage=_Storage())
    resolved = _resolve_usage_db_path(config)
    assert resolved == configured_db


def test_resolve_usage_db_path_prefers_localappdata_when_it_has_recent_activity(tmp_path: Path, monkeypatch) -> None:
    configured_dir = tmp_path / "programdata"
    local_dir = tmp_path / "localapp"
    configured_db = configured_dir / "usage.db"
    local_db = local_dir / "FocusGuard" / "usage.db"

    configured_dir.mkdir(parents=True, exist_ok=True)
    local_db.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(configured_db)) as conn:
        conn.execute(
            """
            CREATE TABLE usage_sessions (
                id INTEGER PRIMARY KEY,
                start_time TIMESTAMP,
                end_time TIMESTAMP
            )
            """
        )

    with sqlite3.connect(str(local_db)) as conn:
        conn.execute(
            """
            CREATE TABLE usage_sessions (
                id INTEGER PRIMARY KEY,
                start_time TIMESTAMP,
                end_time TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            INSERT INTO usage_sessions (start_time, end_time)
            VALUES (datetime('now', '-30 minutes'), datetime('now', '-25 minutes'))
            """
        )

    monkeypatch.setenv("LOCALAPPDATA", str(local_dir))

    class _Storage:
        def get_data_directory(self) -> Path:
            return configured_dir

    config = SimpleNamespace(storage=_Storage())
    resolved = _resolve_usage_db_path(config)
    assert resolved == local_db


def test_resolve_usage_db_path_falls_back_to_localappdata_when_config_invalid(tmp_path: Path, monkeypatch) -> None:
    configured_dir = tmp_path / "programdata"
    local_dir = tmp_path / "localapp"
    configured_db = configured_dir / "usage.db"
    local_db = local_dir / "FocusGuard" / "usage.db"

    configured_dir.mkdir(parents=True, exist_ok=True)
    local_db.parent.mkdir(parents=True, exist_ok=True)

    # Invalid configured DB (exists but no usage_sessions table)
    with sqlite3.connect(str(configured_db)) as conn:
        conn.execute("CREATE TABLE something_else (id INTEGER PRIMARY KEY)")

    with sqlite3.connect(str(local_db)) as conn:
        conn.execute("CREATE TABLE usage_sessions (id INTEGER PRIMARY KEY)")

    monkeypatch.setenv("LOCALAPPDATA", str(local_dir))

    class _Storage:
        def get_data_directory(self) -> Path:
            return configured_dir

    config = SimpleNamespace(storage=_Storage())
    resolved = _resolve_usage_db_path(config)
    assert resolved == local_db


def test_schedule_interval_minutes_preferred_over_hours() -> None:
    schedule = ScheduleConfig(hourly_interval_minutes=5, hourly_interval_hours=4)
    assert schedule.get_hourly_interval_minutes() == 5


def test_schedule_interval_falls_back_to_hours_when_minutes_missing() -> None:
    schedule = ScheduleConfig(hourly_interval_minutes=0, hourly_interval_hours=2)
    assert schedule.get_hourly_interval_minutes() == 120


def test_send_hourly_report_uses_schedule_interval_minutes(tmp_path: Path) -> None:
    """Hourly email should query exactly the configured minute window (e.g., 5 min)."""
    db_path = tmp_path / "usage.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE usage_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                domain TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                active_duration REAL DEFAULT 0
            )
            """
        )

    config = DeploymentConfig()
    config.reporting.schedule.hourly_interval_minutes = 5
    config.email.enabled = True
    config.email.smtp_username = "user@example.com"
    config.email.smtp_password = "app-password"
    config.email.sender_email = "focusguard@example.com"
    config.email.recipients = ["parent@example.com"]
    reporter = EmailReporter(config)

    observed = {}

    def _fake_get_period_stats(_db_path: Path, start_time: datetime, end_time: datetime):
        observed["start_time"] = start_time
        observed["end_time"] = end_time
        return {
            "sessions_count": 0,
            "total_active_time": 0.0,
            "top_applications": [],
            "top_domains": [],
        }

    reporter._get_period_stats = _fake_get_period_stats  # type: ignore[method-assign]
    reporter._send_email = lambda *_args, **_kwargs: True  # type: ignore[method-assign]

    assert reporter.send_hourly_report(db_path) is True

    interval = (observed["end_time"] - observed["start_time"]).total_seconds()
    assert 299 <= interval <= 301


def test_hourly_fallback_uses_visible_windows_when_sessions_have_zero_active_time(tmp_path: Path) -> None:
    """Open sessions with zero stored active_duration should use overlap estimation."""
    db_path = tmp_path / "usage.db"

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE usage_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                domain TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                active_duration REAL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE visible_windows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                window_title TEXT,
                is_foreground BOOLEAN DEFAULT 0,
                screen_percent REAL DEFAULT 0,
                timestamp TIMESTAMP NOT NULL
            )
            """
        )

        # Session overlaps report period but contributes zero active duration.
        conn.execute(
            """
            INSERT INTO usage_sessions (app_name, domain, start_time, end_time, active_duration)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("Code.exe", None, "2026-02-15 11:00:00", "2026-02-15 11:20:00", 0.0),
        )
        conn.executemany(
            """
            INSERT INTO visible_windows (app_name, window_title, is_foreground, screen_percent, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("Code.exe", "editor", 1, 85.0, "2026-02-15 11:10:00"),
                ("Code.exe", "editor", 1, 86.0, "2026-02-15 11:10:05"),
            ],
        )
        conn.commit()

    config = DeploymentConfig()
    config.monitoring.sampling_interval = 5
    reporter = EmailReporter(config)

    stats = reporter._get_period_stats(
        db_path,
        datetime(2026, 2, 15, 11, 0, 0),
        datetime(2026, 2, 15, 12, 0, 0),
    )

    assert stats["sessions_count"] >= 1
    # Overlap estimate from 11:00 to 11:20 => 1200 seconds.
    assert stats["total_active_time"] == 1200.0
    assert stats["top_applications"]


def test_hourly_period_stats_prefers_activity_samples_when_available(tmp_path: Path) -> None:
    """Samples should be the primary source for ad-hoc interval totals when present."""
    db_path = tmp_path / "usage.db"

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE usage_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                domain TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                active_duration REAL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE activity_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                window_title TEXT,
                domain TEXT,
                url TEXT,
                is_foreground BOOLEAN DEFAULT 1,
                sample_seconds REAL NOT NULL,
                timestamp TIMESTAMP NOT NULL
            )
            """
        )

        # Existing sessions should not override the sample-first interval total.
        conn.execute(
            """
            INSERT INTO usage_sessions (app_name, domain, start_time, end_time, active_duration)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("Code.exe", None, "2026-02-15 11:00:00", "2026-02-15 11:20:00", 1200.0),
        )
        conn.executemany(
            """
            INSERT INTO activity_samples (app_name, window_title, domain, url, is_foreground, sample_seconds, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("Code.exe", "editor", None, None, 1, 5.0, "2026-02-15 11:10:00"),
                ("msedge.exe", "docs", "example.com", "https://example.com", 1, 5.0, "2026-02-15 11:10:05"),
                ("msedge.exe", "docs", "example.com", "https://example.com", 1, 5.0, "2026-02-15 11:10:10"),
            ],
        )
        conn.commit()

    config = DeploymentConfig()
    reporter = EmailReporter(config)

    stats = reporter._get_period_stats(
        db_path,
        datetime(2026, 2, 15, 11, 0, 0),
        datetime(2026, 2, 15, 12, 0, 0),
    )

    assert stats["total_active_time"] == 15.0
    assert stats["top_applications"][0]["app_name"] == "msedge.exe"
    assert stats["top_domains"][0]["domain"] == "example.com"


def test_hourly_fallback_uses_visible_windows_when_activity_samples_empty(tmp_path: Path) -> None:
    """With empty samples, overlap-estimated session time remains authoritative."""
    db_path = tmp_path / "usage.db"

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE usage_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                domain TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                active_duration REAL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE activity_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                window_title TEXT,
                domain TEXT,
                url TEXT,
                is_foreground BOOLEAN DEFAULT 1,
                sample_seconds REAL NOT NULL,
                timestamp TIMESTAMP NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE visible_windows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                window_title TEXT,
                is_foreground BOOLEAN DEFAULT 0,
                screen_percent REAL DEFAULT 0,
                timestamp TIMESTAMP NOT NULL
            )
            """
        )

        # Overlapping session has no active duration; activity_samples table exists but is empty.
        conn.execute(
            """
            INSERT INTO usage_sessions (app_name, domain, start_time, end_time, active_duration)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("Code.exe", None, "2026-02-15 11:00:00", "2026-02-15 11:20:00", 0.0),
        )

        conn.executemany(
            """
            INSERT INTO visible_windows (app_name, window_title, is_foreground, screen_percent, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("Code.exe", "editor", 1, 80.0, "2026-02-15 11:10:00"),
                ("Code.exe", "editor", 1, 82.0, "2026-02-15 11:10:05"),
                ("msedge.exe", "docs", 1, 70.0, "2026-02-15 11:10:10"),
            ],
        )
        conn.commit()

    config = DeploymentConfig()
    config.monitoring.sampling_interval = 5
    reporter = EmailReporter(config)

    stats = reporter._get_period_stats(
        db_path,
        datetime(2026, 2, 15, 11, 0, 0),
        datetime(2026, 2, 15, 12, 0, 0),
    )

    # Overlap estimate from 11:00 to 11:20 => 1200 seconds.
    assert stats["total_active_time"] == 1200.0
    assert stats["top_applications"]
    assert stats["top_applications"][0]["app_name"] == "Code.exe"


def test_daily_report_sends_with_fallback_stats_when_daily_stats_fail(tmp_path: Path) -> None:
    """Daily report should still send using fallback stats when DB stats retrieval fails."""
    db_path = tmp_path / "usage.db"
    db_path.write_text("")

    config = DeploymentConfig()
    config.email.enabled = True
    config.email.smtp_username = "user@example.com"
    config.email.smtp_password = "app-password"
    config.email.sender_email = "focusguard@example.com"
    config.email.recipients = ["parent@example.com"]

    reporter = EmailReporter(config)
    reporter._get_daily_stats = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("db unavailable"))  # type: ignore[method-assign]
    reporter._send_email = lambda *_args, **_kwargs: True  # type: ignore[method-assign]

    assert reporter.send_daily_report(db_path, date="2026-02-15") is True


def test_generate_daily_report_html_handles_sparse_stats() -> None:
    """Daily report HTML generation should not require every stats key."""
    reporter = EmailReporter(DeploymentConfig())

    html = reporter._generate_daily_report_html({"total_active_time": 0}, "2026-02-15")

    assert "Daily Summary" in html
    assert "Total Sessions" in html
