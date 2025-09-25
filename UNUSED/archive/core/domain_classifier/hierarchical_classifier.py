"""
Hierarchical Link Classifier

This module provides the main hierarchical classifier implementation that
delegates to specialized classifiers for different types of content.
"""

import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from .classifier_registry import classifier_registry
from .base_classifier import ContentClassifier

# Set up logging
logger = logging.getLogger(__name__)


class HierarchicalLinkClassifier:
    """
    Main hierarchical link classifier that orchestrates the classification process.
    
    This class is responsible for delegating classification requests to the 
    appropriate specialized classifiers registered in the classifier registry.
    It provides a simple interface for classifying links while hiding the 
    complexity of the underlying classification system.
    """
    
    def __init__(self, registry=None):
        """
        Initialize the hierarchical link classifier.
        
        Args:
            registry: Optional classifier registry to use (uses global singleton if not provided)
        """
        self.registry = registry or classifier_registry
        
    def classify_link(self, url: str, domain: str = None) -> Dict[str, Any]:
        """
        Classify a link using the hierarchical classification system.
        
        This method delegates to the classifier registry, which will find the
        appropriate specialized classifier for the given content.
        
        Args:
            url: The URL to classify
            domain: Optional domain part of the URL (extracted from URL if not provided)
            
        Returns:
            Dict with standardized classification result
        """
        return self.registry.classify(url, domain)
    
    def register_classifier(self, classifier: ContentClassifier) -> None:
        """
        Register a new classifier with the system.
        
        Args:
            classifier: The classifier to register
        """
        self.registry.register(classifier)


# Singleton instance for easy import
link_classifier = HierarchicalLinkClassifier()
