"""
T-0090 D5 — MCP stdio client tests (AC-02b / AC-02c, MCP part).

Full protocol flow against the LOCAL mock stdio server
(tests/mcp_mock_server.py): initialize -> notifications/initialized ->
tools/list -> tools/call. Plus error paths (MCP_TIMEOUT / MCP_ERROR /
MCP_CONNECTION_FAILED) and the no-network guarantee.

The mock server is a plain child process speaking JSON-RPC over pipes —
no sockets are involved. This file proves it by failing any socket use
during a complete session (test_no_sockets_opened).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

from loop_core.mcp_client import (
    DEFAULT_TIMEOUT_SECONDS,
    MCP_CONNECTION_FAILED,
    MCP_ERROR,
    MCP_PROTOCOL_VERSION,
    MCP_TIMEOUT,
    MCPSession,
    MCPSessionError,
)

PYTHON = sys.executable
MOCK_SERVER = Path(__file__).resolve().parent / "mcp_mock_server.py"


def _session(env_overrides: dict[str, str] | None = None, **session_kwargs) -> MCPSession:
    env = {"MOCK_SERVER_MODE": "", **(env_overrides or {})}
    return MCPSession(
        [PYTHON, str(MOCK_SERVER)],
        request_timeout=10.0,
        env={k: v for k, v in env.items() if v},
        **session_kwargs,
    )


# ── AC-02b: full protocol flow (local mock server) ──────────────────────

class TestHandshakeAndFlow:
    def test_initialize(self):
        session = _session()
        try:
            assert session.initialized is True
            assert session.server_info["name"] == "loop-engine-mock-server"
            assert session.server_protocol_version == MCP_PROTOCOL_VERSION
            assert session.alive is True
        finally:
            session.close()

    def test_initialized_notification_sent(self, tmp_path):
        """notifications/initialized must be sent after initialize."""
        record = tmp_path / "record.jsonl"
        session = _session(env_overrides={"MOCK_SERVER_RECORD": str(record)})
        try:
            session.list_tools()
        finally:
            session.close()
        methods = [json.loads(line)["method"]
                   for line in record.read_text(encoding="utf-8").splitlines()]
        assert "initialize" in methods
        assert "notifications/initialized" in methods
        # notification carries no id
        notify = next(json.loads(line) for line in
                      record.read_text(encoding="utf-8").splitlines()
                      if json.loads(line)["method"] == "notifications/initialized")
        assert notify["id"] is None

    def test_list_tools(self):
        session = _session()
        try:
            tools = session.list_tools()
            names = {t["name"] for t in tools}
            assert {"echo", "add", "fail_tool", "sleep_tool"} <= names
            echo = next(t for t in tools if t["name"] == "echo")
            assert echo["inputSchema"]["required"] == ["message"]
        finally:
            session.close()

    def test_call_tool_echo(self):
        session = _session()
        try:
            result = session.call_tool("echo", {"message": "hello-mcp"})
            text = result["content"][0]["text"]
            assert text == "hello-mcp"
        finally:
            session.close()

    def test_call_tool_add(self):
        session = _session()
        try:
            result = session.call_tool("add", {"a": 2, "b": 40})
            assert result["content"][0]["text"] == "42"
        finally:
            session.close()

    def test_call_tool_without_arguments(self):
        session = _session()
        try:
            result = session.call_tool("echo")
            assert result["content"][0]["text"] == ""
        finally:
            session.close()


# ── AC-02b: error paths ─────────────────────────────────────────────────

class TestErrorPaths:
    def test_call_tool_iserror_raises_mcp_error(self):
        session = _session()
        try:
            with pytest.raises(MCPSessionError) as exc:
                session.call_tool("fail_tool")
            assert exc.value.code == MCP_ERROR
            assert "isError" in exc.value.message
        finally:
            session.close()

    def test_unknown_tool_raises_mcp_error(self):
        session = _session()
        try:
            with pytest.raises(MCPSessionError) as exc:
                session.call_tool("no_such_tool")
            assert exc.value.code == MCP_ERROR
            assert "-32602" in exc.value.message
        finally:
            session.close()

    def test_request_timeout_raises_mcp_timeout(self):
        session = _session()
        try:
            with pytest.raises(MCPSessionError) as exc:
                session.call_tool("sleep_tool", {"seconds": 3},
                                  timeout_seconds=0.5)
            assert exc.value.code == MCP_TIMEOUT
            assert "timed out" in exc.value.message
        finally:
            session.close()

    def test_session_recoverable_after_timeout(self):
        """A timed-out request must not wedge the session."""
        session = _session()
        try:
            with pytest.raises(MCPSessionError):
                session.call_tool("sleep_tool", {"seconds": 2},
                                  timeout_seconds=0.5)
            result = session.call_tool("echo", {"message": "after-timeout"},
                                       timeout_seconds=5.0)
            assert result["content"][0]["text"] == "after-timeout"
        finally:
            session.close()

    def test_connection_failed_process_exits_at_spawn(self):
        with pytest.raises(MCPSessionError) as exc:
            _session(env_overrides={"MOCK_SERVER_MODE": "exit"})
        assert exc.value.code == MCP_CONNECTION_FAILED

    def test_connection_failed_garbage_stdout(self):
        """Non-JSON output then exit -> connection failure, not a hang."""
        with pytest.raises(MCPSessionError) as exc:
            _session(env_overrides={"MOCK_SERVER_MODE": "garbage"})
        assert exc.value.code == MCP_CONNECTION_FAILED

    def test_connection_failed_process_dies_mid_call(self):
        """Server exits right after initialize -> next call fails fast."""
        session = _session(env_overrides={"MOCK_SERVER_MODE": "exit_after_initialize"})
        try:
            assert session.initialized is True
            with pytest.raises(MCPSessionError) as exc:
                session.list_tools()
            assert exc.value.code == MCP_CONNECTION_FAILED
        finally:
            session.close()

    def test_spawn_failure_raises_connection_failed(self):
        with pytest.raises(MCPSessionError) as exc:
            MCPSession(["/definitely/not/a/real/binary"])
        assert exc.value.code == MCP_CONNECTION_FAILED

    def test_call_before_initialize_raises(self):
        session = _session(auto_initialize=False)
        try:
            assert session.initialized is False
            with pytest.raises(MCPSessionError) as exc:
                session.list_tools()
            assert exc.value.code == MCP_ERROR
            assert "not initialized" in exc.value.message
        finally:
            session.close()

    def test_use_after_close_raises(self):
        session = _session()
        session.close()
        with pytest.raises(MCPSessionError) as exc:
            session.call_tool("echo", {})
        assert exc.value.code == MCP_CONNECTION_FAILED

    def test_double_close_safe(self):
        session = _session()
        session.close()
        session.close()  # must not raise

    def test_context_manager_closes(self):
        with _session() as session:
            assert session.alive is True
        with pytest.raises(MCPSessionError):
            session.call_tool("echo", {})


# ── AC-02c: security — local only, no network ───────────────────────────

class TestNoNetwork:
    def test_no_sockets_opened_during_full_flow(self):
        """Complete initialize/list/call must never touch the network."""
        session = _session()
        try:
            with mock.patch("socket.socket",
                            side_effect=AssertionError("socket used!")):
                with mock.patch("socket.create_connection",
                                side_effect=AssertionError("socket used!")):
                    session.initialize()
                    tools = session.list_tools()
                    assert len(tools) >= 4
                    result = session.call_tool("add", {"a": 1, "b": 2})
                    assert result["content"][0]["text"] == "3"
        finally:
            session.close()

    def test_connection_is_local_subprocess_only(self):
        """The spawned server command must be the local python + mock file."""
        session = _session()
        try:
            assert session.command[0] == PYTHON
            assert Path(session.command[1]).resolve() == MOCK_SERVER.resolve()
        finally:
            session.close()

    def test_no_network_imports_in_client_source(self):
        src = Path(__file__).resolve().parent.parent / "loop_core" / "mcp_client.py"
        text = src.read_text(encoding="utf-8")
        for banned in ("import socket", "import urllib", "import http.client",
                       "import requests"):
            assert banned not in text, f"banned network import: {banned}"


def test_protocol_constants():
    assert MCP_PROTOCOL_VERSION == "2024-11-05"
    assert DEFAULT_TIMEOUT_SECONDS == 10.0
    assert os.environ.get("LLM_API_KEY") is None  # no credentials in env
