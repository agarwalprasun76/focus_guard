"""
Integration tests for the YouTube classifier with the core_v2 API.

This module contains tests for the integration of the YouTube classifier adapter
with the classifier-blocker API in the core_v2 architecture.
"""

import unittest
from unittest.mock import MagicMock, patch

from dataclasses import dataclass
from typing import Dict, Any, Optional

from core_v2.domain.models import Domain, Category, URL
from core_v2.classification.classifiers.youtube import YouTubeClassifierAdapter
from core_v2.api import ClassifierBlockerAPI

# Local definition for tab information (used in place of core_v2.blocking.models.TabInfo)
@dataclass
class TabInfo:
    """Information about a browser tab."""
    tab_id: int
    window_id: int
    url: Optional[str] = None
    domain: Optional[str] = None
    reason: Optional[str] = None


class TestYouTubeClassifierIntegration(unittest.TestCase):
    """Test cases for the YouTube classifier integration with the classifier-blocker API."""
    
    def setUp(self):
        """Set up the test environment."""
        # Initialize the classifier-blocker API with context-aware classification enabled
        self.api = ClassifierBlockerAPI(
            block_categories=[Category.SOCIAL_MEDIA, Category.ENTERTAINMENT, Category.DISTRACTIONS],
            context_aware=True
        )
    
    @patch('core_v2.classification.classifiers.youtube.YouTubeClassifierAdapter._get_legacy_classifier')
    def test_youtube_video_id_extraction(self, mock_get_legacy):
        """Test YouTube video ID extraction from different URL formats."""
        # Configure the mock to return a MagicMock
        mock_legacy_classifier = MagicMock()
        mock_get_legacy.return_value = mock_legacy_classifier
        
        # Import the utility function for extracting YouTube video IDs
        from core_v2.utils.youtube_utils import extract_youtube_id
        
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
            video_id = extract_youtube_id(test["url"])
            self.assertEqual(video_id, test["expected"], f"Failed for URL: {test['url']}")
    
    @patch('core_v2.classification.classifiers.youtube.YouTubeClassifierAdapter._get_legacy_classifier')
    def test_youtube_classification(self, mock_get_legacy):
        """Test YouTube classification based on metadata."""
        # Configure the mock to return a MagicMock
        mock_legacy_classifier = MagicMock()
        mock_get_legacy.return_value = mock_legacy_classifier
        
        # Create an instance of the adapter
        adapter = YouTubeClassifierAdapter()
        
        test_cases = [
            {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "metadata": {
                    "title": "Rick Astley - Never Gonna Give You Up",
                    "description": "Official music video for Rick Astley - Never Gonna Give You Up",
                    "channel": "Rick Astley",
                    "tags": ["Rick Astley", "music", "pop"]
                },
                "legacy_result": "entertainment",
                "expected_classification": Category.ENTERTAINMENT
            },
            {
                "url": "https://www.youtube.com/watch?v=_uQrJ0TkZlc",
                "metadata": {
                    "title": "Python Tutorial for Beginners - Learn Python in 5 Hours",
                    "description": "This Python tutorial for beginners shows how to get started with Python quickly.",
                    "channel": "Programming with Mosh",
                    "tags": ["python", "programming", "tutorial", "beginners"]
                },
                "legacy_result": "education",
                "expected_classification": Category.EDUCATION
            },
            {
                "url": "https://www.youtube.com/watch?v=abcdefghijk",
                "metadata": {
                    "title": "Quarterly Business Review - Q2 2023",
                    "description": "Company performance review for the second quarter of 2023",
                    "channel": "Company Internal",
                    "tags": ["business", "quarterly review", "finance"]
                },
                "legacy_result": "productivity",
                "expected_classification": Category.PRODUCTIVITY
            }
        ]
        
        for test in test_cases:
            # Configure the mock legacy classifier to return the expected legacy result
            mock_legacy_classifier.classify_youtube_url.return_value = test["legacy_result"]
            
            # Create a domain from the URL
            domain = Domain("youtube.com")
            
            # Create a context with the metadata
            context = {
                "url": test["url"],
                "metadata": test["metadata"]
            }
            
            # Classify with context
            category = adapter.classify_with_context(domain, context)
            
            # Verify the classification
            self.assertEqual(category, test["expected_classification"], 
                            f"Failed for video: {test['metadata']['title']}")
            
            # Verify that the legacy classifier was called with the correct URL
            mock_legacy_classifier.classify_youtube_url.assert_called_with(test["url"])
    
    @patch('core_v2.classification.classifiers.youtube.YouTubeClassifierAdapter._get_legacy_classifier')
    def test_classifier_blocker_api_integration(self, mock_get_legacy):
        """Test the integration of YouTube classifier with the classifier-blocker API."""
        # Configure the mock to return a MagicMock
        mock_legacy_classifier = MagicMock()
        mock_get_legacy.return_value = mock_legacy_classifier
        
        test_cases = [
            {
                "tab_info": TabInfo(
                    url=URL("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
                    domain=Domain("youtube.com"),
                    title="Rick Astley - Never Gonna Give You Up",
                    context={
                        "title": "Rick Astley - Never Gonna Give You Up",
                        "description": "Official music video for Rick Astley",
                        "channel": "Rick Astley",
                        "tags": ["Rick Astley", "music", "pop"]
                    }
                ),
                "legacy_result": "entertainment",
                "expected_block": True,
                "expected_reason": "blocked_category:entertainment"
            },
            {
                "tab_info": TabInfo(
                    url=URL("https://www.youtube.com/watch?v=_uQrJ0TkZlc"),
                    domain=Domain("youtube.com"),
                    title="Python Tutorial for Beginners",
                    context={
                        "title": "Python Tutorial for Beginners - Learn Python in 5 Hours",
                        "description": "This Python tutorial for beginners shows how to get started with Python quickly.",
                        "channel": "Programming with Mosh",
                        "tags": ["python", "programming", "tutorial", "beginners"]
                    }
                ),
                "legacy_result": "education",
                "expected_block": False,
                "expected_reason": "allowed_category:education"
            }
        ]
        
        for test in test_cases:
            # Configure the mock legacy classifier to return the expected legacy result
            mock_legacy_classifier.classify_youtube_url.return_value = test["legacy_result"]
            
            # Use the classifier-blocker API
            should_block, reason = self.api.should_block_tab(test["tab_info"])
            
            # Verify the blocking decision
            self.assertEqual(should_block, test["expected_block"], 
                            f"Failed block decision for {test['tab_info'].domain.value}")
            
            # Verify the reason
            self.assertEqual(reason, test["expected_reason"], 
                            f"Failed reason for {test['tab_info'].domain.value}")


if __name__ == "__main__":
    unittest.main()
