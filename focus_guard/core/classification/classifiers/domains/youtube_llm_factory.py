"""
Factory functions for creating LLM-based YouTube classifiers.
"""

from typing import Optional, Dict, Any

from focus_guard.core.domain.models import Domain, Category, Classification
from .youtube_llm import LLMBasedYouTubeClassifier
from ...classifiers.llm.base_llm import LLMClient


def create_llm_based_youtube_classifier(llm_client: LLMClient) -> LLMBasedYouTubeClassifier:
    """Create a new instance of the LLM-based YouTube classifier.
    
    This is a convenience function that creates and returns a new instance
    of the LLMBasedYouTubeClassifier with the provided LLM client.
    
    Args:
        llm_client: The LLM client to use for classification
        
    Returns:
        A new instance of LLMBasedYouTubeClassifier
    """
    return LLMBasedYouTubeClassifier(llm_client=llm_client)
