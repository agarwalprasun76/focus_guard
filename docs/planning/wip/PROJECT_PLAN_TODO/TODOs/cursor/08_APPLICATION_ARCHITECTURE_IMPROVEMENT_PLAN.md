# FocusGuard — Application Architecture Improvement Blueprint

**Created**: February 21, 2026  
**Purpose**: Comprehensive audit of the full application — identifying what's missing, cumbersome, fragile, or inelegant — with a prioritized roadmap for improvements.

---

## Classification System

| # | Category | Issue | Impact | Effort |
|---|----------|-------|--------|--------|
| 1 | CRITICAL | Auth bug in login | User stays null after login | 5 min |
| 2 | CRITICAL | Dashboard makes 12+ sequential HTTP calls | Slow dashboard load (~200ms+ per call) | 1-2 days |
| 3 | CRITICAL | Exe not rebuilt since Phase 3.5 work | All recent fixes not deployed | 0.5 day |
| 4 | CRITICAL | Hourly email still blank in runtime | Core feature broken for real user | 1-2 days |
| 5 | IMPORTANT | Settings page is empty | Admin has no way to configure anything | 3-5 days |
| 6 | IMPORTANT | No database migration system | Schema changes require manual steps | 2-3 days |
| 7 | IMPORTANT | Test suite fragmentation | No confidence in releases | 2-3 days |
| 8 | IMPORTANT | Admin gateway port confusion (3000 vs 58393) | Dev/prod mismatch | 0.5 day |
| 9 | PERFORMANCE | Tab server uses sync http.server | Thread per request, blocks on I/O | 3-5 days |
| 10 | PERFORMANCE | No classification caching in tab server | Same URL re-classified on every visit | 1-2 days |
| 11 | NICE TO HAVE | No auto-update mechanism | Manual deployment only | 1-2 weeks |
| 12 | NICE TO HAVE | 442 MB exe size | Large download, slow startup | 1-2 days |

---

## 1. CRITICAL Issues

### ~~1.1 Auth Provider Login Bug~~ — FALSE POSITIVE (verified Feb 21)

**File**: `admin_ui/src/auth/AuthProvider.tsx`  
**Status**: The actual file already has `setUser(me)` on line 75. The initial review (via subagent) reported `setUser(user)` but this was incorrect. No fix needed.

---

### 1.2 Dashboard Aggregation Makes 12+ Sequential HTTP Calls

**File**: `focus_guard/core/admin_gateway/services/dashboard_service.py`

The `get_dashboard()` method makes these calls **sequentially** (each blocks until the previous completes):
1. `/api/health`
2. `/api/distraction/budget`
3. `/api/distraction/sites`
4. `/api/override/stats`
5. `/api/override/log`
6. `/api/enforcement_mode`
7. `/api/blocked/sites`
8. `/api/saved_links/stats`
9. `/api/saved_links`
10. `/api/tabs`
11. `/api/activity/stats`
12. `/api/activity/logs`

Each call goes through `urllib.request.urlopen` with a 5-second timeout. On a good day this is 200-600ms total. On a slow day with one timeout, it's 5+ seconds.

**Fix options (pick one)**:
- **Option A (Quick)**: Use `concurrent.futures.ThreadPoolExecutor` to make all 12 calls in parallel. ~3x-5x speedup for free.
- **Option B (Better)**: Create a single `/api/dashboard_snapshot` endpoint on the tab server that gathers all data server-side in one call. Eliminates HTTP overhead entirely.
- **Option C (Best long-term)**: Add a server-sent events (SSE) or WebSocket endpoint that streams dashboard updates. Frontend subscribes once and gets pushed updates.

**Recommended**: Option A immediately (0.5 day), Option B soon after (1 day).

---

### 1.3 Exe Not Rebuilt Since Phase 3.5

Many critical fixes from Feb 21 sessions (BUG-006, BUG-007, BUG-008, BUG-009, BUG-010, BUG-014, BUG-016 plus classifier trust hardening and admin console improvements) are only in source code. The running `FocusGuard.exe` doesn't have them.

**Fix**: Rebuild immediately:
```powershell
cd admin_ui && npm run build
cd .. && python -m PyInstaller --clean deployment/application/windows/specs/focusguard_unified.spec
```
Then verify with the packaged smoke suite.

