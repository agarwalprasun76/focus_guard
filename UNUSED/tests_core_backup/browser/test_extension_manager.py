"""
Unit tests for the ExtensionManager class.

This module contains tests for the ExtensionManager class in core_v2.browser.adapter.
"""

import unittest
import os
import shutil
from unittest.mock import patch, MagicMock, mock_open
import pytest
import tempfile

from core_v2.browser.adapter import ExtensionManager
from core_v2.browser.models.browser import BrowserType


class TestExtensionManager:
    """Test cases for the ExtensionManager class."""

    @pytest.fixture
    def extension_manager(self):
        """Create an ExtensionManager instance for testing."""
        return ExtensionManager()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Clean up after test
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    def test_is_extension_installed_not_installed(self, extension_manager):
        """Test is_extension_installed when extension is not installed."""
        # Mock the _get_extension_path method to return None
        with patch.object(ExtensionManager, '_get_extension_path', return_value=None):
            # Check if extension is installed
            result = extension_manager.is_extension_installed(BrowserType.CHROME)
            
            # Verify the result
            assert result is False

    def test_is_extension_installed_installed(self, extension_manager):
        """Test is_extension_installed when extension is installed."""
        # Mock the _get_extension_path method to return a path
        with patch.object(ExtensionManager, '_get_extension_path', return_value="/path/to/extension"):
            # Check if extension is installed
            result = extension_manager.is_extension_installed(BrowserType.CHROME)
            
            # Verify the result
            assert result is True

    def test_get_extension_path_chrome(self, extension_manager, temp_dir):
        """Test _get_extension_path for Chrome."""
        # Create a mock Chrome extension directory
        chrome_ext_dir = os.path.join(temp_dir, "chrome_extension")
        os.makedirs(chrome_ext_dir)
        
        # Mock the _get_browser_extension_dir method to return our test directory
        with patch.object(ExtensionManager, '_get_browser_extension_dir', return_value=chrome_ext_dir):
            # Get the extension path
            path = extension_manager._get_extension_path(BrowserType.CHROME)
            
            # Verify the path
            assert path == chrome_ext_dir

    def test_get_extension_path_nonexistent(self, extension_manager):
        """Test _get_extension_path for a nonexistent extension directory."""
        # Mock the _get_browser_extension_dir method to return a nonexistent directory
        with patch.object(ExtensionManager, '_get_browser_extension_dir', return_value="/nonexistent/path"):
            # Get the extension path
            path = extension_manager._get_extension_path(BrowserType.CHROME)
            
            # Verify the path is None
            assert path is None

    def test_get_browser_extension_dir_chrome(self, extension_manager):
        """Test _get_browser_extension_dir for Chrome."""
        # Mock the _get_extension_base_dir method
        base_dir = "/base/dir"
        with patch.object(ExtensionManager, '_get_extension_base_dir', return_value=base_dir):
            # Get the browser extension directory
            dir_path = extension_manager._get_browser_extension_dir(BrowserType.CHROME)
            
            # Verify the directory path
            assert dir_path == os.path.join(base_dir, "chrome")

    def test_get_browser_extension_dir_firefox(self, extension_manager):
        """Test _get_browser_extension_dir for Firefox."""
        # Mock the _get_extension_base_dir method
        base_dir = "/base/dir"
        with patch.object(ExtensionManager, '_get_extension_base_dir', return_value=base_dir):
            # Get the browser extension directory
            dir_path = extension_manager._get_browser_extension_dir(BrowserType.FIREFOX)
            
            # Verify the directory path
            assert dir_path == os.path.join(base_dir, "firefox")

    def test_get_browser_extension_dir_edge(self, extension_manager):
        """Test _get_browser_extension_dir for Edge."""
        # Mock the _get_extension_base_dir method
        base_dir = "/base/dir"
        with patch.object(ExtensionManager, '_get_extension_base_dir', return_value=base_dir):
            # Get the browser extension directory
            dir_path = extension_manager._get_browser_extension_dir(BrowserType.EDGE)
            
            # Verify the directory path
            assert dir_path == os.path.join(base_dir, "edge")

    def test_get_browser_extension_dir_unsupported(self, extension_manager):
        """Test _get_browser_extension_dir for an unsupported browser type."""
        # Mock the _get_extension_base_dir method
        base_dir = "/base/dir"
        with patch.object(ExtensionManager, '_get_extension_base_dir', return_value=base_dir):
            # Get the browser extension directory for an unsupported browser type
            dir_path = extension_manager._get_browser_extension_dir("UNSUPPORTED")
            
            # Verify the directory path is None
            assert dir_path is None

    def test_get_extension_base_dir(self, extension_manager):
        """Test _get_extension_base_dir."""
        # Mock the os.path.abspath and os.path.join functions
        with patch('os.path.abspath', return_value="/abs/path"), \
             patch('os.path.join', return_value="/abs/path/extensions"):
            # Get the extension base directory
            base_dir = extension_manager._get_extension_base_dir()
            
            # Verify the base directory
            assert base_dir == "/abs/path/extensions"

    def test_install_extension_success(self, extension_manager):
        """Test install_extension with successful installation."""
        # Mock the necessary methods
        with patch.object(ExtensionManager, '_get_browser_extension_dir', return_value="/ext/dir"), \
             patch('os.path.exists', return_value=False), \
             patch('os.makedirs') as mock_makedirs, \
             patch('shutil.copytree') as mock_copytree:
            # Install the extension
            result = extension_manager.install_extension(BrowserType.CHROME)
            
            # Verify the result
            assert result is True
            
            # Verify the directories were created
            mock_makedirs.assert_called_once()
            
            # Verify the extension files were copied
            mock_copytree.assert_called_once()

    def test_install_extension_already_installed(self, extension_manager):
        """Test install_extension when extension is already installed."""
        # Mock the necessary methods
        with patch.object(ExtensionManager, '_get_browser_extension_dir', return_value="/ext/dir"), \
             patch('os.path.exists', return_value=True), \
             patch('shutil.copytree') as mock_copytree:
            # Install the extension
            result = extension_manager.install_extension(BrowserType.CHROME)
            
            # Verify the result
            assert result is True
            
            # Verify no files were copied (already installed)
            mock_copytree.assert_not_called()

    def test_install_extension_unsupported_browser(self, extension_manager):
        """Test install_extension with an unsupported browser type."""
        # Mock the _get_browser_extension_dir method to return None for unsupported browser
        with patch.object(ExtensionManager, '_get_browser_extension_dir', return_value=None):
            # Install the extension
            result = extension_manager.install_extension("UNSUPPORTED")
            
            # Verify the result
            assert result is False

    def test_install_extension_error(self, extension_manager):
        """Test install_extension with an error during installation."""
        # Mock the necessary methods
        with patch.object(ExtensionManager, '_get_browser_extension_dir', return_value="/ext/dir"), \
             patch('os.path.exists', return_value=False), \
             patch('os.makedirs'), \
             patch('shutil.copytree', side_effect=Exception("Installation error")):
            # Install the extension
            result = extension_manager.install_extension(BrowserType.CHROME)
            
            # Verify the result
            assert result is False

    def test_update_extension_success(self, extension_manager):
        """Test update_extension with successful update."""
        # Mock the necessary methods
        with patch.object(ExtensionManager, '_get_browser_extension_dir', return_value="/ext/dir"), \
             patch('os.path.exists', return_value=True), \
             patch('shutil.rmtree') as mock_rmtree, \
             patch('shutil.copytree') as mock_copytree:
            # Update the extension
            result = extension_manager.update_extension(BrowserType.CHROME)
            
            # Verify the result
            assert result is True
            
            # Verify the old extension was removed
            mock_rmtree.assert_called_once()
            
            # Verify the new extension was copied
            mock_copytree.assert_called_once()

    def test_update_extension_not_installed(self, extension_manager):
        """Test update_extension when extension is not installed."""
        # Mock the necessary methods
        with patch.object(ExtensionManager, '_get_browser_extension_dir', return_value="/ext/dir"), \
             patch('os.path.exists', return_value=False), \
             patch('shutil.rmtree') as mock_rmtree, \
             patch('shutil.copytree') as mock_copytree:
            # Update the extension
            result = extension_manager.update_extension(BrowserType.CHROME)
            
            # Verify the result
            assert result is False
            
            # Verify no files were removed or copied
            mock_rmtree.assert_not_called()
            mock_copytree.assert_not_called()

    def test_update_extension_unsupported_browser(self, extension_manager):
        """Test update_extension with an unsupported browser type."""
        # Mock the _get_browser_extension_dir method to return None for unsupported browser
        with patch.object(ExtensionManager, '_get_browser_extension_dir', return_value=None):
            # Update the extension
            result = extension_manager.update_extension("UNSUPPORTED")
            
            # Verify the result
            assert result is False

    def test_update_extension_error(self, extension_manager):
        """Test update_extension with an error during update."""
        # Mock the necessary methods
        with patch.object(ExtensionManager, '_get_browser_extension_dir', return_value="/ext/dir"), \
             patch('os.path.exists', return_value=True), \
             patch('shutil.rmtree'), \
             patch('shutil.copytree', side_effect=Exception("Update error")):
            # Update the extension
            result = extension_manager.update_extension(BrowserType.CHROME)
            
            # Verify the result
            assert result is False


if __name__ == "__main__":
    pytest.main(["-v", "test_extension_manager.py"])
