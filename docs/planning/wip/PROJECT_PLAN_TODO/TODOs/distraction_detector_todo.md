# Module: Distraction Detector (`distraction_detector`)

## Purpose
- Compare current activity (from activity monitor) to allowed list for the active task.
- Detect and flag distractions in real time.

## To-Do List (Expanded & Integrated)
- [ ] **Implement comparison logic**
    - Use activity data (window titles, process names, etc.) from the activity monitor.
    - Fetch the allowed app/process list for the current focus/task context.
    - Compare current activity against this list.
    - Support fuzzy matching for app/process names (to handle minor variations).
- [ ] **Track time spent in each app**
    - Aggregate time per app/process using timestamps from the activity monitor.
    - Store historical usage per session for reporting and learning.
- [ ] **Trigger alert if threshold exceeded**
    - Define configurable time thresholds for distractions (per app or global).
    - Integrate with alert/notification system to notify user when a distraction is detected.
    - Support both immediate and delayed alerts.
- [ ] **Allow for future learning/personalization hooks**
    - Design API to allow the system to learn from user corrections (e.g., marking an app as not a distraction).
    - Store user overrides/preferences for future sessions.
- [ ] **Integration with activity monitor**
    - Subscribe to or poll activity monitor events/data.
    - Ensure minimal latency between activity detection and distraction detection.
    - Handle edge cases (e.g., rapid app switching, idle time).
- [ ] **Logging and reporting**
    - Log all detected distractions with timestamps and context.
    - Provide hooks for summary reporting (for use in reporting system).
- [ ] **Configuration and extensibility**
    - Allow user to configure allowed/distraction lists and thresholds.
    - Support per-task or global configuration.

## Requirements (Expanded)
- Must be accurate, responsive, and low-latency.
- Configurable alert thresholds (per app, per session, per user).
- Seamless integration with activity monitor and alert system.
- Extensible for future learning and reporting features.

## Testing Plan (Expanded)
- Unit tests for matching and threshold logic.
- Simulated distraction scenarios using mock activity monitor data.
- End-to-end tests: activity monitor → distraction detector → alert system.
- Test user configuration overrides and learning hooks.
