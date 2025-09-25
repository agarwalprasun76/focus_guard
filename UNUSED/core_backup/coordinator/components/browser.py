"""
Browser integration component for the Focus Guard coordinator.

This module provides a wrapper for the browser integration system, making it
available to the coordinator and other components.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from core_v2.coordinator.components.base import BaseComponent
from core_v2.coordinator.interfaces import EventBus
from core_v2.coordinator.events import EventTypes, EventData
from core_v2.config.interfaces import ConfigurationManager
from core_v2.browser.integration import BrowserIntegration
from core_v2.browser.tab_server import TabServer
from core_v2.browser.models import BrowserTab, BrowserInfo


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
    
    def __init__(self, browser_integration: BrowserIntegration, tab_server: TabServer, 
                 event_bus: EventBus, config_manager: ConfigurationManager):
        """
        Initialize the browser integration component.
        
        Args:
            browser_integration (BrowserIntegration): The browser integration to use.
            tab_server (TabServer): The tab server to use.
            event_bus (EventBus): The event bus to use for communication.
            config_manager (ConfigurationManager): The configuration manager to use.
        """
        super().__init__("browser_integration", event_bus, config_manager)
        self._browser_integration = browser_integration
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
            self._polling_interval = self._config_manager.get(
                "browser_integration.polling_interval_seconds", 
                self._polling_interval
            )
            self._health_check_interval = self._config_manager.get(
                "browser_integration.health_check_interval_seconds", 
                self._health_check_interval
            )
            
            # Initialize the browser integration
            self._logger.info("Initializing browser integration")
            
            # Initialize the tab server
            self._logger.info("Initializing tab server")
            await self._tab_server.initialize()
            
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
            await self._tab_server.start()
            
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
            await self._tab_server.stop()
            
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
            # Shutdown the tab server
            self._logger.info("Shutting down tab server")
            await self._tab_server.shutdown()
            
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
            "tab_server_running": self._tab_server.is_running()
        }
    
    def _is_component_healthy(self) -> bool:
        """
        Check if the component implementation is healthy.
        
        Returns:
            bool: True if the component is healthy, False otherwise.
        """
        # Browser integration is healthy if polling task is running and tab server is running
        polling_healthy = self._polling_task is not None and not self._polling_task.done()
        tab_server_healthy = self._tab_server.is_running()
        
        return polling_healthy and tab_server_healthy
    
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
                    # Get all browser tabs
                    tabs = await self._browser_integration.get_all_tabs()
                    
                    # Track new, updated, and closed tabs
                    current_tab_ids = set()
                    
                    for tab in tabs:
                        tab_id = f"{tab.browser_name}:{tab.window_id}:{tab.tab_id}"
                        current_tab_ids.add(tab_id)
                        
                        if tab_id not in self._known_tabs:
                            # New tab
                            self._known_tabs[tab_id] = tab
                            await self._event_bus.publish(
                                EventTypes.BROWSER_TAB_OPENED,
                                BrowserTabEventData("browser_integration", tab)
                            )
                        else:
                            # Check if tab was updated
                            old_tab = self._known_tabs[tab_id]
                            if (old_tab.url != tab.url or 
                                    old_tab.title != tab.title or
                                    old_tab.favicon_url != tab.favicon_url):
                                self._known_tabs[tab_id] = tab
                                await self._event_bus.publish(
                                    EventTypes.BROWSER_TAB_UPDATED,
                                    BrowserTabEventData("browser_integration", tab)
                                )
                    
                    # Check for closed tabs
                    closed_tab_ids = set(self._known_tabs.keys()) - current_tab_ids
                    for tab_id in closed_tab_ids:
                        tab = self._known_tabs.pop(tab_id)
                        await self._event_bus.publish(
                            EventTypes.BROWSER_TAB_CLOSED,
                            BrowserTabEventData("browser_integration", tab)
                        )
                    
                    # Check extension status
                    browsers = await self._browser_integration.get_detected_browsers()
                    for browser in browsers:
                        is_installed = await self._browser_integration.is_extension_installed(browser.name)
                        is_enabled = await self._browser_integration.is_extension_enabled(browser.name)
                        
                        old_status = self._extension_status.get(browser.name, {})
                        if (old_status.get("is_installed") != is_installed or 
                                old_status.get("is_enabled") != is_enabled):
                            self._extension_status[browser.name] = {
                                "is_installed": is_installed,
                                "is_enabled": is_enabled
                            }
                            await self._event_bus.publish(
                                EventTypes.BROWSER_EXTENSION_STATUS_CHANGED,
                                ExtensionStatusEventData(
                                    "browser_integration", 
                                    browser.name, 
                                    is_installed, 
                                    is_enabled
                                )
                            )
                
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
                    # Check tab server health
                    if not self._tab_server.is_running():
                        self._logger.warning("Tab server is not running, attempting to restart")
                        await self._tab_server.stop()
                        await self._tab_server.start()
                    
                    # Check extension connectivity
                    browsers = await self._browser_integration.get_detected_browsers()
                    for browser in browsers:
                        is_installed = await self._browser_integration.is_extension_installed(browser.name)
                        is_enabled = await self._browser_integration.is_extension_enabled(browser.name)
                        
                        if is_installed and is_enabled:
                            # Check connectivity
                            try:
                                await self._browser_integration.ping_extension(browser.name)
                            except Exception as e:
                                self._logger.warning(f"Failed to ping extension for {browser.name}: {e}")
                                # Could implement recovery logic here
                
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
    
    def get_browser_integration(self) -> BrowserIntegration:
        """
        Get the browser integration.
        
        Returns:
            BrowserIntegration: The browser integration.
        """
        return self._browser_integration
    
    def get_tab_server(self) -> TabServer:
        """
        Get the tab server.
        
        Returns:
            TabServer: The tab server.
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
            
            # Use the browser integration to close the tab via the extension
            success = await self._browser_integration.close_tab(
                tab.browser_name,
                tab.tab_id,
                tab.window_id,
                reason=reason
            )
            
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
            self._logger.exception(f"Error closing tab: {e}")
            return False
