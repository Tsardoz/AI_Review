"""
Retry utilities with exponential backoff for resilient API calls.
"""

import time
import asyncio
from typing import Callable, Any, Optional, TypeVar
from functools import wraps

from .logger import get_logger

T = TypeVar('T')
logger = get_logger("retry")


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random())
        
        return delay


def retry(
    func: Optional[Callable[..., T]] = None,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        func: Function to decorate
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for delay between attempts
        retryable_exceptions: Tuple of exceptions to retry on
    """
    
    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        @wraps(f)
        def wrapper(*args, **kwargs) -> T:
            config = RetryConfig(
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor
            )
            
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return f(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt >= config.max_retries:
                        logger.error(
                            f"Failed after {config.max_retries} retries: {f.__name__}",
                            error=str(e),
                            attempt=attempt
                        )
                        raise
                    
                    delay = config.get_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {f.__name__}, retrying in {delay:.1f}s",
                        error=str(e),
                        delay=delay,
                        attempt=attempt
                    )
                    time.sleep(delay)
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    
    # Support both @retry and @retry(...) syntax
    if func is not None:
        return decorator(func)
    return decorator


def async_retry(
    func: Optional[Callable[..., T]] = None,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying async functions with exponential backoff.
    """
    
    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        @wraps(f)
        async def wrapper(*args, **kwargs) -> T:
            config = RetryConfig(
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor
            )
            
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await f(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt >= config.max_retries:
                        logger.error(
                            f"Failed after {config.max_retries} retries: {f.__name__}",
                            error=str(e),
                            attempt=attempt
                        )
                        raise
                    
                    delay = config.get_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {f.__name__}, retrying in {delay:.1f}s",
                        error=str(e),
                        delay=delay,
                        attempt=attempt
                    )
                    await asyncio.sleep(delay)
            
            if last_exception:
                raise last_exception
        
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator
