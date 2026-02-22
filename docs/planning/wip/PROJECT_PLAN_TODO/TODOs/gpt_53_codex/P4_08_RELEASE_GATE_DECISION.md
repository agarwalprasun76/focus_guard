# P4-08 Release Gate Decision (Phase 1 Admin UX)

Date: 2026-02-14
Owner: Core
Decision: **GO** (for Phase 1 scope)

## Scope Reviewed
- P4-01 through P4-07 deliverables and validations.
- Release-gate acceptance criteria from `PHASE1_UX_TASK_BOARD.md`.

## Evidence Snapshot

### Frontend (Critical Flows + Sanity)
- `npm.cmd run test:e2e` (cwd `admin_ui`) -> **4 passed**
  - critical smoke (desktop + mobile)
  - performance sanity (desktop + mobile)

### Backend / Integration / Security / Packaging
- `python -m pytest focus_guard/tests/core/admin_gateway/test_agent_in_loop_real_tab_server.py focus_guard/tests/core/admin_gateway/test_auth_route_protection.py focus_guard/tests/core/admin_gateway/test_origin_safeguards.py focus_guard/tests/core/admin_gateway/test_performance_sanity.py focus_guard/tests/core/admin_gateway/test_admin_spa_serving.py -q` -> **18 passed**

## Acceptance Criteria Status
1. Critical Playwright flows pass (login, allow temp, revoke override): **PASS**
2. No high-severity auth/security defects open: **PASS** (P4-05 completed, targeted checks passing)
3. Known issues captured with severity and workaround: **PASS** (see Known Issues below)
4. Runbook updated for local + LAN admin access: **PASS** (`P4_07_PACKAGING_INTEGRATION_RUNBOOK.md`)

## Known Issues (Release Notes)

| Severity | Issue | Impact | Workaround / Resolution |
|---|---|---|---|
| Medium | SPA assets 404 (`/assets/*`) when SPA is mounted at `/admin` with root-relative build paths | Admin UI shell loads but JS/CSS fail, blank or broken UI | Fixed by setting Vite build base to `/admin/` in `admin_ui/vite.config.ts` and rebuilding `admin_ui/dist` |
| Low | Browser requests `/favicon.ico` by default | Benign 404 in logs | Optional: add favicon asset/route later; no functional impact |

## Go/No-Go Rationale
- All Phase 1 P4 engineering gates now have automated validation evidence.
- Security, performance, packaging integration, and critical UX flows are all passing in current environment.
- Remaining work is post-gate operational hardening/integration expansion, not a Phase 1 release blocker.

## Post-P4 Promotion Control (I2)
- Candidate promotion now requires **both** source-lane and packaged-lane checks.
- Packaged lane minimum gate:
  1. `python scripts/dev/verify_packaged_admin_runtime.py --base-url <runtime-url>` passes
  2. `npm.cmd run test:e2e:packaged:smoke` passes
- If either packaged check fails, release promotion is blocked pending fix + rerun.
