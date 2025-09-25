"""Tests for the extension manager adapter."""

import os
import pytest
from unittest.mock import patch, MagicMock
from focus_guard.core.browser.adapters.extension_manager import DefaultExtensionManager
from focus_guard.core.browser.models.browser import BrowserType

@pytest.fixture
def extension_manager():
    """Fixture that provides a DefaultExtensionManager instance."""
    return DefaultExtensionManager()

@pytest.fixture
def mock_os_path_exists():
    """Fixture to mock os.path.exists function."""
    with patch('os.path.exists') as mock_exists:
        yield mock_exists

@pytest.fixture
def mock_os_makedirs():
    """Fixture to mock os.makedirs."""
    with patch('os.makedirs') as mock_makedirs:
        yield mock_makedirs

@pytest.fixture
def mock_open():
    """Fixture to mock the builtin open function."""
    with patch('builtins.open') as mock_open:
        yield mock_open

def test_is_extension_installed_cached(extension_manager):
    """Test checking if extension is installed (cached)."""
    # Set up cached value
    extension_manager._installed_extensions[BrowserType.CHROME] = True
    
    # Should return cached value without checking filesystem
    with patch('os.path.exists') as mock_exists:
        assert extension_manager.is_extension_installed(BrowserType.CHROME) is True
        mock_exists.assert_not_called()

def test_is_extension_installed_not_cached(extension_manager, mock_os_path_exists):
    """Test checking if extension is installed (not cached)."""
    # Mock the extension path and existence
    with patch.object(extension_manager, '_get_extension_path') as mock_get_path:
        mock_get_path.return_value = "C:\\path\\to\\extension"
        mock_os_path_exists.return_value = True
        
        # First call should check filesystem
        result = extension_manager.is_extension_installed(BrowserType.CHROME)
        
        assert result is True
        mock_get_path.assert_called_once_with(BrowserType.CHROME)
        mock_os_path_exists.assert_called_once_with("C:\\path\\to\\extension")
        
        # Should be cached now
        assert extension_manager._installed_extensions[BrowserType.CHROME] is True

def test_install_extension_success(extension_manager, mock_os_makedirs, mock_open):
    """Test successfully installing an extension."""
    # Mock the extension path
    with patch.object(extension_manager, '_get_extension_path') as mock_get_path:
        mock_get_path.return_value = "/path/to/extension"
        
        # Mock the file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Install the extension
        result = extension_manager.install_extension(BrowserType.CHROME)
        
        # Verify the results
        assert result is True
        mock_os_makedirs.assert_called_once_with(os.path.dirname("/path/to/extension"), exist_ok=True)
        mock_open.assert_called_once_with("/path/to/extension", 'w')
        mock_file.write.assert_called_once_with("Extension for CHROME")
        
        # Should update cache
        assert extension_manager._installed_extensions[BrowserType.CHROME] is True

def test_install_extension_unsupported_browser(extension_manager):
    """Test installing an extension for an unsupported browser."""
    # Mock _get_extension_path to return None for unsupported browser
    with patch.object(extension_manager, '_get_extension_path', return_value=None):
        result = extension_manager.install_extension(BrowserType.UNKNOWN)
        assert result is False

@patch('os.environ.get')
def test_get_extension_base_dir(mock_environ_get, extension_manager):
    """Test getting the base extension directory."""
    # Mock the APPDATA environment variable
    mock_environ_get.return_value = r"C:\\Users\\test\\AppData\\Roaming"
    
    # Should return LocalAppData directory on Windows
    expected = r"C:\\Users\\test\\AppData\\Local"
    result = extension_manager._get_extension_base_dir()
    # Normalize both paths before comparison to handle different path separators
    assert os.path.normpath(result) == os.path.normpath(expected)
    
    # Test when APPDATA is not set (should use home directory)
    mock_environ_get.return_value = None
    with patch('os.path.expanduser', return_value="/home/test"):
        assert extension_manager._get_extension_base_dir() == "/home/test"

def test_get_browser_extension_dir(extension_manager):
    """Test getting the browser-specific extension directory."""
    # Mock the base directory
    with patch.object(extension_manager, '_get_extension_base_dir', 
                     return_value="/base/dir"):
        # Test Chrome
        chrome_path = extension_manager._get_browser_extension_dir(BrowserType.CHROME)
        assert chrome_path == r"/base/dir\Google\Chrome\Extensions"
        
        # Test Firefox
        firefox_path = extension_manager._get_browser_extension_dir(BrowserType.FIREFOX)
        assert firefox_path == r"/base/dir\Mozilla\Firefox\Profiles"
        
        # Test Edge
        edge_path = extension_manager._get_browser_extension_dir(BrowserType.EDGE)
        assert edge_path == r"/base/dir\Microsoft\Edge\Extensions"
        
        # Test Brave
        brave_path = extension_manager._get_browser_extension_dir(BrowserType.BRAVE)
        assert brave_path == r"/base/dir\BraveSoftware\Brave-Browser\Extensions"
        
        # Test Opera
        opera_path = extension_manager._get_browser_extension_dir(BrowserType.OPERA)
        assert opera_path == r"/base/dir\Opera Software\Opera Stable\Extensions"
        
        # Test unknown browser
        unknown_path = extension_manager._get_browser_extension_dir(BrowserType.UNKNOWN)
        assert unknown_path is None

def test_update_extension(extension_manager):
    """Test updating an extension (just calls install_extension)."""
    with patch.object(extension_manager, 'install_extension') as mock_install:
        mock_install.return_value = True
        
        result = extension_manager.update_extension(BrowserType.CHROME)
        
        assert result is True
        mock_install.assert_called_once_with(BrowserType.CHROME)
