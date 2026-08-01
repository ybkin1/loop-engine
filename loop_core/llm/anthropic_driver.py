"""
Anthropic Messages protocol driver — POST /v1/messages with SSE streaming.

T-0091: every model provider in the ZCode host is `anthropic` kind (the
Messages API), so the self-audit loop needs this concrete ProtocolDriver to
reach them.  It mirrors the T-0090 OpenAI driver (httpx lazy import,
MockTransport injection, SSE parsing, cancellation, error mapping, secret
redaction, output clamping, bounded empty-response retries) with Anthropic
wire semantics:

Transport:
- POST {base_url}/v1/messages; base_url defaults to the public Anthropic
  endpoint.  Auth is the `x-api-key` header plus `anthropic-version:
  2023-06-01` — the same pair the ZCode internal SDK sends.
- `transport=` accepts httpx.MockTransport (tests) or any httpx transport;
  `None` means the real network — the runtime capability is provided but
  never exercised by tests or by default.
- httpx is lazy-imported (OPTIONAL runtime dependency, same as the OpenAI
  driver); without it only constructing the driver fails with a clear
  CONFIGURATION_ERROR.

Wire format:
- Request body: model / max_tokens / system (top-level, extracted from any
  role=system messages) / messages (roles user|assistant) / stream /
  optional temperature.
- Non-streaming response: `content[]` text blocks joined into one string;
  `usage` maps {input_tokens, output_tokens} -> Usage.
- Streaming: SSE `data:` events — message_start / content_block_delta
  (delta.type == text_delta -> delta.text) / message_stop (stream end) /
  error (mapped to a unified ErrorCode) / ping (keep-alive, skipped).

Error mapping (HTTP status -> ErrorCode):
  401 MODEL_AUTHENTICATION_FAILED | 403 PERMISSION_DENIED | 404 MODEL_NOT_FOUND
  408/httpx timeout TIMEOUT | 429 RATE_LIMITED | 5xx SERVER_ERROR
  other 4xx INVALID_RESPONSE | connect errors CONNECTION_ERROR
Retryable semantics are identical to openai_driver.py (see errors.py).

Secrets: the resolved api key seeds the Redactor; every error message is
built via `redactor.safe_fragment(...)` — a provider body that echoes the
key cannot leak it into exceptions or logs.
"""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Iterator
from typing import Any

from loop_core.llm.errors import ErrorCode, JSONRepairError, LLMError
from loop_core.llm.json_repair import repair_json
from loop_core.llm.keys import resolve_api_key
from loop_core.llm.output_policy import clamp_output
from loop_core.llm.protocol_driver import (
    CompletionResult,
    JSONResult,
    Usage,
)
from loop_core.llm.protocol_driver import (
    effective_max_tokens as _effective_max_tokens,
)
from loop_core.llm.redaction import Redactor, make_redactor
from loop_core.llm.retry import RetryPolicy, sleep_with_backoff

__version__ = "1.0.0"

logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError:  # pragma: no cover — optional runtime dependency
    httpx = None  # type: ignore[assignment]

# Exception aliases so `except` clauses never touch `httpx` when it is absent.
if httpx is None:  # pragma: no cover — optional runtime dependency
    _TIMEOUT_EXCEPTIONS: tuple[type[BaseException], ...] = ()
    _TRANSPORT_EXCEPTIONS: tuple[type[BaseException], ...] = ()
else:
    _TIMEOUT_EXCEPTIONS = (httpx.TimeoutException,)
    _TRANSPORT_EXCEPTIONS = (httpx.TransportError,)

_DEFAULT_BASE_URL = "https://api.anthropic.com"
_DEFAULT_TIMEOUT = 60.0
_ANTHROPIC_VERSION = "2023-06-01"   # wire protocol version header value
_MESSAGES_PATH = "/v1/messages"
_SYSTEM_ROLE = "system"

