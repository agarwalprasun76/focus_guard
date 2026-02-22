# FocusGuard — Development Workflows & Recipes

**Created**: February 21, 2026
**Purpose**: Common development tasks, debugging patterns, and step-by-step workflows.

---

## 1. Building the Executable

### Prerequisites
```powershell
# Ensure admin_ui is built first (SPA gets bundled into exe)
cd admin_ui
npm install
npm run build
cd ..

# Ensure PyInstaller is installed
pip install pyinstaller
```

### Build Command
```powershell
python -m PyInstaller --clean deployment/application/windows/specs/focusguard_unified.spec
```

### Output
- `dist/FocusGuard.exe` (~442 MB)

### Post-Build Verification
```powershell
# Start the exe
Start-Process dist/FocusGuard.exe

# Verify tab server
Invoke-RestMethod http://127.0.0.1:58392/api/health

# Verify admin gateway
Invoke-RestMethod http://127.0.0.1:58393/admin/health

# Full packaged verification
python scripts/dev/verify_packaged_admin_runtime.py --base-url http://127.0.0.1:58393
```

---

## 2. Running from Source (Development)

### Option A: Full Application (tray + all services)
```powershell
python -m focus_guard.main
```

### Option B: Individual Components

```powershell
# Tab server only (port 58392)
python scripts/dev/start_tab_server.py

# Admin gateway only (port 58393, needs tab server running)
$env:FOCUS_GUARD_TAB_SERVER_BASE_URL = "http://127.0.0.1:58392"
python -m uvicorn focus_guard.core.admin_gateway.app:create_app --factory --host 127.0.0.1 --port 58393

# Admin UI dev server (hot reload, port 5173)
cd admin_ui
npm run dev
```

### Environment Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `FOCUS_GUARD_TAB_SERVER_BASE_URL` | `http://127.0.0.1:58392` | Tab server URL for admin gateway |
| `FOCUS_GUARD_STRICT_RUNTIME_STARTUP` | `false` | Fail if runtime deps can't start |
| `FOCUS_GUARD_START_ADMIN_GATEWAY` | `true` | Whether to start admin gateway |
| `FOCUS_GUARD_ADMIN_GATEWAY_HOST` | `127.0.0.1` | Admin gateway bind host |
| `FOCUS_GUARD_ADMIN_GATEWAY_PORT` | `58393` | Admin gateway bind port |

---

## 3. Running Tests

### Backend Tests
```powershell
# Admin gateway (the most comprehensive backend test suite)
python -m pytest focus_guard/tests/core/admin_gateway/ -q

# Security mitigations (132 tests)
python scripts/test_section8_mitigations.py

# Reporting and override regressions
python -m pytest focus_guard/tests/core/test_reporting_and_override_regressions.py -q

# Classification integration
python -m pytest focus_guard/core/browser_v2/tab_server/tests/test_classification_integration.py -q

# Activity tests
python -m pytest focus_guard/tests/core/activity/ -q

# All backend tests (may have some fragmentation)
python scripts/run_all_tests.py
```

### Frontend Tests
```powershell
cd admin_ui

# Unit tests (Vitest)
npm run test

# Integration tests (MSW-based API contract tests)
npm run test:integration

# E2E tests (Playwright, needs admin gateway running)
npm run test:e2e

# Packaged smoke tests (needs running exe)
$env:PACKAGED_ADMIN_BASE_URL = "http://127.0.0.1:58393"
$env:PACKAGED_ADMIN_USERNAME = "admin"
$env:PACKAGED_ADMIN_PASSWORD = "<your-admin-password>"
npm run test:e2e:packaged:smoke
```

### Simulation Tests
```powershell
# Dry run (no real server needed)
python scripts/integration_tests/distraction_simulation_harness.py --dry-run --scenario all

# With real server
python scripts/integration_tests/distraction_simulation_harness.py --scenario all --base-url http://127.0.0.1:58392
```

---

## 4. Common Debugging Workflows

### A. Investigating a Classification Bug

1. **Reproduce**: Visit the URL in Chrome/Edge with extension active
2. **Check tab server directly**:
   ```powershell
   # Check what the server says about a URL
   $body = @{ url = "https://folger.edu/explore/macbeth"; title = "Macbeth - Folger" } | ConvertTo-Json
   Invoke-RestMethod -Uri "http://127.0.0.1:58392/api/should_block" -Method POST -Body $body -ContentType "application/json"
   ```
3. **Check classification details**:
   - Look at `classification_service.py` for the classify() call chain
   - Check if domain is in `domain_config.json` (pre-classification shortcut)
   - Check domain-specific classifier (if any) vs generic fallback
4. **Check domain config**:
   ```powershell
   Invoke-RestMethod http://127.0.0.1:58392/api/domains/overview
   ```
5. **Key files to inspect**:
   - `browser_v2/tab_server/classification_service.py`
   - `browser_v2/tab_server/classification_blocker.py`
   - `classification/classifiers/domains/<specific>.py`
   - `classification/classifiers/generic/url_composite_classifier.py`

### B. Investigating an Admin UI Bug

1. **Check API response directly**:
   ```powershell
   # Get auth token
   $loginBody = @{ username = "admin"; password = "<password>" } | ConvertTo-Json
   $token = (Invoke-RestMethod -Uri "http://127.0.0.1:58393/admin/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json").access_token

   # Call API with token
   Invoke-RestMethod -Uri "http://127.0.0.1:58393/admin/api/v1/dashboard" -Headers @{ Authorization = "Bearer $token" }
   ```
