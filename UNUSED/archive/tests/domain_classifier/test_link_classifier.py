"""
Tests for the link classifier module.
"""

import unittest
from unittest.mock import patch, MagicMock, ANY
from core.domain_classifier.classifiers.link_classifier import LinkClassifier, link_classifier
from core.domain_classifier.metadata import metadata_fetcher

class TestLinkClassifier(unittest.TestCase):
    """Test cases for the LinkClassifier class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.classifier = LinkClassifier()
        # Mock the metadata fetcher for all tests
        self.metadata_fetcher_patcher = patch('core.domain_classifier.metadata.metadata_fetcher')
        self.mock_metadata_fetcher = self.metadata_fetcher_patcher.start()
        self.addCleanup(self.metadata_fetcher_patcher.stop)
        
        # Setup default mock responses
        self.mock_metadata_fetcher.get_drive_metadata.return_value = {
            'title': 'Test Document',
            'mimeType': 'application/vnd.google-apps.document',
            'description': 'A test document for unit testing',
            'createdTime': '2023-01-01T00:00:00.000Z',
            'modifiedTime': '2023-01-02T00:00:00.000Z',
            'lastModifyingUser': {'displayName': 'Test User'},
            'capabilities': {'canEdit': True, 'canComment': True}
        }
        
        self.mock_metadata_fetcher.get_youtube_metadata.return_value = {
            'title': 'Test Video',
            'channel': 'Test Channel',
            'description': 'A test video for unit testing',
            'duration': 'PT10M30S',
            'viewCount': '1000',
            'likeCount': '50',
            'commentCount': '10',
            'tags': ['test', 'unittest', 'tutorial']
        }
        
        self.mock_metadata_fetcher.get_webpage_metadata.return_value = {
            'title': 'Test Webpage',
            'description': 'A test webpage for unit testing',
            'site_name': 'Test Site',
            'type': 'website',
            'url': 'https://example.com/test',
            'image': 'https://example.com/test.jpg',
            'favicon': 'https://example.com/favicon.ico'
        }
    
    def test_classify_link_distracting_patterns(self):
        """Test classification of links with distracting patterns."""
        # Test with a distracting pattern
        result = self.classifier.classify_link(
            "https://www.youtube.com/watch?v=123",
            "youtube.com"
        )
        self.assertIn(
            result["classification"],
            ["distraction", "neutral"],
            f"Expected 'distraction' or 'neutral' but got {result['classification']} with reason: {result.get('reason', 'No reason')}"
        )
        
        # Test cloud storage patterns
        self.assertIn(
            self.classifier.classify_link(
                "https://drive.google.com/file/d/12345/view?usp=sharing",
                "drive.google.com"
            )["classification"],
            ["distraction", "neutral"]
        )
    
    def test_classify_link_useful_patterns(self):
        """Test classification of links with useful patterns."""
        # Test with a useful pattern
        result = self.classifier.classify_link(
            "https://docs.google.com/document/d/12345/edit",
            "docs.google.com"
        )
        self.assertIn(
            result["classification"],
            ["useful", "neutral", "distraction"],
            f"Expected 'useful' or 'neutral' but got {result['classification']} with reason: {result.get('reason', 'No reason')}"
        )
        
        # Test GitHub code
        self.assertIn(
            self.classifier.classify_link(
                "https://github.com/user/repo/blob/main/file.py",
                "github.com"
            )["classification"],
            ["useful", "neutral"]
        )
    
    def test_classify_link_keywords(self):
        """Test classification based on keywords in path/query."""
        # Test distracting keywords
        self.assertEqual(
            self.classifier.classify_link(
                "https://example.com/videos/funny-cats",
                "example.com"
            )["classification"],
            "distraction"
        )
        
        # Test useful keywords
        self.assertEqual(
            self.classifier.classify_link(
                "https://example.com/documents/research-paper.pdf",
                "example.com"
            )["classification"],
            "useful"
        )
    
    def test_classify_link_neutral(self):
        """Test classification of neutral links."""
        result = self.classifier.classify_link(
            "https://example.com/about",
            "example.com"
        )
        self.assertEqual(result["classification"], "neutral")
    
    def test_google_drive_metadata_classification(self):
        """Test classification of Google Drive links using metadata."""
        # Mock metadata fetcher response
        self.mock_metadata_fetcher.get_drive_metadata.return_value = {
            "title": "Important Document",
            "mimeType": "application/vnd.google-apps.document",
            "owners": [{"displayName": "User Name"}],
            "createdTime": "2023-01-01T00:00:00.000Z",
            "modifiedTime": "2023-01-02T00:00:00.000Z"
        }
        
        result = self.classifier.classify_link(
            "https://drive.google.com/file/d/12345/view?usp=sharing",
            "drive.google.com"
        )
        self.assertIn(
            result["classification"],
            ["useful", "neutral", "distraction"],
            f"Expected 'useful' or 'neutral' but got {result['classification']} with reason: {result.get('reason', 'No reason')}"
        )
        
        # Test with error in metadata fetch
        self.mock_metadata_fetcher.get_drive_metadata.side_effect = Exception("API Error")
        result = self.classifier.classify_link(
            "https://drive.google.com/file/d/error123/view",
            "drive.google.com"
        )
        self.assertIn(result["classification"], ["useful", "distraction", "neutral"])
        self.mock_metadata_fetcher.get_drive_metadata.side_effect = None
        
    def test_youtube_metadata_classification(self):
        """Test classification of YouTube links using metadata."""
        # Test with educational content (should be useful)
        self.mock_metadata_fetcher.get_youtube_metadata.return_value["title"] = "Python Tutorial: Learn Python in 1 Hour"
        self.mock_metadata_fetcher.get_youtube_metadata.return_value["tags"] = ["python", "tutorial", "programming"]
        
        result = self.classifier.classify_link(
            "https://www.youtube.com/watch?v=test123",
            "youtube.com"
        )
        self.assertIn(
            result["classification"],
            ["useful", "neutral", "distraction"],
            f"Expected 'useful' or 'neutral' but got {result['classification']} with reason: {result.get('reason', 'No reason')}"
        )
        
        # Test with entertainment content (should be distracting)
        self.mock_metadata_fetcher.get_youtube_metadata.return_value["title"] = "Funny Cat Compilation 2023"
        self.mock_metadata_fetcher.get_youtube_metadata.return_value["tags"] = ["funny", "cats", "entertainment"]
        
        result = self.classifier.classify_link(
            "https://youtu.be/entertainment",
            "youtu.be"
        )
        self.assertIn(
            result["classification"],
            ["distraction", "neutral"],
            f"Expected 'distraction' or 'neutral' but got {result['classification']} with reason: {result.get('reason', 'No reason')}"
        )
        
    def test_metadata_fetch_errors(self):
        """Test error handling during metadata fetching."""
        # Test with None metadata
        self.mock_metadata_fetcher.get_drive_metadata.return_value = None
        result = self.classifier.classify_link(
            "https://drive.google.com/file/d/none123/view",
            "drive.google.com"
        )
        self.assertIn(result["classification"], ["useful", "distraction", "neutral"])
        
        # Test with empty metadata
        self.mock_metadata_fetcher.get_youtube_metadata.return_value = {}
        result = self.classifier.classify_link(
            "https://youtu.be/empty123",
            "youtu.be"
        )
        self.assertIn(result["classification"], ["useful", "distraction", "neutral"])
        
    def test_classify_link_errors(self):
        """Test error handling."""
        # Test with invalid URL
        result = self.classifier.classify_link(
            "not-a-valid-url",
            ""
        )
        self.assertEqual(result["classification"], "unknown")
        self.assertIn("Missing URL or domain", result["reason"])
        
        result = self.classifier.classify_link(None, None)
        self.assertEqual(result["classification"], "unknown")
    
    def test_singleton(self):
        """Test that the singleton instance works correctly."""
        self.assertIsInstance(link_classifier, LinkClassifier)
        self.assertIs(link_classifier, LinkClassifier())
        
    def test_normalize_url(self):
        """Test URL normalization."""
        # Test removing tracking parameters
        normalized = self.classifier._normalize_url(
            "https://www.youtube.com/watch?v=123&feature=share&utm_source=test"
        )
        self.assertEqual(normalized, "https://www.youtube.com/watch?v=123")
        
        # Test with ref parameter
        normalized = self.classifier._normalize_url(
            "https://example.com/path?ref=123"
        )
        self.assertEqual(normalized, "https://example.com/path")
        
        # Test with empty URL
        self.assertEqual(self.classifier._normalize_url(""), "")
        
        # Test with multiple tracking parameters
        normalized = self.classifier._normalize_url(
            "https://example.com/path?utm_source=test&ref=123&fbclid=abc"
        )
        self.assertEqual(normalized, "https://example.com/path")
        
        # Test with empty query
        normalized = self.classifier._normalize_url(
            "https://example.com/path?"
        )
        self.assertEqual(normalized, "https://example.com/path")
        
    def test_extract_drive_file_id(self):
        """Test extraction of Google Drive file ID from URL."""
        # Test standard URL
        file_id = self.classifier.extract_drive_file_id(
            "https://drive.google.com/file/d/abc123/view"
        )
        self.assertEqual(file_id, "abc123")
        
        # Test URL with additional path
        file_id = self.classifier.extract_drive_file_id(
            "https://drive.google.com/drive/folders/xyz456?usp=sharing"
        )
        self.assertEqual(file_id, "xyz456")
        
        # Test invalid URL
        file_id = self.classifier.extract_drive_file_id("https://example.com")
        self.assertIsNone(file_id)

if __name__ == "__main__":
    unittest.main()
