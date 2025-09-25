"""
Mock Browser Extension for Integration Testing.

This module simulates browser extension behavior for testing tab server communication,
command execution, and the complete tab blocking pipeline without requiring a real browser.
"""

import asyncio
import json
import time
import logging
import requests
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from threading import Thread, Event
import uuid

logger = logging.getLogger(__name__)


@dataclass
class MockTab:
    """Mock tab data structure matching browser extension format."""
    id: int
    windowId: int
    url: str
    title: str
    active: bool
    status: str = "complete"
    favIconUrl: Optional[str] = None
    incognito: bool = False
    pinned: bool = False
    audible: bool = False
    mutedInfo: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class MockBrowserInfo:
    """Mock browser information."""
    name: str
    version: str
    extension_id: str
    user_agent: str = "MockBrowser/1.0"


class MockBrowserExtension:
    """
    Mock browser extension that simulates real extension behavior.
    
    Provides:
    - Tab data reporting to tab server
    - Command polling from tab server
    - Tab closing simulation
    - Event generation for testing
    """
    
    def __init__(self, 
                 tab_server_url: str = "http://localhost:5000",
                 browser_info: Optional[MockBrowserInfo] = None,
                 polling_interval: float = 1.0):
        """
        Initialize mock browser extension.
        
        Args:
            tab_server_url: URL of the tab server to communicate with
            browser_info: Browser information for identification
            polling_interval: How often to poll for commands (seconds)
        """
        self.tab_server_url = tab_server_url.rstrip('/')
        self.browser_info = browser_info or MockBrowserInfo(
            name="MockChrome",
            version="120.0.0.0",
            extension_id="mock-extension-id-12345"
        )
        self.polling_interval = polling_interval
        
        # Internal state
        self._tabs: Dict[int, MockTab] = {}
        self._active_tab_id: Optional[int] = None
        self._window_id = 1
        self._next_tab_id = 1
        self._running = Event()
        self._polling_thread: Optional[Thread] = None
        
        # Event callbacks
        self._tab_created_callbacks: List[Callable[[MockTab], None]] = []
        self._tab_updated_callbacks: List[Callable[[MockTab], None]] = []
        self._tab_closed_callbacks: List[Callable[[int], None]] = []
        self._command_received_callbacks: List[Callable[[Dict], None]] = []
        
        # Statistics
        self.stats = {
            "tabs_created": 0,
            "tabs_closed": 0,
            "commands_received": 0,
            "server_requests": 0,
            "errors": 0
        }
    
    def start(self) -> bool:
        """Start the mock extension (begin polling for commands)."""
        if self._running.is_set():
            logger.warning("Mock extension is already running")
            return True
        
        try:
            # Test connection to tab server
            response = requests.get(f"{self.tab_server_url}/api/status", timeout=5)
            if response.status_code != 200:
                logger.error(f"Tab server not responding: {response.status_code}")
                return False
            
            self._running.set()
            self._polling_thread = Thread(target=self._polling_loop, daemon=True)
            self._polling_thread.start()
            
            logger.info(f"Mock browser extension started, polling {self.tab_server_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start mock extension: {e}")
            return False
    
    def stop(self):
        """Stop the mock extension."""
        if not self._running.is_set():
            return
        
        self._running.clear()
        if self._polling_thread:
            self._polling_thread.join(timeout=2)
        
        logger.info("Mock browser extension stopped")
    
    def create_tab(self, url: str, title: str = None, active: bool = False) -> MockTab:
        """Create a new mock tab."""
        tab_id = self._next_tab_id
        self._next_tab_id += 1
        
        tab = MockTab(
            id=tab_id,
            windowId=self._window_id,
            url=url,
            title=title or f"Tab {tab_id}",
            active=active
        )
        
        self._tabs[tab_id] = tab
        if active:
            self._active_tab_id = tab_id
        
        self.stats["tabs_created"] += 1
        
        # Notify callbacks
        for callback in self._tab_created_callbacks:
            try:
                callback(tab)
            except Exception as e:
                logger.error(f"Error in tab created callback: {e}")
        
        # Send tab data to server
        self._send_tab_data()
        
        logger.debug(f"Created mock tab {tab_id}: {url}")
        return tab
    
    def update_tab(self, tab_id: int, url: str = None, title: str = None, active: bool = None) -> bool:
        """Update an existing mock tab."""
        if tab_id not in self._tabs:
            logger.warning(f"Tab {tab_id} not found for update")
            return False
        
        tab = self._tabs[tab_id]
        updated = False
        
        if url is not None and url != tab.url:
            tab.url = url
            updated = True
        
        if title is not None and title != tab.title:
            tab.title = title
            updated = True
        
        if active is not None and active != tab.active:
            tab.active = active
            if active:
                # Deactivate other tabs
                for other_tab in self._tabs.values():
                    if other_tab.id != tab_id:
                        other_tab.active = False
                self._active_tab_id = tab_id
            updated = True
        
        if updated:
            # Notify callbacks
            for callback in self._tab_updated_callbacks:
                try:
                    callback(tab)
                except Exception as e:
                    logger.error(f"Error in tab updated callback: {e}")
            
            # Send updated tab data to server
            self._send_tab_data()
            logger.debug(f"Updated mock tab {tab_id}: {tab.url}")
        
        return updated
    
    def close_tab(self, tab_id: int) -> bool:
        """Close a mock tab."""
        if tab_id not in self._tabs:
            logger.warning(f"Tab {tab_id} not found for closing")
            return False
        
        tab = self._tabs.pop(tab_id)
        
        # If this was the active tab, activate another one
        if self._active_tab_id == tab_id:
            self._active_tab_id = None
            if self._tabs:
                # Activate the first available tab
                first_tab = next(iter(self._tabs.values()))
                first_tab.active = True
                self._active_tab_id = first_tab.id
        
        self.stats["tabs_closed"] += 1
        
        # Notify callbacks
        for callback in self._tab_closed_callbacks:
            try:
                callback(tab_id)
            except Exception as e:
                logger.error(f"Error in tab closed callback: {e}")
        
        # Send updated tab data to server
        self._send_tab_data()
        
        logger.debug(f"Closed mock tab {tab_id}")
        return True
    
    def get_tabs(self) -> List[MockTab]:
        """Get all current tabs."""
        return list(self._tabs.values())
    
    def get_active_tab(self) -> Optional[MockTab]:
        """Get the currently active tab."""
        if self._active_tab_id and self._active_tab_id in self._tabs:
            return self._tabs[self._active_tab_id]
        return None
    
    def _send_tab_data(self):
        """Send current tab data to the tab server."""
        try:
            tab_data = {
                "tabs": [tab.to_dict() for tab in self._tabs.values()],
                "browser": {
                    "name": self.browser_info.name,
                    "version": self.browser_info.version,
                    "extension_id": self.browser_info.extension_id,
                    "user_agent": self.browser_info.user_agent
                },
                "timestamp": time.time(),
                "active_tab_id": self._active_tab_id
            }
            
            response = requests.post(
                f"{self.tab_server_url}/api/tabs",
                json=tab_data,
                timeout=5
            )
            
            self.stats["server_requests"] += 1
            
            if response.status_code != 200:
                logger.warning(f"Tab server returned {response.status_code}: {response.text}")
                self.stats["errors"] += 1
            
        except Exception as e:
            logger.error(f"Failed to send tab data to server: {e}")
            self.stats["errors"] += 1
    
    def _polling_loop(self):
        """Main polling loop for commands from tab server."""
        logger.debug("Started command polling loop")
        
        while self._running.is_set():
            try:
                # Poll for commands
                response = requests.get(
                    f"{self.tab_server_url}/api/command",
                    params={"browser_id": self.browser_info.extension_id},
                    timeout=5
                )
                
                self.stats["server_requests"] += 1
                
                if response.status_code == 200:
                    data = response.json()
                    commands = data.get("commands", [])
                    
                    for command in commands:
                        self._process_command(command)
                
                elif response.status_code != 204:  # 204 = no commands
                    logger.warning(f"Command polling returned {response.status_code}")
                    self.stats["errors"] += 1
                
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                self.stats["errors"] += 1
            
            # Wait before next poll
            time.sleep(self.polling_interval)
        
        logger.debug("Command polling loop stopped")
    
    def _process_command(self, command: Dict[str, Any]):
        """Process a command from the tab server."""
        try:
            command_type = command.get("action")
            self.stats["commands_received"] += 1
            
            logger.debug(f"Processing command: {command_type}")
            
            if command_type == "close_tab":
                tab_id = command.get("data", {}).get("tabId")
                if tab_id:
                    self.close_tab(int(tab_id))
            
            elif command_type == "block_tab":
                # For blocking, we simulate by closing the tab
                tab_id = command.get("data", {}).get("tabId")
                if tab_id:
                    logger.info(f"Blocking tab {tab_id} (simulated as close)")
                    self.close_tab(int(tab_id))
            
            elif command_type == "navigate_tab":
                tab_id = command.get("data", {}).get("tabId")
                new_url = command.get("data", {}).get("url")
                if tab_id and new_url:
                    self.update_tab(int(tab_id), url=new_url)
            
            else:
                logger.warning(f"Unknown command type: {command_type}")
            
            # Notify callbacks
            for callback in self._command_received_callbacks:
                try:
                    callback(command)
                except Exception as e:
                    logger.error(f"Error in command received callback: {e}")
            
        except Exception as e:
            logger.error(f"Error processing command {command}: {e}")
            self.stats["errors"] += 1
    
    # Event callback registration methods
    def on_tab_created(self, callback: Callable[[MockTab], None]):
        """Register callback for tab creation events."""
        self._tab_created_callbacks.append(callback)
    
    def on_tab_updated(self, callback: Callable[[MockTab], None]):
        """Register callback for tab update events."""
        self._tab_updated_callbacks.append(callback)
    
    def on_tab_closed(self, callback: Callable[[int], None]):
        """Register callback for tab close events."""
        self._tab_closed_callbacks.append(callback)
    
    def on_command_received(self, callback: Callable[[Dict], None]):
        """Register callback for command reception events."""
        self._command_received_callbacks.append(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extension statistics."""
        return {
            **self.stats,
            "tabs_count": len(self._tabs),
            "active_tab_id": self._active_tab_id,
            "running": self._running.is_set()
        }


class MockBrowserScenario:
    """
    Helper class for creating realistic browser usage scenarios for testing.
    """
    
    def __init__(self, extension: MockBrowserExtension):
        self.extension = extension
    
    def simulate_browsing_session(self, duration: float = 10.0):
        """Simulate a realistic browsing session."""
        scenarios = [
            self._productivity_session,
            self._entertainment_session,
            self._mixed_session,
            self._social_media_session
        ]
        
        import random
        scenario = random.choice(scenarios)
        scenario(duration)
    
    def _productivity_session(self, duration: float):
        """Simulate a productivity-focused browsing session."""
        sites = [
            ("https://github.com/user/repo", "GitHub Repository"),
            ("https://stackoverflow.com/questions/123", "Stack Overflow Question"),
            ("https://docs.google.com/document/123", "Google Docs"),
            ("https://www.notion.so/workspace", "Notion Workspace")
        ]
        
        self._simulate_session(sites, duration, "productivity")
    
    def _entertainment_session(self, duration: float):
        """Simulate an entertainment-focused browsing session."""
        sites = [
            ("https://www.youtube.com/watch?v=abc123", "YouTube Video"),
            ("https://www.netflix.com/watch/123", "Netflix Show"),
            ("https://www.twitch.tv/streamer", "Twitch Stream"),
            ("https://www.reddit.com/r/funny", "Reddit Funny")
        ]
        
        self._simulate_session(sites, duration, "entertainment")
    
    def _social_media_session(self, duration: float):
        """Simulate a social media browsing session."""
        sites = [
            ("https://www.facebook.com/feed", "Facebook Feed"),
            ("https://twitter.com/home", "Twitter Home"),
            ("https://www.instagram.com/", "Instagram Feed"),
            ("https://www.linkedin.com/feed", "LinkedIn Feed")
        ]
        
        self._simulate_session(sites, duration, "social_media")
    
    def _mixed_session(self, duration: float):
        """Simulate a mixed browsing session."""
        sites = [
            ("https://github.com/project", "GitHub"),
            ("https://www.youtube.com/watch?v=xyz", "YouTube"),
            ("https://news.ycombinator.com", "Hacker News"),
            ("https://www.facebook.com", "Facebook"),
            ("https://docs.python.org", "Python Docs")
        ]
        
        self._simulate_session(sites, duration, "mixed")
    
    def _simulate_session(self, sites: List[tuple], duration: float, session_type: str):
        """Simulate a browsing session with given sites."""
        logger.info(f"Starting {session_type} browsing session for {duration}s")
        
        start_time = time.time()
        site_index = 0
        
        while time.time() - start_time < duration:
            if site_index < len(sites):
                url, title = sites[site_index]
                tab = self.extension.create_tab(url, title, active=True)
                logger.debug(f"Opened {url}")
                site_index += 1
            else:
                # Update existing tabs or close some
                tabs = self.extension.get_tabs()
                if tabs:
                    import random
                    if random.random() < 0.3:  # 30% chance to close a tab
                        tab_to_close = random.choice(tabs)
                        self.extension.close_tab(tab_to_close.id)
                    else:  # Update a tab
                        tab_to_update = random.choice(tabs)
                        new_url, new_title = random.choice(sites)
                        self.extension.update_tab(tab_to_update.id, url=new_url, title=new_title)
            
            # Wait between actions
            time.sleep(min(2.0, duration / 10))
        
        logger.info(f"Completed {session_type} browsing session")


# Test utilities
def create_test_extension(tab_server_port: int = 5000) -> MockBrowserExtension:
    """Create a mock extension for testing."""
    return MockBrowserExtension(
        tab_server_url=f"http://localhost:{tab_server_port}",
        browser_info=MockBrowserInfo(
            name="TestChrome",
            version="120.0.0.0",
            extension_id=f"test-extension-{uuid.uuid4().hex[:8]}"
        ),
        polling_interval=0.5  # Faster polling for tests
    )


async def wait_for_tab_server(url: str, timeout: float = 10.0) -> bool:
    """Wait for tab server to be ready."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/api/status", timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        
        await asyncio.sleep(0.5)
    
    return False


if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)
    
    extension = create_test_extension()
    
    if extension.start():
        print("Mock extension started. Creating test tabs...")
        
        # Create some test tabs
        extension.create_tab("https://github.com/test/repo", "Test Repository", active=True)
        extension.create_tab("https://www.youtube.com/watch?v=test", "Test Video")
        extension.create_tab("https://www.facebook.com", "Facebook")
        
        print(f"Created {len(extension.get_tabs())} tabs")
        print(f"Active tab: {extension.get_active_tab().url if extension.get_active_tab() else 'None'}")
        
        # Run for a bit
        time.sleep(5)
        
        print(f"Stats: {extension.get_stats()}")
        extension.stop()
    else:
        print("Failed to start mock extension")
