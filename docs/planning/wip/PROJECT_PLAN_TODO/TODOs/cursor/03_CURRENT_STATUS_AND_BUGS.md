# FocusGuard — Current Status, Open Bugs & Next Steps

**Created**: February 21, 2026
**Purpose**: Snapshot of where the project stands and what needs work.

---

## Current Project Status

### What's Working (Verified)
- Unified `FocusGuard.exe` builds and runs (442 MB, onefile)
- System tray with settings, extension links, about dialog
- First-run wizard (7-page PyQt5: Welcome → Email → Extension → Time Limits → Personalization → Domain Manager → Finish)
- Tab server on port 58392 with full HTTP API
- Admin gateway on port 58393 serving React SPA
- Chrome and Edge browser extensions published to stores
- Classification pipeline (YouTube, Reddit, Google, Twitter, generic URL)
- Budget tracking and enforcement (per-category + master distraction budget)
- Override system with penalties and expiry
- Saved links module (save blocked URLs for later viewing)
- Activity monitoring (window tracking, idle detection)
- Email reporting (hourly/daily via Gmail SMTP)
- Security mitigations (132/132 tests passing): API auth, heartbeat monitor, fail-closed, config integrity, enforcement password, hosts blocking, incognito policy, VPN detection, clock monitor, user account monitor
- Admin UI: login, dashboard (activity, blocked sites, budgets, friction, overrides), exceptions (create/list/revoke), devices, saved links
- Enforcement modes: tracking, advisory, enforcing
- Personalized blocked page (greeting, streak, focus score, motivational quotes)
- Domain config consolidation (DomainConfigManager singleton)
- Auto-start on boot
- Log rotation (10MB, 5 backups)

### What's in Progress
- Phase 3.5 reliability sprint (monitoring/reporting/admin hardening)
- Classifier trust hardening (BUG-010: adaptive confidence pipeline)
- Admin console runtime robustness (BUG-011: SPA routes in packaged runtime)

---

## Open Bugs (as of Feb 21, 2026)

### Critical / High Priority

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| BUG-007 | CRITICAL | **Hourly email report arrives blank** — 0 sessions, 0 active time | IN PROGRESS (wiring fix landed, needs rebuild + runtime verification) |
| BUG-011 | HIGH | **Admin console SPA routes unreliable in packaged runtime** — `/admin` may 404 | IN PROGRESS (PyInstaller specs updated to bundle admin_ui/dist) |
| BUG-012 | HIGH | **Admin /devices page throws runtime error** | NOT STARTED |
| BUG-010 | MEDIUM | **Classification false-positive** (folger.edu Macbeth blocked) — classifier trust gap | IN PROGRESS (adaptive confidence pipeline implemented, needs more coverage) |

### Medium Priority

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| BUG-013 | MEDIUM | **Settings page lacks meaningful controls** | NOT STARTED |
| BUG-015 | MEDIUM | **Top Friction/Recent Overrides readability** — labels, semantics, synthetic entries | NOT STARTED |
| BUG-017 | MEDIUM | **Need local log-review helper** for `C:\ProgramData\FocusGuard\logs` | NOT STARTED |
| BUG-018 | MEDIUM | **Blocked popup should show budget context** — limit/used/remaining | NOT STARTED |
| BUG-019 | MEDIUM | **File-sharing fiction detection inconsistency** — archive.org subdomains, gutenberg.org | NOT STARTED |
| BUG-020 | MEDIUM | **Classification latency instrumentation** — per-decision timing diagnostics | NOT STARTED |

### Resolved (Feb 21, 2026)

