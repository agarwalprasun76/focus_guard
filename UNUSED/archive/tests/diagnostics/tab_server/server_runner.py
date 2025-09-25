#!/usr/bin/env python3
"""
Simple script to start the tab server for testing.
"""
import sys
import os
import time

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from core.browser_integration.tab_server import get_tab_server
from core.logger.logger import get_logger

# Setup logger
logger = get_logger("tab_server.runner")

def main():
    """Start the tab server and keep it running."""
    try:
        logger.info("Starting tab server...")
        tab_server = get_tab_server()
        tab_server.start()
        
        logger.info(f"Tab server started on port {tab_server.port}")
        logger.info("Press Ctrl+C to stop the server")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\nStopping tab server...")
        tab_server.stop()
        logger.info("Tab server stopped")
    except Exception as e:
        logger.error(f"Error in tab server: {e}")
        if 'tab_server' in locals():
            tab_server.stop()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
