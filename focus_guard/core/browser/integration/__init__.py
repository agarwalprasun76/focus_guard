"""
Browser integration package.

This package provides integration with browser extensions for tab monitoring and control.
"""

from focus_guard.core.browser.integration.tab_tracker import BrowserTabTracker
from focus_guard.core.browser.integration.tab_blocker import BrowserTabBlocker
from focus_guard.core.browser.integration.browser_integration import BrowserIntegration

__all__ = [
    'BrowserTabTracker',
    'BrowserTabBlocker',
    'BrowserIntegration'
]