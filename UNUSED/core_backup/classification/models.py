"""
Classification models for the Focus Guard system.

This module re-exports the necessary models from domain.models and provides
additional classification-specific models.
"""

from typing import Dict, Any, Optional

# Re-export Category from domain models
from core_v2.domain.models import Category, Domain, Classification


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
