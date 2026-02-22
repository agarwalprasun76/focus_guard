# Progress Tracker — PLAN_02202026_DEPLOYMENT_AND_MVP

**Plan Reference**: `PLAN_02202026_DEPLOYMENT_AND_MVP.md`  
**Created**: February 20, 2026  
**Last Updated**: February 21, 2026 (Session 4)

---

## Phase 1: Critical Bug Fixes & Rebuild (Days 1-2)

| ID | Task | Status | Date | Evidence / Notes |
|----|------|--------|------|-----------------|
| 1.1 | Fix tray icon not showing (BUG-001/AF-6) | ✅ DONE | 2026-02-20 | Added `sys._MEIPASS` path as first candidate in `_load_icon()`, diagnostic logging, improved fallback icon with "FG" text |
| 1.2 | Set enforcement password (`config_password_hash`) | ✅ DONE | 2026-02-20 | Added `PasswordPage` to first-run wizard with validation; wired into `get_config()` and settings dialog pre-fill |
| 1.3 | Update copyright to 2026 (BUG-005) | ✅ DONE | 2026-02-20 | Already 2026 in `main.py:577`; remaining `2025` refs are test data timestamps only |
| 1.4 | Rebuild FocusGuard.exe | 🔲 NOT STARTED | — | Depends on 1.1, 1.2, 1.3 |
| 1.5 | Smoke test rebuilt exe | 🔲 NOT STARTED | — | Depends on 1.4 |

### Phase 1 Exit Gate
- [ ] Rebuilt exe passes 12-point smoke checklist
- [ ] Tray icon visible
- [ ] Enforcement password active

---

## Phase 2: MVP Feature Completion (Days 2-4)

| ID | Task | Status | Date | Evidence / Notes |
|----|------|--------|------|-----------------|
| 2.1 | Blocked sites display on dashboard/popup (AF-5) | ✅ DONE | 2026-02-20 | Added `/api/blocked/sites` endpoint, wired into dashboard_service.py, added `BlockedSiteItem` type + UI section in DashboardPlaceholder.tsx |  
| 2.2 | Save blocked links module (AF-1) | ✅ DONE | 2026-02-20 | Created `saved_links.py` (SQLite store), 5 tab-server endpoints (GET list/stats, POST save/view/delete), "Save for Later" button+form on blocked.html/blocked.js |
| 2.3 | First-run wizard improvements (BUG-002, BUG-003) | ✅ DONE | 2026-02-20 | Added quick presets (Strict/Moderate/Relaxed) to TimeLimitsPage; PasswordPage already added in 1.2 |
| 2.4 | Blocked page UI improvement | ✅ DONE | 2026-02-20 | Added "Save for Later" button+form, saved links badge with unviewed count, dashboard test updated |

### Phase 2 Exit Gate
- [ ] Dashboard shows blocked sites and counts
- [ ] Blocked links can be saved and viewed later
- [ ] First-run wizard is clear and complete
- [ ] Blocked page is informative and well-designed

---

## Phase 3: Stability & Validation (Days 4-6)

| ID | Task | Status | Date | Evidence / Notes |
|----|------|--------|------|-----------------|
| 3.1 | Clean Windows VM validation | 🔲 NOT STARTED | — | — |
| 3.2 | 8-hour soak test | 🔲 NOT STARTED | — | — |
| 3.3 | Test suite organization | 🔲 NOT STARTED | — | — |
| 3.4 | L-002 revisit | 🔲 NOT STARTED | — | — |
| 3.5 | Non-admin startup behavior documentation | 🔲 NOT STARTED | — | — |
| 3.6 | Fail-open vs fail-closed user config | 🔲 NOT STARTED | — | — |
| 3.7 | Rebuild exe + distribution ZIP | 🔲 NOT STARTED | — | Depends on 3.1-3.6 |

### Phase 3 Exit Gate
- [ ] Clean VM validation passes
- [ ] 8-hour soak test passes
- [ ] All tests runnable from single command
- [ ] Distribution ZIP updated

---

## Phase 4: Polish & Release Prep (Days 6-8)

| ID | Task | Status | Date | Evidence / Notes |
|----|------|--------|------|-----------------|
| 4.1 | User feedback module (AF-2) | 🔲 NOT STARTED | — | — |
| 4.2 | Shadow Cycle 002 | 🔲 NOT STARTED | — | — |
| 4.3 | Tracker/governance cleanup | 🔲 NOT STARTED | — | — |
| 4.4 | Release notes v1.1 | 🔲 NOT STARTED | — | — |
| 4.5 | Final rebuild + distribution | 🔲 NOT STARTED | — | Depends on 4.1-4.4 |
| 4.6 | stanfordohs.pronto.io end-to-end test | 🔲 NOT STARTED | — | Depends on 4.5 |

