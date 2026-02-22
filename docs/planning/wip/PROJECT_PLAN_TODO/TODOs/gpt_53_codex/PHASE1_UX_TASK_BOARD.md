# FocusGuard UX — Phase 1 Concrete Task Board (4-Phase Execution)

**Created:** 2026-02-14  
**Scope:** Parent/Accountability Buddy admin UX (Phase 1 MVP slice)  
**Primary References:**
- `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/opus_45/ux_master_plan.md`
- `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/opus_45/PROGRESS_TRACKER.md`

---

## 0) Objective and Boundaries

### Objective
Ship a usable Phase 1 admin experience that allows a parent/accountability buddy to:
1. Log in securely
2. See device + distraction status quickly
3. Allow/block domains with minimal friction
4. Revoke active overrides
5. Operate from desktop and mobile browsers

### Out of Scope (for this board)
- Multi-device orchestration beyond single local agent
- Role-based access control (partner/read-only)
- WebSocket live updates (polling only in Phase 1)
- Full reporting/analytics dashboards
- Policy version rollback UX

---

## 1) Phase Overview

| Phase | Name | Goal | Exit Gate |
|---|---|---|---|
| P1 | Planning + Contract Freeze | Lock Phase 1 API/UI scope and skeleton | Signed-off API + folder structure + sprint backlog |
| P2 | Backend Foundation | Implement admin gateway + auth + core aggregate/mutation APIs | API tests green, manual curl/Postman verification |
| P3 | Frontend MVP | Implement login/dashboard/overrides UX (responsive) | Parent workflows functional on desktop + mobile |
| P4 | Stabilization + Release Gate | Hardening, E2E validation, packaging integration | Release checklist pass + known issues documented |

---

## 1.1) Final Repo Structure + Naming Conventions (P1-05 Sign-off)

### Backend (Python)

```text
focus_guard/core/admin_gateway/
  __init__.py
  app.py
  config.py
  dependencies.py
  models.py
  routers/
    __init__.py
    auth.py
    dashboard.py
    exceptions.py
    devices.py
  services/
    __init__.py
    tab_server_client.py
    dashboard_service.py
    exception_service.py
```

### Frontend (Phase 1 target)

```text
focus_guard/admin_ui/
  src/
    app/
    features/
      auth/
      dashboard/
      exceptions/
      devices/
    lib/api/
```

### Naming Rules
- Routers: plural resource naming where possible (`exceptions.py`, `devices.py`).
- Services: `<domain>_service.py` for orchestration, `tab_server_client.py` for upstream transport.
- Models: request/response schemas centralized in `models.py` for P2; split by domain in P3+ if size grows.
- Public API prefix remains `/admin/api/v1`.

---

## 2) Task Board by Phase

## P1 — Planning + Contract Freeze (2-3 days)

### Deliverables
- Frozen endpoint list for Phase 1
- API request/response schemas for implemented routes
- Implementation skeleton for backend + frontend folders
- Detailed sprint board for P2/P3/P4

### Tasks

| ID | Task | Owner | Depends On | Est. | Output |
|---|---|---|---|---:|---|
| P1-01 | Confirm Phase 1 workflow set (allow/block/revoke/status/login) | Core | None | 2h | Final workflow list in this doc |
| P1-02 | Freeze Phase 1 endpoint contract under `/admin/api/v1` | Core | P1-01 | 3h | `API_CONTRACT_PHASE1.md` |
| P1-03 | Define error model mapping (`UNAUTHORIZED`, `DEVICE_OFFLINE`, etc.) | Core | P1-02 | 2h | Error matrix section in contract |
| P1-04 | Define data schemas (TS + backend models) | Core | P1-02 | 4h | Shared schema checklist |
| P1-05 | Define repo structure + naming conventions | Core | P1-01 | 2h | Folder plan + coding conventions |
| P1-06 | Build implementation backlog with acceptance criteria | Core | P1-02,P1-05 | 2h | Tickets for P2-P4 |

### Acceptance Criteria
- [ ] No open API shape disputes before coding starts
- [ ] Each Phase 1 endpoint has explicit request/response examples
- [ ] UI routes for MVP are fixed (`/login`, `/dashboard`, `/overrides`)

---

## P2 — Backend Foundation (4-6 days)

### Deliverables
- Admin gateway service running (FastAPI)
- JWT auth for admin login and protected routes
- Dashboard aggregate endpoint
- Exception/override mutation endpoints
- CORS + whitelist strategy for “always accessible” admin UI

### Tasks

