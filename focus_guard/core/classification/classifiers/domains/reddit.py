"""
Reddit domain classifier implementation.

Classifies Reddit content based on:
1. Subreddit category (r/programming = productive, r/memes = distraction)
2. Content type (post, comments, search, user profile)
3. Title/content keywords via LLM fallback

Following the YouTube classifier pattern:
- Rule-based for fast, cheap decisions
- LLM fallback for nuanced content analysis
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass

from focus_guard.core.domain.models import Domain, Category, Classification
from .base import (
    BaseDomainClassifier, 
    RuleBasedDomainClassifier, 
    LLMBasedDomainClassifier,
    parse_llm_classification_response,
)

logger = logging.getLogger(__name__)


# Reddit-specific LLM system prompt
REDDIT_SYSTEM_PROMPT = """You are a classifier for Reddit content viewed by a 14-year-old student during study hours.
Your job is to classify the SUBREDDIT CONTENT, not the Reddit platform itself.

Focus on the subreddit name and post title to determine if the content is educational or distracting.

CATEGORIES (choose exactly one):
- EDUCATION: Academic subjects, programming, science, math, learning resources, tutorials, homework help
- ENTERTAINMENT: Memes, funny content, movies, TV shows, celebrity gossip, viral content
- SOCIAL_MEDIA: General social discussion, relationship advice, casual conversation, personal stories
- GAMING: Video games, esports, game discussions, gaming memes
- NEWS: Current events, world news, politics, journalism
- PRODUCTIVITY: Career advice, self-improvement, productivity tips, professional development
- ADULT: NSFW content, inappropriate for minors
- UNKNOWN: Cannot determine

USEFULNESS (for a student during study hours):
- EDUCATIONAL: Directly supports learning (r/learnprogramming, r/AskHistorians, r/explainlikeimfive)
- ENRICHMENT: Broadens knowledge, healthy curiosity (r/science, r/todayilearned, r/AskEngineers)
- NEUTRAL: Not harmful but not study-related (r/casualconversation)
- DISTRACTION: Likely to derail focus (r/memes, r/funny, r/gaming, r/blursedimages)

IMPORTANT RULES:
1. Focus on the SUBREDDIT TOPIC, not that it's on Reddit
2. r/AskHistorians, r/AskScience, r/explainlikeimfive = EDUCATION/EDUCATIONAL
3. r/learnprogramming, r/learnmath, r/homework_help = EDUCATION/EDUCATIONAL  
4. r/memes, r/funny, r/blursedimages, r/cursedcomments = ENTERTAINMENT/DISTRACTION
5. r/Showerthoughts, r/unpopularopinion = SOCIAL_MEDIA/DISTRACTION
6. r/news, r/worldnews = NEWS/ENRICHMENT
7. Programming subreddits (even obscure ones) = EDUCATION/EDUCATIONAL

