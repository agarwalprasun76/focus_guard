"""
Unit tests for domain utilities.

This module contains tests for the domain utility functions.
"""

import unittest
from unittest import TestCase

from core_v2.utils.domain_utils import (
    extract_domain_from_url,
    normalize_domain,
    is_valid_domain,
    get_domain_parts,
    get_parent_domains,
    is_subdomain,
    get_registered_domain,
    create_domain_from_url,
    create_url_from_string,
    is_ip_address,
    is_localhost
)
from core_v2.domain.models import Domain, URL


class TestDomainUtils(TestCase):
    """Tests for domain utility functions."""
    
    def test_extract_domain_from_url(self):
        """Test extracting domain from URL."""
        test_cases = [
            ("http://example.com", "example.com"),
            ("https://sub.example.com/path", "sub.example.com"),
            ("http://example.com:8080/path", "example.com"),
            ("https://user:pass@example.com/path", "example.com"),
            ("invalid-url", None),
            ("", None),
        ]
        
        for url, expected_domain in test_cases:
            self.assertEqual(extract_domain_from_url(url), expected_domain)
    
    def test_normalize_domain(self):
        """Test domain normalization."""
        test_cases = [
            ("EXAMPLE.COM", "example.com"),
            ("Example.Com", "example.com"),
            ("example.com.", "example.com"),
            ("  example.com  ", "example.com"),
            ("", ""),
        ]
        
        for input_domain, expected_domain in test_cases:
            self.assertEqual(normalize_domain(input_domain), expected_domain)
    
    def test_is_valid_domain(self):
        """Test domain validation."""
        valid_domains = [
            "example.com",
            "sub.example.com",
            "sub-domain.example.com",
            "example.co.uk",
        ]
        
        invalid_domains = [
            "",
            "example",
            "example com",
            "http://example.com",
            "-example.com",
            "example-.com",
            "a" * 256 + ".com",  # Too long
        ]
        
        for domain in valid_domains:
            self.assertTrue(is_valid_domain(domain), f"Expected {domain} to be valid")
        
        for domain in invalid_domains:
            self.assertFalse(is_valid_domain(domain), f"Expected {domain} to be invalid")
    
    def test_get_domain_parts(self):
        """Test splitting domain into parts."""
        test_cases = [
            ("example.com", ["example", "com"]),
            ("sub.example.com", ["sub", "example", "com"]),
            ("a.b.c.d.com", ["a", "b", "c", "d", "com"]),
            ("", [""]),
        ]
        
        for domain, expected_parts in test_cases:
            self.assertEqual(get_domain_parts(domain), expected_parts)
    
    def test_get_parent_domains(self):
        """Test getting parent domains."""
        test_cases = [
            ("www.example.com", ["example.com", "com"]),
            ("a.b.c.d.com", ["b.c.d.com", "c.d.com", "d.com", "com"]),
            ("example.com", ["com"]),
            ("com", []),
            ("", []),
        ]
        
        for domain, expected_parents in test_cases:
            self.assertEqual(get_parent_domains(domain), expected_parents)
    
    def test_is_subdomain(self):
        """Test subdomain checking."""
        test_cases = [
            ("sub.example.com", "example.com", True),
            ("sub.sub.example.com", "example.com", True),
            ("example.com", "example.com", False),  # Same domain
            ("example.com", "example.org", False),  # Different domains
            ("example.com", "com", True),  # TLD as parent
            ("com", "com", False),  # Same domain
            ("", "", False),  # Empty domains
        ]
        
        for domain, parent, expected_result in test_cases:
            self.assertEqual(is_subdomain(domain, parent), expected_result)
    
    def test_get_registered_domain(self):
        """Test getting registered domain."""
        test_cases = [
            ("example.com", "example.com"),
            ("sub.example.com", "example.com"),
            ("sub.sub.example.com", "example.com"),
            ("example.co.uk", "example.co.uk"),  # Simplified implementation
        ]
        
        for domain, expected_registered_domain in test_cases:
            self.assertEqual(get_registered_domain(domain), expected_registered_domain)
    
    def test_create_domain_from_url(self):
        """Test creating Domain object from URL."""
        test_cases = [
            ("http://example.com", "example.com"),
            ("https://sub.example.com/path", "sub.example.com"),
            ("invalid-url", None),
            ("", None),
        ]
        
        for url, expected_domain in test_cases:
            domain = create_domain_from_url(url)
            if expected_domain is None:
                self.assertIsNone(domain)
            else:
                self.assertIsInstance(domain, Domain)
                self.assertEqual(domain.value, expected_domain)
    
    def test_create_url_from_string(self):
        """Test creating URL object from string."""
        valid_urls = [
            "http://example.com",
            "https://example.com/path",
            "ftp://example.com",
        ]
        
        invalid_urls = [
            "",
            "example.com",  # No scheme
            "http://",  # No domain
        ]
        
        for url_str in valid_urls:
            url = create_url_from_string(url_str)
            self.assertIsInstance(url, URL)
            self.assertEqual(url.value, url_str)
        
        for url_str in invalid_urls:
            self.assertIsNone(create_url_from_string(url_str))
    
    def test_is_ip_address(self):
        """Test IP address detection."""
        ip_addresses = [
            "192.168.1.1",
            "10.0.0.1",
            "127.0.0.1",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",  # IPv6
        ]
        
        non_ip_addresses = [
            "example.com",
            "192.168.1",  # Incomplete IPv4
            "192.168.1.256",  # Invalid IPv4
            "2001:0db8:85a3:0000:0000:8a2e:0370",  # Incomplete IPv6
        ]
        
        for ip in ip_addresses:
            self.assertTrue(is_ip_address(ip), f"Expected {ip} to be an IP address")
        
        for non_ip in non_ip_addresses:
            self.assertFalse(is_ip_address(non_ip), f"Expected {non_ip} not to be an IP address")
    
    def test_is_localhost(self):
        """Test localhost detection."""
        localhost_domains = [
            "localhost",
            "127.0.0.1",
            "::1",
        ]
        
        non_localhost_domains = [
            "example.com",
            "127.0.0.2",
            "192.168.1.1",
        ]
        
        for domain in localhost_domains:
            self.assertTrue(is_localhost(domain), f"Expected {domain} to be localhost")
        
        for domain in non_localhost_domains:
            self.assertFalse(is_localhost(domain), f"Expected {domain} not to be localhost")


if __name__ == "__main__":
    unittest.main()
