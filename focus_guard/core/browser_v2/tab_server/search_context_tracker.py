"""Search context tracker for detecting entertainment searches.

This module tracks search queries to detect when users are searching for
entertainment content (movies, novels, etc.). When a user searches for
"twilight movie" and then clicks a Google Drive link, we can block it
even though Google Drive itself is a neutral platform.

The key insight: If someone searches for "twilight pdf" and then opens
a Google Drive link, that link is almost certainly the movie/book, not
a work document.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from urllib.parse import urlparse, parse_qs, unquote

logger = logging.getLogger(__name__)


# Search engines and their query parameter names
SEARCH_ENGINES = {
    "google.com": "q",
    "www.google.com": "q",
    "bing.com": "q",
    "www.bing.com": "q",
    "duckduckgo.com": "q",
    "search.yahoo.com": "p",
    "ecosia.org": "q",
    "www.ecosia.org": "q",
}

# File-sharing domains that can host entertainment content
FILE_SHARING_DOMAINS = {
    # Google
    "drive.google.com",
    "docs.google.com",
    "photos.google.com",
    # Microsoft
    "onedrive.live.com",
    "1drv.ms",
    "sharepoint.com",
    # Dropbox
    "dropbox.com",
    "www.dropbox.com",
    "dl.dropboxusercontent.com",
    # Mega
    "mega.nz",
    "mega.co.nz",
    "mega.io",
    # MediaFire
    "mediafire.com",
    "www.mediafire.com",
    # Box
    "box.com",
    "www.box.com",
    "app.box.com",
    # WeTransfer
    "wetransfer.com",
    "we.tl",
    # Archive.org
    "archive.org",
    "www.archive.org",
    "ia601.us.archive.org",
    # SendSpace
    "sendspace.com",
    # pCloud
    "pcloud.com",
    "www.pcloud.com",
    # iCloud
    "icloud.com",
    "www.icloud.com",
    # File hosting (often used for piracy)
    "zippyshare.com",
    "rapidgator.net",
    "uploaded.net",
    "4shared.com",
    "turbobit.net",
    "nitroflare.com",
    "uploadgig.com",
    "katfile.com",
    "filerio.in",
    "clicknupload.co",
    "ddownload.com",
    "filefactory.com",
    "depositfiles.com",
    # Torrent/Magnet related
    "1337x.to",
    "rarbg.to",
    "thepiratebay.org",
    "nyaa.si",
    "yts.mx",
    "torrentgalaxy.to",
    # Streaming sites (often host pirated content)
    "ok.ru",
    "vk.com",
    "dailymotion.com",
    "streamtape.com",
    "mixdrop.co",
    "dood.to",
    "doodstream.com",
    "upstream.to",
    "vidoza.net",
    "fembed.com",
    "filemoon.sx",
    # PDF/Book sharing
    "scribd.com",
    "www.scribd.com",
    "pdfdrive.com",
    "www.pdfdrive.com",
    "zlibrary.org",
    "z-lib.org",
    "libgen.is",
    "libgen.rs",
    "b-ok.org",
    "annas-archive.org",
    # Paste/Text sharing (sometimes used for links)
    "pastebin.com",
    "justpaste.it",
    # Image hosting (can host manga/comics)
    "imgur.com",
    "imgbb.com",
    "postimg.cc",
}

# Default entertainment keywords to detect in searches
DEFAULT_ENTERTAINMENT_KEYWORDS = [
    # Movies/TV
    "movie", "film", "watch online", "stream", "full movie",
    "720p", "1080p", "4k", "bluray", "dvdrip", "webrip", "hdtv",
    "season", "episode", "s01", "s02", "e01", "e02",
    "subtitle", "dubbed", "subbed",
    # Books/Novels (fiction-specific)
    "epub", "ebook", "kindle", "read online", "free download",
    "novel", "wattpad", "fanfiction", "fanfic",
    # Specific titles (fiction)
    "twilight", "harry potter", "hunger games", "divergent",
    "percy jackson", "maze runner", "lord of the rings", "hobbit",
    "game of thrones", "narnia", "eragon", "artemis fowl",
    "fifty shades", "after", "the selection", "red queen",
    # Movies
    "avengers", "spider-man", "batman", "superman", "marvel", "dc",
    "star wars", "fast furious", "transformers", "jurassic",
    "frozen", "disney", "pixar", "dreamworks",
    # Anime/Manga
    "anime", "manga", "naruto", "one piece", "attack on titan",
    "demon slayer", "my hero academia", "jujutsu kaisen",
    # Games (for game guides/downloads)
    "minecraft", "fortnite", "roblox", "gta", "call of duty",
]


@dataclass
class SearchContext:
    """Context from a recent search query."""
    query: str
    timestamp: float
    search_engine: str
    is_entertainment: bool
    matched_keywords: List[str]
    tab_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "timestamp": self.timestamp,
            "search_engine": self.search_engine,
            "is_entertainment": self.is_entertainment,
            "matched_keywords": self.matched_keywords,
            "tab_id": self.tab_id,
            "age_seconds": time.time() - self.timestamp,
        }


@dataclass 
class FlaggedNavigation:
    """A navigation that was flagged due to search context."""
    url: str
    domain: str
    source_search: SearchContext
    timestamp: float
    blocked: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "domain": self.domain,
            "source_search": self.source_search.to_dict(),
            "timestamp": self.timestamp,
            "blocked": self.blocked,
        }


class SearchContextTracker:
    """Tracks search queries to detect entertainment content access.
    
    When a user searches for entertainment content (e.g., "twilight movie pdf"),
    we flag subsequent navigations to file-sharing sites as potentially
    entertainment-related, even if the URL itself doesn't reveal the content.
    
    This solves the problem of blocking movies/books on Google Drive where
    the URL is just a random file ID.
    """
    
    # How long to remember a search context (5 minutes)
    CONTEXT_TTL_SECONDS = 300
    
    def __init__(
        self,
        keywords: Optional[List[str]] = None,
        data_file: Optional[Path] = None,
    ):
        self._lock = threading.RLock()
        self._keywords = set(k.lower() for k in (keywords or DEFAULT_ENTERTAINMENT_KEYWORDS))
        self._data_file = data_file or Path.home() / ".focus_guard" / "search_context.json"
        
        # Recent search contexts by tab_id
        self._search_contexts: Dict[int, SearchContext] = {}
        
        # Global recent entertainment searches (for cross-tab detection)
        self._recent_entertainment_searches: List[SearchContext] = []
        
        # Flagged navigations for logging
        self._flagged_navigations: List[FlaggedNavigation] = []
        
        # Ensure directory exists
        self._data_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "SearchContextTracker initialized with %d entertainment keywords",
            len(self._keywords)
        )
    
    def _is_search_url(self, url: str) -> Optional[str]:
        """Check if URL is a search engine and extract the query.
        
        Returns the search query if found, None otherwise.
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            if domain in SEARCH_ENGINES:
                query_param = SEARCH_ENGINES[domain]
                query_dict = parse_qs(parsed.query)
                if query_param in query_dict:
                    return unquote(query_dict[query_param][0])
        except Exception as e:
            logger.debug("Error parsing search URL: %s", e)
        
        return None
    
    def _is_file_sharing_domain(self, domain: str) -> bool:
        """Check if domain is a file-sharing platform."""
        domain_lower = domain.lower()
        return domain_lower in FILE_SHARING_DOMAINS
    
    def _detect_entertainment_keywords(self, text: str) -> List[str]:
        """Detect entertainment keywords in text.
        
        Returns list of matched keywords.
        """
        text_lower = text.lower()
        matched = []
        
        for keyword in self._keywords:
            # Use word boundary matching for short keywords
            if len(keyword) <= 3:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, text_lower):
                    matched.append(keyword)
            else:
                if keyword in text_lower:
                    matched.append(keyword)
        
        return matched
    
    def _cleanup_old_contexts(self) -> None:
        """Remove expired search contexts."""
        now = time.time()
        cutoff = now - self.CONTEXT_TTL_SECONDS
        
        # Clean tab-specific contexts
        expired_tabs = [
            tab_id for tab_id, ctx in self._search_contexts.items()
            if ctx.timestamp < cutoff
        ]
        for tab_id in expired_tabs:
            del self._search_contexts[tab_id]
        
        # Clean global recent searches
        self._recent_entertainment_searches = [
            ctx for ctx in self._recent_entertainment_searches
            if ctx.timestamp >= cutoff
        ]
    
    def process_navigation(
        self,
        url: str,
        tab_id: Optional[int] = None,
        title: str = "",
        referrer: str = "",
    ) -> Dict[str, Any]:
        """Process a navigation event and check for entertainment context.
        
        This should be called for every navigation. It will:
        1. Check if this is a search query and track it
        2. Check if this navigation to a file-sharing site should be blocked
           based on recent search context
        
        Args:
            url: The URL being navigated to
            tab_id: The browser tab ID
            title: The page title (if available)
            referrer: The referrer URL (if available)
            
        Returns:
            Dict with:
            - is_search: bool - Whether this was a search query
            - is_entertainment_search: bool - Whether search was for entertainment
            - should_block: bool - Whether to block this navigation
            - reason: str - Reason for blocking (if applicable)
            - search_context: dict - The triggering search context (if applicable)
        """
        with self._lock:
            self._cleanup_old_contexts()
            
            result = {
                "is_search": False,
                "is_entertainment_search": False,
                "should_block": False,
                "reason": "",
                "search_context": None,
                "matched_keywords": [],
            }
            
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                
                # Check if this is a search query
                search_query = self._is_search_url(url)
                if search_query:
                    result["is_search"] = True
                    matched_keywords = self._detect_entertainment_keywords(search_query)
                    is_entertainment = len(matched_keywords) > 0
                    
                    # Create search context
                    ctx = SearchContext(
                        query=search_query,
                        timestamp=time.time(),
                        search_engine=domain,
                        is_entertainment=is_entertainment,
                        matched_keywords=matched_keywords,
                        tab_id=tab_id,
                    )
                    
                    # Store context
                    if tab_id is not None:
                        self._search_contexts[tab_id] = ctx
                    
                    if is_entertainment:
                        result["is_entertainment_search"] = True
                        result["matched_keywords"] = matched_keywords
                        self._recent_entertainment_searches.append(ctx)
                        logger.info(
                            "Entertainment search detected: '%s' (keywords: %s)",
                            search_query, matched_keywords
                        )
                    
                    return result
                
                # Check if this is a file-sharing navigation that should be blocked
                if self._is_file_sharing_domain(domain):
                    # Check tab-specific context first
                    if tab_id is not None and tab_id in self._search_contexts:
                        ctx = self._search_contexts[tab_id]
                        if ctx.is_entertainment:
                            result["should_block"] = True
                            result["reason"] = f"File accessed after searching for entertainment: '{ctx.query}'"
                            result["search_context"] = ctx.to_dict()
                            result["matched_keywords"] = ctx.matched_keywords
                            
                            # Log flagged navigation
                            self._flagged_navigations.append(FlaggedNavigation(
                                url=url,
                                domain=domain,
                                source_search=ctx,
                                timestamp=time.time(),
                                blocked=True,
                            ))
                            
                            logger.info(
                                "Blocking file-sharing URL due to entertainment search context: %s (search: '%s')",
                                url, ctx.query
                            )
                            return result
                    
                    # Check global recent entertainment searches
                    for ctx in reversed(self._recent_entertainment_searches):
                        if ctx.is_entertainment:
                            result["should_block"] = True
                            result["reason"] = f"File accessed after recent entertainment search: '{ctx.query}'"
                            result["search_context"] = ctx.to_dict()
                            result["matched_keywords"] = ctx.matched_keywords
                            
                            self._flagged_navigations.append(FlaggedNavigation(
                                url=url,
                                domain=domain,
                                source_search=ctx,
                                timestamp=time.time(),
                                blocked=True,
                            ))
                            
                            logger.info(
                                "Blocking file-sharing URL due to recent entertainment search: %s (search: '%s')",
                                url, ctx.query
                            )
                            return result
                    
                    # Also check title/URL/referrer for entertainment keywords
                    combined_text = f"{url} {title} {referrer}"
                    matched = self._detect_entertainment_keywords(combined_text)
                    if matched:
                        result["should_block"] = True
                        result["reason"] = f"Entertainment content detected on file-sharing site: {', '.join(matched)}"
                        result["matched_keywords"] = matched
                        logger.info(
                            "Blocking file-sharing URL due to content keywords: %s (keywords: %s)",
                            url, matched
                        )
                        return result
                    
                    # Check if referrer is a search URL with entertainment keywords
                    if referrer:
                        referrer_query = self._is_search_url(referrer)
                        if referrer_query:
                            referrer_keywords = self._detect_entertainment_keywords(referrer_query)
                            if referrer_keywords:
                                result["should_block"] = True
                                result["reason"] = f"File accessed from entertainment search: '{referrer_query}'"
                                result["matched_keywords"] = referrer_keywords
                                result["referrer_search"] = referrer_query
                                logger.info(
                                    "Blocking file-sharing URL due to referrer search: %s (search: '%s')",
                                    url, referrer_query
                                )
                                return result
                
            except Exception as e:
                logger.error("Error processing navigation: %s", e)
            
            return result
    
    def check_should_block_file_sharing(
        self,
        url: str,
        domain: str,
        title: str = "",
        tab_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Check if a file-sharing URL should be blocked.
        
        This is a convenience method that focuses on file-sharing detection.
        
        Returns:
            Dict with should_block, reason, and context info
        """
        if not self._is_file_sharing_domain(domain):
            return {"should_block": False, "reason": "", "is_file_sharing": False}
        
        result = self.process_navigation(url, tab_id, title)
        result["is_file_sharing"] = True
        return result
    
    def get_recent_searches(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent search contexts for debugging/display."""
        with self._lock:
            self._cleanup_old_contexts()
            searches = list(self._search_contexts.values()) + self._recent_entertainment_searches
            searches.sort(key=lambda x: x.timestamp, reverse=True)
            return [s.to_dict() for s in searches[:limit]]
    
    def get_flagged_navigations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent flagged navigations for logging/display."""
        with self._lock:
            return [n.to_dict() for n in self._flagged_navigations[-limit:]]
    
    def add_keyword(self, keyword: str) -> None:
        """Add a new entertainment keyword."""
        with self._lock:
            self._keywords.add(keyword.lower())
    
    def remove_keyword(self, keyword: str) -> None:
        """Remove an entertainment keyword."""
        with self._lock:
            self._keywords.discard(keyword.lower())
    
    def get_keywords(self) -> List[str]:
        """Get all entertainment keywords."""
        with self._lock:
            return sorted(self._keywords)
    
    def clear_context(self, tab_id: Optional[int] = None) -> None:
        """Clear search context for a tab or all tabs."""
        with self._lock:
            if tab_id is not None:
                self._search_contexts.pop(tab_id, None)
            else:
                self._search_contexts.clear()
                self._recent_entertainment_searches.clear()


# Singleton instance
_tracker: Optional[SearchContextTracker] = None
_tracker_lock = threading.Lock()


def get_search_context_tracker() -> SearchContextTracker:
    """Get or create the singleton SearchContextTracker instance."""
    global _tracker
    with _tracker_lock:
        if _tracker is None:
            _tracker = SearchContextTracker()
        return _tracker


def reset_search_context_tracker() -> None:
    """Reset the singleton (for testing)."""
    global _tracker
    with _tracker_lock:
        _tracker = None
