# FocusGuard — Project Overview & Orientation Guide

**Created**: February 21, 2026
**Purpose**: Comprehensive reference for Cursor AI agent to navigate and work on the FocusGuard codebase.

---

## What is FocusGuard?

FocusGuard is an **AI-powered productivity management application** for Windows that helps users (primarily students/children, monitored by parents) stay focused by:

1. **Classifying websites** as educational, entertainment, social media, etc. using rule-based and LLM (OpenAI) classifiers
2. **Enforcing time budgets** — e.g., 10 min/day of entertainment, 45 min total distraction
3. **Blocking distracting sites** via a browser extension that communicates with a local HTTP server
4. **Monitoring activity** — tracking active windows, browser tabs, idle time
5. **Reporting to parents** — hourly/daily email reports, admin web dashboard
6. **Resisting bypass** — security mitigations against process kills, extension removal, VPN, clock manipulation, etc.

## Key Authors / Users

- **Prasun Agarwal** — developer/parent
- **Siyona Agarwal** — target user (student)
- Machine: `NucBox_K8Plus`

## Architecture at a Glance

```
FocusGuard.exe (PyInstaller onefile, ~442 MB)
├── System Tray (PyQt5) ──── user interaction, first-run wizard, settings
├── Tab Server (aiohttp, port 58392) ──── browser extension HTTP API
│   ├── Classification pipeline (rule-based + optional LLM)
│   ├── Domain usage tracker + budgets
│   ├── Override manager (time-limited relaxations)
│   ├── Audit/search/screenshot logging (SQLite)
│   ├── Analytics service (daily/weekly/heatmap)
│   ├── Saved links module (save blocked URLs for later)
│   ├── Security monitors (heartbeat, hosts, VPN, clock, user accounts)
│   └── API auth (bearer token on mutations)
├── Admin Gateway (FastAPI/uvicorn, port 58393) ──── parent/admin web UI
│   ├── Auth (login/refresh/logout/me)
│   ├── Dashboard aggregation (proxies tab server data)
│   ├── Exception management (create/list/revoke overrides)
│   ├── Device status + enforcement control
│   └── Static SPA serving (/admin → admin_ui/dist)
├── Activity Monitor ──── window/tab tracking via win32 APIs
├── Email Reporter ──── hourly/daily scheduled email reports (Gmail SMTP)
└── Coordinator ──── lifecycle management of all components
```

## Browser Extensions

| Browser | Store | Extension ID |
|---------|-------|-------------|
| Chrome | Chrome Web Store | `hnpfnmlcmdhkbhnfifmnonehebeafclp` |
| Edge | Microsoft Edge Add-ons | `legaalcjhhgofgpgbbpoadafdjllckgg` |

The extension is MV3 (Manifest V3), located at `focus_guard/core/browser/extension/webextension_mv3/`.

## Port Assignments

| Service | Port | Purpose |
|---------|------|---------|
| Tab Server | 58392 | Browser extension API |
| Admin Gateway | 58393 | Parent/admin web UI |

## Data Locations (Runtime)

| Data | Path |
|------|------|
| Config | `C:\ProgramData\FocusGuard\deployment_config.json` |
| Domain config | `C:\ProgramData\FocusGuard\domain_config.json` |
| API token | `C:\ProgramData\FocusGuard\api_token.json` |
| Logs | `C:\ProgramData\FocusGuard\logs\` |
| Usage DB | `C:\Users\<user>\AppData\Local\FocusGuard\usage.db` |
| Domain config hash | `C:\ProgramData\FocusGuard\domain_config.hash` |

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.8+ |
| GUI | PyQt5 (system tray, first-run wizard) |
| Tab Server | `http.server` (ThreadingHTTPServer) / aiohttp |
| Admin Gateway | FastAPI + uvicorn |
| Admin UI | React + TypeScript + Tailwind CSS + TanStack Query |
| Admin UI Build | Vite |
| Admin E2E | Playwright |
| Browser Extension | JavaScript (MV3, background service worker) |
| Packaging | PyInstaller (single onefile .exe) |
| Database | SQLite (usage, audit, search logs, saved links) |
| Classification | Rule-based + OpenAI LLM (optional) |
| Email | smtplib (Gmail SMTP) |
| OS Integration | pywin32 (window tracking, registry, services) |

## Development Tracks

The project has been developed across two main AI assistant tracks:

| Track | Time Period | Focus |
|-------|------------|-------|
| **opus_45** | Feb 1-9, 2026 | Core app: unified main.py, PyInstaller build, first-run wizard, deployment, security mitigations (Section 8), domain config consolidation, analytics |
| **gpt_53_codex** | Feb 14-21, 2026 | Admin UX: FastAPI gateway, React admin UI, integration testing, packaged-lane validation, bug fixes, MVP polish |

**Current active plan**: `gpt_53_codex/PLAN_02202026_DEPLOYMENT_AND_MVP.md` (supersedes all prior plans)

## Build Command

```powershell
python -m PyInstaller --clean deployment/application/windows/specs/focusguard_unified.spec
```

Output: `dist/FocusGuard.exe`

## Running from Source

```powershell
# Main application (tray + all services)
python -m focus_guard.main

# Tab server only
python scripts/dev/start_tab_server.py

# Admin gateway only
python -m uvicorn focus_guard.core.admin_gateway.app:create_app --factory --host 127.0.0.1 --port 58393

# Admin UI dev server
cd admin_ui && npm run dev

# Tests
python -m pytest focus_guard/tests/core/admin_gateway/ -q
python scripts/test_section8_mitigations.py
cd admin_ui && npm run test && npm run test:integration && npm run test:e2e
```

---

*This document is the starting point. See companion documents for detailed file maps, bug tracking, and development workflows.*
