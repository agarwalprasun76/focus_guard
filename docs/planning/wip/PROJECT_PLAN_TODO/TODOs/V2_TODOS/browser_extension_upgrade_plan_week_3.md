# Browser Extension Upgrade Plan - Week 3: Test Coverage Enhancement

## Overview

Week 3 focuses on enhancing test coverage for the browser extension installation and integration code. After implementing robustness improvements in Week 2, this phase adds comprehensive tests for previously untested components, creates end-to-end installation tests, and implements communication tests to ensure reliable operation.

## Detailed Tasks

### Task 3.1: Add NativeMessagingHostManager Tests

**Priority**: P0 - Critical  
**Effort**: 2 days  
**Owner**: TBD

#### Description
Create comprehensive tests for the NativeMessagingHostManager class, which currently lacks test coverage. These tests will verify manifest creation/installation, Windows registry integration, and error handling.

#### Steps
1. **Set up test environment**
   - Create test fixtures for NativeMessagingHostManager
   - Set up mocks for registry operations
   - Prepare test manifests and configurations

2. **Implement manifest tests**
   - Test manifest creation with various configurations
   - Test manifest validation
   - Test manifest installation and removal

3. **Implement registry tests**
   - Test registry key creation and removal
   - Test registry access error handling
   - Test registry validation

4. **Implement error handling tests**
   - Test error scenarios for manifest operations
   - Test error scenarios for registry operations
   - Test recovery mechanisms

5. **Implement integration tests**
   - Test interaction with browser extension manager
   - Test end-to-end native host setup
   - Test with different browser types

#### Code Examples

**Test Fixtures:**
```python
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from focus_guard.core.browser.extension.native_host import NativeMessagingHostManager

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test manifests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def mock_registry():
    """Mock Windows registry operations."""
    with patch('focus_guard.core.browser.extension.native_host.winreg') as mock_winreg:
        # Set up mock registry behavior
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.CreateKey.return_value = mock_key
        mock_winreg.HKEY_CURRENT_USER = "HKEY_CURRENT_USER"
        mock_winreg.KEY_WRITE = 0x20006
        mock_winreg.KEY_READ = 0x20019
        yield mock_winreg

@pytest.fixture
def native_host_manager(temp_dir, mock_registry):
    """Create a NativeMessagingHostManager instance for testing."""
    manager = NativeMessagingHostManager(
        extension_id="test_extension_id",
        manifest_dir=temp_dir
    )
    return manager
```

**Manifest Tests:**
```python
import json
import os

def test_create_manifest(native_host_manager, temp_dir):
    """Test creation of native messaging host manifest."""
    # Arrange
    host_name = "com.focusguard.test"
    executable_path = os.path.join(temp_dir, "test_executable.exe")
    allowed_origins = ["chrome-extension://test_extension_id/"]
    
    # Act
    manifest_path = native_host_manager.create_manifest(
        host_name=host_name,
        executable_path=executable_path,
        allowed_origins=allowed_origins
    )
    
    # Assert
    assert os.path.exists(manifest_path)
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    assert manifest["name"] == host_name
    assert manifest["path"] == executable_path
    assert manifest["allowed_origins"] == allowed_origins
    assert manifest["type"] == "stdio"

def test_validate_manifest(native_host_manager, temp_dir):
    """Test validation of native messaging host manifest."""
    # Arrange
    host_name = "com.focusguard.test"
    executable_path = os.path.join(temp_dir, "test_executable.exe")
    allowed_origins = ["chrome-extension://test_extension_id/"]
    
    # Create a valid manifest
    manifest_path = native_host_manager.create_manifest(
        host_name=host_name,
        executable_path=executable_path,
        allowed_origins=allowed_origins
    )
    
    # Act & Assert
    assert native_host_manager.validate_manifest(manifest_path)
    
    # Create an invalid manifest
    invalid_manifest_path = os.path.join(temp_dir, "invalid_manifest.json")
    with open(invalid_manifest_path, 'w') as f:
        json.dump({"name": host_name}, f)  # Missing required fields
    
    # Act & Assert
    assert not native_host_manager.validate_manifest(invalid_manifest_path)
```

