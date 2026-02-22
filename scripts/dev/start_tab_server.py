#!/usr/bin/env python3
"""
Tab Server Startup Script

This script starts the Focus Guard tab server and ensures all components are running.
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from focus_guard.core.browser_v2.tab_server.runner import TabServerRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_tab_server_service():
    """Start the tab server service."""
    logger.info("Starting Focus Guard tab server...")
    
    try:
        runner = TabServerRunner(host="127.0.0.1", port=58392)
        success = runner.start()
        if success:
            logger.info("✅ Tab server started successfully on port 58392")
            return True
        else:
            logger.error("❌ Failed to start tab server")
            return False
    except Exception as e:
        logger.error(f"❌ Tab server startup error: {e}")
        return False

def wait_for_server():
    """Wait for server to be ready."""
    import requests
    
    logger.info("Waiting for tab server to be ready...")
    max_attempts = 30
    
    for attempt in range(max_attempts):
        try:
            response = requests.get("http://127.0.0.1:58392/api/status", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Tab server is ready and responding")
                return True
        except:
            pass
        
        time.sleep(1)
        if attempt % 5 == 0:
            logger.info(f"Still waiting... attempt {attempt + 1}/{max_attempts}")
    
    logger.error("❌ Tab server failed to start within timeout")
    return False

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("FOCUS GUARD TAB SERVER STARTUP")
    logger.info("=" * 50)
    
    if start_tab_server_service():
        if wait_for_server():
            logger.info("🎉 Tab server is running and ready for browser extension!")
            logger.info("Browser extension should now be able to connect.")
        else:
            logger.error("❌ Tab server failed to become ready")
    else:
        logger.error("❌ Failed to start tab server")
