"""
OpenAI-compatible protocol driver — Chat Completions over HTTP(S).

T-0090 D1: the required concrete ProtocolDriver (staffdeck protocol_drivers.py
OpenAI driver pattern, in loop-engine style).  One HTTP client, unified
LLMError surface, shared retry policy, redaction, output clamping.

Transport:
- Uses `httpx` (lazy import — an OPTIONAL runtime dependency like playwright
  in scripts/runtime_delivery_gate.py; declare it when the self-audit loop
  wires real connections, e.g. `pip install httpx`).  Without httpx the rest
  of loop_core still imports; only constructing this driver fails, with a
  clear CONFIGURATION_ERROR.
- `transport=` accepts httpx.MockTransport (tests) or any httpx transport;
  `None` means the real network — the runtime capability is provided but
  never exercised by tests or by default.

Error mapping (HTTP status -> ErrorCode):
  401 MODEL_AUTHENTICATION_FAILED | 403 PERMISSION_DENIED | 404 MODEL_NOT_FOUND
  408/httpx timeout TIMEOUT | 429 RATE_LIMITED | 5xx SERVER_ERROR
  other 4xx INVALID_RESPONSE | connect errors CONNECTION_ERROR

Secrets: the resolved api key seeds the Redactor; every error message is
built via `redactor.safe_fragment(...)` — a provider body that echoes the key
cannot leak it into exceptions or logs.
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

_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_TIMEOUT = 60.0

_EMPTY = object()  # sentinel: 200 response with no usable content


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
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return None
    try:
        return Usage(
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            total_tokens=int(usage.get("total_tokens", 0)),
        )
    except (TypeError, ValueError):
        return None


class OpenAICompatibleDriver:
    """OpenAI Chat Completions driver implementing the ProtocolDriver verbs."""

    name = "openai-compatible"

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
                "httpx is required for the OpenAI-compatible driver "
                "(pip install httpx) — loop-core itself stays dependency-free.",
            )
        if self._client is None:
            headers = {
                "Authorization": "Bearer " + self._resolve_key(),
                "Content-Type": "application/json",
            }
            self._client = httpx.Client(
                base_url=self.base_url,
                transport=self._transport,
                timeout=self.timeout,
                headers=headers,
            )
        return self._client

    @staticmethod
    def _request_headers(api_key: str) -> dict[str, str]:
        return {
            "Authorization": "Bearer " + api_key,
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
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": _effective_max_tokens(operation, max_tokens),
            "stream": stream,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        return payload

    def _extract_content(self, body: dict[str, Any], operation: str) -> str:
        """Pull the completion text out of a Chat Completions body."""
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""
        message = first.get("message") or {}
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
        # Some providers put content directly on the choice.
        if isinstance(first.get("content"), str):
            return first["content"]
        return ""

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
            response = client.post("/chat/completions", json=payload, timeout=timeout)
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
        text = self._extract_content(body, operation)
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
        """Incremental deltas (SSE).  Request-phase failures retry; failures
        after the first delta propagate immediately (a partial stream cannot
        be transparently re-run)."""
        self._check_cancelled()
        resolved_model = model or self.default_model
        if not resolved_model:
            raise LLMError(
                ErrorCode.CONFIGURATION_ERROR,
                "no model specified: pass model= or set default_model on the driver",
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
                    "POST", "/chat/completions", json=payload, timeout=timeout
                ) as response:
                    self._raise_for_status(response, operation)
                    for line in response.iter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except ValueError:
                            continue
                        if isinstance(chunk, dict) and "error" in chunk:
                            err = chunk["error"]
                            frag = self.redactor.safe_fragment(err, 200)
                            raise LLMError(
                                ErrorCode.SERVER_ERROR,
                                f"stream error: {frag}",
                                operation=operation,
                            )
                        delta = ""
                        choices = chunk.get("choices") if isinstance(chunk, dict) else None
                        if isinstance(choices, list) and choices:
                            first = choices[0]
                            if isinstance(first, dict):
                                d = first.get("delta") or {}
                                if isinstance(d, dict) and isinstance(d.get("content"), str):
                                    delta = d["content"]
                        if delta:
                            self._check_cancelled()
                            yielded_any = True
                            first_delta = False
                            yield delta
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
