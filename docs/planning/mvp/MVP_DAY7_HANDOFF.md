# MVP Day 7 Handoff

## Date

Sunday, May 3, 2026

## Objective

Technical MVP freeze / release-candidate labeling per `MVP_DAY7_EXECUTION_PLAN.md`, with manual `MVP_SMOKE_TEST.md` intentionally deferred.

## Release candidate label

- **Documented RC name:** `mvp-rc-2026-05-03` (use as a lightweight or annotated `git` tag on the commit you want to freeze).
- **Tag applied in this session:** No. The working tree had many uncommitted changes at handoff time; apply the tag on a **clean** commit after you capture the snapshot you want to call RC.

## Technical freeze criteria (declared met)

Per `MVP_DAY7_EXECUTION_PLAN.md`:

1. **Automated baseline:** Tier A + B green as recorded in `MVP_DAY6_HANDOFF.md` (`scripts/run_mvp_test_baseline.ps1` with HTTP smoke when services are up; `admin_ui` `npm run test:run` + `npm run build`).
2. **P0 policy:** No P0 defects intended for fix under this RC label; remaining risk is explicitly accepted via the manual-smoke deferral below.

## Manual smoke — deferred (waiver for strict Definition of Done)

Complete `MVP_SMOKE_TEST.md` later, or treat this waiver as satisfying the “recorded waiver” path in `MVP_SPRINT_MASTER_PLAN.md` for **technical freeze** only. **Full product sign-off** still benefits from running the checklist.

| Field | Value |
|-------|--------|
| **Deferred by** | Project maintainer |
| **Date** | Sunday, May 3, 2026 |
| **Reason** | Manual smoke deferred to a later window; Day 7 closed as an **engineering / RC** milestone first. |
| **Risk accepted** | Residual human-facing UX, extension, and install edge cases until `MVP_SMOKE_TEST.md` is executed. |
| **Revisit by** | Before any **strict** “fully smoke-signed MVP” or broader external release claim. |

## What shipped in MVP scope (summary)

- **Blocking / overrides:** Tab server reliability, override flow, blocking/feedback/LLM observability logs and tests as developed through Days 1–6.
- **Remote management:** Admin Gateway APIs; `admin_ui` settings, devices, and dashboard wired to real data.
- **Reporting:** Email reporter and dashboard metrics baseline.
- **Install / onboarding:** Windows install documentation and first-run wizard improvements.
- **Release readiness:** `MVP_TEST_MATRIX.md`, `scripts/mvp_smoke.ps1`, `scripts/run_mvp_test_baseline.ps1`; manual checklist in `MVP_SMOKE_TEST.md`.

## Deferred and parking lot

| Item | Disposition |
|------|-------------|
| `MVP_SMOKE_TEST.md` | **User follow-up** — run when convenient; not blocking technical freeze. |
| `python scripts/admin_gateway_smoke.py --password …` | **Not run** in this handoff session; optional — run locally and add a one-line result here if you want it on record. |
| **FR-014** (admin gateway test dedupe / pytest markers) | **Parked** — see `FEATURE_REQUESTS_PARKING_LOT.md`; not required for RC label. |

## Post-MVP pointers

- Backlog and wishes: `docs/planning/mvp/FEATURE_REQUESTS_PARKING_LOT.md`
- Broader themes (from sprint todos): optional central DB / export (`centralize-data-model`), HTTP remote config/decision service (`remote-config-decision-service`)

## Next actions (owner)

1. Commit the snapshot you want frozen, then: `git tag mvp-rc-2026-05-03` (or annotated equivalent) on that commit.
2. When ready, complete `docs/planning/mvp/MVP_SMOKE_TEST.md` and update this file or a short addendum with “manual smoke: pass / waivers.”
