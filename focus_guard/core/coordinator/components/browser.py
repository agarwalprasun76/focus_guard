"""
Browser integration component for the Focus Guard coordinator.

This module provides a wrapper for the browser integration system, making it
available to the coordinator and other components.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from focus_guard.core.coordinator.components.base import BaseComponent
from focus_guard.core.coordinator.interfaces import EventBus, Component
from focus_guard.core.coordinator.events import EventTypes, EventData
from focus_guard.core.config.interfaces import ConfigurationManager
from focus_guard.core.browser_v2.tab_server.runner import TabServerRunner
from focus_guard.core.browser.models import BrowserTab, BrowserInfo
from focus_guard.core.tab_server_endpoint import DEFAULT_TAB_SERVER_HOST
from focus_guard.core.tab_server_endpoint import DEFAULT_TAB_SERVER_PORT


def create_browser_component(event_bus: EventBus, config_manager: ConfigurationManager) -> Component:
    """
    Create and configure the browser integration component.
    
    Args:
        event_bus: The event bus for component communication
        config_manager: The configuration manager
        
    Returns:
        Component: The configured browser integration component
    """
    # Get tab server configuration from the config manager
    if hasattr(config_manager, 'get_value'):
        host = config_manager.get_value("browser.tab_server.host", DEFAULT_TAB_SERVER_HOST)
        port = config_manager.get_value("browser.tab_server.port", DEFAULT_TAB_SERVER_PORT)
    else:
        host = config_manager.get("browser.tab_server.host", DEFAULT_TAB_SERVER_HOST)
        port = config_manager.get("browser.tab_server.port", DEFAULT_TAB_SERVER_PORT)
    
    # Use browser_v2 TabServerRunner directly
    tab_server = TabServerRunner(
        host=host,
        port=port,
        auto_restart=True,
    )
    
    # Create and return the component
    return BrowserIntegrationComponent(
        tab_server=tab_server,
        event_bus=event_bus,
        config_manager=config_manager
    )


class TabOpenedEventData(EventData):
    """Event data for tab opened events."""
    
    def __init__(self, source: str, tab_id: int, window_id: int, url: str, title: str, favicon: str = None):
        """
        Initialize the tab opened event data.
        
        Args:
            source (str): The source of the event.
            tab_id (int): The ID of the tab.
            window_id (int): The ID of the window.
            url (str): The URL of the tab.
            title (str): The title of the tab.
            favicon (str, optional): The favicon URL of the tab.
        """
        super().__init__(source)
        self.tab_id = tab_id
        self.window_id = window_id
        self.url = url
        self.title = title
        self.favicon = favicon
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["tab_id"] = self.tab_id
        data["window_id"] = self.window_id
        data["url"] = self.url
        data["title"] = self.title
        data["favicon"] = self.favicon
        return data


class TabUpdatedEventData(EventData):
    """Event data for tab updated events."""
    
    def __init__(self, source: str, tab_id: int, window_id: int, url: str, title: str, favicon: str = None):
        """
        Initialize the tab updated event data.
        
        Args:
            source (str): The source of the event.
            tab_id (int): The ID of the tab.
            window_id (int): The ID of the window.
            url (str): The URL of the tab.
            title (str): The title of the tab.
            favicon (str, optional): The favicon URL of the tab.
        """
        super().__init__(source)
        self.tab_id = tab_id
        self.window_id = window_id
        self.url = url
        self.title = title
        self.favicon = favicon
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["tab_id"] = self.tab_id
        data["window_id"] = self.window_id
        data["url"] = self.url
        data["title"] = self.title
        data["favicon"] = self.favicon
        return data


class TabClosedEventData(EventData):
    """Event data for tab closed events."""
    
    def __init__(self, source: str, tab_id: int, window_id: int, url: str):
        """
        Initialize the tab closed event data.
        
        Args:
            source (str): The source of the event.
            tab_id (int): The ID of the tab.
            window_id (int): The ID of the window.
            url (str): The URL of the tab.
        """
        super().__init__(source)
        self.tab_id = tab_id
        self.window_id = window_id
        self.url = url
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["tab_id"] = self.tab_id
        data["window_id"] = self.window_id
        data["url"] = self.url
        return data


class ExtensionStatusChangedEventData(EventData):
    """Event data for extension status changed events."""
    
    def __init__(self, source: str, installed: bool, enabled: bool, version: str):
        """
        Initialize the extension status changed event data.
        
        Args:
            source (str): The source of the event.
            installed (bool): Whether the extension is installed.
            enabled (bool): Whether the extension is enabled.
            version (str): The version of the extension.
        """
        super().__init__(source)
        self.installed = installed
        self.enabled = enabled
        self.version = version
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["installed"] = self.installed
        data["enabled"] = self.enabled
        data["version"] = self.version
        return data


class BrowserTabEventData(EventData):
    """Event data for browser tab events."""
    
    def __init__(self, source: str, tab: BrowserTab):
        """
        Initialize the browser tab event data.
        
        Args:
            source (str): The source of the event.
            tab (BrowserTab): The browser tab.
        """
        super().__init__(source)
        self.tab = tab
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["tab"] = self.tab.to_dict() if hasattr(self.tab, "to_dict") else str(self.tab)
        return data


class ExtensionStatusEventData(EventData):
    """Event data for extension status events."""
    
    def __init__(self, source: str, browser_name: str, is_installed: bool, is_enabled: bool):
        """
        Initialize the extension status event data.
        
        Args:
            source (str): The source of the event.
            browser_name (str): The name of the browser.
            is_installed (bool): Whether the extension is installed.
            is_enabled (bool): Whether the extension is enabled.
        """
        super().__init__(source)
        self.browser_name = browser_name
        self.is_installed = is_installed
        self.is_enabled = is_enabled
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["browser_name"] = self.browser_name
        data["is_installed"] = self.is_installed
        data["is_enabled"] = self.is_enabled
        return data


class BrowserIntegrationComponent(BaseComponent):
    """
    Component wrapper for the browser integration system.
    
    This component provides access to the browser integration system and
    handles browser events.
    """
    
    def __init__(self, tab_server: TabServerRunner,
                 event_bus: EventBus, config_manager: ConfigurationManager):
        """
        Initialize the browser integration component.
        
        Args:
            tab_server (TabServerRunner): The browser_v2 tab server runner.
            event_bus (EventBus): The event bus to use for communication.
            config_manager (ConfigurationManager): The configuration manager to use.
        """
        super().__init__("browser_integration", event_bus, config_manager)
        self._tab_server = tab_server
        self._polling_task = None
        self._polling_interval = 2.0  # Default polling interval in seconds
        self._known_tabs = {}  # Dictionary of known tabs by tab ID
        self._extension_status = {}  # Dictionary of extension status by browser name
        self._health_check_interval = 60.0  # Default health check interval in seconds
        self._health_check_task = None
    
    async def _initialize_component(self) -> bool:
        """
        Initialize the browser integration component.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            # Configure from settings
            # Handle different config manager interfaces
            if hasattr(self._config_manager, 'get_value'):
                self._polling_interval = self._config_manager.get_value(
                    "browser.polling_interval_seconds", 
                    self._polling_interval
                )
            else:
                self._polling_interval = self._config_manager.get(
                    "browser.polling_interval_seconds", 
                    self._polling_interval
                )
            # Handle different config manager interfaces for health check interval
            if hasattr(self._config_manager, 'get_value'):
                self._health_check_interval = self._config_manager.get_value(
                    "browser_integration.health_check_interval_seconds", 
                    self._health_check_interval
                )
            else:
                self._health_check_interval = self._config_manager.get(
                    "browser_integration.health_check_interval_seconds", 
                    self._health_check_interval
                )
            
            # Initialize the browser integration
            self._logger.info("Initializing browser integration")
            
            # Tab server doesn't need explicit initialization - it's ready after construction
            self._logger.info("Tab server ready")
            
            return True
        except Exception as e:
            self._logger.exception(f"Error initializing browser integration: {e}")
            return False
    
    async def _start_component(self) -> bool:
        """
        Start the browser integration component.
        
        Returns:
            bool: True if startup was successful, False otherwise.
        """
        try:
            # Start the tab server
            self._logger.info("Starting tab server")
            self._tab_server.start()
            
            # Start polling for browser tabs
            self._polling_task = asyncio.create_task(self._poll_browser_tabs())
            
            # Start health check
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self._logger.info("Browser integration started")
            return True
        except Exception as e:
            self._logger.exception(f"Error starting browser integration: {e}")
            return False
    
    async def _stop_component(self) -> bool:
        """
        Stop the browser integration component.
        
        Returns:
            bool: True if stopping was successful, False otherwise.
        """
        try:
            # Stop polling for browser tabs
            if self._polling_task is not None:
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass
                self._polling_task = None
            
            # Stop health check
            if self._health_check_task is not None:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
                self._health_check_task = None
            
            # Stop the tab server
            self._logger.info("Stopping tab server")
            self._tab_server.stop()
            
            self._logger.info("Browser integration stopped")
            return True
        except Exception as e:
            self._logger.exception(f"Error stopping browser integration: {e}")
            return False
    
    async def _shutdown_component(self) -> bool:
        """
        Shutdown the browser integration component.
        
        Returns:
            bool: True if shutdown was successful, False otherwise.
        """
        try:
            # Stop the tab server (TabServer uses stop() not shutdown())
            self._logger.info("Stopping tab server")
            self._tab_server.stop()
            
            return True
        except Exception as e:
            self._logger.exception(f"Error shutting down browser integration: {e}")
            return False
    
    def _get_component_status(self) -> Dict[str, Any]:
        """
        Get the component-specific status.
        
        Returns:
            Dict[str, Any]: A dictionary containing the component's status information.
        """
        return {
            "polling_interval": self._polling_interval,
            "tab_count": len(self._known_tabs),
            "extension_status": self._extension_status,
            "tab_server_running": self._tab_server.is_running
        }
    
    def _is_component_healthy(self) -> bool:
        """
        Check if the component implementation is healthy.
        
        Returns:
            bool: True if the component is healthy, False otherwise.
        """
        # Browser integration is healthy if polling task is running and tab server is running
        polling_healthy = self._polling_task is not None and not self._polling_task.done()
        tab_server_healthy = self._tab_server.is_running
        
        return polling_healthy and tab_server_healthy
    
    async def _publish_tab_event(self, event_type: str, tab_data: Dict[str, Any]) -> None:
        """
        Publish a tab event to the event bus.
        
        Args:
            event_type: The type of event (TAB_OPENED, TAB_UPDATED, TAB_CLOSED)
            tab_data: The tab data dictionary
        """
        try:
            if self._event_bus:
                event_data = {
                    'tab_id': tab_data.get('id'),
                    'url': tab_data.get('url'),
                    'title': tab_data.get('title'),
                    'window_id': tab_data.get('windowId'),
                    'active': tab_data.get('active', False),
                    'timestamp': tab_data.get('timestamp')
                }
                await self._event_bus.publish(event_type, event_data)
        except Exception as e:
            self._logger.error(f"Error publishing tab event {event_type}: {e}")
    
    async def _poll_browser_tabs(self) -> None:
        """
        Poll for browser tabs.
        
        This method runs in a loop, polling for browser tabs and
        publishing events when tabs are opened, closed, or updated.
        """
        self._logger.debug("Starting browser tab polling")
        
        try:
            while True:
                try:
                    # The tab server handles tab tracking via the extension.
                    # We just check health here; actual tab events come through the server.
                    tabs = []  # Tab polling now handled by browser_v2 tab server
                    
                    # Track current tab IDs for closed tab detection
                    current_tab_ids = set()
                    
                    # Process each tab and publish events for new/updated/closed tabs
                    for tab in tabs:
                        tab_id = tab.get('tab_id') or tab.get('id')
                        tab_url = tab.get('url', '')
                        tab_title = tab.get('title', '')
                        
                        # Ensure tab_id is hashable (not a dict)
                        if isinstance(tab_id, dict):
                            # If tab_id is a dict, use a string representation or specific field
                            tab_id = str(tab_id.get('id', tab_id))
                        
                        # Add to current tab IDs
                        current_tab_ids.add(tab_id)
                        
                        # Extract domain for logging
                        domain = self._extract_domain_from_url(tab_url) if tab_url else 'unknown'
                        
                        if tab_id not in self._known_tabs:
                            # New tab opened
                            self._logger.info(f" NEW TAB: {domain} | {tab_url[:80]}{'...' if len(tab_url) > 80 else ''}")
                            
                            # Trigger domain classification and blocking check for new tabs
                            if tab_url and domain != 'unknown':
                                await self._check_tab_blocking(tab_url, domain, tab_title)
                            
                            # Store the new tab
                            try:
                                self._known_tabs[tab_id] = tab
                                self._logger.debug(f"Successfully stored tab {tab_id} in known_tabs")
                            except Exception as e:
                                self._logger.error(f"Failed to store tab {tab_id} in known_tabs: {e}")
                                # Continue anyway - the tab will be processed but not stored
                            await self._publish_tab_event(EventTypes.TAB_OPENED, tab)
                        elif self._known_tabs[tab_id] != tab:
                            # Tab updated (URL or title changed)
                            prev_url = self._known_tabs[tab_id].get('url', '')
                            if prev_url != tab_url:
                                self._logger.info(f" TAB UPDATED: {domain} | {tab_url[:80]}{'...' if len(tab_url) > 80 else ''}")
                                
                                # Trigger domain classification and blocking check for updated tabs
                                if tab_url and domain != 'unknown':
                                    await self._check_tab_blocking(tab_url, domain, tab_title)
                            
                            # Store the updated tab
                            self._known_tabs[tab_id] = tab
                            await self._publish_tab_event(EventTypes.TAB_UPDATED, tab)
                    
                    # Check for closed tabs
                    closed_tab_ids = set(self._known_tabs.keys()) - current_tab_ids
                    for tab_id in closed_tab_ids:
                        tab = self._known_tabs.pop(tab_id)
                        tab_url = tab.get('url') if isinstance(tab, dict) else getattr(tab, 'url', 'unknown')
                        self._logger.info(f"TAB CLOSED: {tab_url}")
                        await self._event_bus.publish(
                            EventTypes.TAB_CLOSED,
                            BrowserTabEventData("browser_integration", tab)
                        )
                    
                    # Check extension status - simplified for now
                    # TODO: Implement proper browser detection and extension status checking
                    pass
                
                except Exception as e:
                    self._logger.exception(f"Error polling browser tabs: {e}")
                
                # Wait for next poll
                await asyncio.sleep(self._polling_interval)
        
        except asyncio.CancelledError:
            self._logger.debug("Browser tab polling cancelled")
            raise
    
    async def _health_check_loop(self) -> None:
        """
        Perform periodic health checks on the browser integration.
        
        This method runs in a loop, checking the health of the browser
        integration and attempting to recover if necessary.
        """
        self._logger.debug("Starting browser integration health check loop")
        
        try:
            while True:
                try:
                    # Check tab server health via the runner's property
                    if not self._tab_server.is_running:
                        self._logger.warning("Tab server is not running, attempting to restart")
                        self._tab_server.stop()
                        self._tab_server.start()
                    else:
                        self._logger.debug("Health check: tab server is running")
                
                except Exception as e:
                    self._logger.exception(f"Error in browser integration health check: {e}")
                
                # Wait for next health check
                await asyncio.sleep(self._health_check_interval)
        
        except asyncio.CancelledError:
            self._logger.debug("Browser integration health check cancelled")
            raise
    
    async def _handle_config_changed(self, event_data: Any) -> None:
        """
        Handle a configuration change event.
        
        Args:
            event_data (Any): The event data.
        """
        path = event_data.path
        new_value = event_data.new_value
        
        if path == "browser_integration.polling_interval_seconds":
            self._polling_interval = new_value
            self._logger.info(f"Updated polling interval to {new_value} seconds")
        
        elif path == "browser_integration.health_check_interval_seconds":
            self._health_check_interval = new_value
            self._logger.info(f"Updated health check interval to {new_value} seconds")
    
    def get_tab_server(self) -> TabServerRunner:
        """
        Get the tab server runner.
        
        Returns:
            TabServerRunner: The browser_v2 tab server runner.
        """
        return self._tab_server
    
    async def close_tab(self, tab: BrowserTab, reason: str = "user_action") -> bool:
        """
        Close a browser tab.
        
        This method uses the browser extension approach instead of CDP,
        as outlined in the implementation plan.
        
        Args:
            tab (BrowserTab): The tab to close.
            reason (str, optional): The reason for closing the tab. Defaults to "user_action".
            
        Returns:
            bool: True if the tab was closed successfully, False otherwise.
        """
        try:
            self._logger.info(f"Closing tab {tab.tab_id} in {tab.browser_name}: {tab.url}")
            
            # Tab closing is handled by the browser extension's blocking mechanism.
            # The tab server sends block responses and the extension redirects to blocked.html.
            self._logger.info(f"Tab close requested for {tab.url} — handled by extension blocking")
            success = True  # Blocking is handled at the extension level
            
            if success:
                # Remove from known tabs
                tab_id = f"{tab.browser_name}:{tab.window_id}:{tab.tab_id}"
                if tab_id in self._known_tabs:
                    self._known_tabs.pop(tab_id)
                
                # Publish tab closed event
                await self._event_bus.publish(
                    EventTypes.BROWSER_TAB_CLOSED,
                    BrowserTabEventData("browser_integration", tab)
                )
            
            return success
            
        except Exception as e:
            self._logger.error(f"Error closing single tab {tab_id}: {e}")
            return False
    
    def _extract_domain_from_url(self, url: str) -> str:
        """Extract domain from URL for logging purposes."""
        try:
            from focus_guard.core.domain.utils import extract_domain_from_url
            domain = extract_domain_from_url(url)
            return domain or 'unknown'
        except Exception:
            return 'unknown'
    
    async def _check_tab_blocking(self, url: str, domain: str, title: str = ""):
        """Check if a tab should be blocked using the existing API functionality."""
        try:
            # Import the API to check blocking
            from focus_guard.core.api.api import api
            
            # Create metadata for context-aware classification
            from datetime import datetime
            metadata = {
                'url': url,
                'title': title,
                'timestamp': datetime.now().isoformat(),
                'domain': domain
            }
            
            self._logger.info(f"CHECKING BLOCKING for {domain} | {url}")
            
            # Use combined method to get all blocking details in a single call
            blocking_result = await api.check_blocking_with_details(url, metadata)
            
            self._logger.info(f"BLOCKING DECISION for {domain}: {blocking_result.should_block}")
            
            if blocking_result.should_block:
                reason = blocking_result.reason or 'Policy violation'
                self._logger.info(f"BLOCKING TAB: {domain} - {reason}")
                
                # Find and close the tab by URL
                await self._close_tab_by_url(url, reason)
            else:
                self._logger.info(f"ALLOWING TAB: {domain}")
            
        except Exception as e:
            self._logger.error(f"Error checking tab blocking for {domain}: {e}", exc_info=True)
    
    async def _close_tab_by_url(self, url: str, reason: str):
        """Request tab closure by URL.

        In browser_v2, blocking is handled at the tab server / extension level:
        the extension checks each navigation against the tab server's blocking
        API and redirects to blocked.html when appropriate.  This method just
        logs the intent and removes the tab from the local known-tabs cache.
        """
        self._logger.info(f"Block requested for {url}: {reason}")
        domain = self._extract_domain_from_url(url)

        for tab_id, tab in list(self._known_tabs.items()):
            tab_url = tab.get('url') if isinstance(tab, dict) else getattr(tab, 'url', None)
            if tab_url == url or (tab_url and self._extract_domain_from_url(tab_url) == domain):
                self._logger.info(f"Removing blocked tab {tab_id} from known tabs")
                self._known_tabs.pop(tab_id, None)
                return True

        self._logger.debug(f"Tab for {url} not in local cache — extension handles blocking directly")
        return True
