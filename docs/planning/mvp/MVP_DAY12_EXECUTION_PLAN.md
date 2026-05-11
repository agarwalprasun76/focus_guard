# Focus Guard MVP Day 12 Execution Plan

## Day 12 Objective
Finalize low-cost remote login runbook and close Week 2 with integrated validation + handoff updates.

## Workstream
- **F) Low-cost remote login runbook** (Week 2 required)
- Week 2 integration closure across A-F

## Tasks
- [x] Add a practical remote login runbook in `INSTALL_WINDOWS.md` for out-of-network access:
  - recommended low-cost secure tunnel path
  - operational fallback path
  - troubleshooting flow
- [x] Add security guardrails:
  - no raw public ports by default
  - admin credential hygiene requirements
  - session/origin hardening notes
- [x] Update `MVP_SMOKE_TEST.md` with a Week 2 remote-access verification step.
- [x] Run or document evidence for Week 2 validation:
  - setup validation gate behavior
  - extension onboarding clarity
  - metrics range-query checks
  - remote login path test
- [x] Create/update a Week 2 handoff section (in Week 2 master or a dedicated handoff file).

## Optional stretch
- [ ] Run `python scripts/admin_gateway_smoke.py --password ...` and append one-line result in relevant handoff docs.
- [x] Cross-link Week 2 outcomes back into `MVP_SPRINT_MASTER_PLAN.md`.

## Validation checklist
- [x] A new operator can follow docs to access dashboard from a different network safely.
- [x] Security caveats and guardrails are clear at the point of action.
- [x] Week 2 execution tracker in master plan reflects actual status.
- [x] Open follow-ups are moved to parking lot explicitly (no silent leftovers).

## Files expected to change
- `docs/planning/mvp/INSTALL_WINDOWS.md`
- `docs/planning/mvp/MVP_SMOKE_TEST.md`
- `docs/planning/mvp/MVP_SPRINT_MASTER_PLAN_Week2.md`
- Optional: `docs/planning/mvp/MVP_WEEK2_HANDOFF.md` (new) if preferred over inline closeout

## Exit criteria
Day 12 is done when Week 2 required outcomes are either completed with evidence or explicitly deferred with rationale and next owner.
