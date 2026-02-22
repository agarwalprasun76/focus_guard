# Next Session: Admin Dashboard Improvements

**Created**: February 21, 2026  
**Purpose**: Handoff brief for the next Cursor AI agent session focused on making the admin console genuinely useful for a parent.

---

## Context

Read the orientation docs in this order:
1. `00_INDEX.md` — master index
2. `08_APPLICATION_ARCHITECTURE_IMPROVEMENT_PLAN.md` — current status, completed items, known issues
3. `07_ADMIN_CONSOLE_UX_IMPROVEMENT_PLAN.md` — full UX blueprint (Phases A-E)

The admin console is at `admin_ui/` (React + Tailwind + TanStack Query SPA). The backend is at `focus_guard/core/admin_gateway/` (FastAPI). Both proxy to the tab server at `focus_guard/core/browser_v2/tab_server/server.py` (port 58392).

---

## What Was Completed (Feb 21)

### Settings Page (Sprint 3 — Done)
- **Enforcement mode toggle**: 3-card selector (Monitor Only / Warn / Block). Password prompt auto-appears on 403 failure from tab server. Backend: `settings_service.py` + `routers/settings.py` (8 endpoints).
- **Budget controls**: Today's usage progress bar, master budget slider (15 min–4 hrs) with quick presets, per-category read-only display. 
- **Domain management**: Searchable table with category dropdown, status filter (Allowed/Blocked/Budgeted/Tracked), Daily Budget column, Visits column, Always Allow / Remove Allow actions.

### Email Fix (Sprint 4 — Done)
- Fixed `_get_period_stats` in `deployment/email_reporter.py`: open-session WHERE clause, active-duration estimation, ISO timestamp normalization.

### Exe Rebuilt
- `dist/FocusGuard.exe` includes all fixes.

---

## What Needs Work Next (Prioritized)

### P0: Dashboard Redesign (Doc 07, Phase A — 3-5 days)

The dashboard is the most-visited page but it's a data dump. Redesign it around two modes:

1. **Hero summary section** (A1): Replace the 8-card grid with a single hero — focus score ring, natural-language summary sentence, budget progress bar, quick stats row. The data already comes from `GET /admin/api/v1/dashboard`.

2. **Alerts & actions bar** (A2): Replace "Attention Items" chips with actionable alerts — each alert has an icon, message, and action button (e.g., "reddit.com overridden 3 times → [Block Now]").

3. **Activity timeline** (A3): Hourly bar chart showing the day's activity color-coded by category. Requires new backend endpoint `GET /api/activity/timeline?date=YYYY-MM-DD` or can be derived from existing `GET /api/analytics/heatmap`.

4. **Collapsible detail sections** (A4): Move current cards into accordion sections, default collapsed.

5. **Date/time range selector** (A5): Presets (Today, Yesterday, This Week) + custom date range. Requires `start_date`/`end_date` query params on dashboard aggregation.

**Key files**: `admin_ui/src/views/Dashboard.tsx`, `focus_guard/core/admin_gateway/services/dashboard_service.py`, `focus_guard/core/admin_gateway/routers/dashboard.py`

### P1: Settings Page Polish

1. **Per-category budget editing** — currently read-only. Add sliders for each category (Entertainment, Social Media, Gaming). Uses `POST /api/domains/budgets/classification` (already wired in backend).

2. **Per-domain budget editing** — clicking a domain in the table should allow setting a per-domain budget. Uses `POST /api/domains/budgets/domain` (already wired).

3. **Email report configuration** — needs new admin gateway endpoint `POST /admin/api/v1/settings/email` that proxies to deployment config. UI: toggle, recipient email, frequency, test button.

4. **Password change** — needs new endpoint `POST /admin/api/v1/settings/password`.

### P1: Navigation & Terminology (Doc 07, Phase C)

1. Rename "Exceptions" → "Rules & Overrides" in nav and page title
2. Add "Saved Links" to sidebar nav (currently missing)
3. Use parent-friendly language throughout (see Doc 07 §3 terminology table)

### P2: Exception/Override UX Polish (Doc 07, Phase D)

1. Replace raw seconds inputs with human-friendly controls ("5 minutes" / "15 minutes" / "30 minutes" / "1 hour" / Custom)
2. Show overrides with full context (which site, when, how long, whether used)
3. Add "Allow for 30 min" quick actions on dashboard blocked sites

### P2: Verify Runtime Behavior

1. Start `FocusGuard.exe` and open `http://127.0.0.1:58393/admin`
2. Verify Settings page loads enforcement mode, budgets, and domains correctly
3. Verify enforcement mode change with password works end-to-end
4. Verify Exceptions page create/list/revoke works
5. Check next hourly email for non-blank content
6. Verify Devices page no longer shows INTERNAL_ERROR

---

## Architecture Notes for the Next Agent

### How data flows
```
Browser Extension → Tab Server (port 58392) → SQLite DBs
Admin UI SPA → Admin Gateway (port 58393) → Tab Server (port 58392)
```

### Key patterns
- **Backend**: FastAPI routers → service classes → `TabServerClient` → tab server HTTP
- **Frontend**: `api/*.ts` typed functions → TanStack Query hooks in views → React components
- **Auth**: Admin gateway uses JWT (login → access token). Tab server uses bearer API token (auto-loaded).
- **Mutations require auth**: `Depends(require_authenticated_admin)` on POST/PUT/DELETE endpoints

### Build & deploy
```powershell
cd admin_ui && npm run build          # builds to admin_ui/dist/
cd .. && python -m PyInstaller --clean deployment/application/windows/specs/focusguard_unified.spec
```

### Test
```powershell
python -m pytest focus_guard/tests/core/admin_gateway/ -q    # backend
cd admin_ui && npm run test:e2e                                # frontend E2E
```

---

## Files Changed This Session

| File | What |
|------|------|
| `focus_guard/core/admin_gateway/services/settings_service.py` | NEW — settings service (8 methods) |
| `focus_guard/core/admin_gateway/routers/settings.py` | NEW — settings router (8 endpoints) |
| `focus_guard/core/admin_gateway/routers/__init__.py` | Registered settings router |
| `focus_guard/core/admin_gateway/services/devices_service.py` | Made `list_devices` resilient to partial failures |
| `admin_ui/src/api/settings.ts` | NEW — typed API functions |
| `admin_ui/src/api/index.ts` | Added settingsApi export |
| `admin_ui/src/views/Settings.tsx` | Full rewrite — enforcement, budgets, domains |
| `focus_guard/deployment/email_reporter.py` | Fixed `_get_period_stats` — 3 root causes |
