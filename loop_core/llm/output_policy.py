"""
Operation-level output token clamping — mirrors StaffDeck output_policy.py.

T-0090 D1: every call into the LLM layer carries an `operation`; the policy
maps it to a max output token budget.  The driver applies the budget two ways:
  1. request-level  — `max_tokens` in the Chat Completions body is set to the
     operation cap (the model stops generating at the budget);
  2. response-level — a defensive post-clamp truncates output that still
     exceeds the cap (models may ignore max_tokens / streaming may overrun),
     marking the result `clamped` so consumers can audit the truncation.

Token counting is approximate (chars / CHARS_PER_TOKEN, 4 chars ~ 1 token) —
documented deliberately: loop-engine's abstraction does not depend on a
vendor tokenizer; caps are enforced conservatively at the character level.
"""
from __future__ import annotations

from dataclasses import dataclass

__version__ = "1.0.0"

# ── operation -> max output tokens (request-level cap + post-clamp) ────────
# Operations are governance roles/acts that will consume LLM output
# (T-0090/B5: router, audit, self-review are the first self-audit consumers).
DEFAULT_OUTPUT_TOKEN_CAP = 4000

OUTPUT_TOKEN_CAPS: dict[str, int] = {
    "router": 4000,       # intent routing decisions
    "audit": 8000,        # audit findings (longer, structured)
    "self-review": 6000,  # self-review verdict + rationale
    "planner": 8000,      # plan generation
    "summarize": 2000,    # context summaries — deliberately tight
    "classify": 1000,     # short classification labels
    "default": DEFAULT_OUTPUT_TOKEN_CAP,
}

CHARS_PER_TOKEN = 4  # conservative heuristic: 4 chars ≈ 1 token

_CLAMP_SUFFIX = "\n[clamped: output truncated by loop-engine output policy]"


@dataclass(frozen=True)
class ClampResult:
    """Result of clamping — text may be truncated; metadata preserved."""
    text: str
    clamped: bool
    cap_tokens: int
    approx_tokens: int
    operation: str


def cap_for_operation(operation: str) -> int:
    """Max output tokens allowed for an operation (unknown -> default cap)."""
    return OUTPUT_TOKEN_CAPS.get(operation, DEFAULT_OUTPUT_TOKEN_CAP)


def approx_tokens(text: str) -> int:
    """Rough token estimate (chars / CHARS_PER_TOKEN), never negative."""
    return max(1, (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN)


def clamp_output(
    text: str,
    operation: str,
    *,
    max_tokens: int | None = None,
    chars_per_token: int = CHARS_PER_TOKEN,
) -> ClampResult:
    """Clamp `text` to the operation's output token budget.

    `max_tokens` overrides the operation cap (driver passes the effective
    request cap so both layers agree).  Returns the (possibly truncated)
    text plus clamp metadata; truncation appends an explicit marker so
    downstream consumers can detect and audit it.
    """
    cap = cap_for_operation(operation) if max_tokens is None else max_tokens
    estimate = max(1, (len(text) + chars_per_token - 1) // chars_per_token)
    if estimate <= cap or not text:
        return ClampResult(text=text, clamped=False, cap_tokens=cap,
                           approx_tokens=estimate, operation=operation)
    keep_chars = cap * chars_per_token
    truncated = text[:keep_chars] + _CLAMP_SUFFIX
    return ClampResult(text=truncated, clamped=True, cap_tokens=cap,
                       approx_tokens=estimate, operation=operation)
