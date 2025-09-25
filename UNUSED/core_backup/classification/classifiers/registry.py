"""
Classifier registry implementation.

This module provides a registry for managing and accessing classifiers.
"""

from typing import Dict, List, Optional, Type

from core_v2.classification.base import Classifier


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
    
    def unregister(self, name: str) -> None:
        """
        Unregister a classifier.
        
        Args:
            name: The name of the classifier to unregister.
        """
        if name in self._classifiers:
            del self._classifiers[name]
            
        if name in self._priorities:
            del self._priorities[name]
    
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
        Get all registered classifiers.
        
        Returns:
            A list of all registered classifiers.
        """
        return list(self._classifiers.values())
    
    def get_sorted_classifiers(self) -> List[Classifier]:
        """
        Get all registered classifiers sorted by priority (highest first).
        
        Returns:
            A list of classifiers sorted by priority.
        """
        return [
            self._classifiers[name]
            for name, _ in sorted(
                self._priorities.items(),
                key=lambda item: item[1],
                reverse=True
            )
        ]
