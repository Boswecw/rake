"""Retry Utilities for Rake Service

Provides decorators and utilities for retrying failed operations with
exponential backoff and configurable strategies.

Built on top of the `tenacity` library for robust retry logic.

Example:
    >>> from utils.retry import retry_with_backoff
    >>>
    >>> @retry_with_backoff(max_attempts=3)
    ... async def fetch_data():
    ...     # Operation that might fail
    ...     return await api_call()
"""

import logging
from functools import wraps
from typing import Callable, Optional, Type, Tuple, Any
import asyncio

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
    RetryCallState,
    AsyncRetrying
)

from config import settings

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: float = 60.0,
    multiplier: Optional[float] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger_instance: Optional[logging.Logger] = None
):
    """Decorator for retrying async functions with exponential backoff.

    Provides configurable retry logic with exponential backoff for async operations.
    Uses settings from config.py by default.

    Args:
        max_attempts: Maximum retry attempts (default: settings.RETRY_ATTEMPTS)
        base_delay: Initial delay in seconds (default: settings.RETRY_DELAY)
        max_delay: Maximum delay between retries in seconds
        multiplier: Exponential backoff multiplier (default: settings.RETRY_BACKOFF)
        exceptions: Tuple of exceptions to retry on
        logger_instance: Custom logger (default: module logger)

    Returns:
        Decorated async function with retry logic

    Example:
        >>> @retry_with_backoff(max_attempts=3, base_delay=1.0)
        ... async def fetch_document(url: str) -> str:
        ...     async with httpx.AsyncClient() as client:
        ...         response = await client.get(url)
        ...         response.raise_for_status()
        ...         return response.text
        ...
        >>> # Will retry up to 3 times with exponential backoff
        >>> text = await fetch_document("https://example.com/doc")
    """
    max_attempts = max_attempts or settings.RETRY_ATTEMPTS
    base_delay = base_delay or settings.RETRY_DELAY
    multiplier = multiplier or settings.RETRY_BACKOFF
    log = logger_instance or logger

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            """Async wrapper with retry logic."""
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(
                    multiplier=base_delay,
                    max=max_delay,
                    exp_base=multiplier
                ),
                retry=retry_if_exception_type(exceptions),
                before_sleep=before_sleep_log(log, logging.WARNING),
                after=after_log(log, logging.DEBUG),
                reraise=True
            ):
                with attempt:
                    return await func(*args, **kwargs)

        return wrapper

    return decorator


def retry_sync_with_backoff(
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: float = 60.0,
    multiplier: Optional[float] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger_instance: Optional[logging.Logger] = None
):
    """Decorator for retrying synchronous functions with exponential backoff.

    Similar to retry_with_backoff but for synchronous functions.

    Args:
        max_attempts: Maximum retry attempts (default: settings.RETRY_ATTEMPTS)
        base_delay: Initial delay in seconds (default: settings.RETRY_DELAY)
        max_delay: Maximum delay between retries in seconds
        multiplier: Exponential backoff multiplier (default: settings.RETRY_BACKOFF)
        exceptions: Tuple of exceptions to retry on
        logger_instance: Custom logger (default: module logger)

    Returns:
        Decorated function with retry logic

    Example:
        >>> @retry_sync_with_backoff(max_attempts=3)
        ... def parse_pdf(file_path: str) -> str:
        ...     with open(file_path, 'rb') as f:
        ...         return extract_text(f)
    """
    max_attempts = max_attempts or settings.RETRY_ATTEMPTS
    base_delay = base_delay or settings.RETRY_DELAY
    multiplier = multiplier or settings.RETRY_BACKOFF
    log = logger_instance or logger

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=base_delay,
            max=max_delay,
            exp_base=multiplier
        ),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(log, logging.WARNING),
        after=after_log(log, logging.DEBUG),
        reraise=True
    )


