"""
Focus Guard MVP Main Entry Point

This script provides a simple entry point for the Focus Guard MVP that uses
the existing full coordinator system with all components.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('focus_guard_mvp.log')
    ]
)

logger = logging.getLogger("focus_guard.mvp")

# Import Focus Guard components
from focus_guard.core.config.manager import DefaultConfigurationManager
from focus_guard.core.coordinator.focus_guard_coordinator import FocusGuardCoordinator
from focus_guard.core.browser.extension.installer import ExtensionInstaller


async def setup_extension() -> bool:
    """
    Set up browser extension and tab server with auto-installation.
    
    Returns:
        bool: True if setup successful, False otherwise
    """
    try:
        logger.info("Setting up browser extension...")
        installer = ExtensionInstaller()
        
        # First, try to start the tab server (checks if extension is already working)
        if installer.ensure_tab_server_running():
            logger.info("Extension is already working - tab server started successfully")
            return True
        
        # If tab server failed, try to install the extension
        logger.info("Tab server failed to start - attempting extension installation...")
        
        try:
            # Attempt automatic extension installation
            success = installer.install_extension()
            if success:
                logger.info("Extension installation completed")
                
                # Wait a moment for installation to complete
                import asyncio
                await asyncio.sleep(2)
                
                # Try starting tab server again
                if installer.ensure_tab_server_running():
                    logger.info("Extension installation successful - tab server is now running")
                    return True
                else:
                    logger.warning("Extension installed but tab server still not responding")
                    return False
            else:
                logger.warning("Automatic extension installation failed")
                logger.info("Manual extension installation may be required")
                return False
                
        except Exception as install_error:
            logger.warning(f"Extension installation error: {install_error}")
            logger.info("Continuing without extension - some features may be limited")
            return False
            
    except Exception as e:
        logger.error(f"Error setting up extension: {e}")
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
        
        # Set up browser extension
        extension_ready = await setup_extension()
        if not extension_ready:
            logger.warning("Browser extension not ready - some features may not work")
        
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
