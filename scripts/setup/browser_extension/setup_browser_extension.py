#!/usr/bin/env python3
"""
Browser Extension Setup Script

This script sets up the complete browser extension integration including:
1. Native messaging host installation
2. Registry entries for Windows
3. Manifest files for different browsers
4. Tab server configuration
"""

import os
import sys
import json
import platform
import subprocess
from pathlib import Path

def setup_browser_extension():
    """Set up the complete browser extension integration."""
    
    # Fix the path to point to the correct extension directory
    project_root = Path(__file__).parent.parent.parent  # Go up one more level to reach the actual project root
    extension_dir = project_root / "focus_guard" / "core" / "browser" / "extension"
    manifests_dir = extension_dir / "manifests"
    
    print(f"Setting up browser extension integration...")
    print(f"Extension directory: {extension_dir}")
    print(f"Manifests directory: {manifests_dir}")
    
    # Ensure directories exist
    manifests_dir.mkdir(parents=True, exist_ok=True)
    
    # Get the correct paths based on platform
    if platform.system() == 'Windows':
        app_data = Path(os.environ.get('APPDATA', ''))
        chrome_manifest_dir = app_data / 'Google' / 'Chrome' / 'User Data' / 'NativeMessagingHosts'
        edge_manifest_dir = app_data / 'Microsoft' / 'Edge' / 'User Data' / 'NativeMessagingHosts'
        firefox_manifest_dir = Path.home() / 'AppData' / 'Roaming' / 'Mozilla' / 'NativeMessagingHosts'
    else:
        home = Path.home()
        chrome_manifest_dir = home / '.config' / 'google-chrome' / 'NativeMessagingHosts'
        edge_manifest_dir = home / '.config' / 'microsoft-edge' / 'NativeMessagingHosts'
        firefox_manifest_dir = home / '.mozilla' / 'native-messaging-hosts'
    
    # Create native host executable paths
    native_host_script = extension_dir / "focus_guard_native_host.py"
    
    # Create the native host script
    with open(native_host_script, 'w') as f:
        f.write('''#!/usr/bin/env python3
"""
Focus Guard Native Messaging Host

This script acts as a bridge between browser extensions and the Focus Guard application.
"""

import sys
import json
import struct
import logging
import threading
import asyncio
from typing import Dict, Any
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from focus_guard.core.config.windows_config import WindowsConfig
from focus_guard.core.browser.extension.tab_server import get_tab_server, TabServerConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=os.path.join(os.path.dirname(__file__), 'native_host.log')
)
logger = logging.getLogger(__name__)

class FocusGuardNativeHost:
    def __init__(self):
        self.running = True
        self.config = WindowsConfig()
        self.tab_server = None
        
    def send_message(self, message: Dict[str, Any]):
        """Send a message to the browser extension."""
        try:
            encoded_content = json.dumps(message).encode('utf-8')
            encoded_length = struct.pack('@I', len(encoded_content))
            sys.stdout.buffer.write(encoded_length)
            sys.stdout.buffer.write(encoded_content)
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            
    def read_message(self) -> Dict[str, Any]:
        """Read a message from the browser extension."""
        try:
            raw_length = sys.stdin.buffer.read(4)
            if len(raw_length) == 0:
                sys.exit(0)
            message_length = struct.unpack('@I', raw_length)[0]
            message = sys.stdin.buffer.read(message_length).decode('utf-8')
            return json.loads(message)
        except Exception as e:
            logger.error(f"Error reading message: {e}")
            return {'action': 'error', 'error': str(e)}
            
    def ensure_tab_server_running(self):
        """Ensure the tab server is running."""
        try:
            if self.tab_server is None:
                config = self.config.load_config()
                tab_server_config = TabServerConfig(
                    host=config.get('tab_server_host', '127.0.0.1'),
                    port=config.get('tab_server_port', 5000)
                )
                self.tab_server = get_tab_server(tab_server_config)
                
            # Check if server is running
            import requests
            try:
                response = requests.get(f"http://{self.tab_server.config.host}:{self.tab_server.config.port}/api/status", timeout=2)
                if response.status_code == 200:
                    return True
            except:
                pass
                
            # Start the server if not running
            self.tab_server.start()
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring tab server running: {e}")
            return False
            
    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming messages from the browser extension."""
        try:
            action = message.get('action')
            
            if action == 'ping':
                return {'status': 'success', 'message': 'pong'}
                
            elif action == 'get_status':
                return {
                    'status': 'success',
                    'running': True,
                    'tab_server_running': self.ensure_tab_server_running()
                }
                
            elif action == 'close_tab':
                tab_data = message.get('tab_data', {})
                if self.ensure_tab_server_running():
                    # Forward to tab server
                    import requests
                    try:
                        response = requests.post(
                            f"http://{self.tab_server.config.host}:{self.tab_server.config.port}/api/command",
                            json=tab_data,
                            timeout=5
                        )
                        return response.json()
                    except Exception as e:
                        return {'status': 'error', 'message': str(e)}
                else:
                    return {'status': 'error', 'message': 'Tab server not available'}
                    
            elif action == 'get_tabs':
                if self.ensure_tab_server_running():
                    import requests
                    try:
                        response = requests.get(
                            f"http://{self.tab_server.config.host}:{self.tab_server.config.port}/api/tabs",
                            timeout=5
                        )
                        return response.json()
                    except Exception as e:
                        return {'status': 'error', 'message': str(e)}
                else:
                    return {'status': 'error', 'message': 'Tab server not available'}
                    
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return {'status': 'error', 'message': str(e)}
            
    def run(self):
        """Run the native messaging host."""
        try:
            logger.info("Focus Guard Native Host started")
            while True:
                message = self.read_message()
                response = self.handle_message(message)
                self.send_message(response)
        except KeyboardInterrupt:
            logger.info("Native host interrupted")
        except Exception as e:
            logger.error(f"Error in native host: {e}")

if __name__ == '__main__':
    host = FocusGuardNativeHost()
    host.run()
''')
    
    # Make it executable
    if platform.system() != 'Windows':
        os.chmod(native_host_script, 0o755)
    
    # Create batch file for Windows
    if platform.system() == 'Windows':
        batch_file = extension_dir / "focus_guard_native_host.bat"
        with open(batch_file, 'w') as f:
            f.write(f'''@echo off
python "{native_host_script}" %*
''')
    
    # Create manifest files
    create_manifests(manifests_dir, str(native_host_script))
    
    # Create registry entries for Windows
    if platform.system() == 'Windows':
        try:
            import winreg
            # Chrome registry entry
            chrome_key_path = r"SOFTWARE\Google\Chrome\NativeMessagingHosts\com.focusguard.native"
            chrome_key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, chrome_key_path)
            chrome_manifest_path = str(manifests_dir / "chrome_native_host.json")
            winreg.SetValueEx(chrome_key, "", 0, winreg.REG_SZ, chrome_manifest_path)
            winreg.CloseKey(chrome_key)
            print(f"Chrome registry entry created: {chrome_key_path}")
            
            # Edge registry entry
            edge_key_path = r"SOFTWARE\Microsoft\Edge\NativeMessagingHosts\com.focusguard.native"
            edge_key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, edge_key_path)
            edge_manifest_path = str(manifests_dir / "edge_native_host.json")
            winreg.SetValueEx(edge_key, "", 0, winreg.REG_SZ, edge_manifest_path)
            winreg.CloseKey(edge_key)
            print(f"Edge registry entry created: {edge_key_path}")
        except Exception as e:
            print(f"Error creating registry entries: {e}")
    
    print("Browser extension setup complete!")
    print(f"Native host script: {native_host_script}")
    if platform.system() == 'Windows':
        print(f"Batch file: {batch_file}")
        print("Registry entries created for Chrome and Edge.")
        print("\nTo verify installation, please check:")
        print("1. Chrome/Edge extensions are installed")
        print("2. Native messaging host is registered in registry")
        print("3. Tab server is running")