---

### 1.4 Hourly Email Report Still Blank

BUG-007 has been "fixed" multiple times but the user still receives blank emails. The root causes identified:
- DB path resolution picks wrong database
- `_get_period_stats` query doesn't match sessions in the report window
- Fallback from visible windows doesn't trigger correctly

This is the single most user-visible bug — the parent sees empty emails every hour.

**Fix**: This needs end-to-end debugging in the actual runtime:
1. Add diagnostic fields to the email body itself (DB path used, query executed, rows found)
2. Rebuild exe with diagnostics
3. Wait for next hourly email and inspect
4. Fix root cause based on actual runtime evidence
5. Remove diagnostics, rebuild

---

## 2. IMPORTANT Issues

### 2.1 Settings Page is Empty

The Settings page says "P3-04 shell route placeholder." The parent has **zero configuration ability** from the admin UI. Everything must be done via the first-run wizard or by editing JSON files.

**What needs to be wired** (in priority order):
1. Enforcement mode toggle (endpoint exists)
2. Budget configuration (endpoints exist)
3. Domain management (endpoints exist)
4. Email configuration (needs new endpoint)
5. Password change (needs new endpoint)
6. Export data

**Effort**: 3-5 days (most endpoints already exist)

---

### 2.2 No Database Migration System

The application uses SQLite databases with schemas created implicitly in code. There's no migration system, no schema versioning, and no way to upgrade a database in place.

Current databases:
- `usage.db` — activity sessions, usage tracking
- Audit log (SQLite via AuditLogger)
- Activity log (SQLite via ActivityLogger)
- Search log (SQLite via SearchLogger)
- Saved links (SQLite via SavedLinksStore)
- Domain usage (JSON file)
- Master budget (JSON file)

**Risks**:
- Adding a column to any table requires manual migration or data loss
- No way to know what schema version a database is at
- Testing with real databases is fragile

**Fix**: Introduce `alembic` (for SQLAlchemy) or a simpler custom migration system:
- Version table in each database
- Migration scripts that run on startup
- Rollback capability

**Effort**: 2-3 days

---

### 2.3 Test Suite Fragmentation

Tests are scattered across:
- `focus_guard/tests/` — main test directory (pytest)
- `focus_guard/core/browser_v2/tab_server/tests/` — classification integration tests
- `scripts/test_section8_mitigations.py` — security tests (standalone script, not pytest)
- `scripts/run_all_tests.py` — supposed to run everything but unclear if it works
- `admin_ui/` — Vitest unit + MSW integration + Playwright E2E
- Various `scripts/testing/` files — ad hoc test scripts

**Problems**:
- No single command to run all tests
- Security tests aren't in pytest format
- Some tests import from wrong locations
- Coverage reporting is fragmented

**Fix**: Consolidate:
1. Move all Python tests under `focus_guard/tests/` with proper pytest structure
2. Convert `test_section8_mitigations.py` to pytest format
3. Create a `Makefile` or `scripts/test_all.py` that runs backend + frontend + E2E in order
4. Add CI configuration (GitHub Actions) for automated testing

**Effort**: 2-3 days

---

### 2.4 Admin Gateway Port Confusion

The `AdminGatewayConfig` defaults to port 3000, but the runtime startup (`main.py`) starts it on port 58393. The packaged lane uses 58393. Some test fixtures use 3000. The `allowed_origins` tuple includes `localhost:3000` and `localhost:5173` but not `localhost:58393`.

This leads to:
- CORS issues when testing locally
- Confusion about which port to use
- Stale port references in documentation

**Fix**: 
1. Change `AdminGatewayConfig.port` default to 58393
2. Add `http://127.0.0.1:58393` and `http://localhost:58393` to `allowed_origins`
3. Grep the codebase for `:3000` and update stale references
4. Ensure all docs and scripts use 58393

**Effort**: 0.5 day

---

### 2.5 Configuration Sprawl

Configuration is spread across too many files and formats:

