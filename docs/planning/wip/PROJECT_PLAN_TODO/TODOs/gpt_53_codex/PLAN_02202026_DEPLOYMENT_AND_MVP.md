# Focus Guard — Updated Deployment & MVP Plan
**Date**: February 20, 2026  
**Status**: Comprehensive stocktake and forward blueprint  
**Supersedes**: `Plan_02152026.md`, `PLAN_02152026_1536_MVP_EXECUTION_CHECKLIST.md`

---

## Table of Contents
1. [Where We Are — Project Stocktake](#1-where-we-are--project-stocktake)
2. [Outstanding Bugs & Open Items](#2-outstanding-bugs--open-items)
3. [Additional Features Requested](#3-additional-features-requested)
4. [Updated MVP Definition](#4-updated-mvp-definition)
5. [Execution Plan — Phased Blueprint](#5-execution-plan--phased-blueprint)
6. [Validation & Release Gates](#6-validation--release-gates)
7. [Post-MVP Roadmap (Prioritized)](#7-post-mvp-roadmap-prioritized)

---

# 1. Where We Are — Project Stocktake

## 1.1 Completed Work Summary

### Core Application (opus_45 track — Feb 6-9, 2026)
| Component | Status | Key Evidence |
|-----------|--------|-------------|
| **Unified entry point** (`focus_guard/main.py`) | ✅ Done | Single exe starts tray + tab server + monitor + email reporter |
| **PyInstaller build** (`FocusGuard.exe`, 442 MB) | ✅ Done | Onefile, console=False, all components verified |
| **First-run wizard** (7-page PyQt5) | ✅ Done | Welcome → Email → Extension → Time Limits → Personalization → Domain Manager → Finish |
| **System tray** (Settings, Extension, About, Exit) | ✅ Done | Proper dialogs, no raw JSON |
| **Distribution ZIP** (`FocusGuard-v1.0.0-win64.zip`) | ✅ Done | 441.6 MB with README, LICENSE, PRIVACY_POLICY |
| **Post-build verification** (12/12 smoke checks) | ✅ Done | Tray, tab server, blocking, override, email, 1hr soak, reboot autostart |
| **Enforcement modes** (tracking/advisory/enforcing) | ✅ Done | Feature 6.4 complete |
| **Personalized blocking page** | ✅ Done | Feature 6.5 complete — greeting, streak, focus score, motivational quotes |
| **Domain config consolidation** (`DomainConfigManager`) | ✅ Done | Single source of truth, API endpoints, wizard UI |
| **Analytics service** (daily/weekly/heatmap APIs) | ✅ Done | Focus score, streak, top domains, alerts |
| **Security mitigations** (Section 8, P0-P3) | ✅ Done | 13 modules, 132/132 tests passing |

### Browser Extensions
| Component | Status | Details |
|-----------|--------|---------|
| **Chrome extension** | ✅ Live | ID: `hnpfnmlcmdhkbhnfifmnonehebeafclp` |
| **Edge extension** | ✅ Live | ID: `legaalcjhhgofgpgbbpoadafdjllckgg` |
| **Manifest version** | 1.0.1 | Both stores |

### Admin UX (gpt_53_codex track — Feb 14-18, 2026)
| Component | Status | Key Evidence |
|-----------|--------|-------------|
| **Phase 1 UX (P1-P4)** | ✅ Done | Release gate: GO |
| **Admin gateway** (FastAPI, auth, CORS, SPA serving) | ✅ Done | 36+ backend tests passing |
| **Admin UI** (React + Tailwind + TanStack Query) | ✅ Done | Login, dashboard, exceptions, devices, settings |
| **Post-P4 integration (I0-I6)** | ✅ Done | Contract foundations, packaged lane, resilience, simulation, loophole triage |
| **Runtime startup orchestrator** | ✅ Done | Graceful tab-server/admin-gateway bring-up, diagnostics command |
| **Packaged lane validation** | ✅ Done | Source + packaged lanes both green (P0-2 verified) |

## 1.2 Architecture Overview (Current)

```
FocusGuard.exe (PyInstaller onefile, 442 MB)
├── System Tray (PyQt5) ──── user interaction, settings wizard
├── Tab Server (aiohttp, port 58392) ──── browser extension API
│   ├── Classification pipeline (rule-based + optional LLM)
│   ├── Domain usage tracker + budgets
│   ├── Override manager
│   ├── Audit/search/screenshot logging
│   ├── Analytics service (daily/weekly/heatmap)
│   ├── Security monitors (heartbeat, hosts, VPN, clock, user account)
│   └── API auth (bearer token on mutations)
├── Admin Gateway (FastAPI, port 58393) ──── parent/admin web UI
│   ├── Auth (login/refresh/logout/me)
│   ├── Dashboard aggregation
│   ├── Exception management (create/list/revoke)
│   ├── Device status + enforcement control
│   └── Static SPA serving (/admin)
├── Activity Monitor ──── window tracking
├── Email Reporter ──── scheduled reports
└── Coordinator ──── lifecycle management
```

## 1.3 Test Coverage Snapshot

| Layer | Tests | Status |
|-------|-------|--------|
| Backend admin gateway (pytest) | ~45+ | ✅ Passing |
| Security mitigations (pytest) | 132 | ✅ Passing |
| Frontend unit (Vitest) | ~10+ | ✅ Passing |
| Frontend integration (MSW) | 6 | ✅ Passing |
| Frontend E2E (Playwright) | 8+ | ✅ Passing |
| Packaged smoke (Playwright) | 4 | ✅ Passing |
| Distraction simulation harness | 5 scenarios + chaos | ✅ Passing (dry-run) |

---

# 2. Outstanding Bugs & Open Items

## 2.1 Known Bugs / Unresolved Issues

| ID | Severity | Description | Status | Notes |
|----|----------|-------------|--------|-------|
| **BUG-001** | HIGH | **System tray icon not showing** | NEW | Reported in ADDITIONAL_FEATURES.md item #6. Needs investigation — may be PyInstaller resource bundling issue or PyQt5 icon path resolution in frozen exe. |
| **BUG-002** | MEDIUM | **First-run wizard UX needs improvement** | OPEN | Per DEPLOYMENT_AND_MVP_PLAN notes: email config unclear, UI not polished, missing info about app capabilities and available settings. |
| **BUG-003** | MEDIUM | **Time limits not fully configured in wizard** | OPEN | Per DEPLOYMENT_AND_MVP_PLAN: educational/distraction/override time limits need proper defaults and user-facing configuration. TimeLimitsPage exists but may need UX refinement. |
| **BUG-004** | LOW | **Favicon 404 in logs** | KNOWN | Browser requests `/favicon.ico` — benign, cosmetic fix. |
| **BUG-005** | LOW | **Version info says 2025 copyright** | KNOWN | Per DEPLOYMENT_AND_MVP_PLAN — needs update to 2026. |
| **BUG-006** | HIGH | **Saved links fails with disk I/O error** | NEW | User-reported from blocked flow. Must verify SQLite write path and add fallback/readability diagnostics. |
| **BUG-007** | CRITICAL | **Hourly email report arrives blank (0 sessions / 0 active time)** | ✅ FIXED (2026-02-21) | Root-cause fix landed: telemetry-aware DB selection + hourly fallback from foreground visible-window samples; forced hourly send returned success in runtime sanity check. |
| **BUG-008** | HIGH | **Edge extension not blocking while Chrome blocks** | NEW | Needs parity verification for Edge service-worker flow, runtime connectivity, and mutation/block checks. |
| **BUG-009** | MEDIUM | **Saved links discoverability gap (where to view?)** | NEW | User expects visibility in extension popup and tray/admin surfaces. |
| **BUG-010** | MEDIUM | **Potential false-positive classification (folger.edu Macbeth blocked)** | NEW | Needs rule/classifier review and appeal/feedback workflow guidance. |
| **BUG-011** | HIGH | **Admin console launch/reliability gaps in packaged runtime** | NEW | Admin API may come up while SPA shell is unavailable (`/admin`/`/admin/saved-links`); requires startup architecture hardening + better diagnostics. |
| **BUG-012** | HIGH | **Admin devices page throws runtime error** | NEW | User reports `/admin/devices` failing at runtime; likely contract/UI rendering mismatch under packaged lane. |
| **BUG-013** | MEDIUM | **Settings page lacks meaningful controls/content** | NEW | User reports settings view is present but not actionable; needs MVP-meaningful controls and wiring. |
| **BUG-014** | HIGH | **Admin dashboard missing expected activity visibility** | ✅ FIXED (2026-02-21) | Dashboard now exposes and renders activity summary + open tabs + recent blocked tabs with regression coverage. |
| **BUG-015** | MEDIUM | **Top Friction Domains / Recent Overrides readability is poor** | NEW | Values and labels are hard to interpret (including synthetic smoke domains); requires UX/data clarity improvements. |
| **BUG-016** | MEDIUM | **Saved links list not rendered as clickable hyperlinks** | ✅ FIXED (2026-02-21) | Saved Links URLs now render as clickable anchors with safe href normalization; critical smoke asserts link + href. |
| **BUG-017** | MEDIUM | **Need local log-review helper for `C:\ProgramData\FocusGuard\logs`** | NEW | User requested a module to summarize logs and suggest software improvements from runtime evidence. |
| **BUG-018** | MEDIUM | **Blocked popup should show per-page/domain limit and time used** | NEW | User requested clearer budget context directly on blocking popup to explain why a page is blocked. |

## 2.1.1 Newly Reported MVP-Blocking Focus (Feb 21, 2026)

For launch readiness, these are treated as immediate blockers in this order:

1. **Reporting reliability**: BUG-007 (blank hourly report)
2. **Monitoring/blocking parity**: BUG-008 (Edge vs Chrome behavior mismatch)
3. **Saved-links reliability and visibility**: BUG-006 + BUG-009
4. **Classification trust/accuracy**: BUG-010

## 2.1.2 Newly Added Unresolved Bug Sequence (from BUGS_02212026 updates)

After BUG-007/014/016 closure, execute remaining unresolved items sequentially:

1. **BUG-012**: fix `/admin/devices` runtime failure
2. **BUG-015**: clarify Top Friction + Recent Overrides semantics and presentation
3. **BUG-013**: make settings page actionable for MVP-critical controls
4. **BUG-017**: add log-review helper module for `C:\ProgramData\FocusGuard\logs`
5. **BUG-018**: show per-page/domain limit and time-used context on blocking popup

## 2.2 Open Loopholes (from LOOPHOLE_TRACKER.md)

| ID | Severity | Status | Description |
|----|----------|--------|-------------|
| **L-001** | S2 | CLOSED | Vite build base path mismatch — fixed |
| **L-002** | S3 | DEFERRED | Recovery messaging responsiveness — stale-snapshot message delayed during recovery. Revisit date was 2026-02-22. |
| **L-003** | S2 | VERIFIED | Packaged mutation confidence gap — addressed with green evidence |

## 2.3 Open Checklist Items (from PLAN_02152026_1536)

| Item | Priority | Status | Notes |
|------|----------|--------|-------|
| **P0-1** L-003 packaged mutation gap | P0 | ✅ DONE | Verified green |
| **P0-2** Runtime contract verification | P0 | ✅ DONE | Both lanes green |
| **P0-3** Clean Windows VM validation | P0 | ❌ NOT DONE | Critical for real-world confidence |
| **P0-4** Enforcement password activation | P0 | ❌ NOT DONE | `config_password_hash` not set |
| **P1-1** L-002 revisit decision | P1 | ❌ NOT DONE | Due 2026-02-22 |
| **P1-2** Shadow Cycle 002 | P1 | ❌ NOT DONE | Nightly cycle not yet run |
| **P1-3** Tracker/governance consistency | P1 | ❌ NOT DONE | Housekeeping |
| **P1-4** Non-admin startup warnings | P1 | ❌ NOT DONE | Hosts/incognito require admin |

## 2.4 Deployment Plan Open Items (from opus_45 DEPLOYMENT_AND_MVP_PLAN)

| Item | Status | Notes |
|------|--------|-------|
| **Inno Setup installer** (D2) | NOT STARTED | Proper Windows installer with Start Menu, uninstaller, etc. |
| **Clean VM testing** (B2 partial) | NOT DONE | Never tested on machine without Python |
| **Test suite organization** | NOT DONE | Per Section 8 note: "fragmented test suite, need to organize" |
| **Fail-open vs fail-closed user config** | NOT DONE | Per Section 8 end note |
| **Rebuild exe with security modules** | NEEDED | Security modules (Section 8) added but exe not rebuilt since |
| **stanfordohs.pronto.io end-to-end test** | NOT DONE | Per Section 8 remaining item |

---

# 3. Additional Features Requested

From `ADDITIONAL_FEATURES.md`:

| # | Feature | Priority | Effort Est. | Notes |
|---|---------|----------|-------------|-------|
| AF-1 | **Save blocked links module** — save URLs blocked during focus, let user add comments, store in DB, allow viewing during break time | HIGH | 3-5 days | High user value — turns blocking from frustration into deferred gratification |
| AF-2 | **User request/feedback collation module** | MEDIUM | 2-3 days | Collect user feedback on classifications, blocking decisions |
| AF-3 | **Agentic debugging via log review** — improve debugging by having AI review logs and fix issues | MEDIUM | 3-5 days | Dev productivity improvement |
| AF-4 | **Multi-VM testing with agent simulation** — create VMs running FocusGuard, have agents do random things to generate logs/patterns | LOW | 1-2 weeks | Testing infrastructure investment |
| AF-5 | **Dashboard/popup blocked sites display** — show websites blocked and block count on dashboard/popup | HIGH | 1-2 days | Quick win, high visibility — analytics service already has the data |
| AF-6 | **Fix tray icon not showing** | HIGH | 0.5-1 day | Bug fix — same as BUG-001 |

---

# 4. Updated MVP Definition

## 4.1 What "MVP Shippable" Means (Feb 20, 2026 Revision)

The MVP is **shippable to a real user** when ALL of the following are true:

### Must-Have (Blocking Release)
- [ ] `FocusGuard.exe` works on a clean Windows 10/11 machine (no Python)
- [ ] System tray icon appears and is functional
- [ ] Extension installs from Chrome/Edge store and connects to tab server
- [ ] At least 3 domain classifiers work correctly (YouTube, Reddit, Google)
- [ ] Budget tracking and blocking work end-to-end
- [ ] Override system works with penalties and expiry
- [ ] App runs stable for 8+ hours without crash
- [ ] App auto-starts on boot
- [ ] Logs rotate and don't grow unbounded
- [ ] Enforcement password is active and working
- [ ] Admin UI is accessible and functional (login, dashboard, exceptions, devices)
- [ ] No critical or high severity bugs remain open
- [ ] Exe is rebuilt with all current code (security modules, admin gateway, analytics)

- [ ] Email reports send correctly (when configured)
- [ ] First-run wizard is clear and complete
- [ ] Blocked sites display on dashboard/popup (AF-5)
- [ ] Saved blocked links feature (AF-1)
- [ ] Incognito browsing is monitored
- [ ] Full test suite organized and runnable

### Nice-to-Have (Defer if Needed)
- [ ] Inno Setup installer
- [ ] Clean VM validation documented

---

# 5. Execution Plan — Phased Blueprint

## Phase 1: Critical Bug Fixes & Rebuild (Days 1-2)
> **Goal**: Fix blocking bugs, rebuild exe with all current code

| ID | Task | Priority | Est. | Depends On |
|----|------|----------|------|------------|
| 1.1 | **Fix tray icon not showing** (BUG-001/AF-6) — investigate PyInstaller resource path, PyQt5 icon loading in frozen exe | CRITICAL | 2-4h | — |
| 1.2 | **Set enforcement password** — generate `config_password_hash`, verify mode-change API rejects without password, accepts with password | CRITICAL | 1h | — |
| 1.3 | **Update copyright to 2026** (BUG-005) | LOW | 15m | — |
| 1.4 | **Rebuild FocusGuard.exe** with all current code (security modules, admin gateway, analytics, bug fixes) | CRITICAL | 2-4h | 1.1, 1.2, 1.3 |
| 1.5 | **Smoke test rebuilt exe** — tray icon, tab server health, admin UI, blocking, override lifecycle | CRITICAL | 1-2h | 1.4 |

### Exit Gate
- Rebuilt exe passes 12-point smoke checklist
- Tray icon visible
- Enforcement password active

---

## Phase 2: MVP Feature Completion (Days 2-4)
> **Goal**: Add high-value features that define the MVP experience

| ID | Task | Priority | Est. | Depends On |
|----|------|----------|------|------------|
| 2.1 | **Blocked sites display on dashboard/popup** (AF-5) — add blocked sites list + count to dashboard widget and extension popup. Data already available from analytics service. | HIGH | 1-2 days | 1.4 |
| 2.2 | **Save blocked links module** (AF-1) — when a site is blocked, save URL + timestamp + optional user comment to SQLite. Add API endpoint to list/view saved links. Add "View Later" section to blocked page and dashboard. | HIGH | 3-4 days | 1.4 |
| 2.3 | **First-run wizard improvements** (BUG-002, BUG-003) — clarify email roles, improve UI polish, add more app info, ensure time limits are properly set with sensible defaults | MEDIUM | 1-2 days | 1.4 |
| 2.4 | **Blocked page UI improvement** — improve organization, show more info (budget remaining, override count, saved links option), better visual design | MEDIUM | 1 day | 2.2 |

### Exit Gate
- Dashboard shows blocked sites and counts
- Blocked links can be saved and viewed later
- First-run wizard is clear and complete
- Blocked page is informative and well-designed

---

## Phase 3: Stability & Validation (Days 4-6)
> **Goal**: Validate on clean environment, organize tests, ensure stability

| ID | Task | Priority | Est. | Depends On |
|----|------|----------|------|------------|
| 3.1 | **Clean Windows VM validation** — test FocusGuard.exe on a clean Windows 10/11 VM with no Python installed. Run full smoke checklist. | CRITICAL | 0.5-1 day | Phase 2 |
| 3.2 | **8-hour soak test** — run rebuilt exe for 8+ hours, monitor memory, check logs for errors | HIGH | 1 day (background) | 3.1 |
| 3.3 | **Test suite organization** — create a single `scripts/run_all_tests.py` that runs all backend + frontend + e2e tests in order with clear pass/fail reporting | HIGH | 0.5 day | — |
| 3.4 | **L-002 revisit** — reproduce stale recovery message, decide close/tune/defer | MEDIUM | 2h | — |
| 3.5 | **Non-admin startup behavior documentation** — document expected warnings when running without admin (hosts blocker, incognito policy), add guidance to README | MEDIUM | 1h | — |
| 3.6 | **Fail-open vs fail-closed user config** — make fail-closed behavior configurable in deployment_config.json per user preference | MEDIUM | 2-3h | — |
| 3.7 | **Rebuild exe + distribution ZIP** with all Phase 2-3 changes | HIGH | 2-4h | 3.1-3.6 |

### Exit Gate
- Clean VM validation passes
- 8-hour soak test passes
- All tests runnable from single command
- Distribution ZIP updated

---

## Phase 3.5: Monitoring/Reporting/Admin Reliability Sprint (Hotfix) (Days 6-7)
> **Goal**: Ensure monitoring, reporting, and admin console workflows are seamless before MVP launch.

| ID | Task | Priority | Est. | Depends On |
|----|------|----------|------|------------|
| 3.5.1 | **Fix blank hourly reports (reopened)** (BUG-007) — validate runtime lane where reports still show `Active Time: 0.0`/`Sessions: 0`; add scheduler diagnostics + DB/read-path reconciliation and close with real non-blank runtime email evidence | CRITICAL | 2-4h | 3.1 |
| 3.5.2 | **Saved links reliability hardening** (BUG-006) — validate write path in packaged runtime, add safer fallback/error messaging | HIGH | 2-3h | 3.1 |
| 3.5.3 | **Saved links discoverability** (BUG-009) — add blocked-popup CTA link to Saved Links page + admin dashboard card | HIGH | 2-4h | 3.5.2 |
| 3.5.4 | **Edge blocking parity verification/fix** (BUG-008) — validate background checks and blocking path in Edge lane with reproducible smoke | HIGH | 0.5-1 day | 3.1 |
| 3.5.5 | **Classifier trust hardening** (BUG-010) — continue adaptive confidence pipeline (rule/LLM escalation + uncertain policy + explainability) for folger.edu and similar false-positive/false-negative cases without one-off domain hardcoding | HIGH | 0.5-1 day | 3.1 |
| 3.5.6 | **Admin console runtime robustness** (BUG-011) — harden startup orchestration so admin gateway API + SPA shell (`/admin`) come up reliably together; emit actionable diagnostics when UI assets are missing | CRITICAL | 0.5-1 day | 3.1 |
| 3.5.7 | **Packaged smoke hardening for admin routes** — add explicit assertion for `/admin/saved-links` route in packaged smoke suite | HIGH | 0.5-1h | 3.5.6 |
| 3.5.8 | **Admin console integration coverage expansion** — add integration/E2E checks for login shell, saved-links route, and key admin flows under app runtime contracts | HIGH | 2-4h | 3.5.6 |
| 3.5.9 | **Devices route stability fix** (BUG-012) — reproduce `/admin/devices` failure, fix backend/UI contract mismatch, add regression coverage | HIGH | 2-4h | 3.5.6 |
| 3.5.10 | **Activity-first admin dashboard expansion** (BUG-014) — expose open tabs, blocked tabs, saved links, and per-user activity signals for debugging/parent oversight | HIGH | 0.5-1 day | 3.5.9 |
| 3.5.11 | **Saved links hyperlink rendering fix** (BUG-016) — ensure saved links are clickable and open correctly from admin UI | MEDIUM | 1-2h | 3.5.10 |
| 3.5.12 | **Friction/override UX clarity pass** (BUG-015) — improve labels, units, and filtering of synthetic domains in Top Friction / Recent Overrides | MEDIUM | 2-4h | 3.5.10 |
| 3.5.13 | **Settings page MVP wiring pass** (BUG-013) — provide actionable settings tied to real runtime behavior | MEDIUM | 2-4h | 3.5.10 |
| 3.5.14 | **Local log-review helper module** (BUG-017) — add tooling to inspect `C:\ProgramData\FocusGuard\logs` and emit actionable improvement suggestions | MEDIUM | 0.5-1 day | 3.1 |
| 3.5.15 | **Blocked-popup budget context pass** (BUG-018) — show limit/used/remaining values for the blocked page/domain directly in popup UI | MEDIUM | 2-4h | 3.5.10 |
| 3.5.16 | **File-sharing fiction detection consistency** (BUG-019) — ensure fiction/book content on archive.org subdomains, extension-wrapped URLs, and gutenberg.org gets consistently classified/blocked via metadata + search-context pathways; add regression coverage | HIGH | 0.5-1 day | 3.5.5 |
| 3.5.17 | **Classification latency instrumentation + SLA guardrails** (BUG-020) — instrument per-decision timing (rules vs LLM vs escalation), detect stale/missed context windows, and tune TTL/thresholds to reduce "should-have-blocked" misses | MEDIUM | 2-4h | 3.5.5 |

### Exit Gate
- Hourly email reports include real activity data when activity occurs
- Saved links can be saved and discovered from user-facing surfaces
- Edge lane matches Chrome lane for core blocking flows
- Macbeth/folger classification behavior is explained and adjusted (or intentionally documented)
- File-sharing literature/fiction classification is consistent across archive.org (including subdomains), extension-wrapped URLs, and gutenberg.org
- Classification latency/escalation timing is observable with actionable diagnostics
- Admin console SPA routes (`/admin`, `/admin/saved-links`) are validated in packaged smoke and integration coverage
- Devices route, dashboard activity visibility, saved-link hyperlink behavior, and friction/override clarity are validated in packaged/runtime lanes

---

## Phase 4: Polish & Release Prep (Days 6-8)
> **Goal**: Final polish, documentation, release artifacts

| ID | Task | Priority | Est. | Depends On |
|----|------|----------|------|------------|
| 4.1 | **User feedback module** (AF-2) — simple feedback form in admin UI or tray menu for classification corrections and feature requests, stored locally | MEDIUM | 1-2 days | Phase 3 |
| 4.2 | **Shadow Cycle 002** — run nightly simulation, publish cycle doc, refresh loophole queue | LOW | 2-3h | — |
| 4.3 | **Tracker/governance cleanup** — align all tracker docs, add cross-track note (opus_45 = historical, gpt_53_codex = active), update dates | LOW | 1h | — |
| 4.4 | **Release notes v1.1** — document all changes since v1.0.0, known issues, upgrade instructions | MEDIUM | 1h | Phase 3 |
| 4.5 | **Final rebuild + distribution** | HIGH | 2-4h | 4.1-4.4 |
| 4.6 | **stanfordohs.pronto.io end-to-end test** — verify subdomain matching works in built exe | LOW | 30m | 4.5 |

### Exit Gate
- Release notes complete
- All trackers synchronized
- Final distribution ZIP ready
- MVP acceptance criteria met

---

# 6. Validation & Release Gates

## 6.1 Must-Pass Test Commands (PR Gate)

```bash
# Backend
python -m pytest focus_guard/tests/core/admin_gateway/ -q
python scripts/test_section8_mitigations.py

# Frontend
cd admin_ui && npm.cmd run test && npm.cmd run test:integration

# E2E
cd admin_ui && npm.cmd run test:e2e

# Packaged smoke (requires running exe)
cd admin_ui && npm.cmd run test:e2e:packaged:smoke
```

## 6.2 Manual Smoke Checklist (Pre-Release)

- [ ] Double-click `FocusGuard.exe` → tray icon appears
- [ ] Right-click tray → menu shows correctly
- [ ] Tab server responds at `http://127.0.0.1:58392/api/health`
- [ ] Admin UI accessible at `http://127.0.0.1:58393/admin`
- [ ] Admin login works
- [ ] Dashboard shows device status, budget, blocked sites count
- [ ] Install extension from store → connects to tab server
- [ ] Visit blocked site → blocking works, blocked page shows correctly
- [ ] Blocked page offers "Save for Later" option
- [ ] Override request works with correct expiry
- [ ] Enforcement mode change requires password
- [ ] Activity monitoring logs window changes
- [ ] Email report sends (if configured)
- [ ] App survives 1+ hour without crash
- [ ] Closing from tray → clean shutdown
- [ ] Reboot → app auto-starts

## 6.3 Clean VM Checklist

- [ ] Fresh Windows 10/11 (no Python, no dev tools)
- [ ] Download and extract ZIP
- [ ] Run FocusGuard.exe → first-run wizard appears
- [ ] Complete wizard → services start
- [ ] Install extension from store
- [ ] Verify blocking + override + dashboard
- [ ] Verify email (if configured)
- [ ] Reboot → auto-start works

---

# 7. Post-MVP Roadmap (Prioritized)

After MVP release, work proceeds in priority order:

## Tier 1: High Impact, Near-Term (Weeks 1-4 post-MVP)

| # | Feature | Effort | Impact | Source |
|---|---------|--------|--------|--------|
| R1 | **Inno Setup installer** — proper Windows installer with Start Menu, uninstaller, admin elevation | 1-2 days | HIGH | opus_45 §4.3 |
| R2 | **Classification proxy service** — Cloudflare Worker for LLM calls, removes API key requirement | 2-3 days | HIGH | opus_45 §4.2 / §6.1 |
| R3 | **Agentic log debugging** (AF-3) — AI reviews logs and suggests fixes | 3-5 days | MEDIUM | ADDITIONAL_FEATURES |
| R4 | **News & streaming classifiers** — CNN, BBC, Netflix, Twitch, etc. | 3-5 days | MEDIUM | opus_45 §4.4 |
| R5 | **Daily/weekly summary notifications** — Windows toast notifications | 1-2 days | MEDIUM | opus_45 §4.5 |

## Tier 2: Medium Impact, Medium-Term (Weeks 4-8 post-MVP)

| # | Feature | Effort | Impact | Source |
|---|---------|--------|--------|--------|
| R6 | **Focus sessions / Pomodoro mode** | 3-4 days | MEDIUM | opus_45 §4.6 |
| R7 | **Rule evolution system** — learn from overrides, suggest rule updates | 1-2 weeks | HIGH | opus_45 §4.7 |
| R8 | **Multi-VM testing infrastructure** (AF-4) | 1-2 weeks | LOW | ADDITIONAL_FEATURES |
| R9 | **Application monitoring** (beyond browser) — track desktop apps | 3-5 days | MEDIUM | opus_45 §4.10 |
| R10 | **WebSocket live updates** — replace polling with real-time | 3-4 days | MEDIUM | gpt_53_codex scope |

## Tier 3: High Impact, Long-Term (Months 2-4 post-MVP)

| # | Feature | Effort | Impact | Source |
|---|---------|--------|--------|--------|
| R11 | **Parent/guardian portal** — remote web portal for monitoring | 1-2 weeks | HIGH | opus_45 §4.8 |
| R12 | **Multi-device support (macOS)** | 3-4 weeks | HIGH | opus_45 §6.3 |
| R13 | **Screen capture + Vision LLM** | 2-4 weeks | VERY HIGH | opus_45 §4.11 |
| R14 | **Mobile companion app** | 4-8 weeks | HIGH | opus_45 §4.12 |
| R15 | **Gamification & rewards** | 2-3 weeks | MEDIUM | opus_45 §4.13 |

---

## Appendix A: Document Cross-Reference

| Document | Track | Role |
|----------|-------|------|
| `opus_45/DEPLOYMENT_AND_MVP_PLAN_02062026.md` | opus_45 | Historical deployment baseline + long-range roadmap |
| `opus_45/PROGRESS_TRACKER.md` | opus_45 | Deployment phases A-E + security + domain consolidation tracking |
| `opus_45/ADDITIONAL_FEATURES.md` | opus_45 | User-requested additional features |
| `gpt_53_codex/PHASE1_UX_TASK_BOARD.md` | gpt_53_codex | Admin UX Phase 1 task definitions |
| `gpt_53_codex/PROGRESS_TRACKER.md` | gpt_53_codex | Active execution tracking (UX + post-P4 integration) |
| `gpt_53_codex/POST_P4_EXECUTION_TASK_BOARD.md` | gpt_53_codex | Post-P4 integration task definitions (I0-I6) |
| `gpt_53_codex/LOOPHOLE_TRACKER.md` | gpt_53_codex | Active loophole tracking |
| **This document** | gpt_53_codex | **Current blueprint — supersedes prior plans** |

## Appendix B: Key File Locations

| Component | Path |
|-----------|------|
| Main entry point | `focus_guard/main.py` |
| PyInstaller launcher | `launch_focusguard.py` |
| PyInstaller spec | `deployment/application/windows/specs/focusguard_unified.spec` |
| Tab server | `focus_guard/core/browser_v2/tab_server/server.py` |
| Admin gateway | `focus_guard/core/admin_gateway/app.py` |
| Admin UI | `admin_ui/` |
| Browser extension | `focus_guard/core/browser/extension/webextension_mv3/` |
| First-run wizard | `focus_guard/gui/first_run_wizard.py` |
| Domain config manager | `focus_guard/core/domain/domain_config_manager.py` |
| Security monitors | `focus_guard/core/browser_v2/tab_server/{api_auth,heartbeat_monitor,hosts_blocker,...}.py` |
| Analytics service | `focus_guard/core/browser_v2/tab_server/analytics_service.py` |
| Runtime orchestrator | `focus_guard/deployment/runtime_startup.py` |
| Deployment config | `C:\ProgramData\FocusGuard\deployment_config.json` |
| Domain config | `C:\ProgramData\FocusGuard\domain_config.json` |

## Appendix C: Port Assignments

| Service | Port | Notes |
|---------|------|-------|
| Tab server | 58392 | Browser extension API |
| Admin gateway | 58393 | Parent/admin web UI |

---

*Created: February 20, 2026*  
*Author: Focus Guard Development Team*
