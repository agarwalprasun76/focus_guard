#!/usr/bin/env python
"""Browser Tab Blocker: Functionality to close or block browser tabs based on domain or URL.

This module provides the capability to:
1. Close specific browser tabs (e.g., YouTube) when they are detected
2. Block access to specific domains or URLs
3. Integrate with the FocusGuard coordinator to receive blocking signals
"""

import os
import sys
import time
import json
import logging
import subprocess
from typing import Dict, List, Optional, Union, Set, TYPE_CHECKING
from pathlib import Path

# Import domain blocker for domain-level blocking decisions
from core.blocker.domain_blocker import should_block, block_reason

# Import the browser integration for extension-based tab closing
from core.browser_detection.browser_integration.browser_integration_v2 import close_tab as extension_close_tab
from core.browser_detection.browser_integration.browser_integration_v2 import is_extension_connected

# Conditionally import CDP-based tab controller (only for development/testing)
# This allows the production code to run without CDP dependencies
CDP_AVAILABLE = False
try:
    # Import the browser tab controller for CDP-based tab closing (fallback/development only)
    from core.blocker.browser_tab_controller import BrowserTabController
    CDP_AVAILABLE = True
except ImportError:
    # CDP dependencies not available or not desired in production
    BrowserTabController = None
    CDP_AVAILABLE = False

# Setup logging
logger = logging.getLogger("browser_tab_blocker")


