"""
Process manager for browser extension components.

This module provides a process manager for browser extension components,
particularly the tab server. It handles starting, stopping, monitoring,
and automatically restarting processes when needed.
"""

import logging
import os
import subprocess
import threading
import time
import signal
import sys
import psutil
from typing import Optional, Dict, Any, Callable, List

from focus_guard.core.browser.extension.interfaces import ProcessManagerInterface

logger = logging.getLogger(__name__)


class TabServerProcessManager(ProcessManagerInterface):
    """Process manager for the tab server."""
    
    def __init__(self, 
                 python_executable: str = sys.executable,
                 tab_server_module: str = "focus_guard.core.browser.extension.tab_server",
                 auto_restart: bool = True,
                 max_restarts: int = 3,
                 restart_delay: int = 5,
                 health_check_interval: int = 30,
                 on_start_callback: Optional[Callable[[], None]] = None,
                 on_stop_callback: Optional[Callable[[], None]] = None):
        """Initialize the tab server process manager.
        
        Args:
            python_executable: Path to the Python executable
            tab_server_module: Module path to the tab server
            auto_restart: Whether to automatically restart the process if it crashes
            max_restarts: Maximum number of automatic restarts
            restart_delay: Delay in seconds between restart attempts
            on_start_callback: Callback function to call when the process starts
            on_stop_callback: Callback function to call when the process stops
        """
        self._python_executable = python_executable
        self._tab_server_module = tab_server_module
        self._auto_restart = auto_restart
        self._max_restarts = max_restarts
        self._restart_delay = restart_delay
        self._health_check_interval = health_check_interval
        self._on_start_callback = on_start_callback
        self._on_stop_callback = on_stop_callback
        
        # Process state
        self._process: Optional[subprocess.Popen] = None
        self._process_id: Optional[int] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._health_monitor_thread: Optional[threading.Thread] = None
        self._should_stop = threading.Event()
        self._restart_count = 0
        self._start_time = 0
        self._actual_port: Optional[int] = None
        self._status = {
            "running": False,
            "pid": None,
            "uptime": 0,
            "restart_count": 0,
            "last_start_time": 0,
            "last_error": None,
            "health_status": "unknown",
            "last_health_check": 0,
            "port": None
        }
        
        # Register cleanup handler
        import atexit
        atexit.register(self.stop)
    
    def start(self) -> bool:
        """Start the tab server process.
        
        Returns:
            bool: True if the process started successfully, False otherwise
        """
        if self.is_running():
            logger.info("Tab server process is already running")
            return True
        
        logger.info("Starting tab server process...")
        
        try:
            # Start the tab server as a module
            cmd = [self._python_executable, "-m", self._tab_server_module]
            
            # Use DETACHED_PROCESS flag on Windows to prevent the process from
            # being killed when the parent process exits
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.DETACHED_PROCESS
            
            # Start the process
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creation_flags
            )
            
            self._process_id = self._process.pid
            self._start_time = time.time()
            self._status["running"] = True
            self._status["pid"] = self._process_id
            self._status["last_start_time"] = self._start_time
            self._status["last_error"] = None
            
            logger.info(f"Tab server process started with PID {self._process_id}")
            
            # Start the monitor threads
            self._should_stop.clear()
            self._monitor_thread = threading.Thread(
                target=self._monitor_process,
                daemon=True,
                name="TabServerProcessMonitor"
            )
            self._monitor_thread.start()
            
            # Start health monitoring thread
            self._health_monitor_thread = threading.Thread(
                target=self._monitor_health,
                daemon=True,
                name="TabServerHealthMonitor"
            )
            self._health_monitor_thread.start()
            
            # Call the on_start callback if provided
            if self._on_start_callback:
                try:
                    self._on_start_callback()
                except Exception as e:
                    logger.error(f"Error in on_start callback: {e}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error starting tab server process: {e}")
            self._status["last_error"] = str(e)
            return False
    
    def stop(self) -> None:
        """Stop the tab server process."""
        if not self.is_running():
            logger.info("Tab server process is not running")
            return
        
        logger.info("Stopping tab server process...")
        
        # Signal the monitor threads to stop
        self._should_stop.set()
        
        # Try to terminate the process gracefully
        try:
            if self._process and self._process.poll() is None:
                # First try to send a graceful shutdown request
                try:
                    import requests
                    # Use the actual port if available
                    port = getattr(self, '_actual_port', 5000)
                    shutdown_url = f"http://localhost:{port}/api/shutdown"
                    logger.debug(f"Sending graceful shutdown request to {shutdown_url}")
                    requests.post(shutdown_url, timeout=2)
                    
                    # Wait for the process to exit gracefully
                    for i in range(10):  # Wait up to 5 seconds
                        if self._process.poll() is not None:
                            logger.info("Process shut down gracefully")
                            break
                        time.sleep(0.5)
                    else:
                        logger.warning("Process did not respond to graceful shutdown request")
                except Exception as e:
                    logger.debug(f"Graceful shutdown request failed: {e}, falling back to process termination")
                
                # If the process is still running, terminate it
                if self._process.poll() is None:
                    if sys.platform == "win32":
                        # On Windows, use taskkill to kill the process tree
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(self._process_id)], 
                                      stdout=subprocess.DEVNULL, 
                                      stderr=subprocess.DEVNULL)
                    else:
                        # On Unix, use SIGTERM
                        self._process.terminate()
                        self._process.wait(timeout=5)
        except Exception as e:
            logger.error(f"Error stopping tab server process: {e}")
        
        # Update status
        self._status["running"] = False
        self._status["pid"] = None
        self._status["health_status"] = "stopped"
        self._process = None
        self._process_id = None
        self._actual_port = None
        
        # Call the on_stop callback if provided
        if self._on_stop_callback:
            try:
                self._on_stop_callback()
            except Exception as e:
                logger.error(f"Error in on_stop callback: {e}")
        
        logger.info("Tab server process stopped")
    
    def restart(self) -> bool:
        """Restart the tab server process.
        
        Returns:
            bool: True if the process restarted successfully, False otherwise
        """
        logger.info("Restarting tab server process...")
        
        self.stop()
        time.sleep(1)  # Brief delay to ensure cleanup
        return self.start()
    
    def is_running(self) -> bool:
        """Check if the tab server process is running.
        
        Returns:
            bool: True if the process is running, False otherwise
        """
        if self._process is None:
            return False
        
        # Check if the process is still running
        return self._process.poll() is None
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the tab server process.
        
        Returns:
            dict: Status information
        """
        # Update the uptime if the process is running
        if self.is_running():
            self._status["uptime"] = time.time() - self._start_time
        
        # Add port information if available
        if self._actual_port:
            self._status["port"] = self._actual_port
        
        return self._status.copy()
    
    def _monitor_process(self) -> None:
        """Monitor the tab server process and restart it if needed."""
        while not self._should_stop.is_set():
            # Check if the process is still running
            if self._process and self._process.poll() is not None:
                exit_code = self._process.returncode
                logger.warning(f"Tab server process exited with code {exit_code}")
                
                # Collect any error output
                stderr = self._process.stderr.read() if self._process.stderr else ""
                if stderr:
                    logger.error(f"Tab server process error output: {stderr}")
                    self._status["last_error"] = stderr
                
                # Update status
                self._status["running"] = False
                self._status["pid"] = None
                
                # Restart the process if auto-restart is enabled
                if self._auto_restart and self._restart_count < self._max_restarts:
                    self._restart_count += 1
                    self._status["restart_count"] = self._restart_count
                    
                    logger.info(f"Auto-restarting tab server process (attempt {self._restart_count}/{self._max_restarts})...")
                    time.sleep(self._restart_delay)
                    
                    try:
                        self.start()
                    except Exception as e:
                        logger.error(f"Error auto-restarting tab server process: {e}")
                        self._status["last_error"] = str(e)
                else:
                    logger.warning("Not auto-restarting tab server process (max restarts reached or auto-restart disabled)")
                    break
            
            # Sleep for a bit before checking again
            time.sleep(1)
    
    def _monitor_health(self) -> None:
        """Monitor the health of the tab server via HTTP health checks."""
        while not self._should_stop.is_set():
            if self.is_running():
                try:
                    # Perform health check
                    health_status = self._perform_health_check()
                    self._status["health_status"] = health_status
                    self._status["last_health_check"] = time.time()
                    
                    if health_status == "unhealthy":
                        logger.warning("Tab server health check failed")
                        # Could trigger restart here if needed
                        
                except Exception as e:
                    logger.error(f"Error during health check: {e}")
                    self._status["health_status"] = "error"
            
            # Wait for the next health check
            time.sleep(self._health_check_interval)
    
    def _perform_health_check(self) -> str:
        """Perform a health check on the tab server.
        
        Returns:
            str: Health status ('healthy', 'degraded', 'unhealthy', 'error')
        """
        try:
            import requests
            # Try to determine the actual port
            port = self._actual_port or 5000
            health_url = f"http://localhost:{port}/api/health"
            
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                return health_data.get("status", "unknown")
            elif response.status_code == 503:
                # Server is responding but degraded
                return "degraded"
            else:
                return "unhealthy"
                
        except requests.exceptions.ConnectionError:
            return "unhealthy"
        except requests.exceptions.Timeout:
            return "degraded"
        except Exception as e:
            logger.debug(f"Health check error: {e}")
            return "error"
    
    def get_health_status(self) -> str:
        """Get the current health status of the tab server.
        
        Returns:
            str: Health status
        """
        return self._status.get("health_status", "unknown")


# Singleton instance
_process_manager_instance = None

def get_tab_server_process_manager(**kwargs) -> TabServerProcessManager:
    """Get the singleton tab server process manager instance.
    
    Args:
        **kwargs: Arguments to pass to the TabServerProcessManager constructor
        
    Returns:
        TabServerProcessManager: The singleton instance
    """
    global _process_manager_instance
    if _process_manager_instance is None:
        _process_manager_instance = TabServerProcessManager(**kwargs)
    return _process_manager_instance

def start_tab_server_process(**kwargs) -> bool:
    """Start the tab server process.
    
    Args:
        **kwargs: Arguments to pass to the TabServerProcessManager constructor
        
    Returns:
        bool: True if the process started successfully, False otherwise
    """
    process_manager = get_tab_server_process_manager(**kwargs)
    return process_manager.start()

def stop_tab_server_process() -> None:
    """Stop the tab server process."""
    global _process_manager_instance
    if _process_manager_instance is not None:
        _process_manager_instance.stop()

def restart_tab_server_process() -> bool:
    """Restart the tab server process.
    
    Returns:
        bool: True if the process restarted successfully, False otherwise
    """
    process_manager = get_tab_server_process_manager()
    return process_manager.restart()

def is_tab_server_running() -> bool:
    """Check if the tab server process is running.
    
    Returns:
        bool: True if the process is running, False otherwise
    """
    process_manager = get_tab_server_process_manager()
    return process_manager.is_running()

def get_tab_server_status() -> Dict[str, Any]:
    """Get the status of the tab server process.
    
    Returns:
        dict: Status information
    """
    process_manager = get_tab_server_process_manager()
    return process_manager.get_status()
