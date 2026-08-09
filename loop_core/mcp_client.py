"""
MCP Client — JSON-RPC 2.0 over stdio for external MCP tools.

T-0090 D5: the StaffDeck tools/mcp_client.py pattern (stdio transport +
_StdioSession request/response matching, benchmarked in T-0086
staffdeck-benchmark.md D5) applied to loop-engine. The governance system can
drive external checkers exposing the Model Context Protocol over stdio.

Protocol coverage (AC-02b), in handshake order:
    1. initialize          — negotiate protocolVersion (default 2024-11-05)
    2. notifications/initialized — one-way notification after initialize
    3. tools/list          — enumerate the server's tool catalog
    4. tools/call          — invoke a tool with arguments

Transport details:
    - stdio only: spawns a local child process and speaks JSON-RPC 2.0 line
      framed over stdin/stdout. No network sockets are ever opened.
    - Responses are matched to requests by JSON-RPC id via a reader thread
      and per-request futures.
    - stderr is drained to a bounded buffer (no pipe deadlock) and surfaced
      in connection-failure diagnostics.

Error codes (AC-02):
    MCP_TIMEOUT            — no response within the request timeout
    MCP_ERROR              — JSON-RPC error response (or tools/call isError)
    MCP_CONNECTION_FAILED  — spawn failure / process exit / write failure
"""
from __future__ import annotations

import itertools
import json
import logging
import os
import subprocess
import threading
from collections import deque
from collections.abc import Mapping, Sequence
from concurrent.futures import Future
from typing import Any

logger = logging.getLogger(__name__)

MCP_PROTOCOL_VERSION = "2024-11-05"
DEFAULT_TIMEOUT_SECONDS = 10.0
_STDERR_TAIL_LINES = 50

MCP_TIMEOUT = "MCP_TIMEOUT"
MCP_ERROR = "MCP_ERROR"
MCP_CONNECTION_FAILED = "MCP_CONNECTION_FAILED"


