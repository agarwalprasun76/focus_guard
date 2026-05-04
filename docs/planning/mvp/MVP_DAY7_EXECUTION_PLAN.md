# Focus Guard MVP Day 7 Execution Plan

## Day 7 Objective
**Technical MVP freeze / release-candidate labeling** — close the sprint as an engineering milestone even when `MVP_SMOKE_TEST.md` is intentionally deferred.

## Prerequisite (flexible)

- **Minimum:** Automated Tier A + B green (`scripts/run_mvp_test_baseline.ps1`, `admin_ui` test + build) — already recorded in `MVP_DAY6_HANDOFF.md`.
- **Recommended before calling “fully signed MVP”:** complete `docs/planning/mvp/MVP_SMOKE_TEST.md`, **or** record a **dated waiver** below (stakeholder, reason, revisit date).

### Manual smoke waiver (fill only if deferring)

Filled in **`MVP_DAY7_HANDOFF.md`** (table + narrative). Summary:

- **Deferred by:** Project maintainer
- **Date:** Sunday, May 3, 2026
- **Reason:** Manual smoke time-boxed after engineering RC; internal / technical freeze first.
- **Risk accepted:** Residual UX/extension/install edge cases until `MVP_SMOKE_TEST.md` runs.
- **Revisit by:** Before strict “fully smoke-signed” MVP claim.

## Tasks

- [x] Choose label or tag (e.g. `mvp-rc-1`, date-based tag) and document it in `MVP_DAY7_HANDOFF.md`.
- [x] Update `MVP_SPRINT_MASTER_PLAN.md` execution tracker row **10** to **Done** once freeze criteria below are met.
- [x] One-page **`MVP_DAY7_HANDOFF.md`**: what shipped in MVP scope, what was deferred (manual smoke, parking-lot FRs), next priorities (post-MVP).
- [x] Triage open parking-lot items: confirm **FR-014** (gateway test dedupe) and any smoke-debt stay parked unless P0.
- [ ] (Optional) Run `python scripts/admin_gateway_smoke.py --password ...` and paste pass/fail summary into Day 7 handoff.

## Resume after sidetrack (Day 7 closure — May 2026)

Work that interrupted the original Day 7 narrative is **resolved**; treat the items below as the remaining **optional** checklist before you mentally “close the file” on Day 7.

| Item | Status |
|------|--------|
| GitHub push protection / history scrub for leaked `sk-proj-` test material | **Done** (see `MVP_DAY7_HANDOFF.md` § GitHub push protection) |
| `git` tag **`mvp-rc-2026-05-03`** on remote | **Done** (force-updated to current `main` / RC tip as you publish) |
| OpenAI: single-file secret + verifier (`api_token.json` + `scripts/verify_openai_key.py`, `OPENAI_API_KEY` precedence) | **Done** (see `INSTALL_WINDOWS.md`) |
| `git push origin main` in sync with local `main` (e.g. OpenAI feature commit) | **Owner** — run `git fetch` + `git push --force-with-lease origin main` if still ahead |
| `python scripts/admin_gateway_smoke.py --password …` | **Optional** — checkbox above; paste one-line result into `MVP_DAY7_HANDOFF.md` if you run it |
| `MVP_SMOKE_TEST.md` manual checklist | **Deferred** — for **strict** Definition of Done in `MVP_SPRINT_MASTER_PLAN.md`; not required for technical freeze |

**You are “back on track”** when: `main` (and tag, if used) match what you intend on GitHub, and any optional rows above are either done or consciously skipped.

## Definition of “technical freeze” (Day 7 without manual smoke)

You may declare **technical freeze** when:

1. `run_mvp_test_baseline.ps1` passes (with HTTP smoke when services are up, or `-SkipHttpSmoke` for CI-only with documented reason).
2. `admin_ui`: `npm run test:run` + `npm run build` pass.
3. No **P0** open defects you intend to fix in this tag (park others).

## Definition of “full MVP sign-off” (stricter)

Match `MVP_SPRINT_MASTER_PLAN.md` Definition of Done: complete **`MVP_SMOKE_TEST.md`** **or** attach the **waiver** block above in `MVP_DAY7_HANDOFF.md`.

## Files to touch

- `docs/planning/mvp/MVP_DAY7_HANDOFF.md` (new)
- `docs/planning/mvp/MVP_SPRINT_MASTER_PLAN.md` (tracker row 10)
- Optional: `README.md` one line “MVP RC” if you want public visibility
- Post-sidetrack (done): `focus_guard/core/program_data_paths.py`, `scripts/verify_openai_key.py`, `INSTALL_WINDOWS.md` (OpenAI + verify)

## Next step after Day 7

Post-MVP backlog: `FEATURE_REQUESTS_PARKING_LOT.md`, **FR-004+** roadmap items, `centralize-data-model` / `remote-config-decision-service` todos when you re-prioritize.
