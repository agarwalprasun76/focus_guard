"""
Browser Extension Integration Tests.

This module tests the integration between the browser extension and Focus Guard
components, validating real extension behavior patterns and communication protocols.
"""

import asyncio
import json
import time
import tempfile
import logging
import pytest
import requests
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from focus_guard.core.browser.extension.tab_server import TabServer, TabServerConfig
from focus_guard.core.browser.integration.browser_integration import BrowserIntegration
from focus_guard.core.browser.extension.manager import ExtensionManager
from focus_guard.core.browser.extension.robust_installer import RobustExtensionInstaller
from focus_guard.tests.integration.mock_browser_extension import MockBrowserExtension, MockBrowserInfo, MockBrowserScenario

logger = logging.getLogger(__name__)


@pytest.fixture
async def extension_test_server():
    """Create tab server specifically for extension testing."""
    config = TabServerConfig(host='localhost', port=5556)
    server = TabServer(config)
    
    started = server.start(5556)
    if not started:
        pytest.skip("Could not start extension test server")
    
    await asyncio.sleep(1)  # Wait for server to be ready
    
    yield server
    
    server.stop()


@pytest.fixture
async def mock_extension_chrome(extension_test_server):
    """Create mock Chrome extension."""
    extension = MockBrowserExtension(
        tab_server_url=f"http://localhost:{extension_test_server.port}",
        browser_info=MockBrowserInfo(
            name="Chrome",
            version="120.0.6099.109",
            extension_id="chrome-test-extension-id"
        ),
        polling_interval=0.1
    )
    
    if not extension.start():
        pytest.skip("Could not start mock Chrome extension")
    
    yield extension
    
    extension.stop()


@pytest.fixture
async def mock_extension_edge(extension_test_server):
    """Create mock Edge extension."""
    extension = MockBrowserExtension(
        tab_server_url=f"http://localhost:{extension_test_server.port}",
        browser_info=MockBrowserInfo(
            name="Edge",
            version="120.0.2210.61",
            extension_id="edge-test-extension-id"
        ),
        polling_interval=0.1
    )
    
    if not extension.start():
        pytest.skip("Could not start mock Edge extension")
    
    yield extension
    
    extension.stop()


