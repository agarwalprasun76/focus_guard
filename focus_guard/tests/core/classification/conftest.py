"""
Pytest configuration and fixtures for classification module tests.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from focus_guard.core.classification.base import Classifier, ClassifierRegistry, ClassificationPipeline
from focus_guard.core.domain.models import Domain, Category, Classification


@pytest.fixture
def mock_domain():
    """Create a mock Domain instance."""
    return Domain("example.com")


@pytest.fixture
def mock_category():
    """Return a sample category."""
    return Category.ENTERTAINMENT


@pytest.fixture
def mock_classification_result(mock_domain, mock_category):
    """Create a mock Classification."""
    return Classification(
        domain=mock_domain,
        category=mock_category,
        confidence=0.9,
        metadata={"source": "test"}
    )


@pytest.fixture
def mock_classifier():
    """Create a mock Classifier instance."""
    classifier = MagicMock(spec=Classifier)
    classifier.name = "mock_classifier"
    classifier.classify = MagicMock(return_value=Category.ENTERTAINMENT)
    return classifier


@pytest.fixture
def mock_context_aware_classifier():
    """Create a mock ContextAwareClassifier instance."""
    from focus_guard.core.classification.base import ContextAwareClassifier
    from focus_guard.core.domain.models import Domain, Category, Classification
    
    # Create a proper mock with the right spec
    classifier = MagicMock(spec=ContextAwareClassifier)
    classifier.name = "context_aware_classifier"
    classifier.classify = MagicMock(return_value=Category.PRODUCTIVITY)
    classifier.classify_with_context = MagicMock(return_value=Classification(
        domain=Domain("example.com"),
        category=Category.PRODUCTIVITY,
        confidence=0.85
    ))
    return classifier


@pytest.fixture
def classifier_registry(mock_classifier, mock_context_aware_classifier):
    """Create a ClassifierRegistry with test classifiers."""
    registry = ClassifierRegistry()
    registry.register(mock_classifier)
    registry.register(mock_context_aware_classifier)
    return registry


@pytest.fixture
def classification_pipeline(classifier_registry):
    """Create a ClassificationPipeline with test classifiers."""
    pipeline = ClassificationPipeline(classifier_registry)
    pipeline.add_classifier("mock_classifier")
    pipeline.add_classifier("context_aware_classifier")
    return pipeline