Output valid JSON only:
{
  "category": "EDUCATION|ENTERTAINMENT|SOCIAL_MEDIA|GAMING|NEWS|PRODUCTIVITY|ADULT|UNKNOWN",
  "usefulness": "EDUCATIONAL|ENRICHMENT|NEUTRAL|DISTRACTION",
  "confidence": 0.0-1.0,
  "reason": "brief explanation focusing on subreddit content"
}
"""

CATEGORIES = ["EDUCATION", "ENTERTAINMENT", "SOCIAL_MEDIA", "GAMING", "NEWS", "PRODUCTIVITY", "ADULT", "UNKNOWN"]
USEFULNESS = ["EDUCATIONAL", "ENRICHMENT", "NEUTRAL", "DISTRACTION"]


# Subreddit categories - curated lists
PRODUCTIVE_SUBREDDITS = {
    # Programming/Tech
    "programming", "python", "javascript", "java", "cpp", "rust", "golang",
    "webdev", "frontend", "backend", "devops", "machinelearning", "datascience",
    "learnprogramming", "cscareerquestions", "experienceddevs", "coding",
    "softwareengineering", "compsci", "algorithms", "leetcode",
    # Education
    "learnmath", "math", "physics", "chemistry", "biology", "science",
    "askscience", "explainlikeimfive", "todayilearned", "education",
    "college", "gradschool", "homework_help", "apstudents",
    # Productivity
    "productivity", "getdisciplined", "decidingtobebetter", "selfimprovement",
    "getmotivated", "zenhabits", "minimalism", "financialindependence",
    # Career/Professional
    "jobs", "careerguidance", "resumes", "interviews", "entrepreneur",
    "startups", "business", "marketing", "sales",
    # News/Current Events (informational)
    "news", "worldnews", "technology", "futurology", "space",
}

ENTERTAINMENT_SUBREDDITS = {
    # Memes/Humor
    "memes", "dankmemes", "funny", "jokes", "comedyheaven", "me_irl",
    "wholesomememes", "prequelmemes", "historymemes", "animemes",
    # Gaming
    "gaming", "games", "pcgaming", "ps5", "xbox", "nintendoswitch",
    "minecraft", "fortnite", "leagueoflegends", "valorant", "dota2",
    "roblox", "genshinimpact", "pokemon", "zelda",
    # Entertainment Media
    "movies", "television", "netflix", "anime", "manga", "comics",
    "marvelstudios", "starwars", "harrypotter", "gameofthrones",
    # Social/Casual
    "askreddit", "casualconversation", "unpopularopinion", "amitheasshole",
    "relationship_advice", "tifu", "confessions", "offmychest",
    # Pictures/Videos
    "pics", "videos", "gifs", "aww", "eyebleach", "oddlysatisfying",
    "interestingasfuck", "nextfuckinglevel", "publicfreakout",
    # Sports
    "sports", "nba", "nfl", "soccer", "baseball", "hockey",
    # Music
    "music", "hiphopheads", "popheads", "indieheads", "kpop",
}

ADULT_SUBREDDITS = {
    "nsfw", "gonewild", "realgirls", "nsfw_gifs","nsfl"
    # Note: Reddit has many NSFW subreddits, this is just a sample
    # The classifier will also check for NSFW flags in the URL/content
}


@dataclass
class RedditURLInfo:
    """Parsed information from a Reddit URL."""
    subreddit: Optional[str] = None
    post_id: Optional[str] = None
    is_comments: bool = False
    is_search: bool = False
    is_user_profile: bool = False
    is_home_feed: bool = False
    is_popular: bool = False
    is_all: bool = False
    username: Optional[str] = None


class RuleBasedRedditClassifier(RuleBasedDomainClassifier):
    """Rule-based Reddit content classifier.
    
    Classifies Reddit URLs based on subreddit and content type.
    """
    
    def __init__(self, name: str = "reddit_rules"):
        super().__init__(name)
        self._productive_subreddits = PRODUCTIVE_SUBREDDITS
        self._entertainment_subreddits = ENTERTAINMENT_SUBREDDITS
        self._adult_subreddits = ADULT_SUBREDDITS
        
        # Title keywords for additional classification hints
        self._education_keywords = {
            "tutorial", "guide", "how to", "learn", "explained", "course",
            "beginner", "advanced", "tips", "help", "question", "eli5"
        }
        self._entertainment_keywords = {
            "meme", "funny", "lol", "lmao", "cursed", "blessed", "wholesome",
            "cringe", "based", "sus", "bruh", "oof"
        }
    
    def _get_rules(self) -> Dict[str, Any]:
        return {
            "productive_subreddits": self._productive_subreddits,
            "entertainment_subreddits": self._entertainment_subreddits,
            "adult_subreddits": self._adult_subreddits,
        }
    
    def _parse_reddit_url(self, url: str) -> RedditURLInfo:
        """Parse a Reddit URL to extract subreddit and content type."""
        info = RedditURLInfo()
        
        # Normalize URL
        url_lower = url.lower()
        
        # Check for home feed
        if re.search(r'reddit\.com/?$', url_lower) or re.search(r'reddit\.com/\?', url_lower):
            info.is_home_feed = True
            return info
        
        # Check for r/popular or r/all
        if '/r/popular' in url_lower:
            info.is_popular = True
            return info
        if '/r/all' in url_lower:
            info.is_all = True
            return info
        
        # Check for search
        if '/search' in url_lower:
            info.is_search = True
            return info
        
        # Check for user profile
        user_match = re.search(r'/u(?:ser)?/([^/?\s]+)', url_lower)
        if user_match:
            info.is_user_profile = True
            info.username = user_match.group(1)
            return info
        
        # Extract subreddit
        subreddit_match = re.search(r'/r/([^/?\s]+)', url_lower)
        if subreddit_match:
            info.subreddit = subreddit_match.group(1).lower()
            
            # Check if viewing comments
            if '/comments/' in url_lower:
                info.is_comments = True
                # Extract post ID
                post_match = re.search(r'/comments/([^/?\s]+)', url_lower)
                if post_match:
                    info.post_id = post_match.group(1)
        
        return info
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify Reddit content based on subreddit and URL structure."""
        context = context or {}
        url = context.get("url", "")
        title = context.get("title", "").lower()
        
        # Parse the URL
        info = self._parse_reddit_url(url)
        
        # Home feed, popular, all - these are distracting browsing
        if info.is_home_feed or info.is_popular or info.is_all:
            return Classification(
                domain=domain,
                category=Category.SOCIAL_MEDIA,
                confidence=0.85,
                metadata={
                    "usefulness": "DISTRACTION",
                    "classifier": self.name,
                    "reason": "Reddit home feed/popular/all is casual browsing"
                }
            )
        
        # Search - neutral, depends on what they're searching for
        if info.is_search:
            # Check search query in URL for entertainment keywords
            if any(kw in url.lower() for kw in self._entertainment_keywords):
                return Classification(
                    domain=domain,
                    category=Category.SOCIAL_MEDIA,
                    confidence=0.7,
                    metadata={
                        "usefulness": "DISTRACTION",
                        "classifier": self.name,
                        "reason": "Reddit search for entertainment content"
                    }
                )
            return None  # Let LLM decide
        
        # User profile - usually casual browsing
        if info.is_user_profile:
            return Classification(
                domain=domain,
                category=Category.SOCIAL_MEDIA,
                confidence=0.6,
                metadata={
                    "usefulness": "NEUTRAL",
                    "classifier": self.name,
                    "reason": "Reddit user profile browsing"
                }
            )
        
        # Subreddit-based classification
        if info.subreddit:
            # Check adult subreddits first
            if info.subreddit in self._adult_subreddits:
                return Classification(
                    domain=domain,
                    category=Category.ADULT,
                    confidence=0.95,
                    metadata={
                        "usefulness": "DISTRACTION",
                        "classifier": self.name,
                        "reason": f"r/{info.subreddit} is an adult subreddit"
                    }
                )
            
            # Check productive subreddits
            if info.subreddit in self._productive_subreddits:
                return Classification(
                    domain=domain,
                    category=Category.EDUCATION,
                    confidence=0.8,
                    metadata={
                        "usefulness": "EDUCATIONAL",
                        "classifier": self.name,
                        "reason": f"r/{info.subreddit} is a productive/educational subreddit"
                    }
                )
            
            # Check entertainment subreddits
            if info.subreddit in self._entertainment_subreddits:
                return Classification(
                    domain=domain,
                    category=Category.ENTERTAINMENT,
                    confidence=0.85,
                    metadata={
                        "usefulness": "DISTRACTION",
                        "classifier": self.name,
                        "reason": f"r/{info.subreddit} is an entertainment subreddit"
                    }
                )
            
            # Unknown subreddit - check title for hints
            if any(kw in title for kw in self._education_keywords):
                return Classification(
                    domain=domain,
                    category=Category.EDUCATION,
                    confidence=0.6,
                    metadata={
                        "usefulness": "ENRICHMENT",
                        "classifier": self.name,
                        "reason": f"r/{info.subreddit} post has educational keywords in title"
                    }
                )
            
            if any(kw in title for kw in self._entertainment_keywords):
                return Classification(
                    domain=domain,
                    category=Category.ENTERTAINMENT,
                    confidence=0.6,
                    metadata={
                        "usefulness": "DISTRACTION",
                        "classifier": self.name,
                        "reason": f"r/{info.subreddit} post has entertainment keywords in title"
                    }
                )
        
        # Can't determine from rules alone - return None to let LLM decide
        return None
    
    def add_productive_subreddit(self, subreddit: str) -> None:
        """Add a subreddit to the productive list."""
        self._productive_subreddits.add(subreddit.lower())
    
    def add_entertainment_subreddit(self, subreddit: str) -> None:
        """Add a subreddit to the entertainment list."""
        self._entertainment_subreddits.add(subreddit.lower())


