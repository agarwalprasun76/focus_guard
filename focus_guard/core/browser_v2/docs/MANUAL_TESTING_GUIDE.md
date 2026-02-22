# Manual Testing Guide for Browser Extension

## Overview

This guide helps you verify the browser extension works correctly before store submission.

---

## What the Unit Tests Cover vs Don't Cover

### ✅ Unit Tests Cover (55 tests)
- **TabStorage**: Memory storage of tab data, browser connection tracking
- **BlockingManager**: Rule matching, caching, domain blocking logic
- **InstallerStrategy**: Strategy selection, browser detection
- **InstallResult/Status**: Data models and serialization

### ❌ Unit Tests Do NOT Cover
- Actual browser extension behavior (`background.js`)
- HTTP communication between extension ↔ tab server
- Real browser tab events
- Extension popup UI
- Chrome/Edge specific behaviors

---

## Manual Testing Steps

### Step 1: Start the Tab Server

```powershell
cd c:\Users\prasun_agarwal\focus_guard
python -c "
from focus_guard.core.browser_v2 import initialize_browser_integration
controller = initialize_browser_integration()
print('Tab server started on http://127.0.0.1:5000')
print('Press Ctrl+C to stop')
import time
while True:
    time.sleep(1)
"
```

Verify server is running:
```powershell
curl http://127.0.0.1:5000/api/health
```

Expected response: `{"status": "ok", ...}`

### Step 2: Load Extension in Developer Mode

**Chrome:**
1. Open `chrome://extensions/`
2. Enable "Developer mode" (top right toggle)
3. Click "Load unpacked"
4. Select: `c:\Users\prasun_agarwal\focus_guard\focus_guard\core\browser\extension\webextension_mv3`
5. Note the Extension ID shown

**Edge:**
1. Open `edge://extensions/`
2. Enable "Developer mode" (left sidebar)
3. Click "Load unpacked"
4. Select same folder as above

### Step 3: Verify Extension Loaded

- Extension icon should appear in toolbar
- Click icon → popup should show connection status
- If "Disconnected", check tab server is running

### Step 4: Test Tab Tracking

1. Open several tabs in the browser
2. Check tab server received data:
```powershell
curl http://127.0.0.1:5000/api/tabs
```

Expected: JSON with list of your open tabs

3. Switch between tabs, verify active tab updates:
```powershell
curl http://127.0.0.1:5000/api/status
```

### Step 5: Test Blocking (Optional)

Add a blocking rule via Python:
```python
from focus_guard.core.browser_v2.tab_server import get_blocking_manager, BlockingRule

manager = get_blocking_manager()
manager.add_rule(BlockingRule(domain="example.com", reason="test"))
```

Then navigate to `example.com` - the extension should check blocking status.

### Step 6: Check Extension Console for Errors

1. Go to `chrome://extensions/` or `edge://extensions/`
2. Find Focus Guard extension
3. Click "Service worker" link to open DevTools
4. Check Console tab for errors

---

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Popup shows "Disconnected" | Tab server not running | Start tab server first |
| No tabs in `/api/tabs` | Extension not sending data | Check extension console for errors |
| Extension won't load | Missing icons | Run `generate_icons.py` or create placeholder PNGs |
| CORS errors in console | Server not sending headers | Server should include CORS headers (already implemented) |

---

## Quick Verification Checklist

- [ ] Tab server starts without errors
- [ ] `/api/health` returns OK
- [ ] Extension loads in browser without errors
- [ ] Popup shows "Connected" status
- [ ] `/api/tabs` returns your open tabs
- [ ] `/api/status` shows browser as connected
- [ ] Switching tabs updates active tab in API
- [ ] Extension console has no errors

---

## Testing Without Full Focus Guard

You can test the extension + tab server in isolation:

```python
# test_extension_manual.py
import time
from focus_guard.core.browser_v2 import initialize_browser_integration

controller = initialize_browser_integration()
print("Tab server running at http://127.0.0.1:5000")
print("\nLoad the extension manually in your browser, then check:")
print("  - http://127.0.0.1:5000/api/health")
print("  - http://127.0.0.1:5000/api/tabs")
print("  - http://127.0.0.1:5000/api/status")
print("\nPress Ctrl+C to stop")

try:
    while True:
        status = controller.get_status()
        if status.connected_browsers:
            print(f"\rConnected: {status.connected_browsers}, Tabs: {status.total_tabs}", end="")
        time.sleep(2)
except KeyboardInterrupt:
    controller.shutdown()
    print("\nStopped")
```
