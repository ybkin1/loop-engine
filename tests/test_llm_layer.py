"""
T-0090 D1 — LLM access abstraction layer tests (AC-01a..f).

ALL tests are fully mocked:
- HTTP layer: httpx.MockTransport handlers (no real network — an autouse
  guard blocks http.client/socket connections and records every httpx.Client
  instantiation; test_no_real_network_calls asserts every client was created
  with a mock transport).
- Keys: fake keys injected via env mapping / monkeypatch.setenv, or passed
  explicitly to the driver (never real credentials).

AC mapping:
  AC-01a test_driver_complete / test_driver_stream / protocol contract
  AC-01b error codes + retryable flags + retry behaviour (429/500/timeout)
  AC-01c JSON repair (multi-candidate + unrepairable -> INVALID_RESPONSE)
  AC-01d redaction (keys/tokens never in error messages)
  AC-01e operation-level output token clamping
  AC-01f key resolution from environment (missing -> explicit error)
"""
from __future__ import annotations

import http.client
import json
import re
import socket
from pathlib import Path

import httpx
import pytest

import loop_core.llm.openai_driver as openai_driver
from loop_core.llm import (
    CompletionResult,
    ErrorCode,
    JSONResult,
    LLMError,
    LLMKeyError,
    OpenAICompatibleDriver,
    Redactor,
    cap_for_operation,
    clamp_output,
    make_redactor,
    repair_json,
    resolve_api_key,
)
from loop_core.llm.errors import JSONRepairError
from loop_core.llm.retry import RetryPolicy

FAKE_KEY = "sk-test-0123456789abcdef"  # fake test-only key (never a real secret)
FAKE_KEY2 = "sk-test-abcdef0123456789"
BASE = "https://llm.test.invalid/v1"  # .invalid TLD — never resolvable

# ── shared mock handlers ───────────────────────────────────────────────────


def _chat_response(content: str, model: str = "m-test", **extra: object) -> httpx.Response:
    body: dict[str, object] = {
        "id": "cmpl-test",
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }
    body.update(extra)
    return httpx.Response(200, json=body)


def _error_response(status: int, message: str) -> httpx.Response:
    return httpx.Response(status, json={"error": {"message": message}})


def _sse_response(deltas: list[str]) -> httpx.Response:
    lines = [
        f'data: {{"choices": [{{"delta": {{"content": {json.dumps(d)}}}}}]}}\n\n'
        for d in deltas
    ]
    lines.append("data: [DONE]\n\n")
    return httpx.Response(
        200, content="".join(lines).encode(), headers={"content-type": "text/event-stream"}
    )


# ── network isolation (AC-01 / AC-06 proof) ────────────────────────────────


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
    - httpx.Client is wrapped: every instantiation is recorded; the final
      test asserts all of them were created with a transport (MockTransport).
    """
    def _block_http_connect(self: object, *args: object, **kwargs: object) -> None:
        raise AssertionError("REAL NETWORK ATTEMPT: http.client connection blocked (tests must use MockTransport)")

    def _block_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("REAL NETWORK ATTEMPT: socket.create_connection blocked (tests must use MockTransport)")

    monkeypatch.setattr(http.client.HTTPConnection, "connect", _block_http_connect)
    monkeypatch.setattr(socket, "create_connection", _block_socket)

    real_client = openai_driver.httpx.Client

    class _RecordingClient(real_client):  # type: ignore[misc, valid-type]
        def __init__(self, *args: object, **kwargs: object) -> None:
            client_log.append(
                {"transport": kwargs.get("transport"), "base_url": kwargs.get("base_url")}
            )
            super().__init__(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(openai_driver.httpx, "Client", _RecordingClient)
    yield


@pytest.fixture()
def no_env_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every LLM key env var so tests start from a clean slate."""
    from loop_core.llm.keys import KEY_ENV_VARS

    for var in KEY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("LLM_REDACT_SECRETS", raising=False)


