"""
Manual Edge extension installation guide.
"""

import os
import sys
import subprocess

# Add the focus_guard package to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from focus_guard.core.browser.extension.robust_installer import RobustExtensionInstaller
from focus_guard.core.browser.models.browser import BrowserType

def install_edge_extension_properly():
    """Install Edge extension using the proper method."""
    print("Focus Guard - Proper Edge Extension Installation")
    print("=" * 60)
    
    installer = RobustExtensionInstaller()
    
    # Get extension directory
    extension_dir = installer._extension_dir
    print(f"Extension directory: {extension_dir}")
    
    # Check if Edge is available
    if BrowserType.EDGE not in installer._browser_paths:
        print("ERROR: Microsoft Edge not detected")
        return False
    
    edge_path = installer._browser_paths[BrowserType.EDGE]
    print(f"Edge path: {edge_path}")
    
    print("\n" + "=" * 60)
    print("MANUAL INSTALLATION STEPS")
    print("=" * 60)
    print("1. Opening Microsoft Edge...")
    
    try:
        # Launch Edge normally (without --load-extension which is temporary)
        subprocess.Popen([edge_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("   ✅ Edge launched")
    except Exception as e:
        print(f"   ❌ Failed to launch Edge: {e}")
        return False
    
    print("\n2. Follow these steps in Edge:")
    print("   a) Go to: edge://extensions/")
    print("   b) Enable 'Developer mode' (toggle on the left)")
    print("   c) Click 'Load unpacked' button")
    print(f"   d) Navigate to and select: {extension_dir}")
    print("   e) Click 'Select Folder'")
    
    print("\n3. Expected result:")
    print("   - 'FocusGuard Tab Watcher (MV3)' should appear in extensions list")
    print("   - Extension should be enabled by default")
    
    print("\n" + "=" * 60)
    print("ALTERNATIVE: Automatic Installation")
    print("=" * 60)
    print("If you want to try automatic installation:")
    
    response = input("Launch Edge with extension pre-loaded? (y/n): ").lower().strip()
    
    if response == 'y':
        try:
            # Launch Edge with extension loaded (temporary)
            cmd = [edge_path, f"--load-extension={extension_dir}", "--no-first-run"]
            subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("✅ Edge launched with extension pre-loaded")
            print("Note: This is temporary - extension will disappear when Edge restarts")
            return True
        except Exception as e:
            print(f"❌ Failed to launch Edge with extension: {e}")
            return False
    
    return True

if __name__ == "__main__":
    install_edge_extension_properly()