| ID | Task | Owner | Depends On | Est. | Output |
|---|---|---|---|---:|---|
| P2-01 | Create admin gateway module scaffold (`core/admin_gateway`) | Backend | P1-05 | 3h | App bootstrap + router split |
| P2-02 | Implement auth endpoints (`login/refresh/logout/me`) | Backend | P2-01 | 6h | `auth.py`, token utils, tests |
| P2-03 | Add auth middleware/dependency for protected routes | Backend | P2-02 | 3h | Route guards + negative tests |
| P2-04 | Implement `/dashboard` aggregator from tab server endpoints | Backend | P1-02 | 8h | `dashboard_service.py` + tests |
| P2-05 | Implement `/exceptions` create/list/revoke/proxy mapping | Backend | P2-04 | 8h | `exceptions_service.py` + tests |
| P2-06 | Implement `/devices` status endpoint (single-device MVP) | Backend | P2-04 | 4h | Device DTO + tests |
| P2-07 | Implement structured error model + translation layer | Backend | P1-03 | 4h | Consistent error responses |
| P2-08 | Add CORS/origin settings + admin UI accessibility safeguards | Backend | P2-01 | 4h | Configurable allowed origins |
| P2-09 | Wire static SPA serving from gateway (`/admin`) | Backend | P2-01 | 4h | Static mount + route fallback |
| P2-10 | Backend contract tests + smoke scripts | Backend/QA | P2-02..P2-09 | 6h | pytest + manual smoke checklist |

### Acceptance Criteria
- [ ] Authenticated call succeeds; unauthenticated mutation fails with `401/403`
- [ ] Parent can create temporary/permanent/budget exception via gateway API
- [ ] Dashboard response includes status, budget, top friction, recent overrides
- [ ] API works from localhost and LAN access scenario (config-driven)

### Notes
- Polling-based freshness only in Phase 1 (WebSocket deferred)
- Keep backend authoritative; no heavy caching logic in gateway

---

## P3 — Frontend MVP (5-7 days)

### Deliverables
- React + TypeScript + Vite admin UI app
- Auth flow and protected routes
- Responsive dashboard and override management UX
- Error/loading/empty states implemented

### Tasks

| ID | Task | Owner | Depends On | Est. | Output |
|---|---|---|---|---:|---|
| P3-01 | Bootstrap app (`admin_ui`) with TS, Tailwind, Router, Query | Frontend | P1-05 | 4h | Working project skeleton |
| P3-02 | Build API client + token interceptor + error handling | Frontend | P2-02,P2-07 | 5h | `api/client.ts` + tests |
| P3-03 | Build auth pages + route guards | Frontend | P3-02 | 4h | `/login` + protected layout |
| P3-04 | Build app shell (sidebar desktop, bottom tabs mobile) | Frontend | P3-01 | 6h | Shared layout components |
| P3-05 | Build dashboard widgets (status, budget, friction, overrides) | Frontend | P2-04,P3-04 | 10h | Dashboard page |
| P3-06 | Build exception modal (temporary/permanent/budgeted) | Frontend | P2-05 | 8h | Mutation forms + validation |
| P3-07 | Build active override list + revoke action | Frontend | P2-05 | 6h | Overrides page/section |
| P3-08 | Implement polling strategy (10-30s intervals by view) | Frontend | P3-05 | 2h | Query config tuned |
| P3-09 | Implement loading/error/empty/offline states | Frontend | P3-05..P3-07 | 5h | UX state coverage |
| P3-10 | Accessibility pass (focus, ARIA labels, contrast) | Frontend | P3-04..P3-09 | 4h | A11y checklist pass |

### Acceptance Criteria
- [ ] Parent can log in and stay logged in (token refresh path)
- [ ] Parent can allow, block, and revoke from UI without page reload
- [ ] Mobile layout works at ~375px width with no horizontal overflow
- [ ] Mutation success/failure feedback is clear (toast + inline errors)

### Notes
- Use optimistic updates only for actions with safe rollback
- Keep component complexity low; no global client store for now

---

## P4 — Stabilization + Release Gate (3-4 days)

### Deliverables
- Automated test baseline for Phase 1
- End-to-end flow validation with real tab server
- Packaging/runtime integration checklist
- Release notes + known issues log

### Tasks

