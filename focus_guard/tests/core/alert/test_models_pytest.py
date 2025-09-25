"""
Pytest tests for alert system models.

This module contains tests for the alert system data models.
"""

import pytest
from datetime import datetime
from dataclasses import asdict

from focus_guard.core.alert.models import AlertLevel, AlertInfo, AlertHistoryEntry


class TestAlertLevel:
    """Tests for the AlertLevel enum."""
    
    @pytest.mark.parametrize("input_str,expected_level", [
        ("normal", AlertLevel.NORMAL),
        ("NORMAL", AlertLevel.NORMAL),
        ("warning", AlertLevel.WARNING),
        ("WARNING", AlertLevel.WARNING),
        ("critical", AlertLevel.CRITICAL),
        ("CRITICAL", AlertLevel.CRITICAL),
    ])
    def test_from_string(self, input_str, expected_level):
        """Test converting strings to AlertLevel."""
        assert AlertLevel.from_string(input_str) == expected_level
    
    def test_from_string_invalid(self):
        """Test invalid string values for AlertLevel."""
        with pytest.raises(ValueError):
            AlertLevel.from_string("invalid")
    
    @pytest.mark.parametrize("level,expected_str", [
        (AlertLevel.NORMAL, "normal"),
        (AlertLevel.WARNING, "warning"),
        (AlertLevel.CRITICAL, "critical"),
    ])
    def test_to_string(self, level, expected_str):
        """Test converting AlertLevel to string."""
        assert level.to_string() == expected_str
    
    def test_comparison(self):
        """Test comparing AlertLevel values."""
        assert AlertLevel.NORMAL.value < AlertLevel.WARNING.value
        assert AlertLevel.WARNING.value < AlertLevel.CRITICAL.value
        assert AlertLevel.CRITICAL.value > AlertLevel.NORMAL.value


class TestAlertInfo:
    """Tests for the AlertInfo dataclass."""
    
    @pytest.fixture
    def sample_alert_info(self):
        """Create a sample AlertInfo instance for testing."""
        return AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=datetime.now(),
            window_title="Test Window",
            window_rect={"x": 0, "y": 0, "width": 800, "height": 600}
        )
    
    def test_creation(self, sample_alert_info):
        """Test creating an AlertInfo instance."""
        assert sample_alert_info.app_name == "TestApp"
        assert sample_alert_info.message == "Test message"
        assert sample_alert_info.level == AlertLevel.WARNING
        assert isinstance(sample_alert_info.timestamp, datetime)
        assert sample_alert_info.window_title == "Test Window"
        assert sample_alert_info.window_rect == {"x": 0, "y": 0, "width": 800, "height": 600}
    
    def test_creation_with_string_level(self):
        """Test creating an AlertInfo with string level."""
        info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level="warning"
        )
        assert info.level == "warning"
    
    def test_to_dict(self):
        """Test converting AlertInfo to dictionary."""
        timestamp = datetime.now()
        info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=timestamp
        )
        
        info_dict = info.to_dict()
        assert info_dict["app_name"] == "TestApp"
        assert info_dict["message"] == "Test message"
        assert info_dict["level"] == "warning"
        assert info_dict["timestamp"] == timestamp.isoformat()
    
    def test_from_dict(self):
        """Test creating AlertInfo from dictionary."""
        timestamp = datetime.now()
        info_dict = {
            "app_name": "TestApp",
            "message": "Test message",
            "level": "warning",
            "timestamp": timestamp.isoformat(),
            "window_title": "Test Window",
            "window_rect": {"x": 0, "y": 0, "width": 800, "height": 600}
        }
        
        info = AlertInfo.from_dict(info_dict)
        assert info.app_name == "TestApp"
        assert info.message == "Test message"
        assert info.level == AlertLevel.WARNING
        assert info.timestamp.isoformat() == timestamp.isoformat()
        assert info.window_title == "Test Window"
        assert info.window_rect == {"x": 0, "y": 0, "width": 800, "height": 600}


class TestAlertHistoryEntry:
    """Tests for the AlertHistoryEntry dataclass."""
    
    @pytest.fixture
    def sample_alert_info(self):
        """Create a sample AlertInfo instance for testing."""
        return AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            window_title="Test Window"
        )
    
    @pytest.fixture
    def sample_history_entry(self, sample_alert_info):
        """Create a sample AlertHistoryEntry instance for testing."""
        timestamp = datetime.now()
        return AlertHistoryEntry(
            alert_info=sample_alert_info,
            timestamp=timestamp,
            providers_used=["popup", "sound"],
            acknowledged=True,
            acknowledged_time=timestamp
        )
    
    def test_creation(self, sample_history_entry, sample_alert_info):
        """Test creating an AlertHistoryEntry instance."""
        assert sample_history_entry.alert_info == sample_alert_info
        assert isinstance(sample_history_entry.timestamp, datetime)
        assert sample_history_entry.providers_used == ["popup", "sound"]
        assert sample_history_entry.acknowledged is True
        assert isinstance(sample_history_entry.acknowledged_time, datetime)
    
    def test_to_dict(self, sample_alert_info):
        """Test converting AlertHistoryEntry to dictionary."""
        timestamp = datetime.now()
        entry = AlertHistoryEntry(
            alert_info=sample_alert_info,
            timestamp=timestamp,
            providers_used=["popup"],
            acknowledged=True,
            acknowledged_time=timestamp
        )
        
        entry_dict = entry.to_dict()
        
        # Check alert_info is properly converted
        assert entry_dict["alert_info"]["app_name"] == "TestApp"
        assert entry_dict["alert_info"]["message"] == "Test message"
        assert entry_dict["alert_info"]["level"] == "warning"
        
        # Check other fields
        assert entry_dict["timestamp"] == timestamp.isoformat()
        assert entry_dict["providers_used"] == ["popup"]
        assert entry_dict["acknowledged"] is True
        assert entry_dict["acknowledged_time"] == timestamp.isoformat()
    
    def test_from_dict(self):
        """Test creating AlertHistoryEntry from dictionary."""
        timestamp = datetime.now()
        
        # Create a dictionary with nested AlertInfo
        entry_dict = {
            "alert_info": {
                "app_name": "TestApp",
                "message": "Test message",
                "level": "warning",
                "window_title": "Test Window"
            },
            "timestamp": timestamp.isoformat(),
            "providers_used": ["popup", "sound"],
            "acknowledged": True,
            "acknowledged_time": timestamp.isoformat()
        }
        
        entry = AlertHistoryEntry.from_dict(entry_dict)
        
        # Check alert_info
        assert entry.alert_info.app_name == "TestApp"
        assert entry.alert_info.message == "Test message"
        assert entry.alert_info.level == AlertLevel.WARNING
        assert entry.alert_info.window_title == "Test Window"
        
        # Check other fields
        assert entry.timestamp.isoformat() == timestamp.isoformat()
        assert entry.providers_used == ["popup", "sound"]
        assert entry.acknowledged is True
        assert entry.acknowledged_time.isoformat() == timestamp.isoformat()