**Registry Tests:**
```python
def test_install_chrome_registry(native_host_manager, mock_registry, temp_dir):
    """Test installation of Chrome registry keys."""
    # Arrange
    host_name = "com.focusguard.test"
    manifest_path = os.path.join(temp_dir, f"{host_name}.json")
    
    # Create a test manifest
    with open(manifest_path, 'w') as f:
        json.dump({
            "name": host_name,
            "path": os.path.join(temp_dir, "test_executable.exe"),
            "allowed_origins": ["chrome-extension://test_extension_id/"],
            "type": "stdio"
        }, f)
    
    # Act
    result = native_host_manager.install_chrome_registry(host_name, manifest_path)
    
    # Assert
    assert result
    mock_registry.CreateKey.assert_called()
    mock_registry.SetValueEx.assert_called()

def test_registry_error_handling(native_host_manager, mock_registry):
    """Test handling of registry access errors."""
    # Arrange
    host_name = "com.focusguard.test"
    manifest_path = "nonexistent_path.json"
    
    # Simulate registry error
    mock_registry.CreateKey.side_effect = Exception("Access denied")
    
    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        native_host_manager.install_chrome_registry(host_name, manifest_path)
    
    assert "Access denied" in str(exc_info.value)
```

#### Acceptance Criteria
- [ ] Unit tests for manifest creation/installation
- [ ] Tests for Windows registry integration
- [ ] Tests for error handling and edge cases
- [ ] 90%+ code coverage for NativeMessagingHostManager
- [ ] Tests integrated with CI pipeline
- [ ] Documentation of test approach

#### Testing Strategy
- Use pytest for all tests
- Mock Windows registry operations
- Use temporary directories for test manifests
- Test both success and failure scenarios
- Verify proper error handling

---

### Task 3.2: Create End-to-End Installation Tests

**Priority**: P1 - High  
**Effort**: 3 days  
**Owner**: TBD

#### Description
Implement end-to-end tests for the complete browser extension installation process, including browser detection, extension installation, native host setup, and verification.

#### Steps
1. **Design test framework**
   - Create test fixtures for end-to-end testing
   - Set up mocks for browser processes
   - Define test scenarios and success criteria

2. **Implement Chrome extension tests**
   - Test Chrome detection
   - Test Chrome extension installation
   - Test Chrome extension verification

3. **Implement Edge extension tests**
   - Test Edge detection
   - Test Edge extension installation
   - Test Edge extension verification

4. **Implement native host tests**
   - Test native host setup for Chrome
   - Test native host setup for Edge
   - Test native host verification

5. **Implement installation verification tests**
   - Test verification of complete installation
   - Test handling of partial installations
   - Test recovery from failed installations

#### Code Examples

**End-to-End Test Framework:**
```python
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from focus_guard.core.browser.extension.manager import BrowserExtensionManager
from focus_guard.core.browser.extension.installer import ExtensionInstaller
from focus_guard.core.browser.extension.native_host import NativeMessagingHostManager

@pytest.fixture
def mock_browser_processes():
    """Mock browser process detection and management."""
    with patch('focus_guard.core.browser.extension.manager.subprocess') as mock_subprocess:
        # Set up mock process behavior
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_subprocess.Popen.return_value = mock_process
        yield mock_subprocess

@pytest.fixture
def mock_browser_paths():
    """Mock browser executable paths."""
    with patch('focus_guard.core.browser.extension.manager.BrowserExtensionManager._get_browser_path') as mock_get_path:
        mock_get_path.return_value = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        yield mock_get_path

@pytest.fixture
def extension_installer(mock_browser_processes, mock_browser_paths):
    """Create an ExtensionInstaller instance for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        installer = ExtensionInstaller(
            extension_dir=os.path.join(temp_dir, "extension"),
            native_messaging_host_path=os.path.join(temp_dir, "native_host.exe")
        )
        yield installer
```

