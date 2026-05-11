# Focus Guard MVP Day 9 Execution Plan

## Day 9 Objective
Define and implement the canonical admin-install + designated monitored-user machine model so deployment posture is explicit, secure, and repeatable.

## Workstream
- **C) Admin install + designated monitored-user model** (Week 2 required)

## Tasks
- [x] Document supported deployment posture in `INSTALL_WINDOWS.md`:
  - installer run by admin
  - monitored user privilege expectations
  - service/tray responsibility boundaries
  - known multi-session limits
- [x] Add deployment metadata fields (if needed) in `deployment/config.py` for install posture tracking.
- [x] Ensure installer/runtime code writes/reads posture fields safely (backward compatible defaults).
- [x] Add an operator checklist for "machine prepared correctly" before first run.
- [x] Add/adjust tests for config load/save compatibility when new fields are absent.

## Implementation notes
- Backward compatibility is mandatory for existing `deployment_config.json`.
- Avoid breaking existing install paths; this day is clarity + guardrail focused.
- If a true per-user enforcement guarantee is not currently feasible, document the limitation explicitly.

## Validation checklist
- [x] Existing installs still load config cleanly.
- [x] New installs persist posture metadata and show expected defaults.
- [x] Install docs reflect one unambiguous supported model.
- [x] Reviewer can answer "who installs?" and "who is monitored?" from docs alone.

## Files expected to change
- `focus_guard/deployment/config.py`
- `focus_guard/deployment/installer.py`
- `docs/planning/mvp/INSTALL_WINDOWS.md`
- Optional tests under deployment/config coverage

## Exit criteria
Day 9 is done when the machine-user model is explicit in both code/config and documentation, with no ambiguity for operators.