# Anthropic streaming `error` event types -> unified ErrorCodes.  Unknown
# types fall back to SERVER_ERROR (retryable).
_STREAM_ERROR_TYPES: dict[str, ErrorCode] = {
    "authentication_error": ErrorCode.MODEL_AUTHENTICATION_FAILED,
    "permission_error": ErrorCode.PERMISSION_DENIED,
    "not_found_error": ErrorCode.MODEL_NOT_FOUND,
    "rate_limit_error": ErrorCode.RATE_LIMITED,
    "timeout_error": ErrorCode.TIMEOUT,
    "api_error": ErrorCode.SERVER_ERROR,
    "overloaded_error": ErrorCode.SERVER_ERROR,
    "invalid_request_error": ErrorCode.INVALID_RESPONSE,
}


def _map_http_status(status: int) -> ErrorCode:
    """HTTP status -> unified error code (retryable flags live in ErrorCode)."""
    if status == 401:
        return ErrorCode.MODEL_AUTHENTICATION_FAILED
    if status == 403:
        return ErrorCode.PERMISSION_DENIED
    if status == 404:
        return ErrorCode.MODEL_NOT_FOUND
    if status == 408:
        return ErrorCode.TIMEOUT
    if status == 429:
        return ErrorCode.RATE_LIMITED
    if status >= 500:
        return ErrorCode.SERVER_ERROR
    return ErrorCode.INVALID_RESPONSE


def _extract_usage(body: dict[str, Any]) -> Usage | None:
    """Anthropic usage: {input_tokens, output_tokens} -> unified Usage."""
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return None
    try:
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        return Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )
    except (TypeError, ValueError):
        return None


def _extract_content(body: dict[str, Any], operation: str) -> str:
    """Join text blocks from an Anthropic `content` array into one string."""
    content = body.get("content")
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)


