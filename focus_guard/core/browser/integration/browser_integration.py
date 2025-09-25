"""
Browser integration module.

This module provides the concrete implementation of browser integration functionality,
connecting to the tab server to monitor and control browser tabs.
"""

import logging
import requests
import json
import time
from typing import Dict, List, Optional, Any
from urllib.parse import quote

from focus_guard.core.utils.retry import retry
from focus_guard.core.utils.enhanced_retry import (
    retry_network_call, retry_file_operation, retry_database_operation
)
from focus_guard.core.utils.error_monitoring import (
    get_error_monitor, record_error, record_success, ErrorSeverity
)
from focus_guard.core.utils.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, get_circuit_breaker, CircuitBreakerError
)

from focus_guard.core.browser.interfaces import BrowserIntegrationInterface
from focus_guard.core.browser.models.tab import Tab
from focus_guard.core.browser.extension.tab_server import get_tab_server, start_tab_server, stop_tab_server
from focus_guard.core.browser.extension.process_manager import get_tab_server_process_manager, start_tab_server_process

logger = logging.getLogger(__name__)


class BrowserIntegration(BrowserIntegrationInterface):
    """Browser integration implementation that connects to the tab server."""
    
    def __init__(self, tab_server_url: str = "http://localhost:5000", auto_start: bool = True, tab_server: Optional[Any] = None, config=None):
        """Initialize the browser integration with improved lifecycle management.
        
        Args:
            tab_server_url: URL of the tab server
            auto_start: Whether to automatically start the tab server if it's not running
            tab_server: Optional pre-configured TabServer instance to use
            config: Configuration manager instance
        """
        from focus_guard.core.browser.extension.interfaces import TabServerConfig
        
        self._tab_server_url = tab_server_url
        self._last_update_time = 0
        self._cache_ttl = 1.0  # Cache tab data for 1 second
        self._tab_cache = []
        self._last_update_time = 0
        self._startup_timeout = 15  # Maximum time to wait for server startup
        self._health_check_interval = 60  # Check server health every minute
        
        # Create tab server config from configuration manager
        tab_server_config = TabServerConfig()
        if config:
            # Handle different config manager interfaces
            if hasattr(config, 'load_config'):
                cfg = config.load_config()
                tab_server_config.port = cfg.get('tab_server_port', 5000)
                tab_server_config.host = cfg.get('tab_server_host', 'localhost')
            elif hasattr(config, 'get_value'):
                tab_server_config.port = config.get_value('browser.tab_server.port', 5000)
                tab_server_config.host = config.get_value('browser.tab_server.host', 'localhost')
            else:
                # Fallback to defaults
                tab_server_config.port = 5000
                tab_server_config.host = 'localhost'
        
        self._tab_server = tab_server if tab_server is not None else get_tab_server(tab_server_config)
        # Initialize process manager with enhanced configuration
        self._process_manager = get_tab_server_process_manager(
            health_check_interval=30,  # Check health every 30 seconds
            max_restarts=3,
            restart_delay=5
        )
        
        # Real-time blocking integration
        self._classification_callback = None
        self._event_listeners = []
        self._blocking_enabled = True
        
        # Error handling and resilience
        self._setup_circuit_breakers()
        self._error_counts = {
            'tab_server_connection': 0,
            'classification_errors': 0,
            'command_failures': 0
        }
        self._last_error_reset = time.time()
        self._max_error_rate = 10  # Reset error counts every 10 errors
        
        # Auto-start the tab server if requested
        if auto_start:
            self._ensure_tab_server_running()
            
        # Set up classification integration
        self._setup_classification_integration()
        
        logger.info(f"Browser integration initialized with resilience features")
    
    def _check_tab_server_status(self) -> bool:
        """Check if the tab server is running and responsive with enhanced health check.
        
        Returns:
            bool: True if the tab server is running and healthy
        """
        try:
            # First check if process is running
            if not self._process_manager.is_running():
                logger.debug("Tab server process is not running")
                return False
            
            # Check server health via HTTP
            response = requests.get(f"{self._tab_server_url}/api/health", timeout=2)
            if response.status_code == 200:
                health_data = response.json()
                is_healthy = health_data.get("status") == "healthy"
                if not is_healthy:
                    logger.warning(f"Tab server is unhealthy: {health_data.get('issues', [])}")
                return is_healthy
            else:
                logger.debug(f"Tab server health check failed with status {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.debug(f"Tab server health check failed: {e}")
            return False
    
    def _setup_circuit_breakers(self):
        """Set up circuit breakers for different service calls."""
        # Tab server circuit breaker
        tab_server_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            success_threshold=2,
            timeout=10.0,
            expected_exception=(requests.exceptions.RequestException, ConnectionError, TimeoutError)
        )
        self._tab_server_breaker = get_circuit_breaker("tab_server", tab_server_config)
        
        # Classification circuit breaker
        classification_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60.0,
            success_threshold=3,
            timeout=5.0,
            expected_exception=(Exception,)
        )
        self._classification_breaker = get_circuit_breaker("classification", classification_config)
        
        logger.info("Circuit breakers configured for browser integration")
    
    def _setup_classification_integration(self):
        """Set up integration with classification system for real-time blocking."""
        try:
            # Get the tab server instance to register classification callback
            tab_server = get_tab_server()
            if tab_server and hasattr(tab_server, 'set_classification_callback'):
                tab_server.set_classification_callback(self._classify_for_blocking_with_resilience)
                logger.info("Classification callback registered with tab server")
            else:
                logger.warning("Could not register classification callback - tab server not available")
        except Exception as e:
            logger.error(f"Error setting up classification integration: {e}")
            self._record_error('classification_errors')
    
    def _classify_for_blocking_with_resilience(self, url: str, domain: str, browser: str, tab_id: str) -> tuple[bool, str]:
        """Fast classification callback with resilience and error handling.
        
        Args:
            url: The URL to classify
            domain: The domain extracted from the URL
            browser: The browser name
            tab_id: The tab ID
            
        Returns:
            tuple[bool, str]: (should_block, reason)
        """
        try:
            if not self._blocking_enabled:
                return False, "blocking_disabled"
            
            # Use circuit breaker for classification
            return self._classification_breaker.call(
                self._classify_for_blocking_internal, url, domain, browser, tab_id
            )
            
        except CircuitBreakerError:
            logger.warning(f"Classification circuit breaker open for {domain} - using fallback")
            return self._fallback_classification(url, domain)
        except Exception as e:
            logger.error(f"Error in classification callback: {e}")
            self._record_error('classification_errors')
            return self._fallback_classification(url, domain)
    
    def _classify_for_blocking_internal(self, url: str, domain: str, browser: str, tab_id: str) -> tuple[bool, str]:
        """Internal classification logic."""
        # Use the registered classification callback if available
        if self._classification_callback:
            return self._classification_callback(url, domain, browser, tab_id)
        
        # Default fast classification based on domain patterns
        distracting_patterns = {
            'youtube.com': 'video_streaming',
            'facebook.com': 'social_media',
            'twitter.com': 'social_media', 
            'instagram.com': 'social_media',
            'reddit.com': 'social_media',
            'tiktok.com': 'video_streaming',
            'netflix.com': 'video_streaming',
            'twitch.tv': 'video_streaming',
            'discord.com': 'communication',
            'snapchat.com': 'social_media'
        }
        
        for pattern, category in distracting_patterns.items():
            if pattern in domain.lower():
                logger.debug(f"Blocking {domain} - category: {category}")
                return True, f"blocked_category_{category}"
        
        return False, "not_distracting"
    
    def _fallback_classification(self, url: str, domain: str) -> tuple[bool, str]:
        """Fallback classification when main system fails."""
        # Simple domain-based blocking as fallback
        high_risk_domains = {'youtube.com', 'facebook.com', 'twitter.com', 'instagram.com'}
        should_block = any(d in domain.lower() for d in high_risk_domains)
        reason = "fallback_high_risk" if should_block else "fallback_allowed"
        return should_block, reason
    
    def set_classification_callback(self, callback):
        """Set the classification callback for real-time blocking.
        
        Args:
            callback: Function that takes (url, domain, browser, tab_id) and returns (should_block, reason)
        """
        self._classification_callback = callback
        logger.info("Classification callback registered")
    
    def enable_blocking(self, enabled: bool = True):
        """Enable or disable real-time blocking.
        
        Args:
            enabled: Whether to enable blocking
        """
        self._blocking_enabled = enabled
        logger.info(f"Real-time blocking {'enabled' if enabled else 'disabled'}")
    
    @retry_network_call(max_attempts=2, base_delay=1.0)
    def get_recent_events(self, browser: str = None, since: float = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent tab events from the server with retry protection.
        
        Args:
            browser: Filter by browser name
            since: Get events since this timestamp
            limit: Maximum number of events to return
            
        Returns:
            List[Dict[str, Any]]: List of recent events
        """
        try:
            params = {}
            if browser:
                params['browser'] = browser
            if since:
                params['since'] = str(since)
            if limit:
                params['limit'] = str(limit)
            
            response = self._tab_server_breaker.call(
                lambda: requests.get(
                    f"{self._tab_server_url}/api/events",
                    params=params,
                    timeout=5
                )
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('events', [])
            else:
                logger.warning(f"Failed to get events: HTTP {response.status_code}")
                return []
                
        except CircuitBreakerError:
            logger.warning("Tab server circuit breaker open - cannot get events")
            return []
        except (requests.exceptions.RequestException, Exception) as e:
            logger.error(f"Error getting recent events: {e}")
            return []
    
    def stop(self):
        """Stop the browser integration and tab server."""
        logger.info("Stopping browser integration")
        try:
            # Clear event listeners
            self._event_listeners.clear()
            
            # Stop the process manager (which will gracefully stop the tab server)
            if hasattr(self, '_process_manager'):
                self._process_manager.stop()
                logger.info("Tab server process stopped")
        except Exception as e:
            logger.error(f"Error stopping browser integration: {e}")
    
    def add_event_listener(self, callback):
        """Add an event listener for tab events.
        
        Args:
            callback: Function to call when events are received
        """
        self._event_listeners.append(callback)
        logger.debug(f"Added event listener, total: {len(self._event_listeners)}")
    
    def remove_event_listener(self, callback):
        """Remove an event listener.
        
        Args:
            callback: Function to remove from listeners
        """
        if callback in self._event_listeners:
            self._event_listeners.remove(callback)
            logger.debug(f"Removed event listener, total: {len(self._event_listeners)}")
    
    def _record_error(self, error_type: str, message: str = "", severity: ErrorSeverity = ErrorSeverity.MEDIUM, context: Optional[Dict[str, Any]] = None):
        """Record an error for monitoring and alerting."""
        self._error_counts[error_type] += 1
        
        # Record in centralized error monitoring
        record_error(
            component="browser_integration",
            error_type=error_type,
            message=message or f"Error in {error_type}",
            severity=severity,
            context=context
        )
        
        # Check if we need to reset error counts (every 5 minutes)
        current_time = time.time()
        if current_time - self._last_error_reset > 300:  # 5 minutes
            total_errors = sum(self._error_counts.values())
            if total_errors > 10:  # High error rate
                logger.warning(f"High error rate detected: {self._error_counts}")
                # Reset counts to prevent constant alerting
                self._error_counts = {key: 0 for key in self._error_counts}
                self._last_error_reset = current_time
    
    def _record_success(self, operation: str):
        """Record a successful operation."""
        record_success("browser_integration")
    
    def _notify_event_listeners(self, events):
        """Notify all event listeners of new events with error handling.
        
        Args:
            events: List of events to notify about
        """
        for callback in self._event_listeners:
            try:
                callback(events)
            except Exception as e:
                logger.error(f"Error in event listener callback: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status including circuit breaker states.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Get circuit breaker statuses
            tab_server_status = self._tab_server_breaker.get_status()
            classification_status = self._classification_breaker.get_status()
            
            # Check tab server connectivity
            tab_server_healthy = self._check_tab_server_status()
            
            return {
                "browser_integration_healthy": tab_server_healthy,
                "blocking_enabled": self._blocking_enabled,
                "error_counts": self._error_counts.copy(),
                "last_error_reset": self._last_error_reset,
                "circuit_breakers": {
                    "tab_server": tab_server_status,
                    "classification": classification_status
                },
                "cache_status": {
                    "tab_count": len(self._tab_cache),
                    "last_update": self._last_update_time
                }
            }
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {"error": str(e), "healthy": False}
    
    def reset_circuit_breakers(self):
        """Reset all circuit breakers to closed state."""
        try:
            self._tab_server_breaker.reset()
            self._classification_breaker.reset()
            self._error_counts = {key: 0 for key in self._error_counts}
            logger.info("All circuit breakers reset")
        except Exception as e:
            logger.error(f"Error resetting circuit breakers: {e}")
    
    @retry_network_call(max_attempts=3, base_delay=0.5)
    def get_all_tabs(self) -> List[Dict[str, Any]]:
        """Get all open tabs with retry and circuit breaker protection."""
        try:
            return self._tab_server_breaker.call(self._get_all_tabs_internal)
        except CircuitBreakerError:
            # Return cached data if available
            if hasattr(self, '_tab_cache') and self._tab_cache:
                logger.warning("Tab server circuit breaker open - returning cached data")
                return self._tab_cache
            return []
        except Exception as e:
            self._record_error('tab_server_connection', f"Failed to get tabs: {e}", ErrorSeverity.HIGH)
            logger.error(f"Failed to get tabs: {e}")
            return []
    
    def _get_all_tabs_internal(self) -> List[Dict[str, Any]]:
        """Internal method to get all tabs."""
        if not self._ensure_tab_server_running():
            raise ConnectionError("Tab server not available")
        
        response = requests.get(f"{self._tab_server_url}/api/tabs", timeout=5)
        response.raise_for_status()
        tabs = response.json().get('tabs', [])
        
        # Cache the result
        self._tab_cache = tabs
        self._record_success("get_all_tabs")
        return tabs
    
    def _ensure_tab_server_running(self) -> bool:
        """Ensure the tab server process is running."""
        try:
            if self._check_tab_server_status():
                return True
            
            if self._process_manager and self._process_manager.start():
                # Wait for server to become responsive with polling
                for i in range(10):
                    if self._check_tab_server_status():
                        return True
                    time.sleep(0.5 if i < 5 else 1.0)
            
            return False
        except Exception as e:
            logger.error(f"Error ensuring tab server running: {e}")
            return False
    
    def _check_tab_server_status(self) -> bool:
        """Check if tab server is responsive."""
        try:
            response = requests.get(f"{self._tab_server_url}/api/status", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def _legacy_get_all_tabs(self) -> List[Dict[str, Any]]:
        """Legacy method for getting tabs when direct API is not available."""
        try:
            if self._tab_server:
                tabs_data = self._tab_server.get_tabs()
                if tabs_data:
                    # Process tab data to ensure consistent format
                    processed_tabs = []
                    for tab in tabs_data:
                        processed_tab = {
                            'tab_id': tab.get('id', ''),
                            'window_id': tab.get('windowId', ''),
                            'url': tab.get('url', ''),
                            'title': tab.get('title', ''),
                            'browser': tab.get('browser', ''),
                            'active': tab.get('active', False),
                            'domain': self._extract_domain(tab.get('url', '')),
                            'timestamp': tab.get('timestamp', current_time)
                        }
                        processed_tabs.append(processed_tab)
                    
                    self._tab_cache = processed_tabs
                    self._last_update_time = current_time
                    return processed_tabs
            
            # Fall back to HTTP API if direct access fails
            response = requests.get(f"{self._tab_server_url}/api/tabs")
            if response.status_code == 200:
                tabs_data = response.json()
                
                # Handle different response formats
                if isinstance(tabs_data, dict) and 'tabs' in tabs_data:
                    # Tab server returns {"tabs": [...]} format
                    tabs_data = tabs_data['tabs']
                elif not isinstance(tabs_data, list):
                    logger.warning(f"Expected list or dict with 'tabs' key from tab server, got {type(tabs_data)}: {tabs_data}")
                    return self._tab_cache if self._tab_cache else []
                
                # Process tab data to ensure consistent format
                processed_tabs = []
                for tab in tabs_data:
                    if not isinstance(tab, dict):
                        logger.warning(f"Expected dict for tab, got {type(tab)}: {tab}")
                        continue
                    processed_tab = {
                        'tab_id': tab.get('id', ''),
                        'window_id': tab.get('windowId', ''),
                        'url': tab.get('url', ''),
                        'title': tab.get('title', ''),
                        'browser': tab.get('browser', ''),
                        'active': tab.get('active', False),
                        'domain': self._extract_domain(tab.get('url', '')),
                        'timestamp': tab.get('timestamp', current_time)
                    }
                    processed_tabs.append(processed_tab)
                
                self._tab_cache = processed_tabs
                self._last_update_time = current_time
                return processed_tabs
            else:
                logger.warning(f"Failed to get tab data: {response.status_code}")
                return self._tab_cache if self._tab_cache else []
        except Exception as e:
            logger.error(f"Error getting tabs from tab server: {e}")
            return self._tab_cache if self._tab_cache else []
    
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """Get the currently active tab.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing information about the active tab,
                                     or None if no tab is active
        """
        # Ensure the tab server is running
        if not self._ensure_tab_server_running():
            return None
            
        # Try to get the active tab directly from the tab server object first
        if self._tab_server:
            try:
                active_tab = self._tab_server.get_active_tab()
                if active_tab:
                    # Process tab data to ensure consistent format
                    current_time = time.time()
                    processed_tab = {
                        'tab_id': active_tab.get('id', ''),
                        'window_id': active_tab.get('windowId', ''),
                        'url': active_tab.get('url', ''),
                        'title': active_tab.get('title', ''),
                        'browser': active_tab.get('browser', ''),
                        'active': True,
                        'domain': self._extract_domain(active_tab.get('url', '')),
                        'timestamp': active_tab.get('timestamp', current_time)
                    }
                    return processed_tab
            except Exception as e:
                logger.warning(f"Failed to get active tab directly from tab server: {e}, falling back to HTTP API")
                # Fall through to HTTP API
        
        # Fall back to filtering all tabs
        tabs = self.get_all_tabs()
        active_tabs = [tab for tab in tabs if tab.get('active', False)]
        
        if active_tabs:
            return active_tabs[0]
        return None
    
    def is_extension_connected(self, browser_name: str = None) -> bool:
        """Check if the browser extension is connected.
        
        Args:
            browser_name: Name of the browser to check (optional)
            
        Returns:
            bool: True if the extension is connected, False otherwise
        """
        # Ensure the tab server is running
        if not self._ensure_tab_server_running():
            return False
            
        try:
            # Try to check connection status directly from the tab server object first
            if self._tab_server:
                return self._tab_server.is_extension_connected(browser_name)
                
            # Fall back to HTTP API if direct access fails
            response = requests.get(f"{self._tab_server_url}/api/status")
            if response.status_code == 200:
                status_data = response.json()
                
                if browser_name:
                    # Check specific browser connection status
                    browser_statuses = status_data.get('browser_statuses', {})
                    return browser_statuses.get(browser_name, {}).get('connected', False)
                else:
                    # Check overall extension connection status
                    return status_data.get('extension_connected', False)
            else:
                logger.warning(f"Failed to get extension status: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error checking extension connection: {e}")
            return False
    
    def close_tab(self, tab_id: str, window_id: str = None, browser_name: str = None) -> bool:
        """Close a browser tab.
        
        Args:
            tab_id: ID of the tab to close
            window_id: ID of the window containing the tab (optional)
            browser_name: Name of the browser (optional)
            
        Returns:
            bool: True if the tab was closed successfully, False otherwise
        """
        # Ensure the tab server is running
        if not self._ensure_tab_server_running():
            return False
            
        try:
            command_data = {
                'action': 'close_tab',
                'data': {
                    'tabId': tab_id
                }
            }
            
            if window_id:
                command_data['data']['windowId'] = window_id
            
            # Try to add the command directly to the tab server object first
            if self._tab_server:
                try:
                    self._tab_server.add_command(command_data)
                    logger.info(f"Tab close command queued for tab {tab_id}")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to add command directly to tab server: {e}, falling back to HTTP API")
                    # Fall through to HTTP API
                
            # Fall back to HTTP API if direct access fails
            if browser_name:
                # Add browser parameter to URL
                browser_param = f"?browser={quote(browser_name)}"
                url = f"{self._tab_server_url}/api/command{browser_param}"
            else:
                url = f"{self._tab_server_url}/api/command"
                
            # Use circuit breaker for command requests
            response = self._tab_server_breaker.call(
                lambda: requests.post(url, json=command_data, timeout=10)
            )
            
            if response.status_code == 200:
                result = response.json()
                success = result.get('success', False)
                if not success:
                    self._record_error('command_failures')
                return success
            else:
                logger.warning(f"Failed to close tab: {response.status_code}")
                self._record_error('command_failures')
                return False
                
        except CircuitBreakerError:
            logger.warning("Tab server circuit breaker open - cannot close tab")
            return False
        except Exception as e:
            logger.error(f"Error closing tab: {e}")
            self._record_error('command_failures')
            return False
    
    def send_command(self, command: str, data: Dict[str, Any], browser_name: str = None) -> bool:
        """Send a command to the browser extension.
        
        Args:
            command: Command to send
            data: Data to send with the command
            browser_name: Name of the browser (optional)
            
        Returns:
            bool: True if the command was sent successfully, False otherwise
        """
        # Ensure the tab server is running
        if not self._ensure_tab_server_running():
            return False
            
        try:
            command_data = {
                'action': command,
                'data': data
            }
            
            # Try to add the command directly to the tab server object first
            if self._tab_server:
                try:
                    self._tab_server.add_command(command_data)
                    logger.info(f"Command '{command}' queued successfully")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to add command directly to tab server: {e}, falling back to HTTP API")
                    # Fall through to HTTP API
            
            # Fall back to HTTP API if direct access fails
            if browser_name:
                # Add browser parameter to URL
                browser_param = f"?browser={quote(browser_name)}"
                url = f"{self._tab_server_url}/api/command{browser_param}"
            else:
                url = f"{self._tab_server_url}/api/command"
                
            response = requests.post(url, json=command_data)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False)
            else:
                logger.warning(f"Failed to send command: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL.
        
        Args:
            url: URL to extract domain from
            
        Returns:
            str: Domain name
        """
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
                
            return domain
        except Exception:
            return ''
