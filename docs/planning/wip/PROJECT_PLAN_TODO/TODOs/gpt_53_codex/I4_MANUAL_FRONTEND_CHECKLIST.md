# I4-01 Manual Frontend RC Checklist

## Purpose
Repeatable manual checklist for release-candidate validation of core admin UX flows (auth, dashboard, exceptions, mobile layout).

## Session Metadata
- Tester:
- Date:
- Build/runtime:
- Environment (source/packaged, browser/device):

## Preconditions
- Admin gateway running and reachable.
- Admin credentials available.
- Clean browser session (or documented existing token state).
- For mobile checks: viewport ~375x812 or real mobile browser.

## Checklist

| Area | Check | Expected | Pass/Fail | Notes |
|---|---|---|---|---|
| Auth | Login with valid credentials | Redirect to dashboard; no console blocking errors |  |  |
| Auth | Login with invalid credentials | Structured error shown; no blank screen |  |  |
| Auth | Logout | Session cleared; returns to login |  |  |
| Dashboard | Dashboard loads after login | Core cards visible (status/focus/budget/overrides) |  |  |
| Dashboard | Readiness badges render | Gateway/tab server/enforcement badges visible |  |  |
| Dashboard | Degraded message behavior | Offline/degraded status message appears when applicable |  |  |
| Exceptions | Create temporary exception | Success toast/feedback; appears in list |  |  |
| Exceptions | Revoke exception | Row disappears or status updates correctly |  |  |
| Exceptions | Validation guardrails | Invalid form inputs blocked with clear error |  |  |
| Devices | Device list view loads | Device row + status fields visible |  |  |
| Navigation | Route transitions | Dashboard/overrides/devices switch cleanly |  |  |
| Mobile | No horizontal overflow | Content readable, no clipped actions |  |  |
| Mobile | Form/action usability | Exception form and revoke action are usable via touch layout |  |  |

## Exit Rule
- If any baseline flow fails (auth/dashboard/exception create/revoke), log in `LOOPHOLE_TRACKER.md` as same-day entry before sign-off.
