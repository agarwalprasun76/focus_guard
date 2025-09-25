"""
Debug script for tab server.

This script runs the tab server directly with verbose logging to diagnose issues.
"""

import os
import sys
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import the tab server
from core.browser_detection.browser_integration.tab_server_v2 import tab_server

def main():
    """Run the tab server with verbose logging."""
    print("Starting tab server in debug mode...")
    
    # Print configuration
    from core.browser_detection.browser_integration.config import Config
    print(f"Host: {Config.SERVER_HOST}")
    print(f"Port: {Config.SERVER_PORT}")
    
    # Start the server
    success = tab_server.start()
    if success:
        print("Tab server started successfully")
        print("Press Ctrl+C to stop the server")
        try:
            # Keep the script running
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping tab server...")
            tab_server.stop()
            print("Tab server stopped")
    else:
        print("Failed to start tab server")

if __name__ == "__main__":
    main()
