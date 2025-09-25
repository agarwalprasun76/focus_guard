# core/process_manager.py
import atexit
import signal
from typing import List, Callable, Optional
import logging

logger = logging.getLogger(__name__)

class ProcessManager:
    """
    Manages application lifecycle including cleanup on exit.
    
    This class provides a way to register cleanup handlers that will be called
    when the application exits, either normally or due to a signal.
    """
    
    _instance: Optional['ProcessManager'] = None
    _cleanup_handlers: List[Callable[[], None]] = []
    _initialized: bool = False
    
    def __new__(cls):
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the process manager if not already initialized."""
        if not self._initialized:
            self._initialized = True
            self._setup_signal_handlers()
            atexit.register(self._cleanup)
    
    def _setup_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        signals = [signal.SIGINT, signal.SIGTERM]
        for sig in signals:
            try:
                signal.signal(sig, self._handle_signal)
            except (ValueError, AttributeError) as e:
                # Handle cases where signals aren't available (e.g., on Windows)
                logger.warning(f"Could not set up signal handler for {sig}: {e}")
    
    def _handle_signal(self, signum, frame) -> None:
        """Handle termination signals."""
        signame = signal.Signals(signum).name
        logger.info(f"Received signal {signame}, initiating shutdown...")
        self._cleanup()
        raise SystemExit(0)
    
    def register_cleanup(self, handler: Callable[[], None]) -> None:
        """Register a cleanup handler to be called on exit.
        
        Args:
            handler: A callable that takes no arguments and returns None.
        """
        if handler not in self._cleanup_handlers:
            logger.debug(f"Registering cleanup handler: {handler.__name__}")
            self._cleanup_handlers.append(handler)
    
    def unregister_cleanup(self, handler: Callable[[], None]) -> None:
        """Unregister a previously registered cleanup handler."""
        if handler in self._cleanup_handlers:
            logger.debug(f"Unregistering cleanup handler: {handler.__name__}")
            self._cleanup_handlers.remove(handler)
    
    def _cleanup(self) -> None:
        """Execute all registered cleanup handlers in reverse order."""
        logger.info("Starting cleanup process...")
        for handler in reversed(self._cleanup_handlers):
            try:
                logger.debug(f"Running cleanup handler: {handler.__name__}")
                handler()
            except Exception as e:
                logger.error(f"Error in cleanup handler {handler.__name__}: {e}")
        logger.info("Cleanup complete")

# Create a singleton instance
process_manager = ProcessManager()

def register_cleanup(handler: Callable[[], None]) -> None:
    """Register a cleanup handler with the global process manager.
    
    Example:
        def cleanup_db():
            db.close()
            
        register_cleanup(cleanup_db)
    """
    process_manager.register_cleanup(handler)

def unregister_cleanup(handler: Callable[[], None]) -> None:
    """Unregister a cleanup handler from the global process manager."""
    process_manager.unregister_cleanup(handler)