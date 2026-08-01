"""
ProtocolDriver — the unified LLM interface every driver implements.

T-0090 D1: mirrors StaffDeck protocol_drivers.py.  Two verbs only:
  - complete(): one-shot text generation (with optional JSON repair mode)
  - stream():   incremental text generation (SSE deltas)

Every implementation:
  - raises only LLMError subclasses (unified error codes, `retryable` flag);
  - applies the shared retry policy to retryable codes;
  - redacts secrets from all error messages and logs;
  - honours the operation-level output token cap (output_policy.py).
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from loop_core.llm.output_policy import cap_for_operation

__version__ = "1.0.0"


@dataclass(frozen=True)
class Usage:
    """Token usage as reported by the provider (may be None per provider)."""
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class CompletionResult:
    """Outcome of a complete() call — text plus audit metadata."""
    text: str
    model: str
    operation: str
    attempts: int = 1
    usage: Usage | None = None
    clamped: bool = False
    clamp_cap: int | None = None
    repair_strategy: str | None = None   # set by complete_json()

    @property
    def approx_output_tokens(self) -> int:
        from loop_core.llm.output_policy import approx_tokens
        return approx_tokens(self.text)


@dataclass(frozen=True)
class JSONResult:
    """Outcome of a complete_json() call — parsed data plus repair metadata."""
    text: str
    data: Any
    model: str
    operation: str
    attempts: int = 1
    repair_strategy: str = "identity"
    usage: Usage | None = None


@runtime_checkable
class ProtocolDriver(Protocol):
    """The unified driver contract (complete + stream + unified errors)."""

    name: str

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        operation: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout: float | None = None,
    ) -> CompletionResult:
        """One-shot completion.  Raises LLMError on any failure."""
        ...

    def complete_json(
        self,
        messages: list[dict[str, str]],
        *,
        operation: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout: float | None = None,
    ) -> JSONResult:
        """Completion whose output is repaired/parsed as JSON."""
        ...

    def stream(
        self,
        messages: list[dict[str, str]],
        *,
        operation: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout: float | None = None,
    ) -> Iterator[str]:
        """Incremental text deltas.  Raises LLMError on any failure."""
        ...

    def cancel(self) -> None:
        """Request cancellation; in-flight/next calls raise CANCELLED."""
        ...


def effective_max_tokens(operation: str, max_tokens: int | None) -> int:
    """Request-level output budget: explicit override wins, else op cap."""
    if max_tokens is not None:
        return max_tokens
    return cap_for_operation(operation)
