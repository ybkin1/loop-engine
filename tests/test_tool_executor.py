"""
T-0090 D5 — tool executor tests (AC-02a / AC-02c, executor part).

Covers the fail-closed pipeline: existence -> enabled -> whitelist -> type ->
timeout -> execution -> result, with the unified error codes
NOT_FOUND / DISABLED / NOT_ALLOWED / TIMEOUT / EXECUTION_ERROR /
UNSUPPORTED_TYPE, plus security guarantees: whitelist refusal, timeout kill
fallback, and output truncation.

All local: local commands are sys.executable -c snippets; the MCP backend is
exercised against the local mock stdio server (tests/mcp_mock_server.py).
No external network, no credentials.
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import pytest

from loop_core.mcp_client import MCPSession
from loop_core.tool_executor import (
    ErrorCode,
    ExecutionType,
    ToolExecutionError,
    ToolExecutor,
    ToolSpec,
    build_argv,
    truncate_output,
)

PYTHON = sys.executable
MOCK_SERVER = Path(__file__).resolve().parent / "mcp_mock_server.py"


# ── helpers ─────────────────────────────────────────────────────────────

def _echo_spec(tool_id: str = "echo_tool", **overrides) -> ToolSpec:
    spec = ToolSpec(
        tool_id=tool_id,
        name="echo",
        description="echo test",
        execution_type=ExecutionType.LOCAL_COMMAND,
        timeout_seconds=10.0,
        command=[PYTHON, "-c", "import sys; print(sys.argv[1])", "hello"],
    )
    for key, value in overrides.items():
        setattr(spec, key, value)
    return spec


def _start_mcp_session(**env_overrides) -> MCPSession:
    env = {"MOCK_SERVER_MODE": "", **env_overrides}
    return MCPSession(
        [PYTHON, str(MOCK_SERVER)],
        request_timeout=10.0,
        env={k: v for k, v in env.items() if v},
    )


# ── AC-02a: pipeline and error codes ────────────────────────────────────

class TestPipelineErrorCodes:
    def test_not_found(self):
        executor = ToolExecutor()
        result = executor.execute("ghost_tool", {})
        assert result.ok is False
        assert result.code == ErrorCode.NOT_FOUND.value
        assert "ghost_tool" in result.error

    def test_disabled(self):
        executor = ToolExecutor()
        executor.register(_echo_spec("disabled_tool", enabled=False))
        result = executor.execute("disabled_tool", {})
        assert result.ok is False
        assert result.code == ErrorCode.DISABLED.value

    def test_not_allowed_executor_whitelist(self):
        """Executor whitelist configured -> unlisted tool refused (AC-02c)."""
        executor = ToolExecutor(allowed_tool_ids={"allowed_tool"})
        executor.register(_echo_spec("other_tool"))
        result = executor.execute("other_tool", {})
        assert result.ok is False
        assert result.code == ErrorCode.NOT_ALLOWED.value
        assert "whitelist" in result.error

    def test_not_allowed_spec_whitelist(self):
        """Spec-level allowed_tool_ids: spec not listing its own id -> refuse."""
        executor = ToolExecutor()
        executor.register(_echo_spec("spec_tool", allowed_tool_ids={"other_id"}))
        result = executor.execute("spec_tool", {})
        assert result.ok is False
        assert result.code == ErrorCode.NOT_ALLOWED.value
        assert "allowed_tool_ids" in result.error

    def test_allowed_spec_whitelist_passes(self):
        executor = ToolExecutor()
        executor.register(_echo_spec("spec_tool", allowed_tool_ids={"spec_tool"}))
        result = executor.execute("spec_tool", {})
        assert result.ok is True
        assert result.code == ErrorCode.OK.value

    def test_not_allowed_allowed_skills(self):
        """allowed_skills style: skill_id not in the skill set -> refuse."""
        executor = ToolExecutor()
        executor.register(_echo_spec(
            "skill_tool", skill_id="python", allowed_skills={"shell"},
        ))
        result = executor.execute("skill_tool", {})
        assert result.ok is False
        assert result.code == ErrorCode.NOT_ALLOWED.value
        assert "allowed_skills" in result.error

    def test_allowed_skills_passes(self):
        executor = ToolExecutor()
        executor.register(_echo_spec(
            "skill_tool", skill_id="shell", allowed_skills={"shell", "python"},
        ))
        result = executor.execute("skill_tool", {})
        assert result.ok is True

    def test_unsupported_type(self):
        executor = ToolExecutor()
        executor.register(ToolSpec(
            tool_id="http_tool", execution_type=ExecutionType.HTTP,
            http_url="http://127.0.0.1:9/never",
        ))
        result = executor.execute("http_tool", {})
        assert result.ok is False
        assert result.code == ErrorCode.UNSUPPORTED_TYPE.value

    def test_unknown_execution_type_enum_rejected(self):
        with pytest.raises(ValueError):
            ToolSpec(tool_id="x", execution_type="telepathy")

    def test_duplicate_registration_raises(self):
        executor = ToolExecutor()
        executor.register(_echo_spec("dup"))
        with pytest.raises(ValueError, match="already registered"):
            executor.register(_echo_spec("dup"))


class TestLocalCommand:
    def test_success(self):
        executor = ToolExecutor()
        executor.register(_echo_spec())
        result = executor.execute("echo_tool", {})
        assert result.ok is True
        assert result.code == ErrorCode.OK.value
        assert "hello" in result.output
        assert result.error == ""
        assert result.duration_ms >= 0

    def test_failure_exit_code(self):
        executor = ToolExecutor()
        executor.register(ToolSpec(
            tool_id="fail_cmd",
            command=[PYTHON, "-c", "import sys; sys.stderr.write('boom'); sys.exit(3)"],
        ))
        result = executor.execute("fail_cmd", {})
        assert result.ok is False
        assert result.code == ErrorCode.EXECUTION_ERROR.value
        assert "exit code 3" in result.error
        assert "boom" in result.error

    def test_spawn_failure(self):
        executor = ToolExecutor()
        executor.register(ToolSpec(tool_id="nope", command=["/definitely/not/a/binary"]))
        result = executor.execute("nope", {})
        assert result.ok is False
        assert result.code == ErrorCode.EXECUTION_ERROR.value
        assert "spawn failed" in result.error

    def test_timeout_kills_child(self):
        """AC-02c: timeout kills the child — TIMEOUT code and child gone."""
        executor = ToolExecutor(max_output_chars=10_000)
        pid_file = Path(__file__).resolve().parent / "_t0090_child_pid.txt"
        try:
            executor.register(ToolSpec(
                tool_id="sleepy",
                timeout_seconds=1.0,
                command=[
                    PYTHON, "-c",
                    "import os, sys, time; open(sys.argv[1], 'w').write(str(os.getpid())); "
                    "time.sleep(60)",
                    str(pid_file),
                ],
            ))
            started = time.monotonic()
            result = executor.execute("sleepy", {})
            elapsed = time.monotonic() - started
            assert result.ok is False
            assert result.code == ErrorCode.TIMEOUT.value
            assert "killed" in result.error
            assert elapsed < 30, "should return promptly, not after the full sleep"
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            assert _pid_gone(pid), f"child {pid} should have been killed"
        finally:
            pid_file.unlink(missing_ok=True)

    def test_timeout_override_per_call(self):
        executor = ToolExecutor()
        executor.register(ToolSpec(
            tool_id="slow", timeout_seconds=30.0,
            command=[PYTHON, "-c", "import time; time.sleep(60)"],
        ))
        result = executor.execute("slow", {}, timeout_seconds=0.5)
        assert result.code == ErrorCode.TIMEOUT.value

    def test_output_truncation(self):
        """AC-02c: unbounded output is truncated, with a marker."""
        executor = ToolExecutor(max_output_chars=100)
        executor.register(ToolSpec(
            tool_id="noisy",
            command=[PYTHON, "-c", "print('x' * 5000)"],
        ))
        result = executor.execute("noisy", {})
        assert result.ok is True
        assert result.truncated is True
        assert len(result.output) < 5000
        assert "truncated" in result.output

    def test_short_output_not_truncated(self):
        executor = ToolExecutor(max_output_chars=100)
        executor.register(_echo_spec())
        result = executor.execute("echo_tool", {})
        assert result.ok is True
        assert result.truncated is False
        assert "hello" in result.output


class TestSpecBuild:
    def test_template_placeholders(self):
        spec = ToolSpec(
            tool_id="t",
            command='"{py}" -c "import sys; print(sys.argv[1])" "{msg}"',
        )
        argv = build_argv(spec, {"py": PYTHON, "msg": "hi there"})
        assert argv[0] == PYTHON
        assert "hi there" in argv

    def test_missing_placeholder_renders_literal(self):
        spec = ToolSpec(tool_id="t", command="{nope} --flag")
        argv = build_argv(spec, {})
        assert argv == ["{nope}", "--flag"]

    def test_list_command_appends_args(self):
        spec = ToolSpec(tool_id="t", command=[PYTHON, "-c", "pass"])
        argv = build_argv(spec, {"args": ["--x", "1"]})
        assert argv[-2:] == ["--x", "1"]

    def test_missing_command_raises(self):
        spec = ToolSpec(tool_id="t")
        with pytest.raises(ToolExecutionError) as exc:
            build_argv(spec, {})
        assert exc.value.code == ErrorCode.EXECUTION_ERROR


class TestTruncate:
    def test_truncate_marker(self):
        text, truncated = truncate_output("a" * 50, 10)
        assert truncated is True
        assert len(text) < 50
        assert "truncated 40 chars" in text

    def test_no_truncate(self):
        text, truncated = truncate_output("short", 100)
        assert truncated is False
        assert text == "short"


# ── AC-02a: MCP backend through the executor (local mock server) ────────

class TestMcpBackend:
    def test_mcp_call_success(self):
        session = _start_mcp_session()
        try:
            executor = ToolExecutor(mcp_sessions={"mock": session})
            executor.register(ToolSpec(
                tool_id="mcp_echo",
                execution_type=ExecutionType.MCP,
                mcp_server="mock",
                mcp_tool_name="echo",
            ))
            result = executor.execute("mcp_echo", {"message": "from-executor"})
            assert result.ok is True
            assert result.code == ErrorCode.OK.value
            assert "from-executor" in result.output
        finally:
            session.close()

    def test_mcp_tool_iserror_maps_to_execution_error(self):
        session = _start_mcp_session()
        try:
            executor = ToolExecutor(mcp_sessions={"mock": session})
            executor.register(ToolSpec(
                tool_id="mcp_fail",
                execution_type=ExecutionType.MCP,
                mcp_server="mock",
                mcp_tool_name="fail_tool",
            ))
            result = executor.execute("mcp_fail", {})
            assert result.ok is False
            assert result.code == ErrorCode.EXECUTION_ERROR.value
            assert "isError" in result.error
        finally:
            session.close()

    def test_mcp_timeout_maps_to_timeout(self):
        session = _start_mcp_session()
        try:
            executor = ToolExecutor(mcp_sessions={"mock": session})
            executor.register(ToolSpec(
                tool_id="mcp_sleep",
                execution_type=ExecutionType.MCP,
                mcp_server="mock",
                mcp_tool_name="sleep_tool",
                timeout_seconds=1.0,
            ))
            result = executor.execute("mcp_sleep", {"seconds": 2})
            assert result.ok is False
            assert result.code == ErrorCode.TIMEOUT.value
        finally:
            session.close()

    def test_mcp_server_not_registered(self):
        executor = ToolExecutor(mcp_sessions={})
        executor.register(ToolSpec(
            tool_id="mcp_x",
            execution_type=ExecutionType.MCP,
            mcp_server="ghost",
            mcp_tool_name="echo",
        ))
        result = executor.execute("mcp_x", {})
        assert result.ok is False
        assert result.code == ErrorCode.EXECUTION_ERROR.value
        assert "no MCP session" in result.error


# ── security helpers (AC-02c) ───────────────────────────────────────────

def _pid_gone(pid: int) -> bool:
    """True when the process no longer exists (best-effort, portable)."""
    try:
        if platform.system() == "Windows":
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=15,
            )
            return str(pid) not in (r.stdout or "")
        os.kill(pid, 0)
        return False  # still alive
    except (OSError, subprocess.SubprocessError):
        return True


def test_no_network_imports_in_executor_source():
    """The executor surface must not contain network client imports."""
    src = Path(__file__).resolve().parent.parent / "loop_core" / "tool_executor.py"
    text = src.read_text(encoding="utf-8")
    for banned in ("import socket", "import urllib", "import http.client",
                   "import requests"):
        assert banned not in text, f"banned network import: {banned}"
