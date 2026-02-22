"""browser_v2: next-generation browser integration stack for Focus Guard.

This package provides a complete browser extension integration system including:
- Tab server for extension communication
- Installer strategies for different deployment scenarios
- Integration controller for lifecycle management

Quick Start:
    from focus_guard.core.browser_v2 import initialize_browser_integration
    
    controller = initialize_browser_integration()
    controller.install_extension()
    
    # Get current tabs
    tabs = controller.get_tabs()
"""

from .integration import (
    BrowserIntegrationConfig,
    BrowserIntegrationController,
    IntegrationStatus,
    get_browser_integration,
    initialize_browser_integration,
)
from .tab_server import (
    BrowserFamily,
    TabInfo,
    TabsSnapshot,
    ServerState,
)
from .installer import (
    InstallMode,
    InstallStatus,
    detect_browsers,
)

__all__ = [
    # Integration
    "BrowserIntegrationConfig",
    "BrowserIntegrationController",
    "IntegrationStatus",
    "get_browser_integration",
    "initialize_browser_integration",
    # Tab server types
    "BrowserFamily",
    "TabInfo",
    "TabsSnapshot",
    "ServerState",
    # Installer types
    "InstallMode",
    "InstallStatus",
    "detect_browsers",
]
