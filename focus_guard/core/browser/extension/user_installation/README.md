# Focus Guard Browser Extension Installation

This directory contains automated installation scripts for the Focus Guard browser extension.

## Quick Installation

### Option 1: Automated Installation (Recommended)
1. Run `install_extension.bat`
2. Follow the on-screen instructions
3. The script will automatically:
   - Detect Chrome and Edge browsers
   - Enable developer mode
   - Create desktop shortcuts
   - Launch browsers with the extension loaded

### Option 2: Manual Installation
If automated installation fails:

1. **Open Browser Extensions Page**:
   - Chrome: `chrome://extensions/`
   - Edge: `edge://extensions/`

2. **Enable Developer Mode**:
   - Toggle "Developer mode" ON (top-right corner)

3. **Load Extension**:
   - Click "Load unpacked"
   - Select folder: `../webextension_mv3`
   - Ensure extension is enabled

## Verification

After installation, verify the extension is working:

1. **Check Extension Status**:
   ```bash
   curl http://127.0.0.1:5000/api/status
   ```
   Should show `"extension_connected": true`

2. **Check Tab Detection**:
   ```bash
   curl http://127.0.0.1:5000/api/tabs
   ```
   Should show your open tabs

3. **Run Focus Guard MVP**:
   ```bash
   python focus_guard/core/mvp_main.py
   ```

## Troubleshooting

### Extension Not Connecting
- Ensure Focus Guard MVP is running (tab server on port 5000)
- Check browser console for errors (F12 → Console)
- Verify extension is enabled in browser settings

### Tab Detection Not Working
- Refresh browser tabs after installing extension
- Check if extension has necessary permissions
- Restart browser completely

### Manual Load Required
If automated installation doesn't work:
- Use the desktop shortcuts created by the installer
- Or manually load via developer mode as described above

## Files

- `install_extension.bat` - Main installation script (Windows)
- `install_extension.ps1` - PowerShell installation logic
- `README.md` - This documentation
- `../webextension_mv3/` - Extension source files
