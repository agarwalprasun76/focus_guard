def _handle_post_commands(self) -> None:
    """Handle command acknowledgments from the browser extension."""
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    server_instance = self.server.tab_server if hasattr(self.server, 'tab_server') else None
    
    content_length = int(self.headers.get("Content-Length", 0))
    if content_length == 0:
        self._send_json(400, {"error": "No data received"})
        return
    
    try:
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode())
        
        # If the browser acknowledges commands, clear them
        if data.get("status") == "processed":
            # Get browser name if provided
            browser_name = data.get("browser")
            if browser_name:
                logger.info(f"Command acknowledgment from browser: {browser_name}")
            
            if server_instance:
                server_instance.clear_commands()
                self._send_json(200, {"status": "ok"})
            else:
                logger.error("Server instance not available in request handler")
                self._send_json(500, {"error": "Server instance not available"})
        else:
            self._send_json(400, {"error": "Invalid acknowledgment"})
            
    except json.JSONDecodeError:
        self._send_json(400, {"error": "Invalid JSON"})
    except Exception as e:
        logger.error(f"Error processing command acknowledgment: {e}")
        self._send_json(500, {"error": "Internal Server Error"})
