"""
Factory functions for creating rule-based YouTube classifiers.
"""

from typing import Optional, Dict, Any

from focus_guard.core.domain.models import Domain, Category, Classification
from .youtube_rules import RuleBasedYouTubeClassifier


def create_rule_based_youtube_classifier() -> RuleBasedYouTubeClassifier:
    """Create a new instance of the rule-based YouTube classifier.
    
    This is a convenience function that creates and returns a new instance
    of the RuleBasedYouTubeClassifier with default settings.
    
    Returns:
        A new instance of RuleBasedYouTubeClassifier
    """
    return RuleBasedYouTubeClassifier()