| ID | Description | Resolution |
|----|-------------|------------|
| BUG-001 | Tray icon not showing | Fixed: `sys._MEIPASS` path + fallback icon |
| BUG-005 | Copyright says 2025 | Fixed: updated to 2026 |
| BUG-006 | Saved links disk I/O error | Fixed: write path hardened |
| BUG-008 | Edge extension not blocking | Fixed: verified parity with Chrome |
| BUG-009 | Saved links not discoverable | Fixed: dashboard card + blocked-popup CTA |
| BUG-014 | Dashboard missing activity data | Fixed: activity_summary + open_tabs + recent_blocked_tabs |
| BUG-016 | Saved links not clickable hyperlinks | Fixed: rendered as `<a>` with safe href |

---

## Execution Plan (from PLAN_02202026)

### Current Phase: 3.5 — Monitoring/Reporting/Admin Reliability Sprint

**Completed tasks**: 3.5.2 through 3.5.4, 3.5.7, 3.5.8, 3.5.10, 3.5.11
**In progress**: 3.5.1 (blank reports), 3.5.5 (classifier trust), 3.5.6 (admin runtime)
**Not started**: 3.5.9, 3.5.12-3.5.17

### Remaining Phases

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1: Bug Fixes & Rebuild | Fix tray, password, copyright, rebuild exe | Mostly done (rebuild pending) |
| Phase 2: MVP Feature Completion | Blocked sites, saved links, wizard, blocked page | Done |
| Phase 3: Stability & Validation | Clean VM, soak test, test org, fail-open config | Not started |
| Phase 3.5: Reliability Sprint | Reporting, admin, classification hardening | In progress |
| Phase 4: Polish & Release | Feedback module, shadow cycle, release notes | Not started |

### Key Blockers Before MVP Ship

1. **Rebuild exe** with all current fixes (last rebuild was before Phase 3.5 work)
2. **Verify hourly email** produces non-blank report in runtime
3. **Admin console** must reliably serve SPA in packaged exe
4. **Clean VM test** — never tested on machine without Python

---

## Open Loopholes (from LOOPHOLE_TRACKER.md)

| ID | Severity | Status | Description |
|----|----------|--------|-------------|
| L-001 | S2 | CLOSED | Vite build base path mismatch |
| L-002 | S3 | DEFERRED | Recovery messaging responsiveness (stale snapshot delay). Revisit: 2026-02-22 |
| L-003 | S2 | VERIFIED | Packaged mutation confidence gap — green evidence |

---

## Recommended Next Actions (for new Cursor session)

1. **Rebuild the .exe** — many fixes since last build:
   ```powershell
   python -m PyInstaller --clean deployment/application/windows/specs/focusguard_unified.spec
   ```

2. **Verify hourly email** in runtime — BUG-007 fix needs real-world confirmation

3. **Fix BUG-012** — Admin devices page runtime error (likely contract mismatch)

4. **Fix BUG-013** — Wire settings page to real runtime controls

5. **Fix BUG-015** — Improve friction/override readability in admin dashboard

6. **Address BUG-019** — File-sharing fiction classification consistency

7. **Test on clean Windows VM** — critical gap, never done

---

## Test Commands Quick Reference

```powershell
# Backend admin gateway tests
python -m pytest focus_guard/tests/core/admin_gateway/ -q

# Section 8 security mitigations (132 tests)
python scripts/test_section8_mitigations.py

# Reporting + override regressions
python -m pytest focus_guard/tests/core/test_reporting_and_override_regressions.py -q

# Classification integration
python -m pytest focus_guard/core/browser_v2/tab_server/tests/test_classification_integration.py -q

# Frontend unit tests
cd admin_ui && npm run test

# Frontend integration tests (MSW)
cd admin_ui && npm run test:integration

# Frontend E2E (Playwright)
cd admin_ui && npm run test:e2e

# Packaged smoke (requires running exe + admin gateway)
cd admin_ui && npm run test:e2e:packaged:smoke

# Packaged runtime HTTP verification
python scripts/dev/verify_packaged_admin_runtime.py --base-url http://127.0.0.1:58393

# Simulation harness (dry run)
python scripts/integration_tests/distraction_simulation_harness.py --dry-run --scenario all
```
