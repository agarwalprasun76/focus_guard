# FocusGuard — Codebase Map & File Reference

**Created**: February 21, 2026
**Purpose**: Quick-reference map of every important file and folder in the project.

---

## Top-Level Structure

```
focus_guard/                    # Root of the repository
├── focus_guard/                # Main Python source package
├── admin_ui/                   # React/TypeScript admin frontend
├── config/                     # Configuration templates
├── deployment/                 # Build specs, installers, deployment tools
├── docs/                       # Documentation
├── scripts/                    # Dev/test/troubleshooting scripts
├── data/                       # Simulation reports and test data
├── UNUSED/                     # Archived/deprecated code
├── pyproject.toml              # Python project config, dependencies
├── launch_focusguard.py        # PyInstaller entry point (bootstraps sys.path)
└── README.md                   # Project README
```

---

## Core Python Package: `focus_guard/`

### Entry Points

| File | Purpose |
|------|---------|
| `focus_guard/main.py` | **Primary entry point** — starts tray + tab server + admin gateway + coordinator + email reporter |
| `focus_guard/cli/main.py` | CLI interface (Click-based) |
| `launch_focusguard.py` | PyInstaller bootstrap — sets up sys.path for frozen exe, calls `focus_guard.main.main()` |

### Activity Monitoring: `focus_guard/core/activity/`

| File | Purpose |
|------|---------|
| `monitor.py` | Cross-platform activity monitor — active windows, tabs, idle state |
| `usage_tracker.py` | Tracks per-app and per-domain usage time |
| `enhanced_logger.py` | Enhanced activity logging with structured events |
| `browser/comprehensive_activity_system.py` | Full browser activity tracking system |
| `browser/extension_integration.py` | Bridge between activity monitor and browser extension data |
| `platform/` | Platform-specific implementations (Windows win32 APIs) |

### Admin Gateway: `focus_guard/core/admin_gateway/`

| File | Purpose |
|------|---------|
| `app.py` | FastAPI app factory — CORS, SPA serving, error handlers |
| `config.py` | Gateway config (origins, ports, auth settings) |
| `dependencies.py` | FastAPI dependency injection (auth guards) |
| `error_handling.py` | Structured error envelope translation |
| `routers/auth.py` | Login/refresh/logout/me endpoints |
| `routers/devices.py` | Device status + enforcement mode endpoints |
| `routers/exceptions.py` | Override/exception create/list/revoke endpoints |
| `routers/meta.py` | Capabilities, readiness, versioning endpoint |
| `services/dashboard_service.py` | Aggregates data from tab server for dashboard |
| `services/devices_service.py` | Single-device status payload |
| `services/tab_server_client.py` | HTTP client for tab server API (upstream proxy) |

### Blocking: `focus_guard/core/blocking/`

| File | Purpose |
|------|---------|
| `engine.py` | `PolicyEngine` — evaluates blocking policies against domains |
| `policies/base.py` | Abstract `BlockingPolicy` interface |
| `policies/domain.py` | Domain-based blocking policy |
| `policies/time_based.py` | Time-based blocking policy |

### Browser Integration (Legacy v1): `focus_guard/core/browser/`

| File | Purpose |
|------|---------|
| `extension/domain_blocking.py` | Domain blocking logic |
| `extension/integration.py` | Extension integration adapter |
| `extension/interfaces.py` | Interface definitions |
| `extension/manager.py` | Extension management |
| `extension/webextension_mv3/` | **Browser extension source code** |
| `extension/webextension_mv3/manifest.json` | Extension manifest (MV3) |
| `extension/webextension_mv3/background.js` | **Service worker** — blocking logic, tab tracking, API communication |
| `extension/webextension_mv3/blocked.html` | Blocked page UI (personalized) |
| `extension/webextension_mv3/blocked.js` | Blocked page JS (save for later, budget context) |
| `extension/webextension_mv3/popup.html` | Extension popup UI |
| `extension/webextension_mv3/popup.js` | Extension popup JS |
| `extension/webextension_mv3/icons/` | Extension icons (16, 32, 48, 128 px) |
| `integration/browser_integration.py` | Browser integration controller |
| `integration/tab_tracker.py` | Tab tracking logic |

### Browser Integration (v2): `focus_guard/core/browser_v2/`

**This is the active/primary browser integration stack.**

