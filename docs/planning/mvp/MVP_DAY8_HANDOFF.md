# MVP Day 8 Handoff

## Date

Saturday, May 10, 2026

## Objective

Deliver **setup validation in the first-run wizard** and clearer **extension store onboarding**, per `MVP_DAY8_EXECUTION_PLAN.md` and Week 2 streams A + B (phase 1).

## What shipped

1. **Finish-page Setup Validation** (`focus_guard/gui/first_run_wizard.py`)
   - States: **Ready**, **Ready with warnings**, **Not ready** (blocking issues block finish; warnings confirm to continue).
   - Checks: extension install confirmation checkbox, tab server `GET /api/health`, admin `GET …/admin/health`, **`GET /api/status`** for a connected browser, **`GET /api/auth/status`** for `token_exists`.
   - **Ready with warnings** when the extension is “installed” per checkbox but **`/api/status` shows no connected browser** — remediation text tells the operator to open Chrome/Edge, enable the extension, load a tab, then re-run validation.

2. **First-run bootstrap ordering** (`focus_guard/main.py`)
   - On **first launch only**, the tab server and admin gateway start **before** the wizard so health and status probes work during Finish-page validation.
   - If the user **cancels** the wizard, those bootstrap threads are torn down before the normal startup path runs (no duplicate listeners).
   - If the configured tab-server port was busy during bootstrap, host/port fallback is **`_persist_tab_server_endpoint` after a successful wizard** so `deployment_config.json` matches the live listener.

3. **Extension onboarding copy**
   - Store buttons use `CHROME_STORE_URL` / `EDGE_STORE_URL`; IDs on the page use `CHROME_EXTENSION_ID` / `EDGE_EXTENSION_ID` from `extension_constants.py`.

4. **Docs**
   - `INSTALL_WINDOWS.md`: first-launch service bootstrap note; validation behavior summary.
   - `MVP_SMOKE_TEST.md`: precondition that Setup Validation is not **Not ready** (already aligned in tree).
   - `MVP_DAY8_EXECUTION_PLAN.md`: task checkboxes marked complete; `main.py` added to “files expected to change.”

## Follow-up for the owner (quick manual pass)

Run once on a clean profile (or temporary `deployment_config.json` rename) and tick the **Validation checklist** in `MVP_DAY8_EXECUTION_PLAN.md`:

- Final page shows expected readiness states.
- With services stopped or ports blocked, remediation text is actionable.
- With extension installed and a tab open, `/api/status` drives **Ready** or drops the “not connected” warning as appropriate.

## Parking lot / later

- **FR-015** — store release automation (CI packaging) remains parked.
- **Day 9+** — further Week 2 items (multi-admin model, metrics range API depth, remote access hardening) per `MVP_SPRINT_MASTER_PLAN_Week2.md`.

## Next actions

1. Execute the short manual validation above; update this handoff or the Day 8 plan checklist when done.
2. Proceed to **`MVP_DAY9_EXECUTION_PLAN.md`** (or the next open day in the Week 2 table).
