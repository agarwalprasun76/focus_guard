# P4-07 Packaging Integration Runbook (Admin Gateway + SPA)

## Purpose
Validate that the packaged/runtime admin gateway serves the built Admin UI SPA at `/admin` while preserving backend API routing under `/admin/api/*`.

## Preconditions
- `admin_ui/dist` exists (build completed).
- Python environment can run admin gateway tests.
- (Optional for manual LAN verification) machine IP is known (e.g., `192.168.1.25`).

## 1) Build SPA Artifact

```bash
npm.cmd run build
```

Run from: `admin_ui/`

Expected:
- `admin_ui/dist/index.html` exists.
- `admin_ui/dist/assets/*` exists.
- `admin_ui/dist/index.html` asset links resolve under `/admin/assets/*` (not `/assets/*`).

## 2) Automated Packaging Integration Checks

Run from repo root:

```bash
python -m pytest focus_guard/tests/core/admin_gateway/test_admin_spa_serving.py -q
```

Coverage provided by this suite:
- default app serves real `admin_ui/dist` when present
- configured `admin_ui_dist_dir` serves `/admin` and `/admin/assets/*`
- client-route fallback (e.g., `/admin/exceptions/new`) serves SPA index
- reserved backend routes (`/admin/api*`, `/admin/health`) are not hijacked by SPA fallback

## 3) Manual Local Runtime Verification

Start gateway:

```bash
python -m uvicorn focus_guard.core.admin_gateway.app:create_app --factory --host 127.0.0.1 --port 58393
```

Check in browser/curl:
1. `GET http://127.0.0.1:58393/admin/health` -> `200` JSON health payload
2. `GET http://127.0.0.1:58393/admin` -> SPA index HTML
3. `GET http://127.0.0.1:58393/admin/dashboard` -> SPA index fallback
4. `GET http://127.0.0.1:58393/admin/api/v1/dashboard` -> backend API response (not SPA HTML)

Additional check:
- Open `admin_ui/dist/index.html` and confirm JS/CSS links are `/admin/assets/...`.

## 4) Manual LAN Runtime Verification

Start gateway bound to all interfaces:

```bash
python -m uvicorn focus_guard.core.admin_gateway.app:create_app --factory --host 0.0.0.0 --port 58393
```

From another device in the same LAN, verify:
- `http://<host-ip>:58393/admin` loads UI.
- `http://<host-ip>:58393/admin/health` returns health JSON.

If origin checks are enabled and browser access is blocked for LAN origin:
- Add LAN origin to `AdminGatewayConfig.additional_allowed_origins` in runtime configuration path, then restart gateway.
- Example origin format: `http://192.168.1.25:58393`.

## 5) Packaging Notes

- Gateway SPA resolution order:
  1. explicit `admin_ui_dist_dir` config path
  2. repo default `admin_ui/dist`
  3. fallback `focus_guard/admin_ui/dist`
- If none resolve, `/admin` is not mounted and returns 404.

## 6) I2 Deterministic Packaged-Lane Workflow

Use the packaged-lane workflow helper from repo root:

```bash
python scripts/dev/run_packaged_lane.py --dry-run
```

This prints deterministic steps in order:
1. Build admin UI
2. Export admin gateway OpenAPI schema snapshot
3. Build executable
4. Verify packaged runtime endpoints + asset links
5. Run packaged Playwright smoke

When runtime is started and ready, run the real check:

```bash
python scripts/dev/run_packaged_lane.py --runtime-base-url http://127.0.0.1:58393
```

## 7) Packaged Runtime Verification Commands

### HTTP startup verification script

```bash
python scripts/dev/verify_packaged_admin_runtime.py --base-url http://127.0.0.1:58393
```

Checks:
- `/admin/health` returns 200
- `/admin/api/v1/meta` returns 200 with `service=admin_gateway`
- `/admin/api/v1/dashboard` returns contract shape
- `/admin` HTML contains `/admin/assets/*` links

### Packaged Playwright smoke profile

```bash
npm.cmd run test:e2e:packaged:smoke
```

Uses `admin_ui/playwright.packaged.config.ts` and validates:
- `/admin` + core admin API endpoints
- exceptions mutation flow in packaged lane (create/list/revoke)

Credential/runtime prerequisites:
- `PACKAGED_ADMIN_BASE_URL` (default `http://127.0.0.1:58393`)
- `PACKAGED_ADMIN_USERNAME` (default `admin`)
- `PACKAGED_ADMIN_PASSWORD` (default `secret123`)

Example:

```bash
set PACKAGED_ADMIN_BASE_URL=http://127.0.0.1:58393
set PACKAGED_ADMIN_USERNAME=admin
set PACKAGED_ADMIN_PASSWORD=<configured-admin-password>
npm.cmd run test:e2e:packaged:smoke
```

## 8) Promotion Gate Rule (I2-04)

A candidate release is **blocked** if any of these fail:
- source lane tests
- packaged HTTP verification script
- packaged Playwright smoke profile

Promotion requires all three to pass on the same candidate build.

## Troubleshooting

### SPA loads but JS/CSS 404 from `/assets/*`

Symptom in gateway logs:
- `GET /admin` -> 200
- `GET /assets/index-*.js` -> 404

Cause:
- Admin UI build emitted root-relative asset paths (`/assets/*`) instead of `/admin/assets/*`.

Fix:
- Ensure Vite production build base is `/admin/` (configured in `admin_ui/vite.config.ts`).
- Rebuild:

```bash
npm.cmd run build
```

- Re-verify `admin_ui/dist/index.html` contains:
  - `<script ... src="/admin/assets/...">`
  - `<link ... href="/admin/assets/...">`

## Exit Criteria (P4-07 + I2)
- SPA build succeeds.
- SPA serving test suite passes.
- Local `/admin` + `/admin/api/*` coexistence verified.
- LAN admin access steps documented and reproducible.
- Packaged-lane verification script passes on runtime candidate.
- Packaged Playwright smoke passes on runtime candidate.
