"""
Tests for the idle detection system.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from focus_guard.core.activity.idle_detector import (
    IdleDetector, IdleConfiguration, IdleState, IdleEvent,
    WindowsIdleDetector, LinuxIdleDetector, MacOSIdleDetector
)


class TestIdleConfiguration:
    """Test idle configuration."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = IdleConfiguration()
        assert config.short_idle_threshold == 60.0
        assert config.medium_idle_threshold == 300.0
        assert config.long_idle_threshold == 900.0
        assert config.polling_interval == 5.0
        assert config.sensitivity == 1.0
    
    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = IdleConfiguration(
            short_idle_threshold=30.0,
            medium_idle_threshold=120.0,
            long_idle_threshold=600.0,
            polling_interval=2.0,
            sensitivity=1.5
        )
        assert config.short_idle_threshold == 30.0
        assert config.medium_idle_threshold == 120.0
        assert config.long_idle_threshold == 600.0
        assert config.polling_interval == 2.0
        assert config.sensitivity == 1.5


class TestWindowsIdleDetector:
    """Test Windows idle detector."""
    
    def test_is_supported_on_windows(self):
        """Test Windows detector is supported on Windows."""
        detector = WindowsIdleDetector()
        with patch('sys.platform', 'win32'):
            assert detector.is_supported()
    
    def test_is_not_supported_on_linux(self):
        """Test Windows detector is not supported on Linux."""
        detector = WindowsIdleDetector()
        with patch('sys.platform', 'linux'):
            assert not detector.is_supported()
    
    @patch('sys.platform', 'win32')
    def test_get_idle_time_success(self):
        """Test successful idle time retrieval."""
        detector = WindowsIdleDetector()
        
        with patch('ctypes.windll.user32.GetLastInputInfo') as mock_get_input, \
             patch('ctypes.windll.kernel32.GetTickCount') as mock_get_tick, \
             patch('ctypes.sizeof') as mock_sizeof:
            
            mock_get_input.return_value = True
            mock_get_tick.return_value = 10000
            mock_sizeof.return_value = 8
            
            # Mock the structure properly
            mock_struct = Mock()
            mock_struct.dwTime = 5000
            
            with patch('focus_guard.core.activity.idle_detector.ctypes.byref') as mock_byref:
                mock_byref.return_value = mock_struct
                idle_time = detector.get_idle_time_seconds()
                assert idle_time == 5.0  # (10000 - 5000) / 1000
    
    @patch('sys.platform', 'win32')
    def test_get_idle_time_failure(self):
        """Test idle time retrieval failure."""
        detector = WindowsIdleDetector()
        
        with patch('ctypes.windll.user32.GetLastInputInfo') as mock_get_input:
            mock_get_input.return_value = False
            idle_time = detector.get_idle_time_seconds()
            assert idle_time == 0.0
    
    @patch('sys.platform', 'win32')
    def test_get_idle_time_exception(self):
        """Test idle time retrieval with exception."""
        detector = WindowsIdleDetector()
        
        with patch('ctypes.windll.user32.GetLastInputInfo', side_effect=Exception("Test error")):
            idle_time = detector.get_idle_time_seconds()
            assert idle_time == 0.0


class TestLinuxIdleDetector:
    """Test Linux idle detector."""
    
    def test_is_supported_on_linux(self):
        """Test Linux detector is supported on Linux."""
        detector = LinuxIdleDetector()
        with patch('sys.platform', 'linux'):
            assert detector.is_supported()
    
    def test_is_not_supported_on_windows(self):
        """Test Linux detector is not supported on Windows."""
        detector = LinuxIdleDetector()
        with patch('sys.platform', 'win32'):
            assert not detector.is_supported()
    
    @patch('sys.platform', 'linux')
    def test_get_idle_time_xprintidle_success(self):
        """Test successful idle time retrieval with xprintidle."""
        detector = LinuxIdleDetector()
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "5000"
        
        with patch('subprocess.run', return_value=mock_result):
            idle_time = detector.get_idle_time_seconds()
            assert idle_time == 5.0
    
    @patch('sys.platform', 'linux')
    def test_get_idle_time_fallback_to_xssstate(self):
        """Test fallback to xssstate when xprintidle fails."""
        detector = LinuxIdleDetector()
        
        # First call (xprintidle) fails, second call (xssstate) succeeds
        mock_result_fail = Mock()
        mock_result_fail.returncode = 1
        
        mock_result_success = Mock()
        mock_result_success.returncode = 0
        mock_result_success.stdout = "3000"
        
        with patch('subprocess.run', side_effect=[mock_result_fail, mock_result_success]):
            idle_time = detector.get_idle_time_seconds()
            assert idle_time == 3.0
    
    @patch('sys.platform', 'linux')
    def test_get_idle_time_all_methods_fail(self):
        """Test when all idle detection methods fail."""
        detector = LinuxIdleDetector()
        
        with patch('subprocess.run', side_effect=Exception("Command not found")), \
             patch('builtins.open', side_effect=Exception("File not found")):
            idle_time = detector.get_idle_time_seconds()
            assert idle_time == 0.0


