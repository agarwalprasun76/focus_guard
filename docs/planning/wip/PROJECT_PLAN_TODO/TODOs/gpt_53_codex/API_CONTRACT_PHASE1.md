# FocusGuard Admin UX — API Contract (Phase 1)

**Version:** v1.0-phase1  
**Date:** 2026-02-14  
**Status:** Draft for implementation (P1-02)  
**Base Path:** `/admin/api/v1`

---

## 1) Purpose and Scope

This contract defines the **Phase 1** API for the parent/accountability admin interface.

### In Scope (Phase 1)
1. Admin authentication (single admin account)
2. Dashboard aggregation (single-device MVP)
3. Exception/override actions (temporary, permanent, budgeted)
4. Active/history exception listing and revoke
5. Device status (single-device response shape, list-ready)

### Out of Scope (Phase 1)
- Role-based access control (partner/read-only)
- Multi-device orchestration/queuing for offline devices
- WebSocket live updates
- Policy version history/rollback APIs
- Advanced reports API (weekly/monthly deep analytics)

---

## 2) Transport, Auth, and Conventions

## 2.1 Protocol
- HTTP/1.1 JSON over REST
- UTF-8 JSON payloads
- `Content-Type: application/json`

## 2.2 Authentication
- JWT Bearer auth for protected endpoints.
- Header format:
  - `Authorization: Bearer <token>`
- Unauthenticated requests to protected endpoints return `401`.

## 2.3 Time and IDs
- All timestamps are ISO 8601 UTC (`YYYY-MM-DDTHH:mm:ssZ`).
- `device_id` for Phase 1 defaults to machine name from deployment config.
- Exception IDs are gateway-generated (`exc_<uuid>`).

## 2.4 Pagination and Filtering
- `limit` default `50`, max `200`
- `offset` default `0`
- list responses include `total`

## 2.5 Idempotency
- `PUT` endpoints are idempotent.
- `DELETE` endpoints are idempotent.
- `POST /exceptions` accepts optional `Idempotency-Key` header:
  - Same key + same normalized payload within 5 seconds returns the first created result.

---

## 3) Error Model

All non-2xx errors return:

```json
{
  "error": {
    "code": "DEVICE_OFFLINE",
    "message": "Device prasun-pc is not reachable",
    "details": { "last_seen": "2026-02-14T20:30:00Z" },
    "retry_after_seconds": 30
  }
}
```

### Standard Codes (Phase 1)
- `UNAUTHORIZED` (401)
- `FORBIDDEN` (403)
- `VALIDATION_ERROR` (400)
- `NOT_FOUND` (404)
- `CONFLICT` (409)
- `DEVICE_OFFLINE` (409)
- `UPSTREAM_ERROR` (502)
- `INTERNAL_ERROR` (500)

### Error Translation Rules
- Tab server timeout/unreachable -> `DEVICE_OFFLINE` (409) when device-scoped action.
- Tab server 4xx validation -> `VALIDATION_ERROR` (400).
- Tab server unknown 5xx -> `UPSTREAM_ERROR` (502).

---

## 4) Endpoint Catalog (Phase 1)

## 4.1 Auth

### POST `/auth/login`
Authenticate admin user.

Request:
```json
{
  "username": "admin",
  "password": "<plain-password>"
}
```

Response `200`:
```json
{
  "token": "<jwt>",
  "expires_at": "2026-02-14T22:00:00Z",
  "role": "admin"
}
```

Errors: `UNAUTHORIZED`, `VALIDATION_ERROR`

---

### POST `/auth/refresh`
Refresh active token.

Request:
```json
{
  "token": "<jwt>"
}
```

Response `200`:
```json
{
  "token": "<new-jwt>",
  "expires_at": "2026-02-14T23:00:00Z"
}
```

Errors: `UNAUTHORIZED`, `VALIDATION_ERROR`

---

### POST `/auth/logout`
Invalidate current session token (or mark revoked in server-side token store).

Response `200`:
```json
{
  "success": true
}
```

Errors: none (logout should be safe-idempotent)

---

### GET `/auth/me`
Return current authenticated identity.

Response `200`:
```json
{
  "username": "admin",
  "role": "admin",
  "created_at": "2026-02-10T19:15:00Z"
}
```

Errors: `UNAUTHORIZED`

---

