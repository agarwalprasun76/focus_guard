"""
Enhanced retry mechanisms with exponential backoff, jitter, and circuit breaker integration.

This module provides comprehensive retry functionality for robust error handling
across Focus Guard components.
"""

import asyncio
import logging
import random
import time
import functools
from typing import Any, Callable, Optional, Union, Type, Tuple, Dict
from dataclasses import dataclass
from enum import Enum

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, get_circuit_breaker

logger = logging.getLogger(__name__)


class BackoffStrategy(Enum):
    """Backoff strategies for retry attempts."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER
    jitter_range: float = 0.1  # Jitter as fraction of delay (0.1 = ±10%)
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    stop_exceptions: Tuple[Type[Exception], ...] = ()  # Exceptions that stop retrying
    timeout_per_attempt: Optional[float] = None  # Timeout per individual attempt
    circuit_breaker_name: Optional[str] = None  # Optional circuit breaker integration


class RetryExhaustedError(Exception):
    """Exception raised when all retry attempts are exhausted."""
    
    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(f"Retry exhausted after {attempts} attempts. Last error: {last_exception}")


class RetryContext:
    """Context information for retry attempts."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.attempt = 0
        self.total_elapsed = 0.0
        self.last_exception: Optional[Exception] = None
        self.start_time = time.time()
    
    def next_attempt(self) -> bool:
        """Check if another attempt should be made."""
        self.attempt += 1
        return self.attempt <= self.config.max_attempts
    
    def calculate_delay(self) -> float:
        """Calculate delay for current attempt."""
        if self.attempt <= 1:
            return 0.0
        
        if self.config.backoff_strategy == BackoffStrategy.FIXED:
            delay = self.config.base_delay
        elif self.config.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.config.base_delay * (self.attempt - 1)
        elif self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** (self.attempt - 2))
        elif self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL_JITTER:
            base_delay = self.config.base_delay * (2 ** (self.attempt - 2))
            jitter = base_delay * self.config.jitter_range * (2 * random.random() - 1)
            delay = base_delay + jitter
        else:
            delay = self.config.base_delay
        
        return min(delay, self.config.max_delay)
    
    def should_retry(self, exception: Exception) -> bool:
        """Check if we should retry based on the exception."""
        self.last_exception = exception
        
        # Check for stop exceptions
        if any(isinstance(exception, exc_type) for exc_type in self.config.stop_exceptions):
            logger.debug(f"Stop exception encountered: {type(exception).__name__}")
            return False
        
        # Check for retry exceptions
        if not any(isinstance(exception, exc_type) for exc_type in self.config.retry_exceptions):
            logger.debug(f"Non-retryable exception: {type(exception).__name__}")
            return False
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get current retry status."""
        return {
            "attempt": self.attempt,
            "max_attempts": self.config.max_attempts,
            "total_elapsed": time.time() - self.start_time,
            "last_exception": str(self.last_exception) if self.last_exception else None,
            "backoff_strategy": self.config.backoff_strategy.value
        }


def retry_with_config(config: RetryConfig):
    """Decorator to add retry behavior with custom configuration.
    
    Args:
        config: Retry configuration
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return execute_with_retry(func, config, *args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await execute_with_retry_async(func, config, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator


def retry(max_attempts: int = 3,
          base_delay: float = 1.0,
          max_delay: float = 60.0,
          backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER,
          retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
          stop_exceptions: Tuple[Type[Exception], ...] = (),
          circuit_breaker_name: Optional[str] = None):
    """Simple retry decorator with common parameters.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between attempts
        max_delay: Maximum delay between attempts
        backoff_strategy: Backoff strategy to use
        retry_exceptions: Exceptions that trigger retries
        stop_exceptions: Exceptions that stop retrying
        circuit_breaker_name: Optional circuit breaker name
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_strategy=backoff_strategy,
        retry_exceptions=retry_exceptions,
        stop_exceptions=stop_exceptions,
        circuit_breaker_name=circuit_breaker_name
    )
    return retry_with_config(config)


def execute_with_retry(func: Callable, config: RetryConfig, *args, **kwargs) -> Any:
    """Execute function with retry logic.
    
    Args:
        func: Function to execute
        config: Retry configuration
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        RetryExhaustedError: When all retry attempts are exhausted
    """
    context = RetryContext(config)
    circuit_breaker = None
    
    # Get circuit breaker if configured
    if config.circuit_breaker_name:
        cb_config = CircuitBreakerConfig(
            timeout=config.timeout_per_attempt or 30.0,
            expected_exception=config.retry_exceptions
        )
        circuit_breaker = get_circuit_breaker(config.circuit_breaker_name, cb_config)
    
    while context.next_attempt():
        try:
            logger.debug(f"Retry attempt {context.attempt}/{config.max_attempts} for {func.__name__}")
            
            # Execute with or without circuit breaker
            if circuit_breaker:
                result = circuit_breaker.call(func, *args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success
            if context.attempt > 1:
                logger.info(f"Function {func.__name__} succeeded on attempt {context.attempt}")
            
            return result
            
        except Exception as e:
            if not context.should_retry(e):
                logger.warning(f"Non-retryable exception in {func.__name__}: {e}")
                raise
            
            if context.attempt >= config.max_attempts:
                logger.error(f"Retry exhausted for {func.__name__} after {context.attempt} attempts")
                raise RetryExhaustedError(context.attempt, e)
            
            # Calculate and apply delay
            delay = context.calculate_delay()
            if delay > 0:
                logger.debug(f"Retrying {func.__name__} in {delay:.2f}s (attempt {context.attempt})")
                time.sleep(delay)
            
            context.total_elapsed = time.time() - context.start_time
    
    # Should never reach here
    raise RetryExhaustedError(context.attempt, context.last_exception)


async def execute_with_retry_async(func: Callable, config: RetryConfig, *args, **kwargs) -> Any:
    """Execute async function with retry logic.
    
    Args:
        func: Async function to execute
        config: Retry configuration
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        RetryExhaustedError: When all retry attempts are exhausted
    """
    context = RetryContext(config)
    circuit_breaker = None
    
    # Get circuit breaker if configured
    if config.circuit_breaker_name:
        cb_config = CircuitBreakerConfig(
            timeout=config.timeout_per_attempt or 30.0,
            expected_exception=config.retry_exceptions
        )
        circuit_breaker = get_circuit_breaker(config.circuit_breaker_name, cb_config)
    
    while context.next_attempt():
        try:
            logger.debug(f"Async retry attempt {context.attempt}/{config.max_attempts} for {func.__name__}")
            
            # Execute with or without circuit breaker
            if circuit_breaker:
                result = await circuit_breaker.call(func, *args, **kwargs)
            else:
                if config.timeout_per_attempt:
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=config.timeout_per_attempt)
                else:
                    result = await func(*args, **kwargs)
            
            # Success
            if context.attempt > 1:
                logger.info(f"Async function {func.__name__} succeeded on attempt {context.attempt}")
            
            return result
            
        except Exception as e:
            if not context.should_retry(e):
                logger.warning(f"Non-retryable exception in async {func.__name__}: {e}")
                raise
            
            if context.attempt >= config.max_attempts:
                logger.error(f"Async retry exhausted for {func.__name__} after {context.attempt} attempts")
                raise RetryExhaustedError(context.attempt, e)
            
            # Calculate and apply delay
            delay = context.calculate_delay()
            if delay > 0:
                logger.debug(f"Retrying async {func.__name__} in {delay:.2f}s (attempt {context.attempt})")
                await asyncio.sleep(delay)
            
            context.total_elapsed = time.time() - context.start_time
    
    # Should never reach here
    raise RetryExhaustedError(context.attempt, context.last_exception)


# Convenience functions for common retry patterns

def retry_network_call(max_attempts: int = 5, base_delay: float = 1.0):
    """Retry decorator optimized for network calls."""
    import requests
    return retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=30.0,
        backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
        retry_exceptions=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
            ConnectionError,
            TimeoutError
        ),
        stop_exceptions=(
            requests.exceptions.HTTPError,  # Don't retry 4xx errors
        )
    )


def retry_file_operation(max_attempts: int = 3, base_delay: float = 0.5):
    """Retry decorator optimized for file operations."""
    return retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=5.0,
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        retry_exceptions=(
            OSError,
            IOError,
            PermissionError
        ),
        stop_exceptions=(
            FileNotFoundError,  # Don't retry if file doesn't exist
        )
    )


def retry_database_operation(max_attempts: int = 3, base_delay: float = 2.0):
    """Retry decorator optimized for database operations."""
    return retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=10.0,
        backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
        retry_exceptions=(
            ConnectionError,
            TimeoutError,
        ),
        circuit_breaker_name="database"
    )
