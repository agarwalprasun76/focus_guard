# Module: Task Manager (`task_manager`)

## Purpose
- Load, manage, and update user task profiles from configuration (JSON)
- Allow selection of current task
- Provide allowed apps/sites for distraction detection

## To-Do List
- [ ] Define JSON schema for task profiles
- [ ] Implement loader for profiles
- [ ] Allow dynamic reloading of profiles
- [ ] Implement task selection (by name)
- [ ] Provide API for current task info
- [ ] Validate config structure and handle errors

## Requirements
- Profiles must support allowed apps/sites, thresholds, and task name
- Must handle missing or malformed config gracefully

## Testing Plan
- Unit tests for:
  - Loading valid/invalid configs
  - Selecting tasks
  - Error handling
- Integration test: End-to-end config reload and task switch
