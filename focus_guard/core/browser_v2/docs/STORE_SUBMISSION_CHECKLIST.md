# Browser Extension Store Submission Checklist

**Last Updated**: 2026-01-31  
**Status**: Ready for Preparation

## Overview

This checklist guides the submission of Focus Guard Tab Monitor to Chrome Web Store and Microsoft Edge Add-ons.

---

## Pre-Submission Requirements

### 1. Extension Assets ✅

- [x] `manifest.json` updated with store-ready metadata
- [x] `popup.html` and `popup.js` created for status display
- [ ] Icons created (run `generate_icons.py` or provide professional icons):
  - [ ] `icons/icon16.png` (16x16)
  - [ ] `icons/icon32.png` (32x32)
  - [ ] `icons/icon48.png` (48x48)
  - [ ] `icons/icon128.png` (128x128)
- [ ] Screenshots for store listing (1280x800 or 640x400)

### 2. Privacy Policy

- [ ] Create privacy policy page (can be hosted on GitHub Pages or similar)
- [ ] Content must include:
  - Extension only communicates with local Focus Guard application
  - No data sent to external servers
  - No personal data collected by extension
  - Data handling governed by Focus Guard's privacy policy

### 3. Store Listing Content

**Name**: Focus Guard Tab Monitor

**Short Description** (132 chars max):
```
Monitors browser tabs for Focus Guard productivity app. Tracks browsing activity and supports distraction blocking.
```

**Detailed Description**:
```
Focus Guard Tab Monitor works with the Focus Guard desktop application to:

• Track active browser tabs for productivity monitoring
• Enable domain-based distraction blocking
• Provide accurate browsing time statistics
• Support focus sessions by blocking distracting websites

This extension requires the Focus Guard desktop application to function.
Download Focus Guard at: [website URL]

Privacy: This extension only communicates with the locally-running Focus Guard 
application on your computer. No data is sent to external servers.

Permissions explained:
- tabs: Required to monitor which tabs are open and active
- storage: Required to store extension settings locally
- declarativeNetRequest: Required for blocking distracting websites
- nativeMessaging: Required for communication with Focus Guard app
- alarms: Required for periodic status updates
```

---

## Chrome Web Store Submission

### Account Setup
- [ ] Create Chrome Web Store developer account
- [ ] Pay $5 one-time developer fee
- [ ] Verify account

### Submission Steps
1. [ ] Go to https://chrome.google.com/webstore/devconsole
2. [ ] Click "New Item"
3. [ ] Upload extension as `.zip` file (exclude unnecessary files)
4. [ ] Fill in store listing:
   - [ ] Name
   - [ ] Description
   - [ ] Category: Productivity
   - [ ] Language: English
5. [ ] Upload screenshots
6. [ ] Add privacy policy URL
7. [ ] Set visibility (Public or Unlisted for testing)
8. [ ] Submit for review

### Files to Include in ZIP
```
manifest.json
background.js
popup.html
popup.js
icons/
  icon16.png
  icon32.png
  icon48.png
  icon128.png
```

### Files to EXCLUDE
```
*.py
*.spec
*.pyc
__pycache__/
build/
dist/
generate_icons.py
create_all_icons.py
demo_*.py
```

---

## Microsoft Edge Add-ons Submission

### Account Setup
- [ ] Create Microsoft Partner Center account (free)
- [ ] Complete account verification

### Submission Steps
1. [ ] Go to https://partner.microsoft.com/dashboard
2. [ ] Navigate to Edge Add-ons section
3. [ ] Click "Create new extension"
4. [ ] Upload same extension package
5. [ ] Fill in store listing
6. [ ] Submit for review

---

## Post-Submission

### After Approval
1. [ ] Update `StoreInstallStrategy` with real extension IDs:
   ```python
   EXTENSION_IDS = {
       "chrome": "actual_chrome_extension_id",
       "edge": "actual_edge_extension_id",
   }
   ```
2. [ ] Update store URLs in documentation
3. [ ] Test one-click installation flow
4. [ ] Update Focus Guard UI to show store links

### Verification
- [ ] Install from store on clean browser profile
- [ ] Verify extension connects to tab server
- [ ] Test tab tracking functionality
- [ ] Test blocking functionality
- [ ] Verify popup shows correct status

---

## Timeline Estimate

| Task | Duration | Dependencies |
|------|----------|--------------|
| Generate/create icons | 1 hour | None |
| Create privacy policy | 1 hour | None |
| Prepare screenshots | 1 hour | Extension working |
| Chrome Web Store submission | 30 min | All above |
| Edge Add-ons submission | 30 min | All above |
| Chrome review | 1-3 business days | Submission |
| Edge review | 1-5 business days | Submission |
| Update Focus Guard integration | 1 hour | Approval |

**Total**: ~1-2 weeks from start to extensions live in stores

---

## Quick Commands

### Create Extension ZIP (PowerShell)
```powershell
cd focus_guard\core\browser\extension\webextension_mv3
Compress-Archive -Path manifest.json, background.js, popup.html, popup.js, icons -DestinationPath FocusGuard_Extension.zip -Force
```

### Generate Icons
```bash
cd focus_guard/core/browser/extension/webextension_mv3
python generate_icons.py
```

---

## Notes

- Chrome Web Store review typically takes 1-3 business days
- Edge Add-ons review can take 1-5 business days
- First submissions may take longer
- Keep extension permissions minimal to speed up review
- Respond promptly to any reviewer feedback
