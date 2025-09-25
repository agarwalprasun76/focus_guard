import unittest
from typing import List, Optional, Union
from core.domain_classifier.domain_classifier import classify_domain, get_all_categories, get_all_domains
from core.domain_classifier.domain_whitelist import domain_whitelist, add_to_whitelist, remove_from_whitelist, get_whitelisted_domains
from core.domain_classifier.filter_domain import filter_domain
from core.domain_classifier.domain_excluder import domain_excluder, _excluded_domains
from core.domain_classifier.domain_utils import (
    normalize_domain, 
    is_valid_domain, 
    extract_domain_from_url,
    is_subdomain,
    get_domain_parts
)

class TestDomainClassifierPipeline(unittest.TestCase):
    def setUp(self):
        # Patch _excluded_domains for predictable testing
        _excluded_domains.clear()
        _excluded_domains.update({"pornhub.com", "bet365.com", "fakenewswebsite.com"})

    def tearDown(self):
        _excluded_domains.clear()

    def test_domain_excluder(self):
        # Test with known excluded domains
        self.assertTrue(domain_excluder("pornhub.com"))
        self.assertTrue(domain_excluder("bet365.com"))
        
        # Test with non-excluded domains
        self.assertFalse(domain_excluder("google.com"))
        self.assertFalse(domain_excluder("microsoft.com"))
        
        # Test case sensitivity
        self.assertTrue(domain_excluder("PORNHUB.COM"))
        self.assertTrue(domain_excluder("PornHub.com"))
        
        # Test subdomains
        self.assertTrue(domain_excluder("www.pornhub.com"))  # Subdomain of excluded
        self.assertFalse(domain_excluder("mail.google.com"))  # Subdomain of non-excluded
        
        # Test with URLs instead of domains
        self.assertTrue(domain_excluder("https://pornhub.com"))
        self.assertFalse(domain_excluder("http://google.com/path"))
        
        # Test email addresses - should all be rejected
        email_test_cases = [
            "user@google.com",
            "admin@pornhub.com",  # Even if domain is excluded
            "test@example.com",
            "@example.com",
            "user@",
            "@",
            "user@sub.example.com"
        ]
        for email in email_test_cases:
            with self.subTest(email=email):
                self.assertFalse(domain_excluder(email), 
                               f"Email '{email}' should be rejected by excluder")
        
        # Test invalid inputs
        self.assertFalse(domain_excluder(""))  # Empty string
        self.assertFalse(domain_excluder(" "))  # Whitespace
        self.assertFalse(domain_excluder("invalid domain"))  # Invalid domain
        self.assertTrue(domain_excluder("http://pornhub.com"))  # URL with excluded domain
        self.assertTrue(domain_excluder("pornhub.com/path"))  # Path included
        self.assertTrue(domain_excluder("pornhub.com?query=test"))  # Query included
        self.assertTrue(domain_excluder("pornhub.com#fragment"))  # Fragment included
        self.assertTrue(domain_excluder("pornhub.com:8080"))  # Port included
        
        # IP addresses should be rejected
        self.assertFalse(domain_excluder("192.168.1.1"))  # IPv4 address
        self.assertFalse(domain_excluder("2001:0db8:85a3:0000:0000:8a2e:0370:7334"))  # IPv6
        
        # Test with None and non-string inputs
        self.assertFalse(domain_excluder(None))
        self.assertFalse(domain_excluder(123))
        self.assertFalse(domain_excluder({"key": "value"}))

    def test_domain_classifier(self):
        # Test with categorized domains (plain format)
        self.assertEqual(classify_domain("khanacademy.org"), "education")
        self.assertEqual(classify_domain("coursera.org"), "education")
        self.assertEqual(classify_domain("facebook.com"), "social")
        self.assertEqual(classify_domain("twitter.com"), "social")
        self.assertIsNone(classify_domain("nonexistent.com"))  # Not in any category
        
        # Test case sensitivity
        self.assertEqual(classify_domain("KHANACADEMY.ORG"), "education")
        self.assertEqual(classify_domain("FaceBook.com"), "social")
        
        # Test with URLs - should work the same as plain domains
        self.assertEqual(classify_domain("https://khanacademy.org"), "education")
        self.assertEqual(classify_domain("http://facebook.com"), "social")
        
        # Test email addresses - should all be rejected
        email_test_cases = [
            "user@google.com",
            "admin@microsoft.com",
            "test@example.com",
            "@example.com",
            "user@",
            "@",
            "user@sub.example.com",
            "first.last@domain.co.uk"
        ]
        for email in email_test_cases:
            with self.subTest(email=email):
                self.assertIsNone(classify_domain(email), 
                                f"Email '{email}' should be rejected by classifier")
        
        # Test invalid inputs
        self.assertIsNone(classify_domain(""))  # Empty string
        self.assertIsNone(classify_domain(" "))  # Whitespace
        self.assertIsNone(classify_domain("invalid domain"))  # Invalid domain
        self.assertIsNone(classify_domain("http://"))  # Invalid URL
        self.assertEqual(classify_domain("google.com/path"), "work")  # Path should be stripped
        self.assertEqual(classify_domain("google.com?query=test"), "work")  # Query should be stripped
        self.assertEqual(classify_domain("google.com#fragment"), "work")  # Fragment should be stripped
        self.assertEqual(classify_domain("google.com:8080"), "work")  # Port should be stripped
        self.assertIsNone(classify_domain("192.168.1.1"))  # IP address
        self.assertIsNone(classify_domain("2001:0db8:85a3:0000:0000:8a2e:0370:7334"))  # IPv6
        
        # Test with None and non-string inputs
        self.assertIsNone(classify_domain(None))
        self.assertIsNone(classify_domain(123))
        self.assertIsNone(classify_domain({"key": "value"}))
        
        # Test with very long domain
        long_domain = "a" * 63 + "." + "b" * 63 + "." + "c" * 63 + ".com"
        self.assertIsNone(classify_domain(long_domain))  # Long but valid domain
        
        self.assertIsNone(classify_domain("münchen.de"))  # IDN domain

    def test_domain_whitelist(self):
        # Test with domains that are actually in the whitelist
        self.assertTrue(domain_whitelist("google.com"))
        self.assertTrue(domain_whitelist("microsoft.com"))
        self.assertFalse(domain_whitelist("facebook.com"))
        self.assertFalse(domain_whitelist("khanacademy.org"))  # Not in whitelist
        
        # Test case sensitivity
        self.assertTrue(domain_whitelist("GOOGLE.COM"))
        self.assertTrue(domain_whitelist("Google.com"))
        
        # Test subdomains
        self.assertTrue(domain_whitelist("mail.google.com"))  # Subdomain of whitelisted domain
        self.assertTrue(domain_whitelist("subdomain.microsoft.com"))  # Subdomain of whitelisted domain
        
        # Test with URLs instead of domains
        self.assertTrue(domain_whitelist("https://google.com"))
        self.assertTrue(domain_whitelist("http://microsoft.com/path"))
        
        # Test email addresses - should all be rejected
        email_test_cases = [
            "user@google.com",
            "admin@microsoft.com",
            "test@example.com",
            "@example.com",
            "user@",
            "@",
            "user@sub.example.com",
            "first.last@domain.co.uk"
        ]
        for email in email_test_cases:
            with self.subTest(email=email):
                self.assertFalse(domain_whitelist(email), 
                               f"Email '{email}' should be rejected by whitelist")
        
        # Test invalid inputs
        self.assertFalse(domain_whitelist(""))  # Empty string
        self.assertFalse(domain_whitelist(" "))  # Whitespace
        self.assertFalse(domain_whitelist("invalid domain"))  # Invalid domain
        self.assertTrue(domain_whitelist("http://google.com"))  # URL with whitelisted domain
        self.assertTrue(domain_whitelist("google.com/path"))  # Path included
        self.assertTrue(domain_whitelist("google.com?query=test"))  # Query included
        self.assertTrue(domain_whitelist("google.com#fragment"))  # Fragment included
        self.assertTrue(domain_whitelist("google.com:8080"))  # Port included
        
        # IP addresses should be rejected
        self.assertFalse(domain_whitelist("192.168.1.1"))  # IPv4 address
        self.assertFalse(domain_whitelist("2001:0db8:85a3:0000:0000:8a2e:0370:7334"))  # IPv6
        
        # Test with None and non-string inputs
        self.assertFalse(domain_whitelist(None))
        self.assertFalse(domain_whitelist(123))
        self.assertFalse(domain_whitelist({"key": "value"}))
        
        # Test dynamic whitelist modification
        original_whitelist = get_whitelisted_domains().copy()
        try:
            # Add a test domain
            add_to_whitelist("test-whitelist.com")
            self.assertTrue(domain_whitelist("test-whitelist.com"))
            self.assertIn("test-whitelist.com", get_whitelisted_domains())
            
            # Remove the test domain
            remove_from_whitelist("test-whitelist.com")
            self.assertFalse(domain_whitelist("test-whitelist.com"))
            self.assertNotIn("test-whitelist.com", get_whitelisted_domains())
        finally:
            # Restore original whitelist
            current = get_whitelisted_domains()
            current.clear()
            current.update(original_whitelist)

    def test_filter_domain(self):
        # Test excluded domains
        self.assertEqual(filter_domain("pornhub.com"), "excluded")
        self.assertEqual(filter_domain("bet365.com"), "excluded")
        
        # Test categorized domains
        self.assertEqual(filter_domain("khanacademy.org"), "education")
        self.assertEqual(filter_domain("facebook.com"), "social")
        
        # Test whitelisted domains
        self.assertEqual(filter_domain("google.com"), "whitelisted")
        
        # Test unknown domains
        self.assertEqual(filter_domain("randomsite.xyz"), "unknown")
        
        # Test case sensitivity
        self.assertEqual(filter_domain("PORNHUB.COM"), "excluded")
        self.assertEqual(filter_domain("FACEBOOK.COM"), "social")
        
        # Test subdomains
        self.assertEqual(filter_domain("sub.pornhub.com"), "excluded")  # Subdomain of excluded
        self.assertEqual(filter_domain("mail.google.com"), "whitelisted")  # Subdomain of whitelisted
        
        # Test invalid inputs
        self.assertEqual(filter_domain(""), "unknown")  # Empty string
        self.assertEqual(filter_domain(" "), "unknown")  # Whitespace
        self.assertEqual(filter_domain("invalid domain"), "unknown")  # Invalid domain
        self.assertEqual(filter_domain("http://example.com"), "unknown")  # URL with no category
        self.assertEqual(filter_domain("example.com/path"), "unknown")  # Path included
        self.assertEqual(filter_domain("example.com?query=test"), "unknown")  # Query included
        self.assertEqual(filter_domain("example.com#fragment"), "unknown")  # Fragment included
        self.assertEqual(filter_domain("example.com:8080"), "unknown")  # Port included
        self.assertEqual(filter_domain("user@example.com"), "unknown")  # Email instead of domain
        self.assertEqual(filter_domain("192.168.1.1"), "unknown")  # IP address
        self.assertEqual(filter_domain("2001:0db8:85a3:0000:0000:8a2e:0370:7334"), "unknown")  # IPv6 address
        
        # Test with None
        self.assertEqual(filter_domain(None), "unknown")  # None input

    def test_domain_utils(self):
        # Test normalize_domain
        self.assertEqual(normalize_domain("GOOGLE.COM"), "google.com")
        self.assertEqual(normalize_domain("http://example.com"), "example.com")
        self.assertEqual(normalize_domain("example.com/"), "example.com")
        self.assertIsNone(normalize_domain(""))
        self.assertIsNone(normalize_domain(" "))
        self.assertIsNone(normalize_domain("invalid domain"))
        
        # Test is_valid_domain
        self.assertTrue(is_valid_domain("example.com"))
        self.assertTrue(is_valid_domain("sub.example.com"))
        self.assertFalse(is_valid_domain(""))
        self.assertFalse(is_valid_domain(" "))
        self.assertFalse(is_valid_domain("invalid domain"))
        
        # Test extract_domain_from_url
        self.assertEqual(extract_domain_from_url("http://example.com"), "example.com")
        self.assertEqual(extract_domain_from_url("https://sub.example.com/path"), "sub.example.com")
        self.assertIsNone(extract_domain_from_url("not a url"))
        
        # Test is_subdomain
        self.assertTrue(is_subdomain("sub.example.com", "example.com"))
        self.assertFalse(is_subdomain("example.com", "sub.example.com"))
        self.assertFalse(is_subdomain("example.com", ""))
        
        # Test get_domain_parts
        self.assertEqual(get_domain_parts("sub.example.com"), ["sub", "example", "com"])
        self.assertEqual(get_domain_parts("example.com"), ["example", "com"])
        self.assertEqual(get_domain_parts(""), [])
    
    def test_get_all_functions(self):
        # Test get_all_categories
        categories = get_all_categories()
        self.assertIsInstance(categories, list)
        self.assertIn("work", categories)
        self.assertIn("social", categories)
        
        # Test get_all_domains
        domains = get_all_domains()
        self.assertIsInstance(domains, dict)
        self.assertIn("work", domains)
        self.assertIn("social", domains)
        self.assertIsInstance(domains["work"], list)
        self.assertTrue(all(isinstance(d, str) for d in domains["work"]))

if __name__ == "__main__":
    unittest.main()