## 4.2 Dashboard

### GET `/dashboard?device_id=<id>`
Aggregated summary for the main dashboard.

Response `200`:
```json
{
  "device": {
    "id": "prasun-pc",
    "name": "prasun-pc",
    "status": "online",
    "enforcement_mode": "enforcing",
    "last_seen": "2026-02-14T21:50:00Z"
  },
  "focus_score": 82,
  "budget": {
    "used_seconds": 1800,
    "total_seconds": 2700,
    "percent": 66.7
  },
  "blocks_today": 15,
  "overrides_today": 5,
  "attention_items": [
    {
      "type": "frequent_override",
      "domain": "youtube.com",
      "count": 3,
      "suggestion": "promote_to_rule"
    }
  ],
  "recent_overrides": [
    {
      "id": "exc_63c18d35",
      "domain": "youtube.com",
      "status": "active",
      "expires_at": "2026-02-14T22:05:00Z",
      "remaining_seconds": 231
    }
  ],
  "top_friction": [
    {
      "domain": "youtube.com",
      "override_count": 6,
      "time_used_seconds": 1420
    }
  ]
}
```

Errors: `UNAUTHORIZED`, `DEVICE_OFFLINE`, `UPSTREAM_ERROR`

---

## 4.3 Exceptions / Overrides

### POST `/exceptions`
Create admin action to allow/block via one unified endpoint.

Request:
```json
{
  "device_id": "prasun-pc",
  "domain": "youtube.com",
  "type": "temporary",
  "duration_seconds": 300,
  "budget_seconds_per_day": null,
  "reason": "homework video",
  "emergency": false
}
```

`type` allowed values:
- `temporary` -> create override for `duration_seconds`
- `permanent` -> add domain to always-allowed whitelist
- `budgeted` -> set per-domain budget (`budget_seconds_per_day` required)
- `block` -> create explicit block rule (Phase 1 convenience type)

Response `200`:
```json
{
  "id": "exc_63c18d35",
  "status": "active",
  "type": "temporary",
  "domain": "youtube.com",
  "expires_at": "2026-02-14T22:05:00Z",
  "audit_event_id": "evt_90ca6ed9"
}
```

Errors: `UNAUTHORIZED`, `VALIDATION_ERROR`, `DEVICE_OFFLINE`, `CONFLICT`

---

### GET `/exceptions?device_id=<id>&status=active|expired|all&domain=<domain>&limit=50&offset=0`
List exception history and active entries.

