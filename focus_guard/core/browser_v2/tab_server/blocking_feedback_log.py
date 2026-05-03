"""Feedback log for blocking decisions (4.1 Layer 1).

Stores user feedback about individual blocking decisions so that future
ingestion/learning layers can adjust rules and classification thresholds.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _get_data_dir() -> Path:
    """Return FocusGuard data directory for SQLite (same pattern as other logs)."""
    import os

    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        path = Path(local_app) / "FocusGuard"
    else:
        path = Path.home() / ".focus_guard"
    path.mkdir(parents=True, exist_ok=True)
    return path


class BlockingFeedbackLog:
    """SQLite-backed store for per-decision blocking feedback."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or (_get_data_dir() / "blocking_feedback_log.db")
        self._lock = threading.Lock()
        self._init_db()
        logger.info("BlockingFeedbackLog initialized at %s", self._db_path)

    def _init_db(self) -> None:
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS blocking_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at_utc REAL NOT NULL,
                        decision_id INTEGER,
                        url TEXT NOT NULL,
                        domain TEXT NOT NULL,
                        feedback_type TEXT NOT NULL,
                        source TEXT NOT NULL,
                        comment TEXT,
                        extra_json TEXT
                    )
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_bf_decision ON blocking_feedback(decision_id)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_bf_created_at ON blocking_feedback(created_at_utc)"
                )
                # Schema version table for simple migrations in the future.
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER NOT NULL
                    )
                    """
                )
                row = cur.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
                if row is None:
                    cur.execute("INSERT INTO schema_version (version) VALUES (1)")

                conn.commit()
            finally:
                conn.close()

    def write(
        self,
        *,
        url: str,
        domain: str,
        feedback_type: str,
        source: str,
        decision_id: Optional[int] = None,
        comment: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Append one feedback row. Returns feedback_id (row id) or None on failure."""
        try:
            extra_json = json.dumps(extra) if extra else None
            with self._lock:
                conn = sqlite3.connect(str(self._db_path))
                try:
                    cur = conn.execute(
                        """
                        INSERT INTO blocking_feedback (
                            created_at_utc,
                            decision_id,
                            url,
                            domain,
                            feedback_type,
                            source,
                            comment,
                            extra_json
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            time.time(),
                            decision_id,
                            url[:4096] if url else "",
                            domain[:512] if domain else "",
                            feedback_type[:64],
                            source[:64],
                            (comment or "")[:2048] if comment else None,
                            extra_json[:16384] if extra_json else None,
                        ),
                    )
                    conn.commit()
                    return cur.lastrowid
                finally:
                    conn.close()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to write blocking feedback: %s", exc)
            return None

    def list_recent(
        self,
        *,
        decision_id: Optional[int] = None,
        limit: int = 50,
    ) -> list[Dict[str, Any]]:
        """Return recent feedback rows, optionally filtered by decision_id."""
        safe_limit = max(1, min(int(limit), 200))
        query = (
            "SELECT id, created_at_utc, decision_id, url, domain, feedback_type, source, comment, extra_json "
            "FROM blocking_feedback"
        )
        args: list[Any] = []
        if decision_id is not None:
            query += " WHERE decision_id = ?"
            args.append(int(decision_id))
        query += " ORDER BY id DESC LIMIT ?"
        args.append(safe_limit)

        try:
            with self._lock:
                conn = sqlite3.connect(str(self._db_path))
                conn.row_factory = sqlite3.Row
                try:
                    rows = conn.execute(query, tuple(args)).fetchall()
                finally:
                    conn.close()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to list blocking feedback: %s", exc)
            return []

        out: list[Dict[str, Any]] = []
        for row in rows:
            extra_json = row["extra_json"]
            extra: Optional[Dict[str, Any]] = None
            if extra_json:
                try:
                    parsed = json.loads(extra_json)
                    if isinstance(parsed, dict):
                        extra = parsed
                except Exception:
                    extra = None

            out.append(
                {
                    "id": int(row["id"]),
                    "created_at_utc": float(row["created_at_utc"]),
                    "decision_id": int(row["decision_id"]) if row["decision_id"] is not None else None,
                    "url": row["url"],
                    "domain": row["domain"],
                    "feedback_type": row["feedback_type"],
                    "source": row["source"],
                    "comment": row["comment"],
                    "extra": extra,
                }
            )
        return out


_instance: Optional[BlockingFeedbackLog] = None


def get_blocking_feedback_log() -> BlockingFeedbackLog:
    global _instance
    if _instance is None:
        _instance = BlockingFeedbackLog()
    return _instance

