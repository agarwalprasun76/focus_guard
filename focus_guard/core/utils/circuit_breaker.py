"""
Circuit breaker pattern implementation for robust error handling.

This module provides circuit breaker functionality to prevent cascading failures
and provide graceful degradation when services are unavailable.
"""

import asyncio
import logging
import time
import threading
from enum import Enum
from typing import Any, Callable, Optional, Dict, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, calls fail fast
    HALF_OPEN = "half_open"  # Testing if service is back


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: float = 60.0  # Seconds to wait before trying half-open
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: float = 30.0  # Request timeout in seconds
    expected_exception: tuple = (Exception,)  # Exceptions that count as failures


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker implementation for service calls."""
    
    def __init__(self, config: CircuitBreakerConfig, name: str = "default"):
        """Initialize circuit breaker.
        
        Args:
            config: Circuit breaker configuration
            name: Name for logging and identification
        """
        self.config = config
        self.name = name
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self._lock = threading.RLock()
        
        logger.info(f"Circuit breaker '{name}' initialized with config: {config}")
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap functions with circuit breaker."""
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: When circuit is open
        """
        with self._lock:
            current_state = self._get_current_state()
            
            if current_state == CircuitState.OPEN:
                logger.warning(f"Circuit breaker '{self.name}' is OPEN - failing fast")
                raise CircuitBreakerError(f"Circuit breaker '{self.name}' is open")
            
            try:
                # Execute the function with timeout
                start_time = time.time()
                result = self._execute_with_timeout(func, *args, **kwargs)
                execution_time = time.time() - start_time
                
                # Record success
                self._record_success()
                logger.debug(f"Circuit breaker '{self.name}' - successful call in {execution_time:.3f}s")
                
                return result
                
            except self.config.expected_exception as e:
                # Record failure
                self._record_failure()
                logger.warning(f"Circuit breaker '{self.name}' - failure: {e}")
                raise
            except Exception as e:
                # Unexpected exception - don't count as circuit failure
                logger.error(f"Circuit breaker '{self.name}' - unexpected error: {e}")
                raise
    
    def _execute_with_timeout(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with timeout."""
        if asyncio.iscoroutinefunction(func):
            # Handle async functions
            return asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)
        else:
            # Handle sync functions - simple execution (timeout handled by caller)
            return func(*args, **kwargs)
    
    def _get_current_state(self) -> CircuitState:
        """Get current circuit state, updating if necessary."""
        if self.state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
        
        return self.state
    
    def _record_success(self):
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                logger.info(f"Circuit breaker '{self.name}' transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Failure in half-open state - go back to open
            logger.warning(f"Circuit breaker '{self.name}' transitioning to OPEN (failure in half-open)")
            self.state = CircuitState.OPEN
            self.success_count = 0
        elif (self.state == CircuitState.CLOSED and 
              self.failure_count >= self.config.failure_threshold):
            # Too many failures - open the circuit
            logger.warning(f"Circuit breaker '{self.name}' transitioning to OPEN (threshold reached)")
            self.state = CircuitState.OPEN
    
    def reset(self):
        """Reset circuit breaker to closed state."""
        with self._lock:
            logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "success_threshold": self.config.success_threshold,
                    "timeout": self.config.timeout
                }
            }


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        """Initialize circuit breaker registry."""
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()
    
    def get_or_create(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get existing circuit breaker or create new one.
        
        Args:
            name: Circuit breaker name
            config: Configuration (uses default if not provided)
            
        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if name not in self._breakers:
                if config is None:
                    config = CircuitBreakerConfig()
                self._breakers[name] = CircuitBreaker(config, name)
            
            return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name.
        
        Args:
            name: Circuit breaker name
            
        Returns:
            CircuitBreaker instance or None if not found
        """
        with self._lock:
            return self._breakers.get(name)
    
    def reset_all(self):
        """Reset all circuit breakers."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            logger.info("All circuit breakers reset")
    
    def get_status_all(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        with self._lock:
            return {name: breaker.get_status() for name, breaker in self._breakers.items()}


# Global registry instance
_registry = CircuitBreakerRegistry()


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create a circuit breaker.
    
    Args:
        name: Circuit breaker name
        config: Configuration (uses default if not provided)
        
    Returns:
        CircuitBreaker instance
    """
    return _registry.get_or_create(name, config)


def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator to add circuit breaker protection to functions.
    
    Args:
        name: Circuit breaker name
        config: Configuration (uses default if not provided)
    """
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker(name, config)
        return breaker(func)
    
    return decorator


def reset_all_circuit_breakers():
    """Reset all circuit breakers."""
    _registry.reset_all()


def get_all_circuit_breaker_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all circuit breakers."""
    return _registry.get_status_all()
