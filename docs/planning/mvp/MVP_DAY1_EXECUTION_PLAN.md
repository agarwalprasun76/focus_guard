# Focus Guard MVP Day 1 Execution Plan

## Day 1 Objective
Stabilize blocking/override behavior and lock expected behavior with tests.

## Priority
Highest. No dashboard/settings work until this is green.

## Tasks

1) Reproduce and baseline failures
- Run:
  - `pytest focus_guard/core/browser_v2/tab_server/tests/test_override_flow.py -q`
- Capture failing tests and exact assertions.

2) Fix override/session counting contract
- Ensure:
  - Granting override does not increment daily usage count.
  - First actual usage increments exactly once.
  - Reopen within same override does not double count.
  - Session active detection short-circuits duplicate starts.

Files to touch:
- `focus_guard/core/browser_v2/tab_server/override_manager.py`
- `focus_guard/core/browser_v2/tab_server/domain_usage_tracker.py` (only if needed)

3) Add/adjust targeted regression coverage
- Update/add tests for:
  - no increment on grant
  - increment on first usage
  - no increment on reopen same override
  - active session duplicate start handling

Files to touch:
- `focus_guard/core/browser_v2/tab_server/tests/test_override_flow.py`
- optional: `focus_guard/core/browser_v2/tab_server/tests/test_override_regressions.py`

4) Validate full tab_server subset
- Run:
  - `pytest focus_guard/core/browser_v2/tab_server/tests/test_override_flow.py -q`
  - `pytest focus_guard/core/browser_v2/tab_server/tests -q`

5) End-of-day handoff note
- Record:
  - what changed
  - tests run + status
  - open blockers
  - first task for Day 2

## Day 1 Definition of Done
- `test_override_flow.py` green
- No flaky reopen/multi-session override behavior
- Behavior contract captured in tests (not only implementation assumptions)
- Short handoff note written

## Tracker (Day 1)

### Planned
- [x] Reproduce failures in override flow suite
- [x] Implement override/session count fixes
- [x] Add regression tests for reopen and duplicate starts
- [x] Run focused + broader tab_server tests
- [x] Write day-end handoff note

### Touched Files
- [x] `focus_guard/core/browser_v2/tab_server/override_manager.py`
- [ ] `focus_guard/core/browser_v2/tab_server/domain_usage_tracker.py` (if required)
- [x] `focus_guard/core/browser_v2/tab_server/tests/test_override_flow.py`
- [ ] `focus_guard/core/browser_v2/tab_server/tests/test_override_regressions.py` (optional)

### Test Log
- [x] `pytest focus_guard/core/browser_v2/tab_server/tests/test_override_flow.py -q` (17 passed)
- [x] `pytest focus_guard/core/browser_v2/tab_server/tests -q` (67 passed)

### Blockers (90-minute rule)
- Blocker: None
- Decision: Proceed to Day 2.

### Post-MVP Backlog (Do Not Execute Today)
- Item:

### Next First Task (Day 2)
- Start Admin Gateway settings endpoint completion.

### Day 1 Handoff
- Result: Day 1 complete; override/session behavior validated against focused and broader `tab_server` tests.
- Notes: `pytest-asyncio` deprecation warning observed (`asyncio_default_fixture_loop_scope` unset), non-blocking for MVP but should be cleaned up in tooling config later.

