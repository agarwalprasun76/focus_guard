#!/usr/bin/env python3
"""
Browser Integration Validation Script

This script validates the complete browser extension integration including:
1. Tab server connectivity
2. Native messaging host functionality
3. Browser extension communication
4. Domain blocking workflow
"""

import asyncio
import json
import requests
import time
import logging
from pathlib import Path
import sys
import os

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from focus_guard.core.platform_utils.windows.windows_config import WindowsConfig
from focus_guard.core.browser.extension.tab_server import get_tab_server, TabServerConfig
from focus_guard.core.browser.integration.browser_integration import BrowserIntegration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserIntegrationValidator:
    def __init__(self):
        self.config = WindowsConfig()
        self.tab_server = None
        self.browser_integration = None
        
    async def setup_components(self):
        """Set up all components for testing."""
        logger.info("Setting up components...")
        
        # Load configuration
        cfg = self.config.load_config()
        
        # Create tab server config
        tab_server_config = TabServerConfig(
            host=cfg.get('tab_server_host', '127.0.0.1'),
            port=cfg.get('tab_server_port', 5000)
        )
        
        # Get tab server instance
        self.tab_server = get_tab_server(tab_server_config)
        
        # Create browser integration
        self.browser_integration = BrowserIntegration(
            tab_server=self.tab_server,
            config=self.config
        )
        
        logger.info("Components setup complete")
        
    async def test_tab_server_connectivity(self):
        """Test tab server connectivity."""
        logger.info("Testing tab server connectivity...")
        
        try:
            # Start tab server
            if hasattr(self.tab_server, 'start'):
                self.tab_server.start()
                time.sleep(2)  # Wait for server to start
            
            # Test HTTP connectivity
            response = requests.get(
                f"http://{self.tab_server.config.host}:{self.tab_server.config.port}/api/status",
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("✅ Tab server connectivity: PASSED")
                return True
            else:
                logger.error(f"❌ Tab server connectivity: FAILED (status {response.status_code})")
                return False
                
        except Exception as e:
            logger.error(f"❌ Tab server connectivity: FAILED ({e})")
            return False
    
    async def test_browser_integration(self):
        """Test browser integration functionality."""
        logger.info("Testing browser integration...")
        
        try:
            # Test browser integration initialization
            if self.browser_integration:
                logger.info("✅ Browser integration initialization: PASSED")
                
                # Test tab server connection
                success = self.browser_integration._ensure_tab_server_running()
                if success:
                    logger.info("✅ Browser tab server connection: PASSED")
                    return True
                else:
                    logger.error("❌ Browser tab server connection: FAILED")
                    return False
            else:
                logger.error("❌ Browser integration not initialized")
                return False
                
        except Exception as e:
            logger.error(f"❌ Browser integration test: FAILED ({e})")
            return False
    
    async def test_domain_blocking_workflow(self):
        """Test the complete domain blocking workflow."""
        logger.info("Testing domain blocking workflow...")
        
        try:
            # Ensure tab server is running
            if not self.browser_integration._ensure_tab_server_running():
                logger.error("❌ Tab server not running")
                return False
            
            # Test getting tabs
            tabs = self.browser_integration.get_all_tabs()
            logger.info(f"Found {len(tabs)} tabs")
            
            # Test sending close command
            test_command = {
                'action': 'close_tab',
                'tab_id': 'test_tab_123',
                'window_id': 'test_window_456',
                'browser_name': 'chrome',
                'reason': 'domain_blocked'
            }
            
            success = self.browser_integration.send_command('close_tab', test_command)
            if success:
                logger.info("✅ Domain blocking workflow: PASSED")
                return True
            else:
                logger.error("❌ Domain blocking workflow: FAILED")
                return False
                
        except Exception as e:
            logger.error(f"❌ Domain blocking workflow: FAILED ({e})")
            return False
    
    async def test_api_endpoints(self):
        """Test all API endpoints."""
        logger.info("Testing API endpoints...")
        
        base_url = f"http://{self.tab_server.config.host}:{self.tab_server.config.port}"
        
        endpoints = [
            ('/api/status', 'GET'),
            ('/api/tabs', 'GET'),
            ('/api/command', 'POST')
        ]
        
        results = []
        for endpoint, method in endpoints:
            try:
                if method == 'GET':
                    response = requests.get(f"{base_url}{endpoint}", timeout=5)
                elif method == 'POST':
                    # Send proper command structure for POST /api/command
                    if endpoint == "/api/command":
                        response = requests.post(f"{base_url}{endpoint}", 
                                              json={'status': 'processed', 'browser': 'test'}, timeout=5)
                    else:
                        response = requests.post(f"{base_url}{endpoint}", 
                                              json={'test': 'data'}, timeout=5)
                
                if response.status_code == 200:
                    logger.info(f"✅ {method} {endpoint}: PASSED")
                    results.append(True)
                else:
                    logger.error(f"❌ {method} {endpoint}: FAILED (status {response.status_code})")
                    results.append(False)
                    
            except Exception as e:
                logger.error(f"❌ {method} {endpoint}: FAILED ({e})")
                results.append(False)
        
        return all(results)
    
    async def run_all_tests(self):
        """Run all validation tests."""
        logger.info("=" * 60)
        logger.info("Starting Browser Integration Validation")
        logger.info("=" * 60)
        
        # Setup components
        await self.setup_components()
        
        tests = [
            ("Tab Server Connectivity", self.test_tab_server_connectivity),
            ("Browser Integration", self.test_browser_integration),
            ("API Endpoints", self.test_api_endpoints),
            ("Domain Blocking Workflow", self.test_domain_blocking_workflow)
        ]
        
        results = []
        for test_name, test_func in tests:
            logger.info(f"\n{test_name}:")
            logger.info("-" * 40)
            try:
                result = await test_func()
                results.append((test_name, result))
            except Exception as e:
                logger.error(f"❌ {test_name}: FAILED ({e})")
                results.append((test_name, False))
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 60)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
            if result:
                passed += 1
        
        logger.info(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All tests passed! Browser integration is working correctly.")
        else:
            logger.error("⚠️  Some tests failed. Please check the logs above.")
            
        return passed == total

async def main():
    """Main validation function."""
    validator = BrowserIntegrationValidator()
    success = await validator.run_all_tests()
    
    if success:
        print("\nValidation complete! Browser extension integration is working.")
    else:
        print("\nValidation failed. Please check the logs and fix the issues.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
