# FocusGuard — Architecture Deep Dive

**Created**: February 21, 2026
**Purpose**: Detailed reference for understanding how components interact, data flows, and where to make changes.

---

## 1. Request Flow: Browser Extension → Blocking Decision

```
User navigates to youtube.com/shorts
    │
    ▼
Extension background.js: onUpdated fires
    │
    ├── Check blocking cache (30s TTL)
    │   └── Cache miss → continue
    │
    ├── Check declarativeNetRequest rules (instant, synced every 5 min)
    │   └── Known blocked domain → redirect to blocked.html immediately
    │
    ▼
Extension → POST http://127.0.0.1:58392/api/tabs
    │   (sends tab URL, title, browser info)
    │
    ▼
Tab Server (server.py) → _handle_should_block()
    │
    ├── 1. DomainConfigManager.get_domain_status(domain)
    │   └── Check always_allowed, blocked_categories, system_whitelist
    │
    ├── 2. ClassificationService.classify(url, title, context)
    │   ├── Pre-classification: domain category lookup
    │   ├── Domain-specific classifier (YouTube, Reddit, Google, Twitter)
    │   │   ├── Rule-based classifier (patterns, keywords)
    │   │   └── LLM classifier (OpenAI, if configured + rules insufficient)
    │   └── Generic URL composite classifier (fallback)
    │
    ├── 3. ClassificationBlocker.should_block(classification)
    │   ├── Check enforcement mode (tracking → never block, advisory → allow + log)
    │   ├── Check classification budget (time used vs limit)
    │   ├── Check master distraction budget
    │   ├── Check per-domain rules
    │   └── Check active overrides
    │
    └── 4. Return { should_block, reason, classification, budget_info }
            │
            ▼
Extension receives response
    │
    ├── should_block: true → chrome.tabs.update(tabId, { url: blocked.html })
    │   └── blocked.html loads personalized data from /api/popup_context
    │
    └── should_block: false → cache result, continue browsing
```

## 2. Component Lifecycle (Startup Sequence)

```
FocusGuard.exe launched (or `python -m focus_guard.main`)
    │
    ├── 1. ensure_single_instance() — Windows mutex check
    │
    ├── 2. setup_logging() — RotatingFileHandler → C:\ProgramData\FocusGuard\logs\
    │
    ├── 3. First-run check
    │   └── No deployment_config.json → launch first-run wizard (PyQt5)
    │       └── Wizard saves config → continue
    │
    ├── 4. start_tab_server() — daemon thread
    │   └── TabServerRunner.start()
    │       ├── Initialize TabStorage, BlockingManager, ClassificationService
    │       ├── Start ThreadingHTTPServer on port 58392
    │       ├── Start health monitor (background thread)
    │       └── Start security monitors:
    │           ├── HostsBlocker (writes to hosts file)
    │           ├── IncognitoPolicy (registry policy)
    │           ├── VPNProxyDetector (background check every 2 min)
    │           ├── ClockMonitor (drift detection every 30s)
    │           ├── UserAccountMonitor (new account detection every 5 min)
    │           └── HeartbeatMonitor (extension heartbeat check every 10s)
    │
    ├── 5. _start_admin_gateway() — daemon thread
    │   └── uvicorn runs FastAPI app on port 58393
    │       ├── Mounts SPA from admin_ui/dist at /admin
    │       └── API routes under /admin/api/v1/
    │
    ├── 6. start_coordinator() — daemon thread
    │   └── FocusGuardCoordinator manages:
    │       ├── ActivityComponent (window tracking)
    │       └── BrowserComponent (tab server integration)
    │
    ├── 7. start_email_scheduler() — daemon thread
    │   └── EmailReporter: hourly + daily report schedule
    │
    └── 8. run_tray() — MAIN THREAD (PyQt5 requires main thread)
        └── QSystemTrayIcon with menu:
            ├── Status indicator
            ├── Settings... (opens wizard with pre-filled values)
            ├── Install Extension → Edge Store / Chrome
            ├── View Logs
            ├── Open Data Folder
            ├── About Focus Guard
            └── Exit (graceful shutdown)
```

## 3. Classification Pipeline Detail

