"""Activity logging service for tracking browsing and blocking events.

Logs all URL visits, classifications, and blocking decisions to a SQLite database
for monitoring, reporting, and analysis.
"""

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ActivityEntry:
    """Represents a logged browsing activity."""
    id: Optional[int] = None
    timestamp: str = ""
    event_type: str = ""  # visit, block, override, classification
    domain: str = ""
    url: str = ""
    title: str = ""
    classification_category: str = ""
    classification_usefulness: str = ""
    classification_confidence: float = 0.0
    is_blocked: bool = False
    block_reason: str = ""
    is_distracting: bool = False
    browser: str = ""
    tab_id: str = ""
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "domain": self.domain,
            "url": self.url,
            "title": self.title,
            "classification_category": self.classification_category,
            "classification_usefulness": self.classification_usefulness,
            "classification_confidence": self.classification_confidence,
            "is_blocked": self.is_blocked,
            "block_reason": self.block_reason,
            "is_distracting": self.is_distracting,
            "browser": self.browser,
            "tab_id": self.tab_id,
            "duration_seconds": self.duration_seconds,
        }


class ActivityLogger:
    """Logs browsing activity to SQLite database."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the activity logger.
        
        Args:
            db_path: Path to SQLite database. Defaults to data/activity_log.db
        """
        if db_path is None:
            data_dir = Path(__file__).parent.parent.parent.parent.parent / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / "activity_log.db")
        
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_database()
        logger.info("ActivityLogger initialized with database: %s", self.db_path)
    
    def _init_database(self) -> None:
        """Initialize the SQLite database schema."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS activity_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        domain TEXT,
                        url TEXT,
                        title TEXT,
                        classification_category TEXT,
                        classification_usefulness TEXT,
                        classification_confidence REAL DEFAULT 0.0,
                        is_blocked INTEGER DEFAULT 0,
                        block_reason TEXT,
                        is_distracting INTEGER DEFAULT 0,
                        browser TEXT,
                        tab_id TEXT,
                        duration_seconds REAL DEFAULT 0.0,
                        metadata TEXT
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_event_type ON activity_log(event_type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_domain ON activity_log(domain)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_is_blocked ON activity_log(is_blocked)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_is_distracting ON activity_log(is_distracting)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_category ON activity_log(classification_category)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_blocked_timestamp ON activity_log(is_blocked, timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_distracting_timestamp ON activity_log(is_distracting, timestamp)")

                # Simple schema versioning table for future migrations.
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER NOT NULL
                    )
                    """
                )
                row = cursor.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
                if row is None:
                    cursor.execute("INSERT INTO schema_version (version) VALUES (1)")
                
                conn.commit()
            finally:
                conn.close()
    
    def log_visit(
        self,
        domain: str,
        url: str,
        title: str = "",
        classification_category: str = "",
        classification_usefulness: str = "",
        classification_confidence: float = 0.0,
        is_distracting: bool = False,
        browser: str = "",
        tab_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Log a page visit."""
        return self._log_event(
            event_type="visit",
            domain=domain,
            url=url,
            title=title,
            classification_category=classification_category,
            classification_usefulness=classification_usefulness,
            classification_confidence=classification_confidence,
            is_blocked=False,
            block_reason="",
            is_distracting=is_distracting,
            browser=browser,
            tab_id=tab_id,
            metadata=metadata,
        )
    
    def log_block(
        self,
        domain: str,
        url: str,
        block_reason: str,
        classification_category: str = "",
        classification_usefulness: str = "",
        classification_confidence: float = 0.0,
        browser: str = "",
        tab_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Log a blocked page."""
        return self._log_event(
            event_type="block",
            domain=domain,
            url=url,
            title="",
            classification_category=classification_category,
            classification_usefulness=classification_usefulness,
            classification_confidence=classification_confidence,
            is_blocked=True,
            block_reason=block_reason,
            is_distracting=True,  # Blocked content is always distracting
            browser=browser,
            tab_id=tab_id,
            metadata=metadata,
        )
    
    def log_classification(
        self,
        domain: str,
        url: str,
        title: str = "",
        classification_category: str = "",
        classification_usefulness: str = "",
        classification_confidence: float = 0.0,
        is_distracting: bool = False,
        classifier_used: str = "",
        browser: str = "",
        tab_id: str = "",
    ) -> Optional[int]:
        """Log a classification result."""
        return self._log_event(
            event_type="classification",
            domain=domain,
            url=url,
            title=title,
            classification_category=classification_category,
            classification_usefulness=classification_usefulness,
            classification_confidence=classification_confidence,
            is_blocked=False,
            block_reason="",
            is_distracting=is_distracting,
            browser=browser,
            tab_id=tab_id,
            metadata={"classifier_used": classifier_used},
        )
    
    def _log_event(
        self,
        event_type: str,
        domain: str,
        url: str,
        title: str,
        classification_category: str,
        classification_usefulness: str,
        classification_confidence: float,
        is_blocked: bool,
        block_reason: str,
        is_distracting: bool,
        browser: str,
        tab_id: str,
        duration_seconds: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Log an event to the database."""
        try:
            timestamp = datetime.now().isoformat()
            metadata_str = json.dumps(metadata) if metadata else "{}"
            
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO activity_log (
                            timestamp, event_type, domain, url, title,
                            classification_category, classification_usefulness,
                            classification_confidence, is_blocked, block_reason,
                            is_distracting, browser, tab_id, duration_seconds, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        timestamp, event_type, domain, url, title,
                        classification_category, classification_usefulness,
                        classification_confidence, 1 if is_blocked else 0, block_reason,
                        1 if is_distracting else 0, browser, tab_id, duration_seconds, metadata_str
                    ))
                    conn.commit()
                    row_id = cursor.lastrowid
                    
                    logger.debug(
                        "Logged %s: domain=%s, category=%s, blocked=%s",
                        event_type, domain, classification_category, is_blocked
                    )
                    
                    return row_id
                finally:
                    conn.close()
                    
        except Exception as e:
            logger.error("Failed to log activity: %s", e)
            return None
    
    def get_recent_activity(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        domain: Optional[str] = None,
        blocked_only: bool = False,
        distracting_only: bool = False,
        since: Optional[str] = None,
    ) -> List[ActivityEntry]:
        """Get recent activity entries."""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                try:
                    cursor = conn.cursor()
                    
                    query = "SELECT * FROM activity_log WHERE 1=1"
                    params = []
                    
                    if event_type:
                        query += " AND event_type = ?"
                        params.append(event_type)
                    
                    if domain:
                        query += " AND domain = ?"
                        params.append(domain)
                    
                    if blocked_only:
                        query += " AND is_blocked = 1"
                    
                    if distracting_only:
                        query += " AND is_distracting = 1"
                    
                    if since:
                        query += " AND timestamp > ?"
                        params.append(since)
                    
                    query += " ORDER BY timestamp DESC LIMIT ?"
                    params.append(limit)
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    entries = []
                    for row in rows:
                        entries.append(ActivityEntry(
                            id=row[0],
                            timestamp=row[1],
                            event_type=row[2],
                            domain=row[3] or "",
                            url=row[4] or "",
                            title=row[5] or "",
                            classification_category=row[6] or "",
                            classification_usefulness=row[7] or "",
                            classification_confidence=row[8] or 0.0,
                            is_blocked=bool(row[9]),
                            block_reason=row[10] or "",
                            is_distracting=bool(row[11]),
                            browser=row[12] or "",
                            tab_id=row[13] or "",
                            duration_seconds=row[14] or 0.0,
                        ))
                    
                    return entries
                finally:
                    conn.close()
                    
        except Exception as e:
            logger.error("Failed to get recent activity: %s", e)
            return []
    
    def get_activity_stats(
        self,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get activity statistics."""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                try:
                    cursor = conn.cursor()
                    
                    where_clause = ""
                    params = []
                    if since:
                        where_clause = "WHERE timestamp > ?"
                        params.append(since)
                    
                    # Total events
                    cursor.execute(f"SELECT COUNT(*) FROM activity_log {where_clause}", params)
                    total = cursor.fetchone()[0]
                    
                    # Blocked count
                    blocked_where = where_clause + (" AND " if where_clause else "WHERE ") + "is_blocked = 1"
                    cursor.execute(f"SELECT COUNT(*) FROM activity_log {blocked_where}", params)
                    blocked = cursor.fetchone()[0]
                    
                    # Distracting count
                    distracting_where = where_clause + (" AND " if where_clause else "WHERE ") + "is_distracting = 1"
                    cursor.execute(f"SELECT COUNT(*) FROM activity_log {distracting_where}", params)
                    distracting = cursor.fetchone()[0]
                    
                    # By event type
                    cursor.execute(f"""
                        SELECT event_type, COUNT(*) 
                        FROM activity_log {where_clause}
                        GROUP BY event_type
                        ORDER BY COUNT(*) DESC
                    """, params)
                    by_event_type = dict(cursor.fetchall())
                    
                    # By category
                    cursor.execute(f"""
                        SELECT classification_category, COUNT(*) 
                        FROM activity_log {where_clause}
                        WHERE classification_category != ''
                        GROUP BY classification_category
                        ORDER BY COUNT(*) DESC
                    """, params)
                    by_category = dict(cursor.fetchall())
                    
                    # Top blocked domains
                    cursor.execute(f"""
                        SELECT domain, COUNT(*) 
                        FROM activity_log {blocked_where}
                        GROUP BY domain
                        ORDER BY COUNT(*) DESC
                        LIMIT 10
                    """, params)
                    top_blocked_domains = [{"domain": r[0], "count": r[1]} for r in cursor.fetchall()]
                    
                    return {
                        "total_events": total,
                        "blocked_count": blocked,
                        "distracting_count": distracting,
                        "blocked_percentage": (blocked / total * 100) if total > 0 else 0,
                        "distracting_percentage": (distracting / total * 100) if total > 0 else 0,
                        "by_event_type": by_event_type,
                        "by_category": by_category,
                        "top_blocked_domains": top_blocked_domains,
                    }
                finally:
                    conn.close()
                    
        except Exception as e:
            logger.error("Failed to get activity stats: %s", e)
            return {}


# Singleton instance
_activity_logger: Optional[ActivityLogger] = None


def get_activity_logger() -> ActivityLogger:
    """Get the singleton ActivityLogger instance."""
    global _activity_logger
    if _activity_logger is None:
        _activity_logger = ActivityLogger()
    return _activity_logger
