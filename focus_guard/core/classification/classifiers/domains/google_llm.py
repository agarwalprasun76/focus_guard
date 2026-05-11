"""
LLM-based Google Search classifier.

Uses LLM to classify Google search queries and results with nuanced understanding
of user intent, especially for ambiguous cases like PDFs that could be
educational or entertainment (novels/fiction).
"""

import json
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs, unquote

from focus_guard.core.domain.models import Domain, Category, Classification
from .base import LLMBasedDomainClassifier

logger = logging.getLogger(__name__)

GOOGLE_SYSTEM_PROMPT = """You are a classifier for Google Search activity viewed by a 14-year-old student during study hours.
Your job is to determine if the search activity is educational/productive or distracting.

CATEGORIES (choose exactly one):
- EDUCATION: Academic research, homework help, learning resources, tutorials, textbooks, study materials
- ENTERTAINMENT: Movies, TV shows, music, games, memes, viral content, celebrity gossip
- SOCIAL_MEDIA: Social platform searches, influencer content, trending topics
- GAMING: Game-related searches, walkthroughs, cheats, gaming news
- NEWS: Current events, news articles (can be educational or distracting depending on topic)
- SHOPPING: Product searches, price comparisons, buying guides
- PRODUCTIVITY: Work tools, productivity apps, professional resources

SPECIAL FOCUS - PDF/Book Detection:
- Academic PDFs (textbooks, research papers, lecture notes) → EDUCATION
- Fiction novels, romance, fantasy, web novels, fanfiction → ENTERTAINMENT (distracting during study)
- Self-help, non-fiction learning → EDUCATION
- Comic books, manga, light novels → ENTERTAINMENT

USEFULNESS (for a student during study hours):
- EDUCATIONAL: Directly supports learning and homework
- ENRICHMENT: Broadens knowledge, healthy curiosity
- NEUTRAL: Not harmful but not study-related
- DISTRACTION: Likely to derail focus from studying

IMPORTANT:
- A search for "harry potter pdf" is ENTERTAINMENT (fiction novel)
- A search for "calculus textbook pdf" is EDUCATION
- A search for "python tutorial" is EDUCATION
- A search for "fortnite tips" is GAMING/DISTRACTION
- Google Scholar searches are almost always EDUCATION

Output valid JSON only:
{
  "category": "EDUCATION|ENTERTAINMENT|SOCIAL_MEDIA|GAMING|NEWS|SHOPPING|PRODUCTIVITY",
  "usefulness": "EDUCATIONAL|ENRICHMENT|NEUTRAL|DISTRACTION",
  "confidence": 0.0-1.0,
  "reason": "brief explanation",
  "is_pdf": true|false,
  "content_type": "search|pdf|images|videos|scholar|shopping|maps|docs"
}
"""

CATEGORIES = ["EDUCATION", "ENTERTAINMENT", "SOCIAL_MEDIA", "GAMING", "NEWS", "SHOPPING", "PRODUCTIVITY"]
USEFULNESS = ["EDUCATIONAL", "ENRICHMENT", "NEUTRAL", "DISTRACTION"]


