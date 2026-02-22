# I6-02 Loophole Backfill Baseline

Date: 2026-02-15

## Scope
Backfilled loopholes from recent post-P4 sessions, pilot manual runs, and simulation artifacts.

## Source Evidence
- `I4_PILOT_SESSION_RESULTS.md`
- `I5_SIMULATION_LOPHOLE_CANDIDATES.md`
- `P4_07_PACKAGING_INTEGRATION_RUNBOOK.md`
- `admin_ui/e2e/resilience-recovery.spec.ts`
- `admin_ui/e2e/packaged-runtime-smoke.spec.ts`

## Seeded Baseline

| Loophole ID | Summary | Current Status | Rationale | Next Review |
|---|---|---|---|---|
| L-001 | `/admin` asset mount mismatch in packaged runtime | closed | Fix verified by tests and runtime verification; no recurrence observed. | Closed |
| L-002 | Recovery stale-message visibility delay under normal polling cadence | deferred | UX clarity issue with workaround; no baseline breakage; defer until additional live-session evidence shows user impact trend. | 2026-02-22 |
| L-003 | Packaged lane mutation confidence gap (create/revoke not in packaged smoke) | deferred | Release confidence risk acknowledged; deferred with explicit follow-up to extend packaged mutation assertions in next packaging-hardening pass. | 2026-02-20 |

## Notes
- Deferrals were chosen to keep focus on highest-release-risk automation additions while preserving explicit revisit dates.
- Any deterministic simulation regression will bypass deferral and be triaged immediately.
