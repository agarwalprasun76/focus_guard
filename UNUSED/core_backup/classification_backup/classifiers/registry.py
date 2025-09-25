"""
Classifier registry implementation.

This module provides a registry for managing and accessing classifiers.
"""

from typing import Dict, List, Optional, Type, Any, Tuple

from focus_guard.core.classification.base import Classifier
from focus_guard.core.domain.models import Domain, Category


class ClassifierRegistry:
    """
    Registry for domain classifiers.
    
    This class manages a collection of classifiers and provides methods to
    register, unregister, and retrieve them.
    """
    
    def __init__(self):
        """Initialize an empty classifier registry."""
        self._classifiers: Dict[str, Classifier] = {}
        self._priorities: Dict[str, int] = {}
    
    def register(self, classifier: Classifier, priority: int = 0) -> None:
        """
        Register a classifier.
        
        Args:
            classifier: The classifier to register.
            priority: The priority of the classifier (higher values = higher priority).
        """
        self._classifiers[classifier.name] = classifier
        self._priorities[classifier.name] = priority
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a classifier.
        
        Args:
            name: The name of the classifier to unregister.
            
        Returns:
            bool: True if the classifier was found and unregistered, False otherwise.
        """
        found = False
        if name in self._classifiers:
            del self._classifiers[name]
            found = True
            
        if name in self._priorities:
            del self._priorities[name]
            
        return found
    
    def get(self, name: str) -> Optional[Classifier]:
        """
        Get a classifier by name.
        
        Args:
            name: The name of the classifier to retrieve.
            
        Returns:
            The classifier, or None if not found.
        """
        return self._classifiers.get(name)
    
    def get_all(self) -> List[Classifier]:
        """
        Get all registered classifiers sorted by priority (highest first).
        
        Returns:
            A list of all registered classifiers sorted by priority.
        """
        return self.get_sorted_classifiers()
    
    def set_priority(self, name: str, priority: int) -> bool:
        """
        Set the priority of a registered classifier.
        
        Args:
            name: The name of the classifier.
            priority: The new priority value.
            
        Returns:
            bool: True if the classifier was found and priority was updated, False otherwise.
        """
        if name not in self._classifiers:
            return False
            
        self._priorities[name] = priority
        return True

    def classify(self, domain: Domain, **kwargs: Any) -> Optional[Category]:
        """
        Classify a domain using all registered classifiers in priority order.
        
        Args:
            domain: The domain to classify.
            **kwargs: Additional arguments to pass to the classifier.
            
        Returns:
            The first non-None category returned by any classifier, or None if no
            classifier returns a category.
        """
        # Get classifiers in priority order (highest first)
        for classifier in self.get_sorted_classifiers():
            try:
                result = classifier.classify(domain, **kwargs)
                
                # Handle both (category, metadata) and category return types
                if isinstance(result, tuple) and len(result) == 2:
                    category, _ = result
                else:
                    category = result
                
                # Return the first non-None category
                if category is not None:
                    return category
                    
            except Exception as e:
                # Log the error but continue with other classifiers
                import logging
                logging.getLogger(__name__).error(
                    f"Error in classifier {classifier.name}: {str(e)}",
                    exc_info=True
                )
        
        return None

    def get_sorted_classifiers(self) -> List[Classifier]:
        """
        Get all registered classifiers sorted by priority (highest first).
        
        Returns:
            A list of classifiers sorted by priority.
        """
        # Get all classifiers that exist in both dictionaries
        valid_names = set(self._classifiers.keys()) & set(self._priorities.keys())
        
        return [
            self._classifiers[name]
            for name, _ in sorted(
                ((name, self._priorities[name]) for name in valid_names),
                key=lambda item: item[1],
                reverse=True
            )
        ]
