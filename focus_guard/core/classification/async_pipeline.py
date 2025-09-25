"""
Async Classification Pipeline for flexible sync/async classifier support.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, List

from .base import ClassifierRegistry, Classification
from .models import Domain

logger = logging.getLogger(__name__)


class AsyncClassificationPipeline:
    """
    Async version of the classification pipeline that supports both sync and async classifiers.
    
    This pipeline can handle classifiers with both synchronous and asynchronous
    classify methods, providing maximum flexibility for different classifier types.
    """
    
    def __init__(self, registry: ClassifierRegistry):
        """
        Initialize the async classification pipeline.
        
        Args:
            registry: The classifier registry containing available classifiers.
        """
        self._registry = registry
        self._pipeline: List[str] = []
    
    def add_classifier(self, name: str) -> None:
        """
        Add a classifier to the pipeline.
        
        Args:
            name: The name of the classifier to add.
        """
        if name not in self._pipeline:
            self._pipeline.append(name)
    
    def remove_classifier(self, name: str) -> None:
        """
        Remove a classifier from the pipeline.
        
        Args:
            name: The name of the classifier to remove.
        """
        if name in self._pipeline:
            self._pipeline.remove(name)
    
    def clear_pipeline(self) -> None:
        """Clear all classifiers from the pipeline."""
        self._pipeline.clear()
    
    async def classify(
        self, 
        domain: Domain, 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """
        Classify a domain using the async pipeline.
        
        This method executes each classifier in the pipeline in order,
        returning the first non-None result. Supports both sync and async classifiers.
        
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
                # Check if classifier has classify_with_context method
                if hasattr(classifier, 'classify_with_context') and context is not None:
                    method = getattr(classifier, 'classify_with_context')
                    
                    # Handle async vs sync methods
                    if asyncio.iscoroutinefunction(method):
                        result = await method(domain, context)
                    else:
                        result = method(domain, context)
                        
                    if result is not None:
                        return result
                else:
                    # Use regular classify method
                    method = getattr(classifier, 'classify')
                    
                    # Handle async vs sync methods
                    if asyncio.iscoroutinefunction(method):
                        result = await method(domain)
                    else:
                        result = method(domain)
                        
                    if result is not None:
                        # Wrap in Classification object if needed
                        if isinstance(result, str):
                            from .models import Category
                            result = Classification(
                                domain=domain,
                                category=Category(result),
                                confidence=1.0,
                                metadata={"classifier": name}
                            )
                        return result
                        
            except Exception as e:
                logger.error(f"Classifier {name} failed: {e}")
                continue
        
        return None
    
    def get_pipeline_order(self) -> List[str]:
        """
        Get the current order of classifiers in the pipeline.
        
        Returns:
            List of classifier names in execution order.
        """
        return self._pipeline.copy()
    
    def __len__(self) -> int:
        """Get the number of classifiers in the pipeline."""
        return len(self._pipeline)
    
    def __bool__(self) -> bool:
        """Check if the pipeline has any classifiers."""
        return bool(self._pipeline)