def _driver(
    handler: object,
    *,
    api_key: str = FAKE_KEY,
    retry_policy: RetryPolicy | None = None,
    sleep_fn: object = None,
    **kwargs: object,
) -> OpenAICompatibleDriver:
    return OpenAICompatibleDriver(
        api_key=api_key,
        base_url=BASE,
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        default_model="m-test",
        retry_policy=retry_policy or RetryPolicy(max_attempts=3, jitter=0.0),
        sleep_fn=sleep_fn if sleep_fn is not None else (lambda _delay: None),  # deterministic: no real sleeping
        **kwargs,
    )


MSG = [{"role": "user", "content": "ping"}]

# ══════════════════════════════════════════════════════════════════════════
# AC-01a — protocol driver interface (complete / stream)
# ══════════════════════════════════════════════════════════════════════════


def test_driver_complete_returns_text_and_metadata() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _chat_response("Hello, loop-engine!")

    driver = _driver(handler)
    result = driver.complete(MSG, operation="router")

    assert isinstance(result, CompletionResult)
    assert result.text == "Hello, loop-engine!"
    assert result.model == "m-test"
    assert result.operation == "router"
    assert result.attempts == 1
    assert result.usage is not None and result.usage.total_tokens == 7
    assert result.clamped is False

    # request shape: OpenAI-compatible chat completions
    body = json.loads(seen[0].content)
    assert body["model"] == "m-test"
    assert body["stream"] is False
    assert body["messages"] == MSG
    assert body["max_tokens"] == cap_for_operation("router")  # op-level cap
    assert seen[0].url.path.endswith("/chat/completions")
    assert seen[0].headers["authorization"] == f"Bearer {FAKE_KEY}"
    assert "sk-test" in seen[0].headers["authorization"]  # sent to mock only


def test_driver_stream_yields_fragments() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _sse_response(["Hel", "lo, ", "str", "eam!"])

    driver = _driver(handler)
    fragments = list(driver.stream(MSG, operation="router"))

    assert fragments == ["Hel", "lo, ", "str", "eam!"]
    assert "".join(fragments) == "Hello, stream!"
    body = json.loads(seen[0].content)
    assert body["stream"] is True
    assert body["max_tokens"] == cap_for_operation("router")


def test_driver_stream_skips_keepalive_and_null_deltas() -> None:
    lines = [
        ": keep-alive comment\n\n",
        'data: {"choices": [{"delta": {"content": "A"}}]}\n\n',
        'data: {"choices": [{"delta": {}}]}\n\n',
        'data: {"choices": [{"delta": {"content": null}}]}\n\n',
        'data: {"choices": [{"delta": {"content": "B"}}]}\n\n',
        "data: [DONE]\n\n",
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content="".join(lines).encode())

    driver = _driver(handler)
    assert list(driver.stream(MSG, operation="router")) == ["A", "B"]


def test_protocol_driver_contract_is_satisfied() -> None:
    from loop_core.llm.protocol_driver import ProtocolDriver

    driver = _driver(lambda request: _chat_response("x"))
    # runtime_checkable Protocol: complete/stream/complete_json/cancel + name
    assert isinstance(driver, ProtocolDriver)
    assert driver.name == "openai-compatible"
    assert callable(driver.complete)
    assert callable(driver.complete_json)
    assert callable(driver.stream)
    assert callable(driver.cancel)


# ══════════════════════════════════════════════════════════════════════════
# AC-01b — unified error codes + retryable flags + retry behaviour
# ══════════════════════════════════════════════════════════════════════════

REQUIRED_ERROR_CODES = {
    "MODEL_AUTHENTICATION_FAILED",
    "PERMISSION_DENIED",
    "RATE_LIMITED",
    "TIMEOUT",
    "CANCELLED",
    "INVALID_RESPONSE",
}


