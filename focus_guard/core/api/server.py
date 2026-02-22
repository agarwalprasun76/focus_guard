"""
API Server for Focus Guard.

This module provides a simple API server implementation for Focus Guard,
allowing external applications to interact with the system.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List, Awaitable

from aiohttp import web
import json

from focus_guard.core.tab_server_endpoint import DEFAULT_TAB_SERVER_HOST
from focus_guard.core.tab_server_endpoint import DEFAULT_TAB_SERVER_PORT


class ApiServer:
    """
    API Server for Focus Guard.
    
    This class provides a simple HTTP API server for Focus Guard,
    allowing external applications to interact with the system.
    """
    
    def __init__(self):
        """Initialize the API server."""
        self._logger = logging.getLogger("core.api.server")
        self._app = web.Application()
        self._runner = None
        self._site = None
        self._host = DEFAULT_TAB_SERVER_HOST
        self._port = DEFAULT_TAB_SERVER_PORT
        self._running = False
        self._request_handlers = []
        self._routes_initialized = False
    
    async def initialize(
        self,
        host: str = DEFAULT_TAB_SERVER_HOST,
        port: int = DEFAULT_TAB_SERVER_PORT,
    ) -> None:
        """
        Initialize the API server with the given host and port.
        
        Args:
            host (str): The host to bind to.
            port (int): The port to bind to.
        """
        self._host = host
        self._port = port
        
        if not self._routes_initialized:
            # Set up routes
            self._app.router.add_get("/", self._handle_index)
            self._app.router.add_get("/status", self._handle_status)
            self._app.router.add_post("/api/{endpoint}", self._handle_api_request)
            
            # Set up middleware
            self._app.middlewares.append(self._error_middleware)
            
            self._routes_initialized = True
        
        self._logger.info(f"API server initialized with host={host}, port={port}")
    
    async def start(self) -> None:
        """Start the API server."""
        if self._running:
            self._logger.warning("API server is already running")
            return
        
        try:
            self._runner = web.AppRunner(self._app)
            await self._runner.setup()
            self._site = web.TCPSite(self._runner, self._host, self._port)
            await self._site.start()
            self._running = True
            self._logger.info(f"API server started at http://{self._host}:{self._port}")
        except Exception as e:
            self._logger.exception(f"Error starting API server: {e}")
            self._running = False
            raise
    
    async def stop(self) -> None:
        """Stop the API server."""
        if not self._running:
            self._logger.warning("API server is not running")
            return
        
        try:
            if self._site:
                await self._site.stop()
                self._site = None
            
            if self._runner:
                await self._runner.cleanup()
                self._runner = None
            
            self._running = False
            self._logger.info("API server stopped")
        except Exception as e:
            self._logger.exception(f"Error stopping API server: {e}")
            raise
    
    def is_running(self) -> bool:
        """
        Check if the API server is running.
        
        Returns:
            bool: True if the API server is running, False otherwise.
        """
        return self._running
    
    def on_request(self, handler: Callable[[str, str, Dict[str, Any]], Awaitable[None]]) -> None:
        """
        Register a handler for API requests.
        
        Args:
            handler: A function that takes an endpoint, method, and data and handles the request.
        """
        self._request_handlers.append(handler)
    
    @web.middleware
    async def _error_middleware(self, request, handler):
        """Middleware to handle errors and return appropriate JSON responses."""
        try:
            return await handler(request)
        except web.HTTPException as ex:
            return web.json_response(
                {"error": ex.reason},
                status=ex.status
            )
        except Exception as e:
            self._logger.exception(f"Unhandled error in API request: {e}")
            return web.json_response(
                {"error": "Internal server error"},
                status=500
            )
    
    async def _handle_index(self, request: web.Request) -> web.Response:
        """Handle requests to the index endpoint."""
        return web.json_response({
            "name": "Focus Guard API",
            "version": "2.0.0",
            "status": "running"
        })
    
    async def _handle_status(self, request: web.Request) -> web.Response:
        """Handle requests to the status endpoint."""
        return web.json_response({
            "status": "running",
            "uptime": "unknown"  # Could be implemented with a start time
        })
    
    async def _handle_api_request(self, request: web.Request) -> web.Response:
        """Handle API requests to specific endpoints."""
        endpoint = request.match_info.get("endpoint", "")
        method = request.method
        
        try:
            # Parse request data
            if request.content_type == "application/json":
                data = await request.json()
            else:
                data = {}
                if request.method == "POST":
                    post_data = await request.post()
                    for key, value in post_data.items():
                        data[key] = value
            
            # Notify handlers
            for handler in self._request_handlers:
                await handler(endpoint, method, data)
            
            # Return a simple acknowledgement
            return web.json_response({
                "status": "success",
                "endpoint": endpoint,
                "method": method
            })
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON in request body"},
                status=400
            )
        except Exception as e:
            self._logger.exception(f"Error handling API request: {e}")
            return web.json_response(
                {"error": f"Error processing request: {str(e)}"},
                status=500
            )