class TestMacOSIdleDetector:
    """Test macOS idle detector."""
    
    def test_is_supported_on_macos(self):
        """Test macOS detector is supported on macOS."""
        detector = MacOSIdleDetector()
        with patch('sys.platform', 'darwin'):
            with patch.object(detector, '_import_quartz', return_value=True):
                assert detector.is_supported()
    
    def test_is_not_supported_on_windows(self):
        """Test macOS detector is not supported on Windows."""
        detector = MacOSIdleDetector()
        with patch('sys.platform', 'win32'):
            assert not detector.is_supported()
    
    @patch('sys.platform', 'darwin')
    def test_get_idle_time_success(self):
        """Test successful idle time retrieval on macOS."""
        detector = MacOSIdleDetector()
        
        with patch('Quartz.CGEventSourceSecondsSinceLastEventType', return_value=5.5):
            idle_time = detector.get_idle_time_seconds()
            assert idle_time == 5.5
    
    @patch('sys.platform', 'darwin')
    def test_get_idle_time_exception(self):
        """Test idle time retrieval with exception on macOS."""
        detector = MacOSIdleDetector()
        
        with patch('Quartz.CGEventSourceSecondsSinceLastEventType', 
                  side_effect=Exception("Quartz error")):
            idle_time = detector.get_idle_time_seconds()
            assert idle_time == 0.0