| File | Purpose |
|------|---------|
| `tab_server/server.py` | **Main HTTP server** — all REST API endpoints for extension communication |
| `tab_server/runner.py` | `TabServerRunner` — lifecycle, health checks, security monitors |
| `tab_server/classification_service.py` | Classification integration for tab server |
| `tab_server/classification_blocker.py` | Classification-based blocking decisions |
| `tab_server/override_manager.py` | Override (temporary access) management |
| `tab_server/saved_links.py` | SQLite-backed saved links store (save blocked URLs for later) |
| `tab_server/analytics_service.py` | Analytics aggregation (daily/weekly/heatmap) |
| `installer/core_installer.py` | Extension installer orchestration |
| `installer/strategies.py` | Installation strategies (dev unpacked, store) |
| `docs/NORTH_STAR_PLAN.md` | Browser v2 architecture plan |

### Classification: `focus_guard/core/classification/`

| File | Purpose |
|------|---------|
| `classifiers/domain_category_classifier.py` | Main domain category classifier |
| `classifiers/domains/__init__.py` | Domain classifier registry |
| `classifiers/domains/base.py` | Base classes for domain classifiers |
| `classifiers/domains/youtube_llm.py` | YouTube-specific LLM classifier |
| `classifiers/domains/google.py` | Google search classifier |
| `classifiers/domains/google_llm.py` | Google LLM classifier |
| `classifiers/domains/reddit.py` | Reddit classifier |
| `classifiers/domains/twitter.py` | Twitter/X classifier |
| `classifiers/generic/url_composite_classifier.py` | Generic URL composite classifier |

### Configuration: `focus_guard/core/config/`

| File | Purpose |
|------|---------|
| `loader.py` | Legacy configuration loader (fallback defaults) |

### Coordinator: `focus_guard/core/coordinator/`

| File | Purpose |
|------|---------|
| `components/activity.py` | Activity component — window tracking via coordinator |
| `components/browser.py` | Browser component — tab server integration via coordinator |

### Domain Management: `focus_guard/core/domain/`

| File | Purpose |
|------|---------|
| `constants.py` | Domain categories, whitelists (reads from DomainConfigManager) |
| `domain_config_manager.py` | **Singleton** — single source of truth for all domain configuration |

### Platform Utilities: `focus_guard/core/platform_utils/`

| File | Purpose |
|------|---------|
| `windows/windows_config.py` | Windows-specific configuration and defaults |

### Other Core Files

| File | Purpose |
|------|---------|
| `core/mvp_main.py` | **DEPRECATED** — old MVP main entry point, superseded by `focus_guard/main.py` |
| `core/api/server.py` | Core API server (legacy) |
| `core/extension_constants.py` | Extension-related constants |
| `core/tab_server_endpoint.py` | Tab server endpoint constants |
| `core/utils/metadata_fetcher.py` | URL metadata fetching utility |

### GUI: `focus_guard/gui/`

| File | Purpose |
|------|---------|
| `first_run_wizard.py` | PyQt5 7-page setup wizard (Welcome → Email → Extension → Time Limits → Personalization → Domain Manager → Finish) |

### Deployment: `focus_guard/deployment/`

| File | Purpose |
|------|---------|
| `email_reporter.py` | Hourly/daily email report sender |
| `config.py` | `DeploymentConfig` model (enforcement mode, email, popup config) |
| `runtime_startup.py` | Production runtime orchestrator (graceful startup) |
| `service.py` | Windows service wrapper |
| `main_service.py` | CLI for service management + diagnostics |
| `installer.py` | Application installer logic |

### Assets: `focus_guard/assets/`

| File | Purpose |
|------|---------|
| `icon.ico` | Application icon (system tray, exe) |

---

## Admin UI: `admin_ui/`

React/TypeScript SPA served at `http://127.0.0.1:58393/admin`.

