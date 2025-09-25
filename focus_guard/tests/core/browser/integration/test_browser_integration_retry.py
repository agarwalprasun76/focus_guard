"""
Tests for browser integration retry functionality.
"""
import pytest
import requests
import time
import importlib
from unittest.mock import patch, MagicMock, ANY, call, PropertyMock

# Import the module to patch the retry decorator
import focus_guard.core.browser.integration.browser_integration
from focus_guard.core.browser.integration.browser_integration import BrowserIntegration

# Import the retry decorator for testing
from focus_guard.core.utils.retry import retry


# Remove the mock_retry fixture as we'll test the actual retry behavior


@pytest.fixture
def mock_requests():
    """Fixture to mock requests.get for tab server status checks."""
    with patch('requests.get') as mock_get:
        yield mock_get


def test_check_tab_server_status_success(mock_requests):
    """Test successful tab server status check."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_requests.return_value = mock_response
    
    # Initialize browser integration
    bi = BrowserIntegration(auto_start=False)
    
    # Test
    result = bi._check_tab_server_status()
    
    # Assert
    assert result is True
    mock_requests.assert_called_once_with("http://localhost:5000/api/status", timeout=1.0)


def test_check_tab_server_status_retry_on_failure(mock_requests):
    """Test that tab server status check retries on failure."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    # Create instance
    bi = BrowserIntegration(auto_start=False)

    # Mock requests to fail all attempts (max 3 attempts with retry decorator)
    mock_requests.side_effect = [
        requests.RequestException("Connection error"),  # First attempt fails
        requests.RequestException("Connection error"),  # Second attempt fails
        requests.RequestException("Connection error"),  # Third attempt fails
    ]

    # Let the decorated function run with patched time.sleep for speed
    with patch('focus_guard.core.browser.integration.browser_integration.time.sleep', return_value=None), \
         patch('requests.get', mock_requests):

        # The decorated function should handle the retry logic
        result = bi._check_tab_server_status(timeout=0.1)

        # When all attempts fail, the function should return False
        assert result is False, "Expected _check_tab_server_status to return False when all retries fail"


def test_ensure_tab_server_running_already_running(mock_requests):
    """Test that ensure_tab_server_running returns True when server is already running."""
    # Setup mock response for status check
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_requests.return_value = mock_response
    
    # Initialize browser integration with mocked process manager
    with patch('focus_guard.core.browser.extension.process_manager.get_tab_server_process_manager') as mock_pm:
        mock_pm.return_value = MagicMock()
        bi = BrowserIntegration(auto_start=False)
        
        # Test
        result = bi._ensure_tab_server_running()
        
        # Assert
        assert result is True
        mock_pm.return_value.start.assert_not_called()


def test_ensure_tab_server_running_starts_server():
    """Test that ensure_tab_server_running starts the server if not running."""
    # Create a mock process manager
    mock_process_manager = MagicMock()
    mock_process_manager.start.return_value = True  # Simulate successful start

    # Create instance with auto_start=False
    bi = BrowserIntegration(auto_start=False)

    # Mock the process manager directly on the instance
    bi._process_manager = mock_process_manager

    # Create sequence for _check_tab_server_status.__wrapped__
    check_status_returns = [False, True]  # First False, then True

    # Mock the underlying method and time.sleep
    with patch.object(bi, '_check_tab_server_status', side_effect=check_status_returns) as mock_check_status, \
         patch('focus_guard.core.browser.integration.browser_integration.time.sleep', return_value=None):

        result = bi._ensure_tab_server_running()

        # Should start the server and eventually return True
        assert result is True, "Expected _ensure_tab_server_running to return True"
        mock_process_manager.start.assert_called_once()
        assert mock_check_status.call_count >= 2, "Expected _check_tab_server_status to be called at least twice"
