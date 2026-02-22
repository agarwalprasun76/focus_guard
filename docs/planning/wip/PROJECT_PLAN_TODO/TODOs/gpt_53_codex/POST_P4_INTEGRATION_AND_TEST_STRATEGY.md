# Post-P4 Integration and Testing Strategy (Frontend + Backend + Runtime)

**Execution Board:** `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/POST_P4_EXECUTION_TASK_BOARD.md`
**Progress Tracking:** `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/PROGRESS_TRACKER.md`
**Loopholes:** `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/LOOPHOLE_TRACKER.md`

## Purpose
Move from feature-complete Phase 1 to robust real-world integration quality, with automation-first testing and manual testing focused on edge cases.

## Core Principle
- **Automation proves baseline quality.**
- **Manual testing hunts unknown unknowns.**
- Human testing should not be the primary way we discover obvious regressions.

## Delivery Lanes (always-on)
1. **Source lane** (fast feedback): python + node dev/runtime.
2. **Packaged lane** (truth lane): rebuilt `.exe` + realistic machine workflow.

Source-only confidence is insufficient because packaging can introduce path/config/startup/runtime wiring issues.

---

## Implementation Order (Phased)

## Phase 0 - Foundations (contract and compatibility)

### 0.1 Single source of API truth
- Generate typed frontend models/client from backend OpenAPI where feasible.
- Keep one contract authority and remove duplicated hand-written shape drift.
- Add CI check: backend API schema changes must regenerate/update frontend types.

### 0.2 Compatibility matrix
- Define supported FE build vs BE version combinations.
- Add a lightweight backend capabilities/meta endpoint for frontend negotiation.
- Frontend should gate optional features by server capability, not assumptions.

### 0.3 Correlation IDs and structured telemetry
- Add request correlation ID (`X-Request-ID`) from frontend to backend.
- Include correlation ID in error envelopes/logs.
- Make frontend error surfaces show trace ID for faster bug triage.

### 0.4 Readiness and degraded-mode UX model
- Distinguish and expose states clearly:
  - admin gateway up/down
  - tab server up/down
  - enforcement active/degraded
- Add explicit UI status cards/messages + recovery actions.

---

## Phase 1 - Automated FE/BE integration coverage (Requested Category 1)

### Objective
Continuously validate frontend-to-gateway-to-tab-server behavior with minimal manual effort.

### Scope
- Auth: login/logout/me/refresh.
- Dashboard load + refresh behavior.
- Exceptions create/list/revoke.
- Devices read/update enforcement.
- Error handling for offline/upstream failures.
- CORS/origin protections.

### Test layers
1. **Contract tests (MSW)**
   - `admin_ui/src/integration/*.integration.test.ts` as API contract verification.
2. **Gateway integration tests (pytest)**
   - `focus_guard/tests/core/admin_gateway/*` with fake and real tab-server scenarios.
3. **End-to-end browser tests (Playwright)**
   - critical smoke + security/perf sanity.
4. **Cross-endpoint consistency assertions**
   - verify dashboard counters/state match exceptions/devices endpoint state after user actions.

### Must-pass command pack (PR gate)
```bash
python -m pytest focus_guard/tests/core/admin_gateway/test_auth_route_protection.py focus_guard/tests/core/admin_gateway/test_origin_safeguards.py focus_guard/tests/core/admin_gateway/test_admin_spa_serving.py -q
npm.cmd run test:integration
npm.cmd run test:e2e -- e2e/critical-smoke.spec.ts
```

### Nightly command pack
```bash
python -m pytest focus_guard/tests/core/admin_gateway -q
npm.cmd run test:integration
npm.cmd run test:e2e
```

---

## Phase 2 - Packaged lane hardening (.exe) and promotion rules

### Objective
Guarantee packaged behavior matches source-lane behavior before release promotion.

### Workflow
1. Build frontend artifact:
```bash
npm.cmd run build
```
2. Build executable(s) using packaging path.
3. Start runtime via `.exe` entry.
4. Run packaged smoke suite:
   - `/admin/health`, `/admin`, dashboard load, exception lifecycle.
5. Run a packaged Playwright smoke profile.

### CI/CD integration
- Add packaged-lane test stage to release pipeline.
- No candidate promotion unless **source lane + packaged lane** pass.

---

## Phase 3 - Resilience and fault injection

### Objective
Ensure stable user experience under real-world failures and degraded dependencies.

