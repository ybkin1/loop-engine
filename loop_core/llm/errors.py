"""
LLM unified error family — one exception type, machine-readable error codes,
and an explicit `retryable` flag per code.

T-0090 D1: mirrors the StaffDeck ProtocolCallError pattern (llm/client.py)
so every consumer (router, audit, self-review, future self-audit loop) can
classify failures uniformly: "is it safe/pointless to retry?" is answered by
`err.retryable`, never by string matching.

Retryable codes are the ONLY ones the retry policy will re-attempt:
- RATE_LIMITED (429)              -> transient, back off and retry
- TIMEOUT                        -> transient, retry
- SERVER_ERROR (5xx)             -> transient, retry
- CONNECTION_ERROR (network)     -> transient, retry

Everything else fails fast (no point retrying 401/403/404/INVALID_RESPONSE/
CANCELLED/KEY_MISSING).  Empty responses get their own bounded retry counter
in the driver ("空响应重试，上限可配") and surface as INVALID_RESPONSE when
the bound is exhausted.

Security invariant: exception messages NEVER contain raw secrets — the
driver builds messages through the Redactor (`redaction.py`) before raising.
"""
from __future__ import annotations

from enum import Enum

__version__ = "1.0.0"


class ErrorCode(str, Enum):
    """Machine-readable LLM error codes (values are stable wire identifiers)."""

    # ── auth / permission (not retryable) ─────────────────────────────────
    MODEL_AUTHENTICATION_FAILED = "MODEL_AUTHENTICATION_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    KEY_MISSING = "KEY_MISSING"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"  # missing client lib / bad config
    # ── transient (retryable) ─────────────────────────────────────────────
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    SERVER_ERROR = "SERVER_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    # ── terminal (not retryable) ──────────────────────────────────────────
    CANCELLED = "CANCELLED"
    INVALID_RESPONSE = "INVALID_RESPONSE"

    @property
    def retryable(self) -> bool:
        """Whether the retry policy may re-attempt this failure class."""
        return self in _RETRYABLE_CODES

    @property
    def http_status(self) -> int | None:
        """Typical HTTP status this code maps from (None for non-HTTP)."""
        return _HTTP_STATUS.get(self)


_RETRYABLE_CODES = frozenset(
    {ErrorCode.RATE_LIMITED, ErrorCode.TIMEOUT, ErrorCode.SERVER_ERROR, ErrorCode.CONNECTION_ERROR}
)

_HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.MODEL_AUTHENTICATION_FAILED: 401,
    ErrorCode.PERMISSION_DENIED: 403,
    ErrorCode.MODEL_NOT_FOUND: 404,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.TIMEOUT: 408,
    ErrorCode.SERVER_ERROR: 500,
}


class LLMError(Exception):
    """Unified error for every failure surfaced by the LLM abstraction layer.

    `message` is pre-redacted by the caller (driver) — never embed raw
    api keys / tokens / request bodies here.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        operation: str = "",
        attempts: int = 1,
        status_code: int | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = ErrorCode(code)
        self.operation = operation
        self.attempts = attempts
        self.status_code = status_code
        self.request_id = request_id

    @property
    def retryable(self) -> bool:
        return self.code.retryable

    def to_dict(self) -> dict[str, object]:
        """Stable serialization for audit traces / guard events."""
        return {
            "error_code": self.code.value,
            "retryable": self.retryable,
            "message": str(self),
            "operation": self.operation,
            "attempts": self.attempts,
            "status_code": self.status_code,
            "request_id": self.request_id,
        }

    def __str__(self) -> str:  # keep message stable; str(exc) == message
        return super().__str__()


class LLMKeyError(LLMError):
    """API key could not be resolved from the environment (never a default)."""

    def __init__(self, message: str, *, operation: str = "") -> None:
        super().__init__(ErrorCode.KEY_MISSING, message, operation=operation)


class JSONRepairError(ValueError):
    """Structured output could not be repaired into valid JSON.

    Converted to LLMError(INVALID_RESPONSE) by the driver's complete_json()
    so callers only ever catch LLMError at the abstraction boundary.
    """

    def __init__(self, message: str, *, fragment: str = "", strategies_tried: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.fragment = fragment
        self.strategies_tried = strategies_tried
