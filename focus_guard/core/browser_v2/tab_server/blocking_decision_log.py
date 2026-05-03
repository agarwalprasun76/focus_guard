"""Persistent audit log for every blocking decision (4.3).

One row per pipeline run: url, domain, final_decision, reason, step_trace (JSON),
optional classification_snapshot and latency_ms. Enables "why was this blocked?"
and feedback linkage via decision_id.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_data_dir() -> Path:
    """Same pattern as llm_classification_log / saved_links."""
    import os
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        path = Path(local_app) / "FocusGuard"
    else:
        path = Path.home() / ".focus_guard"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _serialize_rule(rule: Any) -> Optional[Dict[str, Any]]:
    if rule is None:
        return None
    if hasattr(rule, "domain"):
        return {"domain": getattr(rule, "domain", ""), "reason": getattr(rule, "reason", ""), "category": getattr(rule, "category")}
    return None


def step_trace_to_json_safe(trace: List[Any]) -> List[Dict[str, Any]]:
    """Convert step trace (StepTraceEntry list) to JSON-serializable list of dicts."""
    out = []
    for entry in trace:
        d = {
            "step_name": getattr(entry, "step_name", ""),
            "terminal": getattr(entry, "terminal", False),
            "should_block": getattr(entry, "should_block", False),
            "reason": getattr(entry, "reason", None),
            "details": {},
        }
        details = getattr(entry, "details", {}) or {}
        if "rule" in details and details["rule"] is not None:
            d["details"]["rule"] = _serialize_rule(details["rule"])
        if "classification" in details and details["classification"] is not None:
            d["details"]["classification"] = details["classification"]
        if "budget_status" in details and details["budget_status"] is not None:
            d["details"]["budget_status"] = details["budget_status"]
        out.append(d)
    return out


class BlockingDecisionLog:
    """SQLite-backed log: one row per blocking pipeline run."""

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or (_get_data_dir() / "blocking_decision_log.db")
        self._lock = threading.Lock()
        self._init_db()
        logger.info("BlockingDecisionLog initialized at %s", self._db_path)

    def _init_db(self) -> None:
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS blocking_decision_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp_utc REAL NOT NULL,
                        url TEXT NOT NULL,
                        domain TEXT NOT NULL,
                        final_decision TEXT NOT NULL,
                        reason TEXT,
                        step_trace_json TEXT NOT NULL,
                        classification_snapshot_json TEXT,
                        latency_ms REAL
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_bdl_timestamp ON blocking_decision_log(timestamp_utc)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_bdl_domain ON blocking_decision_log(domain)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_bdl_final_decision ON blocking_decision_log(final_decision)")

                # Simple schema versioning: single-row schema_version table.
                # Future migrations can inspect and bump this value.
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
        final_decision: str,
        reason: Optional[str] = None,
        step_trace: List[Dict[str, Any]],
        classification_snapshot: Optional[Dict[str, Any]] = None,
        latency_ms: Optional[float] = None,
    ) -> Optional[int]:
        """Append one decision record. Returns decision_id (row id) or None on failure."""
        try:
            step_trace_json = json.dumps(step_trace)
            class_snap_json = json.dumps(classification_snapshot) if classification_snapshot else None
            with self._lock:
                conn = sqlite3.connect(str(self._db_path))
                try:
                    cur = conn.execute(
                        """
                        INSERT INTO blocking_decision_log (
                            timestamp_utc, url, domain, final_decision, reason,
                            step_trace_json, classification_snapshot_json, latency_ms
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            time.time(),
                            url[:4096] if url else "",
                            domain[:512] if domain else "",
                            final_decision,
                            reason[:2048] if reason else None,
                            step_trace_json[:65536],
                            class_snap_json[:32768] if class_snap_json else None,
                            latency_ms,
                        ),
                    )
                    conn.commit()
                    return cur.lastrowid
                finally:
                    conn.close()
        except Exception as e:
            logger.warning("Failed to write blocking decision log: %s", e)
            return None

    def exists(self, decision_id: int) -> bool:
        """Return True when a decision row exists for the given id."""
        if decision_id <= 0:
            return False
        try:
            with self._lock:
                conn = sqlite3.connect(str(self._db_path))
                try:
                    row = conn.execute(
                        "SELECT 1 FROM blocking_decision_log WHERE id = ? LIMIT 1",
                        (decision_id,),
                    ).fetchone()
                    return row is not None
                finally:
                    conn.close()
        except Exception as e:
            logger.warning("Failed to check blocking decision existence: %s", e)
            return False


_instance: Optional[BlockingDecisionLog] = None


def get_blocking_decision_log() -> BlockingDecisionLog:
    global _instance
    if _instance is None:
        _instance = BlockingDecisionLog()
    return _instance
