"""
Sync wrapper utilities for async classifiers.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from .models import Domain, Classification

logger = logging.getLogger(__name__)


class SyncClassifierWrapper:
    """
    Wrapper that converts async classifiers to sync versions.
    
    This allows async classifiers to be used in synchronous contexts
    like the existing ClassificationPipeline.
    """
    
    def __init__(self, async_classifier, timeout: float = 30.0):
        """
        Initialize the sync wrapper.
        
        Args:
            async_classifier: The async classifier to wrap.
            timeout: Timeout for async operations in seconds.
        """
        self._async_classifier = async_classifier
        self._timeout = timeout
        self._executor = ThreadPoolExecutor(max_workers=1)
    
    @property
    def name(self) -> str:
        """Get the classifier name."""
        return getattr(self._async_classifier, 'name', 'async_wrapper')
    
    def classify(self, domain: Domain) -> Optional[str]:
        """
        Synchronous classify method that wraps the async classifier.
        
        Args:
            domain: The domain to classify.
            
        Returns:
            The classification category, or None if classification fails.
        """
        try:
            # Check if the method is actually async
            classify_method = getattr(self._async_classifier, 'classify')
            
            if asyncio.iscoroutinefunction(classify_method):
                # Run async method synchronously
                return asyncio.run(classify_method(domain))
            else:
                # Method is already sync, call directly
                return classify_method(domain)
                
        except Exception as e:
            logger.error(f"Sync classification failed for {domain}: {e}")
            return None
    
    def classify_with_context(
        self, 
        domain: Domain, 
        context: Dict[str, Any]
    ) -> Optional[Classification]:
        """
        Synchronous classify_with_context method that wraps the async classifier.
        
        Args:
            domain: The domain to classify.
            context: Additional context for classification.
            
        Returns:
            The classification result, or None if classification fails.
        """
        try:
            # Check if classifier has classify_with_context
            if not hasattr(self._async_classifier, 'classify_with_context'):
                return None
                
            method = getattr(self._async_classifier, 'classify_with_context')
            
            if asyncio.iscoroutinefunction(method):
                # Run async method synchronously
                return asyncio.run(method(domain, context))
            else:
                # Method is already sync, call directly
                return method(domain, context)
                
        except Exception as e:
            logger.error(f"Sync classification with context failed for {domain}: {e}")
            return None


class FlexibleClassifierAdapter:
    """
    Factory for creating flexible classifiers that can handle both sync and async.
    """
    
    @staticmethod
    def create_sync_classifier(classifier):
        """
        Create a sync version of any classifier.
        
        Args:
            classifier: The classifier to adapt (sync or async).
            
        Returns:
            A classifier that works synchronously.
        """
        # Check if classifier is already sync
        classify_method = getattr(classifier, 'classify')
        
        if asyncio.iscoroutinefunction(classify_method):
            # It's async, wrap it
            return SyncClassifierWrapper(classifier)
        else:
            # It's already sync, return as-is
            return classifier
