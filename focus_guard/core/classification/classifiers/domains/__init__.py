"""
Domain-specific classifiers.

This package contains classifiers for specific domains like YouTube, Google, social media, etc.
"""

from .base import (
    DomainClassifier,
    BaseDomainClassifier,
    RuleBasedDomainClassifier,
    LLMBasedDomainClassifier
)

from .youtube import (
    YouTubeClassifier,
    RuleBasedYouTubeClassifier,
    LLMBasedYouTubeClassifier,
    create_youtube_classifier,
    default_classifier
)

from .google import (
    GoogleClassifier,
    create_google_classifier,
    get_google_classifier,
)

from .google_rules import (
    RuleBasedGoogleClassifier,
    create_google_rules_classifier,
)

from .google_llm import (
    LLMBasedGoogleClassifier,
    create_google_llm_classifier,
)

from .reddit import (
    RedditClassifier,
    RuleBasedRedditClassifier,
    LLMBasedRedditClassifier,
    create_reddit_classifier,
    create_reddit_llm_classifier,
)

from .twitter import (
    TwitterClassifier,
    RuleBasedTwitterClassifier,
    create_twitter_classifier,
)

__all__ = [
    'DomainClassifier',
    'BaseDomainClassifier',
    'RuleBasedDomainClassifier',
    'LLMBasedDomainClassifier',
    # YouTube
    'YouTubeClassifier',
    'RuleBasedYouTubeClassifier',
    'LLMBasedYouTubeClassifier',
    'create_youtube_classifier',
    'default_classifier',
    # Google
    'GoogleClassifier',
    'RuleBasedGoogleClassifier',
    'LLMBasedGoogleClassifier',
    'create_google_classifier',
    'create_google_rules_classifier',
    'create_google_llm_classifier',
    'get_google_classifier',
    # Reddit
    'RedditClassifier',
    'RuleBasedRedditClassifier',
    'LLMBasedRedditClassifier',
    'create_reddit_classifier',
    'create_reddit_llm_classifier',
    # Twitter/X
    'TwitterClassifier',
    'RuleBasedTwitterClassifier',
    'create_twitter_classifier',
]