```
URL + Title + Context
    │
    ▼
ClassificationService.classify()
    │
    ├── Step 1: Pre-classification domain check
    │   └── DomainConfigManager.get_category_for_domain() with subdomain matching
    │       └── If found → return Classification(category, KNOWN, 1.0)
    │
    ├── Step 2: Domain-specific classifier selection
    │   ├── youtube.com → YouTubeLLMClassifier
    │   │   ├── Rule-based: /shorts → ENTERTAINMENT, /channel → depends
    │   │   └── LLM: page title + metadata → classify
    │   ├── reddit.com → RedditClassifier
    │   │   ├── Rule-based: /r/programming → EDUCATION, /r/memes → ENTERTAINMENT
    │   │   └── LLM: subreddit + title analysis
    │   ├── google.com → GoogleClassifier
    │   │   ├── Rule-based: search query keyword analysis
    │   │   └── LLM: search intent classification
    │   └── twitter.com → TwitterClassifier
    │
    ├── Step 3: Generic URL composite classifier (fallback)
    │   ├── Domain category lookup
    │   ├── URL pattern matching
    │   ├── Title keyword analysis
    │   └── Optional LLM escalation (low-confidence + configurable)
    │
    └── Step 4: Result normalization
        └── Classification(category, usefulness, confidence, source, reason)
            ├── category: EDUCATION, ENTERTAINMENT, SOCIAL_MEDIA, GAMING, NEWS, etc.
            ├── usefulness: EDUCATIONAL, DISTRACTION, MIXED
            ├── confidence: 0.0 - 1.0
            ├── source: RULE, LLM, DOMAIN_CONFIG, UNKNOWN
            └── reason: Human-readable explanation
```

## 4. Admin Gateway ↔ Tab Server Communication

The admin gateway acts as a **proxy/aggregator** for the tab server API:

```
Admin UI (React)                Admin Gateway (FastAPI :58393)           Tab Server (:58392)
    │                                   │                                     │
    ├── GET /admin/api/v1/dashboard ──► DashboardService.get_dashboard() ──► GET /api/health
    │                                   │                                ──► GET /api/distraction/budget
    │                                   │                                ──► GET /api/distraction/sites
    │                                   │                                ──► GET /api/override/stats
    │                                   │                                ──► GET /api/override/log
    │                                   │                                ──► GET /api/enforcement_mode
    │                                   │                                ──► GET /api/blocked/sites
    │                                   │                                ──► GET /api/saved_links/stats
    │                                   ◄── aggregated dashboard JSON ◄──┘
    │
    ├── POST /admin/api/v1/exceptions ► ExceptionService.create() ─────► POST /api/override (temporary)
    │                                                                ──► POST /api/domains/whitelist (permanent)
    │                                                                ──► POST /api/domains/budgets/domain (budgeted)
    │
    ├── GET /admin/api/v1/devices ────► DevicesService.get_devices() ──► GET /api/health
    │                                                                ──► GET /api/status
    │                                                                ──► GET /api/enforcement_mode
    │
    └── POST /admin/api/v1/auth/* ───► AuthService (local, not proxied)
```

The gateway attaches the tab server's bearer token for mutation calls via `TabServerClient`.

## 5. Domain Configuration Data Flow

```
domain_config.json (C:\ProgramData\FocusGuard\)
    │
    ▼
DomainConfigManager (singleton, thread-safe)
    │
    ├── domain_categories: { social_media: [...], entertainment: [...], ... }
    ├── always_allowed_domains: [...]
    ├── always_allowed_categories: [EDUCATION, PRODUCTIVITY]
    ├── blocked_categories: [ENTERTAINMENT, GAMING, SOCIAL_MEDIA, ADULT]
    ├── system_whitelist: [google.com, microsoft.com, ...]
    ├── per_domain_rules: { reddit.com: { max_overrides: 3, ... } }
    ├── classification_budgets: { "ENTERTAINMENT:DISTRACTION": { max_time: 600s } }
    └── master_budget: { max_total_distraction: 2700s }
        │
        ├── Read by: constants.py, classification_blocker.py, domain_blocking.py,
        │           domain_category_classifier.py, windows_config.py, hosts_blocker.py
        │
        ├── Written by: Tab server API endpoints (/api/domains/*)
        │               First-run wizard (DomainManagerPage)
        │               Settings dialog
        │
        └── Integrity: SHA-256 hash in domain_config.hash
                        Tamper detection → revert + email alert
```

## 6. Email Reporting Pipeline

```
EmailReporter (scheduled, daemon thread)
    │
    ├── Hourly report (configurable interval):
    │   ├── Query usage.db for sessions in report window
    │   ├── Fallback: use visible_windows if active_time = 0
    │   ├── Compose HTML email (active time, sessions, top domains)
    │   └── Send via Gmail SMTP (focusguardapp@gmail.com)
    │
    └── Daily report:
        ├── Aggregate full day's activity
        ├── Focus score, streaks, budget usage
        └── Send summary email
```

