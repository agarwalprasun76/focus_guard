"""Tab server v2 package.

Provides HTTP endpoints for browser extension communication, tab data storage,
and blocking decision logic.
"""

from .api_models import (
    BrowserFamily,
    BrowserStatus,
    CommandRequest,
    CommandResult,
    TabInfo,
    TabsSnapshot,
)
from .blocking import BlockingManager, BlockingRule, BlockingDecision, get_blocking_manager
from .runner import TabServerRunner, ServerState, ServerStatus, get_tab_server_runner
from .server import TabServer, TabServerContext
from .storage import TabStorage, get_tab_storage
from .domain_usage_tracker import (
    DomainUsageTracker,
    DomainRuleConfig,
    DomainDailyStats,
    get_domain_usage_tracker,
)

__all__ = [
    # API Models
    "BrowserFamily",
    "BrowserStatus",
    "CommandRequest",
    "CommandResult",
    "TabInfo",
    "TabsSnapshot",
    # Blocking
    "BlockingManager",
    "BlockingRule",
    "BlockingDecision",
    "get_blocking_manager",
    # Runner
    "TabServerRunner",
    "ServerState",
    "ServerStatus",
    "get_tab_server_runner",
    # Server
    "TabServer",
    "TabServerContext",
    # Storage
    "TabStorage",
    "get_tab_storage",
    # Domain Usage Tracking
    "DomainUsageTracker",
    "DomainRuleConfig",
    "DomainDailyStats",
    "get_domain_usage_tracker",
]
