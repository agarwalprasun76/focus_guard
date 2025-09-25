"""
Unit tests for alert system models.

This module contains tests for the alert system data models.
"""

import unittest
import time
import json
from dataclasses import asdict

from core_v2.alert.models import AlertLevel, AlertInfo, AlertHistoryEntry


class TestAlertLevel(unittest.TestCase):
    """Tests for the AlertLevel enum."""
    
    def test_from_string(self):
        """Test converting strings to AlertLevel."""
        self.assertEqual(AlertLevel.from_string("normal"), AlertLevel.NORMAL)
        self.assertEqual(AlertLevel.from_string("NORMAL"), AlertLevel.NORMAL)
        self.assertEqual(AlertLevel.from_string("warning"), AlertLevel.WARNING)
        self.assertEqual(AlertLevel.from_string("WARNING"), AlertLevel.WARNING)
        self.assertEqual(AlertLevel.from_string("critical"), AlertLevel.CRITICAL)
        self.assertEqual(AlertLevel.from_string("CRITICAL"), AlertLevel.CRITICAL)
        
        # Test invalid values
        with self.assertRaises(ValueError):
            AlertLevel.from_string("invalid")
    
    def test_to_string(self):
        """Test converting AlertLevel to string."""
        self.assertEqual(AlertLevel.NORMAL.to_string(), "normal")
        self.assertEqual(AlertLevel.WARNING.to_string(), "warning")
        self.assertEqual(AlertLevel.CRITICAL.to_string(), "critical")
    
    def test_comparison(self):
        """Test comparing AlertLevel values."""
        self.assertLess(AlertLevel.NORMAL.value, AlertLevel.WARNING.value)
        self.assertLess(AlertLevel.WARNING.value, AlertLevel.CRITICAL.value)
        self.assertGreater(AlertLevel.CRITICAL.value, AlertLevel.NORMAL.value)


class TestAlertInfo(unittest.TestCase):
    """Tests for the AlertInfo dataclass."""
    
    def test_creation(self):
        """Test creating an AlertInfo instance."""
        from datetime import datetime
        timestamp = datetime.now()
        info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=timestamp,
            window_title="Test Window",
            window_rect={"x": 0, "y": 0, "width": 800, "height": 600}
        )
        
        self.assertEqual(info.app_name, "TestApp")
        self.assertEqual(info.message, "Test message")
        self.assertEqual(info.level, AlertLevel.WARNING)
        self.assertEqual(info.timestamp, timestamp)
        self.assertEqual(info.window_title, "Test Window")
        self.assertEqual(info.window_rect, {"x": 0, "y": 0, "width": 800, "height": 600})
    
    def test_creation_with_string_level(self):
        """Test creating an AlertInfo with string level."""
        info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level="warning"
        )
        
        self.assertEqual(info.level, "warning")
    
    def test_to_dict(self):
        """Test converting AlertInfo to dictionary."""
        from datetime import datetime
        timestamp = datetime.now()
        info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=timestamp
        )
        
        info_dict = info.to_dict()
        self.assertEqual(info_dict["app_name"], "TestApp")
        self.assertEqual(info_dict["message"], "Test message")
        self.assertEqual(info_dict["level"], "warning")
        self.assertEqual(info_dict["timestamp"], timestamp.isoformat())
    
    def test_from_dict(self):
        """Test creating AlertInfo from dictionary."""
        from datetime import datetime
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
        self.assertEqual(info.app_name, "TestApp")
        self.assertEqual(info.message, "Test message")
        self.assertEqual(info.level, AlertLevel.WARNING)
        # Compare string representations since datetime objects might have microsecond differences
        self.assertEqual(info.timestamp.isoformat(), timestamp.isoformat())
        self.assertEqual(info.window_title, "Test Window")
        self.assertEqual(info.window_rect, {"x": 0, "y": 0, "width": 800, "height": 600})


