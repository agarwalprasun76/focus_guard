"""
Tests for the hierarchical classification system.

This file contains tests for both individual specialized classifiers 
and the integrated hierarchical classification system.
"""

import unittest
from unittest.mock import patch, MagicMock, ANY
from urllib.parse import urlparse

# Import the components we need to test
from core.domain_classifier.hierarchical_classifier import HierarchicalLinkClassifier
from core.domain_classifier.classifier_registry import ClassifierRegistry
from core.domain_classifier.base_classifier import ContentClassifier

# Import the specialized classifiers
from core.domain_classifier.classifiers.entertainment_classifier import EntertainmentClassifier
from core.domain_classifier.classifiers.publication_classifier import PublicationClassifier
from core.domain_classifier.classifiers.google_drive_classifier import GoogleDriveClassifier
from core.domain_classifier.classifiers.youtube_classifier import YouTubeClassifier
from core.domain_classifier.classifiers.keyword_classifier import KeywordClassifier


class TestSpecializedClassifiers(unittest.TestCase):
    """Test cases for individual specialized classifiers."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.entertainment_classifier = EntertainmentClassifier()
        self.publication_classifier = PublicationClassifier()
        self.google_drive_classifier = GoogleDriveClassifier()
        self.youtube_classifier = YouTubeClassifier()
        self.keyword_classifier = KeywordClassifier()
    
    def test_entertainment_classifier(self):
        """Test the entertainment classifier."""
        # Test URLs (excluding YouTube URLs as they're now handled by YouTubeClassifier)
        entertainment_urls = [
            "https://www.imdb.com/title/tt0111161/",  # Shawshank Redemption
            "https://www.netflix.com/title/80192098",  # Money Heist
            "https://www.twitch.tv/ninja",  # Twitch streamer
            "https://www.goodreads.com/book/show/3.Harry_Potter_and_the_Sorcerer_s_Stone"  # Book
        ]
        
        for url in entertainment_urls:
            domain = urlparse(url).netloc
            self.assertTrue(
                self.entertainment_classifier.can_classify(url, domain),
                f"Entertainment classifier should recognize {url}"
            )
            
            result = self.entertainment_classifier.classify(url, domain)
            self.assertEqual(
                result["classification"], 
                "distraction",
                f"Expected 'distraction' for {url} but got {result['classification']}"
            )
            self.assertGreaterEqual(
                result["confidence"], 
                0.8,
                f"Expected confidence >= 0.8 for {url} but got {result['confidence']}"
            )
        
        # Test non-entertainment URL
        non_entertainment_url = "https://www.nih.gov/research"
        domain = urlparse(non_entertainment_url).netloc
        self.assertFalse(
            self.entertainment_classifier.can_classify(non_entertainment_url, domain),
            f"Entertainment classifier should not recognize {non_entertainment_url}"
        )
    
    def test_publication_classifier(self):
        """Test the publication classifier."""
        # Test URLs
        publication_urls = [
            "https://arxiv.org/abs/2106.04554",  # arXiv paper
            "https://www.sciencedirect.com/science/article/pii/S0004370221000862",  # Journal article
            "https://www.nature.com/articles/s41586-021-03819-2",  # Nature article
            "https://research.google/pubs/pub41684/",  # Google research
            "https://web.stanford.edu/class/cs224n/readings/cs224n-2019-notes01-wordvecs1.pdf"  # PDF file
        ]
        
        for url in publication_urls:
            domain = urlparse(url).netloc
            self.assertTrue(
                self.publication_classifier.can_classify(url, domain),
                f"Publication classifier should recognize {url}"
            )
    
    @patch('core.domain_classifier.metadata.metadata_fetcher')
    def test_google_drive_classifier(self, mock_metadata_fetcher):
        """Test the Google Drive classifier."""
        # Setup mock
        mock_metadata_fetcher.fetch_metadata_for_google_drive = MagicMock(return_value={
            'mimeType': 'application/vnd.google-apps.document',
            'title': 'Work Document'
        })
        
        # Test URLs
        drive_urls = [
            "https://docs.google.com/document/d/1abc123def456/edit",  # Google Doc
            "https://drive.google.com/file/d/1abc123def456/view",  # Google Drive file
            "https://sheets.google.com/spreadsheets/d/1abc123def456/edit"  # Google Sheet
        ]
        
        for url in drive_urls:
            domain = urlparse(url).netloc
            self.assertTrue(
                self.google_drive_classifier.can_classify(url, domain),
                f"Google Drive classifier should recognize {url}"
            )
            
            result = self.google_drive_classifier.classify(url, domain)
            self.assertEqual(
                result["classification"], 
                "useful",
                f"Expected 'useful' for {url} but got {result['classification']}"
            )
    
    @patch('core.domain_classifier.metadata.metadata_fetcher')
    def test_youtube_classifier(self, mock_metadata_fetcher):
        """Test the YouTube classifier."""
        # Test URLs
        youtube_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Video
            "https://youtu.be/dQw4w9WgXcQ",  # Short URL
            "https://www.youtube.com/playlist?list=abc123",  # Playlist
            "https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw"  # Channel
        ]
        
        for url in youtube_urls:
            domain = urlparse(url).netloc
            self.assertTrue(
                self.youtube_classifier.can_classify(url, domain),
                f"YouTube classifier should recognize {url}"
            )
            
            # Test with educational content
            educational_metadata = {
                'title': 'Introduction to Python Programming',
                'description': 'Learn Python programming basics',
                'channel': 'Code Academy',
                'tags': ['programming', 'education', 'tutorial']
            }
            
            # Set up mock (for backward compatibility)
            mock_metadata_fetcher.fetch_metadata_for_youtube = MagicMock(return_value=educational_metadata)
            
            # Pass the metadata directly to the classify method
            result = self.youtube_classifier.classify(url, domain, educational_metadata)
            
            # Debug print
            print(f"Educational metadata: {educational_metadata}")
            print(f"Result: {result}")
            self.assertEqual(
                result["classification"],
                "useful",
                f"Expected 'useful' for educational video {url} but got {result['classification']}"
            )
            
            # Test with entertainment content
            entertainment_metadata = {
                'title': 'Funny Cat Videos Compilation',
                'description': 'Watch hilarious cat moments',
                'channel': 'Entertainment Central',
                'tags': ['funny', 'cats', 'entertainment']
            }
            
            mock_metadata_fetcher.fetch_metadata_for_youtube = MagicMock(return_value=entertainment_metadata)
            
            result = self.youtube_classifier.classify_link(url, domain, entertainment_metadata)
            self.assertEqual(
                result["classification"],
                "distraction",
                f"Expected 'distraction' for entertainment video {url} but got {result['classification']}"
            )
    
    def test_keyword_classifier(self):
        """Test the keyword classifier."""
        # The keyword classifier can classify any URL, so we'll test the classification results
        
        # URLs likely to be classified as useful
        useful_urls = [
            "https://www.coursera.org/learn/machine-learning",
            "https://github.com/tensorflow/tensorflow",
            "https://stackoverflow.com/questions/tagged/python",
            "https://docs.python.org/3/tutorial/index.html"
        ]
        
        for url in useful_urls:
            domain = urlparse(url).netloc
            result = self.keyword_classifier.classify(url, domain)
            self.assertEqual(
                result["classification"], 
                "useful",
                f"Expected 'useful' for {url} but got {result['classification']}"
            )
        
        # URLs likely to be classified as distraction
        distraction_urls = [
            "https://www.facebook.com/profile",
            "https://www.instagram.com/explore",
            "https://www.reddit.com/r/funny",
            "https://www.tiktok.com/trending"
        ]
        
        for url in distraction_urls:
            domain = urlparse(url).netloc
            result = self.keyword_classifier.classify(url, domain)
            self.assertEqual(
                result["classification"], 
                "distraction",
                f"Expected 'distraction' for {url} but got {result['classification']}"
            )


class TestHierarchicalClassifier(unittest.TestCase):
    """Test cases for the integrated hierarchical classification system."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a new registry and classifier for each test
        self.registry = ClassifierRegistry()
        self.classifier = HierarchicalLinkClassifier(registry=self.registry)
        
        # Create test classifiers with different priorities
        self.entertainment_classifier = EntertainmentClassifier()
        self.publication_classifier = PublicationClassifier()
        self.google_drive_classifier = GoogleDriveClassifier()
        self.youtube_classifier = YouTubeClassifier()
        self.keyword_classifier = KeywordClassifier()
        
        # Register the classifiers in priority order (highest first) to match main.py
        self.registry.register(self.google_drive_classifier)  # Priority 90
        self.registry.register(self.youtube_classifier)      # Priority 85
        self.registry.register(self.publication_classifier)  # Priority 80
        self.registry.register(self.entertainment_classifier)  # Priority 70
        self.registry.register(self.keyword_classifier)      # Priority 30
        
        # Set up mocks
        self.setup_mocks()
    
    def setup_mocks(self):
        """Set up mock objects for external dependencies."""
        # Patch the metadata_fetcher singleton used by both Google Drive and YouTube classifiers
        self.metadata_fetcher_patcher = patch('core.domain_classifier.metadata.metadata_fetcher')
        self.mock_metadata_fetcher = self.metadata_fetcher_patcher.start()
        self.addCleanup(self.metadata_fetcher_patcher.stop)
        
        # Set up Google Drive metadata mock
        self.mock_metadata_fetcher.fetch_metadata_for_google_drive = MagicMock(return_value={
            'mimeType': 'application/vnd.google-apps.document',
            'title': 'Work Document'
        })
        
        # Set up YouTube metadata mock
        self.mock_metadata_fetcher.fetch_metadata_for_youtube = MagicMock(return_value={
            'title': 'Introduction to Python',
            'channel': 'Code Academy',
            'description': 'Learn Python programming',
            'tags': ['programming', 'tutorial', 'education']
        })
        
        # Original publication classifier mock
        self.pub_patcher = patch('core.domain_classifier.classifiers.publication_classifier.original_publication_classifier')
        self.mock_pub_classifier = self.pub_patcher.start()
        self.addCleanup(self.pub_patcher.stop)
        
        # Set up publication classifier mock directly
        self.mock_pub_classifier.classify_link_for_focus_guard.return_value = {
            'classification': 'useful',
            'reason': 'Academic publication',
            'confidence': 0.85,
            'metadata': {}
        }
    
    def test_priority_order(self):
        """Test that classifiers are called in priority order."""
        # Create mock classifiers with known priorities
        mock_high = MagicMock(spec=ContentClassifier)
        mock_high.priority = 100
        mock_high.can_classify.return_value = False
        
        mock_medium = MagicMock(spec=ContentClassifier)
        mock_medium.priority = 50
        mock_medium.can_classify.return_value = False
        
        mock_low = MagicMock(spec=ContentClassifier)
        mock_low.priority = 10
        mock_low.can_classify.return_value = True
        mock_low.classify.return_value = {
            "classification": "neutral",
            "reason": "Test classifier",
            "confidence": 0.5,
            "metadata": {}
        }
        
        # Create a new registry with only these mocks
        test_registry = ClassifierRegistry()
        test_classifier = HierarchicalLinkClassifier(registry=test_registry)
        
        # Register in random order
        test_registry.register(mock_medium)
        test_registry.register(mock_low)
        test_registry.register(mock_high)
        
        # Classify a URL
        test_classifier.classify_link("https://example.com", "example.com")
        
        # Verify they were called in priority order
        mock_high.can_classify.assert_called_once()
        mock_medium.can_classify.assert_called_once()
        mock_low.can_classify.assert_called_once()
        
        # Only the low-priority classifier should be called to classify
        mock_high.classify.assert_not_called()
        mock_medium.classify.assert_not_called()
        mock_low.classify.assert_called_once()
    
    def test_entertainment_classification(self):
        """Test that entertainment URLs are classified correctly."""
        # IMDB URL should be classified by the entertainment classifier
        url = "https://www.imdb.com/title/tt0111161/"
        domain = "www.imdb.com"
        
        result = self.classifier.classify_link(url, domain)
        
        self.assertEqual(result["classification"], "distraction")
        self.assertGreaterEqual(result["confidence"], 0.8)
        self.assertEqual(result["metadata"]["classifier"], "EntertainmentClassifier")
    
    def test_publication_classification(self):
        """Test that publication URLs are classified correctly."""
        url = "https://arxiv.org/abs/2106.04554"
        domain = "arxiv.org"
        
        # Set up the mock to return a specific result
        pub_instance = self.mock_pub_classifier.get_instance.return_value
        pub_instance.classify_link_for_focus_guard.return_value = {
            'classification': 'useful',
            'reason': 'Academic paper on arXiv',
            'confidence': 0.9,
            'metadata': {}
        }
        
        result = self.classifier.classify_link(url, domain)
        
        self.assertEqual(result["classification"], "useful")
        self.assertGreaterEqual(result["confidence"], 0.7)
    
    def test_google_drive_classification(self):
        """Test that Google Drive URLs are classified correctly."""
        url = "https://docs.google.com/document/d/1abc123def456/edit"
        domain = "docs.google.com"
        
        result = self.classifier.classify_link(url, domain)
        
        self.assertEqual(result["classification"], "useful")
        self.assertEqual(result["metadata"]["classifier"], "GoogleDriveClassifier")
    
    def test_youtube_classification(self):
        """Test that YouTube URLs are classified correctly."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        domain = "www.youtube.com"
        
        # Debug print of classifiers and their priorities
        print("\nRegistered classifiers in order:")
        for c in self.registry.classifiers:
            print(f"  {c.__class__.__name__}: priority {c.priority}")
        
        result = self.classifier.classify_link(url, domain)
        print(f"\nYouTube URL classification result: {result}")
        
        # Should be classified by the YouTube classifier
        self.assertEqual(result["metadata"]["classifier"], "YouTubeClassifier")
    
    def test_keyword_fallback(self):
        """Test that the keyword classifier is used as a fallback."""
        url = "https://example.com/learn/python/course"
        domain = "example.com"
        
        result = self.classifier.classify_link(url, domain)
        
        # Should fall back to keyword classifier
        self.assertEqual(result["classification"], "useful")  # "learn" and "course" keywords
        self.assertEqual(result["metadata"]["classifier"], "KeywordClassifier")
    
    def test_confidence_threshold(self):
        """Test that results below confidence threshold are handled correctly."""
        # Create a mock classifier that returns low confidence
        mock_classifier = MagicMock(spec=ContentClassifier)
        mock_classifier.priority = 100
        mock_classifier.can_classify.return_value = True
        mock_classifier.classify.return_value = {
            "classification": "distraction",
            "reason": "Low confidence test",
            "confidence": 0.3,  # Below default threshold of 0.7
            "metadata": {}
        }
        
        # Create a new registry with only this mock and the keyword classifier
        test_registry = ClassifierRegistry()
        test_classifier = HierarchicalLinkClassifier(registry=test_registry)
        
        test_registry.register(mock_classifier)
        test_registry.register(self.keyword_classifier)  # Fallback
        
        # Classify a URL
        url = "https://stackoverflow.com/questions/tagged/python"  # Should be "useful" by keyword classifier
        domain = "stackoverflow.com"
        
        result = test_classifier.classify_link(url, domain)
        
        # The mock result should be rejected due to low confidence
        # and it should fall back to the keyword classifier
        self.assertEqual(result["classification"], "useful")
        self.assertEqual(result["metadata"]["classifier"], "KeywordClassifier")
        
        # Verify the mock was called but its result was rejected
        mock_classifier.can_classify.assert_called_once()
        mock_classifier.classify.assert_called_once()


class TestCompatibility(unittest.TestCase):
    """Test compatibility with the old link classifier."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Import the old classifier for comparison
        from core.domain_classifier.domain_classifier_old.link_classifier import link_classifier as old_classifier
        self.old_classifier = old_classifier
        
        # Get the new classifier
        from core.domain_classifier.hierarchical_classifier import link_classifier as new_classifier
        self.new_classifier = new_classifier
        
        # Set up mocks for consistent testing
        self.setup_mocks()
    
    def setup_mocks(self):
        """Set up mock objects for external dependencies."""
        # Similar to TestHierarchicalClassifier.setup_mocks
        pass  # Omitted for brevity, would mirror the setup in TestHierarchicalClassifier
    
    def test_basic_compatibility(self):
        """Test that the new classifier gives similar results to the old one for common cases."""
        # Test URLs
        test_urls = [
            # Social media (should be distraction)
            "https://www.facebook.com/profile",
            "https://www.twitter.com/user",
            
            # Productivity (should be useful)
            "https://www.github.com/repo",
            "https://stackoverflow.com/questions",
            
            # Entertainment (should be distraction)
            "https://www.youtube.com/watch",
            "https://www.netflix.com/title",
            
            # News/Information (could be neutral)
            "https://www.cnn.com/news",
            "https://www.bbc.com/news"
        ]
        
        for url in test_urls:
            domain = urlparse(url).netloc
            
            # Get classifications from both systems
            old_result = self.old_classifier.classify_link(url, domain)
            new_result = self.new_classifier.classify_link(url, domain)
            
            # Special handling for YouTube and Netflix - old and new classifiers may differ
            if 'youtube' in domain or 'netflix' in domain:
                continue  # Skip YouTube and Netflix URLs in compatibility tests
            
            # For this test, we only care about the classification, not confidence or reason
            # The new system should give the same classification for these common cases
            self.assertEqual(
                old_result["classification"],
                new_result["classification"],
                f"Classification mismatch for {url}: old={old_result['classification']}, new={new_result['classification']}"
            )


if __name__ == "__main__":
    unittest.main()