def test_error_code_family_required_codes_and_retryable_flags() -> None:
    members = {code.value for code in ErrorCode}
    assert REQUIRED_ERROR_CODES <= members, f"missing required codes: {REQUIRED_ERROR_CODES - members}"

    retryable = {ErrorCode.RATE_LIMITED, ErrorCode.TIMEOUT, ErrorCode.SERVER_ERROR, ErrorCode.CONNECTION_ERROR}
    not_retryable = {
        ErrorCode.MODEL_AUTHENTICATION_FAILED,
        ErrorCode.PERMISSION_DENIED,
        ErrorCode.MODEL_NOT_FOUND,
        ErrorCode.KEY_MISSING,
        ErrorCode.CONFIGURATION_ERROR,
        ErrorCode.CANCELLED,
        ErrorCode.INVALID_RESPONSE,
    }
    for code in retryable:
        assert code.retryable is True, code
    for code in not_retryable:
        assert code.retryable is False, code

    # HTTP mapping sanity
    assert ErrorCode.MODEL_AUTHENTICATION_FAILED.http_status == 401
    assert ErrorCode.RATE_LIMITED.http_status == 429
    assert ErrorCode.SERVER_ERROR.http_status == 500


def test_llm_error_carries_code_retryable_and_serializes() -> None:
    err = LLMError(ErrorCode.RATE_LIMITED, "slow down", operation="router", attempts=2, status_code=429)
    assert err.code is ErrorCode.RATE_LIMITED
    assert err.retryable is True
    assert err.attempts == 2
    d = err.to_dict()
    assert d["error_code"] == "RATE_LIMITED"
    assert d["retryable"] is True
    assert d["operation"] == "router"


def test_429_rate_limited_is_retried_then_succeeds() -> None:
    calls: list[int] = []
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return _error_response(429, "rate limited")
        return _chat_response("ok after 429")

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
            return _error_response(500, "boom")
        return _chat_response("recovered")

    driver = _driver(
        handler,
        retry_policy=RetryPolicy(max_attempts=3, base_delay=0.5, jitter=0.0),
        sleep_fn=delays.append,
    )
    result = driver.complete(MSG, operation="router")
    assert result.text == "recovered"
    assert result.attempts == 3
    assert delays == [0.5, 1.0]  # backoff grows: base, base*2


def test_backoff_delays_grow_exponentially() -> None:
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return _error_response(503, "unavailable")

    driver = _driver(
        handler,
        retry_policy=RetryPolicy(max_attempts=4, base_delay=0.5, jitter=0.0),
        sleep_fn=delays.append,
    )
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.SERVER_ERROR
    assert excinfo.value.retryable is True
    assert excinfo.value.attempts == 4
    assert delays == [0.5, 1.0, 2.0]  # 0.5 * 2^0, *2^1, *2^2 (capped at max_delay)


def test_persistent_429_raises_rate_limited_with_attempts() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return _error_response(429, "still limited")

    driver = _driver(handler, retry_policy=RetryPolicy(max_attempts=3, jitter=0.0))
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.RATE_LIMITED
    assert excinfo.value.retryable is True
    assert excinfo.value.attempts == 3
    assert len(calls) == 3  # tried max_attempts times, then gave up


def test_401_auth_failed_never_retried() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return _error_response(401, "invalid api key")

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
        return _error_response(403, "forbidden")

    driver = _driver(handler)
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="audit")
    assert excinfo.value.code is ErrorCode.PERMISSION_DENIED
    assert excinfo.value.retryable is False
    assert len(calls) == 1


def test_404_model_not_found_never_retried() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _error_response(404, "model not found")

    driver = _driver(handler)
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.MODEL_NOT_FOUND
    assert excinfo.value.retryable is False
    assert excinfo.value.attempts == 1


def test_timeout_is_retried_then_succeeds() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ReadTimeout("read timed out", request=request)
        return _chat_response("after timeout")

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


def test_empty_response_retried_with_bounded_budget() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return _chat_response("")  # empty content
        return _chat_response("filled")

    driver = _driver(handler, retry_policy=RetryPolicy(max_attempts=5, empty_response_retries=2, jitter=0.0))
    result = driver.complete(MSG, operation="router")
    assert result.text == "filled"
    assert result.attempts == 2
    assert len(calls) == 2


