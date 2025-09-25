"""
Launcher for the extension installation guide.

This module provides functions to launch the extension installation guide
from various parts of the application.
"""

import os
import sys
import logging
import threading
from typing import Optional

from focus_guard.core.browser.models.browser import BrowserType
from focus_guard.core.browser.extension.user_installation.ui import launch_installation_guide

logger = logging.getLogger(__name__)


def launch_guide_for_browser(browser_type: BrowserType, extension_dir: Optional[str] = None):
    """Launch the installation guide for a specific browser.
    
    Args:
        browser_type: Type of browser to install extension for
        extension_dir: Path to the extension directory. If None, will use default.
    """
    from focus_guard.core.browser.extension.user_installation.guide import ExtensionInstallationGuide
    
    guide = ExtensionInstallationGuide(extension_dir)
    guide.start_installation_guide(browser_type)


def launch_guide_async(extension_dir: Optional[str] = None):
    """Launch the installation guide UI in a separate thread.
    
    Args:
        extension_dir: Path to the extension directory. If None, will use default.
    """
    thread = threading.Thread(
        target=launch_installation_guide,
        args=(extension_dir,),
        daemon=True
    )
    thread.start()
    return thread


if __name__ == "__main__":
    # When run directly, launch the full UI
    logging.basicConfig(level=logging.INFO)
    launch_installation_guide()
