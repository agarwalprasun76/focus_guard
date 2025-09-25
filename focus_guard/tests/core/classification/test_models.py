"""
Tests for the domain models used in classification.
"""
import pytest
from datetime import datetime

from focus_guard.core.domain.models import (
    Domain,
    Category,
    Classification,
    DomainValidationError,
    URL
)


@pytest.fixture
def mock_domain():
    """Create a mock domain for testing."""
    return Domain("example.com")


class TestDomain:
    """Tests for the Domain model."""
    
    def test_domain_creation(self):
        """Test creating a valid domain."""
        domain = Domain("example.com")
        assert domain.value == "example.com"
    
    def test_domain_normalization(self):
        """Test domain normalization (lowercase, remove trailing dots)."""
        domain = Domain("  EXAMPLE.com.  ")
        assert domain.value == "example.com"
    
    def test_empty_domain(self):
        """Test that empty domain raises an error."""
        with pytest.raises(DomainValidationError):
            Domain("")
    
    def test_invalid_domain(self):
        """Test that invalid domain raises an error."""
        with pytest.raises(DomainValidationError):
            Domain("invalid domain")
    
    def test_domain_equality(self):
        """Test domain equality comparison."""
        domain1 = Domain("example.com")
        domain2 = Domain("EXAMPLE.com")
        domain3 = Domain("different.com")
        
        assert domain1 == domain2
        assert domain1 != domain3
        assert domain1 != "example.com"  # Different type
    
    def test_domain_hash(self):
        """Test that domains are hashable and can be used in sets/dicts."""
        domain1 = Domain("example.com")
        domain2 = Domain("EXAMPLE.com")
        domain_set = {domain1, domain2}
        
        assert len(domain_set) == 1  # Should be considered the same domain
        assert domain1 in domain_set
        assert domain2 in domain_set


class TestCategory:
    """Tests for the Category enum."""
    
    def test_from_string_valid(self):
        """Test converting valid strings to Category."""
        assert Category.from_string("SOCIAL_MEDIA") == Category.SOCIAL_MEDIA
        assert Category.from_string("social_media") == Category.SOCIAL_MEDIA
        assert Category.from_string("social-media") == Category.SOCIAL_MEDIA
        assert Category.from_string("social media") == Category.SOCIAL_MEDIA
    
    def test_from_string_invalid(self):
        """Test converting invalid strings raises an error."""
        with pytest.raises(ValueError):
            Category.from_string("NON_EXISTENT_CATEGORY")
    
    def test_str_representation(self):
        """Test string representation of categories."""
        assert str(Category.SOCIAL_MEDIA) == "social_media"
        assert str(Category.ENTERTAINMENT) == "entertainment"


class TestURL:
    """Tests for the URL model."""
    
    def test_url_creation(self):
        """Test creating a URL from a string."""
        url = URL("https://example.com/path?query=test")
        assert url.scheme == "https"
        assert url.domain_str == "example.com"
        assert url.path == "/path"
        assert url.query == "query=test"
    
    def test_url_domain_extraction(self):
        """Test domain extraction from URL."""
        url = URL("https://sub.example.com/path")
        assert isinstance(url.domain, Domain)
        assert url.domain.value == "sub.example.com"
    
    def test_invalid_url(self):
        """Test that invalid URL raises an error."""
        with pytest.raises(ValueError):
            URL("not-a-valid-url")


class TestClassification:
    """Tests for the Classification model."""
    
    def test_classification_result_creation(self, mock_domain):
        """Test creating a classification result."""
        result = Classification(
            domain=mock_domain,
            category=Category.ENTERTAINMENT,
            confidence=0.9,
            metadata={"source": "test"}
        )
        
        assert result.domain == mock_domain
        assert result.category == Category.ENTERTAINMENT
        assert result.confidence == 0.9
        assert result.metadata == {"source": "test"}
    
    def test_default_values(self, mock_domain):
        """Test default values for optional parameters."""
        result = Classification(
            domain=mock_domain,
            category=Category.PRODUCTIVITY
        )
        
        assert result.confidence == 1.0
        assert result.metadata is None
    
    def test_confidence_validation(self, mock_domain):
        """Test confidence value validation."""
        with pytest.raises(ValueError):
            Classification(
                domain=mock_domain,
                category=Category.NEWS,
                confidence=1.1  # Invalid, should be <= 1.0
            )
        
        with pytest.raises(ValueError):
            Classification(
                domain=mock_domain,
                category=Category.NEWS,
                confidence=-0.1  # Invalid, should be >= 0.0
            )