class LLMBasedGoogleClassifier(LLMBasedDomainClassifier):
    """LLM-based classifier for Google Search and results."""
    
    GOOGLE_DOMAINS = [
        'google.com', 'www.google.com',
        'google.co.uk', 'google.ca', 'google.com.au',
        'google.co.in', 'google.de', 'google.fr',
    ]
    
    def __init__(self, llm_client: Any, name: str = "google_llm"):
        super().__init__(
            name=name,
            llm_client=llm_client,
            system_prompt=GOOGLE_SYSTEM_PROMPT,
            response_format={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": CATEGORIES},
                    "usefulness": {"type": "string", "enum": USEFULNESS},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "reason": {"type": "string"},
                    "is_pdf": {"type": "boolean"},
                    "content_type": {"type": "string"}
                },
                "required": ["category", "usefulness", "confidence", "reason"]
            }
        )
        self._classification_cache = {}
        self._cache_max_size = 100
    
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
            if 'q' in params:
                return unquote(params['q'][0])
            return None
        except Exception:
            return None
    
    def _detect_content_type(self, url: str) -> str:
        """Detect what type of Google content this is."""
        url_lower = url.lower()
        
        if 'tbm=isch' in url_lower or '/images' in url_lower:
            return 'images'
        elif 'tbm=vid' in url_lower:
            return 'videos'
        elif 'tbm=nws' in url_lower:
            return 'news'
        elif 'tbm=shop' in url_lower:
            return 'shopping'
        elif 'tbm=bks' in url_lower or '/books' in url_lower:
            return 'books'
        elif '/scholar' in url_lower:
            return 'scholar'
        elif 'drive.google' in url_lower:
            return 'drive'
        elif 'docs.google' in url_lower:
            return 'docs'
        elif url_lower.endswith('.pdf') or '[pdf]' in url_lower:
            return 'pdf'
        elif '/search' in url_lower:
            return 'search'
        
        return 'unknown'
    
    def _format_prompt(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format the prompt for Google classification."""
        ctx = context or {}
        
        url = ctx.get('url', '')
        query = self._extract_search_query(url) or ctx.get('query', '')
        title = ctx.get('title', '')
        content_type = self._detect_content_type(url)
        
        # Check for PDF indicators
        is_pdf = (
            url.lower().endswith('.pdf') or
            '[pdf]' in title.lower() or
            content_type == 'pdf'
        )
        
        prompt_parts = [
            f"Classify this Google activity for a student during study hours:",
            f"",
            f"URL: {url}",
            f"Search Query: {query}" if query else "",
            f"Page Title: {title}" if title else "",
            f"Content Type: {content_type}",
            f"Is PDF: {is_pdf}",
        ]
        
        if ctx.get('description'):
            prompt_parts.append(f"Description: {ctx['description'][:200]}")
        
        return "\n".join(p for p in prompt_parts if p)
    
    def _parse_response(
        self,
        response: str,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Classification:
        """Parse LLM response into Classification."""
        try:
            # Clean response
            raw = response.strip()
            if "```" in raw:
                if "```json" in raw.lower():
                    raw = raw.lower().split("```json", 1)[1].split("```", 1)[0].strip()
                else:
                    raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
            
            data = json.loads(raw)
            
            # Validate category
            cat = data.get("category", "UNKNOWN").upper()
            if cat not in CATEGORIES:
                logger.warning(f"Invalid category from LLM: {cat}")
                cat = "UNKNOWN"
            
            # Map to Category enum
            category_map = {
                "EDUCATION": Category.EDUCATION,
                "ENTERTAINMENT": Category.ENTERTAINMENT,
                "SOCIAL_MEDIA": Category.SOCIAL_MEDIA,
                "GAMING": Category.GAMING,
                "NEWS": Category.NEWS,
                "SHOPPING": Category.SHOPPING,
                "PRODUCTIVITY": Category.PRODUCTIVITY,
            }
            category = category_map.get(cat, Category.UNKNOWN)
            
            usefulness = data.get("usefulness", "NEUTRAL").upper()
            if usefulness not in USEFULNESS:
                usefulness = "NEUTRAL"
            
            return Classification(
                domain=domain,
                category=category,
                confidence=float(data.get("confidence", 0.7)),
                metadata={
                    "classifier": self.name,
                    "usefulness": usefulness,
                    "reason": data.get("reason", ""),
                    "is_pdf": data.get("is_pdf", False),
                    "content_type": data.get("content_type", "unknown"),
                    "is_distracting": usefulness == "DISTRACTION",
                }
            )
            
        except Exception as e:
            preview = (response[:200] if isinstance(response, str) else "") or "(no text)"
            logger.error("Failed to parse Google LLM response: %s, raw: %s", e, preview)
            return Classification(
                domain=domain,
                category=Category.UNKNOWN,
                confidence=0.5,
                metadata={
                    "classifier": self.name,
                    "usefulness": "NEUTRAL",
                    "reason": "Failed to parse LLM response",
                    "error": str(e),
                }
            )
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify Google search activity."""
        # Only handle Google domains
        if not self._is_google_domain(domain.value):
            return None
        
        ctx = context or {}
        
        # Create cache key
        url = ctx.get('url', '')
        query = self._extract_search_query(url)
        cache_key = f"google:{query or url}"
        
        # Check cache
        if cache_key in self._classification_cache:
            logger.debug(f"Cache hit for {cache_key}")
            return self._classification_cache[cache_key]
        
        # Call parent LLM classify
        result = await super().classify(domain, context)
        
        # Cache result
        if result and cache_key:
            if len(self._classification_cache) >= self._cache_max_size:
                oldest = next(iter(self._classification_cache))
                del self._classification_cache[oldest]
            self._classification_cache[cache_key] = result
        
        return result


def create_google_llm_classifier(llm_client: Any = None) -> Optional[LLMBasedGoogleClassifier]:
    """Factory function to create a Google LLM classifier."""
    if llm_client is None:
        try:
            from focus_guard.core.classification.classifiers.llm.openai_client import OpenAIClient
            llm_client = OpenAIClient(model="gpt-4o-mini")
        except Exception as e:
            logger.warning(f"Could not create OpenAI client for Google classifier: {e}")
            return None
    
    return LLMBasedGoogleClassifier(llm_client=llm_client)