class TestExtensionCommunication:
    """Test communication protocols between extension and tab server."""
    
    @pytest.mark.asyncio
    async def test_extension_registration_and_heartbeat(self, mock_extension_chrome, extension_test_server):
        """Test extension registration and heartbeat mechanism."""
        # Extension should register automatically on start
        await asyncio.sleep(0.5)
        
        # Check server status for registered extension
        response = requests.get(f"http://localhost:{extension_test_server.port}/api/status")
        assert response.status_code == 200
        
        status_data = response.json()
        assert 'browsers' in status_data
        
        # Extension should be sending heartbeats
        stats = mock_extension_chrome.get_stats()
        assert stats['server_requests'] > 0, "Extension should be communicating with server"
        assert stats['running'], "Extension should be running"
    
    @pytest.mark.asyncio
    async def test_tab_data_transmission(self, mock_extension_chrome, extension_test_server):
        """Test tab data transmission from extension to server."""
        # Create test tabs
        tab1 = mock_extension_chrome.create_tab("https://github.com/test", "GitHub Test", active=True)
        tab2 = mock_extension_chrome.create_tab("https://www.youtube.com/watch?v=test", "YouTube Test")
        
        await asyncio.sleep(0.5)
        
        # Check that server received tab data
        response = requests.get(f"http://localhost:{extension_test_server.port}/api/tabs")
        assert response.status_code == 200
        
        tabs_data = response.json()
        assert 'tabs' in tabs_data
        assert len(tabs_data['tabs']) >= 2, "Server should receive tab data"
        
        # Verify tab data structure
        server_tabs = tabs_data['tabs']
        github_tab = next((t for t in server_tabs if 'github.com' in t.get('url', '')), None)
        youtube_tab = next((t for t in server_tabs if 'youtube.com' in t.get('url', '')), None)
        
        assert github_tab is not None, "Should find GitHub tab"
        assert youtube_tab is not None, "Should find YouTube tab"
        assert github_tab['active'] == True, "GitHub tab should be active"
        assert youtube_tab['active'] == False, "YouTube tab should not be active"
    
    @pytest.mark.asyncio
    async def test_command_polling_and_execution(self, mock_extension_chrome, extension_test_server):
        """Test command polling and execution by extension."""
        # Create a tab to close
        tab = mock_extension_chrome.create_tab("https://www.facebook.com", "Facebook Test")
        await asyncio.sleep(0.3)
        
        # Send close command via server
        command_data = {
            "action": "close_tab",
            "data": {
                "tabId": tab.id,
                "reason": "blocked"
            },
            "browser_id": "chrome-test-extension-id"
        }
        
        response = requests.post(
            f"http://localhost:{extension_test_server.port}/api/command",
            json=command_data
        )
        assert response.status_code == 200
        
        # Wait for extension to poll and execute command
        await asyncio.sleep(1)
        
        # Verify tab was closed
        remaining_tabs = mock_extension_chrome.get_tabs()
        tab_ids = [t.id for t in remaining_tabs]
        assert tab.id not in tab_ids, "Tab should be closed by command"
        
        # Verify command was processed
        stats = mock_extension_chrome.get_stats()
        assert stats['commands_received'] > 0, "Extension should have received commands"
    
    @pytest.mark.asyncio
    async def test_multiple_browser_coordination(self, mock_extension_chrome, mock_extension_edge, extension_test_server):
        """Test coordination between multiple browser extensions."""
        # Create tabs in both browsers
        chrome_tab = mock_extension_chrome.create_tab("https://github.com/chrome", "Chrome GitHub")
        edge_tab = mock_extension_edge.create_tab("https://github.com/edge", "Edge GitHub")
        
        await asyncio.sleep(0.5)
        
        # Server should track both browsers
        response = requests.get(f"http://localhost:{extension_test_server.port}/api/tabs")
        assert response.status_code == 200
        
        tabs_data = response.json()
        server_tabs = tabs_data['tabs']
        
        # Should have tabs from both browsers
        chrome_tabs = [t for t in server_tabs if 'chrome' in t.get('url', '')]
        edge_tabs = [t for t in server_tabs if 'edge' in t.get('url', '')]
        
        assert len(chrome_tabs) >= 1, "Should have Chrome tabs"
        assert len(edge_tabs) >= 1, "Should have Edge tabs"
        
        # Test browser-specific commands
        chrome_command = {
            "action": "close_tab",
            "data": {"tabId": chrome_tab.id},
            "browser_id": "chrome-test-extension-id"
        }
        
        edge_command = {
            "action": "close_tab", 
            "data": {"tabId": edge_tab.id},
            "browser_id": "edge-test-extension-id"
        }
        
        # Send commands to specific browsers
        requests.post(f"http://localhost:{extension_test_server.port}/api/command", json=chrome_command)
        requests.post(f"http://localhost:{extension_test_server.port}/api/command", json=edge_command)
        
        await asyncio.sleep(1)
        
        # Verify each browser processed only its command
        chrome_tabs_remaining = [t.id for t in mock_extension_chrome.get_tabs()]
        edge_tabs_remaining = [t.id for t in mock_extension_edge.get_tabs()]
        
        assert chrome_tab.id not in chrome_tabs_remaining, "Chrome tab should be closed"
        assert edge_tab.id not in edge_tabs_remaining, "Edge tab should be closed"


