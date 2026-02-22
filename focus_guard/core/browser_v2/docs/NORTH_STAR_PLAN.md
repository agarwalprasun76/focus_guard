# Browser Integration v2 North Star

## Purpose
Steel-man the browser integration workflow so Focus Guard can reliably install, verify, and communicate with a browser extension reporting to the tab server. This document guides the refactor work housed in `focus_guard/core/browser_v2/`.

## Guiding Goals
1. **Reliable install + verify** – clear entry point that installs (or launches) the extension, confirms success, and exposes actionable errors.
2. **Managed lifecycle** – tab server and supporting processes start, monitor, and shut down cleanly across platforms (Windows-first).
3. **Compatibility bridge** – existing Focus Guard components should integrate via adapters/feature flags while the new stack matures.
4. **Security + admin clarity** – make privilege requirements explicit, provide safe defaults, and log actionable troubleshooting info.
5. **Testability** – fast unit coverage, integration harness with mock extension, and manual smoke tests for real browsers.

## Scope & Constraints
- Initial target: Windows (Chrome & Edge). Leave clearly marked extension points for macOS Phase 2.
- Installer must operate with elevated/admin privileges to prevent easy removal of Focus Guard controls.
- Development flow may rely on `--load-extension` while long-term store/policy distribution is researched.
- Production packaging (policy deployment, store publishing) tracked as future work.
- Maintain backward compatibility until v2 is production-ready.
- Prefer incremental PRs with feature flag toggles.
- Headless browsers are out-of-scope for automated tests due to real-site security restrictions.

## Architectural Overview
```
browser_v2/
├── installer/
│   ├── strategies/            # Dev unpacked, Windows policy (future), manual fallback
│   ├── core_installer.py      # Orchestrates strategy selection, privilege handling
│   └── status.py              # Result models, telemetry helpers
├── tab_server/
│   ├── server.py              # Typed HTTP/WebSocket endpoints
│   ├── api_models.py          # Request/response schemas
│   ├── runner.py              # Process launch, port discovery
│   └── supervisor.py          # Health checks, auto restart, metrics
├── integration/
│   ├── controller.py          # Public entry point; coordinates installer + server
│   ├── adapters.py            # Compatibility layer for current Focus Guard modules
│   ├── config.py              # Feature flags, defaults, env integration
│   └── telemetry.py           # Structured logging & metrics forwarders
├── extension/
│   ├── manifest/              # MV3 source, packaging scripts
│   └── README.md              # Manual/CI packaging instructions + macOS placeholder notes
├── tests/
│   ├── unit/                  # Strategy/server/controller tests
│   └── integration/           # Mock extension harness, CLI smoke tests (real-browser only)
└── docs/
    ├── NORTH_STAR_PLAN.md     # This document
    └── decision_log.md        # Record key design decisions
```

## Phased Roadmap
1. **Scaffolding & Feature Flags**
   - Create package structure, stub modules, decision log, and toggle to select v1/v2 integration.
2. **Tab Server v2 Core**
   - Implement typed API, runner, supervisor, and unit tests.
   - Provide adapter exposing current `/api/tabs`, `/api/status`, `/api/command` semantics.
3. **Installer Strategy (Dev Unpacked)**
   - Implement reliable `--load-extension` flow with verification.
   - Add CLI/entry points and structured status reporting.
4. **Integration Controller & Adapter**
   - Coordinate installer + server lifecycle.
   - Expose health snapshots & telemetry; wire feature flag for MVP to opt in.
5. **Testing & Tooling**
   - Build mock extension harness for integration tests.
   - Document manual smoke-test checklist (real Chrome/Edge; note headless limitations).
6. **Beta & Feedback Loop**
   - Enable v2 in dev builds; collect metrics.
   - Iterate on gaps before enabling by default.
7. **Future Enhancements**
   - Chrome/Edge policy deployment, signed packaging.
   - WebSocket push, multi-browser support (macOS), CI automation.

## Implementation Status (2026-01-31)

### ✅ Completed
- [x] Scaffold `tests/` and `integration/controller` modules
- [x] Prototype typed tab data models (`api_models.py`)
- [x] Draft decision log with key decisions
- [x] Research Chrome/Edge store vs policy - **Decision: Store distribution is primary path**
- [x] Flesh out tab server v2 business logic + persistence (`storage.py`, `blocking.py`)
- [x] Add unit tests covering tab_server and installer (55 tests passing)
- [x] Implement `TabServerRunner` with health checks and auto-restart
- [x] Implement installer strategies (`DevUnpackedStrategy`, `StoreInstallStrategy`)
- [x] Wire `BrowserIntegrationController` with lifecycle management
- [x] Update extension manifest for store submission
- [x] Create extension popup for status display
- [x] Create store submission checklist

### 🔄 In Progress
- [ ] Generate extension icons (run `generate_icons.py` or provide professional icons)
- [ ] Create privacy policy page for store submission
- [ ] Submit to Chrome Web Store and Edge Add-ons
- [ ] Wire browser_v2 to existing Focus Guard coordinator/blocking system

### 📋 Remaining Work
- [ ] Add feature flag hook in existing `browser_integration` for opt-in
- [ ] Create adapter layer for backward compatibility with v1
- [ ] Update extension IDs after store approval
- [ ] Integration tests with mock extension harness
- [ ] Manual smoke-test checklist documentation
- [ ] WebSocket push for real-time updates (future enhancement)
- [ ] macOS support (Phase 2)

## Quick Start

```python
from focus_guard.core.browser_v2 import initialize_browser_integration

# Initialize and start tab server
controller = initialize_browser_integration()

# Install extension (opens store page or launches with --load-extension)
controller.install_extension()

# Get current tabs
tabs = controller.get_tabs()

# Check connection status
status = controller.get_status()
print(f"Connected browsers: {status.connected_browsers}")
```

---
_Last updated: 2026-01-31_
