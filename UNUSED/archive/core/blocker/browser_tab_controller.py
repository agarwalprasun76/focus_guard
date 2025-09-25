#!/usr/bin/env python
"""
Browser Tab Controller

This module provides a high-level interface for controlling browser tabs across different
browser instances (Chrome, Edge). It handles browser detection, tab mapping, and tab control
operations.
"""

import os
import sys
import logging
import subprocess
import time
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple

# Import the Chrome DevTools client
from core.blocker.chrome_devtools_client import ChromeDevToolsClient

# Setup logging
logger = logging.getLogger("browser_tab_controller")


class BrowserTabController:
    """
    Controller for browser tabs across different browser instances.
    
    This class provides functionality to:
    1. Detect running browser instances
    2. Map between FocusGuard tab IDs and browser-specific tab IDs
    3. Close tabs by URL, domain, or ID
    4. Handle multiple browser instances
    """
    
    # Known browser executable names
    CHROME_EXECUTABLES = ["chrome.exe", "chrome"]
    EDGE_EXECUTABLES = ["msedge.exe", "msedge"]
    
    # Default debugging ports
    DEFAULT_PORTS = {
        "chrome": 9222,
        "edge": 9223
    }
    
    def __init__(self, auto_detect: bool = True):
        """
        Initialize the Browser Tab Controller.
        
        Args:
            auto_detect: If True, automatically detect running browser instances
        """
        self.clients = {}  # Store CDP clients by browser type and port
        self.detected_browsers = {}  # Store detected browser info
        
        if auto_detect:
            self.detect_browsers()
            
        logger.info(f"Initialized Browser Tab Controller")
    
    def detect_browsers(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect running browser instances with debugging enabled.
        
        Returns:
            Dictionary mapping browser types to lists of browser instances
        """
        self.detected_browsers = {
            "chrome": [],
            "edge": []
        }
        
        # Look for Chrome instances
        chrome_instances = self._find_browser_processes(self.CHROME_EXECUTABLES)
        for instance in chrome_instances:
            if self._is_debugging_enabled(instance, self.DEFAULT_PORTS["chrome"]):
                self.detected_browsers["chrome"].append({
                    "pid": instance["pid"],
                    "port": self.DEFAULT_PORTS["chrome"],
                    "executable": instance["executable"]
                })
                
                # Create a CDP client for this instance
                self._create_client("chrome", self.DEFAULT_PORTS["chrome"])
        
        # Look for Edge instances
        edge_instances = self._find_browser_processes(self.EDGE_EXECUTABLES)
        for instance in edge_instances:
            if self._is_debugging_enabled(instance, self.DEFAULT_PORTS["edge"]):
                self.detected_browsers["edge"].append({
                    "pid": instance["pid"],
                    "port": self.DEFAULT_PORTS["edge"],
                    "executable": instance["executable"]
                })
                
                # Create a CDP client for this instance
                self._create_client("edge", self.DEFAULT_PORTS["edge"])
        
        # Log detection results
        chrome_count = len(self.detected_browsers["chrome"])
        edge_count = len(self.detected_browsers["edge"])
        logger.info(f"Detected {chrome_count} Chrome and {edge_count} Edge instances with debugging enabled")
        
        return self.detected_browsers
    
    def _find_browser_processes(self, executable_names: List[str]) -> List[Dict[str, Any]]:
        """
        Find running processes that match the given executable names.
        
        Args:
            executable_names: List of executable names to look for
            
        Returns:
            List of dictionaries with process information
        """
        browser_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_info = proc.info
                proc_name = proc_info['name'].lower() if proc_info['name'] else ""
                
                if any(exe.lower() in proc_name for exe in executable_names):
                    cmdline = proc_info.get('cmdline', [])
                    browser_processes.append({
                        "pid": proc_info['pid'],
                        "executable": proc_name,
                        "cmdline": cmdline
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return browser_processes
    
    def _is_debugging_enabled(self, process_info: Dict[str, Any], port: int) -> bool:
        """
        Check if a browser process has remote debugging enabled on the specified port.
        
        Args:
            process_info: Dictionary with process information
            port: The port to check for remote debugging
            
        Returns:
            bool: True if debugging is enabled, False otherwise
        """
        cmdline = process_info.get("cmdline", [])
        
        # Check for remote debugging flag and port
        for i, arg in enumerate(cmdline):
            if arg == "--remote-debugging-port" and i < len(cmdline) - 1:
                try:
                    debug_port = int(cmdline[i + 1])
                    return debug_port == port
                except (ValueError, IndexError):
                    pass
            elif arg.startswith("--remote-debugging-port="):
                try:
                    debug_port = int(arg.split("=")[1])
                    return debug_port == port
                except (ValueError, IndexError):
                    pass
        
        return False
    
    def _create_client(self, browser_type: str, port: int) -> Optional[ChromeDevToolsClient]:
        """
        Create a CDP client for a specific browser type and port.
        
        Args:
            browser_type: Type of browser ("chrome" or "edge")
            port: Debugging port
            
        Returns:
            ChromeDevToolsClient instance or None if creation failed
        """
        client_key = f"{browser_type}:{port}"
        
        if client_key in self.clients:
            return self.clients[client_key]
        
        try:
            client = ChromeDevToolsClient(port=port)
            if client.is_chrome_available():
                self.clients[client_key] = client
                logger.info(f"Created CDP client for {browser_type} on port {port}")
                return client
            else:
                logger.warning(f"Failed to connect to {browser_type} on port {port}")
                return None
        except Exception as e:
            logger.error(f"Error creating CDP client for {browser_type} on port {port}: {e}")
            return None
    
    def get_all_tabs(self) -> List[Dict[str, Any]]:
        """
        Get a list of all tabs across all detected browser instances.
        
        Returns:
            List of tab information dictionaries with browser type added
        """
        all_tabs = []
        
        for client_key, client in self.clients.items():
            browser_type = client_key.split(":")[0]
            try:
                tabs = client.get_tabs()
                
                # Add browser type to each tab
                for tab in tabs:
                    tab["browser_type"] = browser_type
                    all_tabs.append(tab)
                    
            except Exception as e:
                logger.error(f"Error getting tabs from {client_key}: {e}")
        
        logger.info(f"Found {len(all_tabs)} tabs across all browser instances")
        return all_tabs
    
    def find_tab_by_url(self, url_pattern: str) -> Optional[Dict[str, Any]]:
        """
        Find a tab by URL pattern across all browser instances.
        
        Args:
            url_pattern: String pattern to match against tab URLs
            
        Returns:
            Tab information dictionary or None if not found
        """
        for client_key, client in self.clients.items():
            browser_type = client_key.split(":")[0]
            try:
                tab = client.find_tab_by_url(url_pattern)
                if tab:
                    tab["browser_type"] = browser_type
                    return tab
            except Exception as e:
                logger.error(f"Error finding tab by URL in {client_key}: {e}")
        
        return None
    
    def find_tab_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Find a tab by domain across all browser instances.
        
        Args:
            domain: Domain to match against tab URLs
            
        Returns:
            Tab information dictionary or None if not found
        """
        # For simple domain matching, we'll just look for the domain in the URL
        return self.find_tab_by_url(domain)
    
    def close_tab(self, tab_info: Dict[str, Any]) -> bool:
        """
        Close a specific tab based on its information.
        
        Args:
            tab_info: Tab information dictionary with at least "id" and "browser_type"
            
        Returns:
            bool: True if successful, False otherwise
        """
        if "id" not in tab_info or "browser_type" not in tab_info:
            logger.error("Tab info missing required fields (id, browser_type)")
            return False
        
        tab_id = tab_info["id"]
        browser_type = tab_info["browser_type"]
        port = self.DEFAULT_PORTS.get(browser_type, 9222)
        
        client_key = f"{browser_type}:{port}"
        client = self.clients.get(client_key)
        
        if not client:
            logger.error(f"No CDP client available for {browser_type} on port {port}")
            return False
        
        try:
            success = client.close_tab(tab_id)
            if success:
                logger.info(f"Successfully closed tab {tab_id} in {browser_type}")
            else:
                logger.warning(f"Failed to close tab {tab_id} in {browser_type}")
            return success
        except Exception as e:
            logger.error(f"Error closing tab {tab_id} in {browser_type}: {e}")
            return False
    
    def close_tab_by_url(self, url_pattern: str) -> bool:
        """
        Close a tab that matches the given URL pattern.
        
        Args:
            url_pattern: String pattern to match against tab URLs
            
        Returns:
            bool: True if a tab was found and closed, False otherwise
        """
        tab = self.find_tab_by_url(url_pattern)
        if tab:
            return self.close_tab(tab)
        return False
    
    def close_tab_by_domain(self, domain: str) -> bool:
        """
        Close a tab that matches the given domain.
        
        Args:
            domain: Domain to match against tab URLs
            
        Returns:
            bool: True if a tab was found and closed, False otherwise
        """
        return self.close_tab_by_url(domain)
    
    def map_focus_guard_tab(self, focus_guard_tab: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Map a FocusGuard tab to a browser-specific tab.
        
        Args:
            focus_guard_tab: FocusGuard tab information
                {
                    "tab_id": int,
                    "window_id": int,
                    "url": str,
                    "domain": str,
                    "title": str (optional)
                }
                
        Returns:
            Browser-specific tab information or None if not found
        """
        if "url" not in focus_guard_tab and "domain" not in focus_guard_tab:
            logger.error("FocusGuard tab missing URL or domain")
            return None
        
        # Try to find by URL first
        if "url" in focus_guard_tab:
            tab = self.find_tab_by_url(focus_guard_tab["url"])
            if tab:
                return tab
        
        # Try to find by domain as fallback
        if "domain" in focus_guard_tab:
            tab = self.find_tab_by_domain(focus_guard_tab["domain"])
            if tab:
                return tab
        
        logger.warning(f"Could not map FocusGuard tab to browser tab: {focus_guard_tab.get('url', focus_guard_tab.get('domain', 'Unknown'))}")
        return None
    
    def close_focus_guard_tab(self, focus_guard_tab: Dict[str, Any]) -> bool:
        """
        Close a tab based on FocusGuard tab information.
        
        Args:
            focus_guard_tab: FocusGuard tab information
                
        Returns:
            bool: True if successful, False otherwise
        """
        browser_tab = self.map_focus_guard_tab(focus_guard_tab)
        if browser_tab:
            return self.close_tab(browser_tab)
        return False
    
    def launch_chrome_with_debugging(self, port: int = 9222) -> bool:
        """
        Launch Chrome with remote debugging enabled.
        
        Args:
            port: The port to use for remote debugging
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Try to find Chrome executable
            chrome_path = None
            
            # Common locations on Windows
            if sys.platform == "win32":
                possible_paths = [
                    os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
                    os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe")
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        chrome_path = path
                        break
            
            # Common locations on macOS
            elif sys.platform == "darwin":
                possible_paths = [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        chrome_path = path
                        break
            
            # Common locations on Linux
            else:
                possible_paths = [
                    "/usr/bin/google-chrome",
                    "/usr/bin/chromium-browser",
                    "/usr/bin/chromium"
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        chrome_path = path
                        break
            
            if not chrome_path:
                logger.error("Could not find Chrome executable")
                return False
            
            # Launch Chrome with remote debugging
            cmd = [
                chrome_path,
                f"--remote-debugging-port={port}",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            
            subprocess.Popen(cmd)
            logger.info(f"Launched Chrome with remote debugging on port {port}")
            
            # Wait for Chrome to start and create a client
            time.sleep(2)
            self._create_client("chrome", port)
            
            return True
            
        except Exception as e:
            logger.error(f"Error launching Chrome with debugging: {e}")
            return False
    
    def close_all_connections(self):
        """
        Close all CDP client connections.
        """
        for client_key, client in self.clients.items():
            try:
                client.close_all_connections()
                logger.debug(f"Closed connections for {client_key}")
            except Exception as e:
                logger.error(f"Error closing connections for {client_key}: {e}")


# Simple test function
def test_browser_tab_controller():
    """
    Test the Browser Tab Controller functionality.
    """
    controller = BrowserTabController()
    
    # Check if any browsers were detected
    if not controller.clients:
        print("No browsers with debugging enabled were detected.")
        print("Would you like to launch Chrome with debugging? (y/n)")
        choice = input().lower()
        if choice == 'y':
            controller.launch_chrome_with_debugging()
        else:
            print("Please start Chrome with: chrome.exe --remote-debugging-port=9222")
            return
    
    # List all tabs
    tabs = controller.get_all_tabs()
    print(f"Found {len(tabs)} tabs across all browsers:")
    for i, tab in enumerate(tabs):
        browser = tab.get("browser_type", "Unknown")
        print(f"{i+1}. [{browser}] {tab.get('title', 'Unknown')} - {tab.get('url', 'No URL')}")
    
    # Close a tab by URL pattern (if any tabs exist)
    if tabs:
        url_pattern = input("Enter URL pattern to close (or press Enter to skip): ")
        if url_pattern:
            success = controller.close_tab_by_url(url_pattern)
            print(f"Tab close {'succeeded' if success else 'failed'}")
    
    # Clean up
    controller.close_all_connections()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    test_browser_tab_controller()
