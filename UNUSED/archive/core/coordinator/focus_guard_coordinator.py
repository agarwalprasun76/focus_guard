#!/usr/bin/env python
"""
FocusGuard Coordinator Service

This module provides the main coordinator service for FocusGuard,
managing and synchronizing various monitoring components.
"""

import os
import sys
import time
import logging
import datetime
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Import activity monitor components
from core.activity_monitor.activity_logger import ActivityLogger

# Import browser blocker components
try:
    from core.blocker.browser_block_manager import BrowserBlockManager
    BROWSER_BLOCKER_AVAILABLE = True
except ImportError:
    BROWSER_BLOCKER_AVAILABLE = False

# Setup logging
logger = logging.getLogger("focus_guard_coordinator")


class FocusGuardCoordinator:
    """
    Coordinator service for FocusGuard components.
    
    This class provides functionality to:
    1. Launch and manage both activity logger and browser native host
    2. Ensure synchronized timestamps between components
    3. Provide a unified interface for starting/stopping monitoring
    """
    
    def __init__(self, 
                 interval_seconds: int = 5,
                 log_dir: Optional[str] = None,
                 native_host_path: Optional[str] = None,
                 block_categories: Optional[List[str]] = None,
                 approved_only: bool = False):
        """
        Initialize the FocusGuard coordinator.
        
        Args:
            interval_seconds: Sampling interval in seconds
            log_dir: Directory to store log files (defaults to %LOCALAPPDATA%/FocusGuard)
            native_host_path: Path to the native host executable
            block_categories: List of categories to block (e.g., ['social', 'entertainment'])
            approved_only: If True, only whitelisted domains are allowed
        """
        self.interval = interval_seconds
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
        
        # Set native host path
        if native_host_path:
            self.native_host_path = Path(native_host_path)
        else:
            # Default path relative to this file
            current_dir = Path(__file__).parent.parent
            self.native_host_path = current_dir / "browser_detection" / "webextension_mv3" / "dist" / "focus_guard_native_host.exe"
        
        # Initialize components
        self.activity_logger = ActivityLogger(interval_seconds=interval_seconds, log_dir=str(self.log_dir))
        self.native_host_process = None
        
        # Initialize browser blocker if available
        self.browser_blocker = None
        if BROWSER_BLOCKER_AVAILABLE:
            self.browser_blocker = BrowserBlockManager(
                block_categories=block_categories or ['social', 'entertainment'],
                approved_only=approved_only,
                log_dir=str(self.log_dir)
            )
            logger.info("Browser blocker initialized")
        else:
            logger.warning("Browser blocker module not available")
        
        # Configure logger
        self._configure_logger()
    
    def _configure_logger(self):
        """Configure the logger with appropriate handlers and format."""
        logger.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create file handler
        log_file = self.log_dir / "focus_guard_coordinator.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    def start_native_host(self) -> bool:
        """
        Start the browser native host process.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.native_host_process:
            logger.warning("Native host process is already running")
            return True
        
        if not self.native_host_path.exists():
            logger.error(f"Native host executable not found at: {self.native_host_path}")
            return False
        
        try:
            # Start the native host process
            # Note: Native host is typically launched by the browser, not directly
            # This is for testing/development purposes
            logger.info(f"Starting native host: {self.native_host_path}")
            
            # Use subprocess.Popen to start the process without blocking
            self.native_host_process = subprocess.Popen(
                [str(self.native_host_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW  # Hide console window
            )
            
            # Check if process started
            if self.native_host_process.poll() is None:
                logger.info("Native host process started successfully")
                return True
            else:
                logger.error("Failed to start native host process")
                self.native_host_process = None
                return False
                
        except Exception as e:
            logger.error(f"Error starting native host: {e}")
            self.native_host_process = None
            return False
    
    def stop_native_host(self):
        """Stop the browser native host process."""
        if not self.native_host_process:
            logger.warning("Native host process is not running")
            return
        
        try:
            # Terminate the process
            self.native_host_process.terminate()
            
            # Wait for process to terminate
            try:
                self.native_host_process.wait(timeout=5)
                logger.info("Native host process terminated")
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate
                self.native_host_process.kill()
                logger.warning("Native host process killed forcefully")
            
            self.native_host_process = None
            
        except Exception as e:
            logger.error(f"Error stopping native host: {e}")
    
    def _coordination_loop(self):
        """Main coordination loop that runs in a separate thread."""
        logger.info(f"Coordination started with {self.interval}s interval")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Generate synchronized timestamp
                timestamp = datetime.datetime.now().isoformat()
                
                # Check if native host is still running
                if self.native_host_process and self.native_host_process.poll() is not None:
                    logger.warning("Native host process has terminated unexpectedly")
                    self.native_host_process = None
                    
                    # Attempt to restart
                    self.start_native_host()
                
                # Calculate sleep time to maintain consistent interval
                elapsed = time.time() - start_time
                sleep_time = max(0.1, self.interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in coordination loop: {e}")
                time.sleep(1)  # Sleep briefly to avoid tight error loops
    
    def start(self):
        """Start the FocusGuard coordinator and its components."""
        if self.running:
            logger.warning("Coordinator is already running")
            return
        
        logger.info("Starting FocusGuard coordinator...")
        
        # Start activity logger
        self.activity_logger.start()
        logger.info("Activity logger started")
        
        # Start native host (optional, as it's typically launched by the browser)
        # self.start_native_host()
        
        # Start browser blocker if available
        if self.browser_blocker:
            self.browser_blocker.start()
            logger.info("Browser blocker started")
        
        # Start coordination thread
        self.running = True
        self.thread = threading.Thread(target=self._coordination_loop)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("FocusGuard coordinator started successfully")
    
    def stop(self):
        """Stop the FocusGuard coordinator and its components."""
        if not self.running:
            logger.warning("Coordinator is not running")
            return
        
        logger.info("Stopping FocusGuard coordinator...")
        
        # Stop coordination thread
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        
        # Stop activity logger
        self.activity_logger.stop()
        logger.info("Activity logger stopped")
        
        # Stop native host (if we started it)
        if self.native_host_process:
            self.stop_native_host()
        
        # Stop browser blocker if available
        if self.browser_blocker:
            self.browser_blocker.stop()
            logger.info("Browser blocker stopped")
        
        logger.info("FocusGuard coordinator stopped successfully")
    
    def handle_tab_activity(self, tab_info: Dict[str, Any]) -> bool:
        """
        Handle tab activity from browser integration and decide if it should be blocked.
        
        Args:
            tab_info: Dictionary containing tab information
                {"tab_id": int, "window_id": int, "url": str, "domain": str, "title": str}
                
        Returns:
            bool: True if the tab was queued for blocking, False otherwise
        """
        if not self.browser_blocker:
            logger.warning("Browser blocker not available, cannot handle tab activity")
            return False
            
        # Check if tab should be blocked
        if self.browser_blocker.should_block_tab(tab_info):
            # Queue the tab for blocking
            success = self.browser_blocker.queue_tab_block(tab_info)
            if success:
                logger.info(f"Queued tab for blocking: {tab_info.get('url', 'Unknown URL')}")
            else:
                logger.warning(f"Failed to queue tab for blocking: {tab_info.get('url', 'Unknown URL')}")
            return success
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the coordinator and its components.
        
        Returns:
            Dict: Status information
        """
        status = {
            "coordinator_running": self.running,
            "activity_logger_running": hasattr(self.activity_logger, 'running') and self.activity_logger.running,
            "native_host_running": self.native_host_process is not None and self.native_host_process.poll() is None,
            "log_directory": str(self.log_dir),
            "sampling_interval": self.interval
        }
        
        # Add browser blocker status if available
        if self.browser_blocker:
            blocker_status = self.browser_blocker.get_status()
            status["browser_blocker_running"] = blocker_status["running"]
            status["browser_blocker_queue_size"] = blocker_status["queue_size"]
            status["browser_blocker_categories"] = blocker_status["block_categories"]
            status["browser_blocker_approved_only"] = blocker_status["approved_only"]
        else:
            status["browser_blocker_available"] = False
        
        return status


def main():
    """Main function for standalone execution."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start coordinator with browser blocking enabled
    coordinator = FocusGuardCoordinator(
        interval_seconds=5,
        block_categories=['social', 'entertainment']
    )
    
    try:
        logger.info("Starting FocusGuard coordinator...")
        coordinator.start()
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping FocusGuard coordinator...")
        coordinator.stop()
        logger.info("FocusGuard coordinator stopped")
    except Exception as e:
        logger.error(f"Error in FocusGuard coordinator: {e}")
        coordinator.stop()


if __name__ == "__main__":
    main()
