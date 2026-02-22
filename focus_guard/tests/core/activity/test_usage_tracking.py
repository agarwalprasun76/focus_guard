"""
Tests for the usage tracking system.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from focus_guard.core.activity.models import WindowInfo
from focus_guard.core.activity.idle_detector import IdleDetector, IdleEvent, IdleState
from focus_guard.core.activity.usage_tracker import (
    UsageTracker, UsageSession, DailyUsageSummary
)


class TestUsageSession:
    """Test usage session functionality."""
    
    def test_session_creation(self):
        """Test creating a usage session."""
        session = UsageSession(
            app_name="chrome.exe",
            window_title="Google - Chrome",
            domain="google.com",
            url="https://google.com",
            is_browser=True
        )
        
        assert session.app_name == "chrome.exe"
        assert session.window_title == "Google - Chrome"
        assert session.domain == "google.com"
        assert session.url == "https://google.com"
        assert session.is_browser is True
        assert session.total_duration == 0.0
        assert session.active_duration == 0.0
        assert len(session.idle_periods) == 0
    
    def test_add_idle_period(self):
        """Test adding idle periods to session."""
        session = UsageSession("test.exe", "Test Window")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)
        
        session.add_idle_period(start_time, end_time)
        
        assert len(session.idle_periods) == 1
        assert session.idle_periods[0]['duration'] == 30.0
        assert session.idle_periods[0]['start_time'] == start_time
        assert session.idle_periods[0]['end_time'] == end_time
    
    def test_calculate_active_duration(self):
        """Test calculating active duration with idle periods."""
        session = UsageSession("test.exe", "Test Window")
        session.total_duration = 100.0
        
        # Add idle periods totaling 30 seconds
        now = datetime.now()
        session.add_idle_period(now, now + timedelta(seconds=10))
        session.add_idle_period(now + timedelta(seconds=50), now + timedelta(seconds=70))
        
        active_duration = session.calculate_active_duration()
        assert active_duration == 70.0  # 100 - 30
        assert session.active_duration == 70.0
    
    def test_to_dict(self):
        """Test session serialization to dictionary."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=60)
        
        session = UsageSession(
            app_name="test.exe",
            window_title="Test Window",
            domain="test.com",
            start_time=start_time,
            end_time=end_time,
            total_duration=60.0,
            active_duration=50.0,
            is_browser=True
        )
        
        session.add_idle_period(start_time + timedelta(seconds=20), start_time + timedelta(seconds=30))
        
        data = session.to_dict()
        
        assert data['app_name'] == "test.exe"
        assert data['window_title'] == "Test Window"
        assert data['domain'] == "test.com"
        assert data['total_duration'] == 60.0
        assert data['active_duration'] == 50.0
        assert data['idle_periods_count'] == 1
        assert data['total_idle_time'] == 10.0
        assert data['is_browser'] is True


class TestDailyUsageSummary:
    """Test daily usage summary functionality."""
    
    def test_summary_creation(self):
        """Test creating a daily summary."""
        summary = DailyUsageSummary(date="2024-01-15")
        
        assert summary.date == "2024-01-15"
        assert summary.total_active_time == 0.0
        assert summary.total_idle_time == 0.0
        assert summary.sessions_count == 0
        assert len(summary.applications) == 0
        assert len(summary.domains) == 0
    
    def test_add_session(self):
        """Test adding sessions to summary."""
        summary = DailyUsageSummary(date="2024-01-15")
        
        session1 = UsageSession("chrome.exe", "Google", domain="google.com")
        session1.active_duration = 30.0
        
        session2 = UsageSession("notepad.exe", "Untitled")
        session2.active_duration = 20.0
        
        summary.add_session(session1)
        summary.add_session(session2)
        
        assert summary.sessions_count == 2
        assert summary.total_active_time == 50.0
        assert summary.applications["chrome.exe"] == 30.0
        assert summary.applications["notepad.exe"] == 20.0
        assert summary.domains["google.com"] == 30.0
    
    def test_to_dict(self):
        """Test summary serialization to dictionary."""
        summary = DailyUsageSummary(date="2024-01-15")
        summary.total_active_time = 100.0
        summary.total_idle_time = 50.0
        summary.sessions_count = 5
        summary.applications = {"chrome.exe": 60.0, "notepad.exe": 40.0}
        summary.domains = {"google.com": 30.0, "github.com": 30.0}
        
        data = summary.to_dict()
        
        assert data['date'] == "2024-01-15"
        assert data['total_active_time'] == 100.0
        assert data['total_idle_time'] == 50.0
        assert data['sessions_count'] == 5
        # Applications should be sorted by time (descending)
        assert list(data['applications'].keys()) == ["chrome.exe", "notepad.exe"]


