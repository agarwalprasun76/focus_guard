#!/usr/bin/env python3
"""
Focus Guard Extension - Guided Installation with Validation
Provides a better UX with proper browser opening and step validation.
"""

import os
import sys
import subprocess
import time
import tkinter as tk
from tkinter import messagebox, simpledialog
from pathlib import Path
import webbrowser

class ExtensionInstaller:
    def __init__(self):
        self.extension_dir = Path(__file__).parent.parent.parent / "focus_guard" / "core" / "browser" / "extension" / "webextension_mv3"
        self.root = tk.Tk()
        self.root.withdraw()  # Hide main window
        self.explorer_opened = False  # Track if explorer window was already opened
        
    def show_message(self, title, message, msg_type="info"):
        """Show message with proper formatting"""
        if msg_type == "error":
            messagebox.showerror(title, message)
            return False
        elif msg_type == "question":
            return messagebox.askyesno(title, message)
        else:
            messagebox.showinfo(title, message)
            return True
    
    def wait_for_confirmation(self, message):
        """Wait for user to confirm they completed a step"""
        return self.show_message("Confirmation Required", message, "question")
    
    def open_browser_extensions(self, browser):
        """Open browser to extensions page with multiple methods"""
        if browser == "chrome":
            urls = ["chrome://extensions/"]
            # Try multiple methods to open Chrome
            try:
                # Method 1: Direct URL
                webbrowser.get('chrome').open(urls[0])
            except:
                try:
                    # Method 2: Command line
                    subprocess.run(["chrome", "--new-tab", urls[0]], check=False)
                except:
                    try:
                        # Method 3: Start command
                        subprocess.run(["start", "chrome", urls[0]], shell=True, check=False)
                    except:
                        return False
        elif browser == "edge":
            urls = ["edge://extensions/"]
            try:
                # Method 1: Direct URL
                webbrowser.get('edge').open(urls[0])
            except:
                try:
                    # Method 2: Command line
                    subprocess.run(["msedge", "--new-tab", urls[0]], check=False)
                except:
                    try:
                        # Method 3: Start command
                        subprocess.run(["start", "msedge", urls[0]], shell=True, check=False)
                    except:
                        return False
        return True
    
    def install_browser_extension(self, browser_name):
        """Install extension for a specific browser"""
        browser_title = browser_name.upper()
        
        # Step 1: Open browser
        self.show_message(f"{browser_title} Installation", 
                         f"Starting {browser_title} extension installation.\n\n"
                         f"The installer will now open {browser_title} to the extensions page.")
        
        success = self.open_browser_extensions(browser_name)
        if not success:
            self.show_message("Error", f"Could not automatically open {browser_title}.\n\n"
                             f"Please manually open {browser_title} and go to:\n"
                             f"{'chrome://extensions/' if browser_name == 'chrome' else 'edge://extensions/'}")
        
        time.sleep(2)  # Give browser time to open
        
        # Step 2: Verify browser opened
        if not self.wait_for_confirmation(f"Did {browser_title} open to the extensions page?\n\n"
                                         f"If not, please open {browser_title} and navigate to:\n"
                                         f"{'chrome://extensions/' if browser_name == 'chrome' else 'edge://extensions/'}\n\n"
                                         f"Click YES when you can see the extensions page."):
            return False
        
        # Step 3: Enable Developer Mode
        self.show_message(f"{browser_title} Step 1", 
                         f"In {browser_title}, look for 'Developer mode' toggle.\n\n"
                         f"Location: TOP-RIGHT corner of the extensions page\n"
                         f"Action: Turn it ON (should turn blue)\n\n"
                         f"Click OK when ready for the next step.")
        
        if not self.wait_for_confirmation(f"Have you enabled 'Developer mode' in {browser_title}?\n\n"
                                         f"You should see a blue toggle and new buttons appeared.\n\n"
                                         f"Click YES if Developer mode is enabled."):
            return False
        
        # Step 4: Click Load Unpacked
        self.show_message(f"{browser_title} Step 2", 
                         f"Now click the 'Load unpacked' button in {browser_title}.\n\n"
                         f"This button appeared after enabling Developer mode.\n\n"
                         f"Click OK when you've clicked 'Load unpacked'.")
        
        if not self.wait_for_confirmation(f"Did you click 'Load unpacked' in {browser_title}?\n\n"
                                         f"A folder selection dialog should have opened.\n\n"
                                         f"Click YES if the folder dialog is open."):
            return False
        
        # Step 5: Open parent folder and guide selection (only once)
        if not self.explorer_opened:
            parent_dir = self.extension_dir.parent  # Open at 'extension' level, not 'webextension_mv3'
            subprocess.run(["explorer", str(parent_dir)], check=False)
            self.explorer_opened = True
            explorer_msg = "A file explorer window opened at the extension folder level.\n\n"
        else:
            explorer_msg = "Use the file explorer window that opened earlier.\n\n"
        
        self.show_message(f"{browser_title} Step 3", 
                         f"{explorer_msg}"
                         f"In {browser_title}'s folder selection dialog:\n"
                         f"1. Navigate to the 'extension' folder\n"
                         f"2. Select the 'webextension_mv3' folder inside it\n"
                         f"3. Click 'Select Folder' or 'Open'\n\n"
                         f"You should see: webextension_mv3 folder in the window")
        
        if not self.wait_for_confirmation(f"Have you selected the extension folder in {browser_title}?\n\n"
                                         f"The extension should now appear in the extensions list.\n\n"
                                         f"Click YES if you can see 'FocusGuard Tab Watcher (MV3)' in the list."):
            return False
        
        # Step 6: Verify extension is enabled
        if not self.wait_for_confirmation(f"Is the FocusGuard extension ENABLED in {browser_title}?\n\n"
                                         f"Check that the toggle next to the extension is ON (blue).\n\n"
                                         f"Click YES if the extension is enabled."):
            self.show_message(f"{browser_title} Action Required", 
                             f"Please enable the FocusGuard extension in {browser_title}:\n\n"
                             f"1. Find 'FocusGuard Tab Watcher (MV3)' in the list\n"
                             f"2. Make sure its toggle is ON (blue)\n"
                             f"3. The extension should show as 'Enabled'")
            
            if not self.wait_for_confirmation(f"Is the extension now enabled in {browser_title}?"):
                return False
        
        self.show_message(f"{browser_title} Complete", 
                         f"✅ {browser_title} extension installation complete!\n\n"
                         f"The FocusGuard extension is now installed and enabled.")
        return True
    
    def run_installation(self):
        """Run the complete installation process"""
        # Check extension directory
        if not self.extension_dir.exists():
            self.show_message("Error", f"Extension directory not found!\n\nExpected: {self.extension_dir}", "error")
            return False
        
        # Welcome message
        self.show_message("Focus Guard Extension Installer", 
                         "Welcome to the Focus Guard Extension Installer!\n\n"
                         "This installer will guide you through installing the extension "
                         "in both Chrome and Edge with step-by-step validation.\n\n"
                         "Please close all browser windows before continuing.")
        
        if not self.wait_for_confirmation("Have you closed all Chrome and Edge windows?\n\n"
                                         "This ensures a clean installation process.\n\n"
                                         "Click YES when all browsers are closed."):
            return False
        
        # Install Chrome extension
        chrome_success = self.install_browser_extension("chrome")
        if not chrome_success:
            if not self.show_message("Chrome Installation Failed", 
                                   "Chrome installation was not completed successfully.\n\n"
                                   "Do you want to continue with Edge installation?", "question"):
                return False
        
        # Install Edge extension
        edge_success = self.install_browser_extension("edge")
        if not edge_success:
            self.show_message("Edge Installation Failed", 
                             "Edge installation was not completed successfully.", "error")
        
        # Final summary
        if chrome_success and edge_success:
            self.show_message("Installation Complete", 
                             "🎉 Installation Complete!\n\n"
                             "✅ Chrome: Extension installed and enabled\n"
                             "✅ Edge: Extension installed and enabled\n\n"
                             "To test the installation:\n"
                             "Run: python focus_guard\\core\\mvp_main.py")
        elif chrome_success or edge_success:
            browser = "Chrome" if chrome_success else "Edge"
            self.show_message("Partial Installation", 
                             f"⚠️ Partial Installation Complete\n\n"
                             f"✅ {browser}: Extension installed and enabled\n"
                             f"❌ {'Edge' if chrome_success else 'Chrome'}: Installation failed\n\n"
                             f"You can retry the failed browser later.")
        else:
            self.show_message("Installation Failed", 
                             "❌ Installation failed for both browsers.\n\n"
                             "Please try running the installer again or install manually.", "error")
        
        return chrome_success or edge_success

def main():
    """Main entry point"""
    installer = ExtensionInstaller()
    try:
        success = installer.run_installation()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nInstallation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        messagebox.showerror("Installation Error", f"An error occurred during installation:\n\n{str(e)}")
        sys.exit(1)
    finally:
        installer.root.destroy()

if __name__ == "__main__":
    main()
