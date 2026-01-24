"""
Rate limiter for Robinhood API calls.
Critical component to prevent API blocks from excessive usage.
"""
import time
from datetime import datetime, timedelta
from collections import deque
from typing import Callable, Any, Optional
from functools import wraps
import backoff
from loguru import logger

from config.settings import get_settings


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open due to repeated failures."""
    pass


class RateLimiter:
    """
    Rate limiter with multiple strategies:
    - Minimum delay between calls
    - Calls per minute limit
    - Calls per hour limit
    - Circuit breaker for repeated failures
    """

    def __init__(self):
        """Initialize rate limiter with settings from config."""
        self.settings = get_settings()
        self.config = self.settings.rate_limit

        # Minimum delay between calls
        self.min_delay = self.config.min_delay_seconds
        self.last_call_time: Optional[float] = None

        # Track calls per minute
        self.calls_per_minute_limit = self.config.calls_per_minute
        self.minute_calls: deque = deque()

        # Track calls per hour
        self.calls_per_hour_limit = self.config.calls_per_hour
        self.hour_calls: deque = deque()

        # Circuit breaker
        self.failure_count = 0
        self.max_failures = 5
        self.circuit_open = False
        self.circuit_open_until: Optional[datetime] = None
        self.circuit_reset_seconds = 60

        logger.info(
            f"RateLimiter initialized: {self.calls_per_minute_limit} calls/min, "
            f"{self.calls_per_hour_limit} calls/hour, {self.min_delay}s min delay"
        )

    def wait_if_needed(self) -> None:
        """
        Wait if necessary to respect rate limits.

        Raises:
            RateLimitExceeded: If rate limit would be exceeded
            CircuitBreakerOpen: If circuit breaker is open
        """
        # Check circuit breaker
        if self.circuit_open:
            if datetime.now() < self.circuit_open_until:
                remaining = (self.circuit_open_until - datetime.now()).seconds
                raise CircuitBreakerOpen(
                    f"Circuit breaker is open. Retry in {remaining} seconds."
                )
            else:
                # Reset circuit breaker
                self._reset_circuit_breaker()

        current_time = time.time()

        # 1. Enforce minimum delay between calls
        if self.last_call_time is not None:
            time_since_last_call = current_time - self.last_call_time
            if time_since_last_call < self.min_delay:
                wait_time = self.min_delay - time_since_last_call
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s (min delay)")
                time.sleep(wait_time)
                current_time = time.time()

        # 2. Check calls per minute limit
        self._cleanup_old_calls(self.minute_calls, 60)
        if len(self.minute_calls) >= self.calls_per_minute_limit:
            oldest_call = self.minute_calls[0]
            wait_time = 60 - (current_time - oldest_call)
            if wait_time > 0:
                logger.warning(
                    f"Rate limit approaching: {len(self.minute_calls)} calls in last minute. "
                    f"Waiting {wait_time:.2f}s"
                )
                time.sleep(wait_time)
                current_time = time.time()
                self._cleanup_old_calls(self.minute_calls, 60)

        # 3. Check calls per hour limit
        self._cleanup_old_calls(self.hour_calls, 3600)
        if len(self.hour_calls) >= self.calls_per_hour_limit:
            oldest_call = self.hour_calls[0]
            wait_time = 3600 - (current_time - oldest_call)
            if wait_time > 0:
                logger.error(
                    f"Hourly rate limit exceeded: {len(self.hour_calls)} calls. "
                    f"Must wait {wait_time / 60:.1f} minutes"
                )
                raise RateLimitExceeded(
                    f"Hourly rate limit exceeded. Wait {wait_time / 60:.1f} minutes."
                )

        # Record this call
        self.last_call_time = current_time
        self.minute_calls.append(current_time)
        self.hour_calls.append(current_time)

    def _cleanup_old_calls(self, call_queue: deque, window_seconds: int) -> None:
        """Remove calls older than the time window."""
        current_time = time.time()
        while call_queue and current_time - call_queue[0] > window_seconds:
            call_queue.popleft()

    def record_success(self) -> None:
        """Record a successful API call (resets failure count)."""
        if self.failure_count > 0:
            logger.debug("API call successful, resetting failure count")
            self.failure_count = 0

    def record_failure(self) -> None:
        """
        Record a failed API call.
        Opens circuit breaker after max failures.
        """
        self.failure_count += 1
        logger.warning(f"API call failed. Failure count: {self.failure_count}/{self.max_failures}")

        if self.failure_count >= self.max_failures:
            self._open_circuit_breaker()

    def _open_circuit_breaker(self) -> None:
        """Open circuit breaker to prevent further calls."""
        self.circuit_open = True
        self.circuit_open_until = datetime.now() + timedelta(seconds=self.circuit_reset_seconds)
        logger.error(
            f"Circuit breaker OPENED due to {self.failure_count} consecutive failures. "
            f"Will reset at {self.circuit_open_until.strftime('%H:%M:%S')}"
        )

    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker after cooldown period."""
        logger.info("Circuit breaker CLOSED - resuming API calls")
        self.circuit_open = False
        self.circuit_open_until = None
        self.failure_count = 0

    def get_stats(self) -> dict:
        """Get current rate limiter statistics."""
        self._cleanup_old_calls(self.minute_calls, 60)
        self._cleanup_old_calls(self.hour_calls, 3600)

        return {
            "calls_last_minute": len(self.minute_calls),
            "calls_last_hour": len(self.hour_calls),
            "minute_limit": self.calls_per_minute_limit,
            "hour_limit": self.calls_per_hour_limit,
            "failure_count": self.failure_count,
            "circuit_open": self.circuit_open,
            "circuit_open_until": self.circuit_open_until.isoformat() if self.circuit_open_until else None,
        }


# Singleton instance
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get or create RateLimiter singleton instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def rate_limited(func: Callable) -> Callable:
    """
    Decorator to apply rate limiting to a function.

    Usage:
        @rate_limited
        def api_call():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        limiter = get_rate_limiter()

        # Wait if needed (may raise RateLimitExceeded or CircuitBreakerOpen)
        limiter.wait_if_needed()

        try:
            result = func(*args, **kwargs)
            limiter.record_success()
            return result
        except Exception as e:
            limiter.record_failure()
            raise

    return wrapper


def with_exponential_backoff(
    max_tries: int = 3,
    max_time: int = 30,
    exception: type = Exception
):
    """
    Decorator for exponential backoff on failures.

    Args:
        max_tries: Maximum number of retry attempts
        max_time: Maximum total time for retries (seconds)
        exception: Exception type to catch and retry

    Usage:
        @with_exponential_backoff(max_tries=3)
        @rate_limited
        def api_call():
            ...
    """
    return backoff.on_exception(
        backoff.expo,
        exception,
        max_tries=max_tries,
        max_time=max_time,
        on_backoff=lambda details: logger.warning(
            f"Backing off {details['wait']:.1f}s after {details['tries']} tries"
        )
    )
