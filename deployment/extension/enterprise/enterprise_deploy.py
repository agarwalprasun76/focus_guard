"""
Complete CRX setup script - builds, configures, and provides deployment instructions.
"""

import os
import sys
import json
import subprocess
import winreg
from pathlib import Path

class CompleteCRXSetup:
    """Complete CRX packaging and policy setup for Focus Guard."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.extension_dir = self.project_root / "focus_guard" / "core" / "browser" / "extension" / "webextension_mv3"
        self.build_dir = self.project_root / "build" / "crx"
        self.chrome_path = self._find_chrome_executable()
        
    def _find_chrome_executable(self):
        """Find Chrome executable."""
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        raise FileNotFoundError("Chrome not found")
    
    def build_crx_package(self):
        """Build the CRX package."""
        print("Building CRX Package...")
        
        # Ensure build directory
        self.build_dir.mkdir(parents=True, exist_ok=True)
        
        # Get extension info
        with open(self.extension_dir / "manifest.json", 'r') as f:
            manifest = json.load(f)
        
        version = manifest.get('version', '1.0.0')
        key_path = self.build_dir / "key.pem"
        crx_path = self.build_dir / f"FocusGuard_v{version}.crx"
        
        # Generate key if needed
        if not key_path.exists():
            print("Generating persistent key...")
            cmd = [self.chrome_path, f"--pack-extension={self.extension_dir}", "--no-message-box"]
            subprocess.run(cmd, capture_output=True, timeout=30)
            
            temp_pem = self.extension_dir.with_suffix('.pem')
            temp_crx = self.extension_dir.with_suffix('.crx')
            
            if temp_pem.exists():
                temp_pem.rename(key_path)
            if temp_crx.exists():
                temp_crx.unlink()
        
        # Build CRX with persistent key
        print("Building CRX with persistent key...")
        cmd = [
            self.chrome_path,
            f"--pack-extension={self.extension_dir}",
            f"--pack-extension-key={key_path}",
            "--no-message-box"
        ]
        
        subprocess.run(cmd, capture_output=True, timeout=30)
        
        temp_crx = self.extension_dir.with_suffix('.crx')
        if temp_crx.exists():
            if crx_path.exists():
                crx_path.unlink()
            temp_crx.rename(crx_path)
        
        return crx_path, key_path, version
    
    def create_updates_xml(self, extension_id, version, crx_url):
        """Create updates.xml file."""
        updates_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<gupdate xmlns="http://www.google.com/update2/response" protocol="2.0">
  <app appid="{extension_id}">
    <updatecheck codebase="{crx_url}" version="{version}"/>
  </app>
</gupdate>'''
        
        updates_path = self.build_dir / "updates.xml"
        with open(updates_path, 'w', encoding='utf-8') as f:
            f.write(updates_xml)
        
        return updates_path
    
    def create_policy_registry(self, extension_id, updates_url):
        """Create Edge policy in registry."""
        policy_key = r'SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist'
        policy_value = f'{extension_id};{updates_url}'
        
        try:
            # Try machine-wide first
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, policy_key) as key:
                winreg.SetValueEx(key, '1', 0, winreg.REG_SZ, policy_value)
            return "HKLM", True
        except PermissionError:
            # Fallback to user-specific
            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, policy_key) as key:
                    winreg.SetValueEx(key, '1', 0, winreg.REG_SZ, policy_value)
                return "HKCU", True
            except:
                return None, False
    
    def generate_deployment_script(self, extension_id, version, crx_url, updates_url):
        """Generate PowerShell deployment script."""
        script_content = f'''# Focus Guard Extension Deployment Script
# Generated automatically

$ExtensionID = "{extension_id}"
$CrxUrl = "{crx_url}"
$UpdatesUrl = "{updates_url}"
$Version = "{version}"

Write-Host "Focus Guard Extension Deployment" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host "Extension ID: $ExtensionID"
Write-Host "Version: $Version"
Write-Host "CRX URL: $CrxUrl"
Write-Host "Updates URL: $UpdatesUrl"
Write-Host ""

# Create Edge policy
$PolicyKey = 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Edge\\ExtensionInstallForcelist'
$PolicyValue = "$ExtensionID;$UpdatesUrl"

try {{
    if (!(Test-Path $PolicyKey)) {{
        New-Item -Path $PolicyKey -Force | Out-Null
    }}
    New-ItemProperty -Path $PolicyKey -Name 1 -Value $PolicyValue -PropertyType String -Force | Out-Null
    Write-Host "SUCCESS: Machine-wide policy created" -ForegroundColor Green
}} catch {{
    Write-Host "ADMIN REQUIRED: Run as Administrator for machine-wide policy" -ForegroundColor Yellow
    
    # Try user-specific
    $PolicyKey = 'HKCU:\\SOFTWARE\\Policies\\Microsoft\\Edge\\ExtensionInstallForcelist'
    try {{
        if (!(Test-Path $PolicyKey)) {{
            New-Item -Path $PolicyKey -Force | Out-Null
        }}
        New-ItemProperty -Path $PolicyKey -Name 1 -Value $PolicyValue -PropertyType String -Force | Out-Null
        Write-Host "SUCCESS: User-specific policy created" -ForegroundColor Green
    }} catch {{
        Write-Host "FAILED: Could not create policy" -ForegroundColor Red
        exit 1
    }}
}}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Upload files to HTTPS server:"
Write-Host "   - {self.build_dir / f'FocusGuard_v{version}.crx'} -> $CrxUrl"
Write-Host "   - {self.build_dir / 'updates.xml'} -> $UpdatesUrl"
Write-Host "2. Close all Edge windows"
Write-Host "3. Open Edge and wait 1-2 minutes"
Write-Host "4. Check edge://policy to verify policy"
Write-Host "5. Check edge://extensions to see extension"
'''
        
        script_path = self.build_dir / "deploy_extension.ps1"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        return script_path
    
    def run_complete_setup(self):
        """Run the complete setup process."""
        print("Focus Guard CRX Complete Setup")
        print("=" * 50)
        
        # Step 1: Build CRX
        crx_path, key_path, version = self.build_crx_package()
        print(f"CRX built: {crx_path}")
        
        # Step 2: Get configuration
        print("\nConfiguration needed:")
        print("1. Extension ID (get from loading extension unpacked)")
        print("2. HTTPS hosting URLs")
        
        # Example values
        extension_id = "abcdefghijklmnopqrstuvwxyz123456"
        crx_url = "https://your-domain.com/focusguard/FocusGuard.crx"
        updates_url = "https://your-domain.com/focusguard/updates.xml"
        
        # Step 3: Create updates.xml
        updates_path = self.create_updates_xml(extension_id, version, crx_url)
        print(f"Updates XML: {updates_path}")
        
        # Step 4: Generate deployment script
        script_path = self.generate_deployment_script(extension_id, version, crx_url, updates_url)
        print(f"Deployment script: {script_path}")
        
        print("\n" + "=" * 50)
        print("SETUP COMPLETE")
        print("=" * 50)
        print("Files created:")
        print(f"  CRX Package: {crx_path}")
        print(f"  Persistent Key: {key_path}")
        print(f"  Updates XML: {updates_path}")
        print(f"  Deploy Script: {script_path}")
        
        print("\nMANUAL STEPS REQUIRED:")
        print("1. Load extension unpacked in Edge to get Extension ID:")
        print("   - Go to edge://extensions/")
        print("   - Enable Developer mode")
        print("   - Click 'Load unpacked'")
        print(f"   - Select: {self.extension_dir}")
        print("   - Copy the 32-character Extension ID")
        
        print("\n2. Update files with real Extension ID:")
        print(f"   - Edit {updates_path}")
        print(f"   - Edit {script_path}")
        print("   - Replace 'abcdefghijklmnopqrstuvwxyz123456' with real ID")
        
        print("\n3. Upload to HTTPS server:")
        print("   - Upload CRX and updates.xml files")
        print("   - Update URLs in deployment script")
        
        print("\n4. Run deployment:")
        print(f"   - Run PowerShell script: {script_path}")
        print("   - Or manually configure registry policy")
        
        return True

def main():
    setup = CompleteCRXSetup()
    return setup.run_complete_setup()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
