# Comprehensive pytest-asyncio Migration Guide

## Overview
This guide provides a systematic approach to migrate all coordinator tests from unittest to pytest-asyncio with AsyncMock.

## Migration Strategy

### 1. Identify Test Patterns
- **unittest.TestCase** → **pytest.mark.asyncio** class
- **asyncio.run()** → **async def test_...()**
- **Mock()** → **AsyncMock()** for async methods
- **setUp()** → **@pytest.fixture**

### 2. File Naming Convention
- Original: `test_component.py`
- Migrated: `test_component_pytest.py`
- Backup: Keep original files until migration is complete

### 3. Key Transformations

#### A. Class Structure
```python
# BEFORE (unittest)
class TestComponent(unittest.TestCase):
    def setUp(self):
        self.mock = Mock()
    
    def test_method(self):
        result = asyncio.run(self.component.method())

# AFTER (pytest-asyncio)
@pytest.mark.asyncio
class TestComponentPytest:
    @pytest.fixture
    def mock(self):
        return AsyncMock()
    
    async def test_method(self, mock):
        result = await self.component.method()
```

#### B. Mock Patterns
```python
# BEFORE
mock = Mock()
mock.method = Mock(return_value=True)

# AFTER
mock = MagicMock()
mock.method = AsyncMock(return_value=True)
```

#### C. Test Method Patterns
```python
# BEFORE
def test_something(self):
    async def run_test():
        return await self.component.method()
    result = asyncio.run(run_test())

# AFTER
async def test_something(self, component):
    result = await component.method()
```

## Migration Checklist

### Step 1: Analyze Original Test
- [ ] Count total test methods
- [ ] Identify async method calls
- [ ] List all mock objects and their usage
- [ ] Note event handling patterns

### Step 2: Create Migration Template
- [ ] Set up pytest fixtures for all mocks
- [ ] Convert async calls to await syntax
- [ ] Update assertion methods (assertEqual → assert)
- [ ] Handle event bus subscriptions properly

### Step 3: Test Validation
- [ ] Run original tests to establish baseline
- [ ] Run migrated tests and fix issues
- [ ] Ensure test count matches original
- [ ] Verify all functionality is preserved

## Component-Specific Patterns

### AlertSystemComponent
- **Async Methods**: show_alert, dismiss_alert, clear_alerts
- **Event Handling**: DISTRACTION_DETECTED, DISTRACTION_RESOLVED, IDLE_STATE_CHANGED
- **Config Changes**: alert_system.enabled, alert_system.cooldown_seconds

### Common Issues and Solutions

#### Issue 1: AsyncMock vs MagicMock
```python
# WRONG - will cause test failures
mock = MagicMock()
mock.async_method = MagicMock()  # Should be AsyncMock

# CORRECT
mock = MagicMock()
mock.async_method = AsyncMock(return_value=True)
```

#### Issue 2: Event Bus Subscriptions
```python
# Original tests may use DefaultEventBus()
# Migrated tests should use AsyncMock for event_bus
```

#### Issue 3: Component Initialization
```python
# Ensure proper async initialization
await component.initialize()
await component.start()  # If needed for tests
```

## Migration Script Template

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
class Test{Component}Pytest:
    
    @pytest.fixture
    def {dependency}(self):
        """Mock {dependency} with proper async behavior."""
        mock = MagicMock()
        mock.async_method = AsyncMock(return_value=True)
        return mock
    
    @pytest.fixture
    def component(self, {all_dependencies}):
        """Create component instance with mocked dependencies."""
        return {Component}({all_dependencies})
    
    async def test_{original_test_name}(self, component, {dependencies}):
        """Test {description} - migrated from unittest."""
        await component.initialize()
        
        # Test logic here
        result = await component.method()
        assert result is True
```

## Validation Commands

```bash
# Run original tests
python -m pytest tests/core_v2/coordinator/test_original.py -v

# Run migrated tests
python -m pytest tests/core_v2/coordinator/test_original_pytest.py -v

# Compare test counts
# Should have same or more tests than original
```

## Quality Assurance

1. **Test Count**: Ensure migrated file has ≥ original test count
2. **Coverage**: Verify all async paths are tested
3. **Mock Accuracy**: Ensure AsyncMock is used for async methods
4. **Event Handling**: Verify event bus interactions
5. **Error Handling**: Ensure exceptions are properly handled

## Next Steps

1. **Batch Migration**: Process 2-3 components at a time
2. **Validation**: Run tests after each migration
3. **Documentation**: Update this guide based on findings
4. **Cleanup**: Remove old files after successful migration

## Migration Order (Priority)

1. **test_alert_component.py** → **test_alert_component_pytest.py** (✅ Created)
2. **test_activity_component.py** → **test_activity_component_pytest.py**
3. **test_browser_component.py** → **test_browser_component_pytest.py**
4. **test_classification_component.py** → **test_classification_component_pytest.py**
5. **test_config_component.py** → **test_config_component_pytest.py**
6. **test_coordinator.py** → **test_coordinator_pytest.py**
7. **test_coordinator_integration.py** → **test_coordinator_integration_pytest.py**

## Common Fixes

### Fix 1: Component Interface Mismatches
- Check actual component constructor signatures
- Ensure mock setup matches component expectations
- Use proper async/await patterns

### Fix 2: Event Bus Mocking
- Use AsyncMock for async event methods
- Ensure proper event data structure
- Mock publish/subscribe methods appropriately

### Fix 3: Configuration Mocking
- Use AsyncMock for config get/set methods
- Ensure proper return values for config paths
- Handle nested config structures
