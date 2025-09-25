# Module: Logger (`logger`)

## Purpose
- Log session activity: timestamp, task, app, title, duration, alert_triggered
- Store logs in SQLite or CSV

## To-Do List
- [ ] Define log schema
- [ ] Implement log writing (SQLite/CSV)
- [ ] Ensure atomic writes and error handling
- [ ] Add log rotation/archival (future)

## Requirements
- Logs must be reliable and recoverable
- Should not block main loop

## Testing Plan
- Unit tests for log writing
- Simulate disk full, permission errors
- Integration test with session loop
