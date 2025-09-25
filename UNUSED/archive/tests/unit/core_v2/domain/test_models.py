"""
Unit tests for domain models.

This module contains tests for the Domain and URL classes.
"""

import unittest
from unittest import TestCase

from core_v2.domain.models import Domain, URL, DomainValidationError, Category


class TestDomain(TestCase):
    """Tests for the Domain class."""
    
    def test_valid_domain_initialization(self):
        """Test that valid domains can be initialized."""
        domains = [
            "example.com",
            "sub.example.com",
            "sub.sub.example.com",
            "example.co.uk",
            "xn--80aswg.xn--p1ai",  # Punycode domain
        ]
        
        for domain_str in domains:
            domain = Domain(domain_str)
            self.assertEqual(domain.value, domain_str)
    
    def test_domain_normalization(self):
        """Test that domains are normalized during initialization."""
        test_cases = [
            ("EXAMPLE.COM", "example.com"),
            ("Example.Com", "example.com"),
            ("example.com.", "example.com"),
            ("  example.com  ", "example.com"),
        ]
        
        for input_domain, expected_domain in test_cases:
            domain = Domain(input_domain)
            self.assertEqual(domain.value, expected_domain)
    
    def test_invalid_domain_initialization(self):
        """Test that invalid domains raise DomainValidationError."""
        invalid_domains = [
            "",  # Empty domain
            "example",  # No TLD
            "example com",  # Space in domain
            "http://example.com",  # URL, not domain
        ]
        
        for domain_str in invalid_domains:
            with self.assertRaises(DomainValidationError):
                Domain(domain_str)
    
    def test_domain_parts(self):
        """Test that domain parts are correctly extracted."""
        domain = Domain("sub.example.com")
        self.assertEqual(domain.parts, ["sub", "example", "com"])
    
    def test_domain_tld(self):
        """Test that TLD is correctly extracted."""
        test_cases = [
            ("example.com", "com"),
            ("example.co.uk", "uk"),
            ("sub.example.com", "com"),
        ]
        
        for domain_str, expected_tld in test_cases:
            domain = Domain(domain_str)
            self.assertEqual(domain.tld, expected_tld)
    
    def test_registered_domain(self):
        """Test that registered domain is correctly extracted."""
        test_cases = [
            ("example.com", "example.com"),
            ("sub.example.com", "example.com"),
            ("sub.sub.example.com", "example.com"),
            ("example.co.uk", "co.uk"),  # Simplified implementation
        ]
        
        for domain_str, expected_registered_domain in test_cases:
            domain = Domain(domain_str)
            self.assertEqual(domain.registered_domain, expected_registered_domain)
    
    def test_is_subdomain_of(self):
        """Test the is_subdomain_of method."""
        test_cases = [
            ("sub.example.com", "example.com", True),
            ("sub.sub.example.com", "example.com", True),
            ("sub.example.com", "sub.example.com", False),  # Same domain
            ("example.com", "example.org", False),  # Different domains
            ("example.com", "com", True),  # TLD as parent
        ]
        
        for domain_str, parent_str, expected_result in test_cases:
            domain = Domain(domain_str)
            parent = Domain(parent_str)
            self.assertEqual(domain.is_subdomain_of(parent), expected_result)
    
    def test_domain_equality(self):
        """Test domain equality comparison."""
        domain1 = Domain("example.com")
        domain2 = Domain("example.com")
        domain3 = Domain("sub.example.com")
        
        self.assertEqual(domain1, domain2)
        self.assertNotEqual(domain1, domain3)
        
        # Test equality with string
        self.assertEqual(domain1, "example.com")
        self.assertNotEqual(domain1, "sub.example.com")


class TestURL(TestCase):
    """Tests for the URL class."""
    
    def test_valid_url_initialization(self):
        """Test that valid URLs can be initialized."""
        urls = [
            "http://example.com",
            "https://example.com",
            "http://sub.example.com/path",
            "https://example.com/path?query=value",
            "https://example.com:8080/path",
        ]
        
        for url_str in urls:
            url = URL(url_str)
            self.assertEqual(url.value, url_str)
    
    def test_invalid_url_initialization(self):
        """Test that invalid URLs raise ValueError."""
        invalid_urls = [
            "",  # Empty URL
            "example.com",  # No scheme
            "http://",  # No domain
            "http:///path",  # No domain
        ]
        
        for url_str in invalid_urls:
            with self.assertRaises(ValueError):
                URL(url_str)
    
    def test_url_domain_extraction(self):
        """Test that domain is correctly extracted from URL."""
        test_cases = [
            ("http://example.com", "example.com"),
            ("https://sub.example.com/path", "sub.example.com"),
            ("http://example.com:8080/path", "example.com"),
            ("https://user:pass@example.com/path", "example.com"),
        ]
        
        for url_str, expected_domain in test_cases:
            url = URL(url_str)
            self.assertEqual(url.domain.value, expected_domain)
    
    def test_url_scheme_extraction(self):
        """Test that scheme is correctly extracted from URL."""
        test_cases = [
            ("http://example.com", "http"),
            ("https://example.com", "https"),
            ("ftp://example.com", "ftp"),
        ]
        
        for url_str, expected_scheme in test_cases:
            url = URL(url_str)
            self.assertEqual(url.scheme, expected_scheme)
    
    def test_url_path_extraction(self):
        """Test that path is correctly extracted from URL."""
        test_cases = [
            ("http://example.com", ""),
            ("https://example.com/", "/"),
            ("https://example.com/path", "/path"),
            ("https://example.com/path/to/resource", "/path/to/resource"),
        ]
        
        for url_str, expected_path in test_cases:
            url = URL(url_str)
            self.assertEqual(url.path, expected_path)
    
    def test_url_query_extraction(self):
        """Test that query string is correctly extracted from URL."""
        test_cases = [
            ("http://example.com", ""),
            ("https://example.com/?", ""),
            ("https://example.com/?query=value", "query=value"),
            ("https://example.com/?a=1&b=2", "a=1&b=2"),
        ]
        
        for url_str, expected_query in test_cases:
            url = URL(url_str)
            self.assertEqual(url.query, expected_query)


class TestCategory(TestCase):
    """Tests for the Category enum."""
    
    def test_category_from_string(self):
        """Test converting strings to Category enum values."""
        test_cases = [
            ("SOCIAL_MEDIA", Category.SOCIAL_MEDIA),
            ("social_media", Category.SOCIAL_MEDIA),
            ("ENTERTAINMENT", Category.ENTERTAINMENT),
            ("productivity", Category.PRODUCTIVITY),
        ]
        
        for category_str, expected_category in test_cases:
            self.assertEqual(Category.from_string(category_str), expected_category)
    
    def test_invalid_category_from_string(self):
        """Test that invalid category strings raise ValueError."""
        with self.assertRaises(ValueError):
            Category.from_string("invalid_category")


if __name__ == "__main__":
    unittest.main()
