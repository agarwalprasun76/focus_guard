"""
YouTube domain classifier implementation.

This module provides a clean entry point for YouTube content classification,
combining both rule-based and LLM-based approaches. The actual implementations
are in separate modules:
- youtube_base.py: Base classes and common functionality
- youtube_rules.py: Rule-based classification
- youtube_llm.py: LLM-based classification
"""

from typing import List, Any

# Import base classifier and factory functions
from .youtube_base import YouTubeClassifier
from .base import BaseDomainClassifier, DomainClassifier
from .youtube_rules import RuleBasedYouTubeClassifier
from .youtube_llm import LLMBasedYouTubeClassifier
from .youtube_rules_factory import create_rule_based_youtube_classifier
from .youtube_llm_factory import create_llm_based_youtube_classifier

# Re-export main classes and functions
__all__ = [
    'YouTubeClassifier',
    'RuleBasedYouTubeClassifier',
    'LLMBasedYouTubeClassifier',
    'create_youtube_classifier',
    'default_classifier'
]

def create_youtube_classifier(
    use_llm: bool = True,
    use_rules: bool = True,
    llm_client: Any = None
) -> YouTubeClassifier:
    """Create a YouTube classifier with the specified configuration.
    
    Args:
        use_llm: Whether to use LLM-based classification if available
        use_rules: Whether to use rule-based classification
        llm_client: Optional LLM client to use for LLM-based classification
        
    Returns:
        A configured YouTube classifier instance
    """
    classifiers: List[Any] = []
    
    if use_llm and llm_client is not None:
        try:
            classifiers.append(create_llm_based_youtube_classifier(llm_client=llm_client))
        except (ImportError, Exception) as e:
            import logging
            logging.warning(f"Failed to initialize LLM-based classifier: {e}")
    
    if use_rules:
        classifiers.append(create_rule_based_youtube_classifier())
    
    if not classifiers:
        raise ValueError(
            "At least one classifier type must be enabled. "
            "If using LLM, make sure to provide an llm_client."
        )
    
    return YouTubeClassifier(classifiers)

# Create a default instance for convenience
default_classifier = create_youtube_classifier(use_llm=False, use_rules=True)
