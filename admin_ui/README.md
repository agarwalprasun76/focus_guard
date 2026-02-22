# FocusGuard Admin UI (P3-01)

Frontend MVP bootstrap for Phase 3 using:
- Vite + React + TypeScript
- TailwindCSS
- React Router
- TanStack Query

## Quick start

```bash
cd admin_ui
npm install
npm run dev
```

App defaults to `http://127.0.0.1:5173`.

## Build

```bash
npm run build
```

The generated `dist/` is compatible with admin gateway static serving at `/admin`.

## API base URL

By default the client calls `/admin/api/v1`.

Override with a Vite env var in `.env` if needed:

```bash
VITE_ADMIN_API_BASE_URL=http://127.0.0.1:3000/admin/api/v1
```
