# Focus Guard MVP Day 4 Execution Plan

## Day 4 Objective
Advance install/onboarding stream to a repeatable MVP path and reduce post-setup confusion.

## Tasks
- [x] Create canonical Windows MVP install doc.
- [x] Link install doc from top-level README.
- [x] Improve first-run wizard finish step with explicit Guardian Dashboard handoff.
- [x] Validate touched files and run regression smoke tests.
- [x] Continue install/onboarding stream with packaged runtime validation and service/startup verification checklist.

## Files Touched
- `docs/planning/mvp/INSTALL_WINDOWS.md`
- `README.md`
- `focus_guard/gui/first_run_wizard.py`
- `deployment/application/windows/scripts/build_exe.py`

## Validation
- [x] Lints for touched files (`first_run_wizard.py`, `README.md`, `INSTALL_WINDOWS.md`)
- [x] `pytest focus_guard/tests/core/test_reporting_and_override_regressions.py -q` (14 passed)
- [x] Runtime diagnostics command added to canonical startup verification checklist

## Notes
- Wizard now provides explicit local admin URL and a one-click **Open Guardian Dashboard** button.
- Install guide now defines a single MVP path (`python -m focus_guard.main`) and includes endpoint/smoke verification.

## Next Step
Proceed to Day 5 (`classification-improvements`) per sprint sequence.

