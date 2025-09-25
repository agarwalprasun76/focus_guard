"""
Tests for LLM classifier adapter pattern.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from focus_guard.core.domain.models import Domain
from focus_guard.core.domain.models import Classification, Category


# Create a simple adapter class for testing
class LLMClassifierAdapter:
    """Adapter for legacy LLM classifiers."""
    
    def __init__(self, legacy_classifier=None):
        self.legacy_classifier = legacy_classifier or MagicMock()
        self.model = "default-model"
    
    def classify(self, domain, title=None):
        """Classify using the legacy classifier."""
        domain_str = domain.value if hasattr(domain, 'value') else domain
        result = self.legacy_classifier.classify(domain_str, title)
        # Map legacy result to new Classification object
        category = self._map_legacy_category(result)
        return Classification(
            domain=domain,
            category=category,
            confidence=1.0
        )
    
    def _map_legacy_category(self, legacy_result):
        """Map legacy category to new Category enum."""
        mapping = {
            "productive": Category.PRODUCTIVITY,
            "entertainment": Category.ENTERTAINMENT,
            "social": Category.SOCIAL_MEDIA,
            "shopping": Category.SHOPPING,
            "unknown": Category.UNKNOWN
        }
        if not legacy_result or legacy_result.lower() not in mapping:
            return Category.UNKNOWN
        return mapping[legacy_result.lower()]
    
    def set_model(self, model):
        """Set the model for the classifier."""
        self.model = model
        self.legacy_classifier.set_model(model)


@pytest.fixture
def mock_legacy_classifier():
    """Fixture for mock legacy classifier."""
    mock = MagicMock()
    mock.classify.return_value = "productive"
    return mock


@pytest.fixture
def adapter(mock_legacy_classifier):
    """Fixture for adapter with mock legacy classifier."""
    return LLMClassifierAdapter(mock_legacy_classifier)


class TestLLMClassifierAdapter:
    """Tests for the LLMClassifierAdapter."""
    
    def test_initialization(self, mock_legacy_classifier):
        """Test initialization of adapter."""
        adapter = LLMClassifierAdapter(mock_legacy_classifier)
        assert adapter.legacy_classifier == mock_legacy_classifier
        assert adapter.model == "default-model"
    
    def test_classify_with_domain_object(self, adapter, mock_legacy_classifier):
        """Test classify with Domain object."""
        domain = Domain("example.com")
        title = "Example Domain"
        
        result = adapter.classify(domain, title)
        
        # Verify legacy classifier was called correctly
        mock_legacy_classifier.classify.assert_called_once_with("example.com", title)
        
        # Verify result
        assert result.domain == domain
        assert result.category == Category.PRODUCTIVITY
        assert result.confidence == 1.0
    
    def test_classify_with_domain_string(self, adapter, mock_legacy_classifier):
        """Test classify with domain string."""
        domain = "example.com"
        title = "Example Domain"
        
        result = adapter.classify(domain, title)
        
        # Verify legacy classifier was called correctly
        mock_legacy_classifier.classify.assert_called_once_with(domain, title)
        
        # Verify result
        assert result.domain == domain
        assert result.category == Category.PRODUCTIVITY
        assert result.confidence == 1.0
    
    def test_category_mapping(self, adapter, mock_legacy_classifier):
        """Test mapping of legacy categories to new categories."""
        domain = "example.com"
        
        # Test different legacy categories
        test_cases = [
            ("productive", Category.PRODUCTIVITY),
            ("PRODUCTIVE", Category.PRODUCTIVITY),  # Test case insensitivity
            ("entertainment", Category.ENTERTAINMENT),
            ("social", Category.SOCIAL_MEDIA),
            ("shopping", Category.SHOPPING),
            ("unknown", Category.UNKNOWN),
            (None, Category.UNKNOWN),  # Test None
            ("invalid", Category.UNKNOWN)  # Test invalid category
        ]
        
        for legacy_category, expected_category in test_cases:
            mock_legacy_classifier.classify.return_value = legacy_category
            result = adapter.classify(domain)
            assert result.category == expected_category, f"Failed for legacy category: {legacy_category}"
    
    def test_set_model(self, adapter, mock_legacy_classifier):
        """Test setting model."""
        new_model = "new-model"
        adapter.set_model(new_model)
        
        # Verify model was set on adapter
        assert adapter.model == new_model
        
        # Verify model was set on legacy classifier
        mock_legacy_classifier.set_model.assert_called_once_with(new_model)
