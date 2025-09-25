"""
Component wrappers for the Focus Guard coordinator.

This module provides component wrappers for all core modules,
making them available to the coordinator.
"""

from focus_guard.core.coordinator.components.base import BaseComponent
from focus_guard.core.coordinator.components.config import ConfigComponent
from focus_guard.core.coordinator.components.activity import ActivityMonitorComponent
from focus_guard.core.coordinator.components.browser import BrowserIntegrationComponent
from focus_guard.core.coordinator.components.classification import ClassificationComponent
from focus_guard.core.coordinator.components.distraction import DistractionDetectorComponent
from focus_guard.core.coordinator.components.alert import AlertSystemComponent
from focus_guard.core.coordinator.components.api import ApiServerComponent

__all__ = [
    'BaseComponent',
    'ConfigComponent',
    'ActivityMonitorComponent',
    'BrowserIntegrationComponent',
    'ClassificationComponent',
    'DistractionDetectorComponent',
    'AlertSystemComponent',
    'ApiServerComponent',
]
