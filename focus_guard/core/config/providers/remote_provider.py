"""
Remote configuration provider.

This module provides a remote configuration provider implementation
that fetches configuration data from a remote server.
"""

from typing import Any, Dict, Optional, Set, List, Tuple
import copy
import json
import threading
import logging
import time
import urllib.request
import urllib.error
import urllib.parse
import ssl
import os

from focus_guard.core.config.interfaces import ConfigPath, ConfigProvider, ConfigScope
from focus_guard.core.config.providers.memory_provider import MemoryConfigProvider


class RemoteConfigProvider(ConfigProvider):
    """
    Remote configuration provider.
    
    This provider fetches configuration data from a remote server,
    with support for caching, authentication, and fallback to local cache.
    """
    
    def __init__(
        self,
        base_url: str,
        cache_dir: Optional[str] = None,
        auth_token: Optional[str] = None,
        refresh_interval: int = 300,  # 5 minutes
        timeout: int = 10,
        verify_ssl: bool = True,
        scope: ConfigScope = ConfigScope.REMOTE
    ):
        """
        Initialize the remote provider.
        
        Args:
            base_url: Base URL of the remote configuration server.
            cache_dir: Directory to store cached configuration data.
            auth_token: Authentication token for the remote server.
            refresh_interval: Interval in seconds to refresh the configuration.
            timeout: Timeout in seconds for HTTP requests.
            verify_ssl: Whether to verify SSL certificates.
            scope: The configuration scope.
        """
        self._base_url = base_url.rstrip('/')
        self._cache_dir = cache_dir
        self._auth_token = auth_token
        self._refresh_interval = refresh_interval
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._scope = scope
        self._lock = threading.RLock()
        self._cache = MemoryConfigProvider()
        self._last_refresh = 0
        self._logger = logging.getLogger(__name__)
        
        # Create cache directory if specified
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
    
    def get_name(self) -> str:
        """
        Get the provider name.
        
        Returns:
            The provider name.
        """
        return "remote"
    
    def get_value(self, path: ConfigPath, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            path: The configuration path.
            default: The default value to return if the path does not exist.
            
        Returns:
            The configuration value, or the default value if the path does not exist.
        """
        with self._lock:
            # Check if we need to refresh the cache
            self._refresh_if_needed()
            
            # Get the value from the cache
            return self._cache.get_value(path, default)
    
    def set_value(self, path: ConfigPath, value: Any) -> bool:
        """
        Set a configuration value.
        
        Args:
            path: The configuration path.
            value: The value to set.
            
        Returns:
            True if the value was set successfully, False otherwise.
        """
        with self._lock:
            # Update the cache
            self._cache.set_value(path, value)
            
            # Send the update to the remote server
            return self._send_update(path, value)
    
    def delete_value(self, path: ConfigPath) -> bool:
        """
        Delete a configuration value.
        
        Args:
            path: The configuration path.
            
        Returns:
            True if the value was deleted successfully, False otherwise.
        """
        with self._lock:
            # Update the cache
            self._cache.delete_value(path)
            
            # Send the delete request to the remote server
            return self._send_delete(path)
    
    def has_value(self, path: ConfigPath) -> bool:
        """
        Check if a configuration path exists.
        
        Args:
            path: The configuration path.
            
        Returns:
            True if the path exists, False otherwise.
        """
        with self._lock:
            # Check if we need to refresh the cache
            self._refresh_if_needed()
            
            # Check if the path exists in the cache
            return self._cache.has_value(path)
    
    def get_all_paths(self, prefix: Optional[str] = None) -> Set[ConfigPath]:
        """
        Get all configuration paths.
        
        Args:
            prefix: Optional prefix to filter paths.
            
        Returns:
            A set of configuration paths.
        """
        with self._lock:
            # Check if we need to refresh the cache
            self._refresh_if_needed()
            
            # Get all paths from the cache
            return self._cache.get_all_paths(prefix)
    
    def get_scope(self) -> ConfigScope:
        """
        Get the provider scope.
        
        Returns:
            The provider scope.
        """
        return self._scope
    
    def load(self) -> bool:
        """
        Load the configuration data.
        
        Returns:
            True if the data was loaded successfully, False otherwise.
        """
        with self._lock:
            # Try to load from the remote server
            success = self._refresh_from_remote()
            
            if not success and self._cache_dir:
                # Try to load from the local cache
                success = self._load_from_cache()
            
            return success
    
    def save(self) -> bool:
        """
        Save the configuration data.
        
        Returns:
            True if the data was saved successfully, False otherwise.
        """
        with self._lock:
            # Get all data from the cache
            data = self._cache.get_data()
            
            # Send the data to the remote server
            success = self._send_all(data)
            
            if success and self._cache_dir:
                # Save to the local cache
                success = self._save_to_cache(data)
            
            return success
    
    def clear(self) -> bool:
        """
        Clear the configuration data.
        
        Returns:
            True if the data was cleared successfully, False otherwise.
        """
        with self._lock:
            # Clear the cache
            self._cache.clear()
            
            # Send the clear request to the remote server
            return self._send_clear()
    
    def _refresh_if_needed(self) -> None:
        """
        Refresh the cache if needed.
        """
        current_time = time.time()
        
        if current_time - self._last_refresh > self._refresh_interval:
            self._refresh_from_remote()
    
    def _refresh_from_remote(self) -> bool:
        """
        Refresh the cache from the remote server.
        
        Returns:
            True if the refresh was successful, False otherwise.
        """
        try:
            # Build the URL
            url = f"{self._base_url}/config"
            
            # Send the request
            response = self._send_request("GET", url)
            
            if response:
                # Parse the response
                data = json.loads(response)
                
                # Update the cache
                self._cache.set_data(data)
                
                # Update the last refresh time
                self._last_refresh = time.time()
                
                # Save to the local cache if specified
                if self._cache_dir:
                    self._save_to_cache(data)
                
                return True
        except Exception as e:
            self._logger.error(f"Failed to refresh from remote server: {e}")
        
        return False
    
    def _send_update(self, path: ConfigPath, value: Any) -> bool:
        """
        Send an update to the remote server.
        
        Args:
            path: The configuration path.
            value: The value to set.
            
        Returns:
            True if the update was successful, False otherwise.
        """
        try:
            # Build the URL
            url = f"{self._base_url}/config/{urllib.parse.quote(path)}"
            
            # Prepare the data
            data = json.dumps({"value": value}).encode("utf-8")
            
            # Send the request
            response = self._send_request("PUT", url, data)
            
            return response is not None
        except Exception as e:
            self._logger.error(f"Failed to send update for path '{path}': {e}")
            return False
    
    def _send_delete(self, path: ConfigPath) -> bool:
        """
        Send a delete request to the remote server.
        
        Args:
            path: The configuration path.
            
        Returns:
            True if the delete was successful, False otherwise.
        """
        try:
            # Build the URL
            url = f"{self._base_url}/config/{urllib.parse.quote(path)}"
            
            # Send the request
            response = self._send_request("DELETE", url)
            
            return response is not None
        except Exception as e:
            self._logger.error(f"Failed to send delete for path '{path}': {e}")
            return False
    
    def _send_all(self, data: Dict[str, Any]) -> bool:
        """
        Send all configuration data to the remote server.
        
        Args:
            data: The configuration data.
            
        Returns:
            True if the send was successful, False otherwise.
        """
        try:
            # Build the URL
            url = f"{self._base_url}/config"
            
            # Prepare the data
            data_json = json.dumps(data).encode("utf-8")
            
            # Send the request
            response = self._send_request("POST", url, data_json)
            
            return response is not None
        except Exception as e:
            self._logger.error(f"Failed to send all configuration data: {e}")
            return False
    
    def _send_clear(self) -> bool:
        """
        Send a clear request to the remote server.
        
        Returns:
            True if the clear was successful, False otherwise.
        """
        try:
            # Build the URL
            url = f"{self._base_url}/config/clear"
            
            # Send the request
            response = self._send_request("POST", url)
            
            return response is not None
        except Exception as e:
            self._logger.error(f"Failed to send clear request: {e}")
            return False
    
    def _send_request(self, method: str, url: str, data: Optional[bytes] = None) -> Optional[str]:
        """
        Send an HTTP request to the remote server.
        
        Args:
            method: The HTTP method.
            url: The URL.
            data: Optional data to send.
            
        Returns:
            The response body, or None if the request failed.
        """
        try:
            # Create the request
            request = urllib.request.Request(url, data=data, method=method)
            
            # Add headers
            request.add_header("Content-Type", "application/json")
            
            if self._auth_token:
                request.add_header("Authorization", f"Bearer {self._auth_token}")
            
            # Create SSL context if needed
            context = None
            if not self._verify_ssl:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            
            # Send the request
            with urllib.request.urlopen(request, timeout=self._timeout, context=context) as response:
                # Read the response
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            self._logger.error(f"HTTP error: {e.code} {e.reason}")
            return None
        except urllib.error.URLError as e:
            self._logger.error(f"URL error: {e.reason}")
            return None
        except Exception as e:
            self._logger.error(f"Request error: {e}")
            return None
    
    def _load_from_cache(self) -> bool:
        """
        Load configuration data from the local cache.
        
        Returns:
            True if the load was successful, False otherwise.
        """
        if not self._cache_dir:
            return False
        
        try:
            # Build the cache file path
            cache_file = os.path.join(self._cache_dir, "remote_config.json")
            
            # Check if the cache file exists
            if not os.path.exists(cache_file):
                return False
            
            # Read the cache file
            with open(cache_file, "r") as f:
                data = json.load(f)
            
            # Update the cache
            self._cache.set_data(data)
            
            return True
        except Exception as e:
            self._logger.error(f"Failed to load from cache: {e}")
            return False
    
    def _save_to_cache(self, data: Dict[str, Any]) -> bool:
        """
        Save configuration data to the local cache.
        
        Args:
            data: The configuration data.
            
        Returns:
            True if the save was successful, False otherwise.
        """
        if not self._cache_dir:
            return False
        
        try:
            # Build the cache file path
            cache_file = os.path.join(self._cache_dir, "remote_config.json")
            
            # Write the cache file
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            self._logger.error(f"Failed to save to cache: {e}")
            return False
