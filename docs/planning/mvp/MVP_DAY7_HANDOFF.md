# MVP Day 7 Handoff

## Date

Sunday, May 3, 2026

## Objective

Technical MVP freeze / release-candidate labeling per `MVP_DAY7_EXECUTION_PLAN.md`, with manual `MVP_SMOKE_TEST.md` intentionally deferred.

## Release candidate label

- **RC identifier:** `mvp-rc-2026-05-03` (git tag + prior milestone commit message on an ancestor).
- **Frozen snapshot (current `main` + tag):** same commit as `mvp-rc-2026-05-03` (run `git rev-parse mvp-rc-2026-05-03` for the full SHA). That tip includes **redaction** of accidentally committed OpenAI-shaped strings and a **history rewrite** (`git filter-repo --replace-text`) so GitHub push protection can accept the ref.
- **Named `git` tag:** `mvp-rc-2026-05-03` → same commit as `main` above (updated after history rewrite).

### GitHub push protection (OpenAI key material)

If `git push origin mvp-rc-2026-05-03` failed with **GH013 / Push cannot contain secrets**, GitHub was scanning **reachable history** for OpenAI API key patterns (including old commits and commented-out lines).

**What was done in-repo:** (1) Remove literals from the current tree (env-only / empty config). (2) Run `git filter-repo --replace-text` to replace the two leaked `sk-proj-…` blobs **across all commits**, then **force-move** the tag to `main`.

**What you must do outside the repo:** If those strings were ever real keys, **revoke/rotate them in the OpenAI dashboard** immediately; treating them as compromised is the safe default.

**Sync to GitHub after a history rewrite** (rewrites all SHAs; coordinate with anyone else using this remote):

```powershell
git push --force-with-lease origin main
git push --force origin mvp-rc-2026-05-03
```

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

1. ~~Commit the RC snapshot~~ **Done** — see **Frozen snapshot** above.
2. **Push:** after the history scrub, use **force** pushes in the block under **GitHub push protection** (normal `git push` for the tag will keep failing until the remote accepts the new history).
3. When ready, complete `docs/planning/mvp/MVP_SMOKE_TEST.md` and update this file or a short addendum with “manual smoke: pass / waivers.”
