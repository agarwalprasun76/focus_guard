def _handle_get_commands(self) -> None:
    """Handle requests for pending commands."""
    # Parse query parameters to get browser name if provided
    query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
    browser_name = None
    if 'browser' in query_components:
        browser_name = query_components['browser'][0]
        logger.info(f"Command request from browser: {browser_name}")
    
    # Get commands filtered by browser name
    commands = server_instance.get_commands(browser_name)
    self._send_json(200, {"commands": commands})


