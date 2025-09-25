"""
Tests for distraction detection models.

This module contains tests for the distraction detection models.
"""

import unittest
from datetime import datetime, timedelta

from focus_guard.core.distraction.models import DistractionAlert, DistractionState, AlertLevel


class TestAlertLevel(unittest.TestCase):
    """Tests for the AlertLevel enum."""
    
    def test_alert_level_values(self):
        """Test alert level values."""
        self.assertEqual(AlertLevel.INFO.value, 0)
        self.assertEqual(AlertLevel.WARNING.value, 1)
        self.assertEqual(AlertLevel.CRITICAL.value, 2)
    
    def test_alert_level_comparison(self):
        """Test alert level comparison."""
        self.assertLess(AlertLevel.INFO, AlertLevel.WARNING)
        self.assertLess(AlertLevel.WARNING, AlertLevel.CRITICAL)
        self.assertGreater(AlertLevel.CRITICAL, AlertLevel.INFO)


class TestDistractionAlert(unittest.TestCase):
    """Tests for the DistractionAlert class."""
    
    def test_create_alert(self):
        """Test creating an alert."""
        timestamp = datetime.now()
        alert = DistractionAlert(
            rule_name="Test Rule",
            level=AlertLevel.WARNING,
            message="Test message",
            metadata={"key": "value"},
            timestamp=timestamp
        )
        
        self.assertEqual(alert.rule_name, "Test Rule")
        self.assertEqual(alert.level, AlertLevel.WARNING)
        self.assertEqual(alert.message, "Test message")
        self.assertEqual(alert.metadata, {"key": "value"})
        self.assertEqual(alert.timestamp, timestamp)


class TestDistractionState(unittest.TestCase):
    """Tests for the DistractionState class."""
    
    def test_initial_state(self):
        """Test initial state."""
        state = DistractionState()
        
        self.assertIsNone(state.active_window)
        self.assertEqual(state.top_windows, [])
        self.assertEqual(state.browser_tabs, {})
        self.assertIsNone(state.last_update)
        self.assertEqual(state.distraction_history, [])
    
    def test_update(self):
        """Test updating the state."""
        state = DistractionState()
        
        active_window = {"title": "Test Window", "app_name": "Test App"}
        top_windows = [active_window, {"title": "Another Window", "app_name": "Another App"}]
        
        state.update(active_window, top_windows)
        
        self.assertEqual(state.active_window, active_window)
        self.assertEqual(state.top_windows, top_windows)
        self.assertIsNotNone(state.last_update)
    
    def test_update_browser_tabs(self):
        """Test updating browser tabs."""
        state = DistractionState()
        
        browser_tabs = {
            "active_tab": {"url": "https://example.com", "title": "Example"},
            "all_tabs": [
                {"url": "https://example.com", "title": "Example"},
                {"url": "https://example.org", "title": "Another Example"}
            ]
        }
        
        state.update_browser_tabs(browser_tabs)
        
        self.assertEqual(state.browser_tabs, browser_tabs)
        self.assertIsNotNone(state.last_update)
    
    def test_add_distraction_alert(self):
        """Test adding a distraction alert."""
        state = DistractionState()
        
        alert = DistractionAlert(
            rule_name="Test Rule",
            level=AlertLevel.WARNING,
            message="Test message",
            metadata={"key": "value"},
            timestamp=datetime.now()
        )
        
        state.add_distraction_alert(alert)
        
        self.assertEqual(len(state.distraction_history), 1)
        self.assertEqual(state.distraction_history[0], alert)
    
    def test_is_distracted_no_alerts(self):
        """Test is_distracted with no alerts."""
        state = DistractionState()
        self.assertFalse(state.is_distracted)
    
    def test_is_distracted_recent_alert(self):
        """Test is_distracted with a recent alert."""
        state = DistractionState()
        
        alert = DistractionAlert(
            rule_name="Test Rule",
            level=AlertLevel.WARNING,
            message="Test message",
            metadata={"key": "value"},
            timestamp=datetime.now()
        )
        
        state.add_distraction_alert(alert)
        
        self.assertTrue(state.is_distracted)
    
    def test_is_distracted_old_alert(self):
        """Test is_distracted with an old alert."""
        state = DistractionState()
        
        alert = DistractionAlert(
            rule_name="Test Rule",
            level=AlertLevel.WARNING,
            message="Test message",
            metadata={"key": "value"},
            timestamp=datetime.now() - timedelta(seconds=120)  # 2 minutes ago
        )
        
        state.add_distraction_alert(alert)
        
        self.assertFalse(state.is_distracted)


if __name__ == "__main__":
    unittest.main()
