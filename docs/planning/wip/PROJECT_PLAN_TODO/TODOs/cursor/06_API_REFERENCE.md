# FocusGuard — API Reference

**Created**: February 21, 2026
**Purpose**: Quick reference for all HTTP API endpoints across both servers.

---

## Tab Server API (port 58392)

Base URL: `http://127.0.0.1:58392`

### Health & Status

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/health` | No | Server health check |
| GET | `/api/status` | No | Server status (connected browsers, uptime) |
| GET | `/api/auth/status` | No | Auth system status (does not expose token) |

### Tab Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/tabs` | No | Get current tab data from connected browsers |
| POST | `/api/tabs` | No | Extension reports tab data (URL, title, browser) |
| POST | `/api/events` | No | Extension reports events |
| POST | `/api/command` | No | Send command to extension |
| GET | `/api/command` | No | Get pending commands for extension |

### Blocking & Classification

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/should_block?url=...` | No | Check if URL should be blocked |
| POST | `/api/should_block/rules` | **Yes** | Add blocking rule |
| DELETE | `/api/should_block/rules` | **Yes** | Remove blocking rule |
| POST | `/api/classification/reload` | **Yes** | Reload classification config |
| POST | `/api/blocking/enable_classification` | **Yes** | Enable/disable classification blocking |

### Overrides

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/override` | No | Request override (temporary unblock) |
| POST | `/api/override/smart` | No | Smart override (considers budgets) |
| POST | `/api/override/start` | No | Start using an active override |
| POST | `/api/override/revoke` | **Yes** | Revoke an active override |
| GET | `/api/override` | No | Get override status |
| GET | `/api/override/active` | No | Get active overrides |
| GET | `/api/override/log` | No | Get override history |
| GET | `/api/override/stats` | No | Get override statistics |

### Domain Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/domains/overview` | No | All domains with category, status, budget |
| GET | `/api/domains/budgets` | No | All budget configs |
| POST | `/api/domains/category` | **Yes** | Move domain(s) to category |
| POST | `/api/domains/whitelist` | **Yes** | Add/remove from always-allowed |
| POST | `/api/domains/budgets/domain` | **Yes** | Set per-domain budget |
| POST | `/api/domains/budgets/classification` | **Yes** | Set classification budget |
| POST | `/api/domains/budgets/master` | **Yes** | Update master budget |
| GET | `/api/domain/rules` | No | Get domain-specific rules |
| POST | `/api/domain/rules` | **Yes** | Set domain rule |
| POST | `/api/domain/rules/delete` | **Yes** | Delete domain rule |
| GET | `/api/domain/usage` | No | Get domain usage data |
| GET | `/api/domain/summary` | No | Get domain usage summary |
| POST | `/api/domain/active` | No | Report active domain |

### Distraction & Budget

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/distraction/budget` | No | Current distraction budget status |
| GET | `/api/distraction/sites` | No | Distraction site statistics |

### Enforcement

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/enforcement_mode` | No | Get current enforcement mode |
| POST | `/api/enforcement_mode` | **Yes** | Set enforcement mode (requires password if set) |

### Analytics

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/analytics/daily` | No | Daily insights (focus score, time metrics, alerts) |
| GET | `/api/analytics/weekly` | No | Weekly summary with trends |
| GET | `/api/analytics/heatmap` | No | Hourly usage heatmap |

### Activity & Audit

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/activity/logs` | No | Activity log entries |
| GET | `/api/activity/stats` | No | Activity statistics |
| GET | `/api/audit` | No | Audit log entries |
| GET | `/api/audit/summary` | No | Audit summary |
| GET | `/api/search/logs` | No | Search query logs |
| GET | `/api/search/stats` | No | Search statistics |
| GET | `/api/search/patterns` | No | Search patterns |

### Saved Links

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/saved_links` | No | List saved links |
| GET | `/api/saved_links/stats` | No | Saved links statistics |
| POST | `/api/saved_links` | No | Save a blocked link |
| POST | `/api/saved_links/view` | No | Mark saved link as viewed |
| POST | `/api/saved_links/delete` | No | Delete saved link |

### Blocked Sites

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/blocked/sites` | No | Today's blocked sites with counts |

### Personalization

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/popup_context` | No | Personalized blocked page data (greeting, streak, score, tidbits) |

---

## Admin Gateway API (port 58393)

Base URL: `http://127.0.0.1:58393`

### Health & Meta

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/admin/health` | No | Gateway health check |
| GET | `/admin/api/v1/meta` | No | Capabilities, readiness, version |

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/admin/api/v1/auth/login` | No | Login (returns access + refresh tokens) |
| POST | `/admin/api/v1/auth/refresh` | No | Refresh access token |
| POST | `/admin/api/v1/auth/logout` | **Yes** | Logout (invalidate tokens) |
| GET | `/admin/api/v1/auth/me` | **Yes** | Get current user info |

### Dashboard

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/admin/api/v1/dashboard` | No | Aggregated dashboard data |

### Exceptions (Overrides)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/admin/api/v1/exceptions` | No | List exceptions/overrides |
| POST | `/admin/api/v1/exceptions` | **Yes** | Create exception (temporary/permanent/budgeted/block) |
| DELETE | `/admin/api/v1/exceptions/{id}` | **Yes** | Revoke exception |

### Devices

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/admin/api/v1/devices` | **Yes** | Device status list |
| PUT | `/admin/api/v1/devices/{id}/enforcement` | **Yes** | Update enforcement mode |

### Static SPA

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/admin` | No | Admin UI SPA (index.html) |
| GET | `/admin/{path}` | No | SPA static assets or client-route fallback |

---

## Authentication Details

### Tab Server Auth
- **Token**: Random 256-bit bearer token, generated on first run
- **Storage**: `C:\ProgramData\FocusGuard\api_token.json`
- **Header**: `Authorization: Bearer <token>`
- **Scope**: Only mutation endpoints require auth (GET endpoints are open)

### Admin Gateway Auth
- **Method**: Username/password login → JWT access + refresh tokens
- **Default credentials**: `admin` / `secret123` (configurable in deployment_config.json)
- **Header**: `Authorization: Bearer <access_token>`
- **Token refresh**: Use refresh token when access token expires

---

## Error Response Format

Both servers use structured error envelopes:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or missing authentication token",
    "details": null,
    "retry_after_seconds": null
  }
}
```

Common error codes: `UNAUTHORIZED`, `FORBIDDEN`, `VALIDATION_ERROR`, `NOT_FOUND`, `DEVICE_OFFLINE`, `INTERNAL_ERROR`
