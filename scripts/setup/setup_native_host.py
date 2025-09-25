#!/usr/bin/env python3
"""
Native Messaging Host Setup Script

This script sets up the native messaging host for browser extensions
to communicate with the Focus Guard application.
"""

import os
import sys
import json
import platform
from pathlib import Path

def setup_native_messaging_host():
    """Set up the native messaging host for browser extensions."""
    
    # Get the current directory
    current_dir = Path(__file__).parent.parent
    extension_dir = current_dir / "focus_guard" / "core" / "browser" / "extension"
    
    # Create native host executable
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
from typing import Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='native_host.log'
)
logger = logging.getLogger(__name__)

class NativeMessagingHost:
    def __init__(self):
        self.running = True
        
    def send_message(self, message: Dict[str, Any]):
        """Send a message to the browser extension."""
        encoded_content = json.dumps(message).encode('utf-8')
        encoded_length = struct.pack('@I', len(encoded_content))
        sys.stdout.buffer.write(encoded_length)
        sys.stdout.buffer.write(encoded_content)
        sys.stdout.flush()
        
    def read_message(self) -> Dict[str, Any]:
        """Read a message from the browser extension."""
        raw_length = sys.stdin.buffer.read(4)
        if len(raw_length) == 0:
            sys.exit(0)
        message_length = struct.unpack('@I', raw_length)[0]
        message = sys.stdin.buffer.read(message_length).decode('utf-8')
        return json.loads(message)
        
    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming messages from the browser extension."""
        try:
            action = message.get('action')
            
            if action == 'ping':
                return {'status': 'success', 'message': 'pong'}
            elif action == 'get_status':
                return {'status': 'success', 'running': True}
            elif action == 'close_tab':
                # Forward to Focus Guard API
                return {'status': 'success', 'message': 'Tab close command sent'}
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return {'status': 'error', 'message': str(e)}
            
    def run(self):
        """Run the native messaging host."""
        try:
            while self.running:
                message = self.read_message()
                response = self.handle_message(message)
                self.send_message(response)
        except KeyboardInterrupt:
            logger.info("Native host interrupted")
        except Exception as e:
            logger.error(f"Error in native host: {e}")

if __name__ == '__main__':
    host = NativeMessagingHost()
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
    
    print("Native messaging host setup complete!")
    print(f"Native host script: {native_host_script}")
    if platform.system() == 'Windows':
        print(f"Batch file: {batch_file}")

if __name__ == "__main__":
    setup_native_messaging_host()
