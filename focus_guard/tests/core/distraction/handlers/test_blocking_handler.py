"""
Tests for the blocking alert handler.

This module contains tests for the BlockingHandler class.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from focus_guard.core.distraction.models import DistractionAlert, AlertLevel
from focus_guard.core.distraction.handlers.blocking_handler import BlockingHandler


class TestBlockingHandler(unittest.TestCase):
    """Tests for the BlockingHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.browser_integration = MagicMock()
        self.handler = BlockingHandler(
            browser_integration=self.browser_integration,
            min_level=AlertLevel.CRITICAL,
            block_duration_seconds=300
        )
    
    def test_can_handle_sufficient_level_with_domain(self):
        """Test can_handle with sufficient alert level and domain."""
        # Create an alert with CRITICAL level and domain
        alert = DistractionAlert(
            rule_name="Test Rule",
            level=AlertLevel.CRITICAL,
            message="Test message",
            metadata={"domain": "example.com"},
            timestamp=datetime.now()
        )
        
        # Test can_handle
        self.assertTrue(self.handler.can_handle(alert))
    
    def test_can_handle_insufficient_level(self):
        """Test can_handle with insufficient alert level."""
        # Create an alert with WARNING level
        alert = DistractionAlert(
            rule_name="Test Rule",
            level=AlertLevel.WARNING,
            message="Test message",
            metadata={"domain": "example.com"},
            timestamp=datetime.now()
        )
        
        # Test can_handle
        self.assertFalse(self.handler.can_handle(alert))
    
    def test_can_handle_no_domain(self):
        """Test can_handle with no domain."""
        # Create an alert with CRITICAL level but no domain
        alert = DistractionAlert(
            rule_name="Test Rule",
            level=AlertLevel.CRITICAL,
            message="Test message",
            metadata={"key": "value"},
            timestamp=datetime.now()
        )
        
        # Test can_handle
        self.assertFalse(self.handler.can_handle(alert))
    
    @patch('focus_guard.core.domain.utils.extract_domain_from_url')
    def test_handle(self, mock_extract_domain):
        """Test handle method."""
        # Mock extract_domain_from_url
        mock_extract_domain.return_value = "example.com"
        
        # Create an alert
        alert = DistractionAlert(
            rule_name="Test Rule",
            level=AlertLevel.CRITICAL,
            message="Test message",
            metadata={"domain": "example.com"},
            timestamp=datetime.now()
        )
        
        # Mock browser integration
        self.browser_integration.get_active_tabs.return_value = {
            "all_tabs": [
                {"id": "1", "url": "https://example.com", "title": "Example"},
                {"id": "2", "url": "https://example.org", "title": "Another Example"}
            ]
        }
        
        # Mock extract_domain_from_url to return different domains based on URL
        def side_effect(url):
            if url == "https://example.com":
                return "example.com"
            else:
                return "example.org"
        mock_extract_domain.side_effect = side_effect
        
        # Handle the alert
        self.handler.handle(alert)
        
        # Verify domain was blocked
        self.browser_integration.block_domain.assert_called_once_with(
            "example.com",
            duration_seconds=300,
            reason="Distraction detected"
        )
        
        # Verify tabs were closed
        self.browser_integration.close_tab.assert_called_once_with("1")
    
    def test_check_and_unblock(self):
        """Test check_and_unblock method."""
        # Add a domain to blocked domains
        self.handler._blocked_domains.add("example.com")
        
        # Set block end time to the past
        self.handler._block_end_time = datetime.now() - timedelta(seconds=10)
        
        # Call check_and_unblock
        self.handler.check_and_unblock()
        
        # Verify domain was unblocked
        self.browser_integration.unblock_domain.assert_called_once_with("example.com")
        
        # Verify blocked domains were cleared
        self.assertEqual(len(self.handler._blocked_domains), 0)
        self.assertIsNone(self.handler._block_end_time)


if __name__ == "__main__":
    unittest.main()