**End-to-End Installation Test:**
```python
@pytest.mark.asyncio
async def test_chrome_extension_installation(extension_installer, mock_browser_processes):
    """Test end-to-end Chrome extension installation."""
    # Arrange
    # Create test extension directory
    os.makedirs(extension_installer.extension_dir, exist_ok=True)
    with open(os.path.join(extension_installer.extension_dir, "manifest.json"), "w") as f:
        f.write('{"name": "Test Extension", "version": "1.0"}')
    
    # Mock successful browser launch
    mock_browser_processes.Popen.return_value.returncode = 0
    
    # Act
    result = await extension_installer.install_extension_for_browser("chrome")
    
    # Assert
    assert result.success
    assert "chrome" in result.browser_type.lower()
    mock_browser_processes.Popen.assert_called()
    
    # Verify installation status
    status = await extension_installer.verify_extension_installation("chrome")
    assert status.is_installed

@pytest.mark.asyncio
async def test_failed_installation_recovery(extension_installer, mock_browser_processes):
    """Test recovery from failed installation."""
    # Arrange
    # Create test extension directory
    os.makedirs(extension_installer.extension_dir, exist_ok=True)
    with open(os.path.join(extension_installer.extension_dir, "manifest.json"), "w") as f:
        f.write('{"name": "Test Extension", "version": "1.0"}')
    
    # Mock failed browser launch followed by successful launch
    mock_browser_processes.Popen.side_effect = [
        MagicMock(returncode=1),  # First attempt fails
        MagicMock(returncode=0)   # Second attempt succeeds
    ]
    
    # Act
    result = await extension_installer.install_extension_for_browser("chrome")
    
    # Assert
    assert result.success
    assert mock_browser_processes.Popen.call_count == 2  # Verify retry happened
```

#### Acceptance Criteria
- [ ] Tests for Chrome extension installation
- [ ] Tests for Edge extension installation
- [ ] Tests for native host setup
- [ ] Tests for installation verification
- [ ] Tests for recovery from failures
- [ ] Documentation of test scenarios

#### Testing Strategy
- Use pytest-asyncio for async tests
- Mock browser processes and file operations
- Test complete installation flow
- Verify proper error handling and recovery
- Test with different browser configurations

---

### Task 3.3: Add Communication Tests

**Priority**: P1 - High  
**Effort**: 2 days  
**Owner**: TBD

#### Description
Create tests for extension-application communication, including tab data flow, command execution, error handling, and reconnection scenarios.

#### Steps
1. **Set up communication test environment**
   - Create test fixtures for tab server
   - Set up mocks for HTTP requests
   - Prepare test data for tab events

2. **Implement tab data flow tests**
   - Test sending tab data from extension to application
   - Test processing of tab data by tab server
   - Test storage and retrieval of tab data

3. **Implement command execution tests**
   - Test sending commands from application to extension
   - Test command processing by tab server
   - Test command execution by extension

4. **Implement error handling tests**
   - Test handling of communication errors
   - Test timeout scenarios
   - Test malformed data handling

5. **Implement reconnection tests**
   - Test detection of lost connections
   - Test automatic reconnection
   - Test data synchronization after reconnection

#### Code Examples

**Communication Test Fixtures:**
```python
import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from focus_guard.core.browser.extension.tab_server import TabServer

@pytest.fixture
async def tab_server():
    """Create a TabServer instance for testing."""
    server = TabServer(port=0)  # Use port 0 to let OS assign a free port
    await server.start()
    yield server
    await server.stop()

@pytest.fixture
async def mock_http_client(tab_server):
    """Create a test HTTP client for the tab server."""
    app = web.Application()
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    client.server_port = tab_server.port
    yield client
    await client.close()

@pytest.fixture
def mock_tab_data():
    """Create mock tab data for testing."""
    return {
        "tabs": [
            {
                "id": 1,
                "url": "https://example.com",
                "title": "Example Domain",
                "active": True,
                "windowId": 1
            },
            {
                "id": 2,
                "url": "https://test.com",
                "title": "Test Website",
                "active": False,
                "windowId": 1
            }
        ],
        "browser": "chrome",
        "timestamp": 1628097600000
    }
```

