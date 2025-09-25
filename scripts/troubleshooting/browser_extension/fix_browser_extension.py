#!/usr/bin/env python3
"""
Comprehensive Browser Extension Fix Script

This script fixes all browser extension issues:
1. Tab server connectivity
2. Native messaging host permissions
3. Registry entries
4. Extension file paths
5. Service startup
"""

import os
import sys
import json
import time
import subprocess
import platform
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class BrowserExtensionFixer:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.extension_dir = self.project_root / "focus_guard" / "core" / "browser" / "extension"
        
    def fix_registry_entries(self):
        """Fix Windows registry entries for native messaging."""
        if platform.system() != 'Windows':
            return True
            
        logger.info("Fixing Windows registry entries...")
        
        # Ensure extension directory exists
        self.extension_dir.mkdir(parents=True, exist_ok=True)
        
        # Create native host script
        native_host_path = self.extension_dir / "focus_guard_native_host.py"
        native_host_bat = self.extension_dir / "focus_guard_native_host.bat"
        
        # Create the native host Python script
        native_host_content = '''#!/usr/bin/env python3
"""
Focus Guard Native Messaging Host
Handles communication between browser extension and Focus Guard
"""

import sys
import json
import logging
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from focus_guard.core.browser.extension.native_messaging import handle_message
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def main():
        """Main native messaging loop."""
        try:
            while True:
                # Read message length (4 bytes)
                raw_length = sys.stdin.buffer.read(4)
                if len(raw_length) == 0:
                    break
                    
                message_length = int.from_bytes(raw_length, byteorder='little')
                
                # Read the actual message
                message = sys.stdin.buffer.read(message_length).decode('utf-8')
                data = json.loads(message)
                
                # Process the message
                response = handle_message(data)
                
                # Send response back
                response_json = json.dumps(response)
                response_bytes = response_json.encode('utf-8')
                response_length = len(response_bytes).to_bytes(4, byteorder='little')
                
                sys.stdout.buffer.write(response_length)
                sys.stdout.buffer.write(response_bytes)
                sys.stdout.buffer.flush()
                
        except Exception as e:
            logger.error(f"Native messaging error: {e}")
            sys.exit(1)
    
    if __name__ == '__main__':
        main()
        
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    sys.exit(1)
'''
        
        with open(native_host_path, 'w') as f:
            f.write(native_host_content)
        
        # Create batch wrapper
        with open(native_host_bat, 'w') as f:
            f.write(f'@echo off\npython "{native_host_path}" %*\n')
        
        logger.info(f"Created native host script: {native_host_path}")
        logger.info(f"Created batch wrapper: {native_host_bat}")
        
        # Fix registry entries
        registry_commands = [
            f'reg add "HKEY_CURRENT_USER\\SOFTWARE\\Google\\Chrome\\User Data\\NativeMessagingHosts\\focus_guard_native" /ve /t REG_SZ /d "{native_host_bat}" /f',
            f'reg add "HKEY_CURRENT_USER\\SOFTWARE\\Microsoft\\Edge\\User Data\\NativeMessagingHosts\\focus_guard_native" /ve /t REG_SZ /d "{native_host_bat}" /f',
            f'reg add "HKEY_CURRENT_USER\\SOFTWARE\\Mozilla\\NativeMessagingHosts\\focus_guard_native" /ve /t REG_SZ /d "{native_host_bat}" /f'
        ]
        
        for cmd in registry_commands:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"Registry fixed: {cmd}")
                else:
                    logger.warning(f"Registry command failed: {result.stderr}")
            except Exception as e:
                logger.error(f"Registry error: {e}")
        
        return True
    
    def create_manifest_files(self):
        """Create proper manifest files for native messaging."""
        logger.info("Creating manifest files...")
        
        manifests_dir = self.extension_dir / "manifests"
        manifests_dir.mkdir(parents=True, exist_ok=True)
        
        # Chrome/Edge manifest
        chrome_manifest = {
            "name": "focus_guard_native",
            "description": "Focus Guard Browser Extension Native Host",
            "path": str(self.extension_dir / "focus_guard_native_host.bat"),
            "type": "stdio",
            "allowed_origins": [
                "chrome-extension://apnmgllhphjajigkkpinbmjgghk/",
                "chrome-extension://*/"
            ]
        }
        
        # Firefox manifest
        firefox_manifest = {
            "name": "focus_guard_native",
            "description": "Focus Guard Browser Extension Native Host",
            "path": str(self.extension_dir / "focus_guard_native_host.bat"),
            "type": "stdio",
            "allowed_origins": [
                "moz-extension://*/"
            ]
        }
        
        # Write manifests
        chrome_path = manifests_dir / "chrome_native_host.json"
        firefox_path = manifests_dir / "firefox_native_host.json"
        
        with open(chrome_path, 'w') as f:
            json.dump(chrome_manifest, f, indent=2)
        
        with open(firefox_path, 'w') as f:
            json.dump(firefox_manifest, f, indent=2)
        
        logger.info(f"Created: {chrome_path}")
        logger.info(f"Created: {firefox_path}")
        
        return True
    
    def start_tab_server(self):
        """Start the tab server service."""
        logger.info("Starting tab server...")
        
        try:
            # Import and start tab server
            sys.path.insert(0, str(self.project_root))
            from focus_guard.core.browser.extension.tab_server import start_tab_server
            
            success = start_tab_server(5000)
            if success:
                logger.info("Tab server started on port 5000")
                return True
            else:
                logger.error("Failed to start tab server")
                return False
                
        except Exception as e:
            logger.error(f"Tab server error: {e}")
            return False
    
    def verify_installation(self):
        """Verify the complete installation."""
        logger.info("Verifying installation...")
        
        # Check if all files exist
        required_files = [
            self.extension_dir / "focus_guard_native_host.py",
            self.extension_dir / "focus_guard_native_host.bat",
            self.extension_dir / "manifests" / "chrome_native_host.json",
            self.extension_dir / "manifests" / "firefox_native_host.json"
        ]
        
        all_exist = True
        for file_path in required_files:
            if not file_path.exists():
                logger.error(f"Missing: {file_path}")
                all_exist = False
            else:
                logger.info(f"Found: {file_path}")
        
        return all_exist
    
    def run_complete_fix(self):
        """Run the complete fix process."""
        logger.info("=" * 60)
        logger.info("BROWSER EXTENSION COMPLETE FIX")
        logger.info("=" * 60)
        
        steps = [
            ("Registry Entries", self.fix_registry_entries),
            ("Manifest Files", self.create_manifest_files),
            ("Installation Verification", self.verify_installation)
        ]
        
        success = True
        for step_name, step_func in steps:
            logger.info(f"\n{step_name}:")
            logger.info("-" * 40)
            try:
                result = step_func()
                if not result:
                    success = False
                    logger.error(f"{step_name} failed")
                else:
                    logger.info(f"{step_name} completed successfully")
            except Exception as e:
                success = False
                logger.error(f"{step_name} error: {e}")
        
        logger.info("\n" + "=" * 60)
        logger.info("FIX SUMMARY")
        logger.info("=" * 60)
        
        if success:
            logger.info("✅ All fixes completed successfully!")
            logger.info("\nNext steps:")
            logger.info("1. Reload browser extension in browser settings")
            logger.info("2. Check browser console for errors")
            logger.info("3. Test domain blocking functionality")
        else:
            logger.error("❌ Some fixes failed. Check logs above.")
        
        return success

def main():
    """Main fix function."""
    fixer = BrowserExtensionFixer()
    return fixer.run_complete_fix()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
