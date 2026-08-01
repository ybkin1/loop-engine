"""
T-0091 AC-01 — Anthropic Messages protocol driver tests.

ALL tests are fully mocked:
- HTTP layer: httpx.MockTransport handlers (no real network — an autouse
  guard blocks http.client/socket connections and records every httpx.Client
  instantiation; test_no_real_network_calls asserts every client was created
  with a mock transport).
- Keys: fake test-only keys injected explicitly (never real credentials).

AC mapping:
  AC-01a test_complete* (x-api-key + anthropic-version headers, content[].text,
         usage, request body shape) / test_stream* (SSE event sequence ->
         text fragments, message_stop ends) / protocol contract
  AC-01b test_stream_error_event* (SSE `error` event -> unified ErrorCode)
  AC-01c error mapping + retryable retry behaviour (401/403/408/429/500,
         httpx timeout, connection error)
  AC-01d empty-response retry (bounded budget) + secret redaction
         (key never in error messages)
  AC-01e output clamping (request cap + post-clamp) + cancel semantics
"""
from __future__ import annotations

import http.client
import json
import socket
from pathlib import Path

import httpx
import pytest

import loop_core.llm.anthropic_driver as anthropic_driver
from loop_core.llm import (
    AnthropicMessagesDriver,
    CompletionResult,
    ErrorCode,
    JSONResult,
    LLMError,
    LLMKeyError,
    cap_for_operation,
)
from loop_core.llm.retry import RetryPolicy

FAKE_KEY = "sk-test-0123456789abcdef"  # fake test-only key (never a real secret)
BASE = "https://anthropic.test.invalid"  # .invalid TLD — never resolvable

# ── shared mock handlers ───────────────────────────────────────────────────


def _messages_response(text: str, model: str = "claude-test", **extra: object) -> httpx.Response:
    body: dict[str, object] = {
        "id": "msg_test_001",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 5, "output_tokens": 2},
    }
    body.update(extra)
    return httpx.Response(200, json=body)


def _error_response(status: int, message: str, *, error_type: str = "api_error",
                    request_id: str | None = None) -> httpx.Response:
    body = {"type": "error", "error": {"type": error_type, "message": message}}
    headers = {"x-request-id": request_id} if request_id else None
    return httpx.Response(status, json=body, headers=headers)


