# FocusGuard — Session Plan: February 22, 2026

**Created**: February 22, 2026  
**Purpose**: Prioritized task list for today's session, informed by current state of all planning docs and recent bug reports.

---

## Current State Summary

### What's Working
- Admin console with login, dashboard (hero redesign done), Rules & Overrides, Settings (enforcement + budgets + domains), Saved Links
- Tab server, admin gateway, browser extensions (Chrome + Edge)
- Activity logger now wired into tray-app path (Feb 22 fix)
- Classification pipeline, budget tracking, override system

### What's Broken / Needs Verification
1. **Domains page regression** — "unable to load domains" error (was working before Feb 21 changes)
2. **App activity tab** — shows no data (activity logger fix landed but exe not rebuilt)
3. **Email reports** — still blank (same root cause: activity logger wasn't persisting samples)
4. **Exe is stale** — Feb 22 changes (activity logger, dashboard hero, nav rename) not in current exe

---

## Session Priority Order

### Tier 1: Fix Regressions & Verify (Do First)

| # | Task | Est. | Priority |
|---|------|------|----------|
| 1 | **Debug & fix domains page regression (BUG-021)** — trace "unable to load domains" error in Settings page domain management. Likely a wiring issue in settings service or router from Feb 21 changes. | 1-2h | CRITICAL |
| 2 | **Rebuild admin UI + exe** — `cd admin_ui && npm run build` then PyInstaller rebuild to include activity logger fix + all Feb 21-22 changes | 30min | CRITICAL |
| 3 | **Verify activity data pipeline** — after rebuild, confirm: (a) activity_samples being written to usage.db, (b) app activity tab shows data, (c) email report includes activity | 30min | CRITICAL |

### Tier 2: Continue UX Improvements (Main Work)

| # | Task | Est. | Priority |
|---|------|------|----------|
| 4 | **Settings page polish: per-category budget sliders** — make per-category budgets editable (currently read-only). Wire to `POST /api/domains/budgets/classification`. | 2-3h | HIGH |
| 5 | **Settings page: per-domain budget editing** — click domain in table to set per-domain budget. Wire to `POST /api/domains/budgets/domain`. | 1-2h | HIGH |
| 6 | **Settings page: email config** — add toggle, recipient email(s), frequency, test button. Support multiple recipients. Needs new admin gateway endpoint. | 2-3h | HIGH |
| 7 | **Fix BUG-012: Devices page runtime error** — debug and fix contract mismatch | 1-2h | MEDIUM |
| 8 | **Fix BUG-015: Friction/override readability** — improve labels, units, filter synthetic domains | 1-2h | MEDIUM |

### Tier 3: Dashboard Remaining Items (If Time Permits)

| # | Task | Est. | Priority |
|---|------|------|----------|
| 9 | **Activity timeline (Phase A3)** — hourly bar chart, color-coded by category. May need new backend endpoint. | 3-4h | MEDIUM |
| 10 | **Collapsible detail sections (Phase A4)** — accordion for detailed cards | 1-2h | LOW |
| 11 | **Date/time range selector (Phase A5)** — presets + custom range, backend query params | 2-3h | LOW |

### Tier 4: Navigation & Architecture (Defer to Next Session)

| # | Task | Est. | Priority |
|---|------|------|----------|
| 12 | Merge Devices into Dashboard | 1-2h | LOW |
| 13 | Add dedicated Activity page | 3-4h | LOW |
| 14 | Add Alerts/Notifications page | 2-3h | LOW |
| 15 | Override UX polish (human-friendly time inputs) | 2-3h | LOW |

---

## Realistic Session Goal

**Minimum**: Complete Tier 1 (fix domains regression, rebuild, verify activity pipeline)  
**Target**: Complete Tier 1 + Tier 2 items 4-6 (settings polish)  
**Stretch**: Also complete Tier 2 items 7-8 (devices fix, friction readability)

---

## Key Files for This Session

| Component | Path |
|-----------|------|
| Settings view | `admin_ui/src/views/Settings.tsx` |
| Settings API | `admin_ui/src/api/settings.ts` |
| Settings service (backend) | `focus_guard/core/admin_gateway/services/settings_service.py` |
| Settings router (backend) | `focus_guard/core/admin_gateway/routers/settings.py` |
| Dashboard view | `admin_ui/src/views/Dashboard.tsx` |
| Dashboard service | `focus_guard/core/admin_gateway/services/dashboard_service.py` |
| Tab server | `focus_guard/core/browser_v2/tab_server/server.py` |
| Main entry (activity logger) | `focus_guard/main.py` |
| Email reporter | `focus_guard/deployment/email_reporter.py` |
| PyInstaller spec | `deployment/application/windows/specs/focusguard_unified.spec` |

---

## Build Commands

```powershell
# Build admin UI
cd admin_ui && npm run build

# Build exe
cd C:\Users\prasun_agarwal\focus_guard
python -m PyInstaller --clean deployment/application/windows/specs/focusguard_unified.spec

# Run diagnostics
python -m focus_guard.deployment.main_service diagnostics

# Run backend tests
python -m pytest focus_guard/tests/core/admin_gateway/ -q
```
