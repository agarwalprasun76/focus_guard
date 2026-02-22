"""
LLM-based generic URL classifier.

Uses LLM to classify any URL based on:
- URL structure and domain
- Page title
- Any available metadata

This is used when rule-based classification is uncertain or unavailable.
"""

import json
import logging
from typing import Dict, Any, Optional

from focus_guard.core.domain.models import Domain, Category, Classification
from focus_guard.core.classification.classifiers.domains.base import LLMBasedDomainClassifier

logger = logging.getLogger(__name__)

GENERIC_URL_SYSTEM_PROMPT = """You are a classifier for web content viewed by a 14-year-old student during study hours.
Your job is to determine if the content is educational/productive or distracting.

CATEGORIES (choose exactly one):
- EDUCATION: Learning resources, tutorials, documentation, academic content
- ENTERTAINMENT: Movies, TV, music, memes, viral content, celebrity gossip
- SOCIAL_MEDIA: Social platforms, messaging, forums (non-educational)
- GAMING: Games, game-related content, esports, streaming
- NEWS: Current events, news articles
- SHOPPING: E-commerce, product pages, shopping
- PRODUCTIVITY: Work tools, professional resources, coding platforms
- ADULT: Inappropriate content for minors
- UNKNOWN: Cannot determine

USEFULNESS (for a student during study hours):
- EDUCATIONAL: Directly supports learning and homework
- ENRICHMENT: Broadens knowledge, healthy curiosity
- NEUTRAL: Not harmful but not study-related
- DISTRACTION: Likely to derail focus from studying

IMPORTANT RULES:
1. Educational platforms (Khan Academy, Coursera, etc.) are always EDUCATION/EDUCATIONAL
2. Social media feeds are usually SOCIAL_MEDIA/DISTRACTION
3. Gaming content is GAMING/DISTRACTION
4. Streaming services (Netflix, etc.) are ENTERTAINMENT/DISTRACTION
5. Documentation and tutorials are EDUCATION/EDUCATIONAL
6. News can be ENRICHMENT unless it's celebrity gossip (DISTRACTION)

Output valid JSON only:
{
  "category": "EDUCATION|ENTERTAINMENT|SOCIAL_MEDIA|GAMING|NEWS|SHOPPING|PRODUCTIVITY|ADULT|UNKNOWN",
  "usefulness": "EDUCATIONAL|ENRICHMENT|NEUTRAL|DISTRACTION",
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}
"""

CATEGORIES = ["EDUCATION", "ENTERTAINMENT", "SOCIAL_MEDIA", "GAMING", "NEWS", "SHOPPING", "PRODUCTIVITY", "ADULT", "UNKNOWN"]
USEFULNESS = ["EDUCATIONAL", "ENRICHMENT", "NEUTRAL", "DISTRACTION"]


class LLMBasedURLClassifier(LLMBasedDomainClassifier):
    """LLM-based classifier for any URL."""
    
    def __init__(self, llm_client: Any, name: str = "url_llm"):
        super().__init__(
            name=name,
            llm_client=llm_client,
            system_prompt=GENERIC_URL_SYSTEM_PROMPT,
            response_format={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": CATEGORIES},
                    "usefulness": {"type": "string", "enum": USEFULNESS},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "reason": {"type": "string"},
                },
                "required": ["category", "usefulness", "confidence", "reason"]
            }
        )
        self._classification_cache = {}
        self._cache_max_size = 200
    
    def _format_prompt(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format the prompt for URL classification."""
        ctx = context or {}
        
        url = ctx.get('url', '')
        title = ctx.get('title', '')
        description = ctx.get('description', '')
        
        prompt_parts = [
            f"Classify this web content for a student during study hours:",
            f"",
            f"Domain: {domain.value}",
            f"URL: {url}" if url else "",
            f"Page Title: {title}" if title else "",
            f"Description: {description[:200]}" if description else "",
        ]
        
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
                "ADULT": Category.ADULT,
                "UNKNOWN": Category.UNKNOWN,
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
                    "is_distracting": usefulness == "DISTRACTION",
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to parse URL LLM response: {e}, raw: {response[:200]}")
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
        """Classify any URL using LLM."""
        ctx = context or {}
        
        # Create cache key
        url = ctx.get('url', domain.value)
        cache_key = f"url:{url}"
        
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


def create_url_llm_classifier(llm_client: Any = None) -> Optional[LLMBasedURLClassifier]:
    """Factory function to create a URL LLM classifier."""
    if llm_client is None:
        try:
            from focus_guard.core.classification.classifiers.llm.openai_client import OpenAIClient
            llm_client = OpenAIClient(model="gpt-4o-mini")
        except Exception as e:
            logger.warning(f"Could not create OpenAI client for URL classifier: {e}")
            return None
    
    return LLMBasedURLClassifier(llm_client=llm_client)
