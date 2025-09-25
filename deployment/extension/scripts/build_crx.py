"""
Build Focus Guard extension as CRX package with persistent key for Edge force-install.

This script implements the enterprise-grade CRX packaging approach for permanent
extension installation via Edge policy.
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path

class CRXBuilder:
    """Builds CRX packages for Focus Guard extension."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.extension_dir = self.project_root / "focus_guard" / "core" / "browser" / "extension" / "webextension_mv3"
        self.build_dir = self.project_root / "deployment" / "crx"
        self.chrome_path = self._find_chrome_executable()
        
    def _find_chrome_executable(self) -> str:
        """Find Chrome executable for CRX packaging."""
        possible_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError("Chrome executable not found. Chrome is required for CRX packaging.")
    
    def ensure_build_directory(self):
        """Create build directory structure."""
        self.build_dir.mkdir(parents=True, exist_ok=True)
        print(f"Build directory: {self.build_dir}")
    
    def get_extension_info(self):
        """Read extension manifest for version and metadata."""
        manifest_path = self.extension_dir / "manifest.json"
        
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        return {
            'name': manifest.get('name', 'FocusGuard'),
            'version': manifest.get('version', '1.0.0'),
            'description': manifest.get('description', '')
        }
    
    def generate_persistent_key(self):
        """Generate or reuse persistent key for consistent extension ID."""
        key_path = self.build_dir / "key.pem"
        
        if key_path.exists():
            print(f"Using existing key: {key_path}")
            return key_path
        
        print("Generating new persistent key...")
        # First pack without key to generate one
        temp_crx = self.extension_dir.with_suffix('.crx')
        temp_pem = self.extension_dir.with_suffix('.pem')
        
        try:
            cmd = [
                str(self.chrome_path),
                f"--pack-extension={self.extension_dir}",
                "--no-message-box"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if temp_pem.exists():
                shutil.move(str(temp_pem), str(key_path))
                print(f"Key generated and saved: {key_path}")
            
            # Clean up temporary CRX
            if temp_crx.exists():
                temp_crx.unlink()
                
        except subprocess.TimeoutExpired:
            print("Chrome packaging timed out, but key may have been generated")
        except Exception as e:
            print(f"Warning: Key generation may have failed: {e}")
        
        if not key_path.exists():
            raise RuntimeError("Failed to generate persistent key")
        
        return key_path
    
    def build_crx(self, key_path: Path):
        """Build CRX package using persistent key."""
        extension_info = self.get_extension_info()
        crx_name = f"FocusGuard_v{extension_info['version']}.crx"
        crx_path = self.build_dir / crx_name
        
        print(f"Building CRX: {crx_name}")
        
        # Remove existing CRX
        if crx_path.exists():
            crx_path.unlink()
        
        # Pack extension with persistent key
        cmd = [
            str(self.chrome_path),
            f"--pack-extension={self.extension_dir}",
            f"--pack-extension-key={key_path}",
            "--no-message-box"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Chrome outputs CRX next to extension directory
            temp_crx = self.extension_dir.with_suffix('.crx')
            
            if temp_crx.exists():
                shutil.move(str(temp_crx), str(crx_path))
                print(f"CRX built successfully: {crx_path}")
                return crx_path
            else:
                raise RuntimeError("CRX file not generated")
                
        except subprocess.TimeoutExpired:
            raise RuntimeError("Chrome packaging timed out")
        except Exception as e:
            raise RuntimeError(f"CRX build failed: {e}")
    
    def get_extension_id_from_key(self, key_path: Path) -> str:
        """Extract extension ID from key file (simplified approach)."""
        # For now, we'll need to load the extension to get the ID
        # In production, you'd calculate this from the key
        return "PLACEHOLDER_EXTENSION_ID"
    
    def create_updates_xml(self, extension_id: str, crx_url: str):
        """Create updates.xml for auto-update mechanism."""
        extension_info = self.get_extension_info()
        
        updates_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<gupdate xmlns="http://www.google.com/update2/response" protocol="2.0">
  <app appid="{extension_id}">
    <updatecheck codebase="{crx_url}" version="{extension_info['version']}"/>
  </app>
</gupdate>'''
        
        updates_path = self.build_dir / "updates.xml"
        with open(updates_path, 'w', encoding='utf-8') as f:
            f.write(updates_xml)
        
        print(f"Updates XML created: {updates_path}")
        return updates_path
    
    def build(self, crx_url: str = None, extension_id: str = None):
        """Complete build process."""
        print("=" * 60)
        print("Focus Guard CRX Builder")
        print("=" * 60)
        
        # Validate extension directory
        if not self.extension_dir.exists():
            raise FileNotFoundError(f"Extension directory not found: {self.extension_dir}")
        
        print(f"Extension directory: {self.extension_dir}")
        print(f"Chrome executable: {self.chrome_path}")
        
        # Setup build environment
        self.ensure_build_directory()
        
        # Get extension info
        extension_info = self.get_extension_info()
        print(f"Extension: {extension_info['name']} v{extension_info['version']}")
        
        # Generate or reuse persistent key
        key_path = self.generate_persistent_key()
        
        # Build CRX
        crx_path = self.build_crx(key_path)
        
        # Create updates.xml if URL provided
        if crx_url and extension_id:
            self.create_updates_xml(extension_id, crx_url)
        
        print("\n" + "=" * 60)
        print("BUILD COMPLETE")
        print("=" * 60)
        print(f"CRX Package: {crx_path}")
        print(f"Persistent Key: {key_path}")
        
        if crx_url:
            print(f"Upload CRX to: {crx_url}")
            print(f"Upload updates.xml to: {crx_url.replace('.crx', '/updates.xml')}")
        
        print("\nNext steps:")
        print("1. Load extension unpacked to get Extension ID")
        print("2. Update updates.xml with real Extension ID")
        print("3. Upload CRX and updates.xml to HTTPS server")
        print("4. Configure Edge policy with Extension ID and updates.xml URL")
        
        return {
            'crx_path': crx_path,
            'key_path': key_path,
            'extension_info': extension_info
        }


def main():
    """Main build script."""
    try:
        builder = CRXBuilder()
        
        # Example URLs - replace with your actual hosting
        crx_url = "https://your-domain.com/focusguard/FocusGuard.crx"
        extension_id = "YOUR_EXTENSION_ID"  # Get this by loading extension unpacked
        
        result = builder.build(crx_url, extension_id)
        return True
        
    except Exception as e:
        print(f"Build failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
