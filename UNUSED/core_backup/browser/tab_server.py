"""
Re-export of the TabServer class from the extension module.

This module provides a convenient import location for the TabServer class,
which is actually implemented in core_v2.browser.extension.tab_server.
"""

# Re-export the TabServer class and related functions
from core_v2.browser.extension.tab_server import (
    TabServer,
    get_tab_server,
    start_tab_server,
    stop_tab_server,
    is_running
)

__all__ = ['TabServer', 'get_tab_server', 'start_tab_server', 'stop_tab_server', 'is_running']
