#!/usr/bin/env python
"""
Browser Block Manager: Manages the blocking of browser tabs based on signals from the coordinator.

This module provides a manager class that:
1. Receives signals about tabs that should be blocked
2. Coordinates with the browser_tab_blocker to perform the actual blocking
3. Provides an interface for the coordinator to trigger blocking actions
"""

import os
import logging
import threading
import time
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
from queue import Queue, Empty

# Import the browser tab blocker
from core.blocker.browser_tab_blocker import BrowserTabBlocker

# Setup logging
logger = logging.getLogger("browser_block_manager")


class BrowserBlockManager:
    """
    Manager for browser tab blocking operations.
    
    This class provides functionality to:
    1. Receive blocking signals from the coordinator
    2. Queue blocking operations
    3. Process blocking operations in a separate thread
    """
    
    def __init__(self, 
                 block_categories: Optional[List[str]] = None,
                 approved_only: bool = False,
                 log_dir: Optional[str] = None):
        """
        Initialize the Browser Block Manager.
        
        Args:
            block_categories: List of categories to block (e.g., ['social', 'entertainment'])
            approved_only: If True, only whitelisted domains are allowed
            log_dir: Directory to store log files
        """
        self.block_queue = Queue()
        self.running = False
        self.thread = None
        
        # Set up logging directory
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            local_appdata = os.environ.get("LOCALAPPDATA", os.getcwd())
            self.log_dir = Path(local_appdata) / "FocusGuard"
            
        # Create directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the browser tab blocker
        self.tab_blocker = BrowserTabBlocker(
            block_categories=block_categories,
            approved_only=approved_only,
            log_dir=str(self.log_dir)
        )
        
        # Configure logger
        self._configure_logger()
        
        logger.info("Browser Block Manager initialized")
    
    def _configure_logger(self):
        """Configure the logger with appropriate handlers and format."""
        logger.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create file handler
        log_file = self.log_dir / "browser_block_manager.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    def queue_tab_block(self, tab_info: Dict[str, Any]) -> bool:
        """
        Queue a tab to be blocked.
        
        Args:
            tab_info: Dictionary containing tab information
                {
                    "tab_id": int,
                    "window_id": int,
                    "url": str,
                    "domain": str,
                    "title": str (optional),
                    "reason": str (optional)
                }
                
        Returns:
            bool: True if the tab was queued for blocking, False otherwise
        """
        try:
            # Validate required fields
            required_fields = ['tab_id', 'window_id']
            for field in required_fields:
                if field not in tab_info:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Add to the blocking queue
            self.block_queue.put(tab_info)
            logger.info(f"Queued tab for blocking: {tab_info.get('url', 'Unknown URL')}")
            return True
            
        except Exception as e:
            logger.error(f"Error queuing tab for blocking: {e}")
            return False
    
    def _blocking_worker(self):
        """Worker thread to process the blocking queue."""
        logger.info("Blocking worker thread started")
        
        while self.running:
            try:
                # Get the next tab to block (with timeout to allow thread to exit)
                try:
                    tab_info = self.block_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                # Process the blocking request
                success = self.tab_blocker.handle_tab_block_signal(tab_info)
                
                if success:
                    logger.info(f"Successfully blocked tab: {tab_info.get('url', 'Unknown URL')}")
                else:
                    logger.warning(f"Failed to block tab: {tab_info.get('url', 'Unknown URL')}")
                
                # Mark the task as done
                self.block_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in blocking worker: {e}")
                time.sleep(1)  # Sleep briefly to avoid tight error loops
    
    def start(self):
        """Start the browser block manager."""
        if self.running:
            logger.warning("Browser block manager is already running")
            return
        
        logger.info("Starting browser block manager...")
        
        # Start the blocking worker thread
        self.running = True
        self.thread = threading.Thread(target=self._blocking_worker)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("Browser block manager started successfully")
    
    def stop(self):
        """Stop the browser block manager."""
        if not self.running:
            logger.warning("Browser block manager is not running")
            return
        
        logger.info("Stopping browser block manager...")
        
        # Stop the blocking worker thread
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        
        logger.info("Browser block manager stopped successfully")
    
    def should_block_tab(self, tab_info: Dict[str, Any]) -> bool:
        """
        Check if a tab should be blocked based on its URL or domain.
        
        Args:
            tab_info: Dictionary containing tab information
            
        Returns:
            bool: True if the tab should be blocked, False otherwise
        """
        return self.tab_blocker.should_block_tab(tab_info)
    
    def add_block_category(self, category: str):
        """Add a category to the block list."""
        self.tab_blocker.add_block_category(category)
    
    def remove_block_category(self, category: str):
        """Remove a category from the block list."""
        self.tab_blocker.remove_block_category(category)
    
    def set_approved_only_mode(self, enabled: bool):
        """Set whether to use approved-only mode (whitelist only)."""
        self.tab_blocker.set_approved_only_mode(enabled)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the browser block manager.
        
        Returns:
            Dict: Status information
        """
        return {
            "running": self.running,
            "queue_size": self.block_queue.qsize(),
            "block_categories": list(self.tab_blocker.block_categories),
            "approved_only": self.tab_blocker.approved_only
        }


def run_tests():
    """Run test cases for the browser block manager."""
    manager = BrowserBlockManager(block_categories=['social', 'entertainment'])
    manager.start()
    
    # Test tab info
    test_tabs = [
        {"tab_id": 1, "window_id": 1, "url": "https://www.youtube.com/watch?v=12345", "domain": "youtube.com"},
        {"tab_id": 2, "window_id": 1, "url": "https://www.github.com/user/repo", "domain": "github.com"},
        {"tab_id": 3, "window_id": 1, "url": "https://www.facebook.com/", "domain": "facebook.com"}
    ]
    
    print("\n=== Browser Block Manager Tests ===\n")
    
    # Test 1: Check if tabs should be blocked
    print("1. Testing tab blocking decisions:")
    for tab in test_tabs:
        should_block = manager.should_block_tab(tab)
        print(f"Tab {tab['tab_id']} ({tab['domain']}): {'BLOCK' if should_block else 'ALLOW'}")
    
    # Test 2: Queue tabs for blocking
    print("\n2. Testing tab blocking queue:")
    for tab in test_tabs:
        if manager.should_block_tab(tab):
            queued = manager.queue_tab_block(tab)
            print(f"Tab {tab['tab_id']} ({tab['domain']}): {'Queued' if queued else 'Not queued'}")
    
    # Wait for queue to process
    print("\nWaiting for blocking queue to process...")
    time.sleep(2)
    
    # Get status
    status = manager.get_status()
    print(f"\nManager status: {status}")
    
    # Stop the manager
    manager.stop()
    print("\nManager stopped")


if __name__ == "__main__":
    run_tests()
