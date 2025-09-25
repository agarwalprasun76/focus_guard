"""
Unit tests for the BrowserDetector class.

This module contains tests for the BrowserDetector class in core_v2.browser.adapter.
"""

import unittest
import time
from unittest.mock import patch, MagicMock
import pytest

from core_v2.browser.adapter import BrowserDetector
from core_v2.browser.models.browser import Browser, BrowserType


class TestBrowserDetector:
    """Test cases for the BrowserDetector class."""

    @pytest.fixture
    def browser_detector(self):
        """Create a BrowserDetector instance for testing."""
        return BrowserDetector()

    @pytest.fixture
    def mock_browser_data(self):
        """Create mock browser data for testing."""
        return {
            "chrome-12345": Browser(
                id="chrome-12345",
                type=BrowserType.CHROME,
                name="chrome",
                process_id=12345,
                window_id=1,
                window_title="Chrome Window",
                metadata={"is_active": True}
            ),
            "firefox-67890": Browser(
                id="firefox-67890",
                type=BrowserType.FIREFOX,
                name="firefox",
                process_id=67890,
                window_id=2,
                window_title="Firefox Window",
                metadata={"is_active": False}
            ),
            "edge-54321": Browser(
                id="edge-54321",
                type=BrowserType.EDGE,
                name="msedge",
                process_id=54321,
                window_id=3,
                window_title="Edge Window",
                metadata={"is_active": False}
            )
        }

    def test_get_active_browsers_empty(self, browser_detector):
        """Test get_active_browsers when no browsers are detected."""
        # Patch the _update_browser_data method to do nothing
        with patch.object(BrowserDetector, '_update_browser_data'):
            # Ensure the browser detector has no browsers
            browser_detector._browsers = {}
            
            # Call the method
            browsers = browser_detector.get_active_browsers()
            
            # Verify the result
            assert isinstance(browsers, list)
            assert len(browsers) == 0

    def test_get_active_browsers_with_data(self, browser_detector, mock_browser_data):
        """Test get_active_browsers when browsers are detected."""
        # Patch the _update_browser_data method to do nothing
        with patch.object(BrowserDetector, '_update_browser_data'):
            # Set mock browser data
            browser_detector._browsers = mock_browser_data
            
            # Call the method
            browsers = browser_detector.get_active_browsers()
            
            # Verify the result
            assert isinstance(browsers, list)
            assert len(browsers) == 3
            
            # Verify browser types
            browser_types = [b.type for b in browsers]
            assert BrowserType.CHROME in browser_types
            assert BrowserType.FIREFOX in browser_types
            assert BrowserType.EDGE in browser_types

    def test_get_active_browser_window_none(self, browser_detector):
        """Test get_active_browser_window when no active browser is found."""
        # Patch the _update_browser_data method to do nothing
        with patch.object(BrowserDetector, '_update_browser_data'):
            # Set mock browser data with no active browsers
            browser_detector._browsers = {
                "chrome-12345": Browser(
                    id="chrome-12345",
                    type=BrowserType.CHROME,
                    name="chrome",
                    process_id=12345,
                    metadata={"is_active": False}
                )
            }
            
            # Call the method
            active_browser = browser_detector.get_active_browser_window()
            
            # Verify the result
            assert active_browser is None

    def test_get_active_browser_window_found(self, browser_detector, mock_browser_data):
        """Test get_active_browser_window when an active browser is found."""
        # Patch the _update_browser_data method to do nothing
        with patch.object(BrowserDetector, '_update_browser_data'):
            # Set mock browser data
            browser_detector._browsers = mock_browser_data
            
            # Call the method
            active_browser = browser_detector.get_active_browser_window()
            
            # Verify the result
            assert active_browser is not None
            assert active_browser.id == "chrome-12345"
            assert active_browser.type == BrowserType.CHROME
            assert active_browser.metadata.get("is_active") is True

    def test_update_browser_data_cache_hit(self, browser_detector, mock_browser_data):
        """Test _update_browser_data when cache is still valid."""
        # Set up the browser detector with mock data and a recent update time
        browser_detector._browsers = mock_browser_data
        browser_detector._last_update_time = time.time()  # Just updated
        
        # Mock psutil to ensure it's not called
        with patch('psutil.process_iter') as mock_process_iter:
            # Call the method
            browser_detector._update_browser_data()
            
            # Verify that psutil was not called (cache hit)
            mock_process_iter.assert_not_called()
            
            # Verify that the browser data is unchanged
            assert browser_detector._browsers == mock_browser_data

    @patch('psutil.process_iter')
    def test_update_browser_data_cache_miss(self, mock_process_iter, browser_detector):
        """Test _update_browser_data when cache is expired."""
        # Set up the browser detector with an expired cache
        browser_detector._last_update_time = 0  # Long time ago
        
        # Mock process data for Chrome
        mock_chrome = MagicMock()
        mock_chrome.info = {'name': 'chrome', 'pid': 12345}
        
        # Set up the mock to return our process
        mock_process_iter.return_value = [mock_chrome]
        
        # Call the method
        browser_detector._update_browser_data()
        
        # Verify that psutil was called (cache miss)
        mock_process_iter.assert_called_once()
        
        # Verify that the browser data was updated
        assert len(browser_detector._browsers) == 1
        assert list(browser_detector._browsers.values())[0].name == "chrome"
        assert list(browser_detector._browsers.values())[0].process_id == 12345

    @patch('psutil.process_iter')
    def test_update_browser_data_import_error(self, mock_process_iter, browser_detector):
        """Test _update_browser_data when psutil import fails."""
        # Set up the browser detector with an expired cache
        browser_detector._last_update_time = 0  # Long time ago
        
        # Make psutil.process_iter raise ImportError
        mock_process_iter.side_effect = ImportError("psutil not available")
        
        # Call the method (should not raise exception)
        browser_detector._update_browser_data()
        
        # Verify that the browser data is empty
        assert browser_detector._browsers == {}

    @patch('psutil.process_iter')
    def test_update_browser_data_multiple_browsers(self, mock_process_iter, browser_detector):
        """Test _update_browser_data with multiple browser processes."""
        # Set up the browser detector with an expired cache
        browser_detector._last_update_time = 0  # Long time ago
        
        # Mock process data for multiple browsers
        mock_chrome = MagicMock()
        mock_chrome.info = {'name': 'chrome', 'pid': 12345}
        
        mock_firefox = MagicMock()
        mock_firefox.info = {'name': 'firefox', 'pid': 67890}
        
        mock_edge = MagicMock()
        mock_edge.info = {'name': 'msedge', 'pid': 54321}
        
        mock_other = MagicMock()
        mock_other.info = {'name': 'notepad', 'pid': 11111}
        
        # Set up the mock to return our processes
        mock_process_iter.return_value = [mock_chrome, mock_firefox, mock_edge, mock_other]
        
        # Call the method
        browser_detector._update_browser_data()
        
        # Verify that psutil was called
        mock_process_iter.assert_called_once()
        
        # Verify that only browser processes were detected (not notepad)
        assert len(browser_detector._browsers) == 3
        
        # Get browser types
        browser_types = [b.type for b in browser_detector._browsers.values()]
        
        # Verify browser types
        assert BrowserType.CHROME in browser_types
        assert BrowserType.FIREFOX in browser_types
        assert BrowserType.EDGE in browser_types


if __name__ == "__main__":
    pytest.main(["-v", "test_browser_detector.py"])
