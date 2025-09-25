"""
Unit tests for alert system platform implementations.

This module contains tests for the platform interface and implementations.
"""

import sys
import pytest
from unittest.mock import patch, MagicMock

from focus_guard.core.alert.platform.base import PlatformAlertInterface
from focus_guard.core.alert.platform import get_platform_implementation
from focus_guard.core.alert.platform.stub import StubAlertPlatform
from focus_guard.core.alert.platform.windows import WindowsAlertPlatform


class TestPlatformInterface:
    """Tests for the platform interface."""
    
    def test_abstract_methods(self):
        """Test that abstract methods are defined."""
        methods = [
            'show_notification',
            'play_sound',
            'show_blocking_alert',
            'is_supported'
        ]
        
        for method in methods:
            assert hasattr(PlatformAlertInterface, method)


class TestPlatformFactory:
    """Tests for the platform factory."""
    
    def test_windows_platform_detection(self):
        """Test Windows platform detection."""
        # Reset the platform singleton instance
        from focus_guard.core.alert.platform import _platform_instance
        _platform_instance = None
        
        # Mock Windows environment
        with patch('sys.platform', 'win32'):
            # Mock is_supported to return True
            with patch.object(WindowsAlertPlatform, 'is_supported', return_value=True):
                platform = get_platform_implementation()
                assert isinstance(platform, WindowsAlertPlatform)
    
    def test_fallback_to_stub(self):
        """Test fallback to stub platform when no supported platform found."""
        # Reset the platform singleton instance
        from focus_guard.core.alert.platform import _platform_instance, get_platform_implementation
        _platform_instance = None
        
        # Mock the platform to be unsupported
        with patch('sys.platform', 'unsupported_platform'):
            # Import here to avoid caching issues
            import importlib
            import focus_guard.core.alert.platform as platform_module
            importlib.reload(platform_module)
            
            # Get the implementation
            platform = platform_module.get_platform_implementation()
            assert isinstance(platform, StubAlertPlatform)
    
    def test_singleton_behavior(self):
        """Test that get_platform_implementation returns a singleton."""
        # Reset the platform singleton instance
        from focus_guard.core.alert.platform import _platform_instance
        _platform_instance = None
        
        # Get platform implementation twice
        platform1 = get_platform_implementation()
        platform2 = get_platform_implementation()
        
        # Should be the same instance
        assert platform1 is platform2


class TestStubPlatform:
    """Tests for the stub platform implementation."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.platform = StubAlertPlatform()
        yield
        # Teardown if needed
    
    def test_is_supported(self):
        """Test that stub platform is always supported."""
        assert StubAlertPlatform.is_supported()
    
    def test_show_notification(self):
        """Test showing a notification."""
        result = self.platform.show_notification(
            title="Test Title",
            message="Test Message",
            level="normal",
            options={"app_name": "TestApp"}
        )
        assert result
    
    def test_play_sound(self):
        """Test playing a sound."""
        # Should not raise any exceptions
        result = self.platform.play_sound("test_sound")
        assert result is True
    
    def test_show_blocking_alert(self):
        """Test showing a blocking alert."""
        # Should not raise any exceptions
        result = self.platform.show_blocking_alert(
            title="Test",
            message="Test message",
            level="warning"
        )
        assert result is True


class TestWindowsPlatform:
    """Tests for the Windows platform implementation."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.platform = WindowsAlertPlatform()
        yield
        # Teardown if needed
    
    def test_is_supported(self):
        """Test Windows platform support detection."""
        # Save original platform
        original_platform = sys.platform
        
        try:
            # Test Windows platform with PowerShell available
            sys.platform = 'win32'
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                assert WindowsAlertPlatform.is_supported()
            
            # Test Windows platform without PowerShell
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = FileNotFoundError()
                assert not WindowsAlertPlatform.is_supported()
            
            # Test non-Windows platform
            sys.platform = 'linux'
            assert not WindowsAlertPlatform.is_supported()
            
        finally:
            # Restore original platform
            sys.platform = original_platform
    
    def test_show_notification(self):
        """Test showing a notification."""
        # Mock the thread
        mock_thread = MagicMock()
        with patch('threading.Thread', return_value=mock_thread) as mock_thread_cls:
            # Call the method
            result = self.platform.show_notification(
                title="Test",
                message="Test message",
                level="normal"
            )
            
            # Verify thread was started
            mock_thread_cls.assert_called_once()
            mock_thread.start.assert_called_once()
            assert result is True
    
    def test_play_sound(self):
        """Test playing a sound."""
        # Mock the thread
        mock_thread = MagicMock()
        
        with patch('threading.Thread', return_value=mock_thread) as mock_thread_cls:
            # Test sound playback
            result = self.platform.play_sound("test_sound")
            mock_thread_cls.assert_called_once()
            mock_thread.start.assert_called_once()
            assert result is True
    
    def test_show_blocking_alert(self):
        """Test showing a blocking alert."""
        # Mock subprocess.run for PowerShell
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            # Call the method
            result = self.platform.show_blocking_alert(
                title="Test",
                message="Test message",
                level="warning"
            )
            
            # Verify PowerShell was called
            mock_run.assert_called_once()
            assert result is True
    
    def test_show_blocking_alert_timeout(self):
        """Test showing a blocking alert with timeout."""
        with patch('subprocess.run') as mock_run:
            # Configure the mock to return success
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_run.return_value = mock_process
            
            # Call the method with timeout
            result = self.platform.show_blocking_alert(
                title="Test",
                message="Test message",
                level="warning",
                options={"timeout": 5}
            )
            
            # Verify PowerShell was called with the correct timeout
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            
            # The args is a list where:
            # args[0] is the command list: ['powershell', '-Command', 'script_content']
            # So we need to check the command and script content
            cmd_args = args[0]
            assert cmd_args[0].endswith('powershell') or cmd_args[0].endswith('powershell.exe')
            assert cmd_args[1] == "-Command"
            
            # The script is in the third argument
            script = cmd_args[2]
            assert "Test message" in script  # Check message is in the script
            assert "Test" in script  # Check title is in the script
            assert kwargs["timeout"] == 5  # Check timeout is set correctly
            assert result is True
# Removed unittest.main() as we're using pytest