def _sse_event(event: str, data: object) -> str:
    """One Anthropic-style SSE event: `event:` line + `data:` JSON line."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _sse_response(deltas: list[str], *, include_ping: bool = False) -> httpx.Response:
    """A realistic Anthropic SSE stream: message_start -> deltas -> stop."""
    lines = [
        _sse_event("message_start", {
            "type": "message_start",
            "message": {"id": "msg_test_001", "type": "message",
                        "role": "assistant", "usage": {"input_tokens": 5, "output_tokens": 1}},
        }),
    ]
    if include_ping:
        lines.append(_sse_event("ping", {"type": "ping"}))
    for d in deltas:
        lines.append(_sse_event("content_block_delta", {
            "type": "content_block_delta", "index": 0,
            "delta": {"type": "text_delta", "text": d},
        }))
    lines.append(_sse_event("message_stop", {"type": "message_stop"}))
    return httpx.Response(
        200, content="".join(lines).encode(), headers={"content-type": "text/event-stream"}
    )


def _sse_only_error(error_type: str, message: str) -> httpx.Response:
    lines = [
        _sse_event("message_start", {
            "type": "message_start",
            "message": {"id": "msg_test_001", "type": "message", "role": "assistant",
                        "usage": {"input_tokens": 1, "output_tokens": 0}},
        }),
        _sse_event("error", {"type": "error",
                             "error": {"type": error_type, "message": message}}),
    ]
    return httpx.Response(
        200, content="".join(lines).encode(), headers={"content-type": "text/event-stream"}
    )


# ── network isolation (AC-01 proof) ────────────────────────────────────────


@pytest.fixture(scope="module")
def client_log() -> list[dict[str, object]]:
    """Records every httpx.Client instantiation (transport / base_url).

    Module-scoped: the whole module's client creations are asserted in
    test_no_real_network_calls, so the log must survive across tests.
    """
    return []


@pytest.fixture(autouse=True)
def _network_guard(monkeypatch: pytest.MonkeyPatch, client_log: list[dict[str, object]]) -> None:
    """Block real TCP connections and prove only mocked transports are used.

    - http.client.HTTPConnection.connect and socket.create_connection raise
      AssertionError: any attempt to reach a real network fails the test.
    - httpx.Client (as seen by the anthropic driver) is wrapped: every
      instantiation is recorded; the final test asserts all of them were
      created with a transport (MockTransport).
    """
    def _block_http_connect(self: object, *args: object, **kwargs: object) -> None:
        raise AssertionError("REAL NETWORK ATTEMPT: http.client connection blocked (tests must use MockTransport)")

    def _block_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("REAL NETWORK ATTEMPT: socket.create_connection blocked (tests must use MockTransport)")

    monkeypatch.setattr(http.client.HTTPConnection, "connect", _block_http_connect)
    monkeypatch.setattr(socket, "create_connection", _block_socket)

    real_client = anthropic_driver.httpx.Client

    class _RecordingClient(real_client):  # type: ignore[misc, valid-type]
        def __init__(self, *args: object, **kwargs: object) -> None:
            client_log.append(
                {"transport": kwargs.get("transport"), "base_url": kwargs.get("base_url")}
            )
            super().__init__(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(anthropic_driver.httpx, "Client", _RecordingClient)
    yield


def _driver(
    handler: object,
    *,
    api_key: str = FAKE_KEY,
    retry_policy: RetryPolicy | None = None,
    sleep_fn: object = None,
    **kwargs: object,
) -> AnthropicMessagesDriver:
    return AnthropicMessagesDriver(
        api_key=api_key,
        base_url=BASE,
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        default_model="claude-test",
        retry_policy=retry_policy or RetryPolicy(max_attempts=3, jitter=0.0),
        sleep_fn=sleep_fn if sleep_fn is not None else (lambda _delay: None),  # deterministic: no real sleeping
        **kwargs,
    )


MSG = [{"role": "user", "content": "ping"}]

# ══════════════════════════════════════════════════════════════════════════
# AC-01a — complete() (headers / body / response parsing / usage)
# ══════════════════════════════════════════════════════════════════════════


def test_complete_returns_text_usage_and_anthropic_headers() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _messages_response("Hello from Anthropic!")

    driver = _driver(handler)
    result = driver.complete(MSG, operation="router")

    assert isinstance(result, CompletionResult)
    assert result.text == "Hello from Anthropic!"
    assert result.model == "claude-test"
    assert result.operation == "router"
    assert result.attempts == 1
    assert result.usage is not None
    assert result.usage.input_tokens == 5
    assert result.usage.output_tokens == 2
    assert result.usage.total_tokens == 7
    assert result.clamped is False

    # wire: POST {base_url}/v1/messages with the Anthropic auth header pair
    assert seen[0].method == "POST"
    assert seen[0].url.path.endswith("/v1/messages")
    assert seen[0].headers["x-api-key"] == FAKE_KEY
    assert seen[0].headers["anthropic-version"] == "2023-06-01"
    assert seen[0].headers["content-type"] == "application/json"

    # request body: model / max_tokens / messages / stream=False
    body = json.loads(seen[0].content)
    assert body["model"] == "claude-test"
    assert body["stream"] is False
    assert body["messages"] == MSG
    assert body["max_tokens"] == cap_for_operation("router")  # op-level cap
    assert "system" not in body


def test_complete_lifts_system_prompt_to_top_level_field() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _messages_response("ok")

    driver = _driver(handler)
    messages = [
        {"role": "system", "content": "You are a terse assistant."},
        {"role": "user", "content": "ping"},
        {"role": "assistant", "content": "pong"},
    ]
    result = driver.complete(messages, operation="router")
    assert result.text == "ok"

    body = json.loads(seen[0].content)
    assert body["system"] == "You are a terse assistant."
    # system prompts must NOT appear inside `messages` (Anthropic rejects them)
    assert body["messages"] == [
        {"role": "user", "content": "ping"},
        {"role": "assistant", "content": "pong"},
    ]


def test_complete_default_base_url_is_public_anthropic_endpoint() -> None:
    driver = AnthropicMessagesDriver(
        api_key=FAKE_KEY,
        transport=httpx.MockTransport(lambda r: _messages_response("x")),  # type: ignore[arg-type]
        default_model="claude-test",
    )
    assert driver.base_url == "https://api.anthropic.com"


def test_complete_multiple_text_blocks_are_joined() -> None:
    body = {
        "id": "msg_test_001", "type": "message", "role": "assistant",
        "model": "claude-test",
        "content": [
            {"type": "text", "text": "part one. "},
            {"type": "text", "text": "part two."},
            {"type": "tool_use", "id": "tool_1", "name": "x", "input": {}},  # skipped
        ],
        "usage": {"input_tokens": 5, "output_tokens": 2},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    driver = _driver(handler)
    assert driver.complete(MSG, operation="router").text == "part one. part two."


def test_protocol_driver_contract_is_satisfied() -> None:
    from loop_core.llm.protocol_driver import ProtocolDriver

    driver = _driver(lambda request: _messages_response("x"))
    # runtime_checkable Protocol: complete/stream/complete_json/cancel + name
    assert isinstance(driver, ProtocolDriver)
    assert driver.name == "anthropic-messages"
    assert callable(driver.complete)
    assert callable(driver.complete_json)
    assert callable(driver.stream)
    assert callable(driver.cancel)


# ══════════════════════════════════════════════════════════════════════════
# AC-01a/b — stream() (SSE event conversion, message_stop, error events)
# ══════════════════════════════════════════════════════════════════════════


def test_stream_yields_fragments_from_sse_events() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _sse_response(["Hel", "lo, ", "Anthropic!"], include_ping=True)

    driver = _driver(handler)
    fragments = list(driver.stream(MSG, operation="router"))

    assert fragments == ["Hel", "lo, ", "Anthropic!"]
    assert "".join(fragments) == "Hello, Anthropic!"
    body = json.loads(seen[0].content)
    assert body["stream"] is True
    assert body["max_tokens"] == cap_for_operation("router")


def test_stream_skips_ping_and_non_text_deltas() -> None:
    lines = [
        _sse_event("ping", {"type": "ping"}),
        _sse_event("content_block_start", {
            "type": "content_block_start", "index": 0,
            "content_block": {"type": "text", "text": ""},
        }),
        _sse_event("content_block_delta", {
            "type": "content_block_delta", "index": 0,
            "delta": {"type": "text_delta", "text": "A"},
        }),
        # non-text deltas (extended thinking / tool input) must be skipped
        _sse_event("content_block_delta", {
            "type": "content_block_delta", "index": 1,
            "delta": {"type": "thinking_delta", "thinking": "hmm"},
        }),
        _sse_event("content_block_delta", {
            "type": "content_block_delta", "index": 2,
            "delta": {"type": "input_json_delta", "partial_json": "{}"},
        }),
        _sse_event("content_block_delta", {
            "type": "content_block_delta", "index": 0,
            "delta": {"type": "text_delta", "text": None},
        }),
        _sse_event("message_delta", {"type": "message_delta",
                                     "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                                     "usage": {"output_tokens": 2}}),
        _sse_event("content_block_delta", {
            "type": "content_block_delta", "index": 0,
            "delta": {"type": "text_delta", "text": "B"},
        }),
        _sse_event("message_stop", {"type": "message_stop"}),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content="".join(lines).encode())

    driver = _driver(handler)
    assert list(driver.stream(MSG, operation="router")) == ["A", "B"]


def test_stream_error_event_maps_authentication_error() -> None:
    """SSE `error` event (authentication_error) -> MODEL_AUTHENTICATION_FAILED,
    raised immediately (not retryable), attempts == 1."""
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return _sse_only_error("authentication_error", "invalid x-api-key")

    driver = _driver(handler)
    with pytest.raises(LLMError) as excinfo:
        list(driver.stream(MSG, operation="router"))
    assert excinfo.value.code is ErrorCode.MODEL_AUTHENTICATION_FAILED
    assert excinfo.value.retryable is False
    assert excinfo.value.attempts == 1
    assert len(calls) == 1


def test_stream_error_event_overloaded_retried_then_succeeds() -> None:
    """SSE `error` event (overloaded_error -> SERVER_ERROR, retryable) is
    retried before the first delta, then the stream succeeds."""
    calls: list[int] = []
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return _sse_only_error("overloaded_error", "overloaded")
        return _sse_response(["a", "b"])

    driver = _driver(handler, sleep_fn=delays.append)
    assert list(driver.stream(MSG, operation="router")) == ["a", "b"]
    assert len(calls) == 2
    assert delays == [0.5]


# ══════════════════════════════════════════════════════════════════════════
# AC-01c — error mapping (HTTP status -> ErrorCode) + retryable behaviour
# ══════════════════════════════════════════════════════════════════════════


def test_401_auth_failed_never_retried() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return _error_response(401, "invalid x-api-key", error_type="authentication_error")

    driver = _driver(handler)
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.MODEL_AUTHENTICATION_FAILED
    assert excinfo.value.retryable is False
    assert len(calls) == 1  # no pointless retry on 401


def test_403_permission_denied_never_retried() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return _error_response(403, "forbidden", error_type="permission_error")

    driver = _driver(handler)
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="audit")
    assert excinfo.value.code is ErrorCode.PERMISSION_DENIED
    assert excinfo.value.retryable is False
    assert len(calls) == 1


def test_429_rate_limited_is_retried_then_succeeds() -> None:
    calls: list[int] = []
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return _error_response(429, "rate limited", error_type="rate_limit_error")
        return _messages_response("ok after 429")

    driver = _driver(
        handler,
        retry_policy=RetryPolicy(max_attempts=3, base_delay=0.5, jitter=0.0),
        sleep_fn=delays.append,
    )
    result = driver.complete(MSG, operation="router")
    assert result.text == "ok after 429"
    assert result.attempts == 2
    assert len(calls) == 2
    assert delays == [0.5]  # exponential backoff: base_delay for 1st retry


def test_500_server_error_retried_twice_then_succeeds() -> None:
    calls: list[int] = []
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) <= 2:
            return _error_response(500, "boom", error_type="api_error")
        return _messages_response("recovered")

    driver = _driver(
        handler,
        retry_policy=RetryPolicy(max_attempts=3, base_delay=0.5, jitter=0.0),
        sleep_fn=delays.append,
    )
    result = driver.complete(MSG, operation="router")
    assert result.text == "recovered"
    assert result.attempts == 3
    assert delays == [0.5, 1.0]  # backoff grows: base, base*2


def test_408_maps_to_timeout_and_is_retried() -> None:
    calls: list[int] = []
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return _error_response(408, "request timeout", error_type="timeout_error")
        return _messages_response("after 408")

    driver = _driver(handler, sleep_fn=delays.append)
    result = driver.complete(MSG, operation="router")
    assert result.text == "after 408"
    assert result.attempts == 2
    assert delays == [0.5]


def test_persistent_429_raises_rate_limited_with_attempts() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return _error_response(429, "still limited", error_type="rate_limit_error")

    driver = _driver(handler, retry_policy=RetryPolicy(max_attempts=3, jitter=0.0))
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.RATE_LIMITED
    assert excinfo.value.retryable is True
    assert excinfo.value.attempts == 3
    assert len(calls) == 3  # tried max_attempts times, then gave up


def test_404_model_not_found_never_retried() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _error_response(404, "model not found", error_type="not_found_error")

    driver = _driver(handler)
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.MODEL_NOT_FOUND
    assert excinfo.value.retryable is False
    assert excinfo.value.attempts == 1


def test_httpx_timeout_is_retried_then_succeeds() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ReadTimeout("read timed out", request=request)
        return _messages_response("after timeout")

    driver = _driver(handler)
    result = driver.complete(MSG, operation="router")
    assert result.text == "after timeout"
    assert result.attempts == 2
    assert len(calls) == 2


def test_persistent_timeout_raises_timeout_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("connect timed out", request=request)

    driver = _driver(handler)
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.TIMEOUT
    assert excinfo.value.retryable is True
    assert excinfo.value.attempts == 3


def test_connect_error_maps_to_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    driver = _driver(handler)
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.CONNECTION_ERROR
    assert excinfo.value.retryable is True


def test_non_json_provider_body_raises_invalid_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>not json</html>")

    driver = _driver(handler)
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.INVALID_RESPONSE
    assert excinfo.value.retryable is False


def test_error_response_captures_request_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _error_response(500, "boom", request_id="req_test_abc123")

    driver = _driver(handler, retry_policy=RetryPolicy(max_attempts=1, jitter=0.0))
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.status_code == 500
    assert excinfo.value.request_id == "req_test_abc123"


def test_messages_without_user_assistant_role_raise_configuration_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _messages_response("x")

    driver = _driver(handler)
    with pytest.raises(LLMError) as excinfo:
        driver.complete([{"role": "system", "content": "only system"}], operation="router")
    assert excinfo.value.code is ErrorCode.CONFIGURATION_ERROR
    assert excinfo.value.retryable is False


def test_driver_requires_model() -> None:
    driver = AnthropicMessagesDriver(
        api_key=FAKE_KEY,
        base_url=BASE,
        transport=httpx.MockTransport(lambda r: _messages_response("x")),  # type: ignore[arg-type]
    )
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.CONFIGURATION_ERROR


# ══════════════════════════════════════════════════════════════════════════
# AC-01d — empty-response retry + secret redaction
# ══════════════════════════════════════════════════════════════════════════


def test_empty_response_retried_with_bounded_budget() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return _messages_response("")  # empty text block
        return _messages_response("filled")

    driver = _driver(handler, retry_policy=RetryPolicy(max_attempts=5, empty_response_retries=2, jitter=0.0))
    result = driver.complete(MSG, operation="router")
    assert result.text == "filled"
    assert result.attempts == 2
    assert len(calls) == 2


def test_persistent_empty_response_raises_invalid_response() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return _messages_response("")

    # empty_response_retries=1 -> total 2 attempts before INVALID_RESPONSE
    driver = _driver(handler, retry_policy=RetryPolicy(max_attempts=5, empty_response_retries=1, jitter=0.0))
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.INVALID_RESPONSE
    assert excinfo.value.attempts == 2
    assert len(calls) == 2


def test_stream_empty_raises_invalid_response() -> None:
    # message_start + message_stop with zero deltas -> empty stream
    lines = [
        _sse_event("message_start", {
            "type": "message_start",
            "message": {"id": "msg_test_001", "type": "message", "role": "assistant",
                        "usage": {"input_tokens": 1, "output_tokens": 0}},
        }),
        _sse_event("message_stop", {"type": "message_stop"}),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content="".join(lines).encode())

    driver = _driver(handler, retry_policy=RetryPolicy(max_attempts=5, empty_response_retries=0, jitter=0.0))
    with pytest.raises(LLMError) as excinfo:
        list(driver.stream(MSG, operation="router"))
    assert excinfo.value.code is ErrorCode.INVALID_RESPONSE


def test_error_message_redacts_key_echoed_by_provider() -> None:
    """Worst case: the provider echoes the x-api-key header in its error
    body — the raised LLMError must still not contain the raw key."""
    def handler(request: httpx.Request) -> httpx.Response:
        echoed = request.headers.get("x-api-key", "")
        return _error_response(401, f"invalid key: {echoed}", error_type="authentication_error")

    driver = _driver(handler, api_key=FAKE_KEY)
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    message = str(excinfo.value)
    assert FAKE_KEY not in message
    assert "sk-" not in message
    assert "<REDACTED>" in message
    # serialized audit payload is clean too
    assert FAKE_KEY not in json.dumps(excinfo.value.to_dict())


def test_stream_error_message_redacts_key_echoed_by_provider() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        echoed = request.headers.get("x-api-key", "")
        return _sse_only_error("authentication_error", f"bad key {echoed}")

    driver = _driver(handler, api_key=FAKE_KEY)
    with pytest.raises(LLMError) as excinfo:
        list(driver.stream(MSG, operation="router"))
    message = str(excinfo.value)
    assert FAKE_KEY not in message
    assert "sk-" not in message
    assert "<REDACTED>" in message


# ══════════════════════════════════════════════════════════════════════════
# AC-01e — output clamping + cancel semantics
# ══════════════════════════════════════════════════════════════════════════


def test_complete_applies_request_cap_and_post_clamp() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _messages_response("y" * 9000)  # model overruns the cap

    driver = _driver(handler)
    result = driver.complete(MSG, operation="summarize")

    assert json.loads(seen[0].content)["max_tokens"] == 2000  # request-level cap
    assert result.clamped is True
    assert result.clamp_cap == 2000
    assert "clamped" in result.text


def test_explicit_max_tokens_overrides_operation_cap() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _messages_response("ok")

    driver = _driver(handler)
    result = driver.complete(MSG, operation="summarize", max_tokens=500)
    assert json.loads(seen[0].content)["max_tokens"] == 500
    assert result.clamped is False


def test_complete_json_repairs_dirty_anthropic_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _messages_response('{"router": "code-review", "confidence": 0.9,}')

    driver = _driver(handler)
    result = driver.complete_json(MSG, operation="router")
    assert isinstance(result, JSONResult)
    assert result.data == {"router": "code-review", "confidence": 0.9}
    assert result.repair_strategy == "trailing-commas"
    assert result.operation == "router"


def test_complete_json_unrepairable_raises_invalid_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _messages_response("I cannot produce JSON today {{{")

    driver = _driver(handler)
    with pytest.raises(LLMError) as excinfo:
        driver.complete_json(MSG, operation="audit")
    assert excinfo.value.code is ErrorCode.INVALID_RESPONSE
    assert excinfo.value.retryable is False


def test_cancel_raises_cancelled_then_one_shot_clears() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _messages_response("ok")

    driver = _driver(handler)
    driver.cancel()
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.CANCELLED
    assert excinfo.value.retryable is False
    # one-shot: next call proceeds normally
    assert driver.complete(MSG, operation="router").text == "ok"


def test_stream_cancel_midstream_raises_cancelled() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _sse_response(["1", "2", "3"])

    driver = _driver(handler)
    gen = driver.stream(MSG, operation="router")
    assert next(gen) == "1"
    driver.cancel()
    with pytest.raises(LLMError) as excinfo:
        next(gen)
    assert excinfo.value.code is ErrorCode.CANCELLED


def test_stream_retries_on_first_chunk_failure() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return _error_response(429, "slow down", error_type="rate_limit_error")
        return _sse_response(["a", "b"])

    driver = _driver(handler)
    assert list(driver.stream(MSG, operation="router")) == ["a", "b"]
    assert len(calls) == 2


# ══════════════════════════════════════════════════════════════════════════
# key resolution (env only, never hardcoded) + no real network proofs
# ══════════════════════════════════════════════════════════════════════════


def test_driver_without_env_key_raises_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from loop_core.llm.keys import KEY_ENV_VARS

    for var in KEY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    driver = AnthropicMessagesDriver(
        base_url=BASE,
        transport=httpx.MockTransport(lambda r: _messages_response("x")),  # type: ignore[arg-type]
        default_model="claude-test",
    )
    with pytest.raises(LLMKeyError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.KEY_MISSING


def test_no_hardcoded_credentials_in_llm_source() -> None:
    """The whole llm package (incl. the new anthropic driver) must contain no
    embedded secret-like literals."""
    pkg_dir = Path(__file__).resolve().parent.parent / "loop_core" / "llm"
    assert pkg_dir.is_dir()
    offenders: list[str] = []
    for path in sorted(pkg_dir.glob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if "sk-" in stripped and len(stripped) < 200 and not stripped.startswith("#"):
                offenders.append(f"{path.name}:{lineno}: {stripped}")
    assert not offenders, "hardcoded credential-like literals found:\n" + "\n".join(offenders)


def test_no_real_network_calls(client_log: list[dict[str, object]]) -> None:
    """Every httpx.Client created during this test module used a transport
    (MockTransport) — combined with the autouse socket/http.client guard,
    no request in this suite could have reached a real network.

    The test is self-sufficient: it exercises a full driver round trip
    (complete + stream) under the guard, then audits every recorded client
    instantiation (including the one it just created)."""
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body.get("stream"):
            return _sse_response(["self-sufficient"])
        return _messages_response("self-sufficient")

    driver = _driver(handler)
    assert driver.complete(MSG, operation="router").text == "self-sufficient"
    assert list(driver.stream(MSG, operation="router")) == ["self-sufficient"]

    assert client_log, "expected httpx.Client instantiations to be recorded"
    for entry in client_log:
        assert entry["transport"] is not None, (
            f"httpx.Client created WITHOUT a transport -> would use the real network: {entry}"
        )
        base = entry.get("base_url")
        assert isinstance(base, str) and base.startswith("https://"), base