def test_persistent_empty_response_raises_invalid_response() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return _chat_response("")

    # empty_response_retries=1 -> total 2 attempts before INVALID_RESPONSE
    driver = _driver(handler, retry_policy=RetryPolicy(max_attempts=5, empty_response_retries=1, jitter=0.0))
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.INVALID_RESPONSE
    assert excinfo.value.attempts == 2
    assert len(calls) == 2


def test_cancel_raises_cancelled_then_one_shot_clears() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _chat_response("ok")

    driver = _driver(handler)
    driver.cancel()
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.CANCELLED
    assert excinfo.value.retryable is False
    # one-shot: next call proceeds normally
    assert driver.complete(MSG, operation="router").text == "ok"


def test_stream_retries_on_first_chunk_failure() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return _error_response(429, "slow down")
        return _sse_response(["a", "b"])

    driver = _driver(handler)
    assert list(driver.stream(MSG, operation="router")) == ["a", "b"]
    assert len(calls) == 2


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


def test_stream_empty_raises_invalid_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"data: [DONE]\n\n")

    driver = _driver(handler, retry_policy=RetryPolicy(max_attempts=5, empty_response_retries=0, jitter=0.0))
    with pytest.raises(LLMError) as excinfo:
        list(driver.stream(MSG, operation="router"))
    assert excinfo.value.code is ErrorCode.INVALID_RESPONSE


# ══════════════════════════════════════════════════════════════════════════
# AC-01c — JSON repair (multi-candidate + INVALID_RESPONSE on failure)
# ══════════════════════════════════════════════════════════════════════════


def test_repair_json_valid_input_identity() -> None:
    data, strategy = repair_json('{"a": 1, "b": [true, null]}')
    assert data == {"a": 1, "b": [True, None]}
    assert strategy == "identity"


def test_repair_json_trailing_comma() -> None:
    data, strategy = repair_json('{"a": 1, "b": 2,}')
    assert data == {"a": 1, "b": 2}
    assert strategy == "trailing-commas"


def test_repair_json_unescaped_quotes() -> None:
    data, strategy = repair_json('{"a": "he said "hi" ok"}')
    assert data == {"a": 'he said "hi" ok'}
    assert strategy == "unescaped-quotes"


def test_repair_json_extracts_balanced_block_from_prose() -> None:
    data, strategy = repair_json('Sure! Here is the JSON:\n```json\n{"a": 1}\n```\nHope it helps')
    assert data == {"a": 1}
    assert strategy in {"extract-block", "trim-fences", "extract+trailing-commas", "combo"}


def test_repair_json_control_chars_escaped() -> None:
    data, strategy = repair_json('{"a": "line1\nline2\tend"}')
    assert data == {"a": "line1\nline2\tend"}
    assert strategy == "control-chars"


def test_repair_json_unquoted_keys() -> None:
    data, strategy = repair_json("{a: 1, b: {c: 2}}")
    assert data == {"a": 1, "b": {"c": 2}}
    assert strategy in {"unquoted-keys", "combo"}


def test_repair_json_unrepairable_raises_with_strategies() -> None:
    with pytest.raises(JSONRepairError) as excinfo:
        repair_json("this is not json at all {{{", context="audit")
    assert excinfo.value.strategies_tried
    assert "audit" in str(excinfo.value)


def test_complete_json_end_to_end_repairs_dirty_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _chat_response('{"router": "code-review", "confidence": 0.9,}')

    driver = _driver(handler)
    result = driver.complete_json(MSG, operation="router")
    assert isinstance(result, JSONResult)
    assert result.data == {"router": "code-review", "confidence": 0.9}
    assert result.repair_strategy == "trailing-commas"
    assert result.operation == "router"


def test_complete_json_unrepairable_raises_llm_error_invalid_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _chat_response("I cannot produce JSON today {{{")

    driver = _driver(handler)
    with pytest.raises(LLMError) as excinfo:
        driver.complete_json(MSG, operation="audit")
    assert excinfo.value.code is ErrorCode.INVALID_RESPONSE
    assert excinfo.value.retryable is False


