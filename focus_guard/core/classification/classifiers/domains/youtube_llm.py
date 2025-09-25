"""
LLM-based YouTube content classifier."""

import json
import logging
import os
from typing import Dict, Any, Optional

from focus_guard.core.domain.models import Domain, Category, Classification
from .base import LLMBasedDomainClassifier

logger = logging.getLogger(__name__)

# System prompt for YouTube classification
YOUTUBE_SYSTEM_PROMPT = """You are a meticulous classifier for YouTube content viewed by a 14-year-old student.
Classify strictly by the definitions below, then assess usefulness for educational purposes. 
Concert violin videos and orchestra should be classified as EDUCATION and useful.
Science and technology videos should be classified as EDUCATION and useful.
Coding and robotics videos should be classified as EDUCATION and useful.


CATEGORIES (choose exactly one - NO OTHER VALUES ALLOWED):
- EDUCATION: Academic subjects, skills, tutorials, explainers, lectures, how-to guides, coding lessons, maker/robotics.
- ENTERTAINMENT: Movies/TV/trailers, comedy/skits, celebrity/gossip, memes, reaction, ASMR, general fun content, music videos.
- SOCIAL_MEDIA: Challenges, trends, platform-centric content (TikTok/shorts compilations, influencer drama).
- GAMING: Let's plays, walkthroughs, streams, esports, game commentary. (Game **development/modding/coding** belongs to EDUCATION.)
- NEWS: News reports, current events, interviews, analysis of public affairs. (Kid-focused news can still be NEWS.)
- SHOPPING: Product reviews, unboxings, deals, hauls, buyer's guides.
- SPORTS: Sports highlights, analysis, training drills, fitness routines, yoga, martial arts.
- ADULT: Explicit/mature (18+), sexually explicit, strongly age-inappropriate material.
- MALICIOUS: Harmful, deceptive, illegal instructions, scams, malware.

CRITICAL: If you cannot determine the exact category, default to ENTERTAINMENT. NEVER use "UNKNOWN", "NEUTRAL", "OTHER", or any category not listed above.

USEFULNESS (choose exactly one for a 13-year-old during study hours):
- EDUCATIONAL: Directly supports learning (school subjects, skills, structured how-tos, violin instrument lessons and concerts).
- ENRICHMENT: Broadens knowledge/healthy habits (fitness drills, kid-appropriate news explainers, museum/history culture).
- NEUTRAL: Not obviously helpful or harmful; acceptable in breaks but not study-supportive.
- DISTRACTION: Likely to derail focus (endless memes, pranks, reaction chains, celebrity gossip, binge gaming streams).
Rules of thumb:
- “Coding in Minecraft” or “physics of games” → EDUCATION.
- Music lessons/performance technique → EDUCATION/ENRICHMENT; music videos for entertainment → DISTRACTION.
- Sports training drills/workouts → ENRICHMENT (or EDUCATIONAL if instructional).
- Trailers/pranks/reaction compilations/ASMR → usually DISTRACTION.

IMPORTANT:
- Metadata may be any language; classify by meaning.
- Output **valid JSON only** (no code fences, no extra text).
- The "category" field MUST be one of the 9 categories listed above (EDUCATION, ENTERTAINMENT, etc.)
- The "usefulness" field is separate and MUST be one of: EDUCATIONAL, ENRICHMENT, NEUTRAL, DISTRACTION
- DO NOT confuse category with usefulness - they are different fields!
- Fields:
  {
    "category": "EDUCATION|ENTERTAINMENT|SOCIAL_MEDIA|GAMING|NEWS|SHOPPING|SPORTS|ADULT|MALICIOUS",
    "usefulness": "EDUCATIONAL|ENRICHMENT|NEUTRAL|DISTRACTION",
    "confidence": 0.0-1.0,
    "reason": "brief, 1-2 sentences",
    "is_distracting": true|false,
    "content_type": "video|channel|playlist|live|shorts|unknown"
  }
- Set is_distracting = (usefulness == "DISTRACTION").
"""

import json
import logging
from typing import Dict, Any, Optional

from focus_guard.core.domain.models import Domain, Category, Classification
from .base import LLMBasedDomainClassifier

logger = logging.getLogger(__name__)

CATEGORIES = ["EDUCATION","ENTERTAINMENT","SOCIAL_MEDIA","GAMING","NEWS","SHOPPING","SPORTS","ADULT","MALICIOUS"]
USEFULNESS = ["EDUCATIONAL","ENRICHMENT","NEUTRAL","DISTRACTION"]
CONTENT_TYPES = ["video","channel","playlist","live","shorts","unknown"]

