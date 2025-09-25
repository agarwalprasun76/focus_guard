# Native Messaging Host Troubleshooting Guide

This guide provides solutions for common issues with the Focus Guard native messaging host setup.

## General Troubleshooting

### 1. Verify Installation Status

Run the validation script to check if the native messaging host is properly installed:

```bash
python core_v2/browser/extension/validate_native_host.py --verbose
```

### 2. Install or Reinstall Native Messaging Host

If the native messaging host is not installed or you're experiencing issues, reinstall it:

```bash
python core_v2/browser/extension/validate_native_host.py --verbose --install
```

To uninstall and then reinstall:

```bash
python core_v2/browser/extension/validate_native_host.py --verbose --uninstall
python core_v2/browser/extension/validate_native_host.py --verbose --install
```

## Browser-Specific Issues

### Chrome and Edge

1. **Browser Restart Required**
   - Chrome and Edge require a complete browser restart after installing or updating the native messaging host.
   - Close all Chrome/Edge windows and processes before restarting the browser.
   - On Windows, check Task Manager to ensure all browser processes are terminated.

2. **Registry Issues**
   - Chrome and Edge use the Windows Registry for native messaging host registration.
   - Ensure you have administrator privileges when installing the native messaging host.
   - Check registry permissions at:
     - Chrome: `HKEY_CURRENT_USER\Software\Google\Chrome\NativeMessagingHosts\com.focusguard.native_host`
     - Edge: `HKEY_CURRENT_USER\Software\Microsoft\Edge\NativeMessagingHosts\com.focusguard.native_host`

3. **Extension Permissions**
   - Ensure the extension has the `nativeMessaging` permission in its manifest.json.
   - Check that the extension ID matches the one in the native messaging host manifest.

### Firefox

1. **Manifest Location**
   - Firefox uses a JSON manifest file located at:
     - Windows: `%APPDATA%\Mozilla\NativeMessagingHosts\com.focusguard.native_host.json`
     - macOS: `~/Library/Application Support/Mozilla/NativeMessagingHosts/com.focusguard.native_host.json`
     - Linux: `~/.mozilla/native-messaging-hosts/com.focusguard.native_host.json`
   - Ensure this file exists and has the correct permissions.

2. **Extension ID**
   - Firefox extensions use a different ID format than Chrome/Edge.
   - Ensure the extension ID in the native messaging host manifest matches your Firefox extension ID.

3. **File Permissions**
   - The native messaging host executable must be executable by the browser.
   - On Unix-like systems: `chmod +x focus_guard_native_host.py`

## Common Error Messages

### "Native host has exited"
- The native messaging host process crashed or was terminated unexpectedly.
- Check the logs for errors.
- Ensure the native host executable path is correct in the manifest.

### "Specified native messaging host not found"
- The browser cannot find the native messaging host manifest.
- Reinstall the native messaging host.
- Restart the browser completely.

### "Access to the specified native messaging host is forbidden"
- The extension ID in the manifest doesn't match your extension.
- The allowed_origins in the manifest is incorrect.
- Check permissions on the native host executable.

### "Cannot establish connection to native messaging host"
- The native host executable cannot be launched.
- Check if the executable exists and has the correct permissions.
- Verify the path in the manifest is correct and absolute.

## Logging and Debugging

### Enable Debug Logging

1. Set the environment variable `FOCUS_GUARD_DEBUG=1` before running the native host.
2. Check logs in:
   - Windows: `%LOCALAPPDATA%\FocusGuard\logs\native_host.log`
   - macOS/Linux: `~/.focusguard/logs/native_host.log`

### Test Native Host Manually

You can test the native host directly without the browser:

```bash
echo '{"text": "ping"}' | python core_v2/browser/extension/focus_guard_native_host.py
```

This should output a JSON response if the native host is working correctly.

## Checking Browser Extension Logs

### Chrome/Edge
1. Go to `chrome://extensions` or `edge://extensions`
2. Enable "Developer mode"
3. Click on "background page" for the Focus Guard extension
4. Check the console for error messages

### Firefox
1. Go to `about:debugging#/runtime/this-firefox`
2. Click "Inspect" on the Focus Guard extension
3. Check the console for error messages

## Advanced Troubleshooting

### Check Process Communication

Use Process Monitor (Windows) or `lsof` (macOS/Linux) to verify that the browser is attempting to communicate with the native host.

### Verify JSON Format

Ensure all JSON files (manifests, messages) are valid JSON. Use a JSON validator if needed.

### Clean Installation

If all else fails:
1. Uninstall the extension from all browsers
2. Uninstall the native messaging host
3. Restart the computer
4. Reinstall the native messaging host
5. Reinstall the extension

## Getting Help

If you continue to experience issues after trying these troubleshooting steps, please:
1. Run the validation script with `--verbose` flag
2. Collect all log files
3. Note your operating system and browser versions
4. Contact support with this information
