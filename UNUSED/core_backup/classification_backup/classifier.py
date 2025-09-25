"""
Domain classifier interface and implementation.

This module provides the DomainClassifier interface and implementation for classifying domains
into predefined categories. It re-exports the StandardDomainClassifier as DomainClassifier
for use by the classification component.
"""

import asyncio
from typing import Optional, Dict, Any

from focus_guard.core.classification.base import Classifier, ContextAwareClassifier
from focus_guard.core.classification.domain_classifier import StandardDomainClassifier
from focus_guard.core.domain.models import Domain, Category, Classification


class ClassificationResult:
    """
    Result of a domain classification operation.
    
    This class encapsulates the result of classifying a domain, including
    the domain itself, the assigned category, and additional metadata.
    """
    
    def __init__(self, domain: str, category: Category, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a classification result.
        
        Args:
            domain: The domain that was classified.
            category: The category assigned to the domain.
            metadata: Optional metadata about the classification.
        """
        self.domain = domain
        self.category = category
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the classification result to a dictionary.
        
        Returns:
            A dictionary representation of the classification result.
        """
        return {
            "domain": self.domain,
            "category": self.category.name if self.category else None,
            "metadata": self.metadata
        }


class DomainClassifier:
    """
    Domain classifier interface.
    
    This class provides methods for classifying domains into predefined categories.
    It wraps the StandardDomainClassifier and provides async methods for classification.
    """
    
    def __init__(self, classifier: Classifier):
        """
        Initialize the domain classifier.
        
        Args:
            classifier: The underlying classifier implementation.
        """
        self._classifier = classifier
        self._context_aware = isinstance(classifier, ContextAwareClassifier)
    
    @classmethod
    def from_config_loader(cls, config_loader):
        """
        Create a domain classifier from a configuration loader.
        
        Args:
            config_loader: The configuration loader to use.
            
        Returns:
            A new DomainClassifier instance.
        """
        return cls(StandardDomainClassifier(config_loader))
    
    async def classify_domain(self, domain_str: str, url: Optional[str] = None) -> ClassificationResult:
        """
        Classify a domain asynchronously.
        
        Args:
            domain_str: The domain string to classify.
            url: Optional URL for additional context.
            
        Returns:
            A ClassificationResult containing the classification outcome.
        """
        try:
            # Create a Domain object
            domain_obj = Domain(domain_str)
            
            # Prepare context if URL is provided and classifier is context-aware
            context = {"url": url} if url and self._context_aware else None
            
            # Run the classification in a thread pool to avoid blocking
            if context and self._context_aware:
                category = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: self._classifier.classify_with_context(domain_obj, context)
                )
            else:
                category = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._classifier.classify(domain_obj)
                )
            
            # Use UNKNOWN category if classification failed
            if category is None:
                category = Category.UNKNOWN
                
            # Create and return the result
            metadata = {"url": url} if url else {}
            return ClassificationResult(domain_str, category, metadata)
            
        except Exception as e:
            # In case of error, return UNKNOWN category
            return ClassificationResult(domain_str, Category.UNKNOWN, {"error": str(e)})
    
    @property
    def name(self) -> str:
        """
        Get the name of the underlying classifier.
        
        Returns:
            The classifier name.
        """
        return self._classifier.name
