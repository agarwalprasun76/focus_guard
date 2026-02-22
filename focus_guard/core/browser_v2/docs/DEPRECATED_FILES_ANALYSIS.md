# Deprecated Files Analysis

## Summary

With `browser_v2` implemented, several files in the old `browser/` folder are now **deprecated** or **duplicated**. This document identifies them.

---

## Architecture Clarification

### What Lives Where

| Location | Purpose | Status |
|----------|---------|--------|
| `browser/extension/webextension_mv3/` | **The actual browser extension** (JS/HTML) | **KEEP** - This is the extension code |
| `browser/extension/*.py` | Old Python backend for extension | **DEPRECATED** by browser_v2 |
| `browser_v2/tab_server/` | New Python tab server | **ACTIVE** |
| `browser_v2/installer/` | New installer strategies | **ACTIVE** |
| `browser_v2/integration/` | New integration controller | **ACTIVE** |

### Key Point
The **extension itself** (`background.js`, `manifest.json`, `popup.html`) correctly lives in `browser/extension/webextension_mv3/`. This is fine because:
- It's JavaScript that runs in the browser
- `browser_v2` is the Python backend that the extension talks to

---

## Deprecated Python Files

### Definitely Deprecated (Replaced by browser_v2)

| File | Replaced By | Notes |
|------|-------------|-------|
| `browser/extension/tab_server.py` (46KB) | `browser_v2/tab_server/server.py` | Old monolithic tab server |
| `browser/extension/tab_server_restored.py` (30KB) | `browser_v2/tab_server/server.py` | Backup of old server |
| `browser/extension/tavb_server_restored_v2` (28KB) | `browser_v2/tab_server/server.py` | Another backup (typo in name) |
| `browser/extension/installer.py` (18KB) | `browser_v2/installer/` | Old installer logic |
| `browser/extension/robust_installer.py` (29KB) | `browser_v2/installer/strategies.py` | Old robust installer |
| `browser/extension/process_manager.py` (16KB) | `browser_v2/tab_server/runner.py` | Old process management |
| `browser/extension/native_host.py` (20KB) | Not needed for store distribution | Native messaging approach |
| `browser/extension/native_host_diagnostics.py` (13KB) | Not needed | Diagnostics for native host |
| `browser/extension/validate_native_host.py` (5KB) | Not needed | Validation for native host |
| `browser/extension/focus_guard_native_host.py` (6KB) | Not needed | Native host implementation |
| `browser/extension/windows_admin_utils.py` (15KB) | Partially in `browser_v2/installer/` | Admin utilities |

### Possibly Deprecated (Need Review)

| File | Notes |
|------|-------|
| `browser/extension/integration.py` (11KB) | May have useful integration logic |
| `browser/extension/manager.py` (27KB) | Extension manager - review for useful code |
| `browser/extension/domain_blocking.py` (9KB) | Blocking logic - compare with browser_v2 |
| `browser/extension/interfaces.py` (6KB) | Interface definitions - may be useful |
| `browser/extension/browser_activity_integration.py` (17KB) | Activity integration - review |

### Keep (Extension Files)

| File | Reason |
|------|--------|
| `browser/extension/webextension_mv3/manifest.json` | **KEEP** - Extension manifest |
| `browser/extension/webextension_mv3/background.js` | **KEEP** - Extension core logic |
| `browser/extension/webextension_mv3/popup.html` | **KEEP** - Extension popup UI |
| `browser/extension/webextension_mv3/popup.js` | **KEEP** - Popup logic |
| `browser/extension/webextension_mv3/icons/` | **KEEP** - Extension icons |

### Should Delete (Utility Scripts in Wrong Location)

| File | Reason |
|------|--------|
| `browser/extension/webextension_mv3/generate_icons.py` | Move to `scripts/` or delete after use |
| `browser/extension/webextension_mv3/create_all_icons.py` | Move to `scripts/` or delete after use |
| `browser/extension/webextension_mv3/demo_collect_tabs.py` | Demo script - move or delete |
| `browser/extension/webextension_mv3/focus_guard_native_host.py` | Native host - deprecated |
| `browser/extension/webextension_mv3/focus_guard_native_host.spec` | PyInstaller spec - deprecated |
| `browser/extension/webextension_mv3/install_focus_guard_extension.bat` | Old installer - deprecated |

---

## Recommended Actions

### Phase 1: Immediate Cleanup
1. Move `generate_icons.py` to `scripts/dev/` after generating icons
2. Delete backup files (`tab_server_restored.py`, `tavb_server_restored_v2`)
3. Delete native host files (not needed for store distribution)

### Phase 2: After browser_v2 is Validated
1. Move deprecated files to `UNUSED/browser_backup/`
2. Update imports throughout codebase to use `browser_v2`
3. Add deprecation warnings to old modules

### Phase 3: Final Cleanup
1. Delete `UNUSED/browser_backup/` after confirming everything works
2. Rename `browser_v2` to `browser` (optional)

---

## Size Comparison

| Old (browser/extension/*.py) | New (browser_v2/) |
|------------------------------|-------------------|
| ~250KB total | ~50KB total |
| Monolithic files | Modular design |
| Mixed concerns | Clear separation |
| No tests | 55 unit tests |

---

## Files I Created in Wrong Location

I apologize for the confusion. These files should be moved:

| File | Current Location | Should Be |
|------|------------------|-----------|
| `generate_icons.py` | `browser/extension/webextension_mv3/` | `scripts/dev/` or delete after use |
| `popup.html` | `browser/extension/webextension_mv3/` | ✅ Correct (it's extension UI) |
| `popup.js` | `browser/extension/webextension_mv3/` | ✅ Correct (it's extension UI) |

The `popup.html` and `popup.js` are correctly placed - they're part of the extension that runs in the browser.