class TestExtensionBehaviorPatterns:
    """Test realistic browser extension behavior patterns."""
    
    @pytest.mark.asyncio
    async def test_rapid_tab_creation_and_navigation(self, mock_extension_chrome, extension_test_server):
        """Test handling of rapid tab creation and navigation."""
        # Simulate rapid browsing behavior
        urls = [
            "https://www.google.com/search?q=test1",
            "https://www.google.com/search?q=test2", 
            "https://github.com/user/repo1",
            "https://github.com/user/repo2",
            "https://stackoverflow.com/questions/1",
            "https://stackoverflow.com/questions/2"
        ]
        
        # Create tabs rapidly
        created_tabs = []
        for url in urls:
            tab = mock_extension_chrome.create_tab(url, f"Tab for {url}")
            created_tabs.append(tab)
            await asyncio.sleep(0.05)  # Very fast tab creation
        
        await asyncio.sleep(1)  # Wait for all data to be sent
        
        # Server should handle all tabs
        response = requests.get(f"http://localhost:{extension_test_server.port}/api/tabs")
        tabs_data = response.json()
        server_tabs = tabs_data['tabs']
        
        assert len(server_tabs) >= len(urls), "Server should handle rapid tab creation"
        
        # Test rapid navigation (URL changes)
        for i, tab in enumerate(created_tabs[:3]):
            new_url = f"https://updated-site-{i}.com"
            mock_extension_chrome.update_tab(tab.id, url=new_url)
            await asyncio.sleep(0.05)
        
        await asyncio.sleep(0.5)
        
        # Server should receive updated tab data
        response = requests.get(f"http://localhost:{extension_test_server.port}/api/tabs")
        updated_tabs_data = response.json()
        updated_server_tabs = updated_tabs_data['tabs']
        
        updated_urls = [t.get('url', '') for t in updated_server_tabs]
        assert any('updated-site-0.com' in url for url in updated_urls), "Should handle rapid navigation"
    
    @pytest.mark.asyncio
    async def test_tab_lifecycle_events(self, mock_extension_chrome, extension_test_server):
        """Test complete tab lifecycle event handling."""
        # Track events
        events_received = []
        
        def track_tab_created(tab):
            events_received.append(('created', tab.id, tab.url))
        
        def track_tab_updated(tab):
            events_received.append(('updated', tab.id, tab.url))
        
        def track_tab_closed(tab_id):
            events_received.append(('closed', tab_id, None))
        
        # Register event callbacks
        mock_extension_chrome.on_tab_created(track_tab_created)
        mock_extension_chrome.on_tab_updated(track_tab_updated)
        mock_extension_chrome.on_tab_closed(track_tab_closed)
        
        # Create tab
        tab = mock_extension_chrome.create_tab("https://example.com", "Example")
        await asyncio.sleep(0.2)
        
        # Update tab
        mock_extension_chrome.update_tab(tab.id, url="https://updated-example.com", title="Updated Example")
        await asyncio.sleep(0.2)
        
        # Close tab
        mock_extension_chrome.close_tab(tab.id)
        await asyncio.sleep(0.2)
        
        # Verify event sequence
        assert len(events_received) == 3, "Should receive all lifecycle events"
        assert events_received[0][0] == 'created', "First event should be created"
        assert events_received[1][0] == 'updated', "Second event should be updated"
        assert events_received[2][0] == 'closed', "Third event should be closed"
        assert events_received[0][1] == events_received[1][1] == events_received[2][1], "All events should be for same tab"
    
    @pytest.mark.asyncio
    async def test_browser_session_simulation(self, mock_extension_chrome, extension_test_server):
        """Test realistic browser session simulation."""
        scenario = MockBrowserScenario(mock_extension_chrome)
        
        # Run a short productivity session
        session_task = asyncio.create_task(
            asyncio.to_thread(scenario._productivity_session, 3.0)
        )
        
        # Monitor server during session
        initial_stats = mock_extension_chrome.get_stats()
        
        await session_task
        await asyncio.sleep(0.5)
        
        final_stats = mock_extension_chrome.get_stats()
        
        # Verify session activity
        assert final_stats['tabs_created'] > initial_stats['tabs_created'], "Should create tabs during session"
        assert final_stats['server_requests'] > initial_stats['server_requests'], "Should send data to server"
        
        # Check server received session data
        response = requests.get(f"http://localhost:{extension_test_server.port}/api/tabs")
        tabs_data = response.json()
        
        # Should have productivity-related tabs
        productivity_domains = ['github.com', 'stackoverflow.com', 'docs.google.com', 'notion.so']
        server_tabs = tabs_data['tabs']
        productivity_tabs = [
            t for t in server_tabs 
            if any(domain in t.get('url', '') for domain in productivity_domains)
        ]
        
        assert len(productivity_tabs) > 0, "Should have productivity tabs from session"