class TestUsageTracker:
    """Test usage tracker functionality."""
    
    @pytest.fixture
    def mock_idle_detector(self):
        """Create a mock idle detector."""
        detector = Mock(spec=IdleDetector)
        detector.is_idle.return_value = False
        detector.add_state_change_callback = Mock()
        return detector
    
    @pytest.fixture
    def usage_tracker(self, mock_idle_detector):
        """Create usage tracker with mock idle detector."""
        return UsageTracker(mock_idle_detector, session_timeout=5.0)
    
    @pytest.fixture
    def sample_window_info(self):
        """Create sample window info."""
        return WindowInfo(
            app_name="chrome.exe",
            window_title="Google - Chrome",
            pid="1234",
            timestamp=datetime.now()
        )
    
    def test_initialization(self, usage_tracker, mock_idle_detector):
        """Test usage tracker initialization."""
        assert usage_tracker.idle_detector == mock_idle_detector
        assert usage_tracker.session_timeout == 5.0
        assert usage_tracker.current_session is None
        assert not usage_tracker._tracking
        assert len(usage_tracker.completed_sessions) == 0
        
        # Verify idle callback was registered
        mock_idle_detector.add_state_change_callback.assert_called_once()
    
    def test_start_stop_tracking(self, usage_tracker):
        """Test starting and stopping tracking."""
        assert not usage_tracker._tracking
        
        usage_tracker.start_tracking()
        assert usage_tracker._tracking
        assert usage_tracker._track_thread is not None
        
        usage_tracker.stop_tracking()
        assert not usage_tracker._tracking
    
    def test_track_activity_new_session(self, usage_tracker, sample_window_info):
        """Test tracking activity starts new session."""
        usage_tracker.track_activity(sample_window_info)
        
        assert usage_tracker.current_session is not None
        assert usage_tracker.current_session.app_name == "chrome.exe"
        assert usage_tracker.current_session.window_title == "Google - Chrome"
    
    def test_track_activity_same_app(self, usage_tracker, sample_window_info):
        """Test tracking activity for same application."""
        # Start first session
        usage_tracker.track_activity(sample_window_info)
        first_session = usage_tracker.current_session
        
        # Track same app again
        usage_tracker.track_activity(sample_window_info)
        
        # Should be same session
        assert usage_tracker.current_session == first_session
    
    def test_track_activity_different_app(self, usage_tracker, sample_window_info):
        """Test tracking activity for different application."""
        # Start first session
        usage_tracker.track_activity(sample_window_info)
        first_session = usage_tracker.current_session
        
        # Give the session meaningful duration so _end_current_session saves it
        # (start_time must be far enough in the past so recalculated total_duration > 5s)
        first_session.start_time = datetime.now() - timedelta(seconds=10)
        
        # Create different window info
        different_window = WindowInfo(
            app_name="notepad.exe",
            window_title="Untitled - Notepad",
            pid="5678",
            timestamp=datetime.now()
        )
        
        # Track different app
        usage_tracker.track_activity(different_window)
        
        # Should be different session
        assert usage_tracker.current_session != first_session
        assert usage_tracker.current_session.app_name == "notepad.exe"
        assert len(usage_tracker.completed_sessions) == 1
    
    def test_track_activity_different_domain(self, usage_tracker):
        """Test tracking activity for different domain in browser."""
        # Create window info with domain
        window1 = WindowInfo(
            app_name="chrome.exe",
            window_title="Google - Chrome",
            pid="1234",
            timestamp=datetime.now()
        )
        window1.domain = "google.com"
        
        usage_tracker.track_activity(window1)
        first_session = usage_tracker.current_session
        
        # Give the session meaningful duration so _end_current_session saves it
        first_session.start_time = datetime.now() - timedelta(seconds=10)
        
        # Create window info with different domain
        window2 = WindowInfo(
            app_name="chrome.exe",
            window_title="GitHub - Chrome",
            pid="1234",
            timestamp=datetime.now()
        )
        window2.domain = "github.com"
        
        usage_tracker.track_activity(window2)
        
        # Should be different session due to different domain
        assert usage_tracker.current_session != first_session
        assert usage_tracker.current_session.domain == "github.com"
        assert len(usage_tracker.completed_sessions) == 1
    
    def test_session_timeout(self, usage_tracker, sample_window_info):
        """Test session timeout behavior."""
        usage_tracker.track_activity(sample_window_info)
        first_session = usage_tracker.current_session
        
        # Give the session meaningful duration so _end_current_session saves it
        first_session.start_time = datetime.now() - timedelta(seconds=10)
        
        # Simulate time passing beyond timeout
        usage_tracker.last_activity_time = datetime.now() - timedelta(seconds=10)
        
        # Track activity again
        usage_tracker.track_activity(sample_window_info)
        
        # Should create new session due to timeout
        assert usage_tracker.current_session != first_session
        assert len(usage_tracker.completed_sessions) == 1
    
    def test_idle_state_change_callback(self, usage_tracker):
        """Test idle state change handling."""
        # Start a session
        window_info = WindowInfo("test.exe", "Test", "123", datetime.now())
        usage_tracker.track_activity(window_info)
        
        # Simulate idle state change to idle
        idle_event = IdleEvent(
            timestamp=datetime.now(),
            previous_state=IdleState.ACTIVE,
            current_state=IdleState.SHORT_IDLE,
            idle_duration=60.0,
            active_duration=120.0
        )
        
        usage_tracker._on_idle_state_change(idle_event)
        assert usage_tracker.current_idle_start is not None
        
        # Simulate return to active
        active_event = IdleEvent(
            timestamp=datetime.now() + timedelta(seconds=30),
            previous_state=IdleState.SHORT_IDLE,
            current_state=IdleState.ACTIVE,
            idle_duration=0.0,
            active_duration=150.0
        )
        
        usage_tracker._on_idle_state_change(active_event)
        assert usage_tracker.current_idle_start is None
        
        # Check that idle period was added to current session
        if usage_tracker.current_session:
            assert len(usage_tracker.current_session.idle_periods) == 1
    
    def test_session_callbacks(self, usage_tracker, sample_window_info):
        """Test session completion callbacks."""
        callback = Mock()
        usage_tracker.add_session_callback(callback)
        
        # Start and end a session
        usage_tracker.track_activity(sample_window_info)
        
        # Simulate meaningful session duration (> 5s threshold in _end_current_session)
        usage_tracker.current_session.active_duration = 10.0
        usage_tracker.current_session.total_duration = 10.0
        usage_tracker.current_session.start_time = datetime.now() - timedelta(seconds=10)
        usage_tracker._end_current_session()
        
        # Verify callback was called
        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert isinstance(call_args, UsageSession)
        assert call_args.app_name == "chrome.exe"
    
    def test_get_current_session_info(self, usage_tracker, sample_window_info):
        """Test getting current session information."""
        # No current session
        assert usage_tracker.get_current_session_info() is None
        
        # With active session
        usage_tracker.track_activity(sample_window_info)
        info = usage_tracker.get_current_session_info()
        
        assert info is not None
        assert info['app_name'] == "chrome.exe"
        assert info['window_title'] == "Google - Chrome"
        assert 'current_duration' in info
        assert 'start_time' in info
    
    def test_daily_summary_update(self, usage_tracker, sample_window_info):
        """Test daily summary updates."""
        usage_tracker.track_activity(sample_window_info)
        
        # Simulate session completion
        session = usage_tracker.current_session
        session.active_duration = 30.0
        session.end_time = datetime.now()
        
        usage_tracker._update_daily_summary(session)
        
        date_str = session.start_time.strftime('%Y-%m-%d')
        assert date_str in usage_tracker.daily_summaries
        
        summary = usage_tracker.daily_summaries[date_str]
        assert summary.sessions_count == 1
        assert summary.total_active_time == 30.0
        assert summary.applications["chrome.exe"] == 30.0
    
    def test_get_usage_statistics(self, usage_tracker):
        """Test getting usage statistics."""
        # Add some mock data
        now = datetime.now()
        usage_tracker.daily_summaries["2024-01-15"] = DailyUsageSummary("2024-01-15")
        usage_tracker.daily_summaries["2024-01-15"].total_active_time = 100.0
        usage_tracker.daily_summaries["2024-01-15"].sessions_count = 5
        usage_tracker.daily_summaries["2024-01-15"].applications = {"chrome.exe": 60.0, "notepad.exe": 40.0}
        
        stats = usage_tracker.get_usage_statistics(7)
        
        assert 'period' in stats
        assert 'total_active_time' in stats
        assert 'total_sessions' in stats
        assert 'average_daily_active_time' in stats
        assert 'top_applications' in stats
        assert 'sessions_per_day' in stats
    
    def test_get_recent_sessions(self, usage_tracker):
        """Test getting recent sessions."""
        # Add some mock sessions
        now = datetime.now()
        
        recent_session = UsageSession("chrome.exe", "Recent", start_time=now - timedelta(hours=1))
        old_session = UsageSession("notepad.exe", "Old", start_time=now - timedelta(days=2))
        
        usage_tracker.completed_sessions = [recent_session, old_session]
        
        recent = usage_tracker.get_recent_sessions(24)
        assert len(recent) == 1
        assert recent[0] == recent_session
    
    def test_clear_old_data(self, usage_tracker):
        """Test clearing old data."""
        now = datetime.now()
        
        # Add old and new data
        old_session = UsageSession("old.exe", "Old", start_time=now - timedelta(days=40))
        new_session = UsageSession("new.exe", "New", start_time=now - timedelta(days=10))
        
        # Use dates relative to now so the 30-day cutoff works correctly
        old_date = (now - timedelta(days=40)).strftime('%Y-%m-%d')
        new_date = (now - timedelta(days=10)).strftime('%Y-%m-%d')
        
        usage_tracker.completed_sessions = [old_session, new_session]
        usage_tracker.daily_summaries = {
            old_date: DailyUsageSummary(old_date),
            new_date: DailyUsageSummary(new_date)
        }
        
        usage_tracker.clear_old_data(30)
        
        # Should keep only new data
        assert len(usage_tracker.completed_sessions) == 1
        assert usage_tracker.completed_sessions[0] == new_session
        assert old_date not in usage_tracker.daily_summaries
        assert new_date in usage_tracker.daily_summaries
    
    def test_is_browser_detection(self, usage_tracker):
        """Test browser detection."""
        assert usage_tracker._is_browser("chrome.exe")
        assert usage_tracker._is_browser("firefox.exe")
        assert usage_tracker._is_browser("msedge.exe")
        assert usage_tracker._is_browser("Chrome")
        assert not usage_tracker._is_browser("notepad.exe")
        assert not usage_tracker._is_browser("calculator.exe")


if __name__ == '__main__':
    pytest.main([__file__])