class LLMBasedRedditClassifier(LLMBasedDomainClassifier):
    """LLM-based Reddit classifier for unknown subreddits.
    
    Uses a Reddit-specific prompt that focuses on subreddit content
    rather than classifying Reddit as a social media platform.
    """
    
    def __init__(self, llm_client: Any, name: str = "reddit_llm"):
        super().__init__(
            name=name,
            llm_client=llm_client,
            system_prompt=REDDIT_SYSTEM_PROMPT,
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
        self._cache_max_size = 100
    
    def _format_prompt(self, domain: Domain, context: Optional[Dict[str, Any]] = None) -> str:
        """Format the prompt for Reddit classification."""
        ctx = context or {}
        url = ctx.get("url", "")
        title = ctx.get("title", "")
        
        # Extract subreddit from URL
        subreddit = "unknown"
        subreddit_match = re.search(r'/r/([^/?\s]+)', url.lower())
        if subreddit_match:
            subreddit = subreddit_match.group(1)
        
        # Extract post title from URL if available
        post_title = ""
        if "/comments/" in url:
            # Try to extract readable title from URL slug
            parts = url.split("/")
            for i, part in enumerate(parts):
                if part == "comments" and i + 2 < len(parts):
                    post_title = parts[i + 2].replace("_", " ")
                    break
        
        prompt = f"""Classify this Reddit content for a 14-year-old student during study hours.

Subreddit: r/{subreddit}
URL: {url}
Page Title: {title if title else 'Not available'}
Post Title (from URL): {post_title if post_title else 'Not available'}

Focus on the SUBREDDIT TOPIC to determine if this is educational or distracting content.
Do NOT classify based on Reddit being a social media platform - classify based on the subreddit's subject matter.

Return valid JSON only with keys: category, usefulness, confidence, reason
"""
        return prompt
    
    def _parse_response(self, response: str, domain: Domain, context: Optional[Dict[str, Any]] = None) -> Classification:
        """Parse LLM response using shared utility."""
        return parse_llm_classification_response(
            response=response,
            domain=domain,
            classifier_name=self.name,
            categories=CATEGORIES,
            usefulness_values=USEFULNESS,
        )
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify Reddit content using LLM."""
        # Only handle Reddit domains
        domain_str = domain.value.lower() if hasattr(domain, 'value') else str(domain).lower()
        if 'reddit.com' not in domain_str:
            return None
        
        ctx = context or {}
        url = ctx.get("url", "")
        cache_key = f"reddit:{url}"
        
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


class RedditClassifier(BaseDomainClassifier):
    """Composite Reddit classifier combining rules and LLM.
    
    Tries rule-based classification first, falls back to LLM for
    unknown subreddits or ambiguous content.
    """
    
    SUPPORTED_DOMAINS = {"reddit.com", "www.reddit.com", "old.reddit.com", "new.reddit.com"}
    
    def __init__(
        self,
        classifiers: Optional[List[BaseDomainClassifier]] = None,
        name: str = "reddit_composite"
    ):
        super().__init__(name)
        self._classifiers = classifiers or [RuleBasedRedditClassifier()]
    
    def supports_domain(self, domain: str) -> bool:
        """Check if this classifier supports the given domain."""
        return domain.lower() in self.SUPPORTED_DOMAINS
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify Reddit content using the classifier chain."""
        for classifier in self._classifiers:
            try:
                result = await classifier.classify(domain, context)
                if result is not None:
                    return result
            except Exception as e:
                logger.warning("Classifier %s failed: %s", classifier.name, e)
        
        # Default: treat unknown Reddit content as social media distraction
        return Classification(
            domain=domain,
            category=Category.SOCIAL_MEDIA,
            confidence=0.5,
            metadata={
                "usefulness": "DISTRACTION",
                "classifier": self.name,
                "reason": "Unknown Reddit content, defaulting to distraction"
            }
        )


def create_reddit_llm_classifier(llm_client: Any = None) -> Optional[LLMBasedRedditClassifier]:
    """Factory function to create a Reddit-specific LLM classifier."""
    if llm_client is None:
        try:
            from focus_guard.core.classification.classifiers.llm.openai_client import OpenAIClient
            llm_client = OpenAIClient(model="gpt-4o-mini")
        except Exception as e:
            logger.warning(f"Could not create OpenAI client for Reddit classifier: {e}")
            return None
    
    return LLMBasedRedditClassifier(llm_client=llm_client)


def create_reddit_classifier(
    use_llm: bool = True,
    llm_client: Any = None
) -> RedditClassifier:
    """Create a Reddit classifier with the specified configuration.
    
    Args:
        use_llm: If True, use Reddit-specific LLM as fallback for unknown subreddits (default: True)
        llm_client: Optional LLM client. If None and use_llm=True, will try to create one.
    """
    classifiers: List[BaseDomainClassifier] = []
    
    # Always use rule-based first (fast)
    classifiers.append(RuleBasedRedditClassifier())
    
    # Add Reddit-specific LLM fallback for unknown subreddits
    if use_llm:
        try:
            llm_classifier = create_reddit_llm_classifier(llm_client)
            if llm_classifier:
                classifiers.append(llm_classifier)
                logger.info("Reddit classifier: Reddit-specific LLM fallback enabled")
        except Exception as e:
            logger.warning("Could not enable LLM fallback for Reddit: %s", e)
    
    return RedditClassifier(classifiers)


# Default instance
default_classifier = create_reddit_classifier()
