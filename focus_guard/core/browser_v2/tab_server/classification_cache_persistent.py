"""Persistent classification cache (4.2).

SQLite-backed cache for classification results. Survives restarts, supports
more entries than in-memory cache. Invalidate on config change via
invalidate_all() (or future invalidate_since(version)).
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
    import os
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        path = Path(local_app) / "FocusGuard"
    else:
        path = Path.home() / ".focus_guard"
    path.mkdir(parents=True, exist_ok=True)
    return path


class PersistentClassificationCache:
    """SQLite cache: cache_key -> result JSON, with TTL."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        ttl_seconds: float = 300.0,
        max_entries: int = 2000,
    ):
        self._db_path = db_path or (_get_data_dir() / "classification_cache.db")
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._init_db()
        logger.info("PersistentClassificationCache at %s (ttl=%.0fs)", self._db_path, self._ttl)

    def _init_db(self) -> None:
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS classification_cache (
                        cache_key TEXT PRIMARY KEY,
                        result_json TEXT NOT NULL,
                        stored_at REAL NOT NULL
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_stored_at ON classification_cache(stored_at)")

                # Simple schema version table so future migrations can evolve the cache.
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

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Return cached result dict (from ClassificationResult.to_dict()) or None if miss/expired."""
        if not cache_key:
            return None
        try:
            with self._lock:
                conn = sqlite3.connect(str(self._db_path))
                try:
                    row = conn.execute(
                        "SELECT result_json, stored_at FROM classification_cache WHERE cache_key = ?",
                        (cache_key[:1024],),
                    ).fetchone()
                    if row is None:
                        return None
                    result_json, stored_at = row
                    if time.time() - stored_at > self._ttl:
                        conn.execute("DELETE FROM classification_cache WHERE cache_key = ?", (cache_key[:1024],))
                        conn.commit()
                        return None
                    return json.loads(result_json)
                finally:
                    conn.close()
        except Exception as e:
            logger.debug("Persistent cache get failed: %s", e)
            return None

    def set(self, cache_key: str, result_dict: Dict[str, Any]) -> None:
        """Store result dict (e.g. from ClassificationResult.to_dict())."""
        if not cache_key:
            return
        try:
            result_json = json.dumps(result_dict)
            with self._lock:
                conn = sqlite3.connect(str(self._db_path))
                try:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO classification_cache (cache_key, result_json, stored_at)
                        VALUES (?, ?, ?)
                        """,
                        (cache_key[:1024], result_json, time.time()),
                    )
                    n = conn.execute("SELECT COUNT(*) FROM classification_cache").fetchone()[0]
                    if n > self._max_entries:
                        to_remove = n - self._max_entries
                        conn.execute(
                            """
                            DELETE FROM classification_cache WHERE cache_key IN (
                                SELECT cache_key FROM classification_cache ORDER BY stored_at ASC
                                LIMIT ?
                            )
                            """,
                            (to_remove,),
                        )
                    conn.commit()
                finally:
                    conn.close()
        except Exception as e:
            logger.debug("Persistent cache set failed: %s", e)

    def invalidate_all(self) -> None:
        """Clear all entries. Call on domain/config change when needed."""
        try:
            with self._lock:
                conn = sqlite3.connect(str(self._db_path))
                try:
                    conn.execute("DELETE FROM classification_cache")
                    conn.commit()
                    logger.info("Persistent classification cache invalidated")
                finally:
                    conn.close()
        except Exception as e:
            logger.warning("Failed to invalidate persistent classification cache: %s", e)


_instance: Optional[PersistentClassificationCache] = None


def get_persistent_classification_cache() -> PersistentClassificationCache:
    global _instance
    if _instance is None:
        _instance = PersistentClassificationCache()
    return _instance
