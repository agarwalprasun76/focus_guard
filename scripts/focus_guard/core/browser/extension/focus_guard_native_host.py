#!/usr/bin/env python3
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
