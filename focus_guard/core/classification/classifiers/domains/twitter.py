"""
Twitter/X domain classifier implementation.

Classifies Twitter content based on:
1. Content type (home feed, search, profile, specific tweet)
2. Profile category (news org, educational, entertainment)
3. Title/content keywords

Following the YouTube classifier pattern:
- Rule-based for fast, cheap decisions
- LLM fallback for nuanced content analysis
"""

import re
import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass

from focus_guard.core.domain.models import Domain, Category, Classification
from .base import BaseDomainClassifier, RuleBasedDomainClassifier

logger = logging.getLogger(__name__)


# Known productive/educational Twitter accounts
PRODUCTIVE_ACCOUNTS = {
    # Tech/Programming
    "github", "vaborsh", "dan_abramov", "addyosmani", "sarah_edo",
    "kentcdodds", "wesbos", "mpjme", "traversymedia", "theprimeagen",
    "fireship_dev", "benlorantfy", "swaborsh", "levelsio",
    # News Organizations
    "reuters", "ap", "baborsh", "nytimes", "washingtonpost", "wsj",
    "bbc", "cnn", "npr", "theguardian", "economist",
    # Science/Education
    "nasa", "spacex", "nature", "science", "newscientist",
    "mittech", "waborsh", "stanfordonline", "harvardmed",
    # Tech Companies (official)
    "google", "microsoft", "apple", "meta", "openai", "anthropic",
    "nvidia", "aws", "azure", "googlecloud",
}

# Known entertainment/distraction accounts
ENTERTAINMENT_ACCOUNTS = {
    # Meme accounts
    "dril", "nihilist_arbys", "horse_ebooks", "shitpostbot5000",
    # Entertainment
    "netflix", "hulu", "disneyplus", "hbomax", "primevideo",
    # Gaming
    "xbox", "playstation", "nintendo", "raborsh", "ign", "gamespot",
    # Celebrities (entertainment-focused)
    "kimkardashian", "kyliejenner", "justinbieber", "arianagrande",
}


@dataclass
class TwitterURLInfo:
    """Parsed information from a Twitter URL."""
    is_home_feed: bool = False
    is_explore: bool = False
    is_search: bool = False
    is_notifications: bool = False
    is_messages: bool = False
    is_profile: bool = False
    is_tweet: bool = False
    is_list: bool = False
    username: Optional[str] = None
    tweet_id: Optional[str] = None
    search_query: Optional[str] = None