def create_manifests(manifests_dir: Path, native_host_path: str):
    """Create native messaging host manifest files."""
    
    # Chrome manifest
    chrome_manifest = {
        "name": "com.focusguard.native",
        "description": "Focus Guard native messaging host",
        "path": native_host_path,
        "type": "stdio",
        "allowed_origins": [
            "chrome-extension://kfhbbnokafpbmjchnjghbdkpkjdpbldh/"
        ]
    }
    
    # Edge manifest (same as Chrome but with Edge extension ID)
    edge_manifest = chrome_manifest.copy()
    edge_manifest["allowed_origins"] = ["chrome-extension://kfhbbnokafpbmjchnjghbdkpkjdpbldh/"]
    
    # Firefox manifest
    firefox_manifest = {
        "name": "com.focusguard.native",
        "description": "Focus Guard native messaging host",
        "path": native_host_path,
        "type": "stdio",
        "allowed_extensions": [
            "focusguard@example.com"
        ]
    }
    
    # Write manifest files
    with open(manifests_dir / "chrome_native_host.json", 'w') as f:
        json.dump(chrome_manifest, f, indent=2)
    
    with open(manifests_dir / "edge_native_host.json", 'w') as f:
        json.dump(edge_manifest, f, indent=2)
    
    with open(manifests_dir / "firefox_native_host.json", 'w') as f:
        json.dump(firefox_manifest, f, indent=2)
    
    print("Manifest files created successfully!")

if __name__ == "__main__":
    setup_browser_extension()
