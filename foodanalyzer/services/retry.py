"""A small exponential-backoff retry helper.

Kept deliberately tiny and dependency-free so the backoff policy is easy to
unit-test with a fake clock. Both a sync and an async variant are provided
because ``ai`` calls are synchronous but the pipeline that fans them out is
asynchronous.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from foodanalyzer.logging_config import get_logger

_log = get_logger(__name__)

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    """Backoff configuration.

    Delay before attempt *n* (1-indexed, n>=2) is::

        min(max_delay, base_delay * 2 ** (n - 2))  (+/- jitter)
    """

    max_attempts: int = 4
    base_delay: float = 0.5
    max_delay: float = 8.0
    jitter: float = 0.1

    def delay_for(self, attempt: int) -> float:
        raw = self.base_delay * (2 ** (attempt - 2))
        raw = min(self.max_delay, raw)
        if self.jitter:
            raw += random.uniform(0.0, self.jitter * raw)
        return max(0.0, raw)

    @classmethod
    def from_settings(cls) -> "RetryPolicy":
        from foodanalyzer.config import get_settings

        s = get_settings()
        return cls(
            max_attempts=s.retry_max_attempts,
            base_delay=s.retry_base_delay_seconds,
            max_delay=s.retry_max_delay_seconds,
        )


def retry_call(
    func: Callable[[], T],
    *,
    retry_on: tuple[type[BaseException], ...],
    policy: RetryPolicy | None = None,
    description: str = "call",
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Run ``func`` with retries; re-raise the last error when attempts run out."""
    policy = policy or RetryPolicy.from_settings()
    last_exc: BaseException | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return func()
        except retry_on as exc:  # noqa: PERF203 - retry loop
            last_exc = exc
            if attempt == policy.max_attempts:
                break
            delay = policy.delay_for(attempt + 1)
            _log.warning(
                "%s failed (attempt %d/%d): %s — retrying in %.2fs",
                description, attempt, policy.max_attempts, exc, delay,
            )
            sleep(delay)
    assert last_exc is not None
    _log.error("%s failed after %d attempts: %s", description, policy.max_attempts, last_exc)
    raise last_exc


async def retry_call_async(
    func: Callable[[], Awaitable[T]],
    *,
    retry_on: tuple[type[BaseException], ...],
    policy: RetryPolicy | None = None,
    description: str = "call",
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Async counterpart of :func:`retry_call`."""
    policy = policy or RetryPolicy.from_settings()
    last_exc: BaseException | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await func()
        except retry_on as exc:
            last_exc = exc
            if attempt == policy.max_attempts:
                break
            delay = policy.delay_for(attempt + 1)
            _log.warning(
                "%s failed (attempt %d/%d): %s — retrying in %.2fs",
                description, attempt, policy.max_attempts, exc, delay,
            )
            await sleep(delay)
    assert last_exc is not None
    _log.error("%s failed after %d attempts: %s", description, policy.max_attempts, last_exc)
    raise last_exc
