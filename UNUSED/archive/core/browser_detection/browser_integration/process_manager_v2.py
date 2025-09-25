# core/browser_integration/process_manager_v2.py
import atexit
import signal
import logging
from typing import List, Callable, Optional

logger = logging.getLogger(__name__)

class ProcessManager:
    """Manages application lifecycle including cleanup on exit.
    
    This class provides a way to register cleanup handlers that will be called
    when the application exits, either normally or due to a signal.
    """
    
    _instance: Optional['ProcessManager'] = None
    _cleanup_handlers: List[Callable[[], None]] = []
    _initialized: bool = False
    
    @classmethod
    def register_cleanup(cls, handler: Callable[[], None]) -> None:
        """Register a cleanup handler to be called on exit.
        
        Args:
            handler: A callable that takes no arguments and returns None.
        """
        if handler not in cls._cleanup_handlers:
            logger.debug(f"Registering cleanup handler: {handler.__name__ if hasattr(handler, '__name__') else handler}")
            cls._cleanup_handlers.append(handler)
    
    @classmethod
    def unregister_cleanup(cls, handler: Callable[[], None]) -> None:
        """Unregister a previously registered cleanup handler.
        
        Args:
            handler: The handler to unregister.
        """
        if handler in cls._cleanup_handlers:
            logger.debug(f"Unregistering cleanup handler: {handler.__name__ if hasattr(handler, '__name__') else handler}")
            cls._cleanup_handlers.remove(handler)
    
    @classmethod
    def cleanup(cls) -> None:
        """Execute all registered cleanup handlers in reverse order."""
        logger.info("Starting cleanup process...")
        for handler in reversed(cls._cleanup_handlers):
            try:
                logger.debug(f"Running cleanup handler: {handler.__name__ if hasattr(handler, '__name__') else handler}")
                handler()
            except Exception as e:
                logger.error(f"Error in cleanup handler {handler.__name__ if hasattr(handler, '__name__') else handler}: {e}")
        logger.info("Cleanup complete")
    
    @classmethod
    def init(cls) -> None:
        """Initialize the process manager if not already initialized."""
        if cls._initialized:
            return
            
        cls._initialized = True
        cls._instance = cls()
        atexit.register(cls.cleanup)
        
        # Register signal handlers for graceful shutdown
        signals = [signal.SIGINT, signal.SIGTERM]
        for sig in signals:
            try:
                signal.signal(sig, cls._handle_signal)
            except (ValueError, AttributeError) as e:
                # Handle cases where signals aren't available
                logger.warning(f"Could not set up signal handler for {sig}: {e}")
    
    @classmethod
    def _handle_signal(cls, signum, frame) -> None:
        """Handle termination signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        try:
            signame = signal.Signals(signum).name
            logger.info(f"Received signal {signame}, initiating shutdown...")
        except (ValueError, AttributeError):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            
        cls.cleanup()
        raise SystemExit(0)

# Initialize the process manager
ProcessManager.init()

# Example usage in your main application:
"""
from core.browser_integration.process_manager_v2 import ProcessManager
from core.browser_integration.tab_server_v2 import tab_server
import time

def main():
    # Register cleanup handlers
    ProcessManager.register_cleanup(tab_server.stop)
    
    # Start the tab server
    if not tab_server.start():
        logger.error("Failed to start tab server")
        return
    
    # Your application logic here
    logger.info("FocusGuard is running. Press Ctrl+C to exit.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
"""