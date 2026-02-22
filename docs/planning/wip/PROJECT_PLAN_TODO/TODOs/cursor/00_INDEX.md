# FocusGuard — Cursor AI Agent Guide Index

**Created**: February 21, 2026
**Purpose**: Master index for all Cursor AI agent orientation documents.

---

## Quick Start

**If you're starting a new task**, read documents in this order:
1. `01_PROJECT_OVERVIEW.md` — What FocusGuard is, architecture, tech stack, how to run/build
2. `03_CURRENT_STATUS_AND_BUGS.md` — What's working, what's broken, what's next
3. `02_CODEBASE_MAP.md` — Find any file or component quickly
4. `04_ARCHITECTURE_DEEP_DIVE.md` — How components interact (request flows, data flows)
5. `05_DEVELOPMENT_WORKFLOWS.md` — How to build, test, debug, add features
6. `06_API_REFERENCE.md` — All HTTP API endpoints

---

## Document Catalog

| # | Document | Purpose | When to Use |
|---|----------|---------|-------------|
| 00 | **INDEX** (this file) | Master index | Starting point |
| 01 | **PROJECT_OVERVIEW** | What FocusGuard is, architecture, tech stack | First orientation |
| 02 | **CODEBASE_MAP** | Every important file and folder mapped | Finding files |
| 03 | **CURRENT_STATUS_AND_BUGS** | Open bugs, project phase, next actions | Understanding what needs work |
| 04 | **ARCHITECTURE_DEEP_DIVE** | Component interactions, data flows, integration points | Understanding how things connect |
| 05 | **DEVELOPMENT_WORKFLOWS** | Build, test, debug, add features | Doing actual development work |
| 06 | **API_REFERENCE** | All HTTP endpoints for both servers | Working with APIs |
| 07 | **ADMIN_CONSOLE_UX_IMPROVEMENT_PLAN** | UX review + improvement blueprint for admin UI | Planning admin console improvements |
| 08 | **APPLICATION_ARCHITECTURE_IMPROVEMENT_PLAN** | Full application audit, prioritized issues + roadmap | Planning broader architecture work |

---

## One-Line Summary

**FocusGuard** is a Windows desktop application (Python + PyQt5 + browser extension) that classifies websites, enforces time budgets, blocks distracting content, and reports activity to parents — packaged as a single `FocusGuard.exe` via PyInstaller, with a React admin UI served by a FastAPI gateway.

---

## Critical Paths (Most Common Tasks)

### "Fix a bug in the admin dashboard"
→ `admin_ui/src/views/` + `core/admin_gateway/services/` + `core/admin_gateway/routers/`

### "Fix a classification/blocking issue"
→ `browser_v2/tab_server/classification_service.py` + `classification/classifiers/domains/` + `browser_v2/tab_server/classification_blocker.py`

### "Fix the browser extension"
→ `browser/extension/webextension_mv3/background.js` + `blocked.html` + `blocked.js`

### "Fix email reports"
→ `focus_guard/deployment/email_reporter.py` + usage.db query logic

### "Rebuild the exe"
→ `cd admin_ui && npm run build` then `python -m PyInstaller --clean deployment/application/windows/specs/focusguard_unified.spec`

### "Run tests"
→ `python -m pytest focus_guard/tests/core/admin_gateway/ -q` (backend) + `cd admin_ui && npm run test:e2e` (frontend)

---

## Related Planning Documents (Other Folders)

| Folder | Contents | Status |
|--------|----------|--------|
| `gpt_53_codex/` | Active execution plan, progress tracker, bug reports | **Current active track** |
| `opus_45/` | Historical deployment plan, progress, additional features | **Historical reference** |
| `V2_TODOS/` | Browser extension upgrade plans (weeks 3-5) | **Historical reference** |

### Key External Documents
- **Active plan**: `gpt_53_codex/PLAN_02202026_DEPLOYMENT_AND_MVP.md`
- **Active progress**: `gpt_53_codex/PROGRESS_TRACKER_02202026.md`
- **Active bugs**: `gpt_53_codex/BUGS_02212026.md`
- **Historical plan**: `opus_45/DEPLOYMENT_AND_MVP_PLAN_02062026.md` (Sections 1-8, comprehensive)
- **Historical progress**: `opus_45/PROGRESS_TRACKER.md` (Sessions 1-8, domain consolidation, security)
