"""
Rule-based Google Search classifier.

Classifies Google search pages and results based on:
- Search query content
- Result types (PDF, images, videos, news, shopping)
- URL patterns indicating content type
"""

import logging
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs, unquote

from focus_guard.core.domain.models import Domain, Category, Classification

from .base import RuleBasedDomainClassifier

logger = logging.getLogger(__name__)


class RuleBasedGoogleClassifier(RuleBasedDomainClassifier):
    """Rule-based classifier for Google Search and related services."""
    
    # Google domains to handle
    GOOGLE_DOMAINS = [
        'google.com', 'www.google.com',
        'google.co.uk', 'google.ca', 'google.com.au',
        'google.co.in', 'google.de', 'google.fr',
    ]
    
    # Educational search query keywords
    EDUCATIONAL_KEYWORDS = [
        'tutorial', 'how to', 'learn', 'course', 'lesson', 'education',
        'study', 'homework', 'assignment', 'exam', 'test prep',
        'programming', 'coding', 'algorithm', 'data structure',
        'math', 'science', 'physics', 'chemistry', 'biology',
        'history', 'geography', 'literature', 'essay',
        'research', 'academic', 'paper', 'thesis', 'dissertation',
        'textbook', 'lecture', 'university', 'college', 'school',
        'khan academy', 'coursera', 'edx', 'udemy',
    ]
    
    # Distracting/entertainment search keywords
    ENTERTAINMENT_KEYWORDS = [
        'movie', 'film', 'tv show', 'series', 'netflix', 'streaming',
        'game', 'gaming', 'gameplay', 'walkthrough', 'cheat',
        'celebrity', 'gossip', 'drama', 'scandal',
        'meme', 'funny', 'viral', 'tiktok', 'instagram',
        'music video', 'lyrics', 'song',
        'free download', 'torrent', 'pirate',
    ]
    
    # Fiction/novel keywords (potentially distracting during study)
    FICTION_KEYWORDS = [
        'novel', 'fiction', 'story', 'romance', 'fantasy', 'sci-fi',
        'thriller', 'mystery', 'horror', 'adventure',
        'wattpad', 'fanfiction', 'fanfic', 'ao3',
        'light novel', 'web novel', 'manga', 'comic',
        'epub', 'kindle', 'ebook',
        # Popular fiction series
        'harry potter', 'hunger games', 'twilight', 'divergent',
        'percy jackson', 'maze runner', 'lord of the rings', 'hobbit',
        'game of thrones', 'narnia', 'eragon', 'artemis fowl',
    ]
    
    # Academic/productive PDF indicators
    ACADEMIC_PDF_KEYWORDS = [
        'textbook', 'manual', 'guide', 'documentation',
        'research', 'paper', 'journal', 'article',
        'thesis', 'dissertation', 'report',
        'lecture notes', 'slides', 'syllabus',
        'solution', 'answer key', 'worksheet',
    ]
    
    # Shopping keywords
    SHOPPING_KEYWORDS = [
        'buy', 'price', 'cheap', 'discount', 'sale', 'deal',
        'amazon', 'ebay', 'walmart', 'target',
        'review', 'best', 'top 10', 'comparison',
        'shopping', 'store', 'shop',
    ]
    
    def __init__(self):
        super().__init__(name="google_rules")
        self._logger = logging.getLogger(__name__)
    
    def _get_rules(self) -> Dict[str, Any]:
        """Return classification rules."""
        return {
            "educational_keywords": self.EDUCATIONAL_KEYWORDS,
            "entertainment_keywords": self.ENTERTAINMENT_KEYWORDS,
            "fiction_keywords": self.FICTION_KEYWORDS,
            "shopping_keywords": self.SHOPPING_KEYWORDS,
        }
    
    def _is_google_domain(self, domain: str) -> bool:
        """Check if domain is a Google domain."""
        domain_lower = domain.lower()
        return any(
            domain_lower == g or domain_lower.endswith('.' + g)
            for g in self.GOOGLE_DOMAINS
        )
    
    def _extract_search_query(self, url: str) -> Optional[str]:
        """Extract search query from Google URL."""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Google uses 'q' parameter for search query
            if 'q' in params:
                return unquote(params['q'][0]).lower()
            
            return None
        except Exception:
            return None
    
    def _detect_result_type(self, url: str) -> str:
        """Detect what type of Google result page this is."""
        url_lower = url.lower()
        
        if '/search?' in url_lower:
            # Check for specific search types
            if 'tbm=isch' in url_lower:
                return 'images'
            elif 'tbm=vid' in url_lower:
                return 'videos'
            elif 'tbm=nws' in url_lower:
                return 'news'
            elif 'tbm=shop' in url_lower:
                return 'shopping'
            elif 'tbm=bks' in url_lower:
                return 'books'
            else:
                return 'web'
        elif '/images' in url_lower:
            return 'images'
        elif '/maps' in url_lower:
            return 'maps'
        elif '/scholar' in url_lower:
            return 'scholar'  # Google Scholar - academic
        elif '/books' in url_lower:
            return 'books'
        elif 'drive.google' in url_lower:
            return 'drive'
        elif 'docs.google' in url_lower:
            return 'docs'
        elif 'sheets.google' in url_lower:
            return 'sheets'
        elif 'slides.google' in url_lower:
            return 'slides'
        
        return 'unknown'
    
    def _is_pdf_link(self, url: str, context: Dict[str, Any]) -> bool:
        """Check if this is a link to a PDF."""
        url_lower = url.lower()
        
        # Direct PDF link
        if url_lower.endswith('.pdf'):
            return True
        
        # Google's PDF viewer
        if 'viewer.googleusercontent.com' in url_lower:
            return True
        
        # Check context for PDF indicators
        title = (context.get('title') or '').lower()
        if '[pdf]' in title or '(pdf)' in title or 'pdf' in title:
            return True
        
        return False
    
    def _classify_pdf_content(
        self, 
        query: str, 
        title: str,
        context: Dict[str, Any]
    ) -> tuple[Category, str, float]:
        """Classify PDF content based on query and title."""
        query_lower = query.lower() if query else ''
        title_lower = title.lower() if title else ''
        combined = f"{query_lower} {title_lower}"
        
        # Check for academic/educational PDFs
        academic_matches = [
            kw for kw in self.ACADEMIC_PDF_KEYWORDS 
            if kw in combined
        ]
        if academic_matches:
            return (
                Category.EDUCATION,
                f"Academic PDF detected: {', '.join(academic_matches[:3])}",
                0.85
            )
        
        # Check for fiction/novel PDFs (potentially distracting)
        fiction_matches = [
            kw for kw in self.FICTION_KEYWORDS 
            if kw in combined
        ]
        if fiction_matches:
            return (
                Category.ENTERTAINMENT,
                f"Fiction/novel PDF detected: {', '.join(fiction_matches[:3])}",
                0.8
            )
        
        # Check for educational keywords
        edu_matches = [
            kw for kw in self.EDUCATIONAL_KEYWORDS 
            if kw in combined
        ]
        if edu_matches:
            return (
                Category.EDUCATION,
                f"Educational PDF: {', '.join(edu_matches[:3])}",
                0.75
            )
        
        # Default: unknown PDF - could be either
        return (
            Category.UNKNOWN,
            "PDF content - classification uncertain",
            0.5
        )
    
    def _classify_search_query(
        self, 
        query: str,
        result_type: str
    ) -> tuple[Category, str, float]:
        """Classify based on search query content."""
        query_lower = query.lower()
        
        # Google Scholar is always academic
        if result_type == 'scholar':
            return (
                Category.EDUCATION,
                "Google Scholar search (academic)",
                0.9
            )
        
        # Shopping searches
        if result_type == 'shopping':
            return (
                Category.SHOPPING,
                "Google Shopping search",
                0.85
            )
        
        # Check for educational queries
        edu_matches = [
            kw for kw in self.EDUCATIONAL_KEYWORDS 
            if kw in query_lower
        ]
        if edu_matches:
            return (
                Category.EDUCATION,
                f"Educational search: {', '.join(edu_matches[:3])}",
                0.8
            )
        
        # Check for entertainment queries
        ent_matches = [
            kw for kw in self.ENTERTAINMENT_KEYWORDS 
            if kw in query_lower
        ]
        if ent_matches:
            return (
                Category.ENTERTAINMENT,
                f"Entertainment search: {', '.join(ent_matches[:3])}",
                0.8
            )
        
        # Check for fiction/novel queries
        fiction_matches = [
            kw for kw in self.FICTION_KEYWORDS 
            if kw in query_lower
        ]
        if fiction_matches:
            return (
                Category.ENTERTAINMENT,
                f"Fiction/novel search: {', '.join(fiction_matches[:3])}",
                0.75
            )
        
        # Check for shopping queries
        shop_matches = [
            kw for kw in self.SHOPPING_KEYWORDS 
            if kw in query_lower
        ]
        if shop_matches:
            return (
                Category.SHOPPING,
                f"Shopping search: {', '.join(shop_matches[:3])}",
                0.75
            )
        
        # Image/video searches are often entertainment
        if result_type in ('images', 'videos'):
            return (
                Category.ENTERTAINMENT,
                f"Google {result_type} search (likely entertainment)",
                0.6
            )
        
        # Default: neutral/unknown
        return (
            Category.UNKNOWN,
            "General web search",
            0.5
        )
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify a Google search or result page."""
        context = context or {}
        
        # Only handle Google domains
        if not self._is_google_domain(domain.value):
            return None
        
        url = context.get('url', '')
        title = context.get('title', '')
        
        # Detect result type
        result_type = self._detect_result_type(url)
        
        # Extract search query
        query = self._extract_search_query(url)
        
        self._logger.info(
            f"Google classification - Type: {result_type}, Query: {query[:50] if query else 'N/A'}"
        )
        
        # Google Docs/Sheets/Slides are productivity tools
        if result_type in ('docs', 'sheets', 'slides', 'drive'):
            return Classification(
                domain=domain,
                category=Category.PRODUCTIVITY,
                confidence=0.9,
                metadata={
                    'classifier': self.name,
                    'result_type': result_type,
                    'usefulness': 'EDUCATIONAL',
                    'reason': f"Google {result_type.title()} - productivity tool",
                }
            )
        
        # Check if this is a PDF link
        if self._is_pdf_link(url, context):
            category, reason, confidence = self._classify_pdf_content(
                query or '', title, context
            )
            
            # Determine usefulness based on category
            if category == Category.EDUCATION:
                usefulness = 'EDUCATIONAL'
            elif category == Category.ENTERTAINMENT:
                usefulness = 'DISTRACTION'
            else:
                usefulness = 'NEUTRAL'
            
            return Classification(
                domain=domain,
                category=category,
                confidence=confidence,
                metadata={
                    'classifier': self.name,
                    'result_type': 'pdf',
                    'query': query,
                    'usefulness': usefulness,
                    'reason': reason,
                    'is_pdf': True,
                }
            )
        
        # Classify based on search query
        if query:
            category, reason, confidence = self._classify_search_query(
                query, result_type
            )
            
            # Determine usefulness
            if category == Category.EDUCATION:
                usefulness = 'EDUCATIONAL'
            elif category in (Category.ENTERTAINMENT, Category.GAMING):
                usefulness = 'DISTRACTION'
            elif category == Category.SHOPPING:
                usefulness = 'NEUTRAL'
            else:
                usefulness = 'NEUTRAL'
            
            return Classification(
                domain=domain,
                category=category,
                confidence=confidence,
                metadata={
                    'classifier': self.name,
                    'result_type': result_type,
                    'query': query,
                    'usefulness': usefulness,
                    'reason': reason,
                }
            )
        
        # No query - just browsing Google
        return Classification(
            domain=domain,
            category=Category.UNKNOWN,
            confidence=0.5,
            metadata={
                'classifier': self.name,
                'result_type': result_type,
                'usefulness': 'NEUTRAL',
                'reason': 'Google browsing - no specific query detected',
            }
        )


def create_google_rules_classifier() -> RuleBasedGoogleClassifier:
    """Factory function to create a Google rules classifier."""
    return RuleBasedGoogleClassifier()
