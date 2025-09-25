"""
Activity monitoring module for Focus Guard.

This module provides functionality for monitoring user activity across applications and browser tabs.
"""

from core_v2.activity.models import WindowInfo, ActivityEvent
from core_v2.activity.monitor import ActivityMonitor

__all__ = ['ActivityMonitor', 'WindowInfo', 'ActivityEvent']
