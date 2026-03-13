"""Saved Links Module — stores blocked URLs for later viewing.

When a site is blocked during a focus session, the user can choose to
"Save for Later". The URL, timestamp, and an optional comment are stored
in a local SQLite database. During break time, the user can browse their
saved links from the dashboard or extension popup.
"""

import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data directory helper
# ---------------------------------------------------------------------------

def _get_data_dir() -> Path:
    """Return a user-writable FocusGuard data directory for SQLite databases.

    Uses ``%LOCALAPPDATA%\\FocusGuard`` (e.g. ``AppData\\Local\\FocusGuard``)
    because both ``C:\\ProgramData\\FocusGuard`` and ``~\\.focus_guard``
    may lack the Delete permission that SQLite needs for journal file
    cleanup, causing persistent "disk I/O error" failures.
    ``%LOCALAPPDATA%`` is always fully writable by the current user.
    """
    import os
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        path = Path(local_app) / "FocusGuard"
    else:
        # Fallback for non-Windows or missing env var
        path = Path.home() / ".focus_guard"
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SavedLink:
    """A single saved link entry."""
    id: int = 0
    url: str = ""
    domain: str = ""
    title: str = ""
    category: str = ""
    comment: str = ""
    saved_at: str = ""
    viewed: bool = False
    viewed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "domain": self.domain,
            "title": self.title,
            "category": self.category,
            "comment": self.comment,
            "saved_at": self.saved_at,
            "viewed": self.viewed,
            "viewed_at": self.viewed_at,
        }


# ---------------------------------------------------------------------------
# SavedLinksStore
# ---------------------------------------------------------------------------

