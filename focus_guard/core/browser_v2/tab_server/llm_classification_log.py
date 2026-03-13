"""Persistent audit log for LLM classification decisions.

LLM-based classifications are the harder and more controversial decisions.
This module persists every LLM classification (and escalation) for greater
auditability, support, and future calibration.
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
    """Return FocusGuard data directory for SQLite (same pattern as saved_links)."""
    import os
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        path = Path(local_app) / "FocusGuard"
    else:
        path = Path.home() / ".focus_guard"
    path.mkdir(parents=True, exist_ok=True)
    return path


class LLMClassificationLog:
    """SQLite-backed audit log for LLM classification outcomes."""

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or (_get_data_dir() / "llm_classification_log.db")
        self._lock = threading.Lock()
        self._init_db()
        logger.info("LLMClassificationLog initialized at %s", self._db_path)

    def _init_db(self) -> None:
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS llm_classification_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp_utc REAL NOT NULL,
                        url TEXT NOT NULL,
                        domain TEXT NOT NULL,
                        title TEXT,
                        category TEXT NOT NULL,
                        usefulness TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        reason TEXT,
                        classifier_used TEXT NOT NULL,
                        is_distracting INTEGER NOT NULL DEFAULT 0,
                        content_type TEXT,
                        classification_time_ms REAL,
                        llm_escalation_attempted INTEGER DEFAULT 0,
                        llm_escalation_applied INTEGER DEFAULT 0,
                        request_context_json TEXT,
                        step_trace_json TEXT
                    )
                """)
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_llm_log_timestamp ON llm_classification_log(timestamp_utc)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_llm_log_domain ON llm_classification_log(domain)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_llm_log_category ON llm_classification_log(category)"
                )
                # Simple schema versioning for future migrations.
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

    def log(
        self,
        *,
        url: str,
        domain: str,
        title: str = "",
        category: str = "",
        usefulness: str = "",
        confidence: float = 0.0,
        reason: str = "",
        classifier_used: str = "",
        is_distracting: bool = False,
        content_type: str = "unknown",
        classification_time_ms: float = 0.0,
        llm_escalation_attempted: bool = False,
        llm_escalation_applied: bool = False,
        request_context: Optional[Dict[str, Any]] = None,
        step_trace: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Append one LLM classification record."""
        try:
            with self._lock:
                conn = sqlite3.connect(str(self._db_path))
                try:
                    conn.execute(
                        """
                        INSERT INTO llm_classification_log (
                            timestamp_utc, url, domain, title,
                            category, usefulness, confidence, reason, classifier_used,
                            is_distracting, content_type, classification_time_ms,
                            llm_escalation_attempted, llm_escalation_applied,
                            request_context_json, step_trace_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            time.time(),
                            url[:4096] if url else "",
                            domain[:512] if domain else "",
                            title[:1024] if title else "",
                            category or "",
                            usefulness or "",
                            confidence,
                            reason[:2048] if reason else "",
                            classifier_used or "llm",
                            1 if is_distracting else 0,
                            content_type or "unknown",
                            classification_time_ms,
                            1 if llm_escalation_attempted else 0,
                            1 if llm_escalation_applied else 0,
                            json.dumps(request_context)[:16384] if request_context else None,
                            json.dumps(step_trace)[:32768] if step_trace else None,
                        ),
                    )
                    conn.commit()
                finally:
                    conn.close()
        except Exception as e:
            logger.warning("Failed to write LLM classification log: %s", e)


_instance: Optional[LLMClassificationLog] = None


def get_llm_classification_log() -> LLMClassificationLog:
    global _instance
    if _instance is None:
        _instance = LLMClassificationLog()
    return _instance


def log_llm_classification(
    url: str,
    domain: str,
    result: Any,
    *,
    title: str = "",
    request_context: Optional[Dict[str, Any]] = None,
    step_trace: Optional[List[Dict[str, Any]]] = None,
    llm_escalation_attempted: bool = False,
    llm_escalation_applied: bool = False,
) -> None:
    """Convenience: persist one LLM classification from a ClassificationResult-like object."""
    usefulness = getattr(result, "usefulness", None)
    usefulness_str = usefulness.value if hasattr(usefulness, "value") else str(usefulness or "")
    get_llm_classification_log().log(
        url=url,
        domain=domain,
        title=title,
        category=getattr(result, "category", ""),
        usefulness=usefulness_str,
        confidence=getattr(result, "confidence", 0.0),
        reason=getattr(result, "reason", "") or "",
        classifier_used=getattr(result, "classifier_used", "llm"),
        is_distracting=getattr(result, "is_distracting", False),
        content_type=getattr(result, "content_type", "unknown"),
        classification_time_ms=getattr(result, "classification_time_ms", 0.0),
        llm_escalation_attempted=llm_escalation_attempted,
        llm_escalation_applied=llm_escalation_applied,
        request_context=request_context,
        step_trace=step_trace,
    )