class AnthropicMessagesDriver:
    """Anthropic Messages API driver implementing the ProtocolDriver verbs."""

    name = "anthropic-messages"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        transport: Any = None,
        retry_policy: RetryPolicy | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        redactor: Redactor | None = None,
    ) -> None:
        self.base_url = (base_url or _DEFAULT_BASE_URL).rstrip("/")
        self.default_model = default_model
        self.timeout = timeout
        self._transport = transport
        # Key is resolved lazily at first use so constructing a driver is
        # side-effect free (and tests can inject a fake key).
        self._api_key: str | None = api_key
        self._key_resolved = api_key is not None
        self.retry_policy = retry_policy or RetryPolicy()
        self._sleep_fn = sleep_fn
        self._redactor = redactor
        self._client: Any = None
        self._cancelled = False

    # ── secrets / redaction ───────────────────────────────────────────────

    @property
    def redactor(self) -> Redactor:
        """Redactor seeded with the resolved key (never expose the key)."""
        if self._redactor is None:
            self._redactor = make_redactor(self._resolve_key())
        return self._redactor

    # ── cancellation ──────────────────────────────────────────────────────

    def cancel(self) -> None:
        """Request cancellation: the next entry/checkpoint raises CANCELLED."""
        self._cancelled = True

    def _check_cancelled(self) -> None:
        if self._cancelled:
            self._cancelled = False  # one-shot: consumer may retry afterwards
            raise LLMError(ErrorCode.CANCELLED, "request cancelled", operation="")

    # ── key resolution ────────────────────────────────────────────────────

    def _resolve_key(self) -> str:
        if not self._key_resolved:
            self._api_key = resolve_api_key(operation=self.name)
            self._key_resolved = True
        return self._api_key or ""

    # ── http plumbing ─────────────────────────────────────────────────────

    def _ensure_client(self) -> Any:
        if httpx is None:  # pragma: no cover — exercised only without httpx
            raise LLMError(
                ErrorCode.CONFIGURATION_ERROR,
                "httpx is required for the Anthropic Messages driver "
                "(pip install httpx) — loop-core itself stays dependency-free.",
            )
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                transport=self._transport,
                timeout=self.timeout,
                headers=self._request_headers(self._resolve_key()),
            )
        return self._client

    @staticmethod
    def _request_headers(api_key: str) -> dict[str, str]:
        """Anthropic auth pair: x-api-key + anthropic-version (SDK parity)."""
        return {
            "x-api-key": api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

    def _error_from_response(self, response: Any, operation: str) -> LLMError:
        """Build a redacted LLMError from a non-2xx response."""
        code = _map_http_status(response.status_code)
        body = self.redactor.safe_fragment(response.text, max_len=300)
        request_id = ""
        rid = response.headers.get("x-request-id") or response.headers.get("request-id")
        if rid:
            request_id = str(rid)
        message = f"provider error [{response.status_code}]: {body}" if body else f"provider error [{response.status_code}]"
        return LLMError(
            code,
            message,
            operation=operation,
            status_code=response.status_code,
            request_id=request_id or None,
        )

    def _raise_for_status(self, response: Any, operation: str) -> None:
        if response.status_code < 200 or response.status_code >= 300:
            raise self._error_from_response(response, operation)

    # ── payload / parsing ─────────────────────────────────────────────────

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        model: str,
        *,
        operation: str,
        max_tokens: int | None,
        temperature: float | None,
        stream: bool,
    ) -> dict[str, Any]:
        """Anthropic request body.

        role=system messages are lifted into the top-level `system` field
        (the Messages API has no system role inside `messages`); the rest
        (user/assistant) are sent verbatim.
        """
        system_parts = [
            m["content"]
            for m in messages
            if m.get("role") == _SYSTEM_ROLE and isinstance(m.get("content"), str)
        ]
        chat_messages = [m for m in messages if m.get("role") != _SYSTEM_ROLE]
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": _effective_max_tokens(operation, max_tokens),
            "messages": chat_messages,
            "stream": stream,
        }
        if system_parts:
            payload["system"] = "\n".join(system_parts)
        if temperature is not None:
            payload["temperature"] = temperature
        return payload

    # ── single attempt ────────────────────────────────────────────────────

    def _complete_once(
        self,
        client: Any,
        payload: dict[str, Any],
        operation: str,
        timeout: float | None,
    ) -> tuple[str, Usage | None]:
        """One HTTP round trip.  Returns (text, usage); "" == empty response."""
        try:
            response = client.post(_MESSAGES_PATH, json=payload, timeout=timeout)
        except _TIMEOUT_EXCEPTIONS as exc:
            raise LLMError(
                ErrorCode.TIMEOUT, f"request timed out: {self.redactor.safe_fragment(str(exc), 160)}",
                operation=operation,
            ) from exc
        except _TRANSPORT_EXCEPTIONS as exc:
            raise LLMError(
                ErrorCode.CONNECTION_ERROR,
                f"connection failed: {self.redactor.safe_fragment(str(exc), 160)}",
                operation=operation,
            ) from exc
        self._raise_for_status(response, operation)
        try:
            body = response.json()
        except ValueError as exc:
            raise LLMError(
                ErrorCode.INVALID_RESPONSE,
                "provider returned non-JSON body: "
                + self.redactor.safe_fragment(response.text, 200),
                operation=operation,
                status_code=response.status_code,
            ) from exc
        if not isinstance(body, dict):
            raise LLMError(
                ErrorCode.INVALID_RESPONSE,
                "provider returned unexpected payload shape",
                operation=operation,
                status_code=response.status_code,
            )
        text = _extract_content(body, operation)
        return text, _extract_usage(body)

    # ── retry loop (retryable codes + bounded empty-response retries) ─────

    def _run_with_retry(
        self,
        messages: list[dict[str, str]],
        *,
        operation: str,
        model: str | None,
        max_tokens: int | None,
        temperature: float | None,
        timeout: float | None,
        stream: bool = False,
    ) -> tuple[str, Usage | None, int]:
        """complete()-style retry loop; returns (text, usage, attempts)."""
        self._check_cancelled()
        resolved_model = model or self.default_model
        if not resolved_model:
            raise LLMError(
                ErrorCode.CONFIGURATION_ERROR,
                "no model specified: pass model= or set default_model on the driver",
                operation=operation,
            )
        if not isinstance(messages, list) or not messages:
            raise LLMError(
                ErrorCode.CONFIGURATION_ERROR,
                "messages must be a non-empty list of {role, content} dicts",
                operation=operation,
            )
        if not any(
            isinstance(m, dict) and m.get("role") != _SYSTEM_ROLE for m in messages
        ):
            raise LLMError(
                ErrorCode.CONFIGURATION_ERROR,
                "messages must contain at least one user/assistant message "
                "(system prompts go into the top-level `system` field)",
                operation=operation,
            )
        client = self._ensure_client()
        payload = self._build_payload(messages, resolved_model, operation=operation,
                                      max_tokens=max_tokens, temperature=temperature,
                                      stream=stream)
        policy = self.retry_policy
        attempts = 0
        empty_retries = 0
        while True:
            attempts += 1
            try:
                text, usage = self._complete_once(client, payload, operation, timeout)
            except LLMError as exc:
                if not (policy.is_retryable(exc.code) and attempts < policy.max_attempts):
                    exc.attempts = attempts
                    raise
                logger.warning(
                    "llm retryable error op=%s code=%s attempt=%d/%d",
                    operation, exc.code.value, attempts, policy.max_attempts,
                )
                sleep_with_backoff(policy, attempts, self._sleep_fn)
                continue
            if text.strip():
                return text, usage, attempts
            # empty 200 response — bounded separate retry budget
            if empty_retries < policy.empty_response_retries and attempts < policy.max_attempts:
                empty_retries += 1
                logger.warning(
                    "llm empty response op=%s attempt=%d empty_retry=%d/%d",
                    operation, attempts, empty_retries, policy.empty_response_retries,
                )
                sleep_with_backoff(policy, attempts, self._sleep_fn)
                continue
            raise LLMError(
                ErrorCode.INVALID_RESPONSE,
                f"empty response after {attempts} attempt(s) (op={operation})",
                operation=operation,
                attempts=attempts,
            )

    # ── public verbs ──────────────────────────────────────────────────────

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
        """One-shot completion with retry, redaction and output clamping."""
        text, usage, attempts = self._run_with_retry(
            messages, operation=operation, model=model, max_tokens=max_tokens,
            temperature=temperature, timeout=timeout,
        )
        cap = _effective_max_tokens(operation, max_tokens)
        clamped = clamp_output(text, operation, max_tokens=cap)
        resolved_model = model or self.default_model or ""
        logger.info(
            "llm complete ok op=%s model=%s attempts=%d clamped=%s chars=%d",
            operation, resolved_model, attempts, clamped.clamped, len(text),
        )
        return CompletionResult(
            text=clamped.text,
            model=resolved_model,
            operation=operation,
            attempts=attempts,
            usage=usage,
            clamped=clamped.clamped,
            clamp_cap=cap if clamped.clamped else None,
        )

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
        """Completion whose output is repaired and parsed as JSON."""
        text, usage, attempts = self._run_with_retry(
            messages, operation=operation, model=model, max_tokens=max_tokens,
            temperature=temperature, timeout=timeout,
        )
        try:
            data, strategy = repair_json(text, context=operation)
        except JSONRepairError as exc:
            raise LLMError(
                ErrorCode.INVALID_RESPONSE,
                f"JSON repair failed for op={operation}: {self.redactor.safe_fragment(exc.fragment, 160)}",
                operation=operation,
                attempts=attempts,
            ) from exc
        resolved_model = model or self.default_model or ""
        logger.info(
            "llm complete_json ok op=%s model=%s strategy=%s attempts=%d",
            operation, resolved_model, strategy, attempts,
        )
        return JSONResult(
            text=text,
            data=data,
            model=resolved_model,
            operation=operation,
            attempts=attempts,
            repair_strategy=strategy,
            usage=usage,
        )

    # ── streaming ─────────────────────────────────────────────────────────

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
        """Incremental deltas (Anthropic SSE events).  Request-phase failures
        retry; failures after the first delta propagate immediately (a
        partial stream cannot be transparently re-run)."""
        self._check_cancelled()
        resolved_model = model or self.default_model
        if not resolved_model:
            raise LLMError(
                ErrorCode.CONFIGURATION_ERROR,
                "no model specified: pass model= or set default_model on the driver",
                operation=operation,
            )
        if not isinstance(messages, list) or not messages:
            raise LLMError(
                ErrorCode.CONFIGURATION_ERROR,
                "messages must be a non-empty list of {role, content} dicts",
                operation=operation,
            )
        client = self._ensure_client()
        payload = self._build_payload(messages, resolved_model, operation=operation,
                                      max_tokens=max_tokens, temperature=temperature,
                                      stream=True)
        policy = self.retry_policy
        attempts = 0
        empty_retries = 0
        while True:
            attempts += 1
            yielded_any = False
            first_delta = True
            try:
                with client.stream(
                    "POST", _MESSAGES_PATH, json=payload, timeout=timeout
                ) as response:
                    self._raise_for_status(response, operation)
                    for line in response.iter_lines():
                        if not line or not line.startswith("data:"):
                            continue  # skip event:/comment/blank SSE lines
                        data = line[5:].strip()
                        if not data:
                            continue
                        try:
                            event = json.loads(data)
                        except ValueError:
                            continue
                        if not isinstance(event, dict):
                            continue
                        etype = event.get("type")
                        if etype == "message_stop":
                            break
                        if etype == "content_block_delta":
                            delta = event.get("delta")
                            if (
                                isinstance(delta, dict)
                                and delta.get("type") == "text_delta"
                            ):
                                text = delta.get("text")
                                if isinstance(text, str) and text:
                                    self._check_cancelled()
                                    yielded_any = True
                                    first_delta = False
                                    yield text
                        elif etype == "error":
                            err = event.get("error") or {}
                            frag = self.redactor.safe_fragment(err, 200)
                            err_type = err.get("type") if isinstance(err, dict) else None
                            code = (
                                _STREAM_ERROR_TYPES.get(str(err_type))
                                if err_type else None
                            )
                            raise LLMError(
                                code or ErrorCode.SERVER_ERROR,
                                f"stream error: {frag}",
                                operation=operation,
                            )
                        # message_start / content_block_start / content_block_stop
                        # / message_delta / ping -> no text, keep waiting.
            except LLMError as exc:
                if first_delta and policy.is_retryable(exc.code) and attempts < policy.max_attempts:
                    sleep_with_backoff(policy, attempts, self._sleep_fn)
                    continue
                exc.attempts = attempts
                raise
            except _TIMEOUT_EXCEPTIONS as exc:
                if first_delta and attempts < policy.max_attempts:
                    sleep_with_backoff(policy, attempts, self._sleep_fn)
                    continue
                raise LLMError(
                    ErrorCode.TIMEOUT,
                    f"stream timed out: {self.redactor.safe_fragment(str(exc), 160)}",
                    operation=operation,
                    attempts=attempts,
                ) from exc
            except _TRANSPORT_EXCEPTIONS as exc:
                if first_delta and attempts < policy.max_attempts:
                    sleep_with_backoff(policy, attempts, self._sleep_fn)
                    continue
                raise LLMError(
                    ErrorCode.CONNECTION_ERROR,
                    f"stream connection failed: {self.redactor.safe_fragment(str(exc), 160)}",
                    operation=operation,
                    attempts=attempts,
                ) from exc
            if yielded_any:
                return
            # stream produced zero deltas — bounded empty retries
            if empty_retries < policy.empty_response_retries and attempts < policy.max_attempts:
                empty_retries += 1
                sleep_with_backoff(policy, attempts, self._sleep_fn)
                continue
            raise LLMError(
                ErrorCode.INVALID_RESPONSE,
                f"empty stream after {attempts} attempt(s) (op={operation})",
                operation=operation,
                attempts=attempts,
            )