## 7. Security Monitor Architecture

All security modules are started/stopped via `TabServerRunner._start_security_monitors()`:

| Module | File | Function | Check Interval |
|--------|------|----------|---------------|
| API Auth | `api_auth.py` | Bearer token on mutation endpoints | Per-request |
| Heartbeat Monitor | `heartbeat_monitor.py` | Detect extension disconnect | 10s |
| Hosts Blocker | `hosts_blocker.py` | Sync blocked domains to hosts file | 5 min |
| Incognito Policy | `incognito_policy.py` | Registry policy to disable incognito | On startup |
| VPN/Proxy Detector | `vpn_proxy_detector.py` | Detect VPN/proxy usage | 2 min |
| Clock Monitor | `clock_monitor.py` | Detect clock manipulation | 30s |
| User Account Monitor | `user_account_monitor.py` | Detect new user accounts | 5 min |
| Fail-Closed | `background.js` | Block non-safe domains when server down | Per-request |
| Config Integrity | `domain_config_manager.py` | SHA-256 hash tamper detection | On reload |
| declarativeNetRequest | `background.js` | Sync blocked domains to browser rules | 5 min |

## 8. Data Storage Architecture

| Store | Technology | Location | Contents |
|-------|-----------|----------|----------|
| Deployment config | JSON file | `C:\ProgramData\FocusGuard\deployment_config.json` | Email, enforcement mode, popup config |
| Domain config | JSON file + SHA-256 hash | `C:\ProgramData\FocusGuard\domain_config.json` | Categories, whitelists, budgets, rules |
| API token | JSON file | `C:\ProgramData\FocusGuard\api_token.json` | Bearer token for mutation endpoints |
| Usage DB | SQLite | `C:\Users\<user>\AppData\Local\FocusGuard\usage.db` | Activity sessions, usage tracking |
| Audit log | SQLite | (in-memory or file via AuditLogger) | Override events, screenshots, notifications |
| Activity log | SQLite | (via ActivityLogger) | Page visits, blocks, classifications |
| Search log | SQLite | (via SearchLogger) | Search queries from Google/Bing |
| Saved links | SQLite | (via SavedLinksStore) | Blocked URLs saved for later |
| Domain usage | JSON file | `~/.focus_guard/domain_usage.json` | Per-domain time tracking |
| Master budget | JSON file | `~/.focus_guard/master_distraction_budget.json` | Daily distraction time used |
| Clock state | JSON file | (via ClockMonitor) | Last known clock values |
| Known users | JSON file | (via UserAccountMonitor) | Known Windows user accounts |

## 9. Key Integration Points for Bug Fixes

### When fixing classification issues (BUG-010, BUG-019):
- Start at `browser_v2/tab_server/classification_service.py`
- Check domain-specific classifiers in `classification/classifiers/domains/`
- Review `classification_blocker.py` for blocking decision logic
- Domain config in `domain/domain_config_manager.py` for pre-classification lookups

### When fixing admin UI issues (BUG-012, BUG-013, BUG-015):
- Frontend views in `admin_ui/src/views/`
- API client in `admin_ui/src/api/`
- Backend services in `core/admin_gateway/services/`
- Backend routers in `core/admin_gateway/routers/`

### When fixing reporting issues (BUG-007):
- Email reporter at `focus_guard/deployment/email_reporter.py`
- Usage DB resolver logic in reporter
- Activity monitor at `core/activity/monitor.py`
- Coordinator activity component at `core/coordinator/components/activity.py`

### When fixing blocked page issues (BUG-018):
- Blocked page HTML: `browser/extension/webextension_mv3/blocked.html`
- Blocked page JS: `browser/extension/webextension_mv3/blocked.js`
- Popup context API: `browser_v2/tab_server/server.py` → `_handle_popup_context()`
- Budget data: `browser_v2/tab_server/domain_usage_tracker.py`

### When rebuilding the exe:
```powershell
python -m PyInstaller --clean deployment/application/windows/specs/focusguard_unified.spec
```
- Check that `admin_ui/dist/` exists (run `cd admin_ui && npm run build` first)
- Output goes to `dist/FocusGuard.exe`
- Spec file bundles: config/, extension files, icons, cache, admin_ui/dist