class RuleBasedTwitterClassifier(RuleBasedDomainClassifier):
    """Rule-based Twitter/X content classifier.
    
    Classifies Twitter URLs based on content type and known accounts.
    """
    
    def __init__(self, name: str = "twitter_rules"):
        super().__init__(name)
        self._productive_accounts = PRODUCTIVE_ACCOUNTS
        self._entertainment_accounts = ENTERTAINMENT_ACCOUNTS
        
        # Keywords for classification hints
        self._news_keywords = {
            "breaking", "news", "update", "report", "announced", "official",
            "statement", "press", "release", "developing"
        }
        self._entertainment_keywords = {
            "meme", "funny", "lol", "lmao", "viral", "trending", "drama",
            "tea", "spill", "omg", "stan", "fandom"
        }
        self._education_keywords = {
            "thread", "tutorial", "explained", "learn", "tip", "guide",
            "how to", "lesson", "course", "study"
        }
    
    def _get_rules(self) -> Dict[str, Any]:
        return {
            "productive_accounts": self._productive_accounts,
            "entertainment_accounts": self._entertainment_accounts,
        }
    
    def _parse_twitter_url(self, url: str) -> TwitterURLInfo:
        """Parse a Twitter/X URL to extract content type."""
        info = TwitterURLInfo()
        url_lower = url.lower()
        
        # Normalize x.com to twitter.com for parsing
        url_lower = url_lower.replace("x.com", "twitter.com")
        
        # Check for home feed
        if re.search(r'twitter\.com/?$', url_lower) or re.search(r'twitter\.com/home', url_lower):
            info.is_home_feed = True
            return info
        
        # Check for explore/trending
        if '/explore' in url_lower or '/trending' in url_lower:
            info.is_explore = True
            return info
        
        # Check for search
        search_match = re.search(r'/search\?q=([^&]+)', url_lower)
        if search_match or '/search' in url_lower:
            info.is_search = True
            if search_match:
                info.search_query = search_match.group(1)
            return info
        
        # Check for notifications
        if '/notifications' in url_lower:
            info.is_notifications = True
            return info
        
        # Check for messages/DMs
        if '/messages' in url_lower:
            info.is_messages = True
            return info
        
        # Check for lists
        if '/lists' in url_lower or '/i/lists' in url_lower:
            info.is_list = True
            return info
        
        # Check for specific tweet
        tweet_match = re.search(r'/([^/]+)/status/(\d+)', url_lower)
        if tweet_match:
            info.is_tweet = True
            info.username = tweet_match.group(1)
            info.tweet_id = tweet_match.group(2)
            return info
        
        # Check for profile
        profile_match = re.search(r'twitter\.com/([^/?]+)(?:\?|$|/(?:with_replies|media|likes)?)', url_lower)
        if profile_match:
            username = profile_match.group(1)
            # Filter out Twitter's own pages
            if username not in {'home', 'explore', 'search', 'notifications', 'messages', 'i', 'settings'}:
                info.is_profile = True
                info.username = username
                return info
        
        return info
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify Twitter content based on URL structure and known accounts."""
        context = context or {}
        url = context.get("url", "")
        title = context.get("title", "").lower()
        
        # Parse the URL
        info = self._parse_twitter_url(url)
        
        # Home feed - this is the main distraction
        if info.is_home_feed:
            return Classification(
                domain=domain,
                category=Category.SOCIAL_MEDIA,
                confidence=0.9,
                metadata={
                    "usefulness": "DISTRACTION",
                    "classifier": self.name,
                    "reason": "Twitter home feed is casual browsing/distraction"
                }
            )
        
        # Explore/Trending - highly distracting
        if info.is_explore:
            return Classification(
                domain=domain,
                category=Category.SOCIAL_MEDIA,
                confidence=0.9,
                metadata={
                    "usefulness": "DISTRACTION",
                    "classifier": self.name,
                    "reason": "Twitter explore/trending is designed for engagement/distraction"
                }
            )
        
        # Search - depends on what they're searching for
        if info.is_search:
            if info.search_query:
                query = info.search_query.lower()
                if any(kw in query for kw in self._entertainment_keywords):
                    return Classification(
                        domain=domain,
                        category=Category.SOCIAL_MEDIA,
                        confidence=0.75,
                        metadata={
                            "usefulness": "DISTRACTION",
                            "classifier": self.name,
                            "reason": "Twitter search for entertainment content"
                        }
                    )
                if any(kw in query for kw in self._news_keywords):
                    return Classification(
                        domain=domain,
                        category=Category.NEWS,
                        confidence=0.65,
                        metadata={
                            "usefulness": "ENRICHMENT",
                            "classifier": self.name,
                            "reason": "Twitter search for news content"
                        }
                    )
            # Generic search - neutral
            return Classification(
                domain=domain,
                category=Category.SOCIAL_MEDIA,
                confidence=0.5,
                metadata={
                    "usefulness": "NEUTRAL",
                    "classifier": self.name,
                    "reason": "Twitter search (purpose unclear)"
                }
            )
        
        # Notifications - social engagement, distracting
        if info.is_notifications:
            return Classification(
                domain=domain,
                category=Category.SOCIAL_MEDIA,
                confidence=0.8,
                metadata={
                    "usefulness": "DISTRACTION",
                    "classifier": self.name,
                    "reason": "Twitter notifications are social engagement/distraction"
                }
            )
        
        # Messages - could be productive or social
        if info.is_messages:
            return Classification(
                domain=domain,
                category=Category.SOCIAL_MEDIA,
                confidence=0.5,
                metadata={
                    "usefulness": "NEUTRAL",
                    "classifier": self.name,
                    "reason": "Twitter DMs (could be work or social)"
                }
            )
        
        # Profile or Tweet - classify based on account
        if info.username:
            username_lower = info.username.lower()
            
            # Check known productive accounts
            if username_lower in self._productive_accounts:
                return Classification(
                    domain=domain,
                    category=Category.NEWS if username_lower in {"reuters", "ap", "bbc", "nytimes", "wsj"} else Category.EDUCATION,
                    confidence=0.75,
                    metadata={
                        "usefulness": "ENRICHMENT",
                        "classifier": self.name,
                        "reason": f"@{info.username} is a known productive/informational account"
                    }
                )
            
            # Check known entertainment accounts
            if username_lower in self._entertainment_accounts:
                return Classification(
                    domain=domain,
                    category=Category.ENTERTAINMENT,
                    confidence=0.8,
                    metadata={
                        "usefulness": "DISTRACTION",
                        "classifier": self.name,
                        "reason": f"@{info.username} is a known entertainment account"
                    }
                )
            
            # Unknown account - check title for hints
            if any(kw in title for kw in self._education_keywords):
                return Classification(
                    domain=domain,
                    category=Category.EDUCATION,
                    confidence=0.6,
                    metadata={
                        "usefulness": "ENRICHMENT",
                        "classifier": self.name,
                        "reason": "Tweet/profile has educational keywords"
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
                        "reason": "Tweet/profile has entertainment keywords"
                    }
                )
        
        # Can't determine from rules alone
        return None
    
    def add_productive_account(self, username: str) -> None:
        """Add an account to the productive list."""
        self._productive_accounts.add(username.lower().lstrip('@'))
    
    def add_entertainment_account(self, username: str) -> None:
        """Add an account to the entertainment list."""
        self._entertainment_accounts.add(username.lower().lstrip('@'))


class TwitterClassifier(BaseDomainClassifier):
    """Composite Twitter/X classifier combining rules and LLM.
    
    Tries rule-based classification first, falls back to LLM for
    unknown accounts or ambiguous content.
    """
    
    SUPPORTED_DOMAINS = {"twitter.com", "www.twitter.com", "x.com", "www.x.com", "mobile.twitter.com"}
    
    def __init__(
        self,
        classifiers: Optional[List[BaseDomainClassifier]] = None,
        name: str = "twitter_composite"
    ):
        super().__init__(name)
        self._classifiers = classifiers or [RuleBasedTwitterClassifier()]
    
    def supports_domain(self, domain: str) -> bool:
        """Check if this classifier supports the given domain."""
        return domain.lower() in self.SUPPORTED_DOMAINS
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify Twitter content using the classifier chain."""
        for classifier in self._classifiers:
            try:
                result = await classifier.classify(domain, context)
                if result is not None:
                    return result
            except Exception as e:
                logger.warning("Classifier %s failed: %s", classifier.name, e)
        
        # Default: treat unknown Twitter content as social media distraction
        return Classification(
            domain=domain,
            category=Category.SOCIAL_MEDIA,
            confidence=0.6,
            metadata={
                "usefulness": "DISTRACTION",
                "classifier": self.name,
                "reason": "Unknown Twitter content, defaulting to distraction"
            }
        )


def create_twitter_classifier(
    use_llm: bool = True,
    llm_client: Any = None
) -> TwitterClassifier:
    """Create a Twitter classifier with the specified configuration.
    
    Args:
        use_llm: If True, use LLM as fallback for unknown accounts (default: True)
        llm_client: Optional LLM client. If None and use_llm=True, will try to create one.
    """
    classifiers: List[BaseDomainClassifier] = []
    
    # Always use rule-based first (fast)
    classifiers.append(RuleBasedTwitterClassifier())
    
    # Add LLM-based fallback for unknown accounts/content
    if use_llm:
        try:
            from focus_guard.core.classification.classifiers.generic.url_llm_classifier import (
                create_url_llm_classifier
            )
            llm_classifier = create_url_llm_classifier(llm_client)
            if llm_classifier:
                classifiers.append(llm_classifier)
                logger.info("Twitter classifier: LLM fallback enabled")
        except Exception as e:
            logger.warning("Could not enable LLM fallback for Twitter: %s", e)
    
    return TwitterClassifier(classifiers)


# Default instance
default_classifier = create_twitter_classifier()