def _infer_content_type(ctx: Dict[str, Any]) -> str:
    # Best-effort local inference to reduce LLM load
    duration = (ctx.get("duration") or "").lower()
    if isinstance(duration, str) and duration.startswith("pt"):  # ISO8601 like PT1M5S
        # Rough parse: treat <= 70 seconds as shorts
        try:
            import re
            m = re.findall(r'(\d+)M', duration)
            minutes = int(m[0]) if m else 0
            s = re.findall(r'(\d+)S', duration)
            seconds = int(s[0]) if s else 0
            total = minutes*60 + seconds
            if total and total <= 70:
                return "shorts"
        except Exception:
            pass
    if ctx.get("live_broadcast_content") == "live" or ctx.get("is_live"):
        return "live"
    return "unknown"

def _clean_json_text(text: str) -> str:
    # Strip code fences / prose if the model ignored instructions
    txt = text.strip()
    if "```" in txt:
        # Prefer fenced json if present
        if "```json" in txt.lower():
            try:
                return txt.lower().split("```json",1)[1].split("```",1)[0].strip()
            except Exception:
                pass
        # Fall back to first fenced block
        try:
            return txt.split("```",1)[1].split("```",1)[0].strip()
        except Exception:
            pass
    return txt

class LLMBasedYouTubeClassifier(LLMBasedDomainClassifier):
    def __init__(self, llm_client: Any, name: str = "youtube_llm"):
        super().__init__(
            name=name,
            llm_client=llm_client,
            system_prompt=YOUTUBE_SYSTEM_PROMPT,
            response_format={  # keep your tool/JSON schema hints
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": CATEGORIES},
                    "usefulness": {"type": "string", "enum": USEFULNESS},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "reason": {"type": "string"},
                    "is_distracting": {"type": "boolean"},
                    "content_type": {"type": "string", "enum": CONTENT_TYPES}
                },
                "required": ["category", "usefulness", "confidence", "reason", "is_distracting", "content_type"]
            }
        )
        # Add simple in-memory cache for performance
        self._classification_cache = {}
        self._cache_max_size = 100
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify YouTube content using LLM approach with caching."""
        # Return None for non-YouTube domains (same as rule-based classifier)
        if 'youtube.com' not in domain.value and 'youtu.be' not in domain.value:
            return None
        
        # Create cache key based on video ID or URL
        ctx = context or {}
        cache_key = None
        if 'video_id' in ctx:
            cache_key = f"video_id:{ctx['video_id']}"
        elif 'url' in ctx:
            cache_key = f"url:{ctx['url']}"
        
        # Check cache first
        if cache_key and cache_key in self._classification_cache:
            logger.debug(f"Cache hit for {cache_key}")
            return self._classification_cache[cache_key]
        
        # Use parent class implementation for YouTube domains
        result = await super().classify(domain, context)
        
        # Cache the result if we have a cache key
        if cache_key and result is not None:
            # Manage cache size
            if len(self._classification_cache) >= self._cache_max_size:
                # Remove oldest entry (simple FIFO)
                oldest_key = next(iter(self._classification_cache))
                del self._classification_cache[oldest_key]
            
            self._classification_cache[cache_key] = result
            logger.debug(f"Cached result for {cache_key}")
        
        return result

    def _format_prompt(self, domain: Domain, context: Optional[Dict[str, Any]] = None) -> str:
        ctx = context or {}
        # Pre-compute hints
        content_type_hint = ctx.get("content_type") or _infer_content_type(ctx)
        priors = []
        title = (ctx.get("title") or "").lower()
        if any(k in title for k in ["trailer","prank","compilation","asmr","reaction"]):
            priors.append("likely_entertainment")
        if any(k in title for k in ["lecture","tutorial","lesson","how to","exam","practice","workout","drill","exercise","ap "]):
            priors.append("likely_educational_or_enrichment")
        if "minecraft" in title and any(k in title for k in ["coding","code","python","redstone","modding"]):
            priors.append("minecraft_coding_signal")

        prompt = f"""Classify the YouTube item for a 13-year-old student.

Metadata:
Title: {ctx.get('title','Unknown')}
Channel: {ctx.get('channel_title','Unknown channel')}
Views: {ctx.get('view_count','unknown')}
Likes: {ctx.get('like_count','unknown')}
Comments: {ctx.get('comment_count','unknown')}
Duration: {ctx.get('duration','unknown')}
Type (hint): {content_type_hint}
Language: {ctx.get('language','unknown')}

Description:
{ctx.get('description','No description')}

Heuristics/Priors (may be empty): {', '.join(priors) if priors else 'none'}

