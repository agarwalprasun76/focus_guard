"""
Improved browser tab detection using Chrome DevTools Protocol (CDP) and UI Automation.
"""
import json
import re
import socket
import contextlib
from typing import List, Dict, Any, Optional, Set

import psutil
import requests
import uiautomation as auto
from ..base import BrowserInfo, TabInfo

# Configuration for different browsers
BROWSER_CONFIG = {
    "chrome.exe": {
        "family": "chromium",
        "default_cdp_port": 9222,
        "display_name": "Chrome"
    },
    "msedge.exe": {
        "family": "chromium",
        "default_cdp_port": 9223,
        "display_name": "Microsoft Edge"
    },
    "brave.exe": {
        "family": "chromium",
        "default_cdp_port": 9226,
        "display_name": "Brave"
    },
    "opera.exe": {
        "family": "chromium",
        "default_cdp_port": 9227,
        "display_name": "Opera"
    },
    "vivaldi.exe": {
        "family": "chromium",
        "default_cdp_port": 9228,
        "display_name": "Vivaldi"
    },
    "firefox.exe": {
        "family": "firefox",
        "display_name": "Firefox"
    },
}

class BrowserTabDetector:
    """Detect browser tabs using CDP and UI Automation fallback."""
    
    def __init__(self):
        self.processed_windows: Set[int] = set()
    
    @staticmethod
    def _port_is_open(port: int, host: str = "127.0.0.1") -> bool:
        """Check if a port is open on localhost."""
        with contextlib.closing(socket.socket()) as sock:
            sock.settimeout(0.2)
            return sock.connect_ex((host, port)) == 0
    
    @staticmethod
    def _is_private_window(title: str) -> bool:
        """Check if window title indicates private browsing."""
        return bool(re.search(r"\b(Incognito|InPrivate|Private Browsing)\b", title, re.I))
    
    def _fetch_chromium_tabs_via_cdp(self, port: int, browser_name: str) -> List[TabInfo]:
        """Fetch tab information using Chrome DevTools Protocol."""
        try:
            resp = requests.get(f"http://127.0.0.1:{port}/json", timeout=0.5)
            pages = resp.json()
            
            tabs = []
            for page in pages:
                if page.get("type") != "page":
                    continue
                    
                tabs.append(TabInfo(
                    title=page.get("title", ""),
                    url=page.get("url", ""),
                    window_handle=page.get("windowId", 0),
                    is_private=page.get("incognito", False),
                    browser_name=browser_name,
                    source="cdp"
                ))
            return tabs
            
        except Exception as e:
            if __debug__:
                print(f"CDP fetch failed on port {port}: {e}")
            return []
    
    def _fetch_tabs_via_uiautomation(self, process_name: str) -> List[TabInfo]:
        """Fallback to UI Automation when CDP is not available."""
        tabs = []
        try:
            desktop = auto.GetRootControl()
            for win in desktop.GetChildren():
                try:
                    if win.ProcessName.lower() != process_name.lower():
                        continue
                        
                    # Skip if we've already processed this window
                    hwnd = win.NativeWindowHandle
                    if hwnd in self.processed_windows:
                        continue
                        
                    title = win.Name
                    is_private = self._is_private_window(title)
                    
                    # Try to get URL from address bar for better accuracy
                    url = ""
                    try:
                        addrbar = win.Control(searchDepth=4, controlType="Edit")
                        if addrbar:
                            url = addrbar.GetValuePattern().Value or ""
                    except Exception:
                        pass
                    
                    # Clean up title (remove browser name and private mode suffix)
                    clean_title = re.sub(
                        r"\s*-\s*(Google Chrome|Microsoft Edge|Brave|Opera|Vivaldi|Firefox).*$",
                        "", title
                    ).strip()
                    
                    tabs.append(TabInfo(
                        title=clean_title or "Untitled",
                        url=url,
                        window_handle=hwnd,
                        is_private=is_private,
                        browser_name=BROWSER_CONFIG.get(process_name, {}).get("display_name", process_name),
                        source="uia"
                    ))
                    
                    self.processed_windows.add(hwnd)
                    
                except Exception as e:
                    if __debug__:
                        print(f"Error processing window: {e}")
                        
        except Exception as e:
            if __debug__:
                print(f"UI Automation error: {e}")
                
        return tabs
    
    def get_browser_tabs(self) -> List[BrowserInfo]:
        """Get all open browser windows and their tabs."""
        browser_instances: Dict[str, BrowserInfo] = {}
        
        # Find running browser processes
        running_browsers = {}
        for proc in psutil.process_iter(['pid', 'name']):
            proc_name = proc.info['name'].lower()
            if proc_name in BROWSER_CONFIG:
                running_browsers[proc_name] = proc.info
        
        # Process each running browser
        for proc_name, proc_info in running_browsers.items():
            browser_config = BROWSER_CONFIG[proc_name]
            browser_name = browser_config["display_name"]
            pid = proc_info['pid']
            
            # Initialize browser info if not exists
            if browser_name not in browser_instances:
                try:
                    browser_instances[browser_name] = BrowserInfo(
                        name=browser_name,
                        pid=pid,
                        path=psutil.Process(pid).exe(),
                        tabs=[]
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            browser_info = browser_instances[browser_name]
            
            # Try CDP first for Chromium browsers
            if browser_config["family"] == "chromium":
                port = browser_config["default_cdp_port"]
                if self._port_is_open(port):
                    tabs = self._fetch_chromium_tabs_via_cdp(port, browser_name)
                    if tabs:
                        browser_info.tabs.extend(tabs)
                        continue  # Skip UI Automation if CDP worked
            
            # Fall back to UI Automation
            tabs = self._fetch_tabs_via_uiautomation(proc_name)
            if tabs:
                browser_info.tabs.extend(tabs)
        
        return list(browser_instances.values())
