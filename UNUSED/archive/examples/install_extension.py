"""
Extension installation helper for Focus Guard.

This script helps install and verify the browser extension for Focus Guard.
"""

import os
import sys
import logging
import webbrowser
import platform
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def get_extension_path():
    """Get the path to the extension directory."""
    extension_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        '..',
        'core',
        'browser_detection',
        'webextension_mv3'
    ))
    return extension_path

def open_chrome_extensions():
    """Open Chrome extensions page."""
    webbrowser.get('chrome').open('chrome://extensions/')
    logger.info("Opened Chrome extensions page")
    
def open_edge_extensions():
    """Open Edge extensions page."""
    try:
        webbrowser.get('edge').open('edge://extensions/')
        logger.info("Opened Edge extensions page")
    except Exception:
        logger.info("Could not open Edge extensions page directly. Opening manually...")
        webbrowser.open('microsoft-edge://extensions/')

def install_extension_instructions():
    """Print instructions for installing the extension."""
    extension_path = get_extension_path()
    
    print("\n" + "="*80)
    print("FOCUS GUARD EXTENSION INSTALLATION INSTRUCTIONS")
    print("="*80)
    
    print(f"\nExtension location: {extension_path}")
    
    print("\nTo install in Chrome:")
    print("1. Enable Developer Mode (toggle in top-right corner)")
    print("2. Click 'Load unpacked'")
    print(f"3. Select this folder: {extension_path}")
    print("4. Verify the extension is enabled (toggle should be on)")
    
    print("\nTo install in Edge:")
    print("1. Enable Developer Mode (toggle in bottom-left corner)")
    print("2. Click 'Load unpacked'")
    print(f"3. Select this folder: {extension_path}")
    print("4. Verify the extension is enabled (toggle should be on)")
    
    print("\nAfter installation:")
    print("1. The extension icon should appear in your browser toolbar")
    print("2. You may need to restart your browser for the extension to fully activate")
    print("3. Run the debug_tab_server.py script to verify tab detection is working")
    print("="*80 + "\n")

def verify_extension_config():
    """Verify the extension configuration."""
    extension_path = get_extension_path()
    
    # Check if the extension directory exists
    if not os.path.exists(extension_path):
        logger.error(f"Extension directory not found: {extension_path}")
        return False
    
    # Check if manifest.json exists
    manifest_path = os.path.join(extension_path, 'manifest.json')
    if not os.path.exists(manifest_path):
        logger.error(f"Manifest file not found: {manifest_path}")
        return False
    
    # Check if background.js exists
    background_path = os.path.join(extension_path, 'background.js')
    if not os.path.exists(background_path):
        logger.error(f"Background script not found: {background_path}")
        return False
    
    logger.info("Extension files verified successfully")
    return True

def main():
    """Main function."""
    logger.info("Starting extension installation helper...")
    
    # Verify extension files
    if not verify_extension_config():
        logger.error("Extension verification failed. Please check the extension files.")
        return
    
    # Open extension pages in browsers
    try:
        open_chrome_extensions()
    except Exception as e:
        logger.error(f"Could not open Chrome extensions page: {e}")
    
    try:
        open_edge_extensions()
    except Exception as e:
        logger.error(f"Could not open Edge extensions page: {e}")
    
    # Show installation instructions
    install_extension_instructions()
    
    # Prompt to continue
    input("Press Enter after installing the extension to continue...")
    
    # Suggest next steps
    print("\nNext steps:")
    print("1. Run the debug tab server to verify tab detection:")
    print("   python examples/debug_tab_server.py")
    print("2. Run the integration test script:")
    print("   python examples/test_browser_integration.py")
    print("\nIf tabs are still not detected, check browser console for extension errors.")

if __name__ == "__main__":
    main()
