"""
Base interfaces for domain classification.

This module defines the core interfaces for domain classifiers and related components.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Set

from focus_guard.core.domain.models import Domain, Category


class Classifier(ABC):
    """
    Base interface for domain classifiers.
    
    A classifier is responsible for categorizing domains based on specific criteria.
    """
    
    @abstractmethod
    def classify(self, domain: Domain) -> Optional[Category]:
        """
        Classify a domain into a category.
        
        Args:
            domain: The domain to classify.
            
        Returns:
            The category of the domain, or None if it couldn't be classified.
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the name of the classifier.
        
        Returns:
            The classifier name.
        """
        pass


class ContextAwareClassifier(Classifier):
    """
    Interface for classifiers that use context beyond just the domain.
    
    Some classifiers may need additional context, such as URL path, query parameters,
    or metadata about the content, to make accurate classification decisions.
    """
    
    @abstractmethod
    def classify_with_context(self, domain: Domain, context: Dict[str, Any]) -> Optional[Category]:
        """
        Classify a domain using additional context.
        
        Args:
            domain: The domain to classify.
            context: Additional context to aid classification.
            
        Returns:
            The category of the domain, or None if it couldn't be classified.
        """
        pass


class ClassifierRegistry:
    """
    Registry for domain classifiers.
    
    This class manages a collection of classifiers and provides methods to
    register, unregister, and retrieve them.
    """
    
    def __init__(self):
        """Initialize an empty classifier registry."""
        self._classifiers: Dict[str, Classifier] = {}
    
    def register(self, classifier: Classifier) -> None:
        """
        Register a classifier.
        
        Args:
            classifier: The classifier to register.
        """
        self._classifiers[classifier.name] = classifier
    
    def unregister(self, name: str) -> None:
        """
        Unregister a classifier.
        
        Args:
            name: The name of the classifier to unregister.
        """
        if name in self._classifiers:
            del self._classifiers[name]
    
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


class ClassificationPipeline:
    """
    Pipeline for executing multiple classifiers in sequence.
    
    This class manages the execution of multiple classifiers and combines
    their results according to a defined strategy.
    """
    
    def __init__(self, registry: ClassifierRegistry):
        """
        Initialize a classification pipeline.
        
        Args:
            registry: The classifier registry to use.
        """
        self._registry = registry
        self._pipeline: List[str] = []
    
    def add_classifier(self, name: str) -> None:
        """
        Add a classifier to the pipeline.
        
        Args:
            name: The name of the classifier to add.
            
        Raises:
            ValueError: If the classifier doesn't exist in the registry.
        """
        if self._registry.get(name) is None:
            raise ValueError(f"Classifier not found: {name}")
        self._pipeline.append(name)
    
    def remove_classifier(self, name: str) -> None:
        """
        Remove a classifier from the pipeline.
        
        Args:
            name: The name of the classifier to remove.
        """
        if name in self._pipeline:
            self._pipeline.remove(name)
    
    def classify(self, domain: Domain, context: Optional[Dict[str, Any]] = None) -> Optional[Category]:
        """
        Classify a domain using the pipeline.
        
        This method executes each classifier in the pipeline in order,
        returning the first non-None result.
        
        Args:
            domain: The domain to classify.
            context: Optional context for context-aware classifiers.
            
        Returns:
            The category of the domain, or None if no classifier could classify it.
        """
        for name in self._pipeline:
            classifier = self._registry.get(name)
            if classifier is None:
                continue
            
            if context is not None and isinstance(classifier, ContextAwareClassifier):
                result = classifier.classify_with_context(domain, context)
            else:
                result = classifier.classify(domain)
            
            if result is not None:
                return result
        
        return None
