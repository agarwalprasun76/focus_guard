#!/usr/bin/env python3
"""
Automated browser extension installer for Focus Guard.
Supports Chrome and Edge browsers with automatic detection and installation.
"""

import os
import sys
import json
import shutil
import subprocess
import winreg
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class BrowserExtensionInstaller:
    """Automated installer for Focus Guard browser extension."""
    
    def __init__(self):
        self.extension_dir = Path(__file__).parent.parent.parent.parent / "focus_guard" / "core" / "browser" / "extension" / "webextension_mv3"
        self.extension_id = "hmjfbkppeejdnekjapejicmfhfogocjo"
        
    def detect_browsers(self) -> Dict[str, Optional[Path]]:
        """Detect installed browsers and their installation paths."""
        browsers = {
            "chrome": None,
            "edge": None
        }
        
        # Chrome detection
        chrome_paths = [
            Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe"
        ]
        
        for path in chrome_paths:
            if path.exists():
                browsers["chrome"] = path
                break
        
        # Edge detection
        edge_paths = [
            Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
        ]
        
        for path in edge_paths:
            if path.exists():
                browsers["edge"] = path
                break
        
        return browsers
    
    def get_browser_profile_dirs(self, browser: str) -> List[Path]:
        """Get browser profile directories."""
        user_data_paths = {
            "chrome": Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data",
            "edge": Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data"
        }
        
        base_path = user_data_paths.get(browser)
        if not base_path or not base_path.exists():
            return []
        
        profiles = []
        # Default profile
        default_profile = base_path / "Default"
        if default_profile.exists():
            profiles.append(default_profile)
        
        # Additional profiles (Profile 1, Profile 2, etc.)
        for item in base_path.iterdir():
            if item.is_dir() and item.name.startswith("Profile "):
                profiles.append(item)
        
        return profiles
    
    def create_extension_policy(self, browser: str) -> bool:
        """Create registry policy to auto-install extension."""
        try:
            # Registry paths for extension policies
            registry_paths = {
                "chrome": r"SOFTWARE\Policies\Google\Chrome\ExtensionInstallForcelist",
                "edge": r"SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist"
            }
            
            reg_path = registry_paths.get(browser)
            if not reg_path:
                return False
            
            # Create registry key
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                # Add extension to force install list
                extension_entry = f"{self.extension_id};file:///{self.extension_dir.as_posix()}/manifest.json"
                winreg.SetValueEx(key, "1", 0, winreg.REG_SZ, extension_entry)
            
            print(f"[OK] Created registry policy for {browser}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to create registry policy for {browser}: {e}")
            return False
    
    def close_browser(self, browser: str) -> bool:
        """Close all instances of the specified browser and ensure they stay closed."""
        try:
            process_name = "chrome" if browser == "chrome" else "msedge"
            
            # Kill all processes multiple times to ensure they're fully closed
            for attempt in range(3):
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", f"{process_name}.exe"],
                    capture_output=True,
                    text=True
                )
                import time
                time.sleep(1)
            
            print(f"[OK] Closed {browser} processes")
            
            # Wait longer to ensure all background processes terminate
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to close {browser}: {e}")
            return False

    def install_via_developer_mode(self, browser: str, browser_path: Path) -> bool:
        """Install extension by enabling developer mode and loading unpacked."""
        try:
            # First, close the browser to prevent preferences overwriting
            print(f"   Closing {browser} to modify preferences...")
            if not self.close_browser(browser):
                print(f"[ERROR] Failed to close {browser}")
                return False
            
            profiles = self.get_browser_profile_dirs(browser)
            if not profiles:
                print(f"[ERROR] No {browser} profiles found")
                return False
            
            success_count = 0
            for profile in profiles:
                try:
                    # Create preferences to enable developer mode
                    prefs_file = profile / "Preferences"
                    if prefs_file.exists():
                        with open(prefs_file, 'r', encoding='utf-8') as f:
                            prefs = json.load(f)
                    else:
                        prefs = {}
                    
                    # Enable developer mode
                    if "extensions" not in prefs:
                        prefs["extensions"] = {}
                    if "ui" not in prefs["extensions"]:
                        prefs["extensions"]["ui"] = {}
                    
                    prefs["extensions"]["ui"]["developer_mode"] = True
                    
                    # Add extension to load
                    if "settings" not in prefs["extensions"]:
                        prefs["extensions"]["settings"] = {}
                    
                    # Create extension entry
                    extension_data = {
                        "active_permissions": {
                            "api": ["tabs", "nativeMessaging", "alarms", "webRequest", "declarativeNetRequest"],
                            "explicit_host": ["<all_urls>"]
                        },
                        "creation_flags": 1,
                        "from_webstore": False,
                        "location": 4,  # LOAD_UNPACKED
                        "manifest": {
                            "name": "FocusGuard Tab Watcher (MV3)",
                            "version": "1.0.0"
                        },
                        "path": str(self.extension_dir),
                        "state": 1,  # ENABLED
                        "was_installed_by_default": False,
                        "was_installed_by_oem": False
                    }
                    
                    prefs["extensions"]["settings"][self.extension_id] = extension_data
                    
                    # Write back preferences
                    with open(prefs_file, 'w', encoding='utf-8') as f:
                        json.dump(prefs, f, indent=2)
                    
                    success_count += 1
                    print(f"[OK] Configured {browser} profile: {profile.name}")
                    
                except Exception as e:
                    print(f"[ERROR] Failed to configure {browser} profile {profile.name}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            print(f"[ERROR] Failed to install via developer mode for {browser}: {e}")
            return False
    
    def install_via_external_extensions_dir(self, browser: str) -> bool:
        """Install extension by copying to browser's external extensions directory."""
        try:
            # Get browser's external extensions directory
            if browser == "chrome":
                external_dir = Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Google" / "Chrome" / "Application" / "Extensions"
                if not external_dir.exists():
                    external_dir = Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Google" / "Chrome" / "Application" / "Extensions"
            elif browser == "edge":
                external_dir = Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Microsoft" / "Edge" / "Application" / "Extensions"
            else:
                return False
            
            if not external_dir.exists():
                external_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy extension to external directory
            target_dir = external_dir / self.extension_id
            if target_dir.exists():
                import shutil
                shutil.rmtree(target_dir)
            
            import shutil
            shutil.copytree(self.extension_dir, target_dir)
            print(f"[OK] Copied extension to {target_dir}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to install via external directory: {e}")
            return False

    def launch_browser_with_extension(self, browser: str, browser_path: Path) -> bool:
        """Launch browser with extension loaded."""
        try:
            # Browser-specific arguments
            args = [
                str(browser_path),
                f"--load-extension={self.extension_dir}",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            
            # Launch browser
            subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            print(f"[OK] Launched {browser} with extension loaded")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to launch {browser}: {e}")
            return False
    
    def verify_extension_files(self) -> bool:
        """Verify extension files exist and are valid."""
        required_files = ["manifest.json", "background.js"]
        
        if not self.extension_dir.exists():
            print(f"[ERROR] Extension directory not found: {self.extension_dir}")
            return False
        
        for file in required_files:
            file_path = self.extension_dir / file
            if not file_path.exists():
                print(f"[ERROR] Required file missing: {file}")
                return False
        
        # Validate manifest
        try:
            with open(self.extension_dir / "manifest.json", 'r') as f:
                manifest = json.load(f)
                if manifest.get("manifest_version") != 3:
                    print("[ERROR] Invalid manifest version")
                    return False
        except Exception as e:
            print(f"[ERROR] Invalid manifest.json: {e}")
            return False
        
        print("[OK] Extension files validated")
        return True
    
    def install_all(self) -> bool:
        """Install extension for all detected browsers."""
        print("Starting automated browser extension installation...")
        print(f"Extension directory: {self.extension_dir}")
        
        # Verify extension files
        if not self.verify_extension_files():
            return False
        
        # Detect browsers
        browsers = self.detect_browsers()
        print(f"Detected browsers: {list(browsers.keys())}")
        
        success = False
        for browser, path in browsers.items():
            if path:
                print(f"\nInstalling extension for {browser.title()}...")
                
                methods = [
                    ("Registry Policy", lambda: self.create_extension_policy(browser)),
                    ("External Extensions Dir", lambda: self.install_via_external_extensions_dir(browser)),
                    ("Developer Mode", lambda: self.install_via_developer_mode(browser, path)),
                    ("Launch with Extension", lambda: self.launch_browser_with_extension(browser, path))
                ]
                
                browser_success = False
                for method_name, method in methods:
                    print(f"   Trying {method_name}...")
                    try:
                        if method():
                            browser_success = True
                            print(f"   [OK] {method_name} successful")
                            break
                    except Exception as e:
                        print(f"   [ERROR] {method_name} failed: {e}")
                
                if browser_success:
                    success = True
                    print(f"[OK] {browser.title()} installation completed")
                else:
                    print(f"[ERROR] {browser.title()} installation failed")
            else:
                print(f"[ERROR] {browser.title()} not found")
        
        return success
    
    def show_manual_instructions(self):
        """Show manual installation instructions as fallback."""
        print("\n" + "="*60)
        print("MANUAL INSTALLATION INSTRUCTIONS")
        print("="*60)
        print(f"If automated installation failed, follow these steps:")
        print(f"")
        print(f"1. Open Chrome or Edge")
        print(f"2. Go to chrome://extensions/ or edge://extensions/")
        print(f"3. Enable 'Developer mode' (toggle in top-right)")
        print(f"4. Click 'Load unpacked'")
        print(f"5. Select folder: {self.extension_dir}")
        print(f"6. Ensure the extension is enabled")
        print("="*60)

def main():
    """Main installation function."""
    installer = BrowserExtensionInstaller()
    
    print("Focus Guard Browser Extension Installer")
    print("="*50)
    
    success = installer.install_all()
    
    if success:
        print("\nInstallation completed successfully!")
        print("Next steps:")
        print("   1. Start your browser(s) - they were closed during installation")
        print("   2. Go to chrome://extensions/ or edge://extensions/ to verify")
        print("   3. The extension should appear as 'FocusGuard Tab Watcher (MV3)'")
        print("   4. Run the Focus Guard MVP to test tab detection")
    else:
        print("\nAutomated installation failed")
        installer.show_manual_instructions()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