### Phase 4 Exit Gate
- [ ] Release notes complete
- [ ] All trackers synchronized
- [ ] Final distribution ZIP ready
- [ ] MVP acceptance criteria met

---

## Phase 3.5: Monitoring/Reporting/Admin Reliability Sprint (Days 6-7)

| ID | Task | Status | Date | Evidence / Notes |
|----|------|--------|------|-----------------|
| 3.5.1 | Fix blank hourly reports (BUG-007) | 🟡 IN PROGRESS | 2026-02-21 | Added report-window wiring + diagnostics: `send_hourly_report()` now uses configured minute interval (`schedule.get_hourly_interval_minutes()`), logs 5-min telemetry diagnostics (`sessions_in_window`, `open_sessions`, `visible_foreground_samples`, DB path), and fallback now derives activity from `visible_windows` whenever active duration is zero (not only when session count is zero). Added regressions in `test_reporting_and_override_regressions.py`; targeted run passed (`10 passed`). Remaining close criteria: verify non-blank email in rebuilt/runtime lane with captured logs. |
| 3.5.2 | Saved links reliability hardening (BUG-006) | ✅ DONE | 2026-02-21 | User confirmed save flow now works; blocked-page badge reflects unviewed saved link count. |
| 3.5.3 | Saved links discoverability (BUG-009) | ✅ DONE | 2026-02-21 | Added dashboard saved-links card + blocked-popup CTA link that opens dedicated admin UI Saved Links route (`/saved-links`). |
| 3.5.4 | Edge blocking parity verification/fix (BUG-008) | ✅ DONE | 2026-02-21 | Focused packaged-lane smoke: `/api/status` shows both `chrome` + `edge` connected; `/api/should_block` parity check matches for `youtube.com` (blocked in both) and `wikipedia.org` (allowed in both) when `browser=Microsoft Edge` vs `browser=Google Chrome`. |
| 3.5.5 | Classifier trust hardening (BUG-010) | � IN PROGRESS | 2026-02-21 | Implemented adaptive slice: generic classifier now preserves classifier provenance, blocker adds normalized decision metadata (`decision_source`, `block_basis`), low-confidence LLM escalation, and non-destructive uncertain policy defaults; regression suite extended and passing (`29 passed` in `test_classification_integration.py`). |
| 3.5.6 | Admin console runtime robustness (BUG-011) | 🟡 IN PROGRESS | 2026-02-21 | Root-cause hardening landed: packaged smoke/verification defaults now target admin gateway (`58393`), and PyInstaller specs now bundle `admin_ui/dist` so `/admin` SPA can be mounted in frozen runtime. Current live runtime still shows `/admin` 404 with health/meta/dashboard 200 until rebuilt/relaunched on updated artifact; auth login now reaches route (401 on default creds instead of 404). |
| 3.5.7 | Packaged smoke hardening for admin routes | ✅ DONE | 2026-02-21 | Added explicit `/admin/saved-links` assertion to packaged smoke spec (`admin_ui/e2e/packaged-runtime-smoke.spec.ts`). |
| 3.5.8 | Admin console integration coverage expansion | ✅ DONE | 2026-02-21 | Extended admin SPA backend serving test for `/admin/saved-links` + `/admin/login` and expanded Playwright critical smoke to validate Saved Links page render and data. |
| 3.5.9 | Devices route stability fix (BUG-012) | 🔲 NOT STARTED | — | New unresolved bug from `BUGS_02212026.md`: `/admin/devices` throws error in runtime lane. |
| 3.5.10 | Activity-first admin dashboard expansion (BUG-014) | ✅ DONE | 2026-02-21 | Added backend aggregation + frontend rendering for `activity_summary`, `open_tabs`, and `recent_blocked_tabs`; added regression coverage in dashboard service tests. |
| 3.5.11 | Saved links hyperlink rendering fix (BUG-016) | ✅ DONE | 2026-02-21 | Saved Links URLs now render as clickable anchors with safe href normalization; Playwright critical smoke asserts link + href. |
| 3.5.12 | Friction/override UX clarity pass (BUG-015) | 🔲 NOT STARTED | — | Improve interpretability of Top Friction Domains + Recent Overrides (labels, semantics, synthetic entries). |
| 3.5.13 | Settings page MVP wiring pass (BUG-013) | 🔲 NOT STARTED | — | `/admin/settings` currently not meaningful; add actionable controls tied to runtime behavior. |
| 3.5.14 | Local log-review helper module (BUG-017) | 🔲 NOT STARTED | — | Add module to inspect `C:\ProgramData\FocusGuard\logs` and suggest improvements. |
| 3.5.15 | Blocked-popup budget context pass (BUG-018) | 🔲 NOT STARTED | — | Show limit/used/remaining values in blocked popup for current domain/classification budget. |
| 3.5.16 | File-sharing fiction detection consistency (BUG-019) | 🔲 NOT STARTED | — | New report: inconsistent behavior for fiction/books across archive.org subdomains/extension-wrapped URLs vs archive.org details pages; also include gutenberg.org classification consistency and regression tests. |
| 3.5.17 | Classification latency instrumentation + SLA guardrails (BUG-020) | 🔲 NOT STARTED | — | User observed possible latency/context timing gap in file-sharing decisions; add per-decision timing diagnostics (rules/LLM/escalation/context age), then tune thresholds/TTL. |

