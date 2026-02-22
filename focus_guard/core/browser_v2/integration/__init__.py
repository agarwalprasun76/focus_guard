"""Browser integration package.

Provides the main controller for coordinating browser extension installation,
tab server lifecycle, and extension communication.
"""

from .controller import (
    BrowserIntegrationConfig,
    BrowserIntegrationController,
    IntegrationStatus,
    get_browser_integration,
    initialize_browser_integration,
)
from .adapters import (
    CoreBlockingAdapter,
    BlockingAdapter,
    TabDataAdapter,
    EventAdapter,
    create_tabs_updater,
    wire_blocking_adapter,
    DEFAULT_BLOCKING_CONFIG_PATH,
)

__all__ = [
    # Controller
    "BrowserIntegrationConfig",
    "BrowserIntegrationController",
    "IntegrationStatus",
    "get_browser_integration",
    "initialize_browser_integration",
    # Adapters
    "CoreBlockingAdapter",
    "BlockingAdapter",
    "TabDataAdapter",
    "EventAdapter",
    "create_tabs_updater",
    "wire_blocking_adapter",
    "DEFAULT_BLOCKING_CONFIG_PATH",
]
