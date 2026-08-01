"""
Retry policy — exponential backoff for retryable LLM errors, plus a bounded
separate retry budget for empty responses.

T-0090 D1: only ErrorCode.retryable codes are re-attempted
(RATE_LIMITED / TIMEOUT / SERVER_ERROR / CONNECTION_ERROR — see errors.py).
A 401/403/404/CANCELLED failure raises immediately (no pointless retries).
Empty 200 responses (no choices / blank content) get their own configurable
retry budget ("空响应重试，上限可配") and surface as INVALID_RESPONSE when
exhausted.

`sleep_fn` is injectable (tests record delays and use sleep_fn=lambda _: None)
so backoff behaviour is verified deterministically without waiting.
"""
from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from loop_core.llm.errors import ErrorCode

__version__ = "1.0.0"

_RETRYABLE_DEFAULT = frozenset(
    {
        ErrorCode.RATE_LIMITED,
        ErrorCode.TIMEOUT,
        ErrorCode.SERVER_ERROR,
        ErrorCode.CONNECTION_ERROR,
    }
)

SleepFn = Callable[[float], None]


@dataclass(frozen=True)
class RetryPolicy:
    """Backoff + attempt budget shared by every protocol driver."""

    max_attempts: int = 3                 # total attempts incl. the first
    base_delay: float = 0.5               # delay for the 1st retry (seconds)
    max_delay: float = 8.0                # backoff ceiling (seconds)
    backoff_factor: float = 2.0           # delay *= factor per retry
    jitter: float = 0.0                   # optional +/- jitter fraction
    empty_response_retries: int = 1       # extra attempts on EMPTY responses
    retryable_codes: frozenset[ErrorCode] = field(default_factory=lambda: _RETRYABLE_DEFAULT)

    def delay_for(self, attempt: int) -> float:
        """Backoff delay for the given attempt number (1-based retry index)."""
        if attempt <= 0:
            return 0.0
        delay = min(self.max_delay, self.base_delay * (self.backoff_factor ** (attempt - 1)))
        if self.jitter > 0:
            delay = max(0.0, delay * (1.0 + random.uniform(-self.jitter, self.jitter)))
        return delay

    def is_retryable(self, code: ErrorCode) -> bool:
        return code in self.retryable_codes


def sleep_with_backoff(
    policy: RetryPolicy,
    attempt: int,
    sleep_fn: SleepFn = time.sleep,
) -> None:
    """Sleep the policy's backoff delay for the given retry attempt."""
    sleep_fn(policy.delay_for(attempt))
