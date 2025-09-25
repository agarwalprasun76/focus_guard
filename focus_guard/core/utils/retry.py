"""
Retry decorator with exponential backoff for handling transient failures.
"""
import asyncio
import time
import logging
from functools import wraps
from typing import Callable, TypeVar, Any, Optional, Type, Tuple, Union

T = TypeVar('T')


def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    logger: Optional[logging.Logger] = None,
    reraise: bool = True
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay between retries in seconds (default: 1.0)
        backoff_factor: Multiplier for delay between retries (default: 2.0)
        exceptions: Exception(s) to catch and retry on (default: Exception)
        logger: Logger to use for logging retry attempts (default: module logger)
        reraise: Whether to re-raise the exception after all retries fail (default: True)
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            nonlocal logger
            logger = logger or logging.getLogger(func.__module__)
            attempt = 1
            delay = initial_delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt >= max_attempts:
                        logger.error(
                            f"Failed after {attempt} attempts: {str(e)}",
                            exc_info=True
                        )
                        if reraise:
                            raise
                        return None
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed: {str(e)}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    time.sleep(delay)
                    delay *= backoff_factor
                    attempt += 1
                    
        return wrapper
    return decorator


def async_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    logger: Optional[logging.Logger] = None,
    reraise: bool = True
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Async retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay between retries in seconds (default: 1.0)
        backoff_factor: Multiplier for delay between retries (default: 2.0)
        exceptions: Exception(s) to catch and retry on (default: Exception)
        logger: Logger to use for logging retry attempts (default: module logger)
        reraise: Whether to re-raise the exception after all retries fail (default: True)
        
    Returns:
        Decorated async function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            nonlocal logger
            logger = logger or logging.getLogger(func.__module__)
            attempt = 1
            delay = initial_delay
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt >= max_attempts:
                        logger.error(
                            f"Failed after {attempt} attempts: {str(e)}",
                            exc_info=True
                        )
                        if reraise:
                            raise
                        return None
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed: {str(e)}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
                    attempt += 1
                    
        return wrapper
    return decorator