class MCPSessionError(Exception):
    """Raised for all session-level failures; carries a stable error code."""

    def __init__(self, code: str, message: str, detail: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


class _StdioSession:
    """Spawned MCP server process + id-matched JSON-RPC request/response loop.

    Modeled on the StaffDeck _StdioSession: one writer (caller thread), one
    reader thread on stdout, pending requests keyed by JSON-RPC id.
    """

    def __init__(
        self,
        command: Sequence[str],
        request_timeout: float,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ):
        self.command = list(command)
        self.request_timeout = request_timeout
        self._next_id = itertools.count(1)
        self._pending: dict[int, Future] = {}
        self._lock = threading.Lock()
        self._closed = False
        self._eof = False
        self._stderr_tail: deque[str] = deque(maxlen=_STDERR_TAIL_LINES)
        self._stderr_error: str | None = None

        try:
            self._proc = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=dict(os.environ, **(env or {})),
                cwd=cwd,
            )
        except OSError as exc:
            raise MCPSessionError(
                MCP_CONNECTION_FAILED,
                f"failed to spawn MCP server {' '.join(self.command)!r}: {exc}",
            ) from exc

        self._reader = threading.Thread(
            target=self._read_loop, name="mcp-stdio-reader", daemon=True,
        )
        self._reader.start()
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr, name="mcp-stderr-drain", daemon=True,
        )
        self._stderr_thread.start()

    # ── plumbing ────────────────────────────────────────────────────────

    @property
    def alive(self) -> bool:
        return not self._closed and self._proc.poll() is None

    def _write(self, line: str) -> None:
        if self._closed:
            raise MCPSessionError(MCP_CONNECTION_FAILED, "session closed")
        if self._proc.poll() is not None:
            raise MCPSessionError(
                MCP_CONNECTION_FAILED,
                f"MCP server process exited (code {self._proc.returncode})",
            )
        try:
            self._proc.stdin.write(line)
            self._proc.stdin.flush()
        except (OSError, ValueError) as exc:
            raise MCPSessionError(
                MCP_CONNECTION_FAILED, f"write to MCP server failed: {exc}",
            ) from exc

    def _read_loop(self) -> None:
        try:
            for raw in self._proc.stdout:
                line = raw.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    logger.debug("ignoring non-JSON line from MCP server")
                    continue
                if "id" not in msg:
                    continue  # server notification — nothing to resolve
                with self._lock:
                    fut = self._pending.pop(msg["id"], None)
                if fut is not None and not fut.done():
                    fut.set_result(msg)
        finally:
            # Server stdout closed / process gone: fail all pending requests
            # fail-closed instead of letting them hang until timeout.
            with self._lock:
                self._eof = True
                pending = list(self._pending.values())
                self._pending.clear()
            err = self._connection_failure_message()
            for fut in pending:
                if not fut.done():
                    fut.set_exception(
                        MCPSessionError(MCP_CONNECTION_FAILED, err)
                    )

    def _drain_stderr(self) -> None:
        try:
            for raw in self._proc.stderr:
                self._stderr_tail.append(raw.rstrip("\r\n"))
        except (OSError, ValueError):
            pass
        self._stderr_error = self._proc.poll()

    def _connection_failure_message(self) -> str:
        if self._proc.poll() is None:
            base = "MCP server stdout closed unexpectedly"
        else:
            base = f"MCP server process exited (code {self._proc.returncode})"
        tail = "\n".join(list(self._stderr_tail)[-10:])
        return f"{base}" + (f"\nstderr tail:\n{tail}" if tail else "")

    # ── JSON-RPC verbs ──────────────────────────────────────────────────

    def request(self, method: str, params: Mapping[str, Any] | None,
                timeout: float | None) -> dict[str, Any]:
        """Send a request and wait for the id-matched response.

        Raises MCPSessionError: MCP_TIMEOUT / MCP_ERROR / MCP_CONNECTION_FAILED.
        """
        if not self.alive:
            raise MCPSessionError(
                MCP_CONNECTION_FAILED,
                self._connection_failure_message(),
            )
        rid = next(self._next_id)
        payload = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": dict(params or {}),
        }
        fut: Future = Future()
        with self._lock:
            self._pending[rid] = fut
        try:
            self._write(json.dumps(payload) + "\n")
        except MCPSessionError:
            with self._lock:
                self._pending.pop(rid, None)
            raise

        effective_timeout = timeout if timeout is not None else self.request_timeout
        try:
            msg = fut.result(timeout=effective_timeout)
        except MCPSessionError:
            raise
        except TimeoutError:
            with self._lock:
                self._pending.pop(rid, None)
            logger.warning("MCP request %s timed out after %.1fs",
                           method, effective_timeout)
            raise MCPSessionError(
                MCP_TIMEOUT,
                f"MCP request '{method}' timed out after {effective_timeout:g}s",
            ) from None

        if msg.get("error"):
            err = msg["error"]
            raise MCPSessionError(
                MCP_ERROR,
                f"JSON-RPC error {err.get('code')}: {err.get('message', '')}",
                detail=err,
            )
        return msg.get("result", {})

    def notify(self, method: str, params: Mapping[str, Any] | None) -> None:
        """One-way notification — no id, no response expected."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": dict(params or {}),
        }
        self._write(json.dumps(payload) + "\n")

    def close(self) -> None:
        """Terminate the child, drain pipes, resolve nothing further."""
        if self._closed:
            return
        self._closed = True
        if self._proc.poll() is None:
            try:
                self._proc.terminate()
            except OSError:
                pass
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    self._proc.kill()
                except OSError:
                    pass
                self._proc.wait(timeout=5)
        for stream in (self._proc.stdin, self._proc.stdout, self._proc.stderr):
            try:
                stream.close()
            except (OSError, ValueError):
                pass
        self._reader.join(timeout=2)

    def __enter__(self) -> _StdioSession:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()


class MCPSession:
    """High-level MCP stdio client: initialize -> tools/list -> tools/call.

    Typical use:

        with MCPSession([sys.executable, "mock_server.py"]) as s:
            s.initialize()
            tools = s.list_tools()
            result = s.call_tool("echo", {"message": "hi"})

    All network-free: the child is a local process speaking JSON-RPC over
    stdio; no sockets are opened (T-0090: tests stay fully local).
    """

    def __init__(
        self,
        command: Sequence[str],
        protocol_version: str = MCP_PROTOCOL_VERSION,
        request_timeout: float = DEFAULT_TIMEOUT_SECONDS,
        auto_initialize: bool = True,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ):
        self.command = list(command)
        self.protocol_version = protocol_version
        self.request_timeout = request_timeout
        self._session = _StdioSession(command, request_timeout, env=env, cwd=cwd)
        self._initialized = False
        self.server_info: dict[str, Any] = {}
        self.server_protocol_version: str = ""
        if auto_initialize:
            try:
                self.initialize()
            except Exception:
                # Handshake failure (spawn/exit/protocol): don't leak the child.
                self._session.close()
                raise

    # ── lifecycle ───────────────────────────────────────────────────────

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def alive(self) -> bool:
        return self._session.alive

    def initialize(self) -> dict[str, Any]:
        """Handshake: initialize, then send notifications/initialized.

        Per the 2024-11-05 spec the server echoes the protocol version it
        supports; a mismatch fails closed (MCP_ERROR) instead of proceeding.
        """
        result = self._session.request(
            "initialize",
            {
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "loop-engine", "version": "3.12.67"},
            },
            timeout=self.request_timeout,
        )
        server_version = result.get("protocolVersion", "")
        if server_version != self.protocol_version:
            raise MCPSessionError(
                MCP_ERROR,
                f"protocol version mismatch: server {server_version!r} != "
                f"client {self.protocol_version!r}",
                detail=result,
            )
        self._session.notify("notifications/initialized", {})
        self._initialized = True
        self.server_info = result.get("serverInfo", {})
        self.server_protocol_version = server_version
        logger.info("MCP initialized: server=%s protocol=%s",
                    self.server_info.get("name", "?"), server_version)
        return result

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise MCPSessionError(
                MCP_ERROR, "session not initialized (call initialize() first)"
            )

    # ── protocol methods ────────────────────────────────────────────────

    def list_tools(self, timeout_seconds: float | None = None) -> list[dict[str, Any]]:
        """tools/list -> the server's tool catalog."""
        self._require_initialized()
        result = self._session.request(
            "tools/list", {}, timeout=timeout_seconds,
        )
        tools = result.get("tools", [])
        return [dict(t) for t in tools] if isinstance(tools, list) else []

    def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        """tools/call -> the tool's result dict.

        A result flagged isError=True raises MCPSessionError(MCP_ERROR) —
        fail-visible instead of surfacing an error payload as success.
        """
        self._require_initialized()
        result = self._session.request(
            "tools/call",
            {"name": name, "arguments": dict(arguments or {})},
            timeout=timeout_seconds,
        )
        if result.get("isError"):
            raise MCPSessionError(
                MCP_ERROR, f"tool '{name}' returned isError", detail=result,
            )
        return result

    # ── teardown ────────────────────────────────────────────────────────

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> MCPSession:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