class TestIdleDetector:
    """Test main idle detector."""
    
    @pytest.fixture
    def mock_platform_detector(self):
        """Create a mock platform detector."""
        detector = Mock()
        detector.get_idle_time_seconds.return_value = 0.0
        detector.is_supported.return_value = True
        return detector
    
    @pytest.fixture
    def idle_detector(self, mock_platform_detector):
        """Create idle detector with mock platform detector."""
        config = IdleConfiguration(
            short_idle_threshold=10.0,
            medium_idle_threshold=30.0,
            long_idle_threshold=60.0,
            polling_interval=0.1
        )
        
        detector = IdleDetector(config)
        detector.platform_detector = mock_platform_detector
        return detector
    
    def test_initialization(self):
        """Test idle detector initialization."""
        detector = IdleDetector()
        assert detector.current_state == IdleState.ACTIVE
        assert not detector._monitoring
        assert detector.total_active_time == 0.0
        assert detector.total_idle_time == 0.0
    
    def test_get_idle_time_seconds(self, idle_detector, mock_platform_detector):
        """Test getting idle time."""
        mock_platform_detector.get_idle_time_seconds.return_value = 5.0
        assert idle_detector.get_idle_time_seconds() == 5.0
    
    def test_is_idle_with_default_threshold(self, idle_detector, mock_platform_detector):
        """Test idle check with default threshold."""
        mock_platform_detector.get_idle_time_seconds.return_value = 15.0
        assert idle_detector.is_idle()  # Should be idle (15 > 10)
        
        mock_platform_detector.get_idle_time_seconds.return_value = 5.0
        assert not idle_detector.is_idle()  # Should not be idle (5 < 10)
    
    def test_is_idle_with_custom_threshold(self, idle_detector, mock_platform_detector):
        """Test idle check with custom threshold."""
        mock_platform_detector.get_idle_time_seconds.return_value = 25.0
        assert idle_detector.is_idle(20.0)  # Should be idle (25 > 20)
        assert not idle_detector.is_idle(30.0)  # Should not be idle (25 < 30)
    
    def test_is_active(self, idle_detector, mock_platform_detector):
        """Test active check."""
        mock_platform_detector.get_idle_time_seconds.return_value = 5.0
        assert idle_detector.is_active()  # Should be active (5 < 10)
        
        mock_platform_detector.get_idle_time_seconds.return_value = 15.0
        assert not idle_detector.is_active()  # Should not be active (15 > 10)
    
    def test_state_change_callbacks(self, idle_detector):
        """Test state change callback registration."""
        callback1 = Mock()
        callback2 = Mock()
        
        idle_detector.add_state_change_callback(callback1)
        idle_detector.add_state_change_callback(callback2)
        
        assert callback1 in idle_detector.state_change_callbacks
        assert callback2 in idle_detector.state_change_callbacks
        
        idle_detector.remove_state_change_callback(callback1)
        assert callback1 not in idle_detector.state_change_callbacks
        assert callback2 in idle_detector.state_change_callbacks
    
    def test_state_transitions(self, idle_detector, mock_platform_detector):
        """Test idle state transitions."""
        # Start monitoring
        idle_detector.start_monitoring()
        time.sleep(0.2)  # Let monitoring start
        
        # Simulate transition to short idle
        mock_platform_detector.get_idle_time_seconds.return_value = 15.0
        time.sleep(0.2)  # Let state update
        
        assert idle_detector.get_current_state() == IdleState.SHORT_IDLE
        
        # Simulate transition to medium idle
        mock_platform_detector.get_idle_time_seconds.return_value = 35.0
        time.sleep(0.2)  # Let state update
        
        assert idle_detector.get_current_state() == IdleState.MEDIUM_IDLE
        
        # Simulate transition to long idle
        mock_platform_detector.get_idle_time_seconds.return_value = 65.0
        time.sleep(0.2)  # Let state update
        
        assert idle_detector.get_current_state() == IdleState.LONG_IDLE
        
        # Simulate return to active
        mock_platform_detector.get_idle_time_seconds.return_value = 0.0
        time.sleep(0.2)  # Let state update
        
        assert idle_detector.get_current_state() == IdleState.ACTIVE
        
        idle_detector.stop_monitoring()
    
    def test_callback_notification(self, idle_detector, mock_platform_detector):
        """Test that callbacks are called on state changes."""
        callback = Mock()
        idle_detector.add_state_change_callback(callback)
        
        # Start monitoring
        idle_detector.start_monitoring()
        time.sleep(0.2)
        
        # Trigger state change
        mock_platform_detector.get_idle_time_seconds.return_value = 15.0
        time.sleep(0.2)
        
        # Check callback was called
        callback.assert_called()
        
        # Verify event structure
        call_args = callback.call_args[0][0]
        assert isinstance(call_args, IdleEvent)
        assert call_args.current_state == IdleState.SHORT_IDLE
        assert call_args.previous_state == IdleState.ACTIVE
        
        idle_detector.stop_monitoring()
    
    def test_statistics(self, idle_detector):
        """Test statistics collection."""
        stats = idle_detector.get_statistics()
        
        assert 'current_state' in stats
        assert 'current_idle_time' in stats
        assert 'total_active_time' in stats
        assert 'total_idle_time' in stats
        assert 'active_percentage' in stats
        assert 'idle_periods_count' in stats
        assert 'monitoring' in stats
        assert 'platform_detector' in stats
    
    def test_sensitivity_adjustment(self, idle_detector, mock_platform_detector):
        """Test sensitivity adjustment affects thresholds."""
        # Set sensitivity to 0.5 (makes thresholds more sensitive)
        idle_detector.config.sensitivity = 0.5
        
        idle_detector.start_monitoring()
        time.sleep(0.2)
        
        # With sensitivity 0.5, short_idle_threshold becomes 5.0
        mock_platform_detector.get_idle_time_seconds.return_value = 7.0
        time.sleep(0.2)
        
        # Should transition to short idle with adjusted threshold
        assert idle_detector.get_current_state() == IdleState.SHORT_IDLE
        
        idle_detector.stop_monitoring()
    
    def test_monitoring_lifecycle(self, idle_detector):
        """Test monitoring start/stop lifecycle."""
        assert not idle_detector._monitoring
        
        idle_detector.start_monitoring()
        assert idle_detector._monitoring
        assert idle_detector._monitor_thread is not None
        
        idle_detector.stop_monitoring()
        assert not idle_detector._monitoring
    
    def test_recent_idle_periods(self, idle_detector):
        """Test getting recent idle periods."""
        # Add some mock idle periods
        now = datetime.now()
        idle_detector.idle_periods = [
            {
                'start_time': now - timedelta(hours=2),
                'end_time': now - timedelta(hours=1, minutes=55),
                'duration': 300.0,
                'max_state': 'short_idle'
            },
            {
                'start_time': now - timedelta(days=2),
                'end_time': now - timedelta(days=2) + timedelta(hours=1),
                'duration': 600.0,
                'max_state': 'medium_idle'
            }
        ]
        
        # Get recent periods (last 24 hours)
        recent = idle_detector.get_recent_idle_periods(24)
        assert len(recent) == 1
        assert recent[0]['duration'] == 300.0
        
        # Get all periods (last 48 hours)
        all_periods = idle_detector.get_recent_idle_periods(48)
        assert len(all_periods) == 2
    
    def test_reset_statistics(self, idle_detector):
        """Test statistics reset."""
        # Set some values
        idle_detector.total_active_time = 100.0
        idle_detector.total_idle_time = 50.0
        idle_detector.idle_periods = [{'test': 'data'}]
        
        idle_detector.reset_statistics()
        
        assert idle_detector.total_active_time == 0.0
        assert idle_detector.total_idle_time == 0.0
        assert len(idle_detector.idle_periods) == 0


if __name__ == '__main__':
    pytest.main([__file__])