### Phase 3.5 Exit Gate
- [ ] Hourly emails contain real activity when activity occurred
- [ ] Saved links are stable and discoverable
- [ ] Edge lane parity with Chrome lane is validated
- [ ] Classification accuracy issue is resolved or explicitly documented
- [ ] File-sharing literature/fiction classification is consistent across archive.org (including subdomains), extension-wrapped URLs, and gutenberg.org
- [ ] Classification latency/escalation timing has actionable runtime diagnostics
- [ ] Admin console SPA routes (`/admin`, `/admin/saved-links`) are reliable in packaged runtime
- [ ] Devices route, activity dashboard visibility, saved-links hyperlink behavior, and friction/override readability are validated

---

## Session Log

### Session 1 — February 20, 2026
- **Scope**: Phase 1 (1.1–1.3) + Phase 2 (2.1–2.2)
- **Tasks Completed**: 1.1, 1.2, 1.3, 2.1, 2.2
- **Files Modified**:
  - `focus_guard/main.py` — `_load_icon()` rewritten with `sys._MEIPASS` path, logging, improved fallback; `_get_meipass()` helper added; settings dialog pre-fills password page
  - `focus_guard/gui/first_run_wizard.py` — Added `PasswordPage` class with validation; wired into wizard page list and `get_config()`; updated welcome page step list
  - `focus_guard/core/browser_v2/tab_server/server.py` — Added `/api/blocked/sites` + `/api/saved_links` (GET/POST) + `/api/saved_links/stats` + `/api/saved_links/view` + `/api/saved_links/delete` routes and handlers
  - `focus_guard/core/admin_gateway/services/dashboard_service.py` — Fetches `/api/blocked/sites`, adds `blocked_sites` + `total_blocks` to dashboard payload
  - `admin_ui/src/api/dashboard.ts` — Added `BlockedSiteItem` type, `blocked_sites`/`total_blocks` fields
  - `admin_ui/src/views/DashboardPlaceholder.tsx` — Added "Blocked Sites Today" section with red-tinted cards
  - `focus_guard/core/browser/extension/webextension_mv3/blocked.html` — Added "Save for Later" button + expandable form
  - `focus_guard/core/browser/extension/webextension_mv3/blocked.js` — Added save link JS functions + event listeners
- **Files Created**:
  - `focus_guard/core/browser_v2/tab_server/saved_links.py` — SQLite-backed SavedLinksStore with CRUD + stats
- **Outcome**: Phase 1 code fixes complete (1.1–1.3), Phase 2 features 2.1 and 2.2 complete. Remaining: 1.4 rebuild, 1.5 smoke test, 2.3 wizard improvements, 2.4 blocked page polish
- **Follow-ups**: Rebuild exe (1.4), smoke test (1.5), then Phase 2.3 wizard improvements

### Session 2 — February 21, 2026
- **Scope**: Triaged user-reported issues from `BUGS_02212026.md`, integrated into plan/tracker, began implementation of highest-priority reliability fixes.
- **Items Added to Active Plan**:
  - BUG-006 Saved links disk I/O error
  - BUG-007 Blank hourly report
  - BUG-008 Edge extension blocking parity gap
  - BUG-009 Saved-links discoverability gap
  - BUG-010 Potential classification false-positive (folger.edu Macbeth)