Return valid JSON ONLY with keys:
category, usefulness, confidence, reason, is_distracting, content_type
"""
        return prompt

    def _parse_response(self, response: str, domain: Domain, context: Optional[Dict[str, Any]] = None) -> Classification:
        raw = response
        
        # Handle None response from LLM client
        if raw is None:
            logger.error("LLM client returned None response")
            # Fallback to rule-based classification
            return Classification(
                domain=domain,
                category=Category.UNKNOWN,
                confidence=0.0,
                metadata={
                    'method': 'llm_fallback',
                    'reason': 'LLM client returned None response',
                    'error': 'API call failed'
                }
            )
        
        try:
            json_str = _clean_json_text(raw)
            data = json.loads(json_str)
        except Exception as e:
            logger.warning(f"Initial JSON parse failed: {e}. Raw: {raw[:4000]}")
            # Minimal repair: try to trim leading/trailing prose and retry
            try:
                json_str = json_str[json_str.find("{"): json_str.rfind("}")+1]
                data = json.loads(json_str)
            except Exception as e2:
                logger.error(f"Failed to parse LLM response: {e2}\nResponse: {raw}")
                # Return fallback classification instead of raising
                return Classification(
                    domain=domain,
                    category=Category.UNKNOWN,
                    confidence=0.0,
                    metadata={
                        'method': 'llm_fallback',
                        'reason': f'JSON parse failed: {e2}',
                        'raw_response': raw,
                        'error': str(e2)
                    }
                )

        # Validate & coerce
        cat = str(data.get("category","")).upper()
        if cat not in CATEGORIES:
            # Better fallback logic - log the issue but don't return None immediately
            logger.warning(f"LLM returned invalid category '{cat}' for YouTube content. Raw response: {raw[:200]}")
            title = (context or {}).get("title", "").lower()
            if "asmr" in title:
                cat = "ENTERTAINMENT"
            elif any(keyword in title for keyword in ["tutorial", "lesson", "how to", "learn", "education"]):
                cat = "EDUCATION"
            elif any(keyword in title for keyword in ["game", "gaming", "play", "minecraft", "fortnite"]):
                cat = "GAMING"
            elif any(keyword in title for keyword in ["news", "breaking", "report"]):
                cat = "NEWS"
            elif any(keyword in title for keyword in ["review", "unbox", "buy", "product"]):
                cat = "SHOPPING"
            else:
                # Default to ENTERTAINMENT for YouTube content rather than returning None
                logger.info(f"Using ENTERTAINMENT as fallback category for YouTube content with invalid LLM category")
                cat = "ENTERTAINMENT"
                
        use = str(data.get("usefulness","")).upper()
        if use not in USEFULNESS:
            use = "NEUTRAL"
            
        # Handle confidence with fallback
        try:
            conf = float(data.get("confidence"))
            if conf is None:
                logger.warning(f"LLM did not provide confidence value. Using fallback confidence. Raw response: {raw[:200]}")
                conf = 0.7  # Reasonable fallback confidence
        except (ValueError, TypeError):
            logger.warning(f"LLM provided invalid confidence value: {data.get('confidence')}. Using fallback confidence. Raw response: {raw[:200]}")
            conf = 0.7  # Reasonable fallback confidence
            
        conf = max(0.0, min(1.0, conf))

        # Map to internal Category enum
        category_map = {
            'EDUCATION': Category.EDUCATION,
            'ENTERTAINMENT': Category.ENTERTAINMENT,
            'SOCIAL_MEDIA': Category.SOCIAL_MEDIA,
            'GAMING': Category.GAMING,
            'NEWS': Category.NEWS,
            'SHOPPING': Category.SHOPPING,
            'SPORTS': Category.ENTERTAINMENT,  # Map SPORTS to ENTERTAINMENT since no SPORTS category exists
            'ADULT': Category.ADULT,
            'MALICIOUS': Category.MALICIOUS
        }
        category = category_map.get(cat)
        if category is None:
            logger.error(f"Invalid category '{cat}' not found in category_map. Using ENTERTAINMENT as fallback.")
            category = Category.ENTERTAINMENT

        is_distracting = bool(data.get("is_distracting", use == "DISTRACTION"))
        content_type = data.get("content_type","unknown")
        if content_type not in CONTENT_TYPES:
            content_type = _infer_content_type(context or {}) or "unknown"

        metadata = {
            'method': 'llm',
            'reason': data.get('reason',''),
            'usefulness': use,
            'is_distracting': is_distracting,
            'content_type': content_type,
            'raw_response': raw,
            'input_title': (context or {}).get('title'),
            'input_channel': (context or {}).get('channel_title'),
        }

        return Classification(
            domain=domain,
            category=category,
            confidence=conf,
            metadata=metadata
        )