**Tab Data Flow Tests:**
```python
@pytest.mark.asyncio
async def test_tab_data_submission(mock_http_client, tab_server, mock_tab_data):
    """Test submission of tab data to tab server."""
    # Arrange
    url = f"http://localhost:{mock_http_client.server_port}/tabs"
    
    # Act
    response = await mock_http_client.post(
        url,
        json=mock_tab_data
    )
    
    # Assert
    assert response.status == 200
    response_data = await response.json()
    assert response_data["success"] is True
    
    # Verify tab data was stored
    stored_tabs = tab_server.get_all_tabs()
    assert len(stored_tabs) == 2
    assert stored_tabs[0]["url"] == "https://example.com"
    assert stored_tabs[1]["url"] == "https://test.com"

@pytest.mark.asyncio
async def test_tab_data_retrieval(mock_http_client, tab_server, mock_tab_data):
    """Test retrieval of tab data from tab server."""
    # Arrange
    # Submit tab data first
    submit_url = f"http://localhost:{mock_http_client.server_port}/tabs"
    await mock_http_client.post(submit_url, json=mock_tab_data)
    
    # Act
    get_url = f"http://localhost:{mock_http_client.server_port}/tabs"
    response = await mock_http_client.get(get_url)
    
    # Assert
    assert response.status == 200
    response_data = await response.json()
    assert len(response_data["tabs"]) == 2
    assert response_data["tabs"][0]["url"] == "https://example.com"
```

**Command Execution Tests:**
```python
@pytest.mark.asyncio
async def test_command_execution(mock_http_client, tab_server):
    """Test sending and executing commands via tab server."""
    # Arrange
    command_url = f"http://localhost:{mock_http_client.server_port}/command"
    command_data = {
        "command": "close_tab",
        "tab_id": 1,
        "browser": "chrome"
    }
    
    # Act
    response = await mock_http_client.post(
        command_url,
        json=command_data
    )
    
    # Assert
    assert response.status == 200
    response_data = await response.json()
    assert response_data["success"] is True
    
    # Verify command was queued
    commands = tab_server.get_pending_commands("chrome")
    assert len(commands) == 1
    assert commands[0]["command"] == "close_tab"
    assert commands[0]["tab_id"] == 1
```

#### Acceptance Criteria
- [ ] Tests for tab data flow
- [ ] Tests for command execution
- [ ] Tests for error handling
- [ ] Tests for reconnection scenarios
- [ ] 90%+ code coverage for communication components
- [ ] Documentation of test approach

#### Testing Strategy
- Use pytest-asyncio for async tests
- Test HTTP endpoints directly
- Verify data flow in both directions
- Test error scenarios and edge cases
- Verify proper handling of concurrent requests

---

## Dependencies and Prerequisites

- Completion of Week 1 and Week 2 tasks
- Understanding of pytest and pytest-asyncio
- Knowledge of mocking techniques
- Familiarity with HTTP testing

## Risks and Mitigations

### Risk: Complex Async Testing
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**: Use pytest-asyncio, proper test fixtures, clear test documentation

### Risk: Mock Limitations
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**: Combine mocks with controlled real components where necessary, thorough test design

### Risk: Test Environment Stability
- **Probability**: Low
- **Impact**: High
- **Mitigation**: Robust test cleanup, isolated test environments, proper resource management

## Deliverables

1. NativeMessagingHostManager test suite
2. End-to-end installation tests
3. Communication test suite
4. Test documentation
5. Code coverage report

## Success Criteria

- 90%+ code coverage for all components
- All critical paths tested
- Edge cases and error scenarios covered
- Tests integrated with CI pipeline
- Documentation of test approach

## Next Steps for Week 4

After completing Week 3, the team will be ready to implement communication reliability improvements in Week 4, including health checks, reconnection strategies, and potentially a WebSocket alternative for more reliable communication.