class RetryableOperation:
    """Context manager for manual retry control.

    Provides fine-grained control over retry logic when decorators
    aren't suitable.

    Attributes:
        max_attempts: Maximum number of attempts
        base_delay: Initial delay between retries
        multiplier: Exponential backoff multiplier
        max_delay: Maximum delay cap

    Example:
        >>> async def fetch_with_manual_retry(url: str) -> str:
        ...     retry_op = RetryableOperation(max_attempts=3)
        ...
        ...     for attempt in retry_op:
        ...         try:
        ...             return await http_client.get(url)
        ...         except httpx.HTTPError as e:
        ...             if not retry_op.should_retry(e):
        ...                 raise
        ...             await retry_op.wait_before_retry()
    """

    def __init__(
        self,
        max_attempts: Optional[int] = None,
        base_delay: Optional[float] = None,
        multiplier: Optional[float] = None,
        max_delay: float = 60.0
    ):
        """Initialize retryable operation.

        Args:
            max_attempts: Maximum retry attempts
            base_delay: Initial delay in seconds
            multiplier: Exponential backoff multiplier
            max_delay: Maximum delay between retries
        """
        self.max_attempts = max_attempts or settings.RETRY_ATTEMPTS
        self.base_delay = base_delay or settings.RETRY_DELAY
        self.multiplier = multiplier or settings.RETRY_BACKOFF
        self.max_delay = max_delay
        self.current_attempt = 0
        self.last_exception: Optional[Exception] = None

    def __iter__(self):
        """Iterate through retry attempts."""
        self.current_attempt = 0
        return self

    def __next__(self) -> int:
        """Get next retry attempt.

        Returns:
            Current attempt number (1-indexed)

        Raises:
            StopIteration: When max attempts exceeded
        """
        self.current_attempt += 1
        if self.current_attempt > self.max_attempts:
            raise StopIteration
        return self.current_attempt

    def should_retry(self, exception: Exception) -> bool:
        """Check if operation should be retried.

        Args:
            exception: The exception that occurred

        Returns:
            True if more attempts available, False otherwise
        """
        self.last_exception = exception
        return self.current_attempt < self.max_attempts

    async def wait_before_retry(self) -> None:
        """Wait before next retry attempt with exponential backoff.

        Uses exponential backoff formula:
        delay = min(base_delay * (multiplier ^ attempt), max_delay)

        Example:
            >>> retry_op = RetryableOperation(base_delay=1.0, multiplier=2.0)
            >>> await retry_op.wait_before_retry()  # Wait 1s
            >>> await retry_op.wait_before_retry()  # Wait 2s
            >>> await retry_op.wait_before_retry()  # Wait 4s
        """
        if self.current_attempt > 0:
            delay = min(
                self.base_delay * (self.multiplier ** (self.current_attempt - 1)),
                self.max_delay
            )
            logger.info(
                f"Retrying in {delay:.2f} seconds (attempt {self.current_attempt}/{self.max_attempts})"
            )
            await asyncio.sleep(delay)

    def get_next_delay(self) -> float:
        """Calculate next retry delay without actually waiting.

        Returns:
            Next delay in seconds

        Example:
            >>> retry_op = RetryableOperation()
            >>> retry_op.current_attempt = 2
            >>> delay = retry_op.get_next_delay()
            >>> print(f"Next retry in {delay}s")
        """
        if self.current_attempt >= self.max_attempts:
            return 0.0

        return min(
            self.base_delay * (self.multiplier ** self.current_attempt),
            self.max_delay
        )


# Example usage and testing
if __name__ == "__main__":
    import httpx

    # Example 1: Async function with retry
    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    async def fetch_url(url: str) -> str:
        """Fetch URL with automatic retry."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    # Example 2: Manual retry control
    async def fetch_with_custom_logic(url: str) -> str:
        """Fetch URL with custom retry logic."""
        retry_op = RetryableOperation(max_attempts=3)

        for attempt in retry_op:
            try:
                logger.info(f"Attempt {attempt}")
                async with httpx.AsyncClient() as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    return response.text
            except httpx.HTTPError as e:
                logger.warning(f"Attempt {attempt} failed: {e}")
                if not retry_op.should_retry(e):
                    logger.error("Max attempts exceeded")
                    raise
                await retry_op.wait_before_retry()

        raise RuntimeError("Should never reach here")

    # Example 3: Synchronous function
    @retry_sync_with_backoff(max_attempts=3)
    def read_file(path: str) -> str:
        """Read file with retry on I/O errors."""
        with open(path, 'r') as f:
            return f.read()

    # Run examples
    async def main():
        """Run retry examples."""
        print("=== Retry Utilities Examples ===\n")

        # Test RetryableOperation
        print("Example 1: RetryableOperation")
        retry_op = RetryableOperation(max_attempts=3, base_delay=0.5)
        for attempt in retry_op:
            print(f"  Attempt {attempt}/{retry_op.max_attempts}")
            if attempt < 3:
                await retry_op.wait_before_retry()

        print("\n✅ All examples completed")

    asyncio.run(main())