class TestAlertHistoryEntry(unittest.TestCase):
    """Tests for the AlertHistoryEntry dataclass."""
    
    def test_creation(self):
        """Test creating an AlertHistoryEntry instance."""
        from datetime import datetime
        timestamp = datetime.now()
        
        # Create AlertInfo first
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            window_title="Test Window"
        )
        
        # Create AlertHistoryEntry with the AlertInfo
        entry = AlertHistoryEntry(
            alert_info=alert_info,
            timestamp=timestamp,
            providers_used=["popup", "sound"],
            acknowledged=True,
            acknowledged_time=timestamp
        )
        
        self.assertEqual(entry.alert_info, alert_info)
        self.assertEqual(entry.timestamp, timestamp)
        self.assertEqual(entry.providers_used, ["popup", "sound"])
        self.assertTrue(entry.acknowledged)
        self.assertEqual(entry.acknowledged_time, timestamp)
    
    def test_to_dict(self):
        """Test converting AlertHistoryEntry to dictionary."""
        from datetime import datetime
        timestamp = datetime.now()
        
        # Create AlertInfo first
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING
        )
        
        # Create AlertHistoryEntry with the AlertInfo
        entry = AlertHistoryEntry(
            alert_info=alert_info,
            timestamp=timestamp,
            providers_used=["popup"],
            acknowledged=True,
            acknowledged_time=timestamp
        )
        
        entry_dict = entry.to_dict()
        
        # Check alert_info is properly converted
        self.assertEqual(entry_dict["alert_info"]["app_name"], "TestApp")
        self.assertEqual(entry_dict["alert_info"]["message"], "Test message")
        self.assertEqual(entry_dict["alert_info"]["level"], "warning")
        
        # Check other fields
        self.assertEqual(entry_dict["timestamp"], timestamp.isoformat())
        self.assertEqual(entry_dict["providers_used"], ["popup"])
        self.assertTrue(entry_dict["acknowledged"])
        self.assertEqual(entry_dict["acknowledged_time"], timestamp.isoformat())
    
    def test_from_dict(self):
        """Test creating AlertHistoryEntry from dictionary."""
        from datetime import datetime
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
        
        # Check AlertInfo was properly created
        self.assertEqual(entry.alert_info.app_name, "TestApp")
        self.assertEqual(entry.alert_info.message, "Test message")
        self.assertEqual(entry.alert_info.level, AlertLevel.WARNING)
        self.assertEqual(entry.alert_info.window_title, "Test Window")
        
        # Check other fields
        self.assertEqual(entry.timestamp.isoformat(), timestamp.isoformat())
        self.assertEqual(entry.providers_used, ["popup", "sound"])
        self.assertTrue(entry.acknowledged)
        self.assertEqual(entry.acknowledged_time.isoformat(), timestamp.isoformat())
    
    def test_json_serialization(self):
        """Test JSON serialization and deserialization."""
        from datetime import datetime
        timestamp = datetime.now()
        
        # Create AlertInfo first
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING
        )
        
        # Create AlertHistoryEntry with the AlertInfo
        entry = AlertHistoryEntry(
            alert_info=alert_info,
            timestamp=timestamp,
            providers_used=["popup"],
            acknowledged=False
        )
        
        # Serialize to JSON
        json_str = json.dumps(entry.to_dict())
        
        # Deserialize from JSON
        entry_dict = json.loads(json_str)
        new_entry = AlertHistoryEntry.from_dict(entry_dict)
        
        # Check AlertInfo was properly serialized/deserialized
        self.assertEqual(new_entry.alert_info.app_name, entry.alert_info.app_name)
        self.assertEqual(new_entry.alert_info.message, entry.alert_info.message)
        self.assertEqual(new_entry.alert_info.level, entry.alert_info.level)
        
        # Check other fields
        self.assertEqual(new_entry.timestamp.isoformat(), entry.timestamp.isoformat())
        self.assertEqual(new_entry.providers_used, entry.providers_used)
        self.assertEqual(new_entry.acknowledged, entry.acknowledged)


if __name__ == "__main__":
    unittest.main()