Response `200`:
```json
{
  "exceptions": [
    {
      "id": "exc_63c18d35",
      "domain": "youtube.com",
      "type": "temporary",
      "status": "active",
      "created_at": "2026-02-14T22:00:00Z",
      "expires_at": "2026-02-14T22:05:00Z",
      "remaining_seconds": 240,
      "reason": "homework video",
      "emergency": false
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

Errors: `UNAUTHORIZED`, `DEVICE_OFFLINE`

---

### DELETE `/exceptions/{id}?device_id=<id>`
Revoke active exception/override.

Response `200`:
```json
{
  "revoked": true,
  "id": "exc_63c18d35"
}
```

If already revoked/expired/non-existent in Phase 1, still return `200` with `revoked: true` for idempotency.

Errors: `UNAUTHORIZED`, `DEVICE_OFFLINE`

---

## 4.4 Devices

### GET `/devices`
Single-device MVP shape, list-ready for future expansion.

Response `200`:
```json
{
  "devices": [
    {
      "id": "prasun-pc",
      "name": "prasun-pc",
      "status": "online",
      "enforcement_mode": "enforcing",
      "last_seen": "2026-02-14T21:50:00Z",
      "browser_status": {
        "connected_browsers": 2
      }
    }
  ]
}
```

Errors: `UNAUTHORIZED`, `UPSTREAM_ERROR`

---

### PUT `/devices/{id}/enforcement`
Set enforcement mode.

Request:
```json
{
  "mode": "tracking",
  "password": "<optional-required-if-configured>"
}
```

Response `200`:
```json
{
  "updated": true,
  "mode": "tracking"
}
```

Errors: `UNAUTHORIZED`, `FORBIDDEN`, `VALIDATION_ERROR`, `DEVICE_OFFLINE`

---

## 5) Data Schemas (Canonical)

## 5.1 Enums

### `EnforcementMode`
- `tracking`
- `advisory`
- `enforcing`

### `ExceptionType`
- `temporary`
- `permanent`
- `budgeted`
- `block`

### `ExceptionStatus`
- `active`
- `expired`
- `revoked`

### `DeviceStatus`
- `online`
- `offline`

---

## 5.2 Core Objects

### `DeviceSummary`
```json
{
  "id": "string",
  "name": "string",
  "status": "online|offline",
  "enforcement_mode": "tracking|advisory|enforcing",
  "last_seen": "ISO8601",
  "browser_status": { "connected_browsers": 0 }
}
```

### `ExceptionRecord`
```json
{
  "id": "string",
  "domain": "string",
  "type": "temporary|permanent|budgeted|block",
  "status": "active|expired|revoked",
  "created_at": "ISO8601",
  "expires_at": "ISO8601|null",
  "remaining_seconds": 0,
  "reason": "string|null",
  "emergency": false,
  "audit_event_id": "string|null"
}
```

### `AttentionItem`
```json
{
  "type": "frequent_override|uncategorized|budget_warning|device_offline",
  "domain": "string|null",
  "count": 0,
  "suggestion": "string"
}
```

---

## 6) Upstream Mapping (Admin Gateway -> Tab Server)

| Admin Endpoint | Tab Server Calls |
|---|---|
| `GET /dashboard` | `GET /api/health`, `GET /api/distraction/budget`, `GET /api/distraction/sites`, `GET /api/override/stats`, `GET /api/override/log?limit=10` |
| `POST /exceptions` (`temporary`) | `POST /api/override` |
| `POST /exceptions` (`permanent`) | `POST /api/domains/whitelist` |
| `POST /exceptions` (`budgeted`) | `POST /api/domains/budgets/domain` |
| `POST /exceptions` (`block`) | `POST /api/should_block/rules` |
| `GET /exceptions` | `GET /api/override/active`, `GET /api/override/log` |
| `DELETE /exceptions/{id}` | `POST /api/override/revoke` |
| `GET /devices` | `GET /api/health`, `GET /api/status`, `GET /api/enforcement_mode` |
| `PUT /devices/{id}/enforcement` | `POST /api/enforcement_mode` |

---

## 7) Validation Rules

### Domain
- Required for exception creation.
- Lowercased and normalized before persistence.

### Temporary exception
- `duration_seconds` required and must be `> 0`.

### Budgeted exception
- `budget_seconds_per_day` required and must be `>= 0`.

### Block action
- `duration_seconds` and `budget_seconds_per_day` must be null/omitted.

### Enforcement mode
- Mode must be one of `tracking|advisory|enforcing`.
- Password required when enforcement password is configured upstream.

---

## 8) Security and Audit Requirements

1. All mutation endpoints require JWT auth.
2. Gateway must never expose tab-server bearer token values.
3. Every mutation must create or propagate auditable event metadata:
   - actor (`admin`)
   - action (`admin_allow`, `admin_block`, `override_revoked`, `rule_changed`, `enforcement_mode_changed`)
   - target domain/device
   - reason (if provided)
4. CORS must be explicit and configuration-driven (no wildcard in production).

---

## 9) Non-Functional Contract (Phase 1)

- Dashboard p95 latency target: <= 700ms on localhost, <= 1500ms over LAN.
- Mutation API p95 latency target: <= 500ms excluding upstream timeout.
- Gateway timeout for upstream tab-server calls: 5 seconds default.
- Retries: none for mutation calls; one safe retry for read calls allowed.

---

## 10) Open Questions (to close before implementation lock)

1. Should `POST /exceptions` support `category` actions in Phase 1 or defer to Phase 2 rules editor?
2. Should `DELETE /exceptions/{id}` require `device_id` query always, or derive from record?
3. Keep refresh token model simple (single JWT refresh endpoint) or add separate refresh token pair now?
4. Do we persist revoked token list, or accept stateless logout for MVP?

---

## 11) Implementation Checklist

- [ ] Backend Pydantic models created for all request/response payloads
- [ ] Frontend Zod schemas mirror canonical objects
- [ ] Contract tests verify success + error shape for each endpoint
- [ ] Smoke script verifies complete flow: login -> dashboard -> create temp exception -> revoke -> verify
