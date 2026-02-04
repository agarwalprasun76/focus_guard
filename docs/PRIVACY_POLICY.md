# FocusGuard Privacy Policy

**Last Updated**: February 2026

## Overview

FocusGuard is a productivity application that helps you manage your browsing time and reduce distractions. This privacy policy explains what data the FocusGuard browser extension collects and how it is used.

## What Data We Collect

The FocusGuard browser extension collects the following information:

### Browsing Activity
- **URLs of websites you visit** - Used to classify content and track time spent
- **Page titles** - Used for activity reports and content classification
- **Time spent on each website** - Used to enforce time budgets
- **Tab activity** (active/inactive state) - Used for accurate time tracking

### Classification Data
- **Content categories** - Sites are classified as Educational, Entertainment, Gaming, Social Media, etc.
- **Domain information** - Used to apply blocking rules and time budgets

## How We Use Your Data

### Local Processing
- **All core functionality runs locally** on your device
- Time tracking, budget enforcement, and blocking decisions are made locally
- Activity data is stored in `C:\ProgramData\FocusGuard\` on Windows

### Communication with FocusGuard Desktop App
- The extension communicates **only with the locally-running FocusGuard application** on your computer (http://127.0.0.1:58392)
- **No data is sent to external servers** by the extension itself
- All blocking decisions are made by your local FocusGuard installation

### Optional Features (Desktop App)
The FocusGuard desktop application (separate from this extension) may optionally:
- Send email reports to configured recipients (e.g., parents, accountability partners)
- Use third-party classification APIs for unknown domains (anonymized, URL only)

These features are configured in the desktop app, not the extension.

## Data We Do NOT Collect

- ❌ We do NOT collect personal identification information
- ❌ We do NOT track your browsing history for advertising
- ❌ We do NOT sell or share your data with third parties
- ❌ We do NOT use cookies or tracking pixels
- ❌ The extension does NOT send data to any external servers

## Incognito/Private Browsing

FocusGuard monitors browsing activity in **incognito/private browsing mode**. This is a core feature required for the application to effectively manage screen time - otherwise, time limits could be bypassed by using private browsing.

**Important**: If you do not want monitoring in incognito mode, you can disable the extension's incognito access in your browser's extension settings.

## Data Storage & Retention

- **Local storage only** - All data is stored on your device
- **Automatic cleanup** - Logs are automatically deleted after 30 days (configurable)
- **Database retention** - Activity records are kept for 90 days (configurable)
- **User control** - You can delete all data by uninstalling the application

## Your Rights & Controls

You have full control over your data:

1. **View your data** - Access all collected data through the FocusGuard dashboard
2. **Export your data** - Export activity reports at any time
3. **Delete your data** - Uninstalling FocusGuard removes all stored data
4. **Disable monitoring** - Disable or uninstall the extension at any time
5. **Configure retention** - Adjust how long data is kept in settings

## Permissions Explained

The extension requests the following permissions:

| Permission | Why It's Needed |
|------------|-----------------|
| `tabs` | Required to monitor which websites you visit and track time spent on each |
| `storage` | Stores your preferences and cached data locally in the browser |
| `alarms` | Enables periodic status updates and time tracking |
| `declarativeNetRequest` | Required to block distracting websites when time budgets are exhausted |
| `host_permissions: <all_urls>` | Needed to classify and track time on any website you visit |

## Security

- All communication between the extension and desktop app uses localhost only
- No external network requests are made by the extension
- The extension contains no obfuscated or remotely-loaded code
- All functionality is contained within the extension bundle

## Children's Privacy

FocusGuard can be used as a parental control tool. When used for children:
- Parents configure the rules and receive reports
- Children's browsing data is stored locally and in optional email reports
- No data is shared with third parties

## Changes to This Policy

We may update this privacy policy from time to time. Changes will be reflected in the "Last Updated" date at the top of this document.

## Contact

For privacy concerns or questions about this policy, please contact:
- **Email**: [your-support-email@example.com]
- **GitHub**: [your-github-repo-url]

## Open Source

FocusGuard is open source software. You can review the complete source code to verify our privacy practices:
- **Repository**: [your-github-repo-url]

---

*This privacy policy applies to the FocusGuard browser extension version 1.0.0 and later.*
