# FocusGuard – High Level Project Plan & To-Do

## Purpose
FocusGuard is a cross-platform desktop application that monitors user activity and helps reduce distractions by alerting users when they deviate from their intended task. This document is the north star for the project, outlining all major modules, their purposes, and key milestones.

## Major Modules & Responsibilities

1. **Task Configuration System (`task_manager`)**
    - Manage and load user task profiles and whitelists.
2. **Activity Monitor (`activity_monitor`)**
    - Track active applications and browser tabs in real time (cross-platform).
3. **Distraction Detection (`distraction_detector`)**
    - Compare current activity against allowed list for the active task, trigger distraction events.
4. **Alert System (`alert_system`)**
    - Notify user when a distraction is detected (popup, sound, etc.).
5. **Logging System (`logger`)**
    - Log session events: timestamp, task, app, title, duration, alert_triggered.
6. **Cross-Platform Utilities (`cross_platform`)**
    - Abstract platform-specific logic for window/app detection.
7. **Time Utilities (`time_utils`)**
    - Provide time and duration utilities.
8. **GUI (`gui_app`)**
    - User interface for task selection, status, and session review.
9. **Data Storage/Session Logs**
    - Store session logs in SQLite or CSV.

## Project Phases

### Phase 1: Core MVP
- [ ] Implement all core modules for basic monitoring and alerting
- [ ] CLI or minimal GUI for task selection
- [ ] Logging and review of session activity

### Phase 2: Enhanced Features
- [ ] Full GUI
- [ ] Browser tab monitoring
- [ ] Session visualization
- [ ] Preferences and customization

### Phase 3: Smart Features
- [ ] Personalized learning
- [ ] Accountability buddy system
- [ ] Federated learning

## General Testing & Quality Plan
- Unit tests for all modules
- Manual end-to-end testing for MVP
- Cross-platform compatibility checks
- Code linting and adherence to PEP8
- Documentation and code comments

---

Each module has its own detailed to-do and testing plan in this folder.
