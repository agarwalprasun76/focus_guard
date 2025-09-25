import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('focus_guard.log')
    ]
)
logger = logging.getLogger("focus_guard")

# Import after path setup
from focus_guard.core.config.manager import DefaultConfigurationManager
from focus_guard.core.config.providers.memory_provider import MemoryConfigProvider
from focus_guard.core.config.providers.json_provider import JsonConfigProvider
from focus_guard.core.coordinator.focus_guard_coordinator import FocusGuardCoordinator
from focus_guard.core.config.interfaces import ConfigScope

class ConfigManagerWithChangeListener(DefaultConfigurationManager):
    """Wrapper around DefaultConfigurationManager that adds change listener support."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._change_listeners = []
    
    def add_change_listener(self, callback):
        """Add a change listener that will be called for any config change."""
        self._change_listeners.append(callback)
        # Subscribe to all changes
        self.subscribe("*", lambda path, value: callback(path, value))
    
    def remove_change_listener(self, callback):
        """Remove a previously registered change listener."""
        if callback in self._change_listeners:
            self._change_listeners.remove(callback)
            # Note: We can't actually unsubscribe from "*" for a specific callback
            # with the current DefaultConfigurationManager implementation


async def setup_config_manager() -> DefaultConfigurationManager:
    """Set up and configure the configuration manager."""
    logger.info("Setting up configuration manager...")
    
    # Create the configuration manager with change listener support
    config_manager = ConfigManagerWithChangeListener(
        validation_enabled=True,
        auto_coerce_types=True,
        cache_ttl=300  # 5 minutes cache TTL
    )
    
    # Set up default configuration
    default_config: Dict[str, Any] = {
        "app": {
            "name": "Focus Guard",
            "version": "1.0.0",
            "debug": True
        },
        "browser_integration": {
            "enabled": True,
            "polling_interval_seconds": 1.0,
            "health_check_interval_seconds": 60.0
        },
        "activity_monitor": {
            "polling_interval_seconds": 1.0,
            "idle_timeout_seconds": 300,
            "idle_threshold_seconds": 300
        },
        "classification": {
            "cache_ttl_seconds": 300,
            "cache_cleanup_interval_seconds": 60
        },
        "alert_system": {
            "enabled": True,
            "default_timeout_seconds": 10,
            "max_alerts": 5,
            "cooldown_seconds": 60
        },
        "api_server": {
            "enabled": True,
            "host": "127.0.0.1",
            "port": 5000,
            "debug": False,
            "health_check_interval_seconds": 60.0
        }
    }
    
    # Create a memory provider with default config
    memory_provider = MemoryConfigProvider(default_config)
    
    # Register the memory provider with highest priority
    config_manager.register_provider(
        memory_provider,
        scope=ConfigScope.USER,
        priority=1000  # Highest priority
    )
    
    # Check for JSON config file
    config_path = os.path.join(project_root, 'config', 'config.json')
    if os.path.exists(config_path):
        logger.info(f"Loading configuration from {config_path}")
        try:
            json_provider = JsonConfigProvider(str(config_path))
            config_manager.register_provider(
                json_provider,
                scope=ConfigScope.USER,
                priority=500  # Medium priority
            )
        except Exception as e:
            logger.error(f"Failed to load JSON config from {config_path}: {e}")
    
    logger.info("Configuration manager setup complete")
    return config_manager

async def main():
    logger.info("Starting Focus Guard...")
    
    try:
        # Set up configuration
        config_manager = await setup_config_manager()

        # Create the coordinator
        logger.debug("Creating coordinator...")
        coordinator = FocusGuardCoordinator(config_manager)
        logger.info("Coordinator created")
        
        try:
            # Initialize all components
            logger.info("Initializing components...")
            if not await coordinator.initialize():
                logger.error("Failed to initialize coordinator")
                return 1
            logger.info("All components initialized successfully")
                
            # Start all components
            logger.info("Starting components...")
            if not await coordinator.start():
                logger.error("Failed to start coordinator")
                return 1
            logger.info("All components started successfully")
            
            logger.info("Focus Guard is running. Press Ctrl+C to exit.")
            
            # Keep the application running
            while True:
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info("Shutdown requested...")
        except Exception as e:
            logger.exception("An unexpected error occurred")
            return 1
        finally:
            # Cleanup
            logger.info("Shutting down components...")
            await coordinator.stop()
            await coordinator.shutdown()
            logger.info("Shutdown complete")
            
    except Exception as e:
        logger.exception("Failed to initialize Focus Guard")
        return 1
        
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        sys.exit(0)
    except Exception as e:
        logger.exception("Fatal error in main loop")
        sys.exit(1)