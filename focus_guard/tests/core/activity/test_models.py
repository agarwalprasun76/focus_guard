"""
Unit tests for the activity monitor models.

This module contains unit tests for the WindowInfo and ActivityEvent classes
defined in core.activity.models.
"""

import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

from focus_guard.core.activity.models import WindowInfo, ActivityEvent


class TestWindowInfo(unittest.TestCase):
    """Tests for the WindowInfo class."""
    
    def test_init(self):
        """Test WindowInfo initialization with basic fields."""
        window_info = WindowInfo(
            app_name="test_app",
            window_title="Test Window",
            pid="12345"
        )
        
        self.assertEqual(window_info.app_name, "test_app")
        self.assertEqual(window_info.window_title, "Test Window")
        self.assertEqual(window_info.pid, "12345")
        self.assertIsInstance(window_info.timestamp, datetime)
        self.assertIsNone(window_info.hwnd)
        self.assertIsNone(window_info.rect)
        self.assertIsNone(window_info.area)
        self.assertIsNone(window_info.percent)
        self.assertIsNone(window_info.url)
        self.assertIsNone(window_info.domain)
    
    def test_from_dict_basic(self):
        """Test WindowInfo.from_dict with basic fields."""
        data = {
            "app_name": "test_app",
            "window_title": "Test Window",
            "pid": "12345",
            "timestamp": "2025-07-26T11:30:00"
        }
        
        window_info = WindowInfo.from_dict(data)
        
        self.assertEqual(window_info.app_name, "test_app")
        self.assertEqual(window_info.window_title, "Test Window")
        self.assertEqual(window_info.pid, "12345")
        self.assertEqual(window_info.timestamp.isoformat(), "2025-07-26T11:30:00")
    
    def test_from_dict_with_url(self):
        """Test WindowInfo.from_dict with URL field."""
        data = {
            "app_name": "chrome",
            "window_title": "Test Page - Google Chrome",
            "pid": "12345",
            "url": "https://example.com/test"
        }
        
        with patch("focus_guard.core.domain.domain_utils_new.create_url_from_string") as mock_create_url:
            mock_url = MagicMock()
            mock_url.domain = MagicMock()
            mock_create_url.return_value = mock_url
            
            window_info = WindowInfo.from_dict(data)
            
            mock_create_url.assert_called_once_with("https://example.com/test")
            self.assertEqual(window_info.url, mock_url)
            self.assertEqual(window_info.domain, mock_url.domain)
    
    def test_to_dict_basic(self):
        """Test WindowInfo.to_dict with basic fields."""
        timestamp = datetime(2025, 7, 26, 11, 30, 0)
        window_info = WindowInfo(
            app_name="test_app",
            window_title="Test Window",
            pid="12345",
            timestamp=timestamp
        )
        
        result = window_info.to_dict()
        
        self.assertEqual(result["app_name"], "test_app")
        self.assertEqual(result["window_title"], "Test Window")
        self.assertEqual(result["pid"], "12345")
        self.assertEqual(result["timestamp"], "2025-07-26T11:30:00")
        self.assertNotIn("hwnd", result)
        self.assertNotIn("rect", result)
        self.assertNotIn("area", result)
        self.assertNotIn("percent", result)
        self.assertNotIn("url", result)
        self.assertNotIn("domain", result)
    
    def test_to_dict_with_optional_fields(self):
        """Test WindowInfo.to_dict with optional fields."""
        timestamp = datetime(2025, 7, 26, 11, 30, 0)
        window_info = WindowInfo(
            app_name="test_app",
            window_title="Test Window",
            pid="12345",
            timestamp=timestamp,
            hwnd=67890,
            rect=(0, 0, 100, 100),
            area=10000,
            percent=0.5
        )
        
        mock_url = MagicMock()
        mock_url.__str__.return_value = "https://example.com/test"
        window_info.url = mock_url
        
        mock_domain = MagicMock()
        mock_domain.__str__.return_value = "example.com"
        window_info.domain = mock_domain
        
        result = window_info.to_dict()
        
        self.assertEqual(result["app_name"], "test_app")
        self.assertEqual(result["window_title"], "Test Window")
        self.assertEqual(result["pid"], "12345")
        self.assertEqual(result["timestamp"], "2025-07-26T11:30:00")
        self.assertEqual(result["hwnd"], 67890)
        self.assertEqual(result["rect"], (0, 0, 100, 100))
        self.assertEqual(result["area"], 10000)
        self.assertEqual(result["percent"], 0.5)
        self.assertEqual(result["url"], "https://example.com/test")
        self.assertEqual(result["domain"], "example.com")


class TestActivityEvent(unittest.TestCase):
    """Tests for the ActivityEvent class."""
    
    def test_init(self):
        """Test ActivityEvent initialization with basic fields."""
        event = ActivityEvent(event_type="window_activated")
        
        self.assertEqual(event.event_type, "window_activated")
        self.assertIsInstance(event.timestamp, datetime)
        self.assertIsNone(event.window_info)
        self.assertEqual(event.metadata, {})
    
    def test_init_with_window_info(self):
        """Test ActivityEvent initialization with window_info."""
        window_info = WindowInfo(
            app_name="test_app",
            window_title="Test Window",
            pid="12345"
        )
        
        event = ActivityEvent(
            event_type="window_activated",
            window_info=window_info,
            metadata={"duration": 60}
        )
        
        self.assertEqual(event.event_type, "window_activated")
        self.assertEqual(event.window_info, window_info)
        self.assertEqual(event.metadata, {"duration": 60})
    
    def test_to_dict_basic(self):
        """Test ActivityEvent.to_dict with basic fields."""
        timestamp = datetime(2025, 7, 26, 11, 30, 0)
        event = ActivityEvent(
            event_type="window_activated",
            timestamp=timestamp,
            metadata={"duration": 60}
        )
        
        result = event.to_dict()
        
        self.assertEqual(result["event_type"], "window_activated")
        self.assertEqual(result["timestamp"], "2025-07-26T11:30:00")
        self.assertEqual(result["metadata"], {"duration": 60})
        self.assertNotIn("window_info", result)
    
    def test_to_dict_with_window_info(self):
        """Test ActivityEvent.to_dict with window_info."""
        timestamp = datetime(2025, 7, 26, 11, 30, 0)
        window_info = WindowInfo(
            app_name="test_app",
            window_title="Test Window",
            pid="12345"
        )
        
        event = ActivityEvent(
            event_type="window_activated",
            timestamp=timestamp,
            window_info=window_info
        )
        
        with patch.object(window_info, "to_dict") as mock_to_dict:
            mock_to_dict.return_value = {"app_name": "test_app"}
            
            result = event.to_dict()
            
            mock_to_dict.assert_called_once()
            self.assertEqual(result["event_type"], "window_activated")
            self.assertEqual(result["timestamp"], "2025-07-26T11:30:00")
            self.assertEqual(result["window_info"], {"app_name": "test_app"})
    
    def test_from_dict_basic(self):
        """Test ActivityEvent.from_dict with basic fields."""
        data = {
            "event_type": "window_activated",
            "timestamp": "2025-07-26T11:30:00",
            "metadata": {"duration": 60}
        }
        
        event = ActivityEvent.from_dict(data)
        
        self.assertEqual(event.event_type, "window_activated")
        self.assertEqual(event.timestamp.isoformat(), "2025-07-26T11:30:00")
        self.assertEqual(event.metadata, {"duration": 60})
        self.assertIsNone(event.window_info)
    
    def test_from_dict_with_window_info(self):
        """Test ActivityEvent.from_dict with window_info."""
        data = {
            "event_type": "window_activated",
            "timestamp": "2025-07-26T11:30:00",
            "window_info": {
                "app_name": "test_app",
                "window_title": "Test Window",
                "pid": "12345"
            }
        }
        
        with patch("focus_guard.core.activity.models.WindowInfo.from_dict") as mock_from_dict:
            mock_window_info = MagicMock()
            mock_from_dict.return_value = mock_window_info
            
            event = ActivityEvent.from_dict(data)
            
            mock_from_dict.assert_called_once_with(data["window_info"])
            self.assertEqual(event.event_type, "window_activated")
            self.assertEqual(event.timestamp.isoformat(), "2025-07-26T11:30:00")
            self.assertEqual(event.window_info, mock_window_info)


if __name__ == "__main__":
    unittest.main()
