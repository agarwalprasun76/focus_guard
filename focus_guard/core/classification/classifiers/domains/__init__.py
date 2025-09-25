"""
Domain-specific classifiers.

This package contains classifiers for specific domains like YouTube, social media, etc.
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

__all__ = [
    'DomainClassifier',
    'BaseDomainClassifier',
    'RuleBasedDomainClassifier',
    'LLMBasedDomainClassifier',
    'YouTubeClassifier',
    'RuleBasedYouTubeClassifier',
    'LLMBasedYouTubeClassifier',
    'create_youtube_classifier',
    'default_classifier'
]