class SavedLinksStore:
    """SQLite-backed store for saved blocked links."""

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or (_get_data_dir() / "saved_links.db")
        self._lock = threading.RLock()
        self._init_db()
        logger.info("SavedLinksStore initialized at %s", self._db_path)

    def _init_db(self) -> None:
        """Create the saved_links table if it doesn't exist.

        If the database file is corrupt (e.g. 0-byte with stale journal),
        delete it and recreate from scratch.
        """
        for attempt in range(2):
            try:
                with self._lock:
                    conn = sqlite3.connect(str(self._db_path))
                    try:
                        # Quick integrity check — catches corrupt / empty DBs
                        conn.execute("SELECT name FROM sqlite_master LIMIT 1")
                        cur = conn.cursor()
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS saved_links (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                url TEXT NOT NULL,
                                domain TEXT NOT NULL DEFAULT '',
                                title TEXT NOT NULL DEFAULT '',
                                category TEXT NOT NULL DEFAULT '',
                                comment TEXT NOT NULL DEFAULT '',
                                saved_at TEXT NOT NULL,
                                viewed INTEGER NOT NULL DEFAULT 0,
                                viewed_at TEXT
                            )
                        """)
                        cur.execute("""
                            CREATE INDEX IF NOT EXISTS idx_saved_links_domain
                            ON saved_links(domain)
                        """)
                        cur.execute("""
                            CREATE INDEX IF NOT EXISTS idx_saved_links_saved_at
                            ON saved_links(saved_at)
                        """)
                        cur.execute("""
                            CREATE INDEX IF NOT EXISTS idx_saved_links_viewed_saved_at
                            ON saved_links(viewed, saved_at)
                        """)
                        # Schema version row so future migrations can evolve the schema.
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
                        return  # success
                    finally:
                        conn.close()
            except sqlite3.DatabaseError as exc:
                logger.warning("saved_links DB corrupt (attempt %d): %s — recreating", attempt + 1, exc)
                # Remove corrupt DB and journal so next attempt starts fresh
                for suffix in ("", "-journal", "-wal", "-shm"):
                    p = Path(str(self._db_path) + suffix)
                    try:
                        p.unlink(missing_ok=True)
                    except OSError:
                        pass
                if attempt == 1:
                    raise  # give up after second attempt

    def save_link(
        self,
        url: str,
        domain: str = "",
        title: str = "",
        category: str = "",
        comment: str = "",
    ) -> SavedLink:
        """Save a blocked link for later viewing.

        Args:
            url: The full URL that was blocked.
            domain: The domain name (e.g., youtube.com).
            title: Page title if available.
            category: Classification category (e.g., ENTERTAINMENT).
            comment: User's comment on why they wanted to visit.

        Returns:
            The saved link entry with its assigned ID.
        """
        saved_at = datetime.now().isoformat()

        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO saved_links (url, domain, title, category, comment, saved_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (url, domain, title, category, comment, saved_at),
                )
                conn.commit()
                link_id = cursor.lastrowid

                link = SavedLink(
                    id=link_id,
                    url=url,
                    domain=domain,
                    title=title,
                    category=category,
                    comment=comment,
                    saved_at=saved_at,
                )
                logger.info("Saved link #%d: %s (%s)", link_id, domain, category)
                return link
            finally:
                conn.close()

    def get_links(
        self,
        limit: int = 50,
        offset: int = 0,
        viewed: Optional[bool] = None,
        domain: Optional[str] = None,
    ) -> List[SavedLink]:
        """Get saved links with optional filtering.

        Args:
            limit: Maximum number of links to return.
            offset: Offset for pagination.
            viewed: Filter by viewed status (None = all).
            domain: Filter by domain.

        Returns:
            List of SavedLink entries, newest first.
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conditions = []
                params: list = []

                if viewed is not None:
                    conditions.append("viewed = ?")
                    params.append(1 if viewed else 0)

                if domain:
                    conditions.append("domain = ?")
                    params.append(domain)

                where = ""
                if conditions:
                    where = "WHERE " + " AND ".join(conditions)

                params.extend([limit, offset])
                rows = conn.execute(
                    f"""
                    SELECT id, url, domain, title, category, comment,
                           saved_at, viewed, viewed_at
                    FROM saved_links
                    {where}
                    ORDER BY saved_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    params,
                ).fetchall()

                return [
                    SavedLink(
                        id=row[0],
                        url=row[1],
                        domain=row[2],
                        title=row[3],
                        category=row[4],
                        comment=row[5],
                        saved_at=row[6],
                        viewed=bool(row[7]),
                        viewed_at=row[8],
                    )
                    for row in rows
                ]
            finally:
                conn.close()

    def get_link_count(self, viewed: Optional[bool] = None) -> int:
        """Get total count of saved links."""
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                if viewed is not None:
                    row = conn.execute(
                        "SELECT COUNT(*) FROM saved_links WHERE viewed = ?",
                        (1 if viewed else 0,),
                    ).fetchone()
                else:
                    row = conn.execute("SELECT COUNT(*) FROM saved_links").fetchone()
                return row[0] if row else 0
            finally:
                conn.close()

    def mark_viewed(self, link_id: int) -> bool:
        """Mark a saved link as viewed.

        Returns True if the link was found and updated.
        """
        viewed_at = datetime.now().isoformat()
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    "UPDATE saved_links SET viewed = 1, viewed_at = ? WHERE id = ?",
                    (viewed_at, link_id),
                )
                conn.commit()
                updated = cursor.rowcount > 0
                if updated:
                    logger.debug("Marked link #%d as viewed", link_id)
                return updated
            finally:
                conn.close()

    def delete_link(self, link_id: int) -> bool:
        """Delete a saved link.

        Returns True if the link was found and deleted.
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    "DELETE FROM saved_links WHERE id = ?",
                    (link_id,),
                )
                conn.commit()
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.debug("Deleted link #%d", link_id)
                return deleted
            finally:
                conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics for saved links."""
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                total = conn.execute("SELECT COUNT(*) FROM saved_links").fetchone()[0]
                unviewed = conn.execute(
                    "SELECT COUNT(*) FROM saved_links WHERE viewed = 0"
                ).fetchone()[0]

                # Top domains
                top_domains = conn.execute(
                    """
                    SELECT domain, COUNT(*) as cnt
                    FROM saved_links
                    GROUP BY domain
                    ORDER BY cnt DESC
                    LIMIT 5
                    """
                ).fetchall()

                return {
                    "total": total,
                    "unviewed": unviewed,
                    "viewed": total - unviewed,
                    "top_domains": [
                        {"domain": row[0], "count": row[1]}
                        for row in top_domains
                    ],
                }
            finally:
                conn.close()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_store: Optional[SavedLinksStore] = None
_store_lock = threading.Lock()


def get_saved_links_store() -> SavedLinksStore:
    """Get or create the singleton SavedLinksStore."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = SavedLinksStore()
    return _store
