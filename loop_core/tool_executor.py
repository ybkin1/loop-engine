"""
Tool Executor — whitelisted, timed, error-coded tool execution surface.

T-0090 D5: the StaffDeck tools/ pattern (tool_schema + tool_executor,
benchmarked in T-0086 staffdeck-benchmark.md D5) applied to loop-engine so the
governance system can directly invoke external checkers/tools. The B3 MCP
capability model (docs/designs/loop-v4-ai-agent-governance.md §6.3) provides
the fail-closed whitelist philosophy this module implements.

Execution pipeline (fail-closed, in order):
    1. existence   — unregistered tool_id               -> NOT_FOUND
    2. enabled     — spec disabled                       -> DISABLED
    3. whitelist   — executor whitelist / spec whitelist -> NOT_ALLOWED
    4. type        — unknown execution type              -> UNSUPPORTED_TYPE
    5. timeout     — per-spec or per-call deadline       -> TIMEOUT (child killed)
    6. execution   — local_command via subprocess, mcp via loop_core.mcp_client
                     (http is registered as UNSUPPORTED_TYPE in this wave)
    7. result      — ToolResult with unified error codes

SAFETY: execution surface is bounded by explicit registration + whitelists.
No shell interpolation (commands are argv lists or shlex-split templates with
a safe dict); output is truncated to guard against unbounded results.
"""
from __future__ import annotations

import logging
import shlex
import subprocess
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ── Unified error codes (AC-02) ─────────────────────────────────────────


class ErrorCode(str, Enum):
    """Unified execution error codes returned by ToolExecutor.execute()."""

    OK = "OK"
    NOT_FOUND = "NOT_FOUND"
    DISABLED = "DISABLED"
    NOT_ALLOWED = "NOT_ALLOWED"
    TIMEOUT = "TIMEOUT"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    UNSUPPORTED_TYPE = "UNSUPPORTED_TYPE"


class ExecutionType(str, Enum):
    """Supported execution backends for a ToolSpec."""

    LOCAL_COMMAND = "local_command"
    MCP = "mcp"
    HTTP = "http"


class ToolExecutionError(Exception):
    """Internal signal carrying a unified ErrorCode (never escapes execute())."""

    def __init__(self, code: ErrorCode, message: str, detail: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


@dataclass
class ToolSpec:
    """One registered, executable tool.

    Whitelist fields (fail-closed when configured):
      - allowed_tool_ids: set of tool_ids permitted to execute this spec
        (a spec may serve several ids; unlisted ids are refused).
      - allowed_skills:   set of skill_ids permitted to execute this spec
        (allowed_skills style, StaffDeck); an empty-string skill_id never
        matches a non-empty allowed_skills set.

    Execution-specific fields (only one group is used per execution_type):
      - local_command: command as argv list, or a template string with
        {placeholder} slots filled from args (then shlex-split).
      - mcp:           mcp_server (session id registered on the executor) +
                       mcp_tool_name (tool to call on that server).
      - http:          http_url — reserved; this wave returns UNSUPPORTED_TYPE.
    """

    tool_id: str
    name: str = ""
    description: str = ""
    execution_type: ExecutionType | str = ExecutionType.LOCAL_COMMAND
    timeout_seconds: float = 10.0
    enabled: bool = True
    # ── whitelist (AC-02 / B3 fail-closed) ──
    allowed_tool_ids: set[str] | None = None
    allowed_skills: set[str] | None = None
    skill_id: str = ""
    # ── local_command ──
    command: str | list[str] | None = None
    # ── mcp ──
    mcp_server: str = ""
    mcp_tool_name: str = ""
    # ── http (reserved) ──
    http_url: str = ""

    def __post_init__(self) -> None:
        self.execution_type = ExecutionType(self.execution_type)
        if self.allowed_tool_ids is not None:
            self.allowed_tool_ids = set(self.allowed_tool_ids)
        if self.allowed_skills is not None:
            self.allowed_skills = set(self.allowed_skills)


@dataclass
class ToolResult:
    """Outcome of one execute() call — always returned, never raised."""

    tool_id: str
    ok: bool
    code: str
    output: str = ""
    error: str = ""
    duration_ms: int = 0
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "ok": self.ok,
            "code": self.code,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "truncated": self.truncated,
        }


