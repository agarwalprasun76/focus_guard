"""
Browser integration package.

This package provides integration with browser extensions for tab monitoring and control.
"""

from core_v2.browser.integration.tab_tracker import BrowserTabTracker
from core_v2.browser.integration.tab_blocker import BrowserTabBlocker
from core_v2.browser.integration.browser_integration import BrowserIntegration

__all__ = [
    'BrowserTabTracker',
    'BrowserTabBlocker',
    'BrowserIntegration'
]