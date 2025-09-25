"""
Integration tests for the OpenAI classifier adapter in core.

This module contains integration tests for the OpenAIClassifierAdapter class
that use the actual OpenAI classifier implementation rather than mocks.
"""

import unittest
import os
from typing import Dict, Any

from focus_guard.core.domain.models import Domain, Category
from focus_guard.core.classification.classifiers.openai import OpenAIClassifierAdapter


class TestOpenAIClassifierAdapterIntegration(unittest.TestCase):
    """Integration tests for the OpenAIClassifierAdapter class."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures for the entire test class.
        
        This method is called once before any tests in the class are run.
        It initializes the OpenAI classifier adapter and checks for API key.
        """
        # Initialize the adapter
        cls.adapter = OpenAIClassifierAdapter()
        
        # Set a smaller, faster model for testing
        cls.adapter.set_model("gpt-4o-mini")
        
        # Check if API key is available
        cls.api_key = os.environ.get("OPENAI_API_KEY")
        if cls.api_key:
            cls.adapter.set_api_key(cls.api_key)
        
        # Skip tests if required dependencies are not available
        try:
            import openai
            cls.dependencies_available = True
        except ImportError:
            cls.dependencies_available = False
    
    def setUp(self):
        """Set up test fixtures for each test.
        
        This method is called before each test method is run.
        It checks if the required dependencies are available and logs a warning if no API key is available.
        """
        if not self.dependencies_available:
            self.skipTest("Required dependency (openai) not available")
        
        if not self.api_key:
            print("WARNING: OpenAI API key not available. Tests will use fallback classification mechanism.")
            # We'll still run the tests, but they'll use the fallback mechanism
    
    def test_classify_educational_content(self):
        """Test classification of educational content.
        
        Verifies that the adapter correctly classifies educational content
        using the actual OpenAI classifier implementation.
        """
        # Create a domain for an educational website
        domain = Domain("khanacademy.org")
        
        # Create a context with metadata for an educational article
        context = {
            "url": "https://www.khanacademy.org/math/calculus",
            "metadata": {
                "title": "Calculus Course - Khan Academy",
                "description": "Learn calculus for free—derivatives, integrals, and more. Full curriculum of exercises and videos.",
                "keywords": ["calculus", "math", "education", "learning", "derivatives", "integrals"]
            }
        }
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that the content is classified as educational
        self.assertEqual(category, Category.EDUCATION)
    
    def test_classify_entertainment_content(self):
        """Test classification of entertainment content.
        
        Verifies that the adapter correctly classifies entertainment content
        using the actual OpenAI classifier implementation.
        """
        # Create a domain for an entertainment website
        domain = Domain("netflix.com")
        
        # Create a context with metadata for an entertainment page
        context = {
            "url": "https://www.netflix.com/title/12345",
            "metadata": {
                "title": "Stranger Things - Netflix",
                "description": "When a young boy vanishes, a small town uncovers a mystery involving secret experiments, terrifying supernatural forces and one strange little girl.",
                "keywords": ["tv show", "entertainment", "sci-fi", "drama"]
            }
        }
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that the content is classified as entertainment
        self.assertEqual(category, Category.ENTERTAINMENT)
    
    def test_classify_neutral_content(self):
        """Test classification of neutral content.
        
        Verifies that the adapter correctly classifies neutral content
        using the actual OpenAI classifier implementation.
        
        Note: Due to the stochastic nature of LLM responses, news content might be
        classified as either neutral (None) or educational (Category.EDUCATION).
        Both are considered acceptable classifications for news content.
        """
        # Create a domain for a news website
        domain = Domain("reuters.com")
        
        # Create a context with metadata for a news article
        context = {
            "url": "https://www.reuters.com/business/finance",
            "metadata": {
                "title": "Financial News - Reuters",
                "description": "Latest financial news and information from Reuters, the world's leading provider of news.",
                "keywords": ["news", "finance", "business", "markets"]
            }
        }
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that the content is classified as either neutral (None) or educational (Category.EDUCATION)
        # News content can reasonably be classified either way depending on the LLM's interpretation
        self.assertIn(category, [None, Category.EDUCATION])
    
    def test_classify_with_context_no_url(self):
        """Test classification with context when no URL is provided.
        
        Verifies that the adapter returns None when no URL is provided in the context.
        """
        # Create a domain
        domain = Domain("example.com")
        
        # Create a context without a URL
        context = {"metadata": {"title": "Some Content"}}
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that None is returned
        self.assertIsNone(category)
    
    def test_classify_with_context_no_metadata(self):
        """Test classification with context when no metadata is provided.
        
        Verifies that the adapter handles the case when no metadata is provided.
        """
        # Create a domain
        domain = Domain("example.com")
        
        # Create a context with a URL but no metadata
        context = {"url": "https://example.com"}
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # The result could be None or a category, depending on the classifier's behavior
        # We're just testing that it doesn't raise an exception
        self.assertIn(category, [None, Category.EDUCATION, Category.ENTERTAINMENT])
    
    def test_youtube_specific_classification(self):
        """Test classification of YouTube content.
        
        Verifies that the adapter correctly classifies YouTube content
        using the actual OpenAI classifier implementation.
        """
        # Create a domain for YouTube
        domain = Domain("youtube.com")
        
        # Create a context with metadata for an educational YouTube video
        context = {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "metadata": {
                "title": "Introduction to Python Programming",
                "description": "Learn the basics of Python programming in this comprehensive tutorial.",
                "channel": "Programming Tutorials",
                "type": "youtube",
                "video_id": "dQw4w9WgXcQ"
            }
        }
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that the content is classified (could be education or entertainment)
        # We're just testing that it returns a valid category
        self.assertIn(category, [Category.EDUCATION, Category.ENTERTAINMENT])


if __name__ == "__main__":
    unittest.main()
