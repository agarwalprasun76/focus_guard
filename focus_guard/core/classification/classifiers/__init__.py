"""
Classifier implementations for different types of content.

This package contains various classifier implementations that can be used
to categorize different types of content based on different criteria.
"""

from typing import Dict, Type, Optional, Any

from focus_guard.core.classification.base import (
    Classifier,
    ContextAwareClassifier,
    ClassifierRegistry,
    ClassificationPipeline
)
from focus_guard.core.domain.models import (
    Domain,
    Category,
    Classification
)

# Import classifiers to register them with the registry
# These will be populated as we implement the classifiers
__all__ = [
    'Classifier',
    'ContextAwareClassifier',
    'ClassifierRegistry',
    'ClassificationPipeline',
    'Domain',
    'Category',
    'Classification'
]
