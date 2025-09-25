"""Tests for the browser detector adapter."""

import pytest
from unittest.mock import patch, MagicMock
from focus_guard.core.browser.adapters.browser_detector import DefaultBrowserDetector
from focus_guard.core.browser.models.browser import Browser, BrowserType

@pytest.fixture
def mock_psutil():
    """Fixture to mock psutil for browser detection tests."""
    with patch('psutil.process_iter') as mock_process_iter:
        yield mock_process_iter

@pytest.fixture
def browser_detector():
    """Fixture that provides a DefaultBrowserDetector instance."""
    return DefaultBrowserDetector(cache_ttl=0)  # Disable caching for tests

def test_get_active_browsers_no_browsers(browser_detector, mock_psutil):
    """Test get_active_browsers when no browsers are running."""
    mock_psutil.return_value = []
    browsers = browser_detector.get_active_browsers()
    assert isinstance(browsers, list)
    assert len(browsers) == 0

def test_get_active_browsers_with_browsers(browser_detector, mock_psutil):
    """Test get_active_browsers with running browsers."""
    # Create mock processes
    chrome_proc = MagicMock()
    chrome_proc.info = {'pid': 1234, 'name': 'chrome.exe'}
    
    firefox_proc = MagicMock()
    firefox_proc.info = {'pid': 5678, 'name': 'firefox.exe'}
    
    mock_psutil.return_value = [chrome_proc, firefox_proc]
    
    with patch('focus_guard.core.browser.adapters.browser_detector.BrowserType.from_name') as mock_from_name:
        mock_from_name.return_value = BrowserType.CHROME
        browsers = browser_detector.get_active_browsers()
        
        assert len(browsers) == 2
        assert all(isinstance(b, Browser) for b in browsers)
        assert mock_from_name.call_count == 2

def test_get_active_browser_window(browser_detector, mock_psutil):
    """Test get_active_browser_window with an active browser."""
    # Create a mock browser process
    chrome_proc = MagicMock()
    chrome_proc.info = {'pid': 1234, 'name': 'chrome.exe'}
    mock_psutil.return_value = [chrome_proc]
    
    with patch('focus_guard.core.browser.adapters.browser_detector.BrowserType.from_name') as mock_from_name:
        mock_from_name.return_value = BrowserType.CHROME
        browser = browser_detector.get_active_browser_window()
        
        # Since we can't easily test window focus, this should return None
        # unless we mock the window focus detection
        assert browser is None

def test_cache_behavior(browser_detector, mock_psutil):
    """Test that the browser detector respects the cache TTL."""
    # Create a detector with a non-zero TTL
    detector = DefaultBrowserDetector(cache_ttl=60)  # 60 second TTL
    
    # First call - should call psutil
    mock_psutil.return_value = []
    detector.get_active_browsers()
    assert mock_psutil.call_count == 1
    
    # Second call - should use cache
    detector.get_active_browsers()
    assert mock_psutil.call_count == 1  # No additional call
    
    # Force cache expiration
    detector._last_update_time = 0
    detector.get_active_browsers()
    assert mock_psutil.call_count == 2  # Called again

def test_psutil_import_error(browser_detector):
    """Test behavior when psutil import fails."""
    with patch.dict('sys.modules', {'psutil': None}):
        browsers = browser_detector.get_active_browsers()
        assert browsers == []
