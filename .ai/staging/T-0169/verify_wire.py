#!/usr/bin/env python3
"""verify_wire.py — T-0169 AC-01/02 验证：loop 注册存在 + clawd 保留 + MCP 正确"""
import json
from pathlib import Path

REAL = Path(r"C:\Users\Administrator\AppData\Roaming\QoderCN\User\settings.json")

def main() -> int:
    d = json.loads(REAL.read_text(encoding="utf-8"))
    hooks = d.get("hooks", {})
    ok = True

    # AC-01: loop hooks 注册存在 + clawd 保留
    pretool_json = json.dumps(hooks.get("PreToolUse", []), ensure_ascii=False)
    loop_scripts = ["gate-guard.js", "path-guard.js", "role-isolation.js", "ledger-guard.js", "import-guard.js", "output_quality_guard.js"]
    for s in loop_scripts:
        present = s in pretool_json
        print(f"  loop hook {s}: {'OK' if present else 'MISSING'}")
        ok = ok and present
    clawd_present = "clawd-hook.js" in pretool_json or "clawd-node-wrapper.ps1" in pretool_json
    print(f"  clawd PreToolUse preserved: {'OK' if clawd_present else 'LOST!'}")
    ok = ok and clawd_present

    ups_json = json.dumps(hooks.get("UserPromptSubmit", []), ensure_ascii=False)
    for s in ["session-brief.js", "auto-activate.js", "template-injector.js"]:
        present = s in ups_json
        print(f"  UserPromptSubmit {s}: {'OK' if present else 'MISSING'}")
        ok = ok and present

    stop_json = json.dumps(hooks.get("Stop", []), ensure_ascii=False)
    print(f"  Stop session-summary: {'OK' if 'session-summary.js' in stop_json else 'MISSING'}")
    ok = ok and "session-summary.js" in stop_json

    # AC-02: mcpServers
    mcp = d.get("mcpServers", {})
    loop_mcp = mcp.get("loop-engineering")
    if not loop_mcp:
        print("  loop-engineering MCP: MISSING")
        return 1
    dist_ok = bool(loop_mcp.get("args")) and "loop-engine-lab/dist/src/server/index.js" in str(loop_mcp.get("args"))
    print(f"  loop-engineering MCP: OK (dist path: {dist_ok})")
    print(f"  constraint-enforcer preserved: {'OK' if 'constraint-enforcer' in mcp else 'LOST!'}")
    ok = ok and dist_ok and "constraint-enforcer" in mcp

    print(f"\n[{'PASS' if ok else 'FAIL'}] AC-01/AC-02 wiring verification")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