### Additions
1. Fault injection between gateway and tab server:
   - latency spikes
   - timeouts
   - intermittent connection resets
2. Assert frontend recovery behavior:
   - retry/backoff works
   - status/degraded messaging remains accurate
   - no stale misleading success state
3. Add long-session drift checks:
   - state refresh consistency over multi-hour runs.

---

## Phase 4 - Human-in-loop validation (Requested Categories 2 and 3)

## 2) Manual tests by a user using the frontend

### Objective
Validate UX correctness and practical usability where strict automation is weaker.

### Test charter
- First-login flow and error messages.
- Dashboard interpretation clarity.
- Exception creation UX (temporary/permanent/budgeted/block).
- Revoke flow confidence (clear status transitions).
- Mobile behavior and responsiveness.
- Session expiry and re-login behavior.

### Cadence
- 30-45 min scripted exploratory session per release candidate.
- Use one checklist and log only meaningful UX/behavior anomalies.

### Output
- Findings go into `LOOPHOLE_TRACKER.md` with repro + impact + expected behavior.

## 3) Manual testing when user is working/getting distracted

### Objective
Validate behavior under realistic live usage conditions (the "mouse trap" conditions).

### Scenarios
1. Focus session with no distractions.
2. Repeated distracting site visits.
3. Temporary allow override then revoke.
4. Browser closed/reopened while rules active.
5. Short network interruptions.
6. Multi-hour run stability.

### Data to capture
- Timeline: event timestamps and user actions.
- Observed enforcement behavior vs expected policy.
- Any lag, stale state, or mismatch between frontend and runtime reality.

### Session protocol
- 60-90 min session.
- Keep one observer log template (time/action/expected/actual).
- Convert findings into loopholes with severity and reproducibility score.

---

## Phase 5 - Automated live-behavior simulation (Requested Category 4)

### Objective
Model user behavior and stress policy enforcement without requiring a human each run.

### Plan
1. Build a distraction simulation harness that can:
   - trigger domain visit/event sequences
   - trigger override request/revoke patterns
   - inject delay/offline/timeout conditions
2. Validate expected outcomes via APIs:
   - dashboard counters, active overrides, enforcement mode, audit log
3. Add deterministic fixtures for repeatability.
4. Add random-but-bounded chaos mode for nightly runs.

### Initial automated scenario pack
- `scenario_focus_stable`
- `scenario_repeated_distraction`
- `scenario_override_lifecycle`
- `scenario_offline_recovery`
- `scenario_long_session_stability`

---

## Phase 6 - Loophole management and AI/rule evolution

## Goal
Capture loopholes without drowning in exception handling noise.

## Rules
1. Every loophole must include: repro, impact, frequency, and likely root cause.
2. Prioritize by **risk score**: `severity x reproducibility x user impact`.
3. Fix top-risk items first; defer low/noise edge cases with explicit rationale.
4. Prefer policy/rule improvements and learning-based heuristics over brittle one-off patches.

## Loophole categories
- Enforcement bypass
- State sync mismatch
- UX confusion/unsafe defaults
- Performance degradation
- Packaging/runtime mismatch
- Recovery/resilience gaps

## AI/Learning rollout (incremental)
1. Add feature flags for smart policy rules in **shadow mode** first.
2. Log model/rule suggestions without immediate enforcement.
3. Evaluate precision/false-positive rate against loophole data.
4. Promote to active policy only after threshold criteria are met.

---

## Proposed 2-Week Execution Plan

## Week 1 (foundation + packaged lane)
- Implement Phase 0 contract/compatibility/telemetry foundations.
- Stand up packaged lane smoke flow in repeatable script form.
- Add cross-endpoint consistency checks for core workflows.
- Backfill known issues in `LOOPHOLE_TRACKER.md` and rank top 5.

## Week 2 (resilience + simulation + triage)
- Add fault injection tests and degraded-mode assertions.
- Implement distraction simulation harness v1.
- Run manual live-distraction sessions + nightly automation.
- Triage loopholes and ship highest-risk fixes.
- Start shadow-mode AI/rule suggestion logging.

---

## Exit Criteria for this post-P4 cycle
- Automated integration lane covers all critical user flows.
- Packaged lane is reproducible and part of release checks.
- Readiness/degraded states are visible and actionable in UI.
- Manual testing primarily finds edge cases, not baseline regressions.
- Loophole tracker is active, prioritized, and linked to fixes.
- At least one AI/rule improvement runs in shadow mode with tracked precision.
