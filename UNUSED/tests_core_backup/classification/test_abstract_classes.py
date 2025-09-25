"""
Unit tests for abstract base classes in the classification system.

This module specifically tests the behavior of the abstract base classes
to ensure they function correctly and cannot be instantiated directly.
"""

import unittest
from abc import ABC, abstractmethod

from core_v2.classification.base import (
    Classifier,
    ContextAwareClassifier,
)
from core_v2.domain.models import Domain, Category


class TestAbstractClasses(unittest.TestCase):
    """Tests for abstract base classes in the classification system."""

    def test_classifier_cannot_be_instantiated(self):
        """Test that Classifier cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            # This should raise TypeError because Classifier is abstract
            classifier = Classifier()
    
    def test_context_aware_classifier_cannot_be_instantiated(self):
        """Test that ContextAwareClassifier cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            # This should raise TypeError because ContextAwareClassifier is abstract
            classifier = ContextAwareClassifier()
    
    def test_classifier_abstract_methods(self):
        """Test that Classifier's abstract methods are properly defined."""
        # Check that classify is an abstract method
        self.assertTrue(hasattr(Classifier.classify, '__isabstractmethod__'))
        self.assertTrue(Classifier.classify.__isabstractmethod__)
        
        # Check that name is an abstract property
        self.assertTrue(hasattr(Classifier.name, '__isabstractmethod__'))
        self.assertTrue(Classifier.name.__isabstractmethod__)
    
    def test_context_aware_classifier_abstract_methods(self):
        """Test that ContextAwareClassifier's abstract methods are properly defined."""
        # Check that classify_with_context is an abstract method
        self.assertTrue(hasattr(ContextAwareClassifier.classify_with_context, '__isabstractmethod__'))
        self.assertTrue(ContextAwareClassifier.classify_with_context.__isabstractmethod__)
        
        # Check that it inherits abstract methods from Classifier
        self.assertTrue(hasattr(ContextAwareClassifier.classify, '__isabstractmethod__'))
        self.assertTrue(ContextAwareClassifier.classify.__isabstractmethod__)
        
        self.assertTrue(hasattr(ContextAwareClassifier.name, '__isabstractmethod__'))
        self.assertTrue(ContextAwareClassifier.name.__isabstractmethod__)


if __name__ == "__main__":
    unittest.main()
