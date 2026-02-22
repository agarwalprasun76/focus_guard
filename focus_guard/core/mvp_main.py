"""
Focus Guard MVP Main Entry Point (LEGACY)

DEPRECATED: Use focus_guard/main.py instead for the unified entry point.
This file is kept for backward compatibility with the CLI and dev workflows.

This script provides a simple entry point for the Focus Guard MVP that uses
the existing full coordinator system with all components.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Configure logging — use rotating handler to avoid unbounded log growth
from logging.handlers import RotatingFileHandler as _RFH

_log_dir = Path(os.environ.get('PROGRAMDATA', r'C:\ProgramData')) / 'FocusGuard' / 'logs'
_log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        _RFH(str(_log_dir / 'focus_guard_mvp.log'), maxBytes=10*1024*1024, backupCount=3),
    ]
)

logger = logging.getLogger("focus_guard.mvp")

# Import Focus Guard components
from focus_guard.core.config.manager import DefaultConfigurationManager
from focus_guard.core.coordinator.focus_guard_coordinator import FocusGuardCoordinator
from focus_guard.core.tab_server_endpoint import resolve_tab_server_endpoint


async def setup_tab_server() -> bool:
    """
    Start the browser_v2 tab server (HTTP API for the browser extension).
    
    Returns:
        bool: True if tab server started successfully, False otherwise
    """
    try:
        from focus_guard.core.browser_v2.tab_server.runner import TabServerRunner

        host, port = resolve_tab_server_endpoint()
        logger.info("Starting tab server on port %d...", port)
        runner = TabServerRunner(
            host=host,
            port=port,
            auto_restart=True,
        )
        success = runner.start()
        if success:
            logger.info("Tab server started successfully")
        else:
            logger.warning("Tab server failed to start — browser extension won't connect")
        return success
    except Exception as e:
        logger.error(f"Error starting tab server: {e}")
        return False


async def main() -> int:
    """
    MVP main entry point using existing coordinator.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    logger.info("Starting Focus Guard MVP...")
    
    try:
        # Set up configuration manager with default settings
        logger.info("Initializing configuration manager...")
        config_manager = DefaultConfigurationManager()
        
        # Start tab server for browser extension communication
        tab_server_ready = await setup_tab_server()
        if not tab_server_ready:
            logger.warning("Tab server not ready - browser extension features may not work")
        
        # Create Focus Guard coordinator
        logger.info("Creating Focus Guard coordinator...")
        coordinator = FocusGuardCoordinator(config_manager)
        
        # Initialize components
        logger.info("Initializing components...")
        if not await coordinator.initialize():
            logger.error("Failed to initialize coordinator")
            return 1
        
        # Start all components
        logger.info("Starting components...")
        if not await coordinator.start():
            logger.error("Failed to start coordinator")
            await coordinator.shutdown()
            return 1
        
        logger.info("Focus Guard MVP is running successfully!")
        logger.info("")
        logger.info("=" * 60)
        logger.info("INTERACTIVE DEMO - Test Browser Blocking")
        logger.info("=" * 60)
        logger.info("")
        logger.info("To test the application's blocking functionality:")
        logger.info("")
        logger.info("1. Open your browser and navigate to:")
        logger.info("   YouTube Shorts: https://www.youtube.com/shorts/At3syx84D34")
        logger.info("   (Should be blocked as SOCIAL_MEDIA/ENTERTAINMENT)")
        logger.info("")
        logger.info("2. Then try opening:")
        logger.info("   NY Times: https://www.nytimes.com/live/2025/08/27/us/minneapolis-church-shooting")
        logger.info("   (Should be allowed as NEWS)")
        logger.info("")
        logger.info("Watch the logs below to see:")
        logger.info("- Tab detection from browser extension")
        logger.info("- Domain classification")
        logger.info("- Blocking decisions")
        logger.info("")
        logger.info("Press Ctrl+C to stop...")
        logger.info("=" * 60)
        logger.info("")
        
        # Keep running until interrupted
        try:
            health_check_counter = 0
            while True:
                await asyncio.sleep(1)
                health_check_counter += 1
                
                # Check system health periodically (every 10 seconds)
                if health_check_counter >= 10:
                    if not coordinator.is_healthy():
                        logger.warning("System health check failed")
                    health_check_counter = 0
                    
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
            
    except Exception as e:
        logger.exception(f"Unexpected error in MVP main: {e}")
        return 1
        
    finally:
        # Graceful shutdown
        logger.info("Shutting down Focus Guard MVP...")
        try:
            await coordinator.shutdown()
            logger.info("Shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            return 1
    
    return 0


def run_mvp():
    """Synchronous wrapper for running the MVP."""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("MVP stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_mvp()
