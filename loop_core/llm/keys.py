"""
API key resolution — environment variables ONLY, never hardcoded, never defaulted.

T-0090 D1 security red line: keys come from the process environment
(LLM_API_KEY first, then provider-specific fallbacks).  If nothing is set the
caller gets LLMKeyError(KEY_MISSING) with a message naming the checked
variables — an explicit failure instead of silently sending an empty key.

For tests, `env` may be injected as a plain mapping (see tests/test_llm_layer.py
AC-01f) so no real environment is touched.
"""
from __future__ import annotations

import os
from collections.abc import Mapping

from loop_core.llm.errors import LLMKeyError

__version__ = "1.0.0"

# Resolution order: first variable that is set and non-empty wins.
KEY_ENV_VARS: tuple[str, ...] = (
    "LLM_API_KEY",      # canonical loop-engine key
    "DEEPSEEK_API_KEY",  # deepseek-compatible endpoints (Chat Completions)
    "OPENAI_API_KEY",   # openai-compatible endpoints
    "ANTHROPIC_API_KEY",  # anthropic-style endpoints (future drivers)
)


def resolve_api_key(
    env: Mapping[str, str] | None = None,
    *,
    operation: str = "",
) -> str:
    """Resolve the API key from environment variables.

    Priority: LLM_API_KEY, DEEPSEEK_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
    (first non-empty wins).  Raises LLMKeyError(KEY_MISSING) when none is set —
    never returns an empty or placeholder key.  The error message lists the
    variable NAMES only (values never leak into messages).
    """
    source = os.environ if env is None else env
    for var in KEY_ENV_VARS:
        value = source.get(var)
        if value and value.strip():
            return value.strip()
    raise LLMKeyError(
        "LLM API key missing: set one of the environment variables "
        + ", ".join(KEY_ENV_VARS)
        + " (keys are read from the environment only; never hardcoded).",
        operation=operation,
    )
