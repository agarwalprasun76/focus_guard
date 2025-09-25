"""
Alert system module.

This module re-exports the AlertSystem class from alert_system.py for
compatibility with the coordinator components.
"""

from focus_guard.core.alert.alert_system import AlertSystem

# Re-export AlertSystem
__all__ = ['AlertSystem']
