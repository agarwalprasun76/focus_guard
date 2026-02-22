"""
Generic URL classifier for any domain.

This classifier works for any URL by analyzing:
1. URL path patterns (fast, rule-based)
2. Page title and metadata (LLM-based)

Rules are loaded from config/classification_rules.json for easy UI editing.
The classifier is designed to be a fallback for domains without
domain-specific classifiers (like YouTube or Google).
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse, unquote

from focus_guard.core.domain.models import Domain, Category, Classification

logger = logging.getLogger(__name__)

# Default config path
CONFIG_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / "config" / "classification_rules.json"


@dataclass
class URLPatternRule:
    """A rule for matching URL patterns."""
    pattern: str  # Regex pattern
    category: Category
    usefulness: str  # EDUCATIONAL, ENRICHMENT, NEUTRAL, DISTRACTION
    confidence: float
    description: str


class RuleBasedURLClassifier:
    """Fast rule-based URL pattern classifier.
    
    Analyzes URL structure to make quick classification decisions
    without needing LLM calls.
    
    Rules are loaded from config/classification_rules.json for easy UI editing.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.name = "url_rules"
        self.config_path = config_path or CONFIG_PATH
        self._config: Optional[Dict[str, Any]] = None
        self._domain_patterns: Dict[str, Tuple[Category, str, float]] = {}
        self._path_patterns: List[Tuple[re.Pattern, str, Category, str, float]] = []
        self._title_keywords: Dict[str, Tuple[Category, str, float]] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load classification rules from config file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                self._parse_domain_rules()
                self._parse_path_patterns()
                self._parse_title_keywords()
                logger.info("Loaded classification rules from %s", self.config_path)
            else:
                logger.warning("Config file not found: %s, using defaults", self.config_path)
                self._load_defaults()
        except Exception as e:
            logger.error("Failed to load config: %s, using defaults", e)
            self._load_defaults()
    
    def _parse_domain_rules(self) -> None:
        """Parse domain rules from config."""
        domain_rules = self._config.get("domain_rules", {})
        for group_name, group_data in domain_rules.items():
            if group_name == "description":
                continue
            category = self._str_to_category(group_data.get("category", "UNKNOWN"))
            usefulness = group_data.get("usefulness", "NEUTRAL")
            confidence = group_data.get("confidence", 0.7)
            for domain in group_data.get("domains", []):
                self._domain_patterns[domain] = (category, usefulness, confidence)
    
    def _parse_path_patterns(self) -> None:
        """Parse URL path patterns from config."""
        path_patterns = self._config.get("path_patterns", {})
        for pattern_name, pattern_data in path_patterns.items():
            if pattern_name == "description":
                continue
            try:
                pattern = re.compile(pattern_data.get("pattern", ""), re.IGNORECASE)
                category = self._str_to_category(pattern_data.get("category", "UNKNOWN"))
                usefulness = pattern_data.get("usefulness", "NEUTRAL")
                confidence = pattern_data.get("confidence", 0.7)
                self._path_patterns.append((pattern, pattern_name, category, usefulness, confidence))
            except re.error as e:
                logger.warning("Invalid regex pattern %s: %s", pattern_name, e)
    
    def _parse_title_keywords(self) -> None:
        """Parse title keywords from config."""
        title_keywords = self._config.get("title_keywords", {})
        for group_name, group_data in title_keywords.items():
            if group_name == "description":
                continue
            category = self._str_to_category(group_data.get("category", "UNKNOWN"))
            usefulness = group_data.get("usefulness", "NEUTRAL")
            confidence = group_data.get("confidence", 0.7)
            for keyword in group_data.get("keywords", []):
                self._title_keywords[keyword.lower()] = (category, usefulness, confidence)
        
        # Also load fiction keywords for file-sharing detection
        self._fiction_keywords: List[str] = []
        fiction_data = self._config.get("fiction_keywords", {})
        if isinstance(fiction_data, dict):
            self._fiction_keywords = [k.lower() for k in fiction_data.get("keywords", [])]
        
        # File-sharing platforms that can host entertainment content
        self._file_sharing_domains = {
            "drive.google.com", "docs.google.com",
            "dropbox.com", "onedrive.live.com",
            "mega.nz", "mediafire.com",
            "wetransfer.com", "sendspace.com",
            "archive.org",  # Can host movies/books
        }
    
    def _str_to_category(self, category_str: str) -> Category:
        """Convert string to Category enum."""
        category_map = {
            "EDUCATION": Category.EDUCATION,
            "ENTERTAINMENT": Category.ENTERTAINMENT,
            "SOCIAL_MEDIA": Category.SOCIAL_MEDIA,
            "GAMING": Category.GAMING,
            "NEWS": Category.NEWS,
            "SHOPPING": Category.SHOPPING,
            "PRODUCTIVITY": Category.PRODUCTIVITY,
            "ADULT": Category.ADULT,
            "MALICIOUS": Category.MALICIOUS,
            "UNKNOWN": Category.UNKNOWN,
        }
        return category_map.get(category_str.upper(), Category.UNKNOWN)
    
    def _load_defaults(self) -> None:
        """Load default rules if config file is not available."""
        # Default fiction keywords for file-sharing detection
        self._fiction_keywords = [
            "novel", "fiction", "story", "romance", "fantasy", "sci-fi",
            "thriller", "mystery", "horror", "adventure",
            "wattpad", "fanfiction", "fanfic", "ao3",
            "light novel", "web novel", "manga", "comic",
            "epub", "kindle", "ebook",
            "harry potter", "hunger games", "twilight", "divergent",
            "percy jackson", "maze runner", "lord of the rings", "hobbit",
            "game of thrones", "narnia", "eragon", "artemis fowl",
            "movie", "film", "720p", "1080p", "bluray", "dvdrip", "webrip",
        ]
        
        # File-sharing platforms
        self._file_sharing_domains = {
            "drive.google.com", "docs.google.com",
            "dropbox.com", "onedrive.live.com",
            "mega.nz", "mediafire.com",
            "wetransfer.com", "sendspace.com",
            "archive.org",
        }
        
        # Default domain patterns
        self._domain_patterns = {
            "netflix.com": (Category.ENTERTAINMENT, "DISTRACTION", 0.9),
            "youtube.com": (Category.ENTERTAINMENT, "DISTRACTION", 0.7),
            "facebook.com": (Category.SOCIAL_MEDIA, "DISTRACTION", 0.8),
            "twitter.com": (Category.SOCIAL_MEDIA, "DISTRACTION", 0.75),
            "instagram.com": (Category.SOCIAL_MEDIA, "DISTRACTION", 0.85),
            "tiktok.com": (Category.ENTERTAINMENT, "DISTRACTION", 0.9),
            "twitch.tv": (Category.GAMING, "DISTRACTION", 0.85),
            "steam.com": (Category.GAMING, "DISTRACTION", 0.8),
            "roblox.com": (Category.GAMING, "DISTRACTION", 0.9),
            "khanacademy.org": (Category.EDUCATION, "EDUCATIONAL", 0.95),
            "coursera.org": (Category.EDUCATION, "EDUCATIONAL", 0.9),
            "wikipedia.org": (Category.EDUCATION, "ENRICHMENT", 0.7),
            "stackoverflow.com": (Category.EDUCATION, "EDUCATIONAL", 0.8),
            "github.com": (Category.PRODUCTIVITY, "EDUCATIONAL", 0.75),
        }
        
        # Default path patterns
        default_patterns = [
            (r"/(watch|video|play|stream)", "video_content", Category.ENTERTAINMENT, "DISTRACTION", 0.7),
            (r"/(shorts|reels|stories)", "short_form", Category.ENTERTAINMENT, "DISTRACTION", 0.8),
            (r"/(game|games|gaming)", "gaming", Category.GAMING, "DISTRACTION", 0.75),
            (r"/(learn|course|tutorial|lesson)", "education", Category.EDUCATION, "EDUCATIONAL", 0.8),
            (r"/(docs|documentation|api)", "docs", Category.EDUCATION, "EDUCATIONAL", 0.75),
        ]
        for pattern_str, name, category, usefulness, confidence in default_patterns:
            self._path_patterns.append((re.compile(pattern_str, re.IGNORECASE), name, category, usefulness, confidence))
        
        # Default title keywords
        self._title_keywords = {
            "tutorial": (Category.EDUCATION, "EDUCATIONAL", 0.8),
            "how to": (Category.EDUCATION, "EDUCATIONAL", 0.75),
            "gameplay": (Category.GAMING, "DISTRACTION", 0.8),
            "movie": (Category.ENTERTAINMENT, "DISTRACTION", 0.7),
            "meme": (Category.ENTERTAINMENT, "DISTRACTION", 0.8),
        }
    
    def reload_config(self) -> None:
        """Reload configuration from file (for UI updates)."""
        self._domain_patterns.clear()
        self._path_patterns.clear()
        self._title_keywords.clear()
        self._load_config()
    
    def _extract_domain(self, url: str) -> str:
        """Extract the base domain from a URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""
    
    def _check_domain_patterns(
        self, domain: str
    ) -> Optional[Tuple[Category, str, float, str]]:
        """Check if domain matches known patterns."""
        for pattern_domain, (category, usefulness, confidence) in self._domain_patterns.items():
            if domain == pattern_domain or domain.endswith("." + pattern_domain):
                return (category, usefulness, confidence, f"Known domain: {pattern_domain}")
        return None
    
    def _check_path_patterns(
        self, url: str
    ) -> Optional[Tuple[Category, str, float, str]]:
        """Check if URL path matches known patterns."""
        try:
            parsed = urlparse(url)
            path = unquote(parsed.path.lower())
            
            for compiled_pattern, pattern_name, category, usefulness, confidence in self._path_patterns:
                if compiled_pattern.search(path):
                    return (category, usefulness, confidence, f"Path pattern: {pattern_name}")
        except Exception:
            pass
        return None
    
    def _check_title_keywords(
        self, title: str
    ) -> Optional[Tuple[Category, str, float, str]]:
        """Check if title contains known keywords."""
        title_lower = title.lower()
        
        for keyword, (category, usefulness, confidence) in self._title_keywords.items():
            if keyword in title_lower:
                return (category, usefulness, confidence, f"Title keyword: {keyword}")
        return None
    
    def _check_file_sharing_entertainment(
        self, url: str, domain: str, title: str = ""
    ) -> Optional[Tuple[Category, str, float, str]]:
        """Check if a file-sharing URL contains entertainment/fiction content.
        
        This detects movies, novels, and other entertainment content hosted
        on neutral platforms like Google Drive, Dropbox, etc.
        """
        # Only check file-sharing domains
        if domain not in self._file_sharing_domains:
            return None
        
        # Combine URL and title for keyword search
        search_text = f"{url} {title}".lower()
        
        # Check for fiction/entertainment keywords
        for keyword in self._fiction_keywords:
            if keyword in search_text:
                return (
                    Category.ENTERTAINMENT,
                    "DISTRACTION",
                    0.8,
                    f"Entertainment content on file-sharing: '{keyword}'"
                )
        
        # Check for video file extensions in URL
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
        url_lower = url.lower()
        for ext in video_extensions:
            if ext in url_lower:
                return (
                    Category.ENTERTAINMENT,
                    "DISTRACTION",
                    0.75,
                    f"Video file on file-sharing platform"
                )
        
        return None
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify a URL using rule-based patterns."""
        context = context or {}
        url = context.get("url", "")
        title = context.get("title", "")
        
        # Extract domain from URL if not provided
        url_domain = self._extract_domain(url) or domain.value
        
        # Priority 1: Check known domains
        domain_match = self._check_domain_patterns(url_domain)
        if domain_match:
            category, usefulness, confidence, reason = domain_match
            return Classification(
                domain=domain,
                category=category,
                confidence=confidence,
                metadata={
                    "classifier": self.name,
                    "usefulness": usefulness,
                    "reason": reason,
                    "is_distracting": usefulness == "DISTRACTION",
                }
            )
        
        # Priority 2: Check file-sharing platforms for entertainment content
        file_sharing_match = self._check_file_sharing_entertainment(url, url_domain, title)
        if file_sharing_match:
            category, usefulness, confidence, reason = file_sharing_match
            return Classification(
                domain=domain,
                category=category,
                confidence=confidence,
                metadata={
                    "classifier": self.name,
                    "usefulness": usefulness,
                    "reason": reason,
                    "is_distracting": usefulness == "DISTRACTION",
                }
            )
        
        # Priority 3: Check URL path patterns
        path_match = self._check_path_patterns(url)
        if path_match:
            category, usefulness, confidence, reason = path_match
            return Classification(
                domain=domain,
                category=category,
                confidence=confidence,
                metadata={
                    "classifier": self.name,
                    "usefulness": usefulness,
                    "reason": reason,
                    "is_distracting": usefulness == "DISTRACTION",
                }
            )
        
        # Priority 4: Check title keywords
        if title:
            title_match = self._check_title_keywords(title)
            if title_match:
                category, usefulness, confidence, reason = title_match
                return Classification(
                    domain=domain,
                    category=category,
                    confidence=confidence,
                    metadata={
                        "classifier": self.name,
                        "usefulness": usefulness,
                        "reason": reason,
                        "is_distracting": usefulness == "DISTRACTION",
                    }
                )
        
        # No match - return None to allow fallback to LLM
        return None


def create_url_rules_classifier() -> RuleBasedURLClassifier:
    """Factory function to create a URL rules classifier."""
    return RuleBasedURLClassifier()
