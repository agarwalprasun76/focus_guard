# Focus Guard MVP Day 2 Execution Plan

## Day 2 Objective
Harden remote-management surface so guardian actions are executable from web UI (settings + devices).

## Tasks
- [x] Verify existing settings backend/routes coverage.
- [x] Add device enforcement API client method in `admin_ui`.
- [x] Wire device enforcement controls in `Devices` view.
- [x] Add frontend API tests for devices endpoint mapping.
- [x] Run frontend tests and build to validate changes.
- [x] Add backend tests for settings/devices services (if test harness exists).
- [x] Record handoff and Day 3 first task.

## Files Touched
- `admin_ui/src/api/devices.ts`
- `admin_ui/src/api/devices.test.ts`
- `admin_ui/src/views/Devices.tsx`
- `focus_guard/core/admin_gateway/tests/test_devices_service.py`
- `focus_guard/core/admin_gateway/tests/test_settings_service.py`

## Validation Log
- [x] `npm run test:run -- src/api/devices.test.ts src/api/exceptions.test.ts`
- [x] `npm run test:run -- src/api/devices.test.ts`
- [x] `npm run build`
- [x] `pytest focus_guard/core/admin_gateway/tests -q`

## Open Items
- None for Day 2 scope.

## Day 3 First Task
Implement dashboard endpoint/data shape consolidation and replace dashboard placeholder metrics with real aggregates.

## Day 2 Handoff
- Result: Day 2 complete. Remote-management surface is now actionable from UI for device enforcement changes.
- Backend tests added for settings/devices service behavior and error mapping.
- Device enforcement UI now supports password-required flows (prompt on upstream password-required errors).

