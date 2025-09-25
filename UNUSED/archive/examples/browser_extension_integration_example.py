"""
Browser Extension Integration Example

This example demonstrates how to use the browser extension integration components
in the core_v2 architecture, including tab server, process management, extension
management, and domain blocking.
"""

import logging
import time
import sys
from typing import Dict, Any, List

from core_v2.browser.models.browser import BrowserType
from core_v2.browser.extension.integration import get_extension_integration
from core_v2.browser.extension.domain_blocking import get_domain_blocking_integration
from core_v2.config.factory import ConfigurationFactory


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main function demonstrating browser extension integration."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting browser extension integration example")
    
    # Initialize configuration
    config_factory = ConfigurationFactory()
    config_manager = config_factory.create_configuration_manager()
    
    # Initialize extension integration (this will auto-start the tab server)
    logger.info("Initializing extension integration")
    integration = get_extension_integration(auto_start_tab_server=True)
    
    # Initialize domain blocking integration
    logger.info("Initializing domain blocking integration")
    domain_blocking = get_domain_blocking_integration(config_manager=config_manager)
    
    # Check if Chrome extension is installed
    if integration.is_extension_installed(BrowserType.CHROME):
        logger.info("Chrome extension is already installed")
    else:
        logger.info("Installing Chrome extension")
        if integration.install_extension(BrowserType.CHROME):
            logger.info("Chrome extension installed successfully")
        else:
            logger.warning("Failed to install Chrome extension")
    
    # Wait for extension connection
    logger.info("Waiting for extension connection...")
    connection_timeout = 30  # seconds
    start_time = time.time()
    extension_connected = False
    
    while time.time() - start_time < connection_timeout:
        if integration.verify_extension_connection(BrowserType.CHROME):
            logger.info("Extension connected successfully")
            extension_connected = True
            break
        time.sleep(1)
    
    if not extension_connected:
        logger.warning("Extension connection timed out")
        logger.info("Please make sure the extension is installed and the browser is running")
        logger.info("You can manually install the extension from the extension directory")
    
    # Get all tabs
    logger.info("Getting all tabs")
    tabs = integration.get_all_tabs()
    logger.info(f"Found {len(tabs)} tabs")
    
    # Print tab information
    for i, tab in enumerate(tabs):
        logger.info(f"Tab {i+1}:")
        logger.info(f"  Title: {tab.get('title', 'Unknown')}")
        logger.info(f"  URL: {tab.get('url', 'Unknown')}")
        logger.info(f"  Browser: {tab.get('browser', 'Unknown')}")
        
        # Check if tab should be blocked
        url = tab.get('url', '')
        if url and domain_blocking.should_block_url(url):
            logger.info(f"  Status: Should be blocked")
        else:
            logger.info(f"  Status: Allowed")
    
    # Get active tab
    active_tab = integration.get_active_tab()
    if active_tab:
        logger.info(f"Active tab: {active_tab.get('title', 'Unknown')} - {active_tab.get('url', 'Unknown')}")
    else:
        logger.info("No active tab found")
    
    # Close blocked tabs (if extension is connected)
    if extension_connected:
        logger.info("Checking for tabs to block")
        closed_count = domain_blocking.close_blocked_tabs()
        if closed_count > 0:
            logger.info(f"Closed {closed_count} blocked tabs")
        else:
            logger.info("No blocked tabs found")
    
    # Get tab server status
    status = integration.get_tab_server_status()
    logger.info(f"Tab server status: {status}")
    
    logger.info("Example completed")


if __name__ == "__main__":
    main()
