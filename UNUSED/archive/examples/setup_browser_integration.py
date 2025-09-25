"""
Setup script for browser integration testing.

This script helps set up the necessary components for testing the browser integration:
1. Starts the legacy tab server from the existing implementation
2. Configures the new browser detection components to work with it
"""

import os
import sys
import time
import logging
import subprocess
import socket
import platform
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def is_port_in_use(port):
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def start_tab_server():
    """Start the legacy tab server."""
    logger.info("Starting legacy tab server...")
    
    # Check if the server is already running
    if is_port_in_use(5000):
        logger.info("Tab server is already running on port 5000")
        return True
    
    # Determine the path to the tab server script
    tab_server_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'core', 
        'browser_detection',
        'browser_integration',
        'tab_server_v2.py'
    ))
    
    # Start the tab server as a background process
    try:
        if platform.system() == "Windows":
            process = subprocess.Popen(
                [sys.executable, tab_server_path],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        else:
            process = subprocess.Popen(
                [sys.executable, tab_server_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setpgrp
            )
        
        # Wait a moment for the server to start
        time.sleep(2)
        
        # Check if the process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            logger.error(f"Tab server failed to start: {stderr.decode() if stderr else ''}")
            return False
        
        # Verify the server is actually accepting connections
        for _ in range(5):  # Try 5 times
            if is_port_in_use(5000):
                logger.info(f"Tab server started with PID: {process.pid}")
                return True
            time.sleep(1)
        
        logger.error("Tab server started but is not accepting connections")
        return False
    
    except Exception as e:
        logger.error(f"Error starting tab server: {e}")
        return False


def ensure_extension_installed():
    """Check if the browser extension is installed and provide instructions if not."""
    # Path to the extension installation script
    install_script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "core", "browser_detection", "webextension_mv3", "install_focus_guard_extension.bat"
    )
    
    if not os.path.exists(install_script):
        logger.warning("Extension installation script not found.")
        logger.warning("Please manually install the extension from the webextension_mv3 directory.")
        return False
    
    logger.info("To install the browser extension, run the following script:")
    logger.info(f"  {install_script}")
    logger.info("This will install the extension in Chrome/Edge for testing.")
    
    return True


def main():
    """Main function."""
    logger.info("Setting up browser integration for testing...")
    
    # Start the legacy tab server
    if not start_tab_server():
        logger.error("Failed to start tab server. Exiting.")
        return
        
    # Check extension installation
    ensure_extension_installed()
    
    # Print instructions
    print("\n" + "="*80)
    print("BROWSER INTEGRATION TESTING SETUP")
    print("="*80)
    print("\nThe legacy tab server is now running on http://localhost:8000")
    print("\nTo test the new browser detection components:")
    print("1. Make sure the browser extension is installed (see instructions above)")
    print("2. Run the browser_detection_example.py script:")
    print("   python examples/browser_detection_example.py")
    print("\nThis will use the new components with the existing extension.")
    print("\nPress Ctrl+C to stop the tab server when done testing.")
    print("="*80 + "\n")
    
    try:
        # Keep the script running until interrupted
        while True:
            time.sleep(1)
            
            # Check if tab server is still running (only if we started it)
            if not server_already_running and tab_server_process and tab_server_process.poll() is not None:
                stdout, stderr = tab_server_process.communicate()
                logger.error(f"Tab server stopped unexpectedly: {stderr}")
                break
    except KeyboardInterrupt:
        if not server_already_running and tab_server_process:
            logger.info("Stopping tab server...")
            tab_server_process.terminate()
            try:
                tab_server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                tab_server_process.kill()
            logger.info("Tab server stopped.")
        else:
            logger.info("Exiting (tab server was already running, not stopping it)")


if __name__ == "__main__":
    main()
