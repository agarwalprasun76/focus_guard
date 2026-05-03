# MVP test matrix (inventory + how to run)

This document **consolidates** MVP-relevant automated checks that were added across sprints (Day 1–6, admin gateway phase, Playwright, Python smoke helpers). Use it as the single index; keep one-off ideas in `FEATURE_REQUESTS_PARKING_LOT.md`.

## Principles

| Tier | When to run | Goal |
|------|----------------|------|
| **A — Baseline** | Every PR / before tag | Fast signal: tab server unit tests, admin gateway service tests, reporting regressions, HTTP smoke |
| **B — Guardian UI** | When `admin_ui/` changes | Vitest + production build |
| **C — Extended Python** | Nightly or weekly | Broader `focus_guard/tests/core` (slow; includes integration-style tests) |
| **D — E2E** | Release candidate | Playwright (needs app + env); packaged smoke variant |
| **E — Live helpers** | Manual with running app | `admin_gateway_smoke.py` (needs admin password) |

---

## Tier A — MVP baseline (recommended default)

Run all at once:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mvp_test_baseline.ps1
```

If the app is **not** running (CI / pytest only), skip HTTP probes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mvp_test_baseline.ps1 -SkipHttpSmoke
```

(`pwsh` works too if PowerShell 7 is installed.)

Or individually:

| Step | Command | What it covers |
|------|---------|----------------|
| A1 | `pwsh -File scripts/mvp_smoke.ps1` | Tab server + admin gateway HTTP probes (no auth body) |
| A2 | `pytest focus_guard/core/browser_v2/tab_server/tests -q` | Blocking pipeline, overrides, feedback logs, classification cache, LLM log, decision log |
| A3 | `pytest focus_guard/core/admin_gateway/tests -q` | Dashboard/settings/devices **service** unit tests (co-located with gateway) |
| A4 | `pytest focus_guard/tests/core/test_reporting_and_override_regressions.py -q` | Email reporting + override-related regressions |
| A5 | `pytest focus_guard/tests/core/admin_gateway/test_dashboard_service.py focus_guard/tests/core/admin_gateway/test_devices_service.py -q` | Same **service names** as A3 but under legacy tree `focus_guard/tests/core/admin_gateway/` (may overlap; `test_settings_service.py` exists only in `focus_guard/core/admin_gateway/tests/` and is covered by **A3**) |

**Note:** Dedupe long-term: prefer **one tree** for new gateway service tests (`focus_guard/core/admin_gateway/tests/`). Keep A5 only while both locations carry distinct assertions.

---

## Tier B — Admin UI (`admin_ui/`)

From `admin_ui/`:

| Step | Command | Notes |
|------|---------|--------|
| B1 | `npm run test:run` | Vitest unit + integration-style tests under `src/` |
| B2 | `npm run build` | Typecheck + Vite build |
| B3 | `npm run test:run -- src/api/dashboard.test.ts src/api/devices.test.ts src/api/exceptions.test.ts` | Fast API client subset |

---

## Tier C — Extended Python core (optional, slower)

```powershell
pytest focus_guard/tests/core -q --ignore=focus_guard/tests/core/integration
```

For full core including heavy paths, drop `--ignore` (expect minutes).

**High-signal subsets** (if you need to narrow):

- `pytest focus_guard/tests/core/admin_gateway -q`
- `pytest focus_guard/tests/integration -q` (longer; may need keys / network depending on tests)

---

## Tier D — Playwright E2E

Run from `admin_ui/` with browsers installed:

| Script | Command |
|--------|---------|
| Default e2e | `npm run test:e2e` |
| Packaged runtime | `npm run test:e2e:packaged` |
| Packaged smoke only | `npm run test:e2e:packaged:smoke` |

Specs of interest:

- `admin_ui/e2e/critical-smoke.spec.ts`
- `admin_ui/e2e/packaged-runtime-smoke.spec.ts`

---

## Tier E — Live smoke helpers (running stack)

| Helper | Command | Needs |
|--------|---------|--------|
| Admin gateway API walkthrough | `python scripts/admin_gateway_smoke.py --password <ADMIN_PASSWORD>` | App + gateway on `58393` |
| Tab + admin HTTP only | `scripts/mvp_smoke.ps1` | Tab server + gateway |

---

## Manual checklist (human gate)

`docs/planning/mvp/MVP_SMOKE_TEST.md` — browser, extension, and guardian flows not fully replaced by automation.

---

## Historical / duplicate checklists (reference only)

Do **not** treat these as the source of truth for CI; they captured context at a point in time:

- `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/P2_10_SMOKE_CHECKLIST.md`
- `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/PLAN_02152026_1536_MVP_EXECUTION_CHECKLIST.md`

If content there is still valid, **merge a bullet into `MVP_SMOKE_TEST.md`** then mark the wip doc superseded in its header (optional cleanup).

---

## Maintenance

- When adding a new MVP-critical test: **register it in Tier A or B** here and in `scripts/run_mvp_test_baseline.ps1` if it should gate releases.
- Prefer **one directory** for gateway service tests over time (`focus_guard/core/admin_gateway/tests/` vs `focus_guard/tests/core/admin_gateway/`) to reduce duplication (parking-lot hygiene).
