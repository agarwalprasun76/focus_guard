# Focus Guard MVP Sprint Master Plan

## Goal
Ship a usable MVP with reliable blocking/override behavior, guardian settings/dashboard, working reports, and repeatable install/onboarding.

## Scope Lock

### In scope
- Blocking + override reliability
- Guardian settings management (web UI)
- Guardian dashboard + reporting baseline
- Windows install/onboarding simplification
- Repeatable MVP smoke test

### Out of scope (Post-MVP)
- Full cloud multi-tenant decision service
- Native mobile app
- Advanced adaptive ML loops
- Deep data model refactors

## Workstreams

### A) Blocking/Override Reliability
- Stabilize `override_manager.py` + `domain_usage_tracker.py`.
- Ensure deterministic count/session behavior.
- Lock behavior with focused regression tests.

Primary files:
- `focus_guard/core/browser_v2/tab_server/override_manager.py`
- `focus_guard/core/browser_v2/tab_server/domain_usage_tracker.py`
- `focus_guard/core/browser_v2/tab_server/tests/test_override_flow.py`

### B) Remote Management Surface
- Complete settings/device APIs in Admin Gateway.
- Wire `admin_ui` settings/devices to real endpoints.

Primary files:
- `focus_guard/core/admin_gateway/api.py`
- `focus_guard/core/admin_gateway/routers/`
- `focus_guard/core/admin_gateway/services/`
- `focus_guard/core/admin_gateway/services/tab_server_client.py`
- `admin_ui/src/views/`
- `admin_ui/src/api/`

### C) Dashboard + Reporting MVP
- Replace dashboard placeholders with real data.
- Fix hourly/daily reporting reliability.

Primary files:
- `focus_guard/core/admin_gateway/services/dashboard_service.py`
- `focus_guard/core/browser_v2/tab_server/analytics_service.py`
- `admin_ui/src/views/*Dashboard*.tsx`
- `focus_guard/deployment/email_reporter.py`

### D) Install + Onboarding
- One clean Windows install path.
- Improve first-run wizard extension/admin handoff.

Primary files:
- `deployment/application/windows/`
- `deployment/installer/`
- `focus_guard/gui/first_run_wizard.py`
- `README.md`
- `docs/planning/mvp/INSTALL_WINDOWS.md` (to create if needed)

### E) MVP Smoke + Release Readiness
- Add and run repeatable smoke checklist/script.
- Burn down blocker bugs only.

Primary files:
- `docs/planning/mvp/MVP_SMOKE_TEST.md` (manual human gate)
- `docs/planning/mvp/MVP_TEST_MATRIX.md` (**index** of pytest / Vitest / Playwright / smoke helpers)
- `scripts/mvp_smoke.ps1` (HTTP smoke: tab + admin)
- `scripts/run_mvp_test_baseline.ps1` (Tier A pytest + smoke in one run)

## 10-Day Sequence
1. Reliability baseline (override flow stable)
2. Settings backend completion
3. Settings UI wiring
4. Devices MVP
5. Dashboard MVP
6. Reporting fixes
7. Install path + docs
8. First-run wizard polish
9. Smoke automation + blocker burn
10. MVP freeze and handoff

## Execution tracker (resume here)

Calendar-style **Day 1–5** execution docs absorbed most of items **1–8** above (overrides, admin surface, dashboard, reporting hardening, install, wizard handoff, classification/feedback slice). Treat the master sequence **9–10** as the remaining MVP closure work.

| Master sequence | Status | Notes |
|-----------------|--------|--------|
| 1–5 Reliability + admin + devices + dashboard | Done (see `MVP_DAY1`–`MVP_DAY3` handoffs) | |
| 6 Reporting fixes | Done | `email_reporter.py` + regression tests |
| 7 Install + docs | Done | `INSTALL_WINDOWS.md`, README, packaging script paths |
| 8 First-run wizard | Done | Guardian dashboard handoff in wizard |
| **9 Smoke + blocker burn** | **Automated slice done (Day 6)** | Baseline + matrix: `run_mvp_test_baseline.ps1`, `MVP_TEST_MATRIX.md`, `MVP_DAY6_HANDOFF.md`. **Manual** `MVP_SMOKE_TEST.md` recommended for full sign-off; **may be deferred** — see `MVP_DAY6_EXECUTION_PLAN.md` § Deferring manual smoke. |
| 10 MVP freeze + handoff | **Done** | **Technical freeze** in `MVP_DAY7_HANDOFF.md`; RC snapshot committed on `main` (`mvp-rc-2026-05-03` message). Optional named `git` tag still available. Manual smoke deferred with waiver. |

**Sprint closure (Day 7):** `MVP_DAY7_HANDOFF.md` — RC snapshot committed on `main`; optional `git tag mvp-rc-2026-05-03` on that commit. Manual `MVP_SMOKE_TEST.md` can still run anytime — see `MVP_DAY6_EXECUTION_PLAN.md` § Deferring manual smoke. **Next:** post-MVP backlog in `FEATURE_REQUESTS_PARKING_LOT.md`.

## Definition of Done
- Critical tab_server tests green
- Settings editable from guardian web UI
- Devices view usable
- Dashboard has real metrics
- Hourly/daily reports populated
- Install/onboarding path repeatable
- MVP smoke checklist passes end-to-end

