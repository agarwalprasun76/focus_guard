"""
Tests for base domain classifier implementations.
"""
import pytest
from unittest.mock import MagicMock, patch

from focus_guard.core.classification.classifiers.domains.base import BaseDomainClassifier
from focus_guard.core.domain.models import Domain, Category, Classification


class TestBaseDomainClassifier:
    """Tests for the BaseDomainClassifier class."""
    
    @pytest.fixture
    def base_classifier(self):
        """Create a concrete BaseDomainClassifier for testing."""
        
        class TestDomainClassifier(BaseDomainClassifier):
            def classify(self, domain):
                return Category.ENTERTAINMENT
            
            def classify_with_context(self, domain, context):
                # Default implementation calls classify
                result = self.classify(domain)
                if result is not None:
                    return Classification(
                        domain=domain,
                        category=result,
                        confidence=1.0,
                        metadata={"classifier": "BaseDomainClassifier"}
                    )
                return None
            
            def _get_domain_variations(self, domain):
                # Split domain into parts and return variations
                parts = domain.value.split('.')
                variations = []
                for i in range(len(parts)):
                    variations.append('.'.join(parts[i:]))
                return variations
            
            def _is_above_confidence_threshold(self, classification, threshold):
                return classification.confidence > threshold
        
        return TestDomainClassifier("test_classifier")
    
    def test_name_property(self, base_classifier):
        """Test that the name property returns the class name."""
        assert base_classifier.name == "test_classifier"
    
    def test_classify_not_implemented(self):
        """Test that the base classify method raises NotImplementedError."""
        # Create a minimal concrete class to test the abstract method
        class TestAbstractClassifier(BaseDomainClassifier):
            def classify(self, domain):
                raise NotImplementedError
        
        classifier = TestAbstractClassifier("test_classifier")
        domain = Domain("example.com")
        with pytest.raises(NotImplementedError):
            classifier.classify(domain)
    
    def test_classify_with_context_calls_classify(self, base_classifier):
        """Test that classify_with_context calls classify by default."""
        domain = Domain("example.com")
        context = {"url": "https://example.com"}
        
        # Patch the classify method to return a known value
        with patch.object(base_classifier, 'classify', 
                         return_value=Category.PRODUCTIVITY) as mock_classify:
            
            result = base_classifier.classify_with_context(domain, context)
            
            # Should have called the classify method
            mock_classify.assert_called_once_with(domain)
            
            # Should return a Classification with the category from classify()
            assert isinstance(result, Classification)
            assert result.domain == domain
            assert result.category == Category.PRODUCTIVITY
            assert result.confidence == 1.0
            assert result.metadata == {"classifier": "BaseDomainClassifier"}
    
    def test_get_domain_variations(self, base_classifier):
        """Test that domain variations are generated correctly."""
        domain = Domain("sub.example.com")
        variations = base_classifier._get_domain_variations(domain)
        
        # Should return all possible domain variations
        expected = [
            "sub.example.com",
            "example.com",
            "com"
        ]
        assert variations == expected
    
    def test_get_domain_variations_tld(self, base_classifier):
        """Test domain variations for TLD-only domains."""
        domain = Domain("com")  # Just a TLD
        variations = base_classifier._get_domain_variations(domain)
        assert variations == ["com"]
    
    @pytest.mark.parametrize("confidence_threshold,expected", [
        (0.8, True),  # Above threshold
        (0.9, False),  # At threshold
        (0.95, False), # Below threshold
    ])
    def test_is_above_confidence_threshold(self, base_classifier, confidence_threshold, expected):
        """Test confidence threshold comparison."""
        result = Classification(
            domain=Domain("example.com"),
            category=Category.ENTERTAINMENT,
            confidence=0.9
        )
        
        assert base_classifier._is_above_confidence_threshold(
            result, 
            confidence_threshold
        ) == expected
