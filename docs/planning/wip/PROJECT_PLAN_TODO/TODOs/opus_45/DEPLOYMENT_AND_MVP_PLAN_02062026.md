# Focus Guard — Deployment, MVP Testing & Feature Roadmap
**Date**: February 6, 2026  
**Status**: Edge extension approved & live in Microsoft Store. Chrome extension pending approval.

---

## Table of Contents
1. [Current State Assessment](#1-current-state-assessment)
2. [Deployment Plan — Creating the .exe](#2-deployment-plan--creating-the-exe)
3. [MVP User Testing Plan](#3-mvp-user-testing-plan)
4. [Recommended Additional Features](#4-recommended-additional-features)
5. [Immediate Next Steps](#5-immediate-next-steps-action-items)
6. [Post-v1.0 Roadmap — Future Work](#6-post-v10-roadmap--future-work)

---

# 1. Current State Assessment

## What's Working
| Component | Location | Status |
|-----------|----------|--------|
| Activity monitoring + idle detection | `focus_guard/core/activity/` | ✅ Working |
| Classification pipeline (YouTube, Reddit, Twitter, Google, generic URL) | `focus_guard/core/classification/` | ✅ Working |
| Content-type aware budgets | `browser_v2/tab_server/domain_usage_tracker.py` | ✅ Working |
| Override system with classification integration | `browser_v2/tab_server/override_manager.py` | ✅ Working |
| Browser extension (MV3) — blocking, popup, blocked page | `browser/extension/webextension_mv3/` | ✅ Working |
| Tab server with HTTP API (port 58392) | `browser_v2/tab_server/server.py` + `runner.py` | ✅ Working |
| Email reporting system | `focus_guard/deployment/email_reporter.py` | ✅ Working |
| Windows service wrapper | `focus_guard/deployment/service.py` | ✅ Working |
| System tray app (PyQt5) | `focus_guard/gui/windows_tray.py` | ✅ Working |
| PyInstaller spec files (CLI + Tray) | `deployment/application/windows/specs/` | ✅ Exist |
| Build script | `deployment/application/windows/scripts/build_exe.py` | ✅ Exists |
| Installer logic (admin, registry, protected dirs) | `focus_guard/deployment/installer.py` | ✅ Exists |
| Edge extension | Microsoft Store | ✅ **Live** | 
| Edge extension URL | https://microsoftedge.microsoft.com/addons/detail/focusguard-productivity/legaalcjhhgofgpgbbpoadafdjllckgg
| Chrome extension | Chrome Web Store | ⏳ Pending approval |
| Search context tracking | `browser_v2/tab_server/search_context_tracker.py` | ✅ Working |
| Audit & search logging | `browser_v2/tab_server/audit_logger.py`, `search_logger.py` | ✅ Working |
| Screenshot service | `browser_v2/tab_server/screenshot_service.py` | ✅ Working |

## What Needs Work Before .exe Release
| Issue | Priority | Notes |
|-------|----------|-------|
| No unified single-exe entry point | **CRITICAL** | Need one `main.py` that starts tray + tab server + monitor |
| PyInstaller specs reference separate CLI/Tray builds | **HIGH** | Should be unified into single exe |
| No application icon (.ico) | **HIGH** | Specs reference `packaging/focus_guard_icon.ico` which doesn't exist |
| Can we use this icon? | **MEDIUM** | C:\Users\prasun_agarwal\focus_guard\focus_guard\core\browser\extension\webextension_mv3\icons\ChatGPT_FocusGuard_v1.png
| Config UI opens raw JSON in notepad | **MEDIUM** | `windows_tray.py` line 214 — `os.startfile(config_path)` |
| No log rotation / cleanup | **MEDIUM** | `focus_guard_mvp.log` is already 97MB |
| `mvp_main.py` imports old `ExtensionInstaller` | **MEDIUM** | Should use browser_v2 installer |
| Autostart registry uses `sys.executable` (Python path) | **HIGH** | Won't work from frozen exe |
| No first-run setup wizard | **MEDIUM** | User needs guided config for email, budgets |
| LLM classification requires API key | **LOW** | Rule-based works without it; proxy service is post-MVP |
| Version info says 2025 copyright | **LOW** | Update to 2026 |

---

# 2. Deployment Plan — Creating the .exe

## 2.1 Architecture Decision

**Single executable: `FocusGuard.exe`** that bundles:
- System tray icon (PyQt5) — the user-facing shell
- Tab server (HTTP API on port 58392) — browser extension backend
- Activity monitor — tracks active windows
- Email reporter — scheduled reports
- Coordinator — orchestrates all components

```
FocusGuard.exe
    ├── System Tray (PyQt5) ──── user interaction
    ├── Tab Server (aiohttp) ─── browser extension API
    ├── Activity Monitor ──────── window tracking
    ├── Email Reporter ────────── scheduled reports
    └── Coordinator ───────────── lifecycle management
```

## 2.2 Step-by-Step Implementation Plan

### Phase A: Code Cleanup & Unification (2-3 days)

#### A1. Create unified entry point
**File**: `focus_guard/main.py`

This single file will:
1. Check for admin privileges (required for protected dirs, registry)
2. Initialize `DeploymentConfig` (create defaults on first run)
3. Start the tab server in a background thread
4. Start the activity monitor in a background thread
5. Start the email reporter scheduler
6. Launch the PyQt5 system tray (main thread — Qt requires main thread)
7. Handle graceful shutdown on exit

Key design points:
- Tab server and activity monitor run as daemon threads
- PyQt5 event loop runs on main thread
- `sys.frozen` check for PyInstaller paths
- Config/data stored in `C:\ProgramData\FocusGuard\`
- Logs stored in `C:\ProgramData\FocusGuard\logs\`

#### A2. Fix autostart for frozen exe
In `windows_tray.py`, the autostart registry currently writes:
```python
app_path = f'"{sys.executable}" -m focus_guard.gui.windows_tray'
```
For a frozen exe, this should be:
```python
if getattr(sys, 'frozen', False):
    app_path = f'"{sys.executable}"'
else:
    app_path = f'"{sys.executable}" -m focus_guard.gui.windows_tray'
```

#### A3. Fix path resolution for frozen exe
All modules that use `Path(__file__)` for relative paths need a frozen-aware helper:
```python
def get_app_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent
```

Affected files:
- `focus_guard/gui/windows_tray.py` (line 15: `project_root`)
- `focus_guard/deployment/main_service.py` (line 17-20)
- `focus_guard/core/mvp_main.py`
- Any file loading config/data relative to project root

#### A4. Clean up log management
- Implement `RotatingFileHandler` with max 10MB per file, 5 backups
- Move log output to `C:\ProgramData\FocusGuard\logs\`
- Add log cleanup for files older than 30 days
- **Immediate**: Delete or truncate `focus_guard_mvp.log` (97MB)

#### A5. Update `mvp_main.py` to use browser_v2
Replace the old `ExtensionInstaller` import with the browser_v2 integration controller.

#### A6. Create application icon
- Generate a `.ico` file with 16x16, 32x32, 48x48, 128x128 sizes
- We have extension icons at `focus_guard/core/browser/extension/webextension_mv3/icons/ChatGPT_FocusGuard_v1.png`
- Place at `focus_guard/assets/icon.ico`
- Use in PyInstaller spec, system tray, and extension

### Phase B: PyInstaller Build (1-2 days)

#### B1. Create unified PyInstaller spec
**File**: `deployment/application/windows/specs/focusguard_unified.spec`

Key decisions:
- **Entry point**: `focus_guard/main.py`
- **console=False**: No console window (tray app)
- **onefile mode**: Single .exe for easy distribution
- **Exclude**: torch, tensorflow, keras, matplotlib, numpy, scipy (not needed at runtime)
- **Include data**:
  - `config/` → default config templates
  - `webextension_mv3/` → extension files (for manual install fallback)
- **Hidden imports**: All focus_guard submodules, PyQt5, aiohttp, psutil, pywin32, pydantic

```python
# Key hidden imports needed:
hiddenimports = [
    # Core
    'focus_guard.core.coordinator.focus_guard_coordinator',
    'focus_guard.core.activity.monitor',
    'focus_guard.core.activity.enhanced_monitor',
    'focus_guard.core.activity.idle_detector',
    'focus_guard.core.activity.usage_tracker',
    # Browser v2
    'focus_guard.core.browser_v2.tab_server.server',
    'focus_guard.core.browser_v2.tab_server.runner',
    'focus_guard.core.browser_v2.tab_server.blocking',
    'focus_guard.core.browser_v2.tab_server.classification_blocker',
    'focus_guard.core.browser_v2.tab_server.classification_service',
    'focus_guard.core.browser_v2.tab_server.domain_usage_tracker',
    'focus_guard.core.browser_v2.tab_server.override_manager',
    'focus_guard.core.browser_v2.tab_server.storage',
    'focus_guard.core.browser_v2.tab_server.search_context_tracker',
    'focus_guard.core.browser_v2.tab_server.audit_logger',
    'focus_guard.core.browser_v2.tab_server.search_logger',
    'focus_guard.core.browser_v2.tab_server.screenshot_service',
    'focus_guard.core.browser_v2.tab_server.email_integration',
    # Classification
    'focus_guard.core.classification.classifiers',
    'focus_guard.core.classification.enhanced_pipeline',
    # Deployment
    'focus_guard.deployment.config',
    'focus_guard.deployment.email_reporter',
    'focus_guard.deployment.service',
    # GUI
    'focus_guard.gui.windows_tray',
    # System
    'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
    'aiohttp', 'aiohttp.web',
    'psutil', 'pydantic',
    'win32api', 'win32con', 'win32gui', 'win32process',
    'win32serviceutil', 'win32service', 'win32event',
    'win32timezone', 'win32ts',
    'asyncio', 'sqlite3', 'json', 'winreg', 'ctypes',
    'email', 'smtplib', 'ssl',
]
```

#### B2. Build & test cycle
```
Step 1: pip install pyinstaller pywin32 in a clean venv
Step 2: pyinstaller focusguard_unified.spec --clean
Step 3: Test dist/FocusGuard.exe on the dev machine
Step 4: Test on a clean Windows VM (no Python installed)
Step 5: Fix any missing imports/data files
Step 6: Repeat until clean
```

#### B3. Expected output
```
dist/
└── FocusGuard.exe    (~100-200MB, single file)
```

### Phase C: First-Run Experience (1-2 days)

#### C1. First-run detection
On startup, check if `C:\ProgramData\FocusGuard\deployment_config.json` exists.
If not → launch first-run wizard.

#### C2. First-run wizard (PyQt5 dialog)
Simple multi-step dialog:
1. **Welcome** — explain what Focus Guard does
2. **Email Setup** (optional) — SMTP server, recipients
3. **Budget Configuration** — sliders for Education/Entertainment/Gaming time limits
4. **Extension Install** — link to Edge store (live) / Chrome store (when approved)
5. **Done** — "Focus Guard is now running in your system tray"

ADDITIONAL TASKS:
The first run wizard email configuration is a bit unclear. We should elaborate the role of the different emails and what should a user enter. 
The UI for the first run wizard is not awesome, we can improve it.
We should also have more information about the app in the first run wizard and what all settings are available to a user.
We didnt set time limits for educational/ distraction sites/ overrides etc, we should set them.


#### C3. Tray menu improvements
Update the tray context menu:
- **Status**: Show running/stopped + today's usage summary
- **Open Dashboard**: Open a simple PyQt5 window showing today's stats
- **Configure**: Open settings dialog (not raw JSON)
- **View Logs**: Open log directory
- **View Usage**: Open usage history window
- **View Dashboard**: Open dashboard window
- **Extension**: Links to install extension
- **About**: Version info
- **Exit**: Graceful shutdown


#### C4. Create Dashboard Window
- Create a simple PyQt5 window showing today's stats.
- Should be configurable to show usage stats for a specific time period (last 30 mins, last 1 hour etc).
- Should be configurable to show usage stats for a specific site.
- Should be configurable to show usage stats for a specific app.
- Should be configurable to show usage stats for a specific user/ device (currently we are single usr/single device).
- Integrate this with the activity monitor and logging system.

#### C5. Improve the blocked html popup page to show more information and improve the UI/organization of the page.



### Phase D: Distribution Packaging (1 day)

#### D1. Create a ZIP distribution
```
FocusGuard-v1.0.0-win64/
├── FocusGuard.exe
├── README.txt          (quick start guide)
├── PRIVACY_POLICY.txt
└── LICENSE.txt
```

#### D2. (Post-MVP) Inno Setup installer
Creates proper Windows installer with:
- Start menu shortcuts
- Desktop shortcut
- Uninstaller in Add/Remove Programs
- Auto-start option
- Admin privilege elevation

### Phase E: Post-Build Verification (1 day)

#### E1. Smoke test checklist
- [ ] Double-click `FocusGuard.exe` → tray icon appears
- [ ] Right-click tray → menu shows correctly
- [ ] Tab server responds at `http://127.0.0.1:58392/api/health`
- [ ] Install Edge extension from store → connects to tab server
- [ ] Visit a blocked site → blocking works
- [ ] Override request works
- [ ] Activity monitoring logs window changes
- [ ] Email report sends (if configured)
- [ ] App survives running for 1+ hour without crash
- [ ] Closing from tray → clean shutdown
- [ ] Reboot → app auto-starts (if enabled)

## 2.3 Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|-------------|
| A: Code Cleanup & Unification | 2-3 days | None |
| B: PyInstaller Build | 1-2 days | Phase A |
| C: First-Run Experience | 1-2 days | Phase A |
| D: Distribution Packaging | 1 day | Phase B |
| E: Post-Build Verification | 1 day | Phases B, C, D |
| **Total** | **6-9 days** | |

---

# 3. MVP User Testing Plan

## 3.1 Test Environment Setup

### Hardware/Software Requirements
- Windows 10 or 11 (64-bit)
- Chrome or Edge browser (Edge preferred — extension is live)
- 4GB+ RAM
- Internet connection (for extension install + optional email)

### Test Accounts
- **Tester 1 (Primary)**: Clean Windows machine, no Python installed
- **Tester 2 (Developer)**: Dev machine with Python, for debugging
- **Tester 3 (Target user)**: Actual child/student for real-world testing

## 3.2 Test Phases

### Phase 1: Installation Testing (Day 1)

| # | Test Case | Steps | Expected Result | Pass/Fail |
|---|-----------|-------|-----------------|-----------|
| 1.1 | Fresh install | Download & run FocusGuard.exe | Tray icon appears, first-run wizard launches | |
| 1.2 | First-run wizard | Complete all wizard steps | Config saved, extension link shown | |
| 1.3 | Extension install | Install from Edge store | Extension icon appears in browser toolbar | |
| 1.4 | Extension connection | Click extension icon | Popup shows "Connected" to tab server | |
| 1.5 | Admin check | Run without admin | App requests elevation or shows warning | |
| 1.6 | Autostart | Reboot machine | FocusGuard starts automatically | |
| 1.7 | Multiple instances | Run exe twice | Second instance detects first and exits | |

### Phase 2: Core Functionality Testing (Days 2-3)

| # | Test Case | Steps | Expected Result | Pass/Fail |
|---|-----------|-------|-----------------|-----------|
| 2.1 | Educational site | Visit youtube.com/watch (tutorial video) | Classified as EDUCATION, allowed | |
| 2.2 | Entertainment site | Visit youtube.com/shorts | Classified as ENTERTAINMENT, budget tracked | |
| 2.3 | Reddit productive | Visit reddit.com/r/programming | Classified as EDUCATION | |
| 2.4 | Reddit distraction | Visit reddit.com/r/memes | Classified as ENTERTAINMENT | |
| 2.5 | Google search | Search "python tutorial" | Classified as EDUCATION | |
| 2.6 | Google search entertainment | Search "funny cat videos" | Classified as ENTERTAINMENT | |
| 2.7 | Budget exhaustion | Use entertainment budget fully | Site blocked, blocked page shown | |
| 2.8 | Blocked page info | View blocked page | Shows classification, budget used, time remaining | |
| 2.9 | Override request | Click override on blocked page | Override granted with penalty applied | |
| 2.10 | Override limit | Exhaust all overrides | No more overrides available | |
| 2.11 | Incognito mode | Open incognito/InPrivate, visit blocked site | Still blocked (extension active in incognito) | |
| 2.12 | Unknown domain | Visit obscure educational site | Falls back to generic URL classifier | |
| 2.13 | Activity tracking | Switch between windows | Activity log records window changes | |
| 2.14 | Idle detection | Leave computer idle 5 min | Idle time not counted toward budgets | |

### Phase 3: Email & Reporting Testing (Day 3)

| # | Test Case | Steps | Expected Result | Pass/Fail |
|---|-----------|-------|-----------------|-----------|
| 3.1 | Email config | Set up Gmail SMTP in settings | Config saved successfully | |
| 3.2 | Test email | Send test email | Email received by recipient | |
| 3.3 | Hourly report | Wait for hourly report trigger | Report email sent with usage summary | |
| 3.4 | Daily report | Trigger daily report manually | Comprehensive report with charts/stats | |
| 3.5 | No email config | Run without email setup | App works fine, no email errors | |

### Phase 4: Stability & Edge Cases (Days 4-5)

| # | Test Case | Steps | Expected Result | Pass/Fail |
|---|-----------|-------|-----------------|-----------|
| 4.1 | Long-running | Run for 8+ hours | No memory leaks, no crashes | |
| 4.2 | Network loss | Disconnect internet | App continues, extension shows offline gracefully | |
| 4.3 | Browser restart | Close and reopen browser | Extension reconnects to tab server | |
| 4.4 | Tab server crash | Kill tab server process | Auto-restart within 10 seconds | |
| 4.5 | Many tabs | Open 50+ tabs rapidly | No performance degradation | |
| 4.6 | Budget reset | Wait for midnight | Budgets reset to full | |
| 4.7 | Config change | Modify budgets while running | Changes take effect immediately | |
| 4.8 | Log size | Run for several days | Logs rotate, don't exceed limits | |
| 4.9 | Disk space | Fill disk near capacity | App handles gracefully, warns user | |
| 4.10 | Sleep/hibernate | Put PC to sleep, wake up | App resumes correctly | |
| 4.11 | Multiple browsers | Use Chrome + Edge simultaneously | Both tracked correctly | |
| 4.12 | Rapid navigation | Navigate quickly between sites | No missed classifications | |

### Phase 5: Security & Anti-Bypass Testing (Day 5)

| # | Test Case | Steps | Expected Result | Pass/Fail |
|---|-----------|-------|-----------------|-----------|
| 5.1 | Extension disable | Try to disable extension | Requires admin or is detected | |
| 5.2 | Kill process | Try to kill FocusGuard from Task Manager | Restarts automatically (if service) | |
| 5.3 | Config tampering | Edit config to remove blocks | Protected by admin-only directory | |
| 5.4 | DNS bypass | Try using alternative DNS | Still blocked (extension-level blocking) | |
| 5.5 | VPN/Proxy | Try accessing blocked site via proxy | URL still classified and blocked | |

## 3.3 Bug Tracking Template

For each bug found:
```
Bug ID: BUG-XXX
Severity: Critical / High / Medium / Low
Component: [Tray App / Tab Server / Extension / Monitor / Email]
Steps to Reproduce:
  1. ...
  2. ...
Expected: ...
Actual: ...
Screenshot: [if applicable]
Log excerpt: [from C:\ProgramData\FocusGuard\logs\]
```

## 3.4 MVP Acceptance Criteria

The MVP is **shippable** when ALL of the following pass:

- [ ] Fresh install on clean Windows 10/11 works without Python
- [ ] Extension installs from Edge store and connects
- [ ] At least 3 domain classifiers work correctly (YouTube, Reddit, Google)
- [ ] Budget tracking and blocking work end-to-end
- [ ] Override system works with penalties
- [ ] App runs stable for 8+ hours without crash
- [ ] App auto-starts on boot
- [ ] Email reports send correctly (when configured)
- [ ] Incognito browsing is monitored
- [ ] Logs don't grow unbounded
- [ ] No critical or high severity bugs remain open

---

# 4. Recommended Additional Features

## Tier 1: High Impact, Low-Medium Effort (Post-MVP Priority)

### 4.1 Configuration Dashboard (Web UI)
**Effort**: 3-4 days | **Impact**: Very High
- Replace raw JSON config with a Streamlit or simple Flask web UI
- Dashboard showing today's usage, budget status, recent activity
- Accessible at `http://127.0.0.1:58392/dashboard`
- Reuse the existing tab server — add HTML routes alongside API routes
- **Why**: Makes the app usable by non-technical parents

### 4.2 Classification Proxy Service
**Effort**: 2-3 days | **Impact**: High
- Cloudflare Worker that proxies LLM classification calls
- Users don't need their own API key
- Server-side caching reduces costs to ~$1-5/month for 1000 users
- Fallback to local rules if proxy is down
- **Why**: Removes the biggest friction point for new users

### 4.3 Inno Setup Installer
**Effort**: 1-2 days | **Impact**: High
- Proper Windows installer with Add/Remove Programs entry
- Start menu shortcuts, desktop icon
- Auto-start configuration
- Uninstaller that cleans up registry + files
- **Why**: Professional distribution, easier for non-technical users

### 4.4 News & Streaming Classifiers
**Effort**: 3-5 days | **Impact**: Medium-High
- News sites: CNN, BBC, NYT — classify by section (tech vs gossip)
- Streaming: Netflix, Hulu, Disney+, Twitch — almost always entertainment
- **Why**: Major distraction sources currently fall through to generic classifier

### 4.5 Daily/Weekly Summary Notifications
**Effort**: 1-2 days | **Impact**: Medium
- Windows toast notifications at end of day: "You spent 2h on educational content, 45m on entertainment"
- Weekly trend: "Entertainment usage down 20% this week!"
- **Why**: Positive reinforcement drives behavior change

## Tier 2: Medium Impact, Medium Effort

### 4.6 Focus Sessions / Pomodoro Mode
**Effort**: 3-4 days | **Impact**: Medium
- User declares "I'm studying math for 2 hours"
- During focus session: stricter blocking, no overrides
- Break periods: relaxed rules
- Session history and productivity score
- **Why**: Structured focus time is proven effective

### 4.7 Rule Evolution System
**Effort**: 1-2 weeks | **Impact**: High (long-term)
- Log all classifications with context
- Track user overrides ("user said productive, we said distraction")
- Weekly LLM analysis suggests rule updates
- Rule versioning with rollback
- **Why**: System gets smarter over time without manual tuning

### 4.8 Parent/Guardian Portal
**Effort**: 1-2 weeks | **Impact**: High
- Simple web portal where parents can:
  - View child's usage remotely
  - Adjust budgets and rules
  - Receive alerts for concerning activity
  - Approve/deny override requests
- Could be a simple hosted web app or even a Telegram bot
- **Why**: Core use case is parental monitoring

### 4.9 Multi-User Support
**Effort**: 3-5 days | **Impact**: Medium
- Different profiles for different users on same PC
- Windows user detection to auto-switch profiles
- Per-user budgets, rules, and reports
- **Why**: Family computers have multiple users

### 4.10 Application Monitoring (Beyond Browser)
**Effort**: 3-5 days | **Impact**: Medium
- Track time in desktop applications (games, Discord, etc.)
- Classify applications as productive/entertainment
- Block application launch when budget exhausted
- **Why**: Distractions aren't limited to browsers

## Tier 3: High Impact, High Effort (Future Vision)

### 4.11 Screen Capture + Vision LLM
**Effort**: 2-4 weeks | **Impact**: Very High
- Periodic screen capture → Vision LLM analysis
- "Is this screen showing productive work or distraction?"
- Works for ANY application, not just browser
- Privacy-first: local processing option (Ollama + LLaVA)
- **Why**: True "agent watching screen" — the ultimate vision

### 4.12 Mobile Companion App
**Effort**: 4-8 weeks | **Impact**: High
- View usage stats on phone
- Parent receives push notifications
- Remote configuration
- Cross-platform (React Native or Flutter)
- **Why**: Parents want to monitor from their phone

### 4.13 Gamification & Rewards
**Effort**: 2-3 weeks | **Impact**: Medium-High
- Points for productive time, streaks for consistent focus
- Achievements/badges
- Leaderboard (opt-in, family/class)
- Reward system: earn entertainment time by being productive
- **Why**: Positive motivation works better than pure restriction

### 4.14 School/Organization Management
**Effort**: 4-8 weeks | **Impact**: High (for B2B)
- Central admin console for schools/organizations
- Deploy policies via Group Policy / MDM
- Aggregate reporting across students
- Teacher can adjust rules per class period
- **Why**: B2B revenue opportunity

### 4.15 AI Tutor Integration
**Effort**: 4-8 weeks | **Impact**: Medium
- When blocking a distraction, offer to help with current task
- "I see you're supposed to be studying math. Want me to help?"
- Integrates with LLM for subject-specific tutoring
- **Why**: Turns blocking from negative to positive experience

## Feature Priority Matrix

| Feature | Impact | Effort | Priority Score | Recommended Order |
|---------|--------|--------|---------------|-------------------|
| 4.1 Config Dashboard | Very High | 3-4d | ⭐⭐⭐⭐⭐ | 1 |
| 4.2 Classification Proxy | High | 2-3d | ⭐⭐⭐⭐⭐ | 2 |
| 4.3 Inno Setup Installer | High | 1-2d | ⭐⭐⭐⭐ | 3 |
| 4.5 Summary Notifications | Medium | 1-2d | ⭐⭐⭐⭐ | 4 |
| 4.4 News/Streaming Classifiers | Med-High | 3-5d | ⭐⭐⭐ | 5 |
| 4.6 Focus Sessions | Medium | 3-4d | ⭐⭐⭐ | 6 |
| 4.8 Parent Portal | High | 1-2w | ⭐⭐⭐ | 7 |
| 4.10 App Monitoring | Medium | 3-5d | ⭐⭐⭐ | 8 |
| 4.9 Multi-User | Medium | 3-5d | ⭐⭐ | 9 |
| 4.7 Rule Evolution | High | 1-2w | ⭐⭐ | 10 |
| 4.11 Screen Capture | Very High | 2-4w | ⭐⭐ | 11 |
| 4.13 Gamification | Med-High | 2-3w | ⭐⭐ | 12 |
| 4.12 Mobile App | High | 4-8w | ⭐ | 13 |
| 4.14 School Management | High | 4-8w | ⭐ | 14 |
| 4.15 AI Tutor | Medium | 4-8w | ⭐ | 15 |

---

# 5. Immediate Next Steps (Action Items)

## This Week
1. **Create unified `focus_guard/main.py`** — single entry point for the exe
2. **Fix frozen-exe path resolution** — `sys.frozen` checks in all path-dependent modules
3. **Implement log rotation** — `RotatingFileHandler`, clean up 97MB log
4. **Create application icon** — `.ico` with all required sizes
5. **Create unified PyInstaller spec** — single `FocusGuard.exe`

## Next Week
6. **Build and test .exe** — iterative build/test/fix cycle
7. **Create first-run wizard** — PyQt5 dialog for initial setup
8. **Update tray menu** — proper settings dialog, dashboard link
9. **Test on clean Windows VM** — no Python installed
10. **Create distribution ZIP** — exe + README + privacy policy

## Week After
11. **User testing Phase 1-3** — installation + core functionality + email
12. **Bug fixes from testing**
13. **User testing Phase 4-5** — stability + security
14. **Final bug fixes**
15. **Release v1.0.0**

---

# 6. Post-v1.0 Roadmap — Future Work

> **Goal**: These features extend Focus Guard beyond the MVP. They are ordered by
> dependency (earlier items unlock later ones) and designed so the current
> architecture stays flexible. Each item notes the **architectural implications**
> — changes we should keep in mind even before implementation begins.

## Table of Contents (Section 6)
- [6.1 Classification API Server](#61-classification-api-server)
- [6.2 Frontend Configuration & Control App](#62-frontend-configuration--control-app)
- [6.3 Multi-Device Support (macOS First)](#63-multi-device-support-macos-first)
- [6.4 Tracking-Only / Logging Mode](#64-tracking-only--logging-mode)
- [6.5 Personalized Popup Experience](#65-personalized-popup-experience)
- [6.6 Analytics & Distraction-Insight Engine](#66-analytics--distraction-insight-engine)
- [6.7 Security Vulnerability Audit](#67-security-vulnerability-audit)

---

## 6.1 Classification API Server

### Problem
The current classification pipeline calls OpenAI directly from the client.
This requires every user to have an API key, leaks usage costs to the user,
and makes it hard to add caching, rate-limiting, or model upgrades centrally.

### Proposed Solution
Stand up a lightweight **Classification API Server** (FastAPI or similar) that
sits between the Focus Guard client and the LLM provider.

```
Browser Extension ──► Tab Server (local) ──► Classification API Server (remote)
                                                   │
                                                   ├─ Cache layer (Redis / SQLite)
                                                   ├─ LLM provider (OpenAI, Anthropic, local Ollama)
                                                   └─ Rule-based fallback
```

### Key Design Points
| Aspect | Decision |
|--------|----------|
| **Transport** | HTTPS REST (`POST /api/v1/classify`) |
| **Auth** | Per-device API token issued on first registration |
| **Caching** | URL + content-hash → cached classification (TTL 24h) |
| **Rate limiting** | Token-bucket per device (e.g., 100 req/min) |
| **Fallback** | If server unreachable, client falls back to local rule-based classifier (already exists) |
| **Provider abstraction** | Server-side adapter pattern — swap OpenAI ↔ Anthropic ↔ Ollama without client changes |
| **Hosting** | Cloudflare Workers / AWS Lambda for low-cost serverless, or a small VPS |

### Architectural Implications for Current Code
- `classification_service.py` needs a **strategy interface**: `LocalClassifier` vs `RemoteClassifier`
- Tab server config should accept `classification_mode: local | remote | hybrid`
- Remote classifier sends `{url, title, page_text_snippet}` and receives `{category, confidence, reasoning}`
- All classification results should be logged uniformly regardless of source

### Effort Estimate
- **Server**: 3–5 days (FastAPI + caching + auth + deploy)
- **Client integration**: 1–2 days (add `RemoteClassifier` strategy)

---

## 6.2 Frontend Configuration & Control App

### Problem
Configuration is currently done via the first-run wizard (PyQt5) or raw JSON.
There is no way to view real-time status, adjust budgets on the fly, or browse
historical data without digging into log files.

### Proposed Solution
A **web-based frontend** served locally (and optionally remotely for the
parent/guardian portal later).

### Architecture Options
| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **A. Extend tab server (add HTML routes)** | Zero new processes, reuse port 58392 | Mixes concerns, harder to maintain | Good for a quick v1 |
| **B. Separate frontend app (React/Next.js)** | Clean separation, modern UI, easy to host remotely later | Extra process, CORS config | **Recommended for long-term** |
| **C. Streamlit** | Fast to build | Heavy dependency, limited customization | Prototyping only |

### Recommended Stack
- **Frontend**: React + TailwindCSS + shadcn/ui (or similar)
- **API layer**: Extend the existing tab server with a `/api/v1/` namespace for config, usage, analytics
- **Serving**: In dev — Vite dev server; in production — static build served by the tab server or bundled into the exe

### Feature Scope
| Feature | Priority | Notes |
|---------|----------|-------|
| **Dashboard** — today's usage, budget meters, active sessions | P0 | Landing page |
| **Budget configuration** — sliders for each category | P0 | Real-time save via API |
| **Site/app rules** — allowlist, blocklist, per-domain overrides | P0 | CRUD table |
| **Email settings** — SMTP config, report schedule | P1 | Form with test-send button |
| **Activity log viewer** — searchable, filterable table | P1 | Paginated from SQLite |
| **User profile** — name, avatar, preferences | P1 | Feeds into personalized popups (6.5) |
| **Analytics dashboard** — charts, trends (see 6.6) | P2 | Separate tab/page |
| **Multi-device view** — see all devices (see 6.3) | P3 | After multi-device lands |

### Architectural Implications
- Tab server API needs versioned endpoints (`/api/v1/config`, `/api/v1/usage`, etc.)
- Config changes via API must be validated (Pydantic models) and persisted atomically
- WebSocket endpoint for real-time status updates (budget ticking down, new classification events)
- CORS must be configured if frontend runs on a different port
- Authentication: local access can be unauthenticated; remote access (parent portal) needs auth tokens

### Effort Estimate
- **API endpoints**: 3–4 days
- **Frontend (React)**: 5–7 days for core features
- **Integration + polish**: 2–3 days

---

## 6.3 Multi-Device Support (macOS First)

### Problem
Focus Guard is Windows-only. Many families have mixed OS environments.
macOS is the highest-priority second platform.

### Platform Abstraction Strategy

```
focus_guard/
├── core/                    # Platform-agnostic logic (classification, budgets, analytics)
├── platform/
│   ├── __init__.py          # Platform detection + factory
│   ├── base.py              # Abstract interfaces (ActivityMonitor, TrayApp, Autostart, etc.)
│   ├── windows/
│   │   ├── activity.py      # win32api-based window tracking
│   │   ├── tray.py          # PyQt5 system tray (current windows_tray.py)
│   │   ├── autostart.py     # Registry-based autostart
│   │   └── installer.py     # Windows installer logic
│   └── macos/
│       ├── activity.py      # NSWorkspace / CGWindowListCopyWindowInfo
│       ├── tray.py          # rumps or PyQt5 on macOS
│       ├── autostart.py     # LaunchAgent plist
│       └── installer.py     # .app bundle / DMG
```

### Key Decisions
| Aspect | Windows (current) | macOS (new) |
|--------|-------------------|-------------|
| **Activity monitoring** | `win32gui.GetForegroundWindow()` | `NSWorkspace` / `CGWindowListCopyWindowInfo` via `pyobjc` |
| **System tray** | PyQt5 `QSystemTrayIcon` | `rumps` (lightweight) or PyQt5 |
| **Autostart** | Registry `HKCU\...\Run` | `~/Library/LaunchAgents/` plist |
| **Packaging** | PyInstaller → `.exe` | PyInstaller → `.app` bundle or `py2app` |
| **Installer** | Inno Setup / ZIP | DMG with drag-to-Applications |
| **Admin/protection** | Admin-only `ProgramData` dir | macOS permissions (Accessibility, Screen Recording) |
| **Browser extension** | Same MV3 extension | Same MV3 extension (Chrome/Edge/Safari) |

### Architectural Implications for Current Code
- **Extract platform-specific code** into `focus_guard/platform/` with abstract base classes
- `focus_guard/main.py` should use a **platform factory** to get the right implementations
- Tab server, classification, budgets, analytics — all remain **platform-agnostic**
- Config/data paths: abstract `get_data_dir()` → Windows: `C:\ProgramData\FocusGuard\`, macOS: `~/Library/Application Support/FocusGuard/`
- Browser extension is already cross-platform (MV3) — no changes needed
- CI/CD: GitHub Actions with matrix builds (windows-latest, macos-latest)

### Effort Estimate
- **Platform abstraction refactor**: 3–5 days
- **macOS activity monitor**: 3–5 days
- **macOS tray + autostart**: 2–3 days
- **macOS packaging (.app / DMG)**: 2–3 days
- **Testing on macOS**: 2–3 days

---

## 6.4 Tracking-Only / Logging Mode

### Problem
Some users (or parents during an initial observation period) want to **monitor
without blocking** — understand usage patterns before deciding what to restrict.

### Proposed Solution
Add an **enforcement mode** setting with three levels:

| Mode | Behavior |
|------|----------|
| **`tracking`** | Log all activity and classifications. No blocking. No popups. Silent. |
| **`advisory`** | Log + show non-blocking notifications ("You've been on Reddit for 30 min"). |
| **`enforcing`** | Full blocking + budgets + overrides (current behavior). |

### Implementation
- New field in `DeploymentConfig`: `enforcement_mode: tracking | advisory | enforcing`
- `classification_blocker.py` → check mode before returning `should_block: true`
- `server.py` `/api/should_block` → in `tracking` mode always returns `{should_block: false}` but still logs
- Extension popup shows current mode badge
- Frontend (6.2) has a toggle to switch modes
- All logging, analytics, and classification continue regardless of mode — only the **enforcement action** changes

### Architectural Implications
- This is a lightweight change if we add the mode check at the **enforcement boundary** (the `/api/should_block` response)
- Do NOT scatter mode checks throughout the pipeline — keep classification and logging unconditional
- The `advisory` mode needs a notification channel: Windows toast / macOS notification center / browser notification via extension

### Effort Estimate
- **Core implementation**: 1–2 days
- **Advisory notifications**: 1–2 days
- **Frontend toggle**: 0.5 day (after 6.2 exists)

---

## 6.5 Personalized Popup Experience

### Problem
The blocked page and override popups are generic. Adding personal touches
(user's name, motivational tidbits, usage context) makes the experience feel
less like punishment and more like coaching.

### Proposed Changes

#### Blocked Page Enhancements
| Element | Current | Proposed |
|---------|---------|----------|
| **Greeting** | "This site is blocked" | "Hey {name}, this site is blocked" |
| **Context** | Category + budget info | + "You've used {X} of {Y} min today on {category}" |
| **Motivation** | None | Random tidbit from a curated list (e.g., "Did you know? 25 min of focused work = 1 Pomodoro 🍅") |
| **Streak info** | None | "You've been focused for {N} days in a row!" (when analytics module exists) |
| **Tone** | Neutral/stern | Friendly, encouraging, age-appropriate |
| **Visual** | Basic HTML | Styled card with the Focus Guard icon, soft colors |

#### Override Popup Enhancements
| Element | Current | Proposed |
|---------|---------|----------|
| **Prompt** | "Request override?" | "Hey {name}, are you sure? You have {N} overrides left today." |
| **Consequence preview** | Penalty info | "This will cost {X} min from your {category} budget" |
| **Alternative suggestion** | None | "Instead, try: {related educational resource}" (future, with AI tutor) |

### Implementation
- **User profile**: Add `user_name`, `user_avatar_url` (optional), `motivational_tidbits_enabled` to config
- **Blocked page template**: The extension's `blocked.html` becomes a template with `{{name}}`, `{{budget_used}}`, `{{tidbit}}` placeholders filled by the tab server API
- **Tidbits database**: Simple JSON/SQLite table of motivational quotes, rotated daily or randomly
- **Tab server endpoint**: `GET /api/blocked-page-data?url=...` returns personalized payload

### Architectural Implications
- Blocked page should fetch its data from the tab server API rather than having everything inline
- This naturally extends to the analytics dashboard (6.6) — same personalization layer
- Keep tidbits/quotes as a configurable data file, not hard-coded

### Effort Estimate
- **Profile config + API**: 1 day
- **Blocked page redesign**: 1–2 days
- **Tidbits system**: 0.5 day
- **Override popup update**: 0.5 day

---

## 6.6 Analytics & Distraction-Insight Engine

### Problem
Users and parents can see raw logs but have no way to understand **patterns**:
When does the user get distracted? What triggers it? Is focus improving over time?

### Proposed Solution
An **Analytics Module** with two parts:
1. **Data pipeline** — aggregates raw activity/classification logs into structured metrics
2. **Insight engine** — draws inferences and surfaces them via dashboard + notifications

### Architecture

```
Raw Data Sources                  Analytics Pipeline                    Presentation
─────────────────                 ──────────────────                    ────────────
Activity monitor logs ──┐
Tab server audit logs ──┼──► Aggregator ──► Metrics DB ──► Insight Engine ──► Dashboard (6.2)
Classification logs ────┤         │              │                │            Notifications
Override logs ──────────┘         │              │                │            Email reports
                                  ▼              ▼                ▼
                            Hourly rollups   SQLite/DuckDB   LLM summarizer
                            Daily rollups                    (optional)
                            Weekly rollups
```

### Metrics to Track
| Metric | Granularity | Source |
|--------|-------------|--------|
| **Time per category** (education, entertainment, gaming, social, etc.) | Per-hour, per-day, per-week | Tab server audit log |
| **Distraction frequency** | Per-hour | Classification events where category = entertainment/gaming |
| **Distraction triggers** | Per-event | What was the user doing before switching to a distraction? (activity monitor) |
| **Peak distraction times** | Hourly heatmap | Aggregated distraction events by hour-of-day |
| **Override usage** | Daily | Override manager logs |
| **Focus streaks** | Daily | Consecutive time blocks with no distraction classification |
| **Budget utilization** | Daily | Budget tracker |
| **Top distracting domains** | Weekly | Aggregated from classification logs |
| **Productivity score** | Daily | Weighted composite: focus time / total active time |

### Insight Engine (Inference Layer)
| Insight | Method | Example Output |
|---------|--------|----------------|
| **Distraction patterns** | Time-series clustering | "You tend to get distracted between 2–4 PM on weekdays" |
| **Trigger analysis** | Sequence mining (activity before distraction) | "After 45 min of study, you often switch to YouTube" |
| **Improvement trends** | Week-over-week comparison | "Entertainment time down 15% vs last week" |
| **Anomaly detection** | Statistical deviation | "Unusually high Reddit usage today (3x normal)" |
| **Recommendations** | Rule-based + optional LLM | "Consider a 5-min break after 45 min of focus" |

### Dashboard Components (integrates with 6.2)
- **Daily summary card** — productivity score, time breakdown pie chart
- **Hourly heatmap** — distraction density by hour (like GitHub contribution graph)
- **Trend line** — focus time over last 7/30 days
- **Top distractors** — ranked list of domains/apps by time wasted
- **Trigger timeline** — "You switched from VS Code → Reddit at 2:47 PM"
- **Weekly report** — auto-generated summary (can also be emailed)

### Architectural Implications
- **Unified event bus**: All components (activity monitor, tab server, classification, override manager) should emit structured events to a common log/event store
- Current `audit_logger.py` and `search_logger.py` are a good start — extend with a standardized event schema:
  ```python
  @dataclass
  class FocusGuardEvent:
      timestamp: datetime
      event_type: str          # "classification", "override", "activity_switch", "budget_update"
      source: str              # "tab_server", "activity_monitor", "override_manager"
      data: dict               # Event-specific payload
      device_id: str           # For multi-device (6.3)
      user_id: str             # For multi-user
  ```
- Analytics aggregation can run as a background task (every 5 min) or on-demand
- SQLite is sufficient for single-device; consider DuckDB for analytical queries at scale
- The insight engine's LLM summarizer is optional — rule-based insights work without API costs

### Effort Estimate
- **Event schema + unified logging**: 2–3 days
- **Aggregation pipeline**: 3–4 days
- **Dashboard UI (charts, heatmaps)**: 4–5 days
- **Insight engine (rule-based)**: 3–4 days
- **LLM summarizer (optional)**: 2–3 days

---

## 6.7 Security Vulnerability Audit

### Problem
Focus Guard runs with elevated privileges, handles browsing data, and is
designed to resist bypass attempts. A thorough security review is essential
before wider distribution.

### Audit Scope

#### A. Local Attack Surface
| Area | Risk | What to Check |
|------|------|---------------|
| **Tab server (port 58392)** | HIGH | Bound to `127.0.0.1` only? No remote access? Input validation on all endpoints? |
| **Config files** | MEDIUM | Admin-only ACLs on `C:\ProgramData\FocusGuard\`? Can a standard user tamper? |
| **Registry entries** | MEDIUM | Autostart entry protected? Can child delete it? |
| **Log files** | LOW | Do logs contain sensitive data (URLs, page content, API keys)? |
| **SQLite databases** | MEDIUM | Are DB files readable by standard users? Do they contain PII? |
| **IPC / named pipes** | LOW | Any inter-process communication that could be hijacked? |

#### B. Network Attack Surface
| Area | Risk | What to Check |
|------|------|---------------|
| **Tab server HTTP API** | HIGH | No authentication currently — any local process can call it. Add localhost-only + optional token auth. |
| **Extension ↔ tab server** | MEDIUM | Extension uses `fetch("http://127.0.0.1:58392/...")` — is this spoofable? Consider adding a shared secret. |
| **Classification API (6.1)** | HIGH | HTTPS only, token auth, rate limiting, input sanitization |
| **Email (SMTP)** | MEDIUM | Credentials stored in plaintext config? Use OS credential store (Windows Credential Manager / macOS Keychain). |
| **Update mechanism** | HIGH | If we add auto-update, it MUST verify signatures. No unsigned code execution. |

#### C. Bypass Resistance
| Bypass Vector | Current Mitigation | Recommended Improvement |
|---------------|-------------------|------------------------|
| **Kill FocusGuard process** | Single-instance mutex | Add Windows Service wrapper for auto-restart; consider watchdog process |
| **Disable extension** | Extension is in store (can't modify code) | Chrome/Edge enterprise policy to force-install extension |
| **Edit config to remove blocks** | Admin-only directory | Add config integrity hash; alert on tampering |
| **Use different browser** | Only Chrome/Edge monitored | Detect unmonitored browsers, alert parent |
| **Use incognito** | Extension works in incognito (if enabled) | Force "allow in incognito" via enterprise policy |
| **DNS / hosts file** | N/A (extension-level blocking) | Already mitigated — blocking is at URL level, not DNS |
| **VPN / proxy** | URL still classified | Already mitigated — classification is URL-based |
| **Boot into safe mode** | Not running | Detect missed monitoring periods, alert parent |

#### D. Data Privacy & Compliance
| Area | What to Check |
|------|---------------|
| **Data minimization** | Are we collecting only what's needed? |
| **Data retention** | Auto-delete old logs/analytics after configurable period (default 90 days) |
| **PII handling** | URLs can contain PII (search queries, usernames). Anonymize in analytics? |
| **COPPA compliance** | If targeting children <13, parental consent flow required |
| **GDPR/CCPA** | Data export and deletion capabilities |
| **Encryption at rest** | Sensitive data (credentials, detailed logs) should be encrypted |

#### E. Recommended Security Hardening (Priority Order)
1. **Tab server auth** — Add a per-session token that the extension must present. Reject requests without it.
2. **Credential storage** — Move SMTP passwords to Windows Credential Manager / macOS Keychain instead of plaintext JSON.
3. **Config integrity** — HMAC hash of config file; detect and alert on unauthorized changes.
4. **Log sanitization** — Strip or hash PII from analytics data.
5. **Watchdog service** — Windows Service that monitors FocusGuard process and restarts if killed.
6. **Enterprise policy deployment** — Script to set Chrome/Edge policies that force-install the extension and prevent disabling.
7. **Data retention policy** — Auto-purge logs older than N days (configurable, default 90).
8. **Penetration testing** — Manual testing of all API endpoints with fuzzing and injection attempts.
9. **Dependency audit** — `pip audit` / `safety check` on all Python dependencies.
10. **Code signing** — Sign the `.exe` with a code-signing certificate to prevent tampering and reduce SmartScreen warnings.

### Effort Estimate
- **Audit + documentation**: 2–3 days
- **Tab server auth + credential storage**: 2–3 days
- **Config integrity + log sanitization**: 1–2 days
- **Watchdog service**: 2–3 days
- **Enterprise policy scripts**: 1–2 days
- **Penetration testing**: 3–5 days

---

## 6.8 Roadmap Summary & Dependencies

```
                    ┌─────────────────────┐
                    │  v1.0 MVP (current)  │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                 ▼
     ┌────────────────┐ ┌───────────┐ ┌─────────────────┐
     │ 6.1 API Server │ │ 6.4 Track │ │ 6.7 Security    │
     │                │ │ Only Mode │ │     Audit        │
     └───────┬────────┘ └─────┬─────┘ └────────┬────────┘
             │                │                 │
             ▼                ▼                 │
     ┌────────────────┐ ┌───────────┐          │
     │ 6.2 Frontend   │ │ 6.5 Popup │          │
     │     App        │ │ Personal. │          │
     └───────┬────────┘ └───────────┘          │
             │                                  │
             ▼                                  │
     ┌────────────────┐                         │
     │ 6.6 Analytics  │◄───────────────────────┘
     │   & Insights   │
     └───────┬────────┘
             │
             ▼
     ┌────────────────┐
     │ 6.3 Multi-     │
     │ Device (macOS) │
     └────────────────┘
```

### Recommended Implementation Order

| Phase | Items | Rationale | Est. Duration |
|-------|-------|-----------|---------------|
| **R1** | 6.4 Tracking Mode + 6.7 Security Audit (initial) | Low effort, high value. Tracking mode enables safe rollout to new users. Security audit de-risks everything else. | 1–2 weeks |
| **R2** | 6.1 API Server + 6.5 Personalized Popups | API server removes the biggest user friction (API keys). Popups are quick wins for UX. | 2–3 weeks |
| **R3** | 6.2 Frontend App | Depends on API endpoints from 6.1. Unlocks self-service configuration. | 2–3 weeks |
| **R4** | 6.6 Analytics Engine + Dashboard | Depends on frontend (6.2) for visualization. Depends on unified event schema. | 3–4 weeks |
| **R5** | 6.3 Multi-Device (macOS) | Largest refactor. Do after architecture is stable from R1–R4. | 3–4 weeks |

### Cross-Cutting Architectural Principles
1. **Event-driven logging** — All components emit `FocusGuardEvent` objects to a unified store. This feeds analytics (6.6), the frontend (6.2), and email reports.
2. **Strategy/adapter patterns** — Classification (local vs remote), platform (Windows vs macOS), enforcement (tracking vs advisory vs enforcing) all use swappable strategies.
3. **API-first design** — Every feature is accessible via the tab server's REST API. The frontend, extension, and CLI are all API consumers.
4. **Config as code** — All settings are Pydantic models, validated on load, persisted atomically, and exposed via API.
5. **Privacy by default** — Minimal data collection, local-first processing, encrypted credentials, configurable retention.

---

*Section 6 added: February 7, 2026*
*Author: Focus Guard Development Team*

---

## 7. Domain Classification & Management Consolidation

### 7.0 Problem Statement

Domain management is currently fragmented across **7 independent sources**, each with its own format, scope, and update mechanism:

| # | Source | Location | What it stores | Configurable? |
|---|--------|----------|---------------|---------------|
| 1 | `config/app_config.json` | Runtime JSON | Distraction categories (social_media, games, video_streaming) | ✅ File edit |
| 2 | `core/domain/constants.py` | Hardcoded Python | `DOMAIN_CATEGORIES` (9 categories), `DOMAIN_WHITELIST`, `APPLICATION_DOMAINS` | ❌ Code change |
| 3 | `core/config/loader.py` | Hardcoded Python | Default fallback domain lists (social_media, entertainment, etc.) | ❌ Code change |
| 4 | `classification_blocker.py` | Hardcoded Python | `DEFAULT_BLOCKED_CATEGORIES`, `ALWAYS_ALLOWED_CATEGORIES`, `ALWAYS_ALLOWED_DOMAINS` | ❌ Code change |
| 5 | `domain_usage_tracker.py` | `~/.focus_guard/domain_rules.json` | Per-domain rules (max overrides, durations, cumulative budgets) | ✅ API |
| 6 | `domain_usage_tracker.py` | Hardcoded Python | `DEFAULT_CLASSIFICATION_BUDGETS` (8 category:usefulness combos) | ❌ Code change |
| 7 | `domain_usage_tracker.py` | `~/.focus_guard/master_distraction_budget.json` | Master budget (45 min total across all distractions) | ✅ File only |

**Key issues:**
- Adding a single domain (e.g., `pronto.io`) requires editing 3 files
- Category names are inconsistent ("social" vs "social_media" vs "SOCIAL_MEDIA")
- No unified view of all domains with their status, budget, and usage
- Budget defaults are hardcoded — changing a time limit requires code change + rebuild
- Two independent whitelists with different domains
- Usage data can be lost on crash (saves are event-driven, not periodic)

### 7.1 Phase 1: Consolidate Domain Config (Foundation)

**Goal:** Single source of truth for all domain configuration.

#### 7.1.1 Create `C:\ProgramData\FocusGuard\domain_config.json`

Unified config file merging all 7 sources:

```json
{
  "version": 1,
  "domain_categories": {
    "social_media": ["facebook.com", "twitter.com", "instagram.com", "reddit.com", "pronto.io", ...],
    "entertainment": ["youtube.com", "netflix.com", "hulu.com", "twitch.tv", ...],
    "gaming": ["store.steampowered.com", "epicgames.com", ...],
    "news": ["nytimes.com", "cnn.com", "bbc.com", ...],
    "shopping": ["amazon.com", "ebay.com", ...],
    "education": ["khanacademy.org", "coursera.org", "wikipedia.org", ...],
    "productivity": ["notion.so", "trello.com", "asana.com", ...],
    "development": ["github.com", "gitlab.com", "stackoverflow.com", ...],
    "email": ["gmail.com", "outlook.com", "protonmail.com", ...]
  },
  "always_allowed_domains": [
    "mail.google.com", "calendar.google.com", "docs.google.com",
    "github.com", "stackoverflow.com", "teams.microsoft.com", ...
  ],
  "always_allowed_categories": ["EDUCATION", "PRODUCTIVITY"],
  "blocked_categories": ["ENTERTAINMENT", "GAMING", "SOCIAL_MEDIA", "ADULT"],
  "system_whitelist": [
    "google.com", "gstatic.com", "googleapis.com", "microsoft.com",
    "cloudfront.net", "cloudflare.com", ...
  ],
  "per_domain_rules": {
    "reddit.com": {
      "max_overrides_per_day": 3,
      "max_override_duration_seconds": 300,
      "max_cumulative_time_seconds": 900
    }
  },
  "classification_budgets": {
    "EDUCATION:EDUCATIONAL": {"max_cumulative_time_seconds": 3600, "max_overrides_per_day": 10},
    "ENTERTAINMENT:DISTRACTION": {"max_cumulative_time_seconds": 600, "max_overrides_per_day": 2},
    "SOCIAL_MEDIA:DISTRACTION": {"max_cumulative_time_seconds": 600, "max_overrides_per_day": 2},
    "GAMING:DISTRACTION": {"max_cumulative_time_seconds": 300, "max_overrides_per_day": 1}
  },
  "master_budget": {
    "max_total_distraction_seconds": 2700,
    "warning_threshold_percent": 70.0,
    "categories_to_track": ["ENTERTAINMENT", "GAMING", "SOCIAL_MEDIA", "ADULT"]
  }
}
```

#### 7.1.2 Create `DomainConfigManager` singleton

- Loads from `domain_config.json` on startup
- In-memory cache with file-watch reload (detects external edits)
- Thread-safe read/write access
- Atomic saves (write to temp file, then rename)
- All existing components (`constants.py`, `loader.py`, `classification_blocker.py`, `domain_usage_tracker.py`) read from this manager instead of their own hardcoded lists
- Hardcoded lists become **fallback defaults** only used to generate the initial `domain_config.json`

#### 7.1.3 Add periodic auto-save for usage data (crash safety)

- `DomainUsageTracker`: auto-save every 60 seconds if dirty
- `MasterDistractionBudget`: auto-save every 60 seconds if dirty
- Graceful shutdown hook to flush on exit
- This ensures a reboot or crash loses at most 60 seconds of usage data

### 7.2 Phase 2: Domain Management API

**Goal:** Full CRUD API for domain configuration, accessible by extension, frontend, and CLI.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/domains/overview` | All domains with category, status (allowed/blocked/budgeted), budget config, and today's usage stats |
| `GET` | `/api/domains/overview?category=social_media` | Filter by category |
| `GET` | `/api/domains/overview?status=blocked` | Filter by status |
| `POST` | `/api/domains/category` | Move domain(s) to a different category. Body: `{"domains": ["x.com"], "category": "social_media"}` |
| `POST` | `/api/domains/whitelist` | Add/remove from always-allowed list. Body: `{"domain": "x.com", "action": "add"|"remove"}` |
| `GET` | `/api/domains/budgets` | All budget configs (per-domain + classification + master) |
| `POST` | `/api/domains/budgets/domain` | Set per-domain budget. Body: `{"domain": "x.com", "max_cumulative_time_seconds": 600, ...}` |
| `POST` | `/api/domains/budgets/classification` | Set classification budget. Body: `{"key": "GAMING:DISTRACTION", "max_cumulative_time_seconds": 300, ...}` |
| `POST` | `/api/domains/budgets/master` | Update master budget. Body: `{"max_total_distraction_seconds": 3600}` |

All endpoints read/write through `DomainConfigManager`, ensuring consistency.

### 7.3 Phase 3: Domain Manager UI

**Goal:** Visual domain management accessible from the system tray Settings menu.

**Domain Manager page** added to the Settings wizard with:

- **Domain table** — sortable/filterable table showing:
  - Domain name
  - Category (dropdown to change)
  - Status: Allowed ✅ / Blocked 🚫 / Budgeted ⏱️
  - Daily budget (editable)
  - Time used today (progress bar)
  - Overrides used / max
- **Quick actions**: Allow, Block, Set Budget, Move Category
- **Search bar** with real-time filtering
- **Category tabs** for quick navigation
- **Bulk operations**: Select multiple domains → change category / set budget
- **Add domain** button for manually adding new domains
- **Master budget display** at the top showing total distraction time used / limit

### 7.4 Implementation Files

| File | Change |
|------|--------|
| `focus_guard/core/domain/domain_config_manager.py` | **NEW** — Singleton config manager |
| `C:\ProgramData\FocusGuard\domain_config.json` | **NEW** — Unified config file |
| `focus_guard/core/domain/constants.py` | Refactor to read from DomainConfigManager, keep as fallback |
| `focus_guard/core/config/loader.py` | Refactor to read from DomainConfigManager |
| `focus_guard/core/browser_v2/tab_server/classification_blocker.py` | Read blocked/allowed from DomainConfigManager |
| `focus_guard/core/browser_v2/tab_server/domain_usage_tracker.py` | Read rules/budgets from DomainConfigManager; add auto-save timer |
| `focus_guard/core/browser_v2/tab_server/server.py` | Add new `/api/domains/*` endpoints |
| `focus_guard/gui/first_run_wizard.py` | Add DomainManagerPage |

*Section 7 added: February 7, 2026*
*Author: Focus Guard Development Team*

---

## Section 8: Adversarial Bypass & Vulnerability Analysis

> **Purpose:** Red-team assessment of FocusGuard's blocking and monitoring controls.
> A motivated user (e.g., a teenager) will actively look for ways to circumvent restrictions.
> This section catalogs every known bypass vector, rates its severity, and proposes mitigations.

### Severity Rating

| Level | Meaning |
|-------|---------|
| 🔴 **Critical** | Completely defeats blocking with minimal effort; no technical skill required |
| 🟠 **High** | Defeats blocking with moderate effort or partial technical knowledge |
| 🟡 **Medium** | Requires specific knowledge or tools; partial bypass only |
| 🟢 **Low** | Theoretical or requires admin/root access the user shouldn't have |

---

### 8.1 Process & Application Layer

#### 8.1.1 Kill the FocusGuard process — 🔴 Critical

**Attack:** Open Task Manager → End Task on `FocusGuard.exe`. All blocking stops immediately.

**Current state:** The app runs as a regular user-mode process. `require_admin_to_stop` exists in `DeploymentConfig` but is **not enforced** — there is no code that actually prevents termination.

**Mitigations:**
1. Run FocusGuard as a **Windows Service** (Session 0) — cannot be killed from Task Manager without admin.
2. Add a **watchdog process** that restarts FocusGuard if killed. The watchdog itself runs as a service.
3. Use `SetProcessShutdownParameters()` to resist casual termination.
4. **Registry policy** to hide FocusGuard from Task Manager's process list (Group Policy: `DisableTaskMgr` is too heavy — instead, rename the exe to something innocuous).
5. Log every process termination event and alert the accountability partner via email.

#### 8.1.2 Rename or delete the FocusGuard executable — 🟠 High

**Attack:** Navigate to `dist\FocusGuard.exe` and delete/rename it. After reboot, nothing starts.

**Mitigations:**
1. Install to `C:\Program Files\FocusGuard\` (requires admin to modify).
2. Set NTFS ACLs on the install directory: deny write/delete for the standard user.
3. Watchdog service detects missing exe and re-extracts from a backup.

#### 8.1.3 Modify the autostart registry entry — 🟠 High

**Attack:** Open `regedit` → delete `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\FocusGuard`. App won't start on reboot.

**Mitigations:**
1. Move autostart to `HKLM\...\Run` (requires admin to modify).
2. Use a **Scheduled Task** (runs as SYSTEM) instead of a registry Run key.
3. Watchdog periodically verifies the autostart entry and re-creates it if missing.
4. Log and alert if the registry key is tampered with.

#### 8.1.4 Change the system clock — 🟡 Medium

**Attack:** Set the system date forward to tomorrow → all daily budgets and block counters reset to zero.

**Mitigations:**
1. Track the **monotonic elapsed time** (not just wall-clock date) for budget consumption.
2. Detect clock jumps: if the date suddenly advances, carry forward the previous day's usage.
3. Use NTP-verified time from a remote server as a secondary check.

---

### 8.2 Browser Extension Layer

#### 8.2.1 Uninstall or disable the browser extension — 🔴 Critical

**Attack:** Go to `edge://extensions` or `chrome://extensions` → toggle off or remove FocusGuard extension. All browser-level blocking stops.

**Current state:** The extension is installed via store or `--load-extension`. There is no enforcement preventing removal.

**Mitigations:**
1. **Enterprise/Registry Policy** (strongest): Deploy via `ExtensionInstallForcelist` registry key under `HKLM\SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist` (and Chrome equivalent). This force-installs the extension and **prevents the user from removing it**. Requires admin to set up.
2. **Detection + Alert:** The tab server can detect when the extension stops sending heartbeats (no `/api/tabs` POST for >30 seconds). Trigger an alert email and/or lock the screen.
3. Block access to `chrome://extensions` and `edge://extensions` pages via the extension itself (redirect to blocked page).
4. Use `chrome.management.onDisabled` / `onUninstalled` events (limited — the extension can't observe its own uninstall, but a second "sentinel" extension can).

#### 8.2.2 Use a different browser — 🔴 Critical

**Attack:** Install Firefox, Brave, Opera, or any browser that doesn't have the FocusGuard extension. Browse freely.

**Current state:** FocusGuard only monitors Chrome and Edge. No other browsers are covered.

**Mitigations:**
1. **DNS-level blocking** (most robust): Run a local DNS resolver (like Pi-hole or a Windows DNS service) that blocks distraction domains at the network layer. This covers ALL browsers and apps.
2. **Firewall rules:** Use Windows Firewall to block outbound connections to known distraction domains for all processes.
3. **Process monitoring:** Detect when unknown browsers (firefox.exe, brave.exe, opera.exe, etc.) are launched. Alert or kill them.
4. **Hosts file blocking:** Write blocked domains to `C:\Windows\System32\drivers\etc\hosts` pointing to `127.0.0.1`. Covers all browsers. Requires admin to undo.
5. Block installation of other browsers via AppLocker or Software Restriction Policies.

#### 8.2.3 Use Incognito / InPrivate mode — 🟡 Medium

**Attack:** Open an incognito window. The extension may not be active there.

**Current state:** `manifest.json` has `"incognito": "split"`, which means the extension runs in incognito **only if the user explicitly enables it** in extension settings.

**Mitigations:**
1. Enterprise policy: `ExtensionAllowedTypes` + force-install also applies to incognito.
2. Registry policy: `InPrivateModeAvailability = 1` disables InPrivate/Incognito entirely.
3. Detection: Monitor for incognito windows via `chrome.windows.onCreated` with `incognito` flag.

#### 8.2.4 Use the browser's built-in reader mode or cached pages — 🟡 Medium

**Attack:** Use Google Cache (`cache:reddit.com`), Wayback Machine, or browser reader mode to view blocked content without triggering the domain check.

**Mitigations:**
1. Block known proxy/cache domains: `webcache.googleusercontent.com`, `web.archive.org`, `archive.org`, `12ft.io`, etc.
2. Classify the **content** (via title/text), not just the domain — the LLM classifier already does this partially.
3. Add `webcache.googleusercontent.com` and archive sites to the blocked domain list.

---

### 8.3 Network & DNS Layer

#### 8.3.1 Use a VPN or proxy — 🟠 High

**Attack:** Connect to a VPN, SOCKS proxy, or Tor. Traffic bypasses any local DNS or firewall blocking.

**Mitigations:**
1. Block known VPN/proxy applications via process monitoring (openvpn.exe, wireguard.exe, tor.exe).
2. Block VPN ports (1194, 51820, etc.) via Windows Firewall.
3. Detect VPN adapter creation (new network interfaces appearing).
4. The browser extension still works regardless of VPN — it checks the domain at the application layer, not the network layer. **This is a strength of the current architecture.**

#### 8.3.2 Modify the hosts file — 🟢 Low

**Attack:** If FocusGuard uses hosts-file blocking, the user could edit `C:\Windows\System32\drivers\etc\hosts` to remove entries.

**Mitigations:**
1. Requires admin privileges to edit the hosts file.
2. Set a file watcher on the hosts file; re-apply entries if tampered.
3. Use NTFS ACLs to deny write access to the standard user.

#### 8.3.3 Use a web-based proxy — 🟡 Medium

**Attack:** Visit `https://www.proxysite.com/` or similar web proxy to access blocked sites through an intermediary.

**Mitigations:**
1. Maintain a list of known web proxy domains and block them.
2. The LLM classifier can detect proxy site content and block it.
3. Block the "proxy" and "unblock" categories in domain classification.

---

### 8.4 API & Configuration Tampering

#### 8.4.1 Call the tab server API directly to disable blocking — 🔴 Critical

**Attack:** The tab server listens on `http://127.0.0.1:58392` with **zero authentication**. Anyone can:
- `POST /api/enforcement_mode` with `{"mode": "tracking"}` → disables all blocking
- `POST /api/domains/whitelist` with `{"domain": "reddit.com", "action": "add"}` → whitelist any domain
- `POST /api/override` → grant unlimited overrides
- `DELETE /api/should_block/rules` → remove all blocking rules

**Current state:** No authentication, no authorization, no rate limiting on any API endpoint.

**Mitigations:**
1. **API authentication:** Require a bearer token or HMAC signature for all mutation endpoints. The extension gets the token at install time; the token is stored in the extension's `chrome.storage.local` (not accessible to web pages).
2. **Localhost binding is not enough:** Any local process or script can call `127.0.0.1:58392`. Add origin checking (only allow requests from the extension's origin).
3. **Read-only vs. write endpoints:** Separate GET (informational) from POST/DELETE (mutations). Require stronger auth for mutations.
4. **Rate limiting:** Cap override requests to prevent brute-force budget exhaustion.
5. **Audit trail:** All API mutations are logged with timestamp and source. Alert on suspicious patterns (e.g., enforcement mode changed to tracking).
6. **Config change cooldown:** After changing enforcement mode, require a waiting period (e.g., 24 hours) before it takes effect, with an immediate email notification to the accountability partner.

#### 8.4.2 Edit domain_config.json directly — 🟠 High

**Attack:** Open `C:\ProgramData\FocusGuard\domain_config.json` in a text editor. Remove domains from blocked categories, add to whitelist, increase budgets to 999999 seconds.

**Current state:** The file is world-readable and world-writable. `DomainConfigManager` has a file watcher that reloads on change — so edits take effect immediately.

**Mitigations:**
1. Set NTFS ACLs: only the FocusGuard service account (SYSTEM) can write; standard user gets read-only.
2. **Config integrity check:** Hash the config on save; verify hash on load. If tampered, revert to last known good or alert.
3. Store a backup copy in a location the user can't easily find/modify.
4. **Digital signature:** Sign the config with a key only the admin/parent knows. Reject unsigned changes.
5. Alert the accountability partner when config changes are detected.

#### 8.4.3 Edit deployment_config.json to change enforcement mode — 🟠 High

**Attack:** Edit `C:\ProgramData\FocusGuard\deployment_config.json`, change `"enforcement_mode": "enforcing"` to `"enforcement_mode": "tracking"`.

**Mitigations:**
1. Same ACL protections as domain_config.json.
2. Config integrity/signature check.
3. The enforcement mode change should trigger an immediate email alert.
4. Require a password (set by the parent/admin) to change enforcement mode.

#### 8.4.4 Delete usage/budget data files — 🟡 Medium

**Attack:** Delete `~/.focus_guard/domain_usage.json` and `~/.focus_guard/master_distraction_budget.json`. All daily usage resets to zero — full budget restored.

**Mitigations:**
1. Move data files to `C:\ProgramData\FocusGuard\` with restricted ACLs.
2. Keep a running hash/checksum; detect if files are truncated or deleted.
3. Maintain a secondary "high-water mark" file that records the maximum usage seen today — even if the main file is deleted, the high-water mark persists.
4. Server-side backup: periodically sync usage data to a remote endpoint.

---

### 8.5 Extension & Blocked Page Bypasses

#### 8.5.1 Navigate away from blocked page before redirect completes — 🟡 Medium

**Attack:** Quickly press Back or navigate to a new URL before the `chrome.tabs.update()` redirect to `blocked.html` completes. The page may partially load.

**Current state:** Blocking is reactive (check on `onUpdated` → redirect). There's a race window.

**Mitigations:**
1. Use `chrome.webNavigation.onBeforeNavigate` (fires earlier than `onUpdated`) for faster interception.
2. Use `declarativeNetRequest` rules for **synchronous** blocking of known domains (no race condition).
3. Combine both: declarativeNetRequest for known domains (instant), real-time API check for unknown domains (async).

#### 8.5.2 Abuse the override system — 🟡 Medium

**Attack:** Request overrides repeatedly across different domains to accumulate distraction time beyond the master budget. Or request an override, use it, then clear browser cookies/cache to reset the extension's local state.

**Current state:** Override tracking is server-side (good), but the master budget check only runs at override-request time, not continuously during the override.

**Mitigations:**
1. Server-side tracking is already robust — clearing browser state doesn't reset server-side counters. ✅
2. Add continuous budget checking during active override sessions (already partially implemented via `tickUsageTracker`).
3. Cap total overrides across ALL domains per day (not just per-domain).

#### 8.5.3 Open blocked content in a new window/tab rapidly — 🟡 Medium

**Attack:** Open 10+ tabs to a blocked site simultaneously. The async blocking check may not catch all of them before content loads.

**Mitigations:**
1. Use `declarativeNetRequest` for known blocked domains — this is synchronous and handles all tabs.
2. Rate-limit tab creation events.
3. The 30-second blocking cache helps here — once one tab is checked, the cache serves the decision for subsequent tabs instantly.

#### 8.5.4 Use DevTools to modify extension behavior — 🟡 Medium

**Attack:** Open DevTools on the extension's service worker, modify `CONFIG.useRealTimeBlocking = false`, or clear the `blockingCache`.

**Mitigations:**
1. Enterprise policy: `DeveloperToolsAvailability = 2` disables DevTools entirely.
2. The extension can detect if DevTools is open (via `chrome.debugger` API or timing attacks) and alert.
3. Even if the extension is tampered with, the **server still classifies and logs** all activity — the accountability report will show unblocked distraction visits.

---

### 8.6 Content & Classification Bypasses

#### 8.6.1 Subdomain evasion — 🟠 High (FIXED)

**Attack:** Access `stanfordohs.pronto.io` instead of `pronto.io`. Exact-match domain lookups miss the subdomain.

**Status:** **Fixed in Session 7** — added `matches_domain()` utility with subdomain-aware matching across `DomainConfigManager`, `ClassificationBlocker`, and pre-classification category check.

#### 8.6.2 Use URL shorteners or redirects — 🟡 Medium

**Attack:** Use `bit.ly/xyz`, `t.co/abc`, or `tinyurl.com/xyz` to reach blocked sites. The initial domain is not blocked; the redirect lands on the blocked domain.

**Current state:** The extension checks on `onUpdated` which fires after redirects resolve, so the final URL **is** checked. However, there may be a brief content flash.

**Mitigations:**
1. Block known URL shortener domains entirely (bit.ly, t.co, tinyurl.com, etc.).
2. The current `onUpdated` listener already catches the final redirected URL. ✅
3. Add `webNavigation.onCompleted` as a secondary check.

#### 8.6.3 LLM classifier misclassification — 🟡 Medium

**Attack:** The LLM classifier may misclassify a site. For example, `stanfordohs.pronto.io` was classified as `EDUCATION` with 0.90 confidence (it's actually a social messaging app).

**Current state:** The pre-classification domain config check (added in Session 7) now catches known domains before the LLM runs. But truly unknown sites still depend on LLM accuracy.

**Mitigations:**
1. Pre-classification check against known domain categories (now implemented). ✅
2. Maintain a **community-sourced blocklist** that's updated regularly.
3. Use multiple classifiers and require consensus.
4. Allow the accountability partner to review and correct classifications.
5. Log all classifications for periodic review.

#### 8.6.4 Access distracting content on allowed domains — 🟡 Medium

**Attack:** Watch entertainment videos embedded on `docs.google.com` (allowed), use Google Translate as a proxy (`translate.google.com/translate?u=reddit.com`), or access social features on `github.com`.

**Mitigations:**
1. The search context tracker already detects entertainment content on file-sharing sites. ✅
2. Block `translate.google.com` when used as a proxy (detect `?u=` parameter pointing to blocked domains).
3. Content-level classification (analyze page title/content, not just domain).
4. Time-based anomaly detection: if a user spends 2+ hours on `docs.google.com`, flag for review.

---

### 8.7 Physical & OS-Level Bypasses

#### 8.7.1 Boot from USB / use a different OS — 🟢 Low

**Attack:** Boot from a Linux USB drive or use a virtual machine. FocusGuard doesn't exist in that environment.

**Mitigations:**
1. BIOS password to prevent boot device changes.
2. Disable USB boot in BIOS/UEFI settings.
3. Network-level blocking (router/DNS) covers all devices on the network.
4. This is largely outside the scope of application-level controls.

#### 8.7.2 Use a mobile device — 🟢 Low

**Attack:** Use a phone or tablet to access distracting content. FocusGuard only runs on the PC.

**Mitigations:**
1. Out of scope for the desktop application.
2. Network-level blocking (Pi-hole, router rules) can cover all devices.
3. Companion mobile app (future roadmap).

#### 8.7.3 Create a new Windows user account — 🟡 Medium

**Attack:** Create a new local user account. FocusGuard's per-user config and autostart won't apply to the new account.

**Mitigations:**
1. Install FocusGuard as a **machine-wide service** (runs for all users).
2. Use `HKLM` registry keys instead of `HKCU`.
3. Monitor for new user account creation events.
4. Restrict account creation via Group Policy (requires admin).

---

### 8.8 Priority Mitigation Roadmap

Based on severity and implementation effort, here is the recommended order of implementation:

| Priority | Vulnerability | Mitigation | Effort |
|----------|--------------|------------|--------|
| **P0** | 8.4.1 — Unauthenticated API | Add bearer token auth to mutation endpoints | 1-2 days |
| **P0** | 8.2.1 — Extension removal | Enterprise policy force-install + heartbeat detection | 1 day |
| **P0** | 8.1.1 — Process kill | Run as Windows Service + watchdog | 2-3 days |
| **P1** | 8.2.2 — Alternative browsers | Hosts-file blocking for known domains (covers all browsers) | 1 day |
| **P1** | 8.4.2 — Config file tampering | NTFS ACLs + integrity hash + alert on change | 1 day |
| **P1** | 8.4.3 — Enforcement mode tampering | Password-protect enforcement mode changes + email alert | 1 day |
| **P1** | 8.1.3 — Autostart tampering | Move to HKLM + Scheduled Task + watchdog verification | 0.5 day |
| **P2** | 8.5.1 — Redirect race | Add declarativeNetRequest rules for known blocked domains | 1 day |
| **P2** | 8.2.3 — Incognito mode | Registry policy to disable InPrivate + force extension in incognito | 0.5 day |
| **P2** | 8.4.4 — Usage data deletion | Move to ProgramData + ACLs + high-water mark | 0.5 day |
| **P2** | 8.3.1 — VPN/proxy | Block VPN executables + detect new network adapters | 1 day |
| **P3** | 8.6.2 — URL shorteners | Block shortener domains | 0.5 day |
| **P3** | 8.6.4 — Allowed domain abuse | Enhanced content classification + translate proxy detection | 1 day |
| **P3** | 8.1.4 — Clock manipulation | Monotonic time tracking + clock jump detection | 0.5 day |
| **P3** | 8.7.3 — New user account | Machine-wide service + HKLM config | 1 day |

**Total estimated effort for P0+P1:** ~7-8 days
**Total estimated effort for all:** ~13-14 days

---

### 8.9 Architectural Recommendations

1. **Defense in depth:** No single layer should be the sole line of defense. Combine browser extension (application layer) + hosts file / DNS (network layer) + Windows Service (process layer) + enterprise policies (OS layer).

2. **Fail-closed, not fail-open:** Currently, if the tab server is unreachable, the extension defaults to `shouldBlock: false` (fail-open). This should be configurable — in enforcing mode, unknown/unreachable should default to **block**.

3. **Accountability over restriction:** Perfect blocking is impossible. The most effective deterrent is **knowing that all activity is logged and reported**. Ensure the reporting pipeline is tamper-resistant and always operational.

4. **Separation of admin and user:** The person configuring FocusGuard (parent/admin) should have a different privilege level than the person being monitored. Config changes should require a password or admin credentials.

5. **Tamper detection over tamper prevention:** It's often easier to detect and alert on bypass attempts than to prevent them entirely. Every bypass attempt should generate an alert to the accountability partner.

## Integration Tests for the whole application and organization of the test suite.
I believe we have a very framgemented test suite and need to organize it better so we can run the full suite of unit and integration tests before making a release.

*Section 8 added: February 8, 2026*
*Author: Focus Guard Development Team (Adversarial Analysis)*

✅ Subdomain matching fix (matches_domain utility)
✅ Pre-classification category check in ClassificationBlocker
✅ Section 8: Adversarial Bypass & Vulnerability Analysis (22 vectors, mitigations, priority roadmap)
Remaining:

🔲 Rebuild exe and test end-to-end with stanfordohs.pronto.io
Just say the word when you're ready to pick back up.

## We should make the user config decide on fail open vs fail close if there is an issue with the browser extension.