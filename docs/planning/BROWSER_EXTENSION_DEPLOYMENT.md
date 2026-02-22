# Browser Extension Deployment Strategy

**Document Version**: 1.0  
**Last Updated**: 2026-01-19  
**Status**: Planning

## Executive Summary

The Focus Guard browser extension has been challenging to deploy due to the complexity of programmatic installation. This document outlines the **recommended path forward**: publishing to browser extension stores (Chrome Web Store, Microsoft Edge Add-ons).

---

## Current Challenges with Programmatic Installation

### What We Tried
1. **`--load-extension` flag** - Requires launching browser with special flags; not persistent
2. **Registry policies** - Requires admin privileges; complex setup; security warnings
3. **Native messaging host** - Works for communication but not for installation
4. **Developer mode unpacked extension** - Requires manual user action; shows warnings

### Why These Failed
- **Security restrictions**: Modern browsers actively prevent silent extension installation
- **Admin requirements**: Registry-based policies need elevated privileges
- **User friction**: Manual installation steps reduce adoption
- **Persistence issues**: Extensions loaded via flags don't persist across browser restarts

---

## Recommended Solution: Store Distribution

### Option 1: Chrome Web Store (Recommended for Chrome)

**Process**:
1. Create a Chrome Web Store developer account ($5 one-time fee)
2. Package extension as `.zip` file
3. Submit for review (typically 1-3 business days)
4. Once approved, users install with one click

**Pros**:
- One-click installation for users
- Automatic updates
- No security warnings
- Persistent across browser restarts

**Cons**:
- Review process (1-3 days, can be longer for first submission)
- Must comply with Chrome Web Store policies
- $5 developer fee

**Requirements**:
- Privacy policy URL
- Extension description and screenshots
- Manifest V3 compliance (✅ already implemented)

### Option 2: Microsoft Edge Add-ons (Recommended for Edge)

**Process**:
1. Create Microsoft Partner Center account (free)
2. Submit extension for review
3. Once approved, users install from Edge Add-ons store

**Pros**:
- Free to publish
- Same extension code works (MV3 compatible)
- One-click installation

**Cons**:
- Review process (can take longer than Chrome)
- Smaller user base than Chrome

### Option 3: Enterprise Policy Deployment (For Managed Environments)

If Focus Guard is deployed in a managed environment (corporate, school, family with parental controls):

**Chrome Enterprise Policy**:
```json
{
  "ExtensionInstallForcelist": [
    "extension_id;https://clients2.google.com/service/update2/crx"
  ]
}
```

**Edge Enterprise Policy**:
```json
{
  "ExtensionInstallForcelist": [
    "extension_id;https://edge.microsoft.com/extensionwebstorebase/v1/crx"
  ]
}
```

**Pros**:
- Silent installation without user interaction
- Cannot be uninstalled by user (if desired)

**Cons**:
- Requires domain-joined machines or MDM
- Complex setup for home users

---

## Implementation Plan

### Phase 1: Prepare for Store Submission (1-2 days)

1. **Update extension manifest**
   - Add proper name, description, version
   - Add icons (16x16, 48x48, 128x128)
   - Ensure permissions are minimal and justified

2. **Create store assets**
   - Screenshots (1280x800 or 640x400)
   - Promotional images (optional)
   - Privacy policy page

3. **Test extension thoroughly**
   - Verify all functionality works
   - Test on both Chrome and Edge
   - Ensure no console errors

### Phase 2: Chrome Web Store Submission (1-3 days)

1. Register at https://chrome.google.com/webstore/devconsole
2. Pay $5 developer fee
3. Create new item and upload `.zip`
4. Fill in store listing details
5. Submit for review

### Phase 3: Edge Add-ons Submission (1-5 days)

1. Register at https://partner.microsoft.com/dashboard
2. Create new submission
3. Upload same extension package
4. Fill in store listing
5. Submit for review

### Phase 4: Update Focus Guard Integration

Once extensions are published:

1. Update Focus Guard to detect if extension is installed
2. Provide direct links to store pages for installation
3. Implement extension ↔ app communication via tab server

---

## Extension Store Listing Content

### Name
**Focus Guard Tab Monitor**

### Short Description
Monitors browser tabs for Focus Guard productivity application. Helps track browsing activity and supports distraction blocking.

### Detailed Description
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
- activeTab: Required to get the current tab's URL and title
- storage: Required to store extension settings locally
```

### Privacy Policy (Required)

Create a simple privacy policy page stating:
- Extension only communicates with local Focus Guard application
- No data is sent to external servers
- No personal data is collected by the extension itself
- Data handling is governed by Focus Guard's privacy policy

---

## Alternative: Self-Hosted Distribution

If store distribution is not desired, extensions can be self-hosted:

### Chrome (Limited)
- Only works for enterprise-managed devices
- Requires hosting `.crx` file and update manifest

### Edge
- Similar restrictions to Chrome

### Firefox (More Flexible)
- Can distribute signed `.xpi` files
- Users can install from file
- Still requires Mozilla signing

---

## Recommended Next Steps

1. **Immediate**: Use the standalone activity monitor (already working)
2. **Short-term**: Submit extension to Chrome Web Store and Edge Add-ons
3. **Medium-term**: Update Focus Guard to guide users to install from stores
4. **Long-term**: Consider enterprise deployment options for managed environments

---

## Files to Prepare for Store Submission

```
focus_guard/core/browser/extension/webextension_mv3/
├── manifest.json          # ✅ Exists - needs store metadata
├── background.js          # ✅ Exists
├── content.js            # ✅ Exists (if applicable)
├── popup.html            # May need to add
├── popup.js              # May need to add
├── icons/
│   ├── icon16.png        # Need to create
│   ├── icon48.png        # Need to create
│   └── icon128.png       # Need to create
└── _locales/             # Optional for internationalization
```

---

## Timeline Estimate

| Task | Duration | Dependencies |
|------|----------|--------------|
| Prepare store assets | 1 day | None |
| Chrome Web Store submission | 1-3 days review | Assets ready |
| Edge Add-ons submission | 1-5 days review | Assets ready |
| Update Focus Guard integration | 1 day | Extensions approved |

**Total**: ~1-2 weeks to have extensions available in stores

---

## Conclusion

**Store distribution is the recommended path** for browser extension deployment. While it requires an initial setup effort and review period, it provides:

- Best user experience (one-click install)
- No security warnings
- Automatic updates
- Persistence across browser sessions

The standalone activity monitor can be used immediately while the extension goes through the store review process.
