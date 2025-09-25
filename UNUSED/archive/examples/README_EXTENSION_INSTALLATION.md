# Browser Extension Installation Guide

This guide explains how to install and verify the Focus Guard browser extension, which is required for browser tab tracking and control functionality.

## Automatic Installation

Focus Guard provides a systematic extension installation utility that can automatically install the extension for supported browsers (Chrome and Edge) and verify the installation.

### Using the Installation Utility

Run the installation utility script:

```bash
python examples/install_extension_systematically.py
```

This will:
1. Detect installed browsers on your system
2. Start the tab server if it's not already running
3. Install the extension for each detected browser
4. Verify that the extension is properly connected to the tab server

### Command-line Options

The installation utility supports several command-line options:

```
usage: install_extension_systematically.py [-h] [--browser BROWSER] [--verify] [--timeout TIMEOUT] [--port PORT]

Install Focus Guard browser extension

options:
  -h, --help         show this help message and exit
  --browser BROWSER  Browser to install extension for (chrome, edge, firefox, all)
  --verify           Verify extension installation and connection
  --timeout TIMEOUT  Timeout in seconds for verification (default: 30)
  --port PORT        Port for tab server (default: 5000)
```

Examples:

```bash
# Install for Chrome only
python examples/install_extension_systematically.py --browser chrome

# Install for all browsers and verify installation
python examples/install_extension_systematically.py --verify

# Install with custom timeout and port
python examples/install_extension_systematically.py --timeout 60 --port 5001
```

## Manual Installation

If automatic installation fails or you prefer to install the extension manually:

1. Open your browser's extension page:
   - Chrome: `chrome://extensions`
   - Edge: `edge://extensions`
   - Firefox: `about:addons`

2. Enable "Developer mode" (toggle in the top-right corner for Chrome/Edge)

3. Click "Load unpacked" and select the extension directory:
   ```
   [project_root]/webextension_mv3
   ```

4. Verify that the extension appears in your browser's extension list

## Verifying Installation

To verify that the extension is properly installed and connected to the tab server:

```bash
python examples/install_extension_systematically.py --verify
```

This will check if:
1. The extension is installed in the browser
2. The tab server is running
3. The extension is successfully connecting to the tab server
4. Tab data is being properly transmitted

## Troubleshooting

If you encounter issues with the extension installation or connection:

1. **Tab server not running**:
   - Check if the tab server is running on the expected port (default: 5000)
   - Try starting it manually: `python core/browser_detection/browser_integration/tab_server_v2.py`

2. **Extension not detected**:
   - Make sure the extension is properly installed
   - Check browser console for any error messages
   - Try reinstalling the extension

3. **Connection issues**:
   - Verify that the tab server port is not blocked by a firewall
   - Check if another application is using the same port
   - Try using a different port with the `--port` option

4. **Browser not supported**:
   - Automatic installation is currently supported for Chrome and Edge
   - For other browsers, follow the manual installation instructions

## Integration with Focus Guard

The browser extension integrates with Focus Guard's activity monitoring system through the tab server. Once installed, it will:

1. Track browser tabs and their activity
2. Report tab changes to the Focus Guard application
3. Allow the application to close tabs when necessary (e.g., for blocked domains)

For developers, the extension integration is handled by the `BrowserExtensionIntegration` class in the `core_v2/activity/browser` module.
