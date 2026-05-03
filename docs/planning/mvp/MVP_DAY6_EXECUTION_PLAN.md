# Focus Guard MVP Day 6 Execution Plan

## Day 6 Objective
Close the **MVP Smoke + Release Readiness** gap from `MVP_SPRINT_MASTER_PLAN.md` (workstream E): a repeatable manual checklist plus a minimal automated smoke probe, then burn only P0 blockers found during that pass.

## Relationship to master plan
The master plan’s 10-day sequence already covered reporting, install, and wizard in earlier execution tracks. **Day 6 here = sequence items 9–10** (smoke automation + blocker burn, then freeze prep), not a repeat of reporting/install days.

## Tasks
- [x] Add `docs/planning/mvp/MVP_SMOKE_TEST.md` — ordered checklist aligned with Definition of Done.
- [x] Add `scripts/mvp_smoke.ps1` — non-destructive HTTP checks (tab server health, admin gateway health/meta) with clear pass/fail output.
- [x] Run automated smoke script once (app running); fix script or docs if environment gaps.
- [x] Run guardian-relevant automated tests (tab_server + admin_gateway slices); log results in validation section below.
- [x] Run `admin_ui` Tier B: `npm run test:run` + `npm run build`.
- [x] Create `MVP_DAY6_HANDOFF.md` with outcomes and explicit “MVP freeze” go/no-go notes.
- [x] Consolidate MVP-related automated tests into `MVP_TEST_MATRIX.md` + `run_mvp_test_baseline.ps1`; cross-link from `MVP_SMOKE_TEST.md`.
- [ ] Manual: complete every section in `MVP_SMOKE_TEST.md` once (guardian-owned; not automatable here).

## Files to touch
- `docs/planning/mvp/MVP_SMOKE_TEST.md` (new)
- `docs/planning/mvp/MVP_TEST_MATRIX.md` (test inventory + tiers)
- `scripts/mvp_smoke.ps1` (new)
- `scripts/run_mvp_test_baseline.ps1` (Tier A runner)
- `docs/planning/mvp/MVP_SPRINT_MASTER_PLAN.md` (tracker update when Day 6 completes)
- `docs/planning/mvp/MVP_DAY6_HANDOFF.md` (new, end of day)

## Validation log
- [x] `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/mvp_smoke.ps1` — **passed** (tab `/api/health`, `/api/auth/status`, admin `/admin/health`, `/admin/api/v1/meta` all HTTP 200)
- [x] `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mvp_test_baseline.ps1 -SkipHttpSmoke` — **passed** (71 + 11 + 14 + 7 pytest tests)
- [x] `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mvp_test_baseline.ps1` (full Tier A **with** HTTP smoke, services up) — **passed** (same pytest counts as above)
- [x] `tab_server/tests` + admin gateway slices — **covered** by baseline A2–A5 (includes `test_override_flow` inside the 71)
- [x] `admin_ui`: `npm run test:run` — **17 passed** (6 files); `npm run build` — **success**
- [ ] Manual: complete every section in `MVP_SMOKE_TEST.md` once (guardian checklist)

## Deferring manual smoke (explicit policy)

**You do not have to finish `MVP_SMOKE_TEST.md` before starting Day 7.** The manual checklist is the **human / guardian** gate: it catches extension UX, real blocking in the browser, and “feels right” flows that automation does not fully replace.

| Path | Meaning |
|------|--------|
| **Day 7 now (technical freeze)** | OK: automated Tier A + B already green; you accept **residual risk** until manual smoke is done later. Label the outcome e.g. **“RC / technical freeze — manual smoke pending”** in `MVP_DAY7` handoff. |
| **Full MVP sign-off (Definition of Done)** | Per `MVP_SPRINT_MASTER_PLAN.md`, “MVP smoke checklist passes end-to-end” means **either** complete `MVP_SMOKE_TEST.md` **or** record a **dated waiver** in `MVP_DAY7_HANDOFF.md` (who/when/why) if you intentionally ship or tag without it. |

If you defer manual smoke: leave the checkbox below **unchecked**, add one line to `MVP_DAY6_HANDOFF.md` under **Deferred**, and proceed to `MVP_DAY7_EXECUTION_PLAN.md`.

## Next step after Day 6
Day 7: **`MVP_DAY7_EXECUTION_PLAN.md`** — technical freeze / RC labeling; complete manual smoke when ready (same checklist file).
