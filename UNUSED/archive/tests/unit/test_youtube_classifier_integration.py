#!/usr/bin/env python
"""
Unit tests for the YouTube classifier integration with the classifier-blocker API.
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the classifier-blocker API and YouTube classifier
from core.integrations.classifier_blocker_api import ClassifierBlockerAPI, TabInfo
from core.domain_classifier.classifiers.youtube_classifier import youtube_classifier

class TestYouTubeClassifierIntegration(unittest.TestCase):
    """Test cases for the YouTube classifier integration with the classifier-blocker API."""
    
    def setUp(self):
        """Set up the test environment."""
        # Initialize the classifier-blocker API with context-aware classification enabled
        self.api = ClassifierBlockerAPI(
            block_categories=["social", "entertainment", "distraction"],
            context_aware=True
        )
    
    def test_youtube_video_id_extraction(self):
        """Test YouTube video ID extraction from different URL formats."""
        test_cases = [
            {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "expected": "dQw4w9WgXcQ"
            },
            {
                "url": "https://youtu.be/dQw4w9WgXcQ",
                "expected": "dQw4w9WgXcQ"
            },
            {
                "url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
                "expected": "dQw4w9WgXcQ"
            },
            {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
                "expected": "dQw4w9WgXcQ"
            },
            {
                "url": "https://www.example.com",
                "expected": None
            }
        ]
        
        for test in test_cases:
            # Use the YouTube classifier's utility function
            from core.domain_classifier.utils import extract_youtube_id
            video_id = extract_youtube_id(test["url"])
            self.assertEqual(video_id, test["expected"], f"Failed for URL: {test['url']}")
    
    def test_youtube_classification(self):
        """Test YouTube classification based on metadata."""
        test_cases = [
            {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "metadata": {
                    "title": "Rick Astley - Never Gonna Give You Up",
                    "description": "Official music video for Rick Astley - Never Gonna Give You Up",
                    "channel": "Rick Astley",
                    "tags": ["Rick Astley", "music", "pop"]
                },
                "expected_classification": "distraction"
            },
            {
                "url": "https://www.youtube.com/watch?v=_uQrJ0TkZlc",
                "metadata": {
                    "title": "Python Tutorial for Beginners - Learn Python in 5 Hours",
                    "description": "This Python tutorial for beginners shows how to get started with Python quickly.",
                    "channel": "Programming with Mosh",
                    "tags": ["python", "programming", "tutorial", "beginners"]
                },
                "expected_classification": "useful"
            },
            {
                "url": "https://www.youtube.com/watch?v=abcdefghijk",
                "metadata": {
                    "title": "Quarterly Business Review - Q2 2023",
                    "description": "Company performance review for the second quarter of 2023",
                    "channel": "Company Internal",
                    "tags": ["business", "quarterly review", "finance"]
                },
                "expected_classification": "useful"
            }
        ]
        
        for test in test_cases:
            # Use the YouTube classifier directly with rule-based method to avoid metadata fetching
            # This ensures we use the provided metadata directly
            result = youtube_classifier._classify_with_rules(
                test["url"], 
                "youtube.com", 
                test["metadata"]
            )
            self.assertEqual(
                result["classification"], 
                test["expected_classification"], 
                f"Failed for video: {test['metadata']['title']}"
            )
    
    def test_classifier_blocker_api_integration(self):
        """Test the integration of YouTube classifier with the classifier-blocker API."""
        test_cases = [
            {
                "tab_info": TabInfo(
                    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    domain="youtube.com",
                    title="Rick Astley - Never Gonna Give You Up",
                    context={
                        "title": "Rick Astley - Never Gonna Give You Up",
                        "description": "Official music video for Rick Astley",
                        "channel": "Rick Astley",
                        "tags": ["Rick Astley", "music", "pop"]
                    }
                ),
                "expected_block": True,
                "expected_reason": "blocked_category:entertainment"
            },
            {
                "tab_info": TabInfo(
                    url="https://www.youtube.com/watch?v=_uQrJ0TkZlc",
                    domain="youtube.com",
                    title="Python Tutorial for Beginners",
                    context={
                        "title": "Python Tutorial for Beginners - Learn Python in 5 Hours",
                        "description": "This Python tutorial for beginners shows how to get started with Python quickly.",
                        "channel": "Programming with Mosh",
                        "tags": ["python", "programming", "tutorial", "beginners"]
                    }
                ),
                "expected_block": False,
                "expected_reason": "allowed_category:education"
            },
            {
                "tab_info": TabInfo(
                    url="https://www.facebook.com",
                    domain="facebook.com",
                    title="Facebook"
                ),
                "expected_block": False,
                "expected_reason": "excluded"
            }
        ]
        
        # Import the domain classifier and logger for debugging
        from core.domain_classifier.domain_classifier import classify_domain, _domain_cache
        from core.logger.logger import get_logger
        logger = get_logger("test_youtube")
        
        # Debug the domain cache
        logger.info(f"Domain cache entries: {len(_domain_cache)}")
        if 'facebook.com' in _domain_cache:
            logger.info(f"facebook.com is in domain cache with category: {_domain_cache['facebook.com']}")
        else:
            logger.info("facebook.com is NOT in domain cache!")
        
        # Debug social category domains
        from core.domain_classifier.domain_config import domain_config
        social_domains = domain_config['categories'].get('social', [])
        logger.info(f"Social domains in config: {social_domains}")
        
        for test in test_cases:
            # Debug domain classification directly
            domain = test["tab_info"].domain
            category = classify_domain(domain)
            logger.info(f"Direct domain classification for {domain}: {category}")
            
            # Use the classifier-blocker API
            should_block, reason = self.api.should_block_tab(test["tab_info"])
            logger.info(f"Block decision for {domain}: {should_block}, reason: {reason}")
            
            self.assertEqual(should_block, test["expected_block"], 
                            f"Failed block decision for {test['tab_info'].url}")
            self.assertTrue(test["expected_reason"] in reason, 
                          f"Failed reason for {test['tab_info'].url}: expected '{test['expected_reason']}' in '{reason}'")



if __name__ == "__main__":
    unittest.main()