| File | Purpose |
|------|---------|
| `src/main.tsx` | App entry point (React + Router + TanStack Query) |
| `src/router.tsx` | Route definitions (/, /exceptions, /devices, /settings, /saved-links) |
| `src/api/client.ts` | API client with token interceptor |
| `src/api/auth.ts` | Auth API (login/refresh/logout) |
| `src/api/dashboard.ts` | Dashboard data fetching |
| `src/api/exceptions.ts` | Exception/override CRUD |
| `src/api/devices.ts` | Device status API |
| `src/api/meta.ts` | Meta/capabilities API |
| `src/auth/AuthProvider.tsx` | Auth session context provider |
| `src/auth/guards.tsx` | Route guards (RequireAuth, RequireGuest) |
| `src/ui/AppLayout.tsx` | App shell (sidebar desktop, bottom tabs mobile) |
| `src/ui/QueryStates.tsx` | Shared loading/error/empty/offline UI states |
| `src/views/DashboardPlaceholder.tsx` | Dashboard with widgets (status, budget, friction, overrides, blocked sites, activity, saved links) |
| `src/views/LoginPage.tsx` | Admin login page |
| `src/views/ExceptionsPlaceholder.tsx` | Override management (create, list, revoke) |
| `src/views/DevicesPlaceholder.tsx` | Device status display |
| `src/views/SettingsPlaceholder.tsx` | Settings page (MVP wiring needed) |
| `src/views/SavedLinksPlaceholder.tsx` | Saved links display |
| `vite.config.ts` | Vite config (base: /admin/) |
| `playwright.packaged.config.ts` | Playwright config for packaged smoke tests |
| `e2e/critical-smoke.spec.ts` | Critical E2E smoke tests |
| `e2e/packaged-runtime-smoke.spec.ts` | Packaged runtime smoke tests |

---

## Configuration: `config/`

| File | Purpose |
|------|---------|
| `app_config.json` | Application config (SMTP defaults, distraction categories) |
| `blocking.json` | Blocking rules |
| `browser_config.json` | Browser-specific configuration |
| `classification_rules.json` | Classification rule definitions |
| `focus_guard_config.json` | Main focus guard config |
| `focus_guard_config_template.json` | Config template |
| `credentials.json` | **SENSITIVE** — credential storage |
| `service-account.json` | **SENSITIVE** — service account credentials |
| `task_profiles.json` | Task profile definitions |
| `users/default.json` | Default user configuration |

---

## Deployment: `deployment/`

| File | Purpose |
|------|---------|
| `application/windows/specs/focusguard_unified.spec` | **PyInstaller spec** — builds FocusGuard.exe |
| `application/windows/scripts/build_exe.py` | Build script |
| `extension/` | Extension deployment scripts (CRX, enterprise policies, developer) |
| `installer/` | Windows installer scripts (BAT, PowerShell) |
| `tools/classification/debug/` | Classification debugging tools |

---

## Tests: `focus_guard/tests/`

| Directory | Purpose |
|-----------|---------|
| `core/admin_gateway/` | Admin gateway backend tests (~45+ tests) |
| `core/activity/` | Activity monitoring tests |
| `core/alert/` | Alert system tests |
| `core/classification/` | Classification tests |
| `core/blocking/` | Blocking engine tests |
| `core/test_reporting_and_override_regressions.py` | Regression tests for reporting + overrides |
| `browser_v2/` | Browser v2 tests |
| `integration/classification/` | Integration tests for classification |

---

## Scripts: `scripts/`

| Script | Purpose |
|--------|---------|
| `dev/start_tab_server.py` | Start tab server for development |
| `dev/run_packaged_lane.py` | Deterministic packaged-lane build + verify workflow |
| `dev/verify_packaged_admin_runtime.py` | HTTP verification of packaged runtime |
| `dev/export_admin_gateway_openapi.py` | Export OpenAPI schema from admin gateway |
| `dev/create_all_icons.py` | Generate all icon sizes |
| `admin_gateway_smoke.py` | Admin gateway manual smoke test |
| `test_section8_mitigations.py` | Run Section 8 security mitigation tests (132 tests) |
| `run_all_tests.py` | Run full test suite |
| `integration_tests/distraction_simulation_harness.py` | Automated distraction simulation |
| `integration_tests/run_distraction_simulation_nightly.py` | Nightly simulation runner |

---

## Key Design Patterns

1. **Singleton pattern**: `DomainConfigManager`, `APIAuthManager`, `TabStorage`
2. **Strategy pattern**: Classification (rule-based vs LLM), installation strategies (dev vs store)
3. **Policy engine**: `PolicyEngine` evaluates multiple blocking policies in priority order
4. **Proxy/gateway**: Admin gateway proxies tab server API for frontend consumption
5. **Thread-based concurrency**: Tab server, coordinator, email reporter run as daemon threads
6. **Event-driven**: Audit events, heartbeat monitoring, config change callbacks
7. **Defense in depth**: Extension blocking + hosts file + declarativeNetRequest rules + VPN detection
