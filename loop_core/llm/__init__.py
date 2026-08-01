"""
loop_core.llm — LLM access abstraction layer (T-0090 D1).

Protocol-driver unified interface (complete / stream), unified error codes
with retryable flags, exponential-backoff retry, multi-candidate JSON repair,
secret redaction, operation-level output token clamping, and environment-only
API key resolution.  B5 self-audit loop prerequisite: loop-engine can call
LLMs itself through this layer without depending on the host.

Security invariants (enforced by tests, tests/test_llm_layer.py):
- API keys come ONLY from environment variables (never hardcoded);
- errors/logs never contain raw secrets (Redactor);
- tests never hit a real network (httpx.MockTransport only).
"""
from __future__ import annotations

from loop_core.llm.anthropic_driver import AnthropicMessagesDriver
from loop_core.llm.errors import (
    ErrorCode,
    JSONRepairError,
    LLMError,
    LLMKeyError,
)
from loop_core.llm.json_repair import repair_json
from loop_core.llm.keys import KEY_ENV_VARS, resolve_api_key
from loop_core.llm.openai_driver import OpenAICompatibleDriver
from loop_core.llm.output_policy import (
    OUTPUT_TOKEN_CAPS,
    ClampResult,
    approx_tokens,
    cap_for_operation,
    clamp_output,
)
from loop_core.llm.protocol_driver import (
    CompletionResult,
    JSONResult,
    ProtocolDriver,
    Usage,
    effective_max_tokens,
)
from loop_core.llm.redaction import Redactor, make_redactor
from loop_core.llm.retry import RetryPolicy, sleep_with_backoff

__version__ = "1.0.0"

__all__ = [
    "ErrorCode",
    "LLMError",
    "LLMKeyError",
    "JSONRepairError",
    "repair_json",
    "KEY_ENV_VARS",
    "resolve_api_key",
    "AnthropicMessagesDriver",
    "OpenAICompatibleDriver",
    "ProtocolDriver",
    "CompletionResult",
    "JSONResult",
    "Usage",
    "effective_max_tokens",
    "Redactor",
    "make_redactor",
    "ClampResult",
    "OUTPUT_TOKEN_CAPS",
    "approx_tokens",
    "cap_for_operation",
    "clamp_output",
    "RetryPolicy",
    "sleep_with_backoff",
]
