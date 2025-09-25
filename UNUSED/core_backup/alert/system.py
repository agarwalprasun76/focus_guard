"""
Alert system module.

This module re-exports the AlertSystem class from alert_system.py for
compatibility with the coordinator components.
"""

from core_v2.alert.alert_system import AlertSystem

# Re-export AlertSystem
__all__ = ['AlertSystem']
