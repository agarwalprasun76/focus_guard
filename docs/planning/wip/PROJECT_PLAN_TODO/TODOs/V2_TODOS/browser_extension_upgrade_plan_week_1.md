# Browser Extension Upgrade Plan - Week 1: Code Migration and Cleanup

## Overview

Week 1 focuses on updating all code references from the deprecated core_v2 structure to the new focus_guard/core structure, refactoring the adapter pattern implementation, and performing general code cleanup. This phase establishes the foundation for all subsequent improvements.

## Detailed Tasks

### Task 1.1: Update Import Paths

**Priority**: P0 - Critical  
**Effort**: 1 day  
**Owner**: TBD

#### Description
Update all import paths in the browser extension code to reflect the new structure without core_v2 references. This includes imports in both the main code and test files.

#### Steps
1. **Identify all core_v2 references**
   - Use grep or similar tool to find all instances of "core_v2" in imports
   - Create a mapping of old paths to new paths
   - Document all affected files

2. **Update main code imports**
   - Update imports in `core/browser/extension/installer.py`
   - Update imports in `core/browser/extension/manager.py`
   - Update imports in `core/browser/extension/tab_server.py`
   - Update imports in `core/browser/extension/native_host.py`
   - Update imports in `core/browser/integration/browser_integration.py`

3. **Update test imports**
   - Update imports in test files for extension installer
   - Update imports in test files for extension manager
   - Update imports in test files for tab server
   - Update imports in test files for browser integration

4. **Verify imports**
   - Run static analysis to ensure no import errors
   - Fix any circular imports or dependency issues

#### Code Examples

**Before:**
```python
from core_v2.browser.models import Browser, Tab
from core_v2.utils.logging import get_logger
from core_v2.config.manager import get_config_manager
```

**After:**
```python
from focus_guard.core.browser.models import Browser, Tab
from focus_guard.core.utils.logging import get_logger
from focus_guard.core.config.manager import get_config_manager
```

#### Acceptance Criteria
- [ ] All imports in browser extension code updated to new paths
- [ ] No references to core_v2 remain in the codebase
- [ ] All tests pass after updates
- [ ] No import errors or warnings during static analysis

#### Testing Strategy
- Run static analysis tools to verify imports
- Run unit tests to ensure functionality is preserved
- Verify that the application can start and operate normally

---

### Task 1.2: Refactor Adapter Pattern

**Priority**: P1 - High  
**Effort**: 2 days  
**Owner**: TBD

#### Description
Update the adapter pattern implementation to work with the new structure. This involves refactoring the adapter classes that bridge between the browser extension code and the rest of the application.

#### Steps
1. **Review current adapter implementation**
   - Identify all adapter classes in the codebase
   - Document their interfaces and dependencies
   - Identify any core_v2 specific design patterns

2. **Update adapter interfaces**
   - Update interface definitions to match new structure
   - Ensure backward compatibility with existing code
   - Document any breaking changes

3. **Refactor adapter implementations**
   - Update adapter implementations to use new paths
   - Ensure proper dependency injection
   - Maintain backward compatibility where possible

4. **Update adapter tests**
   - Update test cases for adapters
   - Add tests for any new functionality
   - Ensure all edge cases are covered

#### Code Examples

**Before:**
```python
class BrowserDetectorAdapter(core_v2.browser.interfaces.BrowserDetectorInterface):
    def __init__(self, legacy_detector):
        self.legacy_detector = legacy_detector
        
    def get_installed_browsers(self):
        return [self._convert_browser(b) for b in self.legacy_detector.get_browsers()]
```

**After:**
```python
class BrowserDetectorAdapter(focus_guard.core.browser.interfaces.BrowserDetectorInterface):
    def __init__(self, legacy_detector):
        self.legacy_detector = legacy_detector
        
    def get_installed_browsers(self):
        return [self._convert_browser(b) for b in self.legacy_detector.get_browsers()]
```

#### Acceptance Criteria
- [ ] Adapter classes properly integrated with new structure
- [ ] Clean interfaces for component interaction
- [ ] Backward compatibility maintained
- [ ] All adapter tests pass
- [ ] No regression in functionality

#### Testing Strategy
- Unit tests for each adapter class
- Integration tests for adapter interactions
- Verify proper event propagation through adapters

---

### Task 1.3: Code Cleanup

**Priority**: P2 - Medium  
**Effort**: 1 day  
**Owner**: TBD

#### Description
Clean up code, remove deprecated functions, improve documentation, and ensure consistent style and conventions throughout the browser extension code.

#### Steps
1. **Identify technical debt**
   - Find deprecated functions and methods
   - Identify redundant or duplicate code
   - Look for outdated comments or documentation

2. **Apply code style and conventions**
   - Ensure consistent naming conventions
   - Apply proper docstrings and type hints
   - Format code according to project standards

3. **Update documentation**
   - Update class and function documentation
   - Add examples where helpful
   - Document any non-obvious behavior

4. **Remove or mark deprecated code**
   - Remove unused code if safe to do so
   - Mark deprecated functions with appropriate warnings
   - Provide migration paths for deprecated functionality

#### Code Examples

**Before:**
```python
def old_function(param):
    # This function is no longer used but kept for backward compatibility
    return new_function(param)

def poorly_documented_func(x, y):
    return x + y
```

**After:**
```python
import warnings

def old_function(param):
    """
    Deprecated: Use new_function() directly instead.
    
    This function will be removed in a future version.
    """
    warnings.warn(
        "old_function is deprecated, use new_function instead",
        DeprecationWarning,
        stacklevel=2
    )
    return new_function(param)

def add_values(x: int, y: int) -> int:
    """
    Add two integer values together.
    
    Args:
        x: First integer to add
        y: Second integer to add
        
    Returns:
        The sum of x and y
    """
    return x + y
```

#### Acceptance Criteria
- [ ] Code follows consistent style and conventions
- [ ] Deprecated functions properly marked or removed
- [ ] Documentation updated to reflect changes
- [ ] No new warnings from static analysis tools
- [ ] Code readability improved

#### Testing Strategy
- Run static analysis and linting tools
- Verify documentation is accurate and helpful
- Ensure deprecated function warnings work correctly

---

## Dependencies and Prerequisites

- Access to the full codebase
- Understanding of the new structure in focus_guard/core
- Knowledge of the adapter pattern implementation
- Familiarity with the browser extension code

## Risks and Mitigations

### Risk: Breaking Changes
- **Probability**: Medium
- **Impact**: High
- **Mitigation**: Implement changes incrementally, maintain backward compatibility, thorough testing

### Risk: Circular Dependencies
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**: Careful refactoring, dependency analysis, proper use of dependency injection

### Risk: Test Coverage Gaps
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**: Add tests for any untested code paths, verify test coverage metrics

## Deliverables

1. Updated codebase with no core_v2 references
2. Refactored adapter classes
3. Cleaned up code with improved documentation
4. Passing test suite
5. Documentation of any breaking changes

## Success Criteria

- All imports updated to new structure
- No references to core_v2 remain
- All tests pass after updates
- Code follows consistent style and conventions
- Documentation is up-to-date and accurate

## Next Steps for Week 2

After completing Week 1, the team will be ready to implement robustness improvements in Week 2, including retry mechanisms, enhanced installation verification, and improved error handling.
