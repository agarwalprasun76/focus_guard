"""
Base interfaces for domain classification.

This module defines the core interfaces for domain classifiers and related components.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Protocol, runtime_checkable

from focus_guard.core.domain.models import Domain, Category, Classification

logger = logging.getLogger(__name__)


@runtime_checkable
class Classifier(Protocol):
    """
    Interface for domain classifiers.
    
    Classifiers determine the category of a domain based on its content,
    URL, or other relevant factors.
    
    This protocol supports both synchronous and asynchronous implementations.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the name of the classifier.
        
        Returns:
            The classifier name.
        """
        ...
    
    def classify(self, domain: Domain) -> Optional[Category]:
        """
        Classify a domain into a category.
        
        Args:
            domain: The domain to classify.
            
        Returns:
            The category of the domain, or None if it couldn't be classified.
        
        Note: This can be either a regular method or async method.
        """
        ...


class ContextAwareClassifier(Classifier, Protocol):
    """
    Interface for classifiers that use context beyond just the domain.
    
    Some classifiers may need additional context, such as URL path, query parameters,
    or metadata about the content, to make accurate classification decisions.
    """
    
    def classify_with_context(
        self, 
        domain: Domain, 
        context: Dict[str, Any]
    ) -> Optional[Classification]:
        """
        Classify a domain using additional context.
        
        Args:
            domain: The domain to classify.
            context: Additional context to aid classification.
            
        Returns:
            The classification result, or None if it couldn't be classified.
            
        Note: This can be either a regular method or async method.
        """
        ...


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
            
        Raises:
            ValueError: If a classifier with the same name already exists.
        """
        if classifier.name in self._classifiers:
            raise ValueError(f"Classifier '{classifier.name}' already exists in registry")
        self._classifiers[classifier.name] = classifier
    
    def unregister(self, name: str) -> None:
        """
        Unregister a classifier.
        
        Args:
            name: The name of the classifier to unregister.
        """
        self._classifiers.pop(name, None)
    
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
        
    def clear(self) -> None:
        """
        Clear all classifiers from the registry.
        """
        self._classifiers.clear()


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
        if name not in self._registry._classifiers:
            raise ValueError(f"No classifier named '{name}' found in registry")
        self._pipeline.append(name)
    
    def remove_classifier(self, name: str) -> None:
        """
        Remove a classifier from the pipeline.
        
        Args:
            name: The name of the classifier to remove.
        """
        if name in self._pipeline:
            self._pipeline.remove(name)
    
    def classify(
        self, 
        domain: Domain, 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """
        Classify a domain using the pipeline.
        
        This method executes each classifier in the pipeline in order,
        returning the first non-None result.
        
        Supports both synchronous and asynchronous classifiers.
        
        Args:
            domain: The domain to classify.
            context: Optional context for context-aware classifiers.
            
        Returns:
            The classification result, or None if no classifier could classify it.
        """
        for name in self._pipeline:
            classifier = self._registry.get(name)
            if classifier is None:
                continue
                
            try:
                if isinstance(classifier, ContextAwareClassifier) and context is not None:
                    # Handle classify_with_context
                    if asyncio.iscoroutinefunction(classifier.classify_with_context):
                        # This is an async classifier - run synchronously
                        result = asyncio.run(classifier.classify_with_context(domain, context))
                    else:
                        # This is a sync classifier
                        result = classifier.classify_with_context(domain, context)
                        
                    if result is not None:
                        return result
                else:
                    # Handle regular classify
                    if asyncio.iscoroutinefunction(classifier.classify):
                        # This is an async classifier - run synchronously
                        result = asyncio.run(classifier.classify(domain))
                    else:
                        # This is a sync classifier
                        result = classifier.classify(domain)
                        
                    if result is not None:
                        result = Classification(
                            domain=domain,
                            category=result,
                            confidence=1.0,
                            metadata={"classifier": name}
                        )
                        return result
            except Exception as e:
                logger.error(f"Classifier {name} failed: {e}")
                continue
        
        return None
