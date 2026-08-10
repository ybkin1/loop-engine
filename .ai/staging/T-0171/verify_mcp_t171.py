#!/usr/bin/env python3
"""verify_mcp_t171.py — loop_oqa_patterns MCP 工具 e2e 验证"""
import json
import subprocess
import sys

proc = subprocess.Popen(
    ["node", r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\dist\src\server\index.js"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8",
)
try:
    # tools/list 确认注册
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    resp = json.loads(line)
    tools = [t["name"] for t in resp.get("result", {}).get("tools", [])]
    has = "loop_oqa_patterns" in tools
    print(f"[AC-03] loop_oqa_patterns registered: {has} (total {len(tools)} tools)")
    if not has:
        sys.exit(1)

    # 调用 loop_oqa_patterns list（真实项目 root）
    call = {
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "loop_oqa_patterns", "arguments": {
            "action": "list", "project_root": r"C:\Users\Administrator\ZCodeProject\loop-engine",
        }},
    }
    proc.stdin.write(json.dumps(call) + "\n")
    proc.stdin.flush()
    line2 = proc.stdout.readline()
    resp2 = json.loads(line2)
    text = resp2["result"]["content"][0]["text"]
    print("[AC-03] loop_oqa_patterns list output:")
    print(text[:600])
    # 应含 5 内置 + 项目级模式
    data = json.loads(text)
    ids = [p["id"] for p in data]
    print(f"  patterns: {len(data)} ids={ids}")
    ok = len(data) >= 5 and "LAZY-FAKE-DATA" in ids and "HALLUCINATE-COMMENT-CLAIM" in ids
    print(f"\n[{'PASS' if ok else 'FAIL'}] loop_oqa_patterns verified")
    sys.exit(0 if ok else 1)
finally:
    proc.terminate()
