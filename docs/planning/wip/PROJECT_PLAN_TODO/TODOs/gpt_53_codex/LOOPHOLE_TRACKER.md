# Loophole Tracker (Post-P4)

## How to use
- Log only confirmed or strongly suspected loopholes.
- Keep entries concise but reproducible.
- Link each closure to a PR/commit/test.

## Severity Scale
- **S1 Critical**: security bypass, data loss, severe enforcement failure.
- **S2 High**: major flow broken for common users.
- **S3 Medium**: partial failure or confusing behavior with workaround.
- **S4 Low**: minor issue, cosmetic, or log noise.

## Reproducibility Scale
- **R3 High**: reproduces most runs.
- **R2 Medium**: intermittent but repeatable with pattern.
- **R1 Low**: rare/uncertain.

## Risk Score Rule (I6)
- Score each entry as: `SeverityWeight x ReproWeight x ImpactWeight`
- Severity weights: S1=4, S2=3, S3=2, S4=1
- Repro weights: R3=3, R2=2, R1=1
- Impact weight (operator judgement): 1-3
- Use Risk Score to maintain the Top-5 triage queue.

## Status
- `new` -> `triaged` -> `in_progress` -> `fixed` -> `verified` -> `closed`
- or `deferred` with rationale.

## Tracker Table

| ID | Date | Category | Severity | Repro | Risk Score | Environment | Trigger / Scenario | Expected | Actual | Impact | Hypothesis | Owner | Status | Mitigation / Fix | Test Added | Links |
|---|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|
| L-001 | 2026-02-14 | Packaging/runtime mismatch | S2 | R3 | 27 | Local packaged gateway | Open `/admin` after build emitted root asset paths | Admin UI loads with JS/CSS | `/assets/*` 404 while `/admin` is 200 | UI unusable in packaged route mount | Vite build base path mismatch | Backend/FE | closed | Fixed + verified by runtime verification and test coverage; no recurrence seen. | yes (`test_admin_spa_serving` + runtime verification) | `admin_ui/vite.config.ts`, `P4_07_PACKAGING_INTEGRATION_RUNBOOK.md`, `I6_BACKFILL_BASELINE.md` |
| L-002 | 2026-02-14 | Recovery/resilience gaps | S3 | R2 | 8 | Source lane dashboard polling | Transient upstream outage during dashboard auto-refresh | Clear degraded recovery hint appears promptly | Stale-snapshot message appears only after polling/retry cycle and can feel delayed | UX ambiguity during recovery window | Default polling cadence and retry timing are conservative for normal operation | FE/QA | deferred | Deferred in I6 cycle pending additional live-session evidence; revisit 2026-02-22. | yes (`admin_ui/e2e/resilience-recovery.spec.ts`) | `I4_PILOT_SESSION_RESULTS.md`, `admin_ui/src/views/DashboardPlaceholder.tsx`, `I6_BACKFILL_BASELINE.md` |
| L-003 | 2026-02-14 | Packaging/runtime mismatch | S2 | R3 | 27 | Packaged lane smoke | Candidate passes packaged shell/API smoke but mutation path not asserted | Packaged lane should include create/revoke mutation confidence checks | Mutation path now executes and passes in packaged smoke with authenticated create/list/revoke flow | Mutation confidence gap addressed; remaining operational choice is whether to keep split local ports (admin 58393 -> tab 58392) or align later | Packaged profile includes mutation assertions and now has green run evidence with valid credential env vars and routed runtime base URL | Core/QA | verified | Implemented mutation assertions, corrected runtime invocation (`npm --prefix admin_ui`), and validated green packaged smoke (4/4 pass) with `PACKAGED_ADMIN_*` env vars. Keep topology-alignment decision as separate follow-up. | yes (e2e packaged mutation smoke assertion added) | `admin_ui/e2e/packaged-runtime-smoke.spec.ts`, `P4_07_PACKAGING_INTEGRATION_RUNBOOK.md`, `PLAN_02152026_1536_MVP_EXECUTION_CHECKLIST.md`, `PROGRESS_TRACKER.md` |

## Triage Queue (Top 5)

| Priority | Loophole ID | Why now | Target sprint |
|---|---|---|---|
| 1 | L-002 | Deferred with dated follow-up; monitor for recurrence before tuning | I6 |
| 2 |  |  |  |
| 3 |  |  |  |
| 4 |  |  |  |
| 5 |  |  |  |

## Notes
- Prefer policy/rule improvements and model-assisted detection where recurring loopholes share patterns.
- Avoid overfitting one-off exception handlers unless risk is high.
