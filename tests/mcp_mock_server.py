#!/usr/bin/env python3
"""
mcp_mock_server.py — LOCAL mock MCP stdio server for T-0090 D5 tests.

A minimal, deterministic JSON-RPC 2.0-over-stdio server used ONLY by
tests/test_mcp_client.py and tests/test_tool_executor.py. It never opens a
network socket — the whole exchange happens over stdin/stdout pipes of the
local subprocess spawned by loop_core.mcp_client.MCPSession.

Behavior:
  - initialize        -> echoes the requested protocolVersion
  - notifications/initialized -> no response (one-way)
  - tools/list        -> a fixed catalog: echo / add / fail_tool / sleep_tool
  - tools/call        -> echo / add succeed; fail_tool returns isError;
                         sleep_tool sleeps `seconds` before responding
                         (timeout tests); unknown tool -> JSON-RPC -32602

Optional modes via env (set by the tests when spawning):
  MOCK_SERVER_MODE=exit                   -> exit(3) immediately
  MOCK_SERVER_MODE=garbage                -> write non-JSON lines, then exit
  MOCK_SERVER_MODE=exit_after_initialize  -> exit right after initialize
  MOCK_SERVER_RECORD=<path>               -> append every received request
                                             (method + id) as JSON lines
"""
import json
import os
import sys
import time

TOOLS = [
    {
        "name": "echo",
        "description": "Echo the given message back",
        "inputSchema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    },
    {
        "name": "add",
        "description": "Add two integers",
        "inputSchema": {
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    },
    {
        "name": "fail_tool",
        "description": "Always returns isError=True",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sleep_tool",
        "description": "Sleep `seconds` before responding (timeout tests)",
        "inputSchema": {
            "type": "object",
            "properties": {"seconds": {"type": "number"}},
        },
    },
]


def handle(request: dict) -> dict | None:
    """Return the response for a request; None = one-way notification."""
    method = request.get("method", "")
    rid = request.get("id")

    if method == "initialize":
        params = request.get("params", {})
        version = params.get("protocolVersion", "2024-11-05")
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "loop-engine-mock-server", "version": "1.0.0"},
            },
        }
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = request.get("params", {})
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        if name == "sleep_tool":
            time.sleep(float(arguments.get("seconds", 2)))
            return {
                "jsonrpc": "2.0", "id": rid,
                "result": {"content": [{"type": "text",
                                        "text": json.dumps({"slept": arguments.get("seconds")})}]},
            }
        if name == "echo":
            return {
                "jsonrpc": "2.0", "id": rid,
                "result": {"content": [{"type": "text",
                                        "text": str(arguments.get("message", ""))}]},
            }
        if name == "add":
            total = int(arguments.get("a", 0)) + int(arguments.get("b", 0))
            return {
                "jsonrpc": "2.0", "id": rid,
                "result": {"content": [{"type": "text", "text": str(total)}]},
            }
        if name == "fail_tool":
            return {
                "jsonrpc": "2.0", "id": rid,
                "result": {"content": [{"type": "text", "text": "boom"}],
                           "isError": True},
            }
        return {
            "jsonrpc": "2.0", "id": rid,
            "error": {"code": -32602, "message": f"unknown tool: {name}"},
        }
    return {
        "jsonrpc": "2.0", "id": rid,
        "error": {"code": -32601, "message": f"unknown method: {method}"},
    }


def main() -> int:
    mode = os.environ.get("MOCK_SERVER_MODE", "")
    record_path = os.environ.get("MOCK_SERVER_RECORD", "")

    if mode == "exit":
        return 3
    if mode == "garbage":
        for _ in range(5):
            sys.stdout.write("this is not json\n")
            sys.stdout.flush()
        return 0

    for line in sys.stdin:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            request = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if record_path:
            with open(record_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"method": request.get("method"),
                                     "id": request.get("id")}) + "\n")
        response = handle(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        if mode == "exit_after_initialize" and request.get("method") == "initialize":
            return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