class BrowserTabBlocker:
    """
    Browser Tab Blocker for closing or blocking distracting tabs.
    
    This class provides functionality to:
    1. Close specific browser tabs based on URL or domain
    2. Block access to specific websites
    3. Receive signals to trigger blocking actions
    """
    
    def __init__(self, 
                 block_categories: Optional[List[str]] = None,
                 approved_only: bool = False,
                 log_dir: Optional[str] = None,
                 use_extension: bool = True,
                 use_cdp_fallback: bool = False,
                 auto_detect_browsers: bool = True):
        """
        Initialize the Browser Tab Blocker.
        
        Args:
            block_categories: List of categories to block (e.g., ['social', 'entertainment'])
            approved_only: If True, only whitelisted domains are allowed
            log_dir: Directory to store log files
            use_extension: If True, use browser extension for tab closing (recommended)
            use_cdp_fallback: If True, allow CDP fallback when extension is not available
            auto_detect_browsers: If True, automatically detect running browser instances for CDP fallback
        """
        self.block_categories = set(block_categories) if block_categories else set()
        self.approved_only = approved_only
        self.use_extension = use_extension
        self.use_cdp_fallback = use_cdp_fallback
        
        # Initialize the browser tab controller for CDP-based tab closing (fallback/development only)
        self.tab_controller = None
        if CDP_AVAILABLE and self.use_cdp_fallback and (not self.use_extension or auto_detect_browsers):
            self.tab_controller = BrowserTabController(auto_detect=auto_detect_browsers)
        
        self.running = False
        
        # Set up logging directory
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            local_appdata = os.environ.get("LOCALAPPDATA", os.getcwd())
            self.log_dir = Path(local_appdata) / "FocusGuard"
            
        # Create directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logger
        self._configure_logger()
        
        # Dictionary to track blocked tabs to avoid repeated actions
        self.recently_blocked_tabs = {}
        
        logger.info(f"Browser Tab Blocker initialized with categories: {self.block_categories}")
        logger.info(f"Using {'browser extension' if self.use_extension else 'CDP'} for tab closing")
    
    def _configure_logger(self):
        """Configure the logger with appropriate handlers and format."""
        logger.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create file handler
        log_file = self.log_dir / "browser_tab_blocker.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    def should_block_tab(self, tab_info: Dict) -> bool:
        """
        Determine if a browser tab should be blocked based on its URL or domain.
        
        Args:
            tab_info: Dictionary containing tab information (url, title, etc.)
            
        Returns:
            bool: True if the tab should be blocked, False otherwise
        """
        url = tab_info.get('url', '')
        domain = tab_info.get('domain', '')
        
        # If no URL or domain, can't make a decision
        if not url and not domain:
            return False
        
        # Use domain_blocker to determine if this domain should be blocked
        block_result = should_block(
            domain or url,
            approved_only=self.approved_only,
            block_categories=self.block_categories
        )
        
        if block_result:
            reason = block_reason(
                domain or url,
                approved_only=self.approved_only,
                block_categories=self.block_categories
            )
            logger.info(f"Tab should be blocked: {url} (Reason: {reason})")
            return True
        
        return False
    
    def close_browser_tab(self, tab_id: int, window_id: int, url: str = None, domain: str = None, reason: str = None) -> bool:
        """
        Close a specific browser tab using either the browser extension or CDP fallback.
        
        Args:
            tab_id: The browser tab ID to close
            window_id: The browser window ID containing the tab
            url: Optional URL of the tab to close
            domain: Optional domain of the tab to close
            reason: Optional reason for closing the tab
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if we've recently tried to close this tab to avoid repeated attempts
            tab_key = f"{window_id}_{tab_id}"
            current_time = time.time()
            
            # Don't try to close the same tab more than once every 30 seconds
            if tab_key in self.recently_blocked_tabs:
                last_time = self.recently_blocked_tabs[tab_key]
                if current_time - last_time < 30:
                    logger.debug(f"Skipping tab close for {tab_key} (recently attempted)")
                    return False
            
            # Mark this tab as recently blocked
            self.recently_blocked_tabs[tab_key] = current_time
            
            # Clean up old entries from recently_blocked_tabs
            self._cleanup_recently_blocked()
            
            # Create a tab info dictionary
            tab_info = {
                "tabId": tab_id,
                "windowId": window_id,
                "reason": reason or "blocked"
            }
            
            if url:
                tab_info["url"] = url
            if domain:
                tab_info["domain"] = domain
            
            success = False
            
            # Try to use browser extension first if enabled
            if self.use_extension and is_extension_connected():
                logger.info(f"Closing browser tab {tab_id} using extension")
                success = extension_close_tab(tab_info)
            # Fall back to CDP if extension is not available or failed and CDP fallback is enabled
            elif CDP_AVAILABLE and self.use_cdp_fallback and self.tab_controller is not None:
                # Convert to format expected by tab_controller
                focus_guard_tab = {
                    "tab_id": tab_id,
                    "window_id": window_id
                }
                
                if url:
                    focus_guard_tab["url"] = url
                if domain:
                    focus_guard_tab["domain"] = domain
                
                logger.info(f"Closing browser tab {tab_id} using CDP (fallback)")
                success = self.tab_controller.close_focus_guard_tab(focus_guard_tab)
            else:
                if not is_extension_connected():
                    logger.error("Browser extension is not connected. Please install and connect the FocusGuard extension.")
                else:
                    logger.error("Failed to close tab using browser extension.")
                success = False
            
            if success:
                logger.info(f"Successfully closed tab {tab_id}")
            else:
                logger.warning(f"Failed to close tab {tab_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error closing browser tab: {e}")
            return False
    
    def _cleanup_recently_blocked(self):
        """Clean up old entries from the recently_blocked_tabs dictionary."""
        current_time = time.time()
        keys_to_remove = []
        
        for tab_key, timestamp in self.recently_blocked_tabs.items():
            if current_time - timestamp > 300:  # Remove entries older than 5 minutes
                keys_to_remove.append(tab_key)
        
        for key in keys_to_remove:
            del self.recently_blocked_tabs[key]
    
    def handle_tab_block_signal(self, signal_data: Dict) -> bool:
        """
        Handle a signal to block a specific tab.
        
        Args:
            signal_data: Dictionary containing signal information
                {
                    "tab_id": int,
                    "window_id": int,
                    "url": str,
                    "domain": str,
                    "reason": str (optional)
                }
                
        Returns:
            bool: True if the tab was blocked, False otherwise
        """
        try:
            tab_id = signal_data.get('tab_id')
            window_id = signal_data.get('window_id')
            url = signal_data.get('url', '')
            domain = signal_data.get('domain', '')
            reason = signal_data.get('reason', 'manual_block')
            
            if not tab_id or not window_id:
                logger.error("Missing required tab_id or window_id in block signal")
                return False
            
            logger.info(f"Received block signal for tab {tab_id} ({url}): {reason}")
            
            # Close the browser tab using the appropriate method
            success = self.close_browser_tab(tab_id, window_id, url, domain, reason)
            
            if success:
                logger.info(f"Successfully blocked tab {tab_id} ({url})")
            else:
                logger.warning(f"Failed to block tab {tab_id} ({url})")
            
            return success
            
        except Exception as e:
            logger.error(f"Error handling tab block signal: {e}")
            return False
    
    def add_block_category(self, category: str):
        """Add a category to the block list."""
        self.block_categories.add(category)
        logger.info(f"Added block category: {category}")
    
    def remove_block_category(self, category: str):
        """Remove a category from the block list."""
        if category in self.block_categories:
            self.block_categories.remove(category)
            logger.info(f"Removed block category: {category}")
    
    def set_approved_only_mode(self, enabled: bool):
        """Set whether to use approved-only mode (whitelist only)."""
        self.approved_only = enabled
        logger.info(f"Set approved-only mode: {enabled}")


def run_tests():
    """Run test cases for the browser tab blocker."""
    blocker = BrowserTabBlocker(block_categories=['social', 'entertainment'])
    
    # Test tab info
    test_tabs = [
        {"tab_id": 1, "window_id": 1, "url": "https://www.youtube.com/watch?v=12345", "domain": "youtube.com"},
        {"tab_id": 2, "window_id": 1, "url": "https://www.github.com/user/repo", "domain": "github.com"},
        {"tab_id": 3, "window_id": 1, "url": "https://www.facebook.com/", "domain": "facebook.com"}
    ]
    
    print("\n=== Browser Tab Blocker Tests ===\n")
    
    # Test 1: Check if tabs should be blocked
    print("1. Testing tab blocking decisions:")
    for tab in test_tabs:
        should_block = blocker.should_block_tab(tab)
        print(f"Tab {tab['tab_id']} ({tab['domain']}): {'BLOCK' if should_block else 'ALLOW'}")
    
    # Test 2: Simulate blocking signal
    print("\n2. Testing block signal handling:")
    signal = {
        "tab_id": 1,
        "window_id": 1,
        "url": "https://www.youtube.com/watch?v=12345",
        "domain": "youtube.com",
        "reason": "test_block"
    }
    result = blocker.handle_tab_block_signal(signal)
    print(f"Block signal result: {'Success' if result else 'Failed'}")


if __name__ == "__main__":
    run_tests()
