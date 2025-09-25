"""
Component wrappers for the Focus Guard coordinator.

This module provides component wrappers for all core modules,
making them available to the coordinator.
"""

from core_v2.coordinator.components.base import BaseComponent
from core_v2.coordinator.components.config import ConfigComponent
from core_v2.coordinator.components.activity import ActivityMonitorComponent
from core_v2.coordinator.components.browser import BrowserIntegrationComponent
from core_v2.coordinator.components.classification import ClassificationComponent
from core_v2.coordinator.components.distraction import DistractionDetectorComponent
from core_v2.coordinator.components.alert import AlertSystemComponent
from core_v2.coordinator.components.api import ApiServerComponent

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
