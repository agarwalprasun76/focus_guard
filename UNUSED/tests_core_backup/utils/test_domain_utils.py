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
    
    # Tests from the original file with comprehensive test cases
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
    
    # More granular tests from the duplicate file
    def test_extract_domain_from_url_http(self):
        """Test extracting domain from HTTP URL."""
        url = "http://example.com/path/to/page"
        domain = extract_domain_from_url(url)
        self.assertEqual(domain, "example.com")
    
    def test_extract_domain_from_url_https(self):
        """Test extracting domain from HTTPS URL."""
        url = "https://example.com/path/to/page"
        domain = extract_domain_from_url(url)
        self.assertEqual(domain, "example.com")
    
    def test_extract_domain_from_url_with_www(self):
        """Test extracting domain from URL with www prefix."""
        url = "https://www.example.com/path/to/page"
        domain = extract_domain_from_url(url)
        self.assertEqual(domain, "example.com")
    
    def test_extract_domain_from_url_with_subdomain(self):
        """Test extracting domain from URL with subdomain."""
        url = "https://sub.example.com/path/to/page"
        domain = extract_domain_from_url(url)
        self.assertEqual(domain, "sub.example.com")
    
    def test_extract_domain_from_url_with_port(self):
        """Test extracting domain from URL with port."""
        url = "https://example.com:8080/path/to/page"
        domain = extract_domain_from_url(url)
        self.assertEqual(domain, "example.com")
    
    def test_extract_domain_from_url_with_query_params(self):
        """Test extracting domain from URL with query parameters."""
        url = "https://example.com/path/to/page?param1=value1&param2=value2"
        domain = extract_domain_from_url(url)
        self.assertEqual(domain, "example.com")
    
    def test_extract_domain_from_url_with_fragment(self):
        """Test extracting domain from URL with fragment."""
        url = "https://example.com/path/to/page#section1"
        domain = extract_domain_from_url(url)
        self.assertEqual(domain, "example.com")
    
    def test_extract_domain_from_url_with_username_password(self):
        """Test extracting domain from URL with username and password."""
        url = "https://user:pass@example.com/path/to/page"
        domain = extract_domain_from_url(url)
        self.assertEqual(domain, "example.com")
    
    def test_extract_domain_from_url_invalid_url(self):
        """Test extracting domain from invalid URL."""
        url = "not a valid url"
        domain = extract_domain_from_url(url)
        self.assertIsNone(domain)
    
    def test_extract_domain_from_url_empty_url(self):
        """Test extracting domain from empty URL."""
        url = ""
        domain = extract_domain_from_url(url)
        self.assertIsNone(domain)
    
    def test_extract_domain_from_url_none(self):
        """Test extracting domain from None."""
        url = None
        domain = extract_domain_from_url(url)
        self.assertIsNone(domain)
    
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
    
    # Tests from the duplicate file for is_subdomain_of
    def test_is_subdomain_of_exact_match(self):
        """Test is_subdomain_of with exact match."""
        domain = "example.com"
        parent_domain = "example.com"
        result = is_subdomain(domain, parent_domain)
        self.assertFalse(result)  # is_subdomain returns False for exact match
    
    def test_is_subdomain_of_subdomain(self):
        """Test is_subdomain_of with subdomain."""
        domain = "sub.example.com"
        parent_domain = "example.com"
        result = is_subdomain(domain, parent_domain)
        self.assertTrue(result)
    
    def test_is_subdomain_of_nested_subdomain(self):
        """Test is_subdomain_of with nested subdomain."""
        domain = "nested.sub.example.com"
        parent_domain = "example.com"
        result = is_subdomain(domain, parent_domain)
        self.assertTrue(result)
    
    def test_is_subdomain_of_different_domain(self):
        """Test is_subdomain_of with different domain."""
        domain = "example.org"
        parent_domain = "example.com"
        result = is_subdomain(domain, parent_domain)
        self.assertFalse(result)
    
    def test_is_subdomain_of_partial_match(self):
        """Test is_subdomain_of with partial match."""
        domain = "myexample.com"
        parent_domain = "example.com"
        result = is_subdomain(domain, parent_domain)
        self.assertFalse(result)
    
    def test_is_subdomain_of_case_insensitive(self):
        """Test is_subdomain_of is case insensitive."""
        domain = "Sub.Example.Com"
        parent_domain = "example.com"
        result = is_subdomain(domain, parent_domain)
        self.assertTrue(result)
    
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
        ]
        
        for url, expected_domain in test_cases:
            domain = create_domain_from_url(url)
            if expected_domain:
                self.assertIsInstance(domain, Domain)
                self.assertEqual(domain.value, expected_domain)
            else:
                self.assertIsNone(domain)
    
    def test_create_url_from_string(self):
        """Test creating URL object from string."""
        test_cases = [
            ("http://example.com", "http://example.com"),
            ("https://sub.example.com/path", "https://sub.example.com/path"),
            ("invalid-url", None),
        ]
        
        for url_str, expected_url in test_cases:
            url = create_url_from_string(url_str)
            if expected_url:
                self.assertIsInstance(url, URL)
                self.assertEqual(str(url), expected_url)
            else:
                self.assertIsNone(url)
    
    def test_is_ip_address(self):
        """Test IP address detection."""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "127.0.0.1",
            "0.0.0.0",
            "255.255.255.255",
        ]
        
        invalid_ips = [
            "example.com",
            "192.168.1",
            "192.168.1.256",
            "192.168.1.1.1",
            "",
            "300.300.300.300",  # Out of range
            "192.168.1.a",     # Non-numeric
            "192.168.1",       # Incomplete
            None,               # None input
        ]
        
        for ip in valid_ips:
            self.assertTrue(is_ip_address(ip), f"Expected {ip} to be a valid IP")
        
        for ip in invalid_ips:
            if ip is not None:  # Skip None for assertion message formatting
                self.assertFalse(is_ip_address(ip), f"Expected {ip} to be an invalid IP")
            else:
                self.assertFalse(is_ip_address(ip), "Expected None to be an invalid IP")
                
    def test_is_ip_address_ipv6_basic(self):
        """Test IPv6 address detection with basic patterns."""
        # Basic IPv6 addresses that should match the simplified pattern
        valid_ipv6 = [
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "fe80:0000:0000:0000:0202:b3ff:fe1e:8329",
        ]
        
        for ip in valid_ipv6:
            self.assertTrue(is_ip_address(ip), f"Expected {ip} to be a valid IPv6")
            
    def test_is_ip_address_regex_patterns(self):
        """Test the regex patterns used in is_ip_address function."""
        import re
        
        # Test IPv4 pattern
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        
        # Valid format (not checking value ranges)
        self.assertTrue(bool(re.match(ipv4_pattern, "192.168.1.1")))
        
        # Invalid format
        self.assertFalse(bool(re.match(ipv4_pattern, "192.168.1")))
        self.assertFalse(bool(re.match(ipv4_pattern, "192.168.1.1.1")))
        
        # IPv6 pattern (simplified)
        ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
        
        # Valid format for the simplified pattern
        self.assertTrue(bool(re.match(ipv6_pattern, "2001:0db8:85a3:0000:0000:8a2e:0370:7334")))
        
        # Invalid format
        self.assertFalse(bool(re.match(ipv6_pattern, "2001:0db8:85a3:0000:0000:8a2e:0370")))
        self.assertFalse(bool(re.match(ipv6_pattern, "2001:0db8:85a3:0000:0000:8a2e:0370:7334:extra")))
    
    def test_is_localhost(self):
        """Test localhost detection."""
        localhost_domains = [
            "localhost",
            "127.0.0.1",
            "::1",
        ]
        
        non_localhost_domains = [
            "example.com",
            "192.168.1.1",
            "10.0.0.1",
            "8.8.8.8",
            "2001:4860:4860::8888",  # Google DNS IPv6
            "",  # Empty string
        ]
        
        for domain in localhost_domains:
            self.assertTrue(is_localhost(domain), f"Expected {domain} to be localhost")
        
        for domain in non_localhost_domains:
            self.assertFalse(is_localhost(domain), f"Expected {domain} not to be localhost")
            
    def test_is_localhost_pattern_matching(self):
        """Test localhost detection pattern matching."""
        # Test each pattern individually
        patterns = [
            "localhost",
            "127.0.0.1",
            "::1"
        ]
        
        for pattern in patterns:
            self.assertTrue(is_localhost(pattern), f"Expected pattern {pattern} to match")


if __name__ == "__main__":
    unittest.main()
