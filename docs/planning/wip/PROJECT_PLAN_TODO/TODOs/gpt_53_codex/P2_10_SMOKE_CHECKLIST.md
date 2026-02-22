# P2-10 Admin Gateway Smoke Checklist

## Preconditions
- Tab server is running (`http://127.0.0.1:8765`).
- Admin gateway is running on `http://127.0.0.1:3000`.
- Admin password is configured (via `focus-guard set-password`).

## Start command
```bash
python -m uvicorn focus_guard.core.admin_gateway.app:create_app --factory --host 127.0.0.1 --port 3000
```

## Smoke steps

1. Health check
   - `GET /admin/health`
   - Expect: `200` and `{ status, service, version }`.

2. Auth login
   - `POST /admin/api/v1/auth/login`
   - Body: `{ "username": "admin", "password": "<password>" }`
   - Expect: `200`, `token`, `expires_at`, `role=admin`.

3. Auth me
   - `GET /admin/api/v1/auth/me` with bearer token
   - Expect: `200`, `username`, `role`, `created_at`.

4. Dashboard
   - `GET /admin/api/v1/dashboard?device_id=<machine-name>`
   - Expect: `200` and keys: `device`, `focus_score`, `budget`, `blocks_today`, `overrides_today`.

5. Exceptions create/list/revoke
   - Create temporary:
     - `POST /admin/api/v1/exceptions`
     - Body: `{ "domain": "youtube.com", "type": "temporary", "duration_seconds": 300, "reason": "smoke" }`
     - Expect: `200` with `id`, `status`, `type`, `domain`.
   - List:
     - `GET /admin/api/v1/exceptions?status=all&limit=50&offset=0`
     - Expect: `200` with `exceptions`, `total`, `limit`, `offset`.
   - Revoke:
     - `DELETE /admin/api/v1/exceptions/{id}`
     - Expect: `200` with `{ revoked: true, id }`.

6. Devices list + enforcement mode
   - `GET /admin/api/v1/devices` with bearer token
   - Expect: `200` with `devices[0].id`, `status`, `enforcement_mode`, `browser_status.connected_browsers`.
   - `PUT /admin/api/v1/devices/{id}/enforcement`
   - Body: `{ "mode": "tracking", "password": "<password-if-required>" }`
   - Expect: `200` with `{ updated: true, mode: "tracking" }`.

7. Origin safeguards
   - `GET /admin/health` with disallowed `Origin`
   - Expect: `403` and structured `error.code=FORBIDDEN`.

8. SPA serving
   - `GET /admin`
   - Expect: SPA index when dist is configured/present.
   - `GET /admin/non-existent-client-route`
   - Expect: SPA index fallback.

## Exit criteria
- All steps above pass without manual code edits.
- No unhandled exceptions in gateway logs.
- Structured error model is returned on negative checks (missing auth/disallowed origin).
