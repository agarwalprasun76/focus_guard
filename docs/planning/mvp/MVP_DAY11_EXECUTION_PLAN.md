# Focus Guard MVP Day 11 Execution Plan

## Day 11 Objective
Decide and codify the supported remote-access architecture for the admin dashboard, with secure defaults and clear trade-off documentation. Please help provide various potential solutions (cost/benefit tradeoffs) that make sense for this step before implementing this as it seems this may be a bigger decision from a scaling perspective.

## Workstream
- **E) Hosted admin dashboard architecture** (Week 2 required)

## Tasks
- [x] Produce an architecture decision note comparing:
  - localhost-only
  - LAN exposure
  - authenticated tunnel (recommended baseline)
  - hosted relay/service
- [x] Select one canonical MVP+ remote profile and document it in `INSTALL_WINDOWS.md`.
- [x] Update admin gateway config guidance (`host`, CORS/origins, auth expectations) for the selected profile.
- [x] Add explicit "do not expose raw public port by default" guidance.
- [x] Link decision from Week 2 plan and Day 7 handoff for continuity.

## Implementation notes
- This day can be documentation-heavy, but config defaults must remain safe.
- Prefer reversible config changes; avoid committing to expensive infra in this sprint.
- Keep threat model lightweight but explicit (who can reach dashboard, how authenticated, what is protected).

## Validation checklist
- [x] One remote profile is declared canonical (not multiple equally preferred options).
- [x] Install docs include concrete steps, not just architecture prose.
- [x] Config/auth guidance is internally consistent across docs.
- [x] Security caveats are visible near operator steps.

## Files expected to change
- `docs/planning/mvp/INSTALL_WINDOWS.md`
- Architecture note `docs/planning/mvp/ADR_001_REMOTE_ADMIN_ACCESS.md`
- `focus_guard/core/admin_gateway/config.py` (+ `dependencies.py`, `app.py`, `main.py`, `gui/setup_health_checks.py` for env-aligned behavior)
- `docs/planning/mvp/MVP_SPRINT_MASTER_PLAN_Week2.md` (status updates)

**Day 12 follow-up:** expand `INSTALL_WINDOWS.md` / `MVP_SMOKE_TEST.md` with a runnable tunnel runbook (Workstream F).

## Exit criteria
Day 11 is done when the team has one endorsed remote-access architecture and operators can follow a secure, low-ambiguity path.
