"""
Unit tests for domain constants and predefined configurations.

This module verifies the structure and content of the domain constants used throughout
the Focus Guard system. These constants define the categorization of domains, applications,
and the mapping between user-friendly category names and internal enum values.

The constants tested here include:
- DOMAIN_CATEGORIES: Dictionary mapping user-friendly category names to lists of domains
- DOMAIN_WHITELIST: Set of always-allowed domains
- APPLICATION_DOMAINS: Dictionary mapping application types to executable names
- CATEGORY_TO_ENUM_MAPPING: Dictionary mapping user-friendly categories to enum values
- DEFAULT_CONFIG: Dictionary containing the default configuration

These tests ensure that the constants are properly structured and contain the expected
values, which is critical for the correct functioning of the domain classification
and blocking system.
"""

import unittest

from focus_guard.core.domain.constants import (
    DOMAIN_CATEGORIES,
    DOMAIN_WHITELIST,
    APPLICATION_DOMAINS,
    CATEGORY_TO_ENUM_MAPPING,
    DEFAULT_CONFIG,
)


class TestDomainConstants(unittest.TestCase):
    """Tests for domain constants and predefined configurations.
    
    This test class verifies that the domain constants are properly structured
    and contain the expected values. These constants are fundamental to the
    Focus Guard system as they define how domains and applications are categorized
    and which domains are always allowed.
    
    The constants form part of the hybrid domain classification system that uses
    both user-friendly string categories (in dictionaries) and type-safe enums
    internally, with a mapping layer connecting them.
    """

    def test_domain_categories_structure(self):
        """Test that domain categories are properly structured.
        
        This test verifies that DOMAIN_CATEGORIES is a dictionary with the expected
        category keys, and that each category contains a non-empty list of domains.
        The structure of this dictionary is critical for the domain classification
        system to work correctly.
        """
        self.assertIsInstance(DOMAIN_CATEGORIES, dict)
        
        # Check that expected categories exist
        expected_categories = [
            "work", "social", "entertainment", "shopping", 
            "news", "email", "development", "productivity", "education"
        ]
        for category in expected_categories:
            self.assertIn(category, DOMAIN_CATEGORIES)
            self.assertIsInstance(DOMAIN_CATEGORIES[category], list)
            self.assertTrue(len(DOMAIN_CATEGORIES[category]) > 0)
    
    def test_domain_categories_content(self):
        """Test that domain categories contain expected domains.
        
        This test verifies that specific domains are correctly assigned to their
        expected categories. It checks a sample of domains from each category to
        ensure they are properly categorized.
        
        The correct categorization of domains is essential for the blocking and
        reporting features of the Focus Guard system.
        """
        # Test a few specific domains in each category
        self.assertIn("github.com", DOMAIN_CATEGORIES["work"])
        self.assertIn("facebook.com", DOMAIN_CATEGORIES["social"])
        self.assertIn("youtube.com", DOMAIN_CATEGORIES["entertainment"])
        self.assertIn("amazon.com", DOMAIN_CATEGORIES["shopping"])
        self.assertIn("nytimes.com", DOMAIN_CATEGORIES["news"])
        self.assertIn("gmail.com", DOMAIN_CATEGORIES["email"])
        self.assertIn("stackoverflow.com", DOMAIN_CATEGORIES["development"])
        self.assertIn("notion.so", DOMAIN_CATEGORIES["productivity"])
        self.assertIn("khanacademy.org", DOMAIN_CATEGORIES["education"])
    
    def test_domain_whitelist(self):
        """Test that domain whitelist is properly defined.
        
        This test verifies that DOMAIN_WHITELIST is a non-empty set containing
        the expected always-allowed domains. The whitelist is critical for ensuring
        that essential system domains and services are never blocked.
        
        Domains in this whitelist are exempt from blocking rules regardless of
        their category or other classification.
        """
        self.assertIsInstance(DOMAIN_WHITELIST, set)
        self.assertTrue(len(DOMAIN_WHITELIST) > 0)
        
        # Check that some expected domains are in the whitelist
        expected_whitelist_domains = [
            "google.com", "microsoft.com", "apple.com", "cloudfront.net"
        ]
        for domain in expected_whitelist_domains:
            self.assertIn(domain, DOMAIN_WHITELIST)
    
    def test_application_domains(self):
        """Test that application domains are properly defined.
        
        This test verifies that APPLICATION_DOMAINS is a dictionary with the expected
        application categories, and that each category contains a non-empty list of
        executable names.
        
        The application domains mapping is used to categorize and potentially
        restrict applications based on their executable names, which complements
        the domain-based blocking system.
        """
        self.assertIsInstance(APPLICATION_DOMAINS, dict)
        
        # Check that expected application categories exist
        expected_app_categories = ["browsers", "development", "communication", "productivity"]
        for category in expected_app_categories:
            self.assertIn(category, APPLICATION_DOMAINS)
            self.assertIsInstance(APPLICATION_DOMAINS[category], list)
            self.assertTrue(len(APPLICATION_DOMAINS[category]) > 0)
        
        # Test a few specific applications in each category
        self.assertIn("chrome.exe", APPLICATION_DOMAINS["browsers"])
        self.assertIn("code.exe", APPLICATION_DOMAINS["development"])
        self.assertIn("teams.exe", APPLICATION_DOMAINS["communication"])
        self.assertIn("outlook.exe", APPLICATION_DOMAINS["productivity"])
    
    def test_category_to_enum_mapping(self):
        """Test that category to enum mapping is properly defined.
        
        This test verifies that CATEGORY_TO_ENUM_MAPPING is a dictionary that maps
        each user-friendly category name to its corresponding enum value string.
        
        This mapping is the bridge between the user-friendly string categories used
        in configuration and the type-safe enum values used internally by the code.
        It ensures that categories from configuration can be correctly translated
        to their internal representation.
        """
        self.assertIsInstance(CATEGORY_TO_ENUM_MAPPING, dict)
        
        # Check that all categories have a mapping
        for category in DOMAIN_CATEGORIES:
            self.assertIn(category, CATEGORY_TO_ENUM_MAPPING)
            self.assertIsInstance(CATEGORY_TO_ENUM_MAPPING[category], str)
        
        # Check some specific mappings
        self.assertEqual(CATEGORY_TO_ENUM_MAPPING["work"], "PRODUCTIVITY")
        self.assertEqual(CATEGORY_TO_ENUM_MAPPING["social"], "SOCIAL_MEDIA")
        self.assertEqual(CATEGORY_TO_ENUM_MAPPING["entertainment"], "ENTERTAINMENT")
    
    def test_default_config(self):
        """Test that default config is properly defined.
        
        This test verifies that DEFAULT_CONFIG is a dictionary containing the expected
        keys and that each key references the correct constant. The default configuration
        provides the initial settings for the Focus Guard system.
        
        The default configuration is used when no custom configuration is provided,
        ensuring that the system has a valid starting state.
        """
        self.assertIsInstance(DEFAULT_CONFIG, dict)
        
        # Check that expected keys exist
        expected_keys = ["domain_categories", "whitelist", "applications"]
        for key in expected_keys:
            self.assertIn(key, DEFAULT_CONFIG)
        
        # Check that the values are the expected constants
        self.assertEqual(DEFAULT_CONFIG["domain_categories"], DOMAIN_CATEGORIES)
        self.assertEqual(DEFAULT_CONFIG["whitelist"], DOMAIN_WHITELIST)
        self.assertEqual(DEFAULT_CONFIG["applications"], APPLICATION_DOMAINS)


if __name__ == "__main__":
    unittest.main()