| ID | Task | Owner | Depends On | Est. | Output |
|---|---|---|---|---:|---|
| P4-01 | Unit tests for key components/forms/formatters | FE/QA | P3-10 | 8h | Vitest suites |
| P4-02 | Integration tests with MSW for API contracts | FE/QA | P3-10 | 8h | Contract behavior tests |
| P4-03 | Playwright smoke suite (desktop + mobile critical paths) | FE/QA | P3-10 | 10h | E2E test pack |
| P4-04 | Agent-in-the-loop tests against real tab server | QA/Backend | P2-10,P3-10 | 8h | True integration verification |
| P4-05 | Security pass (auth bypass checks, token handling, CORS) | Backend | P2-10,P4-04 | 4h | Security checklist |
| P4-06 | Performance sanity check (API latency + UI render) | FE/BE | P4-04 | 3h | Metrics snapshot |
| P4-07 | Packaging integration check (gateway + SPA served in app) | Backend | P4-04 | 5h | Runbook updates |
| P4-08 | Release gate review + go/no-go | Core | P4-01..P4-07 | 2h | Decision record |

### Acceptance Criteria
- [ ] Critical Playwright flows pass (login, allow temp, revoke override)
- [ ] No high-severity auth/security defects open
- [ ] Known issues captured with severity and workaround
- [ ] Runbook updated for local + LAN admin access

---

## 3) Priority Workflows Mapped to Tasks

| Workflow | Backend Tasks | Frontend Tasks | Test Tasks |
|---|---|---|---|
| Allow temporarily/permanently/budgeted | P2-05 | P3-06 | P4-02,P4-03,P4-04 |
| Block now + categorize (MVP block now) | P2-05 | P3-06 | P4-02,P4-03 |
| Revoke active override | P2-05 | P3-07 | P4-02,P4-03,P4-04 |
| Review what’s happening (MVP dashboard) | P2-04,P2-06 | P3-05 | P4-01,P4-02 |

---

## 4) Risks and Mitigations (Phase 1)

| Risk | Impact | Mitigation | Trigger |
|---|---|---|---|
| API contract drift between FE/BE | Rework, bugs | Freeze contract in P1-02 and add schema tests in P4-02 | Any ad-hoc response shape change |
| Auth edge cases (refresh expiry, token theft) | Security/usability issues | Short token TTL + refresh tests + secure handling | Frequent session drops or bypass findings |
| Device offline handling unclear | Bad UX/confusion | Standard `DEVICE_OFFLINE` UI pattern with retry/staleness | API timeout/offline errors during tests |
| Too much scope in Phase 1 | Delivery slip | Strict out-of-scope enforcement section | New feature requests during P2/P3 |

---

## 5) Suggested File Targets (Initial)

### Backend
- `focus_guard/core/admin_gateway/app.py`
- `focus_guard/core/admin_gateway/routes/auth.py`
- `focus_guard/core/admin_gateway/routes/dashboard.py`
- `focus_guard/core/admin_gateway/routes/exceptions.py`
- `focus_guard/core/admin_gateway/routes/devices.py`
- `focus_guard/core/admin_gateway/services/tab_server_client.py`
- `focus_guard/core/admin_gateway/services/dashboard_aggregator.py`
- `focus_guard/core/admin_gateway/services/exception_service.py`

### Frontend
- `focus_guard/admin_ui/src/main.tsx`
- `focus_guard/admin_ui/src/app/router.tsx`
- `focus_guard/admin_ui/src/features/auth/*`
- `focus_guard/admin_ui/src/features/dashboard/*`
- `focus_guard/admin_ui/src/features/exceptions/*`
- `focus_guard/admin_ui/src/lib/api/client.ts`

### Tests
- `focus_guard/admin_ui/src/**/*.test.tsx`
- `focus_guard/admin_ui/e2e/*.spec.ts`
- `focus_guard/core/admin_gateway/tests/test_auth.py`
- `focus_guard/core/admin_gateway/tests/test_dashboard.py`
- `focus_guard/core/admin_gateway/tests/test_exceptions.py`

---

## 6) Execution Checklist (Quick Start)

### Week 1
- [ ] Complete P1 (contract + scaffold decisions)
- [ ] Start/finish P2-01..P2-05

### Week 2
- [ ] Complete P2-06..P2-10
- [ ] Complete P3-01..P3-07

### Week 3
- [ ] Complete P3-08..P3-10
- [ ] Complete P4 release gate tasks

---

## 7) Definition of Done — Phase 1 UX

Phase 1 is done when all are true:
- [ ] Parent can authenticate and access dashboard from desktop and mobile browser
- [ ] Parent can allow/block/revoke domains from UI and changes are reflected in agent behavior
- [ ] Error states are understandable and actionable
- [ ] Automated tests cover critical paths and pass in CI/local
- [ ] Docs/runbook updated for operating the admin interface
