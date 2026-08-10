#!/usr/bin/env python3
"""verify_mcp.py — AC-04：MCP tools/list 实测（行缓冲通信）"""
import json
import subprocess
import sys

proc = subprocess.Popen(
    ["node", r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\dist\src\server\index.js"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
)
try:
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}) + "\n")
    proc.stdin.flush()
    # 读取一行响应（MCP stdio 用换行分隔）
    import select
    line = proc.stdout.readline()
    if not line:
        print("[FAIL] no response line")
        sys.exit(1)
    resp = json.loads(line)
    tools = [t["name"] for t in resp.get("result", {}).get("tools", [])]
    has_oqa = "loop_output_quality" in tools
    has_gate = "loop_quality_gate" in tools
    has_state = "loop_state" in tools
    print(f"[AC-04] MCP tools/list: {len(tools)} tools")
    print(f"  loop_output_quality: {has_oqa}")
    print(f"  loop_quality_gate: {has_gate}")
    print(f"  loop_state: {has_state}")
    if has_oqa and has_gate and has_state:
        print("\n[PASS] AC-04 MCP tools/list verified")
        sys.exit(0)
    print("\n[FAIL] AC-04 missing tools")
    sys.exit(1)
finally:
    proc.terminate()