# ══════════════════════════════════════════════════════════════════════════
# AC-01d — secret redaction (keys/tokens never in errors or logs)
# ══════════════════════════════════════════════════════════════════════════


def test_redactor_replaces_known_secrets() -> None:
    redactor = make_redactor(FAKE_KEY)
    text = f"auth failed for key {FAKE_KEY} and token {FAKE_KEY}"
    out = redactor.redact(text)
    assert FAKE_KEY not in out
    assert out.count("<REDACTED>") == 2


def test_error_message_redacts_key_echoed_by_provider() -> None:
    """Worst case: the provider echoes the Authorization header in its error
    body — the raised LLMError must still not contain the raw key."""
    def handler(request: httpx.Request) -> httpx.Response:
        echoed = request.headers.get("authorization", "")
        return _error_response(401, f"invalid key: {echoed}")

    driver = _driver(handler, api_key=FAKE_KEY)
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    message = str(excinfo.value)
    assert FAKE_KEY not in message
    assert "sk-" not in message
    assert "<REDACTED>" in message
    # serialized audit payload is clean too
    assert FAKE_KEY not in json.dumps(excinfo.value.to_dict())


def test_safe_fragment_truncates_and_redacts() -> None:
    redactor = make_redactor(FAKE_KEY)
    long_body = f"prefix {FAKE_KEY} " + "y" * 5000
    fragment = redactor.safe_fragment(long_body, max_len=200)
    assert len(fragment) <= 202
    assert fragment.endswith("…")
    assert FAKE_KEY not in fragment


def test_redact_url_and_headers() -> None:
    redactor = make_redactor()
    url = "https://user:pass@llm.example/v1/chat?api_key=abc123&model=gpt&token=xyz"
    cleaned = redactor.redact_url(url)
    assert "pass" not in cleaned and "abc123" not in cleaned and "xyz" not in cleaned
    assert "model=gpt" in cleaned  # non-secret params preserved

    headers = redactor.redact_headers(
        {"Authorization": "Bearer sk-real", "x-api-key": "k123", "content-type": "application/json"}
    )
    assert headers["Authorization"] == "<REDACTED>"
    assert headers["x-api-key"] == "<REDACTED>"
    assert headers["content-type"] == "application/json"


def test_redaction_rejects_too_short_secrets() -> None:
    redactor = Redactor(["abc"])  # shorter than _MIN_SECRET_LEN
    assert redactor.secret_count == 0
    assert redactor.redact("value abc value") == "value abc value"


# ══════════════════════════════════════════════════════════════════════════
# AC-01e — operation-level output token clamping
# ══════════════════════════════════════════════════════════════════════════


def test_cap_for_operation_table() -> None:
    assert cap_for_operation("router") == 4000
    assert cap_for_operation("audit") == 8000
    assert cap_for_operation("self-review") == 6000
    assert cap_for_operation("summarize") == 2000
    assert cap_for_operation("unknown-op") == 4000  # default cap


def test_clamp_output_under_cap_unchanged() -> None:
    result = clamp_output("short text", "summarize")
    assert result.clamped is False
    assert result.text == "short text"
    assert result.cap_tokens == 2000


def test_clamp_output_over_cap_truncated_with_marker() -> None:
    big = "x" * 9000  # ~2250 tokens at 4 chars/token > 2000 cap
    result = clamp_output(big, "summarize")
    assert result.clamped is True
    assert result.cap_tokens == 2000
    assert result.approx_tokens == 2250
    assert len(result.text) <= 2000 * 4 + 100  # cap chars + clamp marker
    assert "clamped" in result.text
    assert result.text.startswith("x" * (2000 * 4))


def test_complete_applies_request_cap_and_post_clamp() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _chat_response("y" * 9000)  # model overruns the cap

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
        return _chat_response("ok")

    driver = _driver(handler)
    result = driver.complete(MSG, operation="summarize", max_tokens=500)
    assert json.loads(seen[0].content)["max_tokens"] == 500
    assert result.clamped is False


