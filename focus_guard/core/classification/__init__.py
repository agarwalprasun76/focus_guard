"""
Core classification module for Focus Guard.

This package provides the core functionality for classifying content
and domains into different categories like educational, entertainment, etc.
"""

from typing import Dict, Type, Any, Optional, List
from enum import Enum

# Re-export commonly used types and classes
from focus_guard.core.domain.models import Domain, Category, Classification
from .base import (
    Classifier,
    ContextAwareClassifier,
    ClassifierRegistry,
    ClassificationPipeline
)

# Import classifiers to register them with the registry
# This will be populated as we implement the classifiers
__all__ = [
    'Domain',
    'Category',
    'Classification',
    'Classifier',
    'ContextAwareClassifier',
    'ClassifierRegistry',
    'ClassificationPipeline'
]
