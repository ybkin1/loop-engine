"""
API key resolution — environment variables ONLY, never hardcoded, never defaulted.

T-0090 D1 security red line: keys come from the process environment
(LLM_API_KEY first, then provider-specific fallbacks).  If nothing is set the
caller gets LLMKeyError(KEY_MISSING) with a message naming the checked
variables — an explicit failure instead of silently sending an empty key.

T-0095 (env chain unification): ``KEY_TIERS`` is the canonical env tier table
— the single source of truth for the key + base-url pair priority shared with
``loop_core/llm/zcode_config.ENV_TIERS``.  Unified priority:

    LLM_*  ->  ANTHROPIC_*  ->  OPENAI_*  ->  ZCODE_*   (+ DEEPSEEK_* legacy
    alias tier checked last, so the canonical order is never disturbed).

Each tier pairs its key variable with a base-url variable; the winning tier's
base url is exposed by ``resolve_api_base_url`` (optional — an unset base url
is legal and yields "").

For tests, `env` may be injected as a plain mapping (see tests/test_llm_layer.py
AC-01f) so no real environment is touched.
"""
from __future__ import annotations

import os
from collections.abc import Mapping

from loop_core.llm.errors import LLMKeyError

__version__ = "2.0.0"

# ── Canonical env tier table (T-0095) ────────────────────────────────────
# (key var, base-url var, protocol) — first tier whose key is set and
# non-empty wins.  ``zcode_config.ENV_TIERS`` aliases this table so both
# resolution paths can never drift apart.
KEY_TIERS: tuple[tuple[str, str, str], ...] = (
    ("LLM_API_KEY", "LLM_BASE_URL", "openai"),        # canonical loop-engine key
    ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "anthropic"),  # anthropic-style endpoints
    ("OPENAI_API_KEY", "OPENAI_BASE_URL", "openai"),  # openai-compatible endpoints
    ("ZCODE_API_KEY", "ZCODE_BASE_URL", "openai"),    # ZCode CLI fallback
    ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "openai"),  # legacy alias tier (last)
)

# Key variable names in canonical order (kept for backward compatibility).
KEY_ENV_VARS: tuple[str, ...] = tuple(tier[0] for tier in KEY_TIERS)


def resolve_api_key(
    env: Mapping[str, str] | None = None,
    *,
    operation: str = "",
) -> str:
    """Resolve the API key from environment variables.

    Priority (T-0095 unified chain): LLM_API_KEY, ANTHROPIC_API_KEY,
    OPENAI_API_KEY, ZCODE_API_KEY, then the legacy DEEPSEEK_API_KEY alias
    (first non-empty wins).  Raises LLMKeyError(KEY_MISSING) when none is
    set — never returns an empty or placeholder key.  The error message lists
    the variable NAMES only (values never leak into messages).
    """
    source = os.environ if env is None else env
    for key_var, _base_url_var, _protocol in KEY_TIERS:
        value = source.get(key_var)
        if value and value.strip():
            return value.strip()
    raise LLMKeyError(
        "LLM API key missing: set one of the environment variables "
        + ", ".join(KEY_ENV_VARS)
        + " (keys are read from the environment only; never hardcoded).",
        operation=operation,
    )


def resolve_api_base_url(
    env: Mapping[str, str] | None = None,
    *,
    operation: str = "",
) -> str:
    """Resolve the base URL paired with the winning key tier (optional).

    Returns the base-url variable of the tier whose key ``resolve_api_key``
    would pick ('' when that variable is unset or blank — an empty base url
    means "provider default endpoint", which is legal).  Returns '' when no
    key tier is set at all; the caller that needs a key should call
    ``resolve_api_key`` (which raises KEY_MISSING explicitly).
    """
    source = os.environ if env is None else env
    for key_var, base_url_var, _protocol in KEY_TIERS:
        value = source.get(key_var)
        if value and value.strip():
            return (source.get(base_url_var) or "").strip()
    return ""