class TestExtensionErrorHandling:
    """Test extension error handling and recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_server_disconnection_recovery(self, mock_extension_chrome):
        """Test extension behavior when server is unavailable."""
        # Extension starts without server
        initial_stats = mock_extension_chrome.get_stats()
        
        # Create tabs while server is unavailable
        tab1 = mock_extension_chrome.create_tab("https://github.com/offline", "Offline Test")
        tab2 = mock_extension_chrome.create_tab("https://www.youtube.com/offline", "Offline YouTube")
        
        await asyncio.sleep(1)
        
        # Extension should handle server unavailability gracefully
        current_stats = mock_extension_chrome.get_stats()
        assert current_stats['running'], "Extension should still be running"
        assert current_stats['tabs_created'] == initial_stats['tabs_created'] + 2, "Should still create tabs locally"
        assert current_stats['errors'] > 0, "Should record server connection errors"
    
    @pytest.mark.asyncio
    async def test_malformed_command_handling(self, mock_extension_chrome, extension_test_server):
        """Test handling of malformed commands from server."""
        # Create tab
        tab = mock_extension_chrome.create_tab("https://test.com", "Test")
        await asyncio.sleep(0.3)
        
        # Send malformed commands
        malformed_commands = [
            {"action": "invalid_action", "data": {}},
            {"action": "close_tab"},  # Missing data
            {"action": "close_tab", "data": {"tabId": "not_a_number"}},
            {"invalid": "structure"},
            None,
            ""
        ]
        
        initial_error_count = mock_extension_chrome.get_stats()['errors']
        
        for bad_command in malformed_commands:
            try:
                response = requests.post(
                    f"http://localhost:{extension_test_server.port}/api/command",
                    json=bad_command,
                    timeout=2
                )
            except:
                pass  # Expected for malformed requests
            
            await asyncio.sleep(0.1)
        
        await asyncio.sleep(1)  # Wait for processing
        
        # Extension should handle malformed commands gracefully
        final_stats = mock_extension_chrome.get_stats()
        assert final_stats['running'], "Extension should still be running"
        
        # Tab should still exist (not closed by malformed commands)
        remaining_tabs = mock_extension_chrome.get_tabs()
        tab_ids = [t.id for t in remaining_tabs]
        assert tab.id in tab_ids, "Tab should not be affected by malformed commands"
    
    @pytest.mark.asyncio
    async def test_high_frequency_command_handling(self, mock_extension_chrome, extension_test_server):
        """Test handling of high-frequency commands."""
        # Create multiple tabs
        tabs = []
        for i in range(10):
            tab = mock_extension_chrome.create_tab(f"https://test{i}.com", f"Test {i}")
            tabs.append(tab)
        
        await asyncio.sleep(0.5)
        
        # Send many commands rapidly
        commands_sent = 0
        for tab in tabs:
            command = {
                "action": "close_tab",
                "data": {"tabId": tab.id},
                "browser_id": "chrome-test-extension-id"
            }
            
            try:
                requests.post(
                    f"http://localhost:{extension_test_server.port}/api/command",
                    json=command,
                    timeout=1
                )
                commands_sent += 1
            except:
                pass
            
            await asyncio.sleep(0.01)  # Very rapid commands
        
        await asyncio.sleep(2)  # Wait for processing
        
        # Extension should handle high-frequency commands
        final_stats = mock_extension_chrome.get_stats()
        assert final_stats['running'], "Extension should handle high-frequency commands"
        assert final_stats['commands_received'] > 0, "Should process some commands"
        
        # Most tabs should be closed
        remaining_tabs = mock_extension_chrome.get_tabs()
        assert len(remaining_tabs) < len(tabs), "Should close some tabs"


class TestExtensionPerformance:
    """Test extension performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, mock_extension_chrome, extension_test_server):
        """Test that extension memory usage remains stable."""
        # Create and close many tabs to test memory stability
        for cycle in range(5):
            # Create tabs
            created_tabs = []
            for i in range(20):
                tab = mock_extension_chrome.create_tab(f"https://cycle{cycle}-tab{i}.com", f"Cycle {cycle} Tab {i}")
                created_tabs.append(tab)
            
            await asyncio.sleep(0.5)
            
            # Close half the tabs
            for tab in created_tabs[::2]:
                mock_extension_chrome.close_tab(tab.id)
            
            await asyncio.sleep(0.5)
        
        # Extension should remain stable
        final_stats = mock_extension_chrome.get_stats()
        assert final_stats['running'], "Extension should remain stable"
        assert final_stats['errors'] < 10, "Should have minimal errors"  # Allow some network errors
    
    @pytest.mark.asyncio
    async def test_response_time_consistency(self, mock_extension_chrome, extension_test_server):
        """Test that extension response times remain consistent."""
        response_times = []
        
        for i in range(10):
            start_time = time.time()
            
            # Create tab and wait for server communication
            tab = mock_extension_chrome.create_tab(f"https://timing-test-{i}.com", f"Timing Test {i}")
            await asyncio.sleep(0.3)  # Wait for data to be sent
            
            elapsed = time.time() - start_time
            response_times.append(elapsed)
            
            # Clean up
            mock_extension_chrome.close_tab(tab.id)
        
        # Response times should be consistent
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        assert avg_response_time < 1.0, "Average response time should be reasonable"
        assert max_response_time < 2.0, "Max response time should be reasonable"
        
        # Variance should be low (consistent performance)
        variance = sum((t - avg_response_time) ** 2 for t in response_times) / len(response_times)
        assert variance < 0.5, "Response times should be consistent"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "--tb=short"])
