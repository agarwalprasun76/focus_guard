"""
Base Classifier Module

This module defines the abstract base classes for all content classifiers in the
hierarchical classification system. It provides the common interface that all
specialized classifiers must implement.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)


class ContentClassifier(ABC):
    """
    Abstract base class for all content classifiers.
    
    All specialized classifiers must inherit from this class and implement
    its abstract methods to ensure consistent behavior across the system.
    """
    
    @abstractmethod
    def can_classify(self, url: str, domain: str, metadata: Optional[Dict] = None) -> bool:
        """
        Determine if this classifier can handle the given content.
        
        Args:
            url: The full URL to classify
            domain: The domain part of the URL
            metadata: Optional metadata that may help with classification
            
        Returns:
            bool: True if this classifier can handle this content, False otherwise
        """
        pass
        
    @abstractmethod
    def classify(self, url: str, domain: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Classify the content and return a standardized result.
        
        Args:
            url: The full URL to classify
            domain: The domain part of the URL
            metadata: Optional metadata that may help with classification
            
        Returns:
            Dict with standardized classification result:
            {
                "classification": One of "useful", "distraction", "neutral", "error"
                "reason": String explanation of the classification
                "confidence": Float between 0 and 1 indicating confidence
                "metadata": Optional dict with additional information
            }
        """
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """
        Return the priority of this classifier.
        
        Higher priority classifiers are checked first in the classification chain.
        
        Returns:
            int: Priority value (higher = checked first)
        """
        pass
    
    def create_result(self, classification: str, reason: str = None, 
                      confidence: float = 1.0, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a standardized result dictionary.
        
        Args:
            classification: One of "useful", "distraction", "neutral", "error"
            reason: Explanation of the classification
            confidence: Float between 0 and 1 indicating confidence
            metadata: Additional information about the classification
            
        Returns:
            Dict with classification result
        """
        return {
            "classification": classification,
            "reason": reason,
            "confidence": min(max(confidence, 0.0), 1.0),  # Clamp between 0 and 1
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
