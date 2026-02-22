# Admin Gateway (Phase 1 Scaffold)

This folder contains the initial scaffold for P2-01 from the UX task board.

## What's included
- App bootstrap (`app.py`) with CORS middleware and health endpoint
- Router split (`routers/*`) for auth, dashboard, exceptions, and devices
- Service stubs (`services/*`) for upstream orchestration
- Shared config/dependencies/models scaffolding

## What's intentionally deferred
- JWT implementation (P2-02/P2-03)
- Tab-server HTTP transport and retries (P2-04/P2-05)
- Validation and error translation (P2-07)
- Static SPA serving (`/admin`) (P2-09)
