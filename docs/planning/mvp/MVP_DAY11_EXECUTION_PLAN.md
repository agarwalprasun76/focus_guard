# Focus Guard MVP Day 11 Execution Plan

## Day 11 Objective
Decide and codify the supported remote-access architecture for the admin dashboard, with secure defaults and clear trade-off documentation.

## Workstream
- **E) Hosted admin dashboard architecture** (Week 2 required)

## Tasks
- [ ] Produce an architecture decision note comparing:
  - localhost-only
  - LAN exposure
  - authenticated tunnel (recommended baseline)
  - hosted relay/service
- [ ] Select one canonical MVP+ remote profile and document it in `INSTALL_WINDOWS.md`.
- [ ] Update admin gateway config guidance (`host`, CORS/origins, auth expectations) for the selected profile.
- [ ] Add explicit "do not expose raw public port by default" guidance.
- [ ] Link decision from Week 2 plan and Day 7 handoff for continuity.

## Implementation notes
- This day can be documentation-heavy, but config defaults must remain safe.
- Prefer reversible config changes; avoid committing to expensive infra in this sprint.
- Keep threat model lightweight but explicit (who can reach dashboard, how authenticated, what is protected).

## Validation checklist
- [ ] One remote profile is declared canonical (not multiple equally preferred options).
- [ ] Install docs include concrete steps, not just architecture prose.
- [ ] Config/auth guidance is internally consistent across docs.
- [ ] Security caveats are visible near operator steps.

## Files expected to change
- `docs/planning/mvp/INSTALL_WINDOWS.md`
- Optional architecture note under `docs/planning/mvp/` (new markdown if needed)
- `focus_guard/core/admin_gateway/config.py` (only if defaults/notes need updates)
- `docs/planning/mvp/MVP_SPRINT_MASTER_PLAN_Week2.md` (status updates)

## Exit criteria
Day 11 is done when the team has one endorsed remote-access architecture and operators can follow a secure, low-ambiguity path.
