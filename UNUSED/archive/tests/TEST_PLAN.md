# FocusGuard Test Plan

## Philosophy
- All modules and functions must have unit tests using pytest.
- Integration tests for module interaction and main loop.
- Manual demo scripts for UI/alert/OS integration features.

## Structure
- `tests/` mirrors main code structure (test_core_*.py, test_utils_*.py, etc.)
- `demos/` contains demo scripts for manual/visual testing

## Coverage Goals
- 90%+ code coverage for core logic
- All platform-specific code must be mocked in CI

## Demo Guidelines
- Demos should be simple scripts runnable with `python demos/<demo_name>.py`
- Used for manual verification of popups, GUI, OS integration, etc.

## How to Run
- `pytest` for automated tests
- `python demos/<demo_name>.py` for demos
