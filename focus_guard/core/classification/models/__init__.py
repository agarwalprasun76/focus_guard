"""
Data models for classification results and related types.

This module defines the data structures used throughout the classification system.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Any, Optional, List


class Category(Enum):
    """
    Categories that content can be classified into.
    
    These categories are used throughout the system to classify content.
    """
    UNKNOWN = auto()
    EDUCATION = auto()
    ENTERTAINMENT = auto()
    SOCIAL_MEDIA = auto()
    PRODUCTIVITY = auto()
    SHOPPING = auto()
    NEWS = auto()
    GAMING = auto()
    STREAMING = auto()
    ADULT = auto()
    MALICIOUS = auto()
    
    @classmethod
    def from_string(cls, value: str) -> 'Category':
        """
        Convert a string to a Category enum value.
        
        Args:
            value: The string representation of the category.
            
        Returns:
            The corresponding Category enum value.
            
        Raises:
            ValueError: If the string doesn't match any category.
        """
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Unknown category: {value}")


@dataclass
class ClassificationResult:
    """
    The result of a classification operation.
    
    This class represents the output of a classifier, containing the predicted
    category and any additional metadata.
    """
    domain: str
    category: Category
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the classification result to a dictionary.
        
        Returns:
            A dictionary representation of the classification result.
        """
        return {
            'domain': self.domain,
            'category': self.category.name.lower(),
            'confidence': self.confidence,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClassificationResult':
        """
        Create a ClassificationResult from a dictionary.
        
        Args:
            data: Dictionary containing the classification result data.
            
        Returns:
            A new ClassificationResult instance.
        """
        return cls(
            domain=data['domain'],
            category=Category.from_string(data['category']),
            confidence=data.get('confidence', 1.0),
            metadata=data.get('metadata', {})
        )


@dataclass
class Domain:
    """
    Represents a domain name.
    
    This class provides utilities for working with domain names.
    """
    value: str
    
    def __post_init__(self):
        """Normalize the domain name."""
        # Remove protocol and path if present
        domain = self.value.split('//')[-1].split('/')[0]
        # Remove port if present
        domain = domain.split(':')[0]
        # Convert to lowercase
        self.value = domain.lower().strip()
    
    def __str__(self) -> str:
        return self.value
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Domain):
            return NotImplemented
        return self.value == other.value
    
    def __hash__(self) -> int:
        return hash(self.value)
    
    @property
    def tld(self) -> str:
        """
        Get the top-level domain (TLD) of this domain.
        
        Returns:
            The TLD of the domain.
        """
        return self.value.split('.')[-1] if '.' in self.value else self.value
    
    @property
    def subdomains(self) -> List[str]:
        """
        Get all subdomains of this domain.
        
        Returns:
            A list of subdomains, from most specific to least specific.
        """
        parts = self.value.split('.')
        return ['.'.join(parts[i:]) for i in range(len(parts) - 1)]
