"""
Activity monitoring module for Focus Guard.

This module provides functionality for monitoring user activity across applications and browser tabs.
"""

from focus_guard.core.activity.models import WindowInfo, ActivityEvent
from focus_guard.core.activity.monitor import ActivityMonitor

__all__ = ['ActivityMonitor', 'WindowInfo', 'ActivityEvent']
