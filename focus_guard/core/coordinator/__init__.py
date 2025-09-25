"""
Focus Guard Coordinator Module.

This module provides the central coordination point for all Focus Guard components,
managing their lifecycle, communication, and health monitoring.
"""

from focus_guard.core.coordinator.interfaces import Component, Coordinator, EventBus, EventListener
from focus_guard.core.coordinator.lifecycle import ComponentLifecycleManager
from focus_guard.core.coordinator.events import DefaultEventBus
from focus_guard.core.coordinator.focus_guard_coordinator import FocusGuardCoordinator
from focus_guard.core.coordinator.components import (
    BaseComponent,
    ConfigComponent,
    ActivityMonitorComponent,
    BrowserIntegrationComponent,
    ClassificationComponent,
    DistractionDetectorComponent,
    AlertSystemComponent,
    ApiServerComponent,
)

__all__ = [
    # Core interfaces
    'Component',
    'Coordinator',
    'EventBus',
    'EventListener',
    
    # Core implementation
    'ComponentLifecycleManager',
    'DefaultEventBus',
    'FocusGuardCoordinator',
    
    # Component wrappers
    'BaseComponent',
    'ConfigComponent',
    'ActivityMonitorComponent',
    'BrowserIntegrationComponent',
    'ClassificationComponent',
    'DistractionDetectorComponent',
    'AlertSystemComponent',
    'ApiServerComponent',
]