def test_complete_json_not_text_clamped_keeps_structure() -> None:
    """JSON results are NOT post-clamped (would corrupt structure); the
    request-level cap still applies."""
    seen: list[httpx.Request] = []
    payload = '{"data": "' + "z" * 8800 + '"}'

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _chat_response(payload)

    driver = _driver(handler)
    result = driver.complete_json(MSG, operation="summarize")
    assert json.loads(seen[0].content)["max_tokens"] == 2000
    assert len(result.data["data"]) == 8800  # intact, parseable JSON


# ══════════════════════════════════════════════════════════════════════════
# AC-01f — key resolution from environment (no hardcoded keys)
# ══════════════════════════════════════════════════════════════════════════


def test_resolve_api_key_missing_raises_explicit_error(no_env_keys: None) -> None:
    with pytest.raises(LLMKeyError) as excinfo:
        resolve_api_key()
    assert excinfo.value.code is ErrorCode.KEY_MISSING
    assert excinfo.value.retryable is False
    assert "LLM_API_KEY" in str(excinfo.value)
    assert "environment" in str(excinfo.value)


def test_resolve_api_key_env_mapping_priority(no_env_keys: None) -> None:
    env = {"LLM_API_KEY": "sk-llm-1", "DEEPSEEK_API_KEY": "sk-deep-1"}
    assert resolve_api_key(env) == "sk-llm-1"  # LLM_API_KEY wins


def test_resolve_api_key_deepseek_fallback(no_env_keys: None) -> None:
    env = {"DEEPSEEK_API_KEY": "sk-deep-1"}
    assert resolve_api_key(env) == "sk-deep-1"


def test_resolve_api_key_skips_empty_values(no_env_keys: None) -> None:
    env = {"LLM_API_KEY": "   ", "OPENAI_API_KEY": "sk-open-1"}
    assert resolve_api_key(env) == "sk-open-1"


