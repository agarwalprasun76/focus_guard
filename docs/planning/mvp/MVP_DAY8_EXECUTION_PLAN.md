# Focus Guard MVP Day 8 Execution Plan

## Day 8 Objective
Ship a guided setup-validation experience and tighten the browser-extension onboarding flow so first-run completion reflects real runtime readiness.

## Workstreams
- **A) Setup and onboarding reliability** (Week 2 required)
- **B) Extension store flow hardening** (Week 2 required, phase 1)

## Tasks
- [ ] Add a post-wizard **Setup Validation** step in `first_run_wizard.py`.
- [ ] Validate tab server health and admin gateway health from the wizard finish flow.
- [ ] Validate extension connectivity signal (or explicit "not connected yet" warning with remediation).
- [ ] Update extension install copy with canonical Chrome/Edge store links and extension IDs from `extension_constants.py`.
- [ ] Update `INSTALL_WINDOWS.md` setup section to include the new validation gate and expected pass/fail outcomes.
- [ ] Update `MVP_SMOKE_TEST.md` to include "Setup Validation passes" before manual behavior checks.

## Implementation notes
- Keep failure handling non-destructive: setup should not silently succeed when required checks fail.
- Prefer explicit statuses: **Ready**, **Ready with warnings**, **Not ready**.
- If extension signal is unavailable, show a concrete remediation checklist instead of a generic error.

## Validation checklist
- [ ] Fresh local run reaches final setup page with explicit readiness status.
- [ ] Simulated service-down scenario shows actionable remediation.
- [ ] Extension-connected scenario is detectable and visible in UI text/state.
- [ ] Docs and UI wording are aligned.

## Files expected to change
- `focus_guard/gui/first_run_wizard.py`
- `focus_guard/deployment/runtime_startup.py` (if helper reuse is needed)
- `focus_guard/core/extension_constants.py` (only if constants are missing/unclear)
- `docs/planning/mvp/INSTALL_WINDOWS.md`
- `docs/planning/mvp/MVP_SMOKE_TEST.md`

## Exit criteria
Day 8 is done when setup completion includes a real readiness gate and extension-store onboarding is clear enough for a first-time operator without ad-hoc support.