class _SafeDict(dict):
    """str.format_map helper: missing keys render as {key} instead of KeyError."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def truncate_output(text: str, max_chars: int | None) -> tuple[str, bool]:
    """Truncate long output, appending a marker. Returns (text, truncated)."""
    if max_chars is None or max_chars < 0 or len(text) <= max_chars:
        return text, False
    kept = text[:max_chars]
    return f"{kept}\n...[truncated {len(text) - max_chars} chars]", True


def build_argv(spec: ToolSpec, args: Mapping[str, Any]) -> list[str]:
    """Build the child argv from a local_command spec.

    - list command: used verbatim; extra positional args may be appended via
      args["args"].
    - string command: {placeholder} slots are filled from args with a safe
      dict (missing keys render literally), then shlex-split — no shell.
    """
    cmd = spec.command
    if not cmd:
        raise ToolExecutionError(ErrorCode.EXECUTION_ERROR, "no command configured")
    if isinstance(cmd, str):
        rendered = cmd.format_map(_SafeDict({k: str(v) for k, v in args.items()}))
        argv = shlex.split(rendered)
    else:
        argv = list(cmd)
    extra = args.get("args")
    if isinstance(extra, (list, tuple)):
        argv.extend(str(a) for a in extra)
    if not argv:
        raise ToolExecutionError(ErrorCode.EXECUTION_ERROR, "empty command")
    return argv


class ToolExecutor:
    """Registered-tool executor with whitelist / timeout / error codes.

    Executor-level whitelist: when `allowed_tool_ids` is provided (non-None),
    execute() is fail-closed — any tool_id outside the whitelist returns
    NOT_ALLOWED even if a spec is registered. Spec-level whitelists then gate
    per-spec (allowed_tool_ids / allowed_skills).
    """

    def __init__(
        self,
        allowed_tool_ids: Iterable[str] | None = None,
        max_output_chars: int = 20_000,
        default_timeout_seconds: float = 10.0,
        mcp_sessions: Mapping[str, Any] | None = None,
    ):
        self.allowed_tool_ids = (
            set(allowed_tool_ids) if allowed_tool_ids is not None else None
        )
        self.max_output_chars = max_output_chars
        self.default_timeout_seconds = default_timeout_seconds
        self.mcp_sessions: dict[str, Any] = dict(mcp_sessions or {})
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[ExecutionType, Callable[[ToolSpec, dict, float], tuple[str, bool]]] = {
            ExecutionType.LOCAL_COMMAND: self._execute_local_command,
            ExecutionType.MCP: self._execute_mcp,
            ExecutionType.HTTP: self._execute_http,
        }

    # ── Registration / configuration ────────────────────────────────────

    def register(self, spec: ToolSpec) -> None:
        """Register one spec. Duplicate tool_id raises ValueError."""
        if spec.tool_id in self._specs:
            raise ValueError(f"tool already registered: {spec.tool_id}")
        self._specs[spec.tool_id] = spec

    def register_handler(
        self,
        execution_type: ExecutionType | str,
        handler: Callable[[ToolSpec, dict, float], tuple[str, bool]],
    ) -> None:
        """Override/extend the handler for an execution type."""
        self._handlers[ExecutionType(execution_type)] = handler

    def get_spec(self, tool_id: str) -> ToolSpec | None:
        return self._specs.get(tool_id)

    @property
    def registered(self) -> tuple[str, ...]:
        return tuple(sorted(self._specs))

    # ── Execution pipeline (AC-02a) ─────────────────────────────────────

    def execute(
        self,
        tool_id: str,
        args: Mapping[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> ToolResult:
        """Run the pipeline: existence -> enabled -> whitelist -> type -> run.

        Never raises for a domain failure; returns a ToolResult carrying one
        of the unified ErrorCode values.
        """
        args = dict(args or {})
        started = time.monotonic()

        # 1. existence
        spec = self._specs.get(tool_id)
        if spec is None:
            return ToolResult(
                tool_id=tool_id, ok=False, code=ErrorCode.NOT_FOUND.value,
                error=f"tool not registered: {tool_id}",
            )

        # 2. enabled
        if not spec.enabled:
            return self._fail(spec, ErrorCode.DISABLED, f"tool disabled: {tool_id}",
                              started)

        # 3. whitelist — executor level (fail-closed when configured)
        if (
            self.allowed_tool_ids is not None
            and tool_id not in self.allowed_tool_ids
        ):
            return self._fail(
                spec, ErrorCode.NOT_ALLOWED,
                f"tool '{tool_id}' not in executor whitelist", started,
            )
        # 3b. whitelist — spec level (allowed_tool_ids / allowed_skills)
        if (
            spec.allowed_tool_ids is not None
            and tool_id not in spec.allowed_tool_ids
        ):
            return self._fail(
                spec, ErrorCode.NOT_ALLOWED,
                f"tool '{tool_id}' not in spec allowed_tool_ids", started,
            )
        if (
            spec.allowed_skills is not None
            and spec.skill_id not in spec.allowed_skills
        ):
            return self._fail(
                spec, ErrorCode.NOT_ALLOWED,
                f"spec skill_id '{spec.skill_id}' not in allowed_skills", started,
            )

        # 4. type
        handler = self._handlers.get(spec.execution_type)
        if handler is None:
            return self._fail(
                spec, ErrorCode.UNSUPPORTED_TYPE,
                f"unsupported execution type: {spec.execution_type.value}", started,
            )

        # 5. timeout + 6. execution
        timeout = (
            timeout_seconds if timeout_seconds is not None
            else (spec.timeout_seconds or self.default_timeout_seconds)
        )
        try:
            output, truncated = handler(spec, args, float(timeout))
        except ToolExecutionError as exc:
            return self._fail(spec, exc.code, exc.message, started, detail=exc.detail)
        except Exception as exc:  # noqa: BLE001 — domain boundary: never raise
            logger.exception("tool %s execution failed", tool_id)
            return self._fail(
                spec, ErrorCode.EXECUTION_ERROR, f"execution failed: {exc}", started,
            )

        duration_ms = int((time.monotonic() - started) * 1000)
        return ToolResult(
            tool_id=tool_id, ok=True, code=ErrorCode.OK.value,
            output=output, duration_ms=duration_ms, truncated=truncated,
        )

    # ── Handlers ────────────────────────────────────────────────────────

    def _execute_local_command(
        self, spec: ToolSpec, args: dict, timeout: float
    ) -> tuple[str, bool]:
        """subprocess with timeout (child killed on expiry) + output truncation."""
        argv = build_argv(spec, args)
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            # subprocess.run kills the child on expiry and drains its pipes
            # (AC-02c: timeout kill fallback).
            logger.warning("tool %s timed out after %.1fs (child killed)",
                           spec.tool_id, timeout)
            raise ToolExecutionError(
                ErrorCode.TIMEOUT,
                f"command timed out after {timeout:g}s (child killed)",
            ) from exc
        except OSError as exc:
            raise ToolExecutionError(
                ErrorCode.EXECUTION_ERROR, f"spawn failed: {exc}",
            ) from exc

        stderr = (proc.stderr or "").strip()
        if proc.returncode != 0:
            detail = f"exit code {proc.returncode}"
            if stderr:
                detail += f": {stderr[:500]}"
            raise ToolExecutionError(
                ErrorCode.EXECUTION_ERROR, detail,
            )

        combined = (proc.stdout or "")
        if stderr:
            combined = f"{combined}\n[stderr] {stderr}"
        return truncate_output(combined, self.max_output_chars)

    def _execute_mcp(self, spec: ToolSpec, args: dict, timeout: float) -> tuple[str, bool]:
        """Call a tool on a registered MCP stdio session (loop_core.mcp_client)."""
        session = self.mcp_sessions.get(spec.mcp_server)
        if session is None:
            raise ToolExecutionError(
                ErrorCode.EXECUTION_ERROR,
                f"no MCP session registered for server '{spec.mcp_server}'",
            )
        tool_name = spec.mcp_tool_name or spec.name
        try:
            result = session.call_tool(tool_name, args, timeout_seconds=timeout)
        except Exception as exc:  # MCPSessionError from loop_core.mcp_client
            # Map MCP error codes onto the unified set (AC-02a).
            code = getattr(exc, "code", "")
            if code == "MCP_TIMEOUT":
                raise ToolExecutionError(
                    ErrorCode.TIMEOUT,
                    f"MCP tool '{tool_name}' timed out after {timeout:g}s",
                ) from exc
            message = getattr(exc, "message", str(exc))
            raise ToolExecutionError(
                ErrorCode.EXECUTION_ERROR,
                f"MCP tool '{tool_name}' failed: {message}",
            ) from exc
        text = _mcp_content_text(result)
        return truncate_output(text, self.max_output_chars)

    def _execute_http(self, spec: ToolSpec, args: dict, timeout: float) -> tuple[str, bool]:
        """http execution is reserved; this wave is UNSUPPORTED_TYPE.

        The type is registered so the error code path is explicit and a custom
        handler can be registered via register_handler().
        """
        raise ToolExecutionError(
            ErrorCode.UNSUPPORTED_TYPE,
            "http execution type is not implemented in this wave (D5); "
            "register a custom handler",
        )

    # ── Helpers ─────────────────────────────────────────────────────────

    def _fail(self, spec: ToolSpec, code: ErrorCode, message: str,
              started: float, detail: Any = None) -> ToolResult:
        duration_ms = int((time.monotonic() - started) * 1000)
        err = message if detail is None else f"{message}: {detail}"
        logger.warning("tool %s -> %s: %s", spec.tool_id, code.value, err)
        return ToolResult(
            tool_id=spec.tool_id, ok=False, code=code.value,
            error=err, duration_ms=duration_ms,
        )


def _mcp_content_text(result: Mapping[str, Any]) -> str:
    """Flatten an MCP tools/call result's text content into one string."""
    import json

    if not result:
        return ""
    content = result.get("content")
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, Mapping) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        if parts:
            return "\n".join(parts)
    return json.dumps(result, ensure_ascii=False)