| Config | Format | Location | Runtime? |
|--------|--------|----------|----------|
| `deployment_config.json` | JSON | `C:\ProgramData\FocusGuard\` | Yes |
| `domain_config.json` | JSON | `C:\ProgramData\FocusGuard\` | Yes |
| `api_token.json` | JSON | `C:\ProgramData\FocusGuard\` | Yes |
| `app_config.json` | JSON | `config/` in repo | Yes (bundled) |
| `browser_config.json` | JSON | `config/` in repo | Unclear |
| `classification_rules.json` | JSON | `config/` in repo | Unclear |
| `focus_guard_config.json` | JSON | `config/` in repo | Unclear |
| `AdminGatewayConfig` | Python dataclass | In-memory | Env vars |
| `DeploymentConfig` | Python dataclass + JSON | `C:\ProgramData\FocusGuard\` | Yes |

Plus, `constants.py` and `loader.py` still have hardcoded fallback values that sometimes disagree with `domain_config.json`.

**Fix**: Consolidate into a clear hierarchy:
1. `deployment_config.json` — master config (email, enforcement, monitoring, security)
2. `domain_config.json` — domain rules (categories, budgets, whitelists)
3. `api_token.json` — auth tokens (separate for security)
4. Remove or archive unused config files from `config/`
5. Remove hardcoded fallbacks from `constants.py` and `loader.py` (DomainConfigManager is the source of truth)

**Effort**: 1-2 days

---

### 2.6 Missing Error Monitoring & Crash Reporting

When `FocusGuard.exe` encounters an error on the user's machine, the only evidence is in `C:\ProgramData\FocusGuard\logs\`. There's no:
- Crash reporting to the developer
- Error aggregation
- Alerting when critical components fail
- Health dashboard for the server-side

For a parental monitoring tool, silent failures are the worst possible outcome.

**Fix**:
1. Add a `/api/diagnostics` endpoint that returns component health (tab server, coordinator, email reporter, security monitors)
2. Add the admin gateway's `/admin/api/v1/meta` readiness data to the dashboard permanently
3. Log errors with structured format including component, severity, and stack trace
4. Consider a simple error beacon that sends anonymized crash data to a server (opt-in)

**Effort**: 2-3 days

---

### 2.7 Browser Extension ↔ Server Version Mismatch Risk

The browser extension (published to Chrome/Edge stores) and the tab server (bundled in the exe) can be at different versions. There's no version negotiation or compatibility check.

If the extension expects an API field that the server doesn't provide (or vice versa), things silently break.

**Fix**:
1. Add `X-FocusGuard-Version` header to all extension requests
2. Tab server checks version and returns a warning/error if incompatible
3. Extension shows "Update required" banner if server reports incompatibility
4. Add version to `/api/health` response

**Effort**: 1 day

---

## 3. PERFORMANCE Issues

### 3.1 Tab Server Uses Synchronous `http.server`

The tab server (`server.py`) uses Python's `http.server.BaseHTTPRequestHandler` with `ThreadingHTTPServer`. This means:
- One thread per request
- Synchronous I/O everywhere
- No connection keep-alive
- No WebSocket support
- GIL contention under load

For a local application with 2 browsers making requests every 5 seconds, this works. But it's the wrong foundation for:
- Real-time dashboard updates
- Handling many concurrent tabs
- Classification pipeline with LLM calls (blocks the thread)

**Fix options**:
- **Option A (Moderate)**: Keep the current architecture but move LLM classification to a thread pool
- **Option B (Better)**: Migrate to `aiohttp` server (already a dependency). Tab server becomes async, LLM calls use `asyncio.to_thread()`, and WebSocket support becomes trivial
- **Option C (Best)**: Merge tab server and admin gateway into a single `FastAPI` application with async endpoints

**Recommended**: Option A immediately (1 day), Option B when planning the next major version (3-5 days).

---

### 3.2 No Classification Caching in Tab Server

Every time the extension sends a tab update, the classification pipeline runs from scratch — even if the same URL was classified 30 seconds ago. The extension has a 30-second blocking cache, but the server-side has no cache.

For LLM-based classifiers, each call takes 500ms-2s and costs money (OpenAI API).

**Fix**: Add a server-side classification cache:
- Key: normalized URL + content hash
- TTL: 24 hours for rule-based, 1 hour for LLM
- Storage: in-memory `dict` with LRU eviction (or SQLite for persistence)
- Invalidation: on domain config change

**Effort**: 1-2 days

---

### 3.3 Extension Polls Every 5 Seconds Regardless

The extension sends full tab snapshots every 5 seconds via `setInterval`. This is 720 requests per hour per browser, most of which contain identical data.

**Fix**:
- Only send tab data when something changes (tab created, closed, URL changed, activated)
- Use `chrome.tabs.onUpdated`, `chrome.tabs.onCreated`, `chrome.tabs.onRemoved`, `chrome.tabs.onActivated` events instead of polling
- Keep a heartbeat at 30-second interval for connection monitoring
- This reduces traffic by ~90%

**Effort**: 1 day (extension code change + store submission)

---

### 3.4 SQLite Databases May Lack Indexes

Multiple SQLite databases are used (usage, audit, activity, search, saved links) but I couldn't find evidence of index creation for the query patterns used. Common queries like "get sessions in time range" or "get blocked activities for today" would benefit from indexes on timestamp columns.

**Fix**: Audit each database's create table and add indexes:
- `usage_sessions`: index on `(start_time, end_time)`
- Activity logs: index on `(timestamp, blocked)`
- Search logs: index on `(timestamp)`
- Saved links: index on `(saved_at, viewed)`

**Effort**: 0.5 day

---

## 4. NICE TO HAVE Improvements

### 4.1 Reduce Exe Size (442 MB → target ~150 MB)

The exe is 442 MB because PyInstaller bundles the entire Python standard library plus large dependencies. Key size contributors:
- PyQt5: ~80 MB
- aiohttp: ~20 MB
- All transitive dependencies

**Fix**:
1. Audit the `excludes` list in the spec file — make sure large packages not needed at runtime are excluded
2. Use UPX compression (can reduce size by 30-50%)
3. Consider switching from `onefile` to `onedir` mode (faster startup, can exclude unused DLLs)
4. Strip debug symbols from bundled binaries

**Effort**: 1-2 days

---

### 4.2 Auto-Update Mechanism

Currently, updating FocusGuard requires manually downloading and replacing the exe. For a parental monitoring tool, this is a significant gap — parents need updates to be automatic and tamper-resistant.

**Fix**: Implement a simple auto-update system:
1. On startup, check a version endpoint (hosted JSON file or GitHub releases)
2. If new version available, download in background
3. On next restart, apply update
4. Code-sign the exe to prevent tampering

**Effort**: 1-2 weeks

---

### 4.3 WebSocket Real-Time Updates

Currently all frontend data uses polling (10-30 second intervals). This means:
- Stale data shown between polls
- Unnecessary network traffic when nothing changes
- No instant feedback when blocking events happen

**Fix**: Add a WebSocket endpoint to the admin gateway:
- Subscribe to events: blocking, override, tab update, budget change
- Frontend receives pushes and updates UI in real-time
- Fall back to polling if WebSocket disconnects

**Effort**: 3-4 days

---

### 4.4 Structured Logging

Currently, logging uses Python's `logging` module with basic string formatting. Log messages are inconsistent and hard to parse programmatically.

**Fix**: Adopt structured logging:
- Use `structlog` or `python-json-logger`
- Every log entry has: `timestamp`, `level`, `component`, `event`, `details`
- Makes log analysis, filtering, and the proposed "agentic log review" feature much easier

**Effort**: 2-3 days

---

### 4.5 CI/CD Pipeline

There's no automated build or test pipeline. Every build is manual.

**Fix**: Set up GitHub Actions:
- On push: run all Python tests, frontend tests
- On tag: build exe, run packaged smoke tests, create release
- Lint checks (black, isort, mypy, eslint)

**Effort**: 1-2 days

---

### 4.6 Classification Feedback Loop

When the classifier makes a mistake (e.g., blocking Macbeth on folger.edu), there's no way for the user or parent to correct it. The correction doesn't feed back into the system.

**Fix**: Add a classification feedback endpoint and UI:
- On the blocked page: "This is actually educational" button
- In the admin console: "Override classification for this URL"
- Store feedback in a database
- Use feedback to retrain rules or adjust confidence thresholds
- Weekly digest of misclassifications for developer review

**Effort**: 3-5 days

---

## 5. Technical Debt Items

### 5.1 View Files Named "Placeholder"
All view files are named `*Placeholder.tsx`. These were scaffolds that became permanent. Rename:
- `DashboardPlaceholder.tsx` → `Dashboard.tsx`
- `ExceptionsPlaceholder.tsx` → `Overrides.tsx`
- `DevicesPlaceholder.tsx` → `Devices.tsx`
- `SettingsPlaceholder.tsx` → `Settings.tsx`
- `SavedLinksPlaceholder.tsx` → `SavedLinks.tsx`

### 5.2 Legacy v1 Browser Integration Code
The `focus_guard/core/browser/` directory has legacy v1 code that's mostly superseded by `browser_v2/`. Several files have been deleted in git but the remaining ones (`domain_blocking.py`, `integration.py`, `interfaces.py`, `manager.py`) have `try/except` import fallbacks.

**Fix**: Complete the migration. Remove legacy adapter code, update all imports to `browser_v2`.

### 5.3 `mvp_main.py` is Deprecated but Still Present
`focus_guard/core/mvp_main.py` has a DEPRECATED header but is still importable and could confuse new developers.

**Fix**: Move to `UNUSED/` or delete.

### 5.4 Duplicate `connectNativeHost` in background.js
The function `connectNativeHost()` is defined twice in `background.js` (lines ~97 and ~135). The second definition overwrites the first.

---

## 6. Prioritized Execution Roadmap

### Sprint 1: Stabilize (1-2 days)
1. ~~Fix AuthProvider login bug~~ — FALSE POSITIVE (verified correct Feb 21)
2. ✅ Fix admin gateway port default — 7 files updated (Feb 21)
3. Rebuild exe with all Phase 3.5 fixes (0.5 day) — CRITICAL

### Sprint 2: Make Dashboard Useful (3-5 days)
4. ✅ Parallelize dashboard aggregation calls — ThreadPoolExecutor(6), 3-5x speedup (Feb 21)
5. Dashboard hero summary redesign (2-3 days) — IMPORTANT
6. Date/time range selector (1-2 days) — IMPORTANT

### Sprint 3: Enable Configuration (3-5 days)
7. Wire Settings page with budget controls (2 days) — IMPORTANT
8. Wire Settings page with domain management (2 days) — IMPORTANT
9. Wire enforcement mode toggle (0.5 day) — IMPORTANT

### Sprint 4: Reliability (2-3 days)
10. Fix hourly email with runtime diagnostics (1-2 days) — CRITICAL
11. Add classification cache (1 day) — PERFORMANCE
12. Consolidate test suite (1-2 days) — IMPORTANT

### Sprint 5: Polish (2-3 days)
13. ✅ Rename views from Placeholder (Feb 21) — 5 files renamed + router + Settings content updated
14. Remove legacy browser v1 code — DEFERRED (30+ files cross-reference; needs migration plan)
15. ✅ Add SQLite compound indexes (Feb 21) — activity_logger + saved_links
16. Extension event-driven updates (1 day) — PERFORMANCE

### Also completed (Feb 21):
- ✅ Removed duplicate `connectNativeHost()` in extension background.js
- ✅ Admin UI Vite production build verified clean
- ✅ All 51 backend + 14 frontend tests passing

### Future Sprints
17. Activity timeline page
18. WebSocket real-time updates
19. Auto-update mechanism
20. Classification feedback loop
21. Structured logging
22. CI/CD pipeline
23. Exe size optimization

---

## 7. Architecture Vision

If I were designing FocusGuard from scratch today with the same requirements, the key architectural changes would be:

1. **Single async server** (FastAPI) instead of two separate servers (http.server + FastAPI). The tab server API and admin gateway would be unified, reducing complexity and eliminating the proxy layer.

2. **Event-driven architecture** with an event bus. All components emit events (classification, blocking, override, activity) that other components subscribe to. This enables real-time dashboard, WebSocket pushes, and flexible reporting.

3. **SQLAlchemy + Alembic** for all persistent storage instead of raw SQLite. Gives us migrations, type safety, and easier testing.

4. **React admin UI as a proper SPA** with a design system (shadcn/ui), a state management library (Zustand), and real-time updates via SSE/WebSocket.

5. **Extension communicates via WebSocket** instead of polling HTTP. Enables instant blocking decisions and real-time tab monitoring.

However, the current architecture works and has extensive test coverage. A pragmatic approach is to **improve incrementally** rather than rewrite — fix the critical issues first, then evolve toward the better architecture over time.
