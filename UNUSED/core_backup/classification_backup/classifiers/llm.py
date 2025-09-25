"""
LLM classifier adapter.

This module provides an adapter for the existing LLM classifier to
integrate it with the new classification architecture.
"""

import logging
from typing import Optional, Dict, Any

from focus_guard.core.classification.base import ContextAwareClassifier
from focus_guard.core.domain.models import Domain, Category, URL
from core.domain_classifier.classifiers.llm_classifier import LLMDomainClassifier


class LLMClassifierAdapter(ContextAwareClassifier):
    """
    Adapter for the existing LLM classifier.
    
    This class adapts the existing LLM classifier to the new
    classification architecture, preserving all its functionality.
    """
    
    def __init__(self):
        """Initialize the LLM classifier adapter."""
        # Use the LLMDomainClassifier for domain link classification
        self._legacy_classifier = LLMDomainClassifier()
        self._logger = logging.getLogger("core.classification.classifiers.llm")
        self._logger.info("LLM classifier adapter initialized")
    
    @property
    def name(self) -> str:
        """
        Get the name of the classifier.
        
        Returns:
            The classifier name.
        """
        return "llm_classifier"
    
    def classify(self, domain: Domain) -> Optional[Category]:
        """
        Classify a domain into a category.
        
        The LLM classifier requires context to classify content, so this method
        always returns None.
        
        Args:
            domain: The domain to classify.
            
        Returns:
            None, as the LLM classifier requires context to classify content.
        """
        return None
    
    def classify_with_context(self, domain: Domain, context: Dict[str, Any]) -> Optional[Category]:
        """
        Classify a domain using additional context.
        
        This method uses the legacy LLM classifier to classify content
        based on the URL, domain, and additional context.
        
        Args:
            domain: The domain to classify.
            context: Additional context to aid classification.
            
        Returns:
            The category of the domain, or None if it couldn't be classified.
        """
        # Extract URL from context
        url = context.get("url")
        if not url:
            self._logger.warning("No URL provided in context for LLM classification")
            return None
        
        # Extract metadata from context
        metadata = context.get("metadata", {})
        
        # Check if the legacy classifier can handle this content
        if not self._legacy_classifier.can_classify(url, domain.value, metadata):
            self._logger.info(f"LLM classifier cannot classify: {url}")
            return None
        
        # Use the legacy classifier to classify the content
        self._logger.info(f"Classifying content with LLM: {url}")
        result = self._legacy_classifier.classify(url, domain.value, metadata)
        
        # Map the legacy classification result to a Category
        if result and isinstance(result, dict):
            classification = result.get("classification")
            if classification == "useful":
                self._logger.info(f"Content classified as useful: {url}")
                return Category.EDUCATION
            elif classification == "distraction":
                self._logger.info(f"Content classified as distraction: {url}")
                return Category.ENTERTAINMENT
            else:
                self._logger.info(f"Content classified as neutral or unknown: {url}")
                return None
        
        # Return None if the classifier couldn't classify the content
        self._logger.info(f"LLM classifier returned no result for: {url}")
        return None
    
    def set_model(self, model_name: str) -> None:
        """
        Set the model name for the LLM classifier.
        
        Args:
            model_name: The name of the model to use.
        """
        self._legacy_classifier.model_name = model_name
        self._logger.info(f"Set LLM model to: {model_name}")
