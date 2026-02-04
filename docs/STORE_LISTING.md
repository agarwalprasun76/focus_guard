# FocusGuard - Chrome Web Store & Edge Add-ons Listing

**Last Updated**: February 2026

---

## Extension Name
```
FocusGuard - Productivity & Time Manager
```

## Short Description (132 characters max)
```
Track browsing time, block distractions, and stay focused. Smart content classification with customizable time budgets.
```
*(119 characters)*

---

## Detailed Description

```
FocusGuard helps you stay productive by managing your browsing time and blocking distractions.

🎯 SMART CONTENT CLASSIFICATION
• Automatically detects educational vs entertainment content
• Works with YouTube, Reddit, Twitter, Google, and more
• Intelligent classification for unknown sites

⏱️ TIME BUDGETS
• Set daily limits for different content types
• Educational content: 60 minutes (default)
• Entertainment: 10 minutes (default)
• Gaming: 5 minutes (default)
• Fully customizable to your needs

🚫 DISTRACTION BLOCKING
• Blocks sites when your budget is exhausted
• Override system for flexibility when you need it
• Shows remaining time on blocked page

📊 USAGE TRACKING
• See exactly where your time goes
• Daily and weekly activity reports
• Export data for personal analysis

🔒 PRIVACY FIRST
• All data stored locally on your device
• No cloud sync required
• No data sold to advertisers
• You control your data

Perfect for:
• Students managing study time
• Parents monitoring children's browsing
• Professionals reducing workplace distractions
• Anyone wanting better focus and productivity

⚠️ REQUIRES: FocusGuard desktop application (free download)
The extension works with the FocusGuard app running on your computer.
Download at: [your-website-url]

📖 HOW IT WORKS
1. Install the FocusGuard desktop application
2. Add this extension to your browser
3. Configure your time budgets and rules
4. Browse normally - FocusGuard tracks your time
5. When budget is exhausted, distracting sites are blocked

💡 TIP: Enable "Allow in incognito" in extension settings for complete coverage.
```

---

## Category
**Productivity**

## Language
**English**

---

## Permission Justifications

Use these explanations when filling out the Chrome Web Store developer dashboard:

### tabs
```
Required to monitor which browser tabs are open and active. This enables FocusGuard to:
- Track which websites you visit
- Measure time spent on each site
- Detect when you switch between tabs
- Apply time budgets accurately
```

### storage
```
Required to store extension settings and cached data locally in your browser. This includes:
- Your connection preferences
- Cached blocking decisions for performance
- Extension state between browser sessions
No data is synced to external servers.
```

### alarms
```
Required for periodic background tasks:
- Regular status updates to the FocusGuard app
- Time tracking intervals
- Checking for expired override sessions
This ensures accurate time measurement even when tabs are inactive.
```

### declarativeNetRequest
```
Required to block distracting websites when your time budget is exhausted. This permission enables:
- Redirecting blocked sites to a friendly "blocked" page
- Enforcing time limits you've configured
- Preventing access to sites you've chosen to block
Blocking rules are determined locally by your FocusGuard app.
```

### host_permissions: <all_urls>
```
Required to classify and track time on any website you visit. FocusGuard needs to:
- Read the URL and title of pages for classification
- Determine if a site is educational, entertainment, etc.
- Apply your time budgets across all websites
Without this permission, FocusGuard could only work on specific pre-defined sites.
```

### incognito: split
```
FocusGuard monitors browsing in incognito/private mode. This is essential because:
- Time limits would be ineffective if users could bypass them via incognito
- Parents using FocusGuard for children need complete coverage
- Productivity tracking requires monitoring all browsing activity
Users who don't want incognito monitoring can disable it in browser settings.
```

---

## Privacy Practices Disclosure

### Single Purpose Description
```
FocusGuard is a productivity tool that tracks browsing time and blocks distracting websites based on user-configured time budgets.
```

### Data Usage Disclosure

**Does your extension collect user data?**
- Yes, but all data is stored locally

**What data is collected?**
- Browsing history (URLs visited)
- Website content (page titles for classification)

**How is the data used?**
- Time tracking and budget enforcement
- Content classification (educational vs entertainment)
- Generating activity reports

**Is data sold to third parties?**
- No

**Is data used for purposes unrelated to the extension's single purpose?**
- No

**Is data transferred to third parties?**
- No (extension communicates only with localhost)

---

## Screenshots Guidance

Create screenshots showing:

1. **Popup Status** (320x200 or similar)
   - Extension popup showing "Connected" status
   - Tab count visible
   - Clean, modern UI

2. **Blocked Page** (1280x800)
   - The blocked.html page in action
   - Shows domain, reason, and override option
   - Demonstrates the blocking feature

3. **Time Budget Exhausted** (1280x800)
   - Blocked page showing "Time budget exhausted"
   - Remaining time display
   - Override request button

4. **Dashboard Preview** (1280x800)
   - FocusGuard desktop app dashboard
   - Shows usage statistics
   - Demonstrates the full product

5. **Configuration** (1280x800)
   - Rules configuration page
   - Time budget settings
   - Shows customization options

---

## Promotional Images

### Small Promo Tile (440x280)
- FocusGuard logo
- Tagline: "Stay Focused. Stay Productive."
- Clean, professional design

### Large Promo Tile (920x680) - Optional
- Feature highlights
- Screenshots montage
- Call to action

### Marquee (1400x560) - Optional
- Hero image for featured placement
- Key benefits listed

---

## Store URLs (After Approval)

Update these after your extension is approved:

**Chrome Web Store:**
```
https://chrome.google.com/webstore/detail/focus-guard/[extension-id]
```

**Edge Add-ons:**
```
https://microsoftedge.microsoft.com/addons/detail/focus-guard/[extension-id]
```

---

## Submission Checklist

### Before Submitting

- [ ] All icons present (16, 32, 48, 128 PNG)
- [ ] manifest.json version is correct
- [ ] Privacy policy URL is live and accessible
- [ ] Extension tested on clean browser profile
- [ ] Incognito mode tested
- [ ] Blocking functionality verified
- [ ] Popup displays correctly
- [ ] No console errors in background script
- [ ] No hardcoded API keys or secrets

### Chrome Web Store

1. [ ] Developer account created ($5 fee paid)
2. [ ] ZIP file created (excluding unnecessary files)
3. [ ] Store listing filled out
4. [ ] Screenshots uploaded (at least 1)
5. [ ] Privacy policy URL added
6. [ ] Permission justifications completed
7. [ ] Category set to "Productivity"
8. [ ] Submitted for review

### Edge Add-ons

1. [ ] Microsoft Partner Center account created
2. [ ] Same ZIP file uploaded
3. [ ] Store listing adapted for Edge
4. [ ] Privacy policy URL added
5. [ ] Submitted for review

---

## Post-Approval Tasks

1. [ ] Note the assigned extension IDs
2. [ ] Update documentation with store URLs
3. [ ] Update FocusGuard app to show store links
4. [ ] Test installation from store on clean profile
5. [ ] Add store badges to README and website
