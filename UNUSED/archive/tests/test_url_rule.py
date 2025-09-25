"""
Test the URL rule for distraction detection.
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestURLRule(unittest.TestCase):
    """Test the URL rule for distraction detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Import here to avoid circular imports
        from core.distraction_detector.url_rule import URLRule
        self.url_rule = URLRule()
        
    def test_browser_detection(self):
        """Test browser detection."""
        self.assertTrue(self.url_rule._is_browser('chrome.exe'))
        self.assertTrue(self.url_rule._is_browser('firefox.exe'))
        self.assertTrue(self.url_rule._is_browser('msedge.exe'))
        self.assertFalse(self.url_rule._is_browser('notepad.exe'))
        self.assertFalse(self.url_rule._is_browser('word.exe'))
        
    def test_url_extraction(self):
        """Test URL extraction from window title."""
        # Direct URL in title
        self.assertEqual(
            self.url_rule._extract_url_from_title('http://example.com - Chrome'),
            'http://example.com'
        )
        
        # Common browser title format
        self.assertEqual(
            self.url_rule._extract_url_from_title('Example Page - example.com - Chrome'),
            'http://example.com'
        )
        
        # No URL in title
        self.assertIsNone(self.url_rule._extract_url_from_title('New Tab - Chrome'))
        
    @patch('core.domain_classifier.domain_classifier.classify_domain')
    def test_check_productive_domain(self, mock_classify):
        """Test checking a productive domain."""
        # Mock classify_domain to return 'work' category
        mock_classify.return_value = 'work'
        
        active_window = {
            'app_name': 'chrome.exe',
            'window_title': 'Gmail - mail.google.com - Chrome'
        }
        
        # Check rule
        events = self.url_rule.check(active_window, [], {})
        
        # Should not detect any distractions
        self.assertEqual(len(events), 0)
        
    @patch('core.domain_classifier.domain_classifier.classify_domain')
    def test_check_distracting_domain(self, mock_classify):
        """Test checking a distracting domain."""
        # Mock classify_domain to return 'social' category
        mock_classify.return_value = 'social'
        
        active_window = {
            'app_name': 'chrome.exe',
            'window_title': 'Facebook - facebook.com - Chrome'
        }
        
        # Check rule
        events = self.url_rule.check(active_window, [], {})
        
        # Should detect a distraction
        self.assertEqual(len(events), 1)
        self.assertIn('Distracting website', events[0])
        self.assertIn('facebook.com', events[0])
        
class TestDistractorDetectorWithURLs(unittest.TestCase):
    """Test the distraction detector with URL-based detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Import here to avoid circular imports
        from core.distraction_detector.distraction_detector import DistractionDetector
        self.detector = DistractionDetector(
            allowed_apps=['code.exe', 'notepad.exe'],
            config={
                'productive_categories': ['work', 'education', 'productivity'],
                'distracting_categories': ['social', 'entertainment'],
                'domain_whitelist': ['example.com', 'github.com']
            }
        )
        
    @patch('core.domain_classifier.domain_classifier.classify_domain')
    def test_is_distracted_with_productive_domain(self, mock_classify):
        """Test is_distracted with a productive domain."""
        # Mock classify_domain to return 'work' category
        mock_classify.return_value = 'work'
        
        window_info = {
            'app_name': 'chrome.exe',
            'window_title': 'Gmail - mail.google.com - Chrome'
        }
        
        # Should not be distracted
        self.assertFalse(self.detector.is_distracted(window_info))
        
    @patch('core.domain_classifier.domain_classifier.classify_domain')
    def test_is_distracted_with_distracting_domain(self, mock_classify):
        """Test is_distracted with a distracting domain."""
        # Mock classify_domain to return 'social' category
        mock_classify.return_value = 'social'
        
        window_info = {
            'app_name': 'chrome.exe',
            'window_title': 'Facebook - facebook.com - Chrome'
        }
        
        # Should be distracted
        self.assertTrue(self.detector.is_distracted(window_info))
        
    def test_is_distracted_with_whitelisted_domain(self):
        """Test is_distracted with a whitelisted domain."""
        window_info = {
            'app_name': 'chrome.exe',
            'window_title': 'Example - example.com - Chrome'
        }
        
        # Should not be distracted (whitelisted)
        self.assertFalse(self.detector.is_distracted(window_info))
        
    def test_is_distracted_with_allowed_app(self):
        """Test is_distracted with an allowed app."""
        window_info = {
            'app_name': 'notepad.exe',
            'window_title': 'Untitled - Notepad'
        }
        
        # Should not be distracted (allowed app)
        self.assertFalse(self.detector.is_distracted(window_info))
        
    def test_is_distracted_with_disallowed_app(self):
        """Test is_distracted with a disallowed app."""
        window_info = {
            'app_name': 'steam.exe',
            'window_title': 'Steam'
        }
        
        # Should be distracted (not allowed)
        self.assertTrue(self.detector.is_distracted(window_info))
        
if __name__ == '__main__':
    unittest.main()