2. **Check admin gateway service layer**: `core/admin_gateway/services/dashboard_service.py`
3. **Check tab server upstream**: The admin gateway proxies to tab server
4. **Frontend debugging**: Open browser DevTools at `http://127.0.0.1:58393/admin`

### C. Investigating Email Report Issues

1. **Check email config**: Look at `C:\ProgramData\FocusGuard\deployment_config.json`
2. **Check usage DB**: `C:\Users\<user>\AppData\Local\FocusGuard\usage.db`
3. **Check email reporter**: `focus_guard/deployment/email_reporter.py`
4. **Trigger manual send**:
   ```python
   from focus_guard.deployment.email_reporter import EmailReporter
   reporter = EmailReporter(config)
   reporter.send_hourly_report(start_time, end_time)
   ```

### D. Investigating Extension Issues

1. **Check extension console**: Go to `edge://extensions` or `chrome://extensions`, enable Developer Mode, click "Service Worker" to see background.js console
2. **Check tab server health**: `http://127.0.0.1:58392/api/health`
3. **Check connected browsers**: `http://127.0.0.1:58392/api/status`
4. **Check extension logs**: background.js logs to browser DevTools console

---

## 5. Adding a New Domain Classifier

1. Create a new file: `focus_guard/core/classification/classifiers/domains/<domain>.py`
2. Implement the classifier:
   ```python
   from .base import RuleBasedDomainClassifier  # or LLMBasedDomainClassifier

   class MyDomainClassifier(RuleBasedDomainClassifier):
       SUPPORTED_DOMAINS = ["example.com"]

       def classify(self, url, title, context=None):
           # Rule-based classification logic
           ...
   ```
3. Register in `focus_guard/core/classification/classifiers/domains/__init__.py`
4. Add test in `focus_guard/tests/core/classification/`

---

## 6. Adding a New API Endpoint

### Tab Server (extension-facing API)
1. Add handler method to `browser_v2/tab_server/server.py`:
   - GET: add to `_route_get()` mapping
   - POST: add to `_route_post()` mapping
2. Implement `_handle_<endpoint_name>()` method
3. If mutation: add to auth-gated list in `_require_auth()`

### Admin Gateway (admin UI-facing API)
1. Add route to appropriate router in `core/admin_gateway/routers/`
2. Add service method in `core/admin_gateway/services/`
3. Update TypeScript API client in `admin_ui/src/api/`
4. Add tests in `focus_guard/tests/core/admin_gateway/`

---

## 7. Modifying the Browser Extension

Extension files: `focus_guard/core/browser/extension/webextension_mv3/`

| File | Purpose |
|------|---------|
| `manifest.json` | Extension metadata, permissions, service worker registration |
| `background.js` | Service worker: blocking logic, tab tracking, API calls, declarativeNetRequest sync |
| `blocked.html` / `blocked.js` | Blocked page UI and logic |
| `popup.html` / `popup.js` | Extension popup (status display) |

After modifying:
1. Reload extension in `edge://extensions` or `chrome://extensions`
2. For store updates: increment version in `manifest.json`, submit to stores
3. `background.js` changes take effect after service worker restart

---

## 8. Key Configuration Files to Know

| File | Purpose | When to Edit |
|------|---------|-------------|
| `config/app_config.json` | SMTP defaults, distraction categories | Rarely (DomainConfigManager is primary) |
| `deployment_config.json` (runtime) | Enforcement mode, email, popup config | Via wizard/API, not direct edit |
| `domain_config.json` (runtime) | Domain categories, budgets, rules | Via API or DomainManagerPage |
| `admin_ui/vite.config.ts` | Admin UI build config (base: /admin/) | When changing admin UI serving path |
| `focusguard_unified.spec` | PyInstaller bundling config | When adding new modules or data files |
| `pyproject.toml` | Python dependencies and project metadata | When adding Python dependencies |
| `admin_ui/package.json` | Frontend dependencies | When adding frontend dependencies |

---

## 9. Document Cross-Reference

| Document | Location | Role |
|----------|----------|------|
| **This document** | `cursor/05_DEVELOPMENT_WORKFLOWS.md` | Development recipes |
| Project Overview | `cursor/01_PROJECT_OVERVIEW.md` | High-level orientation |
| Codebase Map | `cursor/02_CODEBASE_MAP.md` | File reference |
| Status & Bugs | `cursor/03_CURRENT_STATUS_AND_BUGS.md` | What's broken and what's next |
| Architecture | `cursor/04_ARCHITECTURE_DEEP_DIVE.md` | How components interact |
| Active Plan | `gpt_53_codex/PLAN_02202026_DEPLOYMENT_AND_MVP.md` | Current execution plan |
| Progress Tracker | `gpt_53_codex/PROGRESS_TRACKER_02202026.md` | Session-by-session progress |
| Bug Reports | `gpt_53_codex/BUGS_02212026.md` | User-reported bugs |
| opus_45 Plan | `opus_45/DEPLOYMENT_AND_MVP_PLAN_02062026.md` | Historical baseline + long-range roadmap |
| opus_45 Progress | `opus_45/PROGRESS_TRACKER.md` | Historical deployment tracking |
| Browser v2 Plan | `focus_guard/core/browser_v2/docs/NORTH_STAR_PLAN.md` | Browser integration architecture |
