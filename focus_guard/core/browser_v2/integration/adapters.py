"""Adapters for integrating browser_v2 with existing Focus Guard components.

This module provides compatibility layers that allow browser_v2 to work with
the existing Focus Guard blocking, activity monitoring, and coordinator systems.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING

from ..tab_server import (
    get_blocking_manager as get_browser_v2_blocking_manager,
    get_tab_storage,
    BlockingRule,
    BlockingDecision,
    TabInfo,
    BrowserFamily,
)

if TYPE_CHECKING:
    from ..integration.controller import BrowserIntegrationController

logger = logging.getLogger(__name__)

# Default config path for blocking rules
DEFAULT_BLOCKING_CONFIG_PATH = Path.home() / ".focus_guard" / "blocking_config.json"


class CoreBlockingAdapter:
    """Integrates browser_v2 with the full core.blocking.BlockingManager.
    
    This adapter provides:
    - Persistent blocking rules via JSON config files
    - Category-based blocking (SOCIAL_MEDIA, GAMING, etc.)
    - Time-based blocking policies
    - Allowlist support
    - Integration with domain classification
    """
    
    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Initialize the core blocking adapter.
        
        Args:
            config_path: Path to blocking config file. Defaults to ~/.focus_guard/blocking_config.json
        """
        self._config_path = config_path or DEFAULT_BLOCKING_CONFIG_PATH
        self._core_manager: Optional[Any] = None
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize the core blocking manager.
        
        Returns:
            True if initialization succeeded.
        """
        try:
            from focus_guard.core.blocking.manager import BlockingManager
            from focus_guard.core.blocking.policies.domain import DomainBlockingPolicy
            from focus_guard.core.domain.models import Category
            
            # Ensure config directory exists
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create or load the blocking manager
            if self._config_path.exists():
                self._core_manager = BlockingManager(config_path=self._config_path)
                logger.info("Loaded blocking config from %s", self._config_path)
            else:
                self._core_manager = BlockingManager()
                # Save initial config
                self._core_manager.save_config(self._config_path)
                logger.info("Created new blocking config at %s", self._config_path)
            
            self._initialized = True
            return True
            
        except ImportError as e:
            logger.warning("Could not import core.blocking module: %s", e)
            return False
        except Exception as e:
            logger.error("Failed to initialize core blocking manager: %s", e)
            return False
    
    def should_block(self, url: str, domain: str) -> BlockingDecision:
        """Check if a URL/domain should be blocked using core blocking manager.
        
        Args:
            url: Full URL to check.
            domain: Domain extracted from URL.
            
        Returns:
            BlockingDecision with the result.
        """
        if not self._initialized or not self._core_manager:
            return BlockingDecision(should_block=False)
        
        try:
            from focus_guard.core.domain.models import Domain
            
            # Create Domain object for evaluation
            try:
                domain_obj = Domain(domain)
            except Exception:
                # Invalid domain, don't block
                return BlockingDecision(should_block=False)
            
            # Evaluate against core blocking manager
            decision = self._core_manager.should_block(domain_obj, context={"url": url})
            
            return BlockingDecision(
                should_block=decision.should_block,
                reason=decision.reason if decision.should_block else "",
            )
            
        except Exception as e:
            logger.warning("Error checking blocking for %s: %s", domain, e)
            return BlockingDecision(should_block=False)
    
    def add_blocked_domain(self, domain: str, reason: str = "User blocked") -> bool:
        """Add a domain to the block list.
        
        Args:
            domain: Domain to block.
            reason: Reason for blocking.
            
        Returns:
            True if domain was added successfully.
        """
        if not self._initialized or not self._core_manager:
            return False
        
        try:
            # Find or create domain blocking policy
            policy = self._get_or_create_domain_policy()
            if policy:
                policy.add_blocked_domain(domain)
                self._save_config()
                logger.info("Added blocked domain: %s", domain)
                return True
            return False
        except Exception as e:
            logger.error("Failed to add blocked domain %s: %s", domain, e)
            return False
    
    def remove_blocked_domain(self, domain: str) -> bool:
        """Remove a domain from the block list.
        
        Args:
            domain: Domain to unblock.
            
        Returns:
            True if domain was removed successfully.
        """
        if not self._initialized or not self._core_manager:
            return False
        
        try:
            policy = self._get_or_create_domain_policy()
            if policy:
                policy.remove_blocked_domain(domain)
                self._save_config()
                logger.info("Removed blocked domain: %s", domain)
                return True
            return False
        except Exception as e:
            logger.error("Failed to remove blocked domain %s: %s", domain, e)
            return False
    
    def add_blocked_category(self, category_name: str) -> bool:
        """Add a category to block (e.g., 'social_media', 'gaming').
        
        Args:
            category_name: Category name to block.
            
        Returns:
            True if category was added successfully.
        """
        if not self._initialized or not self._core_manager:
            return False
        
        try:
            from focus_guard.core.domain.models import Category
            
            category = Category.from_string(category_name)
            policy = self._get_or_create_domain_policy()
            if policy:
                policy.add_blocked_category(category)
                self._save_config()
                logger.info("Added blocked category: %s", category_name)
                return True
            return False
        except ValueError:
            logger.warning("Unknown category: %s", category_name)
            return False
        except Exception as e:
            logger.error("Failed to add blocked category %s: %s", category_name, e)
            return False
    
    def remove_blocked_category(self, category_name: str) -> bool:
        """Remove a category from blocking.
        
        Args:
            category_name: Category name to unblock.
            
        Returns:
            True if category was removed successfully.
        """
        if not self._initialized or not self._core_manager:
            return False
        
        try:
            from focus_guard.core.domain.models import Category
            
            category = Category.from_string(category_name)
            policy = self._get_or_create_domain_policy()
            if policy:
                policy.remove_blocked_category(category)
                self._save_config()
                logger.info("Removed blocked category: %s", category_name)
                return True
            return False
        except ValueError:
            logger.warning("Unknown category: %s", category_name)
            return False
        except Exception as e:
            logger.error("Failed to remove blocked category %s: %s", category_name, e)
            return False
    
    def add_allowlist_domain(self, domain: str) -> bool:
        """Add a domain to the allowlist (never block).
        
        Args:
            domain: Domain to allowlist.
            
        Returns:
            True if domain was added to allowlist.
        """
        if not self._initialized or not self._core_manager:
            return False
        
        try:
            policy = self._get_or_create_domain_policy()
            if policy:
                policy.add_allowlist_domain(domain)
                self._save_config()
                logger.info("Added allowlist domain: %s", domain)
                return True
            return False
        except Exception as e:
            logger.error("Failed to add allowlist domain %s: %s", domain, e)
            return False
    
    def get_blocked_domains(self) -> Set[str]:
        """Get all explicitly blocked domains.
        
        Returns:
            Set of blocked domain names.
        """
        if not self._initialized or not self._core_manager:
            return set()
        
        try:
            policy = self._get_or_create_domain_policy()
            if policy and hasattr(policy, '_config'):
                return set(policy._config.blocked_domains)
            return set()
        except Exception:
            return set()
    
    def get_blocked_categories(self) -> Set[str]:
        """Get all blocked categories.
        
        Returns:
            Set of blocked category names.
        """
        if not self._initialized or not self._core_manager:
            return set()
        
        try:
            policy = self._get_or_create_domain_policy()
            if policy and hasattr(policy, '_config'):
                return {str(cat) for cat in policy._config.blocked_categories}
            return set()
        except Exception:
            return set()
    
    def get_rules_as_list(self) -> List[Dict[str, str]]:
        """Get all blocking rules as a list of dicts.
        
        Returns:
            List of rule dictionaries with 'domain' and 'reason' keys.
        """
        rules = []
        
        # Add explicit domains
        for domain in self.get_blocked_domains():
            rules.append({"domain": domain, "reason": "User blocked"})
        
        # Add categories
        for category in self.get_blocked_categories():
            rules.append({"domain": f"[category:{category}]", "reason": f"Category: {category}"})
        
        return rules
    
    def _get_or_create_domain_policy(self) -> Optional[Any]:
        """Get or create the domain blocking policy.
        
        Returns:
            DomainBlockingPolicy instance or None.
        """
        if not self._core_manager:
            return None
        
        try:
            from focus_guard.core.blocking.policies.domain import DomainBlockingPolicy
            from focus_guard.core.domain.models import Category
            
            # Look for existing domain policy
            for policy in self._core_manager.get_all_policies():
                if isinstance(policy, DomainBlockingPolicy):
                    return policy
            
            # Create new domain policy
            policy = DomainBlockingPolicy.create(
                name="Browser Extension Blocking",
                blocked_domains=set(),
                blocked_categories=set(),
                allowlist=set(),
                description="Domains blocked via browser extension",
                priority=100,  # High priority
            )
            self._core_manager.add_policy(policy)
            return policy
            
        except Exception as e:
            logger.error("Failed to get/create domain policy: %s", e)
            return None
    
    def _save_config(self) -> None:
        """Save the current config to file."""
        if self._core_manager and self._config_path:
            try:
                self._core_manager.save_config(self._config_path)
            except Exception as e:
                logger.error("Failed to save blocking config: %s", e)


class BlockingAdapter:
    """Adapts Focus Guard's domain blocking to browser_v2's blocking manager.

    This adapter bridges the existing domain classifier and blocking rules
    with the browser_v2 tab server's blocking decision system.
    """

    def __init__(self) -> None:
        self._domain_classifier: Optional[Callable[[str], Dict[str, Any]]] = None
        self._blocked_categories: Set[str] = set()
        self._blocked_domains: Set[str] = set()

    def set_domain_classifier(
        self,
        classifier: Callable[[str], Dict[str, Any]],
    ) -> None:
        """Set the domain classifier function.

        Args:
            classifier: Function that takes a domain and returns classification info.
                Expected to return dict with 'category', 'is_productive', etc.
        """
        self._domain_classifier = classifier
        logger.info("Domain classifier set for blocking adapter")

    def set_blocked_categories(self, categories: set[str]) -> None:
        """Set categories that should be blocked.

        Args:
            categories: Set of category names to block (e.g., {'social_media', 'gaming'}).
        """
        self._blocked_categories = categories
        self._sync_rules()

    def set_blocked_domains(self, domains: set[str]) -> None:
        """Set specific domains that should be blocked.

        Args:
            domains: Set of domain names to block.
        """
        self._blocked_domains = domains
        self._sync_rules()

    def add_blocked_domain(self, domain: str, reason: str = "blocked") -> None:
        """Add a domain to the block list.

        Args:
            domain: Domain to block.
            reason: Reason for blocking.
        """
        self._blocked_domains.add(domain.lower())
        blocking_manager = get_browser_v2_blocking_manager()
        blocking_manager.add_rule(BlockingRule(domain=domain, reason=reason))

    def remove_blocked_domain(self, domain: str) -> None:
        """Remove a domain from the block list.

        Args:
            domain: Domain to unblock.
        """
        self._blocked_domains.discard(domain.lower())
        blocking_manager = get_browser_v2_blocking_manager()
        blocking_manager.remove_rule(domain)

    def check_blocking(self, url: str, domain: str) -> BlockingDecision:
        """Check if a URL/domain should be blocked.

        This method is designed to be used as the external_checker for
        the BlockingManager.

        Args:
            url: Full URL to check.
            domain: Domain extracted from URL.

        Returns:
            BlockingDecision with the result.
        """
        # Check explicit domain block list first
        domain_lower = domain.lower()
        if domain_lower in self._blocked_domains:
            return BlockingDecision(
                should_block=True,
                reason="Domain in block list",
            )

        # Check via domain classifier if available
        if self._domain_classifier:
            try:
                classification = self._domain_classifier(domain)
                category = classification.get("category", "").lower()
                is_productive = classification.get("is_productive", True)

                if category in self._blocked_categories:
                    return BlockingDecision(
                        should_block=True,
                        reason=f"Category blocked: {category}",
                    )

                if not is_productive and "unproductive" in self._blocked_categories:
                    return BlockingDecision(
                        should_block=True,
                        reason="Unproductive domain",
                    )

            except Exception as e:
                logger.warning("Domain classifier error for %s: %s", domain, e)

        return BlockingDecision(should_block=False)

    def _sync_rules(self) -> None:
        """Sync blocked domains to the blocking manager."""
        blocking_manager = get_browser_v2_blocking_manager()
        rules = [
            BlockingRule(domain=domain, reason="blocked")
            for domain in self._blocked_domains
        ]
        blocking_manager.set_rules(rules)


class TabDataAdapter:
    """Adapts browser_v2 tab data for existing Focus Guard components.

    Provides methods to convert between browser_v2's typed tab models and
    the dictionary-based format used by existing components.
    """

    @staticmethod
    def tab_to_dict(tab: TabInfo) -> Dict[str, Any]:
        """Convert TabInfo to dictionary format.

        Args:
            tab: TabInfo instance.

        Returns:
            Dictionary with tab data in legacy format.
        """
        return {
            "id": tab.id,
            "url": tab.url,
            "title": tab.title,
            "browser": tab.browser.value if hasattr(tab.browser, "value") else str(tab.browser),
            "window_id": tab.window_id,
            "active": tab.active,
            "audible": tab.audible,
            "muted": tab.muted,
            "incognito": tab.incognito,
            "last_updated": tab.last_updated,
            **tab.extras,
        }

    @staticmethod
    def dict_to_tab(data: Dict[str, Any]) -> TabInfo:
        """Convert dictionary to TabInfo.

        Args:
            data: Dictionary with tab data.

        Returns:
            TabInfo instance.
        """
        browser_str = data.get("browser", "chrome").lower()
        try:
            browser = BrowserFamily(browser_str)
        except ValueError:
            if "edge" in browser_str:
                browser = BrowserFamily.EDGE
            elif "chrome" in browser_str:
                browser = BrowserFamily.CHROME
            else:
                browser = BrowserFamily.CHROME

        return TabInfo(
            id=str(data.get("id", "")),
            url=data.get("url", ""),
            title=data.get("title", ""),
            browser=browser,
            window_id=str(data.get("window_id", "")) if data.get("window_id") else None,
            active=data.get("active", False),
            audible=data.get("audible", False),
            muted=data.get("muted", False),
            incognito=data.get("incognito", False),
            last_updated=data.get("last_updated"),
        )

    @staticmethod
    def get_all_tabs_as_dicts() -> List[Dict[str, Any]]:
        """Get all tabs as dictionaries.

        Returns:
            List of tab dictionaries.
        """
        storage = get_tab_storage()
        snapshot = storage.get_snapshot()
        return [TabDataAdapter.tab_to_dict(tab) for tab in snapshot.tabs]

    @staticmethod
    def get_active_tab_as_dict() -> Optional[Dict[str, Any]]:
        """Get active tab as dictionary.

        Returns:
            Active tab dictionary or None.
        """
        storage = get_tab_storage()
        active = storage.get_active_tab()
        if active:
            return TabDataAdapter.tab_to_dict(active)
        return None


class EventAdapter:
    """Adapts browser_v2 events for existing Focus Guard event handlers.

    Bridges the real-time events from browser extensions with the existing
    Focus Guard event system.
    """

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Register an event handler.

        Args:
            event_type: Type of event to handle.
            handler: Callback function.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def process_event(self, event: Dict[str, Any]) -> None:
        """Process an event from the extension.

        Args:
            event: Event data from extension.
        """
        event_type = event.get("type", "unknown")
        handlers = self._handlers.get(event_type, [])

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.warning("Event handler error for %s: %s", event_type, e)

        # Also call wildcard handlers
        for handler in self._handlers.get("*", []):
            try:
                handler(event)
            except Exception as e:
                logger.warning("Wildcard event handler error: %s", e)


def create_tabs_updater() -> Callable[[Dict[str, Any]], None]:
    """Create a tabs updater function for the tab server context.

    Returns:
        Function that processes tab updates from extensions.
    """
    def update_tabs(data: Dict[str, Any]) -> None:
        """Process tab update from extension."""
        storage = get_tab_storage()
        
        # Extract browser info
        browser_info = data.get("browser", {})
        browser_name = browser_info.get("name", "").lower() if isinstance(browser_info, dict) else str(browser_info).lower()
        
        if "edge" in browser_name:
            browser = BrowserFamily.EDGE
        elif "chrome" in browser_name:
            browser = BrowserFamily.CHROME
        else:
            browser = BrowserFamily.CHROME

        # Convert tabs
        raw_tabs = data.get("tabs", [])
        tabs = []
        for raw_tab in raw_tabs:
            try:
                tab = TabDataAdapter.dict_to_tab(raw_tab)
                tab.browser = browser  # Override with detected browser
                tabs.append(tab)
            except Exception as e:
                logger.warning("Failed to parse tab: %s", e)

        # Update storage
        storage.update_tabs(tabs, browser)
        logger.debug("Updated %d tabs for %s", len(tabs), browser.value)

    return update_tabs


def wire_blocking_adapter(
    controller: "BrowserIntegrationController",
    adapter: BlockingAdapter,
) -> None:
    """Wire a blocking adapter to the controller.

    Args:
        controller: The browser integration controller.
        adapter: The blocking adapter to use.
    """
    controller.set_blocking_checker(adapter.check_blocking)
    logger.info("Blocking adapter wired to controller")
