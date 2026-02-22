"""Search logging service for tracking user searches.

Logs all search queries from Google, Bing, and address bar navigation
to a SQLite database for monitoring and analysis.
"""

import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, parse_qs, unquote

logger = logging.getLogger(__name__)


@dataclass
class SearchEntry:
    """Represents a logged search query."""
    id: Optional[int] = None
    timestamp: str = ""
    search_engine: str = ""  # google, bing, duckduckgo, address_bar, etc.
    query: str = ""
    url: str = ""
    domain: str = ""
    classification_category: str = ""
    classification_usefulness: str = ""
    is_distracting: bool = False
    browser: str = ""
    tab_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "search_engine": self.search_engine,
            "query": self.query,
            "url": self.url,
            "domain": self.domain,
            "classification_category": self.classification_category,
            "classification_usefulness": self.classification_usefulness,
            "is_distracting": self.is_distracting,
            "browser": self.browser,
            "tab_id": self.tab_id,
        }


class SearchLogger:
    """Logs search queries to SQLite database."""
    
    # Search engine patterns for query extraction
    SEARCH_ENGINES = {
        "google": {
            "domains": ["google.com", "google.co.uk", "google.ca", "google.com.au", "google.co.in"],
            "query_param": "q",
            "path_pattern": "/search",
        },
        "bing": {
            "domains": ["bing.com", "www.bing.com"],
            "query_param": "q",
            "path_pattern": "/search",
        },
        "duckduckgo": {
            "domains": ["duckduckgo.com", "www.duckduckgo.com"],
            "query_param": "q",
            "path_pattern": "/",
        },
        "yahoo": {
            "domains": ["search.yahoo.com"],
            "query_param": "p",
            "path_pattern": "/search",
        },
        "ecosia": {
            "domains": ["ecosia.org", "www.ecosia.org"],
            "query_param": "q",
            "path_pattern": "/search",
        },
    }
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the search logger.
        
        Args:
            db_path: Path to SQLite database. Defaults to data/search_log.db
        """
        if db_path is None:
            # Default to data directory in project root
            data_dir = Path(__file__).parent.parent.parent.parent.parent / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / "search_log.db")
        
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_database()
        logger.info("SearchLogger initialized with database: %s", self.db_path)
    
    def _init_database(self) -> None:
        """Initialize the SQLite database schema."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS search_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        search_engine TEXT NOT NULL,
                        query TEXT NOT NULL,
                        url TEXT,
                        domain TEXT,
                        classification_category TEXT,
                        classification_usefulness TEXT,
                        is_distracting INTEGER DEFAULT 0,
                        browser TEXT,
                        tab_id TEXT,
                        metadata TEXT
                    )
                """)
                
                # Create indexes for common queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON search_log(timestamp)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_search_engine 
                    ON search_log(search_engine)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_is_distracting 
                    ON search_log(is_distracting)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_category 
                    ON search_log(classification_category)
                """)
                
                conn.commit()
            finally:
                conn.close()
    
    def detect_search_engine(self, url: str) -> Optional[str]:
        """Detect which search engine a URL belongs to.
        
        Returns:
            Search engine name or None if not a search engine.
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()
            
            for engine_name, config in self.SEARCH_ENGINES.items():
                for engine_domain in config["domains"]:
                    if domain == engine_domain or domain.endswith("." + engine_domain):
                        # Check if it's a search path
                        if config["path_pattern"] in path or path == "/":
                            return engine_name
            
            return None
        except Exception:
            return None
    
    def extract_search_query(self, url: str, search_engine: Optional[str] = None) -> Optional[str]:
        """Extract search query from URL.
        
        Args:
            url: The URL to extract query from
            search_engine: Optional search engine name (auto-detected if not provided)
            
        Returns:
            The search query or None if not found.
        """
        try:
            if search_engine is None:
                search_engine = self.detect_search_engine(url)
            
            if search_engine is None:
                return None
            
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            config = self.SEARCH_ENGINES.get(search_engine, {})
            query_param = config.get("query_param", "q")
            
            if query_param in params:
                return unquote(params[query_param][0])
            
            return None
        except Exception:
            return None
    
    def log_search(
        self,
        url: str,
        search_engine: Optional[str] = None,
        query: Optional[str] = None,
        classification_category: str = "",
        classification_usefulness: str = "",
        is_distracting: bool = False,
        browser: str = "",
        tab_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Log a search query to the database.
        
        Args:
            url: The search URL
            search_engine: Search engine name (auto-detected if not provided)
            query: Search query (extracted from URL if not provided)
            classification_category: Category from classification
            classification_usefulness: Usefulness from classification
            is_distracting: Whether the search is distracting
            browser: Browser name
            tab_id: Tab ID
            metadata: Additional metadata
            
        Returns:
            The ID of the inserted row, or None if failed.
        """
        try:
            # Auto-detect search engine if not provided
            if search_engine is None:
                search_engine = self.detect_search_engine(url) or "address_bar"
            
            # Extract query if not provided
            if query is None:
                query = self.extract_search_query(url, search_engine) or ""
            
            # Skip if no query (not a search)
            if not query and search_engine != "address_bar":
                return None
            
            # Parse domain
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
            except Exception:
                domain = ""
            
            timestamp = datetime.now().isoformat()
            
            # Serialize metadata
            import json
            metadata_str = json.dumps(metadata) if metadata else "{}"
            
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO search_log (
                            timestamp, search_engine, query, url, domain,
                            classification_category, classification_usefulness,
                            is_distracting, browser, tab_id, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        timestamp, search_engine, query, url, domain,
                        classification_category, classification_usefulness,
                        1 if is_distracting else 0, browser, tab_id, metadata_str
                    ))
                    conn.commit()
                    row_id = cursor.lastrowid
                    
                    logger.info(
                        "Logged search: engine=%s, query='%s', category=%s, distracting=%s",
                        search_engine, query[:50] if query else "", 
                        classification_category, is_distracting
                    )
                    
                    return row_id
                finally:
                    conn.close()
                    
        except Exception as e:
            logger.error("Failed to log search: %s", e)
            return None
    
    def log_address_bar_navigation(
        self,
        url: str,
        classification_category: str = "",
        classification_usefulness: str = "",
        is_distracting: bool = False,
        browser: str = "",
        tab_id: str = "",
    ) -> Optional[int]:
        """Log an address bar navigation (direct URL entry).
        
        This is for tracking when users type URLs directly into the address bar,
        which could indicate intentional navigation to specific sites.
        """
        return self.log_search(
            url=url,
            search_engine="address_bar",
            query=url,  # For address bar, the query is the URL itself
            classification_category=classification_category,
            classification_usefulness=classification_usefulness,
            is_distracting=is_distracting,
            browser=browser,
            tab_id=tab_id,
        )
    
    def get_recent_searches(
        self,
        limit: int = 100,
        search_engine: Optional[str] = None,
        distracting_only: bool = False,
        since: Optional[str] = None,
    ) -> List[SearchEntry]:
        """Get recent search entries.
        
        Args:
            limit: Maximum number of entries to return
            search_engine: Filter by search engine
            distracting_only: Only return distracting searches
            since: Only return searches after this ISO timestamp
            
        Returns:
            List of SearchEntry objects
        """
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                try:
                    cursor = conn.cursor()
                    
                    query = "SELECT * FROM search_log WHERE 1=1"
                    params = []
                    
                    if search_engine:
                        query += " AND search_engine = ?"
                        params.append(search_engine)
                    
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
                        entries.append(SearchEntry(
                            id=row[0],
                            timestamp=row[1],
                            search_engine=row[2],
                            query=row[3],
                            url=row[4] or "",
                            domain=row[5] or "",
                            classification_category=row[6] or "",
                            classification_usefulness=row[7] or "",
                            is_distracting=bool(row[8]),
                            browser=row[9] or "",
                            tab_id=row[10] or "",
                        ))
                    
                    return entries
                finally:
                    conn.close()
                    
        except Exception as e:
            logger.error("Failed to get recent searches: %s", e)
            return []
    
    def get_search_stats(
        self,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get search statistics.
        
        Args:
            since: Only count searches after this ISO timestamp
            
        Returns:
            Dictionary with search statistics
        """
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
                    
                    # Total searches
                    cursor.execute(
                        f"SELECT COUNT(*) FROM search_log {where_clause}", 
                        params
                    )
                    total = cursor.fetchone()[0]
                    
                    # Distracting searches
                    distracting_where = where_clause + (" AND " if where_clause else "WHERE ") + "is_distracting = 1"
                    cursor.execute(
                        f"SELECT COUNT(*) FROM search_log {distracting_where}",
                        params
                    )
                    distracting = cursor.fetchone()[0]
                    
                    # By search engine
                    cursor.execute(f"""
                        SELECT search_engine, COUNT(*) 
                        FROM search_log {where_clause}
                        GROUP BY search_engine
                        ORDER BY COUNT(*) DESC
                    """, params)
                    by_engine = dict(cursor.fetchall())
                    
                    # By category
                    cursor.execute(f"""
                        SELECT classification_category, COUNT(*) 
                        FROM search_log {where_clause}
                        GROUP BY classification_category
                        ORDER BY COUNT(*) DESC
                    """, params)
                    by_category = dict(cursor.fetchall())
                    
                    return {
                        "total_searches": total,
                        "distracting_searches": distracting,
                        "distracting_percentage": (distracting / total * 100) if total > 0 else 0,
                        "by_search_engine": by_engine,
                        "by_category": by_category,
                    }
                finally:
                    conn.close()
                    
        except Exception as e:
            logger.error("Failed to get search stats: %s", e)
            return {}
    
    def get_distracting_search_patterns(
        self,
        limit: int = 20,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get most common distracting search patterns.
        
        Returns:
            List of common distracting search queries with counts
        """
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                try:
                    cursor = conn.cursor()
                    
                    where_clause = "WHERE is_distracting = 1"
                    params = []
                    if since:
                        where_clause += " AND timestamp > ?"
                        params.append(since)
                    
                    params.append(limit)
                    
                    cursor.execute(f"""
                        SELECT query, classification_category, COUNT(*) as count
                        FROM search_log {where_clause}
                        GROUP BY query
                        ORDER BY count DESC
                        LIMIT ?
                    """, params)
                    
                    return [
                        {"query": row[0], "category": row[1], "count": row[2]}
                        for row in cursor.fetchall()
                    ]
                finally:
                    conn.close()
                    
        except Exception as e:
            logger.error("Failed to get distracting patterns: %s", e)
            return []


# Singleton instance
_search_logger: Optional[SearchLogger] = None


def get_search_logger() -> SearchLogger:
    """Get the singleton SearchLogger instance."""
    global _search_logger
    if _search_logger is None:
        _search_logger = SearchLogger()
    return _search_logger