def test_driver_resolves_key_from_environment(no_env_keys: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", FAKE_KEY)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == f"Bearer {FAKE_KEY}"
        return _chat_response("env key worked")

    driver = OpenAICompatibleDriver(
        base_url=BASE,
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        default_model="m-test",
        sleep_fn=lambda _d: None,
    )
    assert driver.complete(MSG, operation="router").text == "env key worked"


def test_driver_without_env_key_raises_key_missing(no_env_keys: None) -> None:
    driver = OpenAICompatibleDriver(
        base_url=BASE,
        transport=httpx.MockTransport(lambda r: _chat_response("x")),  # type: ignore[arg-type]
        default_model="m-test",
    )
    with pytest.raises(LLMKeyError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.KEY_MISSING


def test_driver_requires_model(no_env_keys: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", FAKE_KEY)
    driver = OpenAICompatibleDriver(
        base_url=BASE,
        transport=httpx.MockTransport(lambda r: _chat_response("x")),  # type: ignore[arg-type]
    )
    with pytest.raises(LLMError) as excinfo:
        driver.complete(MSG, operation="router")
    assert excinfo.value.code is ErrorCode.CONFIGURATION_ERROR


# ══════════════════════════════════════════════════════════════════════════
# no hardcoded credentials + no real network (AC-01 / AC-06 proofs)
# ══════════════════════════════════════════════════════════════════════════


def test_no_hardcoded_credentials_in_llm_source() -> None:
    """The whole llm package must contain no embedded secret-like literals."""
    pkg_dir = Path(__file__).resolve().parent.parent / "loop_core" / "llm"
    assert pkg_dir.is_dir()
    offenders: list[str] = []
    for path in sorted(pkg_dir.glob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if "sk-" in stripped and len(stripped) < 200 and not stripped.startswith("#"):
                offenders.append(f"{path.name}:{lineno}: {stripped}")
            if "api_key" in stripped and re_quoted_literal(stripped):
                offenders.append(f"{path.name}:{lineno}: {stripped}")
    assert not offenders, "hardcoded credential-like literals found:\n" + "\n".join(offenders)


def re_quoted_literal(line: str) -> bool:
    """True if the line assigns a quoted non-empty literal to api_key."""
    return bool(re.search(r'api_key\s*=\s*["\'][^"\']+["\']', line))


def test_no_real_network_calls(client_log: list[dict[str, object]]) -> None:
    """Every httpx.Client created during this test module used a transport
    (MockTransport) — combined with the autouse socket/http.client guard,
    no request in this suite could have reached a real network.

    The test is self-sufficient: it exercises a full driver round trip
    (complete + stream) under the guard, then audits every recorded client
    instantiation (including the one it just created)."""
    # exercise the driver so at least one client is instantiated here
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body.get("stream"):
            return _sse_response(["self-sufficient"])
        return _chat_response("self-sufficient")

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


# ══════════════════════════════════════════════════════════════════════
# T-0095 item 4: env 链统一（keys.py 与 zcode_config.ENV_TIERS 次序一致）
# ══════════════════════════════════════════════════════════════════════


def test_resolve_api_base_url_paired_with_winning_tier(no_env_keys: None) -> None:
    """base_url 与胜出 tier 成对解析（LLM_* → ANTHROPIC_* → OPENAI_* → ZCODE_*）。"""
    from loop_core.llm.keys import resolve_api_base_url

    env = {
        "LLM_API_KEY": "sk-llm-1", "LLM_BASE_URL": "https://llm.example.invalid/v1",
        "ANTHROPIC_API_KEY": "sk-ant-1", "ANTHROPIC_BASE_URL": "https://ant.example.invalid/v1",
    }
    assert resolve_api_base_url(env) == "https://llm.example.invalid/v1"

    env2 = {"ANTHROPIC_API_KEY": "sk-ant-1",
            "ANTHROPIC_BASE_URL": "https://ant.example.invalid/v1",
            "OPENAI_API_KEY": "sk-open-1"}
    assert resolve_api_base_url(env2) == "https://ant.example.invalid/v1"

    env3 = {"ZCODE_API_KEY": "sk-zc-1", "ZCODE_BASE_URL": "https://zc.example.invalid/v1"}
    assert resolve_api_base_url(env3) == "https://zc.example.invalid/v1"


def test_resolve_api_base_url_empty_when_unset_or_no_key(no_env_keys: None) -> None:
    from loop_core.llm.keys import resolve_api_base_url

    # key set, base url unset -> "" (provider default endpoint is legal)
    assert resolve_api_base_url({"OPENAI_API_KEY": "sk-open-1"}) == ""
    # no key at all -> "" (the key resolver raises; base url stays optional)
    assert resolve_api_base_url({}) == ""


def test_unified_key_chain_priority_anthropic_over_openai(no_env_keys: None) -> None:
    """统一优先序 LLM → ANTHROPIC → OPENAI → ZCODE（+ DEEPSEEK 别名殿后）。"""
    from loop_core.llm.keys import KEY_ENV_VARS, resolve_api_key

    env = {
        "ANTHROPIC_API_KEY": "sk-ant-1",
        "OPENAI_API_KEY": "sk-open-1",
        "ZCODE_API_KEY": "sk-zc-1",
        "DEEPSEEK_API_KEY": "sk-deep-1",
    }
    assert resolve_api_key(env) == "sk-ant-1"  # ANTHROPIC 高于 OPENAI/ZCODE/DEEPSEEK
    assert list(KEY_ENV_VARS) == [
        "LLM_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
        "ZCODE_API_KEY", "DEEPSEEK_API_KEY",
    ]


def test_keys_tiers_are_single_source_for_zcode_config(no_env_keys: None) -> None:
    """ENV_TIERS 必须与 keys.py 的规范表完全一致（同一对象，杜绝漂移）。"""
    from loop_core.llm.keys import KEY_TIERS
    from loop_core.llm.zcode_config import ENV_TIERS

    assert ENV_TIERS is KEY_TIERS
    for (key_var, base_var, proto), (k2, b2, p2) in zip(ENV_TIERS, KEY_TIERS):
        assert (key_var, base_var, proto) == (k2, b2, p2)
