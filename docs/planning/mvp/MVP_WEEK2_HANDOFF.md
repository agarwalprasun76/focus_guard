# MVP Week 2 handoff (post–Day 7 engineering RC)

## Date

Sunday, May 10, 2026

## Purpose

Close **Week 2** workstreams from `MVP_SPRINT_MASTER_PLAN_Week2.md` with **documentation + code evidence** where automation exists, and **explicit human gates** where sign-off requires a live machine or external network.

## Workstream status (summary)

| Workstream | Status | Evidence / notes |
|------------|--------|-------------------|
| **A** Setup validation gate | **Done (implementation)** | `MVP_DAY8_EXECUTION_PLAN.md` tasks checked; wizard + health probes. **Human gate:** Day 8 plan § Validation checklist (fresh run / service-down simulation) — rerun on a dev PC before strict sign-off. |
| **B** Extension store flow hardening | **Done (implementation)** | Day 8: canonical store IDs + copy in wizard / `INSTALL_WINDOWS.md`. |
| **C** Admin install + monitored user | **Done** | Day 9: `deployment_config` posture fields, `INSTALL_WINDOWS.md` posture section, `test_deployment_config_posture.py`. |
| **D** Metrics historical access | **Done** | Day 10: UTC activity range queries, dashboard date alignment, `MVP_TEST_MATRIX.md` contract, integration tests under `focus_guard/tests/integration/tab_server/`. |
| **E** Remote admin architecture | **Done** | `ADR_001_REMOTE_ADMIN_ACCESS.md`; `INSTALL_WINDOWS.md` § Remote guardian access; `FOCUS_GUARD_ADMIN_*` env config (`focus_guard/core/admin_gateway/config.py`). |
| **F** Low-cost remote login runbook | **Done** | Day 12: `INSTALL_WINDOWS.md` § **Day 12 — Practical remote login runbook**; `MVP_SMOKE_TEST.md` § **J**; `scripts/admin_gateway_smoke.py --base-url`. |

## Operator-facing artifacts

- **Install + remote:** `docs/planning/mvp/INSTALL_WINDOWS.md`
- **Manual QA:** `docs/planning/mvp/MVP_SMOKE_TEST.md` (includes Week 2 remote + metrics spot sections)
- **Automated baseline:** `scripts/run_mvp_test_baseline.ps1`, `docs/planning/mvp/MVP_TEST_MATRIX.md` (Tier **E** lists `admin_gateway_smoke.py` with optional `--base-url` for tunnel checks)
- **Architecture:** `docs/planning/mvp/ADR_001_REMOTE_ADMIN_ACCESS.md`

## Deferred / follow-up (not silent)

| Topic | Where tracked |
|--------|----------------|
| Multi-guardian rule races (revision / 409) | **FR-029** |
| External IdP, audit trail, SPA base URL, TLS split-host, fleet plane | **FR-024**–**FR-028** |
| True multi-user Windows | **FR-023** |

## Optional command evidence (fill in when run)

```text
# Example: local gateway API smoke (does not replace browser remote test)
python scripts/admin_gateway_smoke.py --password "<ADMIN_PASSWORD>"
# Through tunnel:
python scripts/admin_gateway_smoke.py --password "<ADMIN_PASSWORD>" --base-url https://<your-hostname>
```

**Recorded in this session:** not executed here (no live tunnel or deployment password in CI). Paste one-line outcome when an operator runs it.

## Next actions

1. Run **`MVP_SMOKE_TEST.md`** end-to-end on a real install (local + § **J** if remote is deployed).
2. Keep **`MVP_SPRINT_MASTER_PLAN_Week2.md`** execution tracker as the live table; this file is the narrative handoff.
3. Continue product backlog from **`FEATURE_REQUESTS_PARKING_LOT.md`**.
