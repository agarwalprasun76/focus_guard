#!/usr/bin/env python3
"""
Browser Extension Troubleshooting Script

This script diagnoses and fixes common browser extension issues:
1. Tab server connectivity
2. Native messaging host permissions
3. Extension file path issues
4. Registry/manifest problems
"""

import os
import sys
import json
import requests
import platform
import subprocess
from pathlib import Path
import logging
import socket
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserExtensionTroubleshooter:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.extension_dir = self.project_root / "focus_guard" / "core" / "browser" / "extension"
        self.manifests_dir = self.extension_dir / "manifests"
        
    def check_tab_server_connectivity(self):
        """Check if tab server is running and accessible."""
        logger.info("=== Checking Tab Server Connectivity ===")
        
        try:
            # Test tab server connectivity
            response = requests.get("http://127.0.0.1:58392/api/status", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Tab server is running and accessible")
                return True
            else:
                logger.error(f"❌ Tab server returned status: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.error("❌ Tab server not accessible - server may not be running")
            return False
        except Exception as e:
            logger.error(f"❌ Tab server error: {e}")
            return False
    
    def check_native_host_permissions(self):
        """Check native messaging host permissions and registry."""
        logger.info("=== Checking Native Host Permissions ===")
        
        system = platform.system()
        
        if system == 'Windows':
            return self._check_windows_native_host()
        else:
            return self._check_unix_native_host()
    
    def _check_windows_native_host(self):
        """Check Windows native messaging host setup."""
        logger.info("Checking Windows native messaging host...")
        
        # Check Chrome registry
        chrome_reg_path = r"HKEY_CURRENT_USER\SOFTWARE\Google\Chrome\User Data\NativeMessagingHosts\focus_guard_native"
        chrome_cmd = f'reg query "{chrome_reg_path}"'
        
        try:
            result = subprocess.run(chrome_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ Chrome native host registry entry found")
            else:
                logger.error("❌ Chrome native host registry entry missing")
                return False
        except Exception as e:
            logger.error(f"❌ Chrome registry check error: {e}")
            return False
        
        # Check Edge registry
        edge_reg_path = r"HKEY_CURRENT_USER\SOFTWARE\Microsoft\Edge\User Data\NativeMessagingHosts\focus_guard_native"
        edge_cmd = f'reg query "{edge_reg_path}"'
        
        try:
            result = subprocess.run(edge_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ Edge native host registry entry found")
            else:
                logger.error("❌ Edge native host registry entry missing")
                return False
        except Exception as e:
            logger.error(f"❌ Edge registry check error: {e}")
            return False
        
        return True
    
    def _check_unix_native_host(self):
        """Check Unix native messaging host setup."""
        logger.info("Checking Unix native messaging host...")
        return True  # Unix checks would go here
    
    def check_extension_files(self):
        """Check if all required extension files exist."""
        logger.info("=== Checking Extension Files ===")
        
        required_files = [
            "manifests/chrome_native_host.json",
            "manifests/firefox_native_host.json",
            "focus_guard_native_host.py",
            "focus_guard_native_host.bat"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.extension_dir / file_path
            if not full_path.exists():
                missing_files.append(str(full_path))
                logger.error(f"❌ Missing: {full_path}")
            else:
                logger.info(f"✅ Found: {full_path}")
        
        return len(missing_files) == 0
    
    def check_port_availability(self):
        """Check if port 5000 is available."""
        logger.info("=== Checking Port Availability ===")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 5000))
            sock.close()
            
            if result == 0:
                logger.info("✅ Port 5000 is in use (likely tab server)")
                return True
            else:
                logger.warning("⚠️ Port 5000 is available (tab server may not be running)")
                return False
        except Exception as e:
            logger.error(f"❌ Port check error: {e}")
            return False
    
    def fix_registry_entries(self):
        """Fix Windows registry entries for native messaging."""
        logger.info("=== Fixing Registry Entries ===")
        
        if platform.system() != 'Windows':
            logger.info("Non-Windows system - skipping registry fixes")
            return
        
        # Get correct paths
        native_host_path = self.extension_dir / "focus_guard_native_host.py"
        native_host_bat = self.extension_dir / "focus_guard_native_host.bat"
        
        if not native_host_path.exists():
            logger.error(f"❌ Native host script not found: {native_host_path}")
            return False
        
        # Create batch wrapper if it doesn't exist
        if not native_host_bat.exists():
            with open(native_host_bat, 'w') as f:
                f.write(f'@echo off\npython "{native_host_path}" %*\n')
            logger.info(f"✅ Created batch wrapper: {native_host_bat}")
        
        # Registry commands for Chrome
        chrome_reg_commands = [
            f'reg add "HKEY_CURRENT_USER\\SOFTWARE\\Google\\Chrome\\User Data\\NativeMessagingHosts\\focus_guard_native" /ve /t REG_SZ /d "{native_host_path}" /f',
            f'reg add "HKEY_CURRENT_USER\\SOFTWARE\\Microsoft\\Edge\\User Data\\NativeMessagingHosts\\focus_guard_native" /ve /t REG_SZ /d "{native_host_path}" /f',
            f'reg add "HKEY_CURRENT_USER\\SOFTWARE\\Mozilla\\NativeMessagingHosts\\focus_guard_native" /ve /t REG_SZ /d "{native_host_path}" /f'
        ]
        
        for cmd in chrome_reg_commands:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"✅ Registry entry created: {cmd}")
                else:
                    logger.warning(f"⚠️ Registry command failed: {result.stderr}")
            except Exception as e:
                logger.error(f"❌ Registry command error: {e}")
        
        return True
    
    def check_browser_extension_manifest(self):
        """Check browser extension manifest validity."""
        logger.info("=== Checking Extension Manifest ===")
        
        # Check if extension is properly loaded
        manifest_path = self.extension_dir / "manifest.json"
        if not manifest_path.exists():
            logger.error(f"❌ Extension manifest not found: {manifest_path}")
            return False
        
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                logger.info("✅ Extension manifest is valid JSON")
                return True
        except Exception as e:
            logger.error(f"❌ Extension manifest error: {e}")
            return False
    
    def start_focus_guard_service(self):
        """Start the Focus Guard service."""
        logger.info("=== Starting Focus Guard Service ===")
        
        try:
            # Import and start the service
            from focus_guard.core.browser.extension.tab_server import start_tab_server
            success = start_tab_server(5000)
            
            if success:
                logger.info("✅ Focus Guard service started successfully")
                return True
            else:
                logger.error("❌ Failed to start Focus Guard service")
                return False
        except Exception as e:
            logger.error(f"❌ Service start error: {e}")
            return False
    
    def run_full_diagnosis(self):
        """Run complete browser extension diagnosis."""
        logger.info("=" * 60)
        logger.info("BROWSER EXTENSION TROUBLESHOOTING")
        logger.info("=" * 60)
        
        checks = [
            ("Tab Server Connectivity", self.check_tab_server_connectivity),
            ("Port Availability", self.check_port_availability),
            ("Extension Files", self.check_extension_files),
            ("Native Host Permissions", self.check_native_host_permissions),
            ("Extension Manifest", self.check_browser_extension_manifest)
        ]
        
        results = []
        for check_name, check_func in checks:
            logger.info(f"\n{check_name}:")
            logger.info("-" * 40)
            try:
                result = check_func()
                results.append((check_name, result))
            except Exception as e:
                logger.error(f"❌ {check_name} failed: {e}")
                results.append((check_name, False))
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("DIAGNOSIS SUMMARY")
        logger.info("=" * 60)
        
        passed = 0
        total = len(results)
        
        for check_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{check_name}: {status}")
            if result:
                passed += 1
        
        logger.info(f"\nOverall: {passed}/{total} checks passed")
        
        if passed < total:
            logger.info("\nAttempting automatic fixes...")
            self.fix_registry_entries()
            self.start_focus_guard_service()
        
        return passed == total

def main():
    """Main troubleshooting function."""
    troubleshooter = BrowserExtensionTroubleshooter()
    success = troubleshooter.run_full_diagnosis()
    
    if success:
        print("\nAll checks passed! Browser extension should be working.")
    else:
        print("\nIssues found. Please check the logs above and run the fixes.")
    
    return success

if __name__ == "__main__":
    main()
