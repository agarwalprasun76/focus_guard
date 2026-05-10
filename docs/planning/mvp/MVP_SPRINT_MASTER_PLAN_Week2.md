# Focus Guard MVP Sprint Master Plan - Week 2

## Why this plan exists
Week 1 reached technical freeze (Day 7). During closeout and a full docs/code review, several required follow-up items were identified before calling the product fully production-ready.

This Week 2 plan captures those **required** items separately from the parking-lot backlog.

## Week 2 required outcomes
1. Startup/setup is seamless and self-validating.
2. Browser extension install flow from Chrome + Edge stores is explicit and reliable.
3. Admin-install and designated monitored-user model is clear and supported.
4. Metrics are easy to query historically and prepared for central storage.
5. Requirements for hosting the admin dashboard beyond localhost are defined and implemented to MVP+ level.
6. A low-cost, secure path to log into the admin dashboard from another machine/network is documented and testable.

## Scope

### In scope (required)
- Setup validation gate in first-run flow
- Store-extension onboarding hardening
- Install-mode clarity for admin-installed machine + monitored user
- Metrics range-query and schema/retention contract
- Remote-access architecture decision and minimum secure implementation
- Low-cost remote access runbook

### Out of scope (still parking lot)
- Full multi-tenant SaaS backend
- Native mobile app
- Advanced analytics warehouse/ML pipelines

## Workstreams

### A) Setup and onboarding reliability (Required)
Goal: setup completion should prove readiness, not assume it.

Deliverables:
- Add a post-wizard "Setup validation" step that checks:
  - tab server health
  - admin gateway health
  - extension connectivity
  - admin auth readiness
- Surface actionable remediation when any check fails.
- Update install docs and smoke docs to include this step.

Primary files:
- `focus_guard/gui/first_run_wizard.py`
- `focus_guard/deployment/runtime_startup.py`
- `docs/planning/mvp/INSTALL_WINDOWS.md`
- `docs/planning/mvp/MVP_SMOKE_TEST.md`

Definition of done:
- Fresh install can end with explicit "ready" status.
- Failure states provide concrete next steps.

### B) Extension store flow hardening (Required)
Goal: remove ambiguity in Chrome/Edge store onboarding.

Deliverables:
- Document canonical store URLs, extension IDs, and supported browser assumptions.
- Add verification steps for "installed + connected" in install and smoke docs.
- Add fallback guidance for store-install failure.

Primary files:
- `focus_guard/core/extension_constants.py`
- `focus_guard/gui/first_run_wizard.py`
- `docs/planning/mvp/INSTALL_WINDOWS.md`
- `docs/planning/mvp/MVP_SMOKE_TEST.md`

Definition of done:
- Guardian can follow docs and verify extension connected state on first attempt.

### C) Admin install + designated monitored-user model (Required)
Goal: make machine-user security model explicit.

Deliverables:
- Document supported posture: installer run by admin, monitored user privilege assumptions, service/tray behavior, multi-session limits.
- Persist install posture metadata in deployment config/state where useful.
- Add operator checklist in install docs.

Primary files:
- `focus_guard/deployment/installer.py`
- `focus_guard/deployment/config.py`
- `docs/planning/mvp/INSTALL_WINDOWS.md`

Definition of done:
- One canonical supported machine-user model is documented and validated.

### D) Metrics usability and historical access (Required)
Goal: metrics should be easy to inspect and audit over time.

Deliverables:
- Confirm/clean local metrics schema contract and timestamp semantics.
- Add/expand date-range query endpoints used by dashboard analytics.
- Add indexing/migration notes for range-query performance.
- Document near-term centralization path (without forcing full cloud migration this sprint).

Primary files:
- `focus_guard/core/browser_v2/tab_server/activity_logger.py`
- `focus_guard/core/admin_gateway/services/dashboard_service.py`
- `focus_guard/core/admin_gateway/routers/activity.py`
- `docs/planning/mvp/MVP_TEST_MATRIX.md`

Definition of done:
- Historical day/week/month range queries are documented, tested, and usable.

### E) Hosted admin dashboard architecture (Required)
Goal: choose and document how remote access should work safely.

Deliverables:
- Architecture decision record comparing:
  - localhost-only baseline
  - LAN exposure
  - secure tunnel (e.g., Tailscale / Cloudflare Tunnel)
  - hosted relay/service
- Select one supported MVP+ remote profile (recommended: local gateway + authenticated tunnel).
- Update host/origin/auth guidance for remote profile.

Primary files:
- `focus_guard/core/admin_gateway/config.py`
- `focus_guard/main.py`
- `docs/planning/mvp/INSTALL_WINDOWS.md`
- `docs/planning/mvp/MVP_DAY7_HANDOFF.md` (cross-reference only)

Definition of done:
- Team has one canonical remote architecture and security expectations are explicit.

### F) Low-cost remote login runbook (Required)
Goal: practical remote access from a different network without unsafe defaults.

Deliverables:
- Add low-cost remote-access runbook with at least:
  - secure tunnel option (recommended)
  - operational fallback option
- Include security guardrails:
  - no raw public port opening by default
  - admin credential guidance
  - origin restriction and session management notes
- Add troubleshooting for remote login failures.

Primary files:
- `docs/planning/mvp/INSTALL_WINDOWS.md`
- `docs/planning/mvp/MVP_SMOKE_TEST.md`

Definition of done:
- Guardian can follow docs and log in remotely from outside local network.

## Week 2 execution tracker

| Workstream | Status | Notes |
|------------|--------|-------|
| A Setup validation gate | Planned | |
| B Extension store flow hardening | Planned | |
| C Admin install + designated user model | Planned | |
| D Metrics historical query contract | Planned | |
| E Hosted/remote architecture decision | Planned | |
| F Low-cost remote login runbook | Planned | |

## Exit criteria
Week 2 is complete when:
1. All six workstreams above are marked done.
2. A new operator can complete install + setup + remote access using docs alone.
3. Metrics historical queries are validated and documented.
4. One remote access architecture is selected and security trade-offs are explicit.

## Links back to Week 1 closeout
- `docs/planning/mvp/MVP_SPRINT_MASTER_PLAN.md`
- `docs/planning/mvp/MVP_DAY7_EXECUTION_PLAN.md`
- `docs/planning/mvp/MVP_DAY7_HANDOFF.md`
- Optional/non-required enhancements remain in `docs/planning/mvp/FEATURE_REQUESTS_PARKING_LOT.md`.
