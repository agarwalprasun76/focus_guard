"""
Focus Guard Coordinator Module.

This module provides the central coordination point for all Focus Guard components,
managing their lifecycle, communication, and health monitoring.
"""

from core_v2.coordinator.interfaces import Component, Coordinator, EventBus, EventListener
from core_v2.coordinator.lifecycle import ComponentLifecycleManager
from core_v2.coordinator.events import DefaultEventBus
from core_v2.coordinator.focus_guard_coordinator import FocusGuardCoordinator
from core_v2.coordinator.components import (
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