- **Priority Order Set**: Reporting reliability (BUG-007) → Edge parity (BUG-008) → Saved-links reliability/discoverability (BUG-006/009) → Classification trust (BUG-010)
- **Current Execution**: 3.5.4 next (Edge parity), after completing 3.5.2 and 3.5.3

### Session 3 — February 21, 2026
- **Scope**: Incorporated newly reported unresolved bugs into active plan and tracker sequencing.
- **New Unresolved Bugs Added**:
  - BUG-012 Devices route runtime error (`/admin/devices`)
  - BUG-013 Settings page lacks meaningful controls
  - BUG-014 Activity visibility gaps in admin dashboard
  - BUG-015 Top Friction / Recent Overrides readability issues
  - BUG-016 Saved links not shown as hyperlinks
  - BUG-017 Request for local log-review helper module
- **Execution Sequence (requested)**: keep BUG-007 as active blocker, then execute 3.5.9 → 3.5.10 → 3.5.11 → 3.5.12 → 3.5.13 → 3.5.14.
- **Current Execution**: 3.5.1 remains IN PROGRESS pending non-blank hourly report evidence from runtime emails.

### Session 4 — February 21, 2026
- **Scope**: Closed BUG-007, BUG-014, BUG-016 with tests and live runtime sanity checks.
- **BUG-007 Evidence**:
  - Runtime resolver selected `C:\Users\prasun_agarwal\AppData\Local\FocusGuard\usage.db`.
  - Telemetry sample query returned persisted `usage_sessions` rows.
  - Forced hourly send using `EmailReporter.send_hourly_report(...)` returned `forced_hourly_send_success=True`.
  - Added regression tests for DB-path selection and visible-window fallback path.
- **BUG-014 Evidence**:
  - Dashboard service now returns activity-first data blocks (`activity_summary`, `open_tabs`, `recent_blocked_tabs`).
  - Admin UI dashboard renders dedicated sections for these signals.
  - Unit test coverage updated for both populated and offline-default scenarios.
- **BUG-016 Evidence**:
  - Saved links page now renders URL as `<a>` with `target="_blank"` and safe href normalization.
  - Critical Playwright smoke updated to validate clickable link behavior.

### Session 5 — February 21, 2026
- **Scope**: Started BUG-010 classifier trust hardening implementation slices and re-triaged newly reported runtime issues.
- **Implementation Completed (BUG-010 slice progress)**:
  - Generic classification now preserves true classifier provenance/reason metadata in tab-server classification results.
  - Classification blocker now emits normalized transparency fields (`decision_source`, `block_basis`, `block_reason`).
  - Added low-confidence handling: optional LLM escalation + configurable uncertain policy (default non-destructive allow).
  - Context wiring improved to forward tab/search-context metadata into adaptive classification path.
- **Regression Coverage**:
  - Added/updated tests in `focus_guard/core/browser_v2/tab_server/tests/test_classification_integration.py`.
  - Targeted test command result: `29 passed`.
- **New/Reopened Triage Outcomes**:
  - BUG-007 reopened based on user-provided blank hourly report evidence in runtime lane.
  - Added BUG-019 for file-sharing fiction detection consistency (archive.org subdomains, extension-wrapped URLs, gutenberg.org).
  - Added BUG-020 for classification latency/context timing instrumentation and tuning.

### Session 6 — February 21, 2026
- **Scope**: BUG-007 runtime blank-email follow-up (wiring + diagnostics pass).
- **Code changes**:
  - `focus_guard/deployment/email_reporter.py`
    - Hourly report window now uses configured minute interval instead of hardcoded 1 hour.
    - Added recent-activity diagnostics logging for report send attempts.
    - Broadened visible-window fallback to recover activity whenever `total_active_time` is zero.
- **Regression coverage**:
  - `focus_guard/tests/core/test_reporting_and_override_regressions.py`
    - Added `test_send_hourly_report_uses_schedule_interval_minutes`.
    - Added `test_hourly_fallback_uses_visible_windows_when_sessions_have_zero_active_time`.
  - Targeted command: `python -m pytest focus_guard/tests/core/test_reporting_and_override_regressions.py -q`
  - Result: `10 passed`.
- **Remaining validation**:
  - Rebuild and run packaged/runtime lane.
  - Confirm hourly email body is non-blank and correlate with new diagnostics log line.
