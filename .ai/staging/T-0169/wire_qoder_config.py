#!/usr/bin/env python3
"""wire_qoder_config.py — T-0169 接线：loop hooks + MCP 注册进 Qoder 真实配置

策略：
1. 读取 Qoder 真实 User/settings.json
2. hooks 追加 loop 脚本（PreToolUse Write|Edit + Bash、UserPromptSubmit、
   Stop、SessionStart），保留 clawd-on-desk 既有注册
3. mcpServers 追加 loop-engineering（保留 constraint-enforcer/spec-oracle）
4. 幂等：已含 loop 注册则跳过
"""
import json
from pathlib import Path

REAL = Path(r"C:\Users\Administrator\AppData\Roaming\QoderCN\User\settings.json")
MIRROR = Path(r"C:\Users\Administrator\.qoder-cn\settings.json")
SCRIPTS = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts")
DIST = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\dist\src\server\index.js")

def node_cmd(name: str) -> dict:
    return {
        "command": f'node "{SCRIPTS / name}"',
        "type": "command",
    }

def main() -> int:
    if not REAL.exists():
        print(f"[err] real settings not found: {REAL}")
        return 1

    d = json.loads(REAL.read_text(encoding="utf-8"))
    hooks = d.setdefault("hooks", {})
    changed = False

    # ── PreToolUse: loop guards（Write|Edit + Bash）──
    pretool = hooks.setdefault("PreToolUse", [])
    loop_pretool = [
        {"matcher": "Write|Edit", "hooks": [node_cmd("gate-guard.js"), node_cmd("path-guard.js"), node_cmd("role-isolation.js"), node_cmd("ledger-guard.js"), node_cmd("import-guard.js"), node_cmd("output_quality_guard.js")]},
        {"matcher": "Bash", "hooks": [node_cmd("gate-guard.js"), node_cmd("path-guard.js"), node_cmd("role-isolation.js"), node_cmd("ledger-guard.js")]},
    ]
    existing_json = json.dumps(pretool, ensure_ascii=False)
    if "output_quality_guard.js" not in existing_json:
        # 追加（保留 clawd）
        for entry in loop_pretool:
            pretool.append(entry)
        changed = True
        print("[hooks] PreToolUse loop guards appended")

    # ── UserPromptSubmit: 状态注入 ──
    ups = hooks.setdefault("UserPromptSubmit", [])
    ups_json = json.dumps(ups, ensure_ascii=False)
    if "session-brief.js" not in ups_json:
        ups.append({"matcher": "", "hooks": [node_cmd("auto-activate.js"), node_cmd("template-injector.js"), node_cmd("session-brief.js")]})
        changed = True
        print("[hooks] UserPromptSubmit loop injectors appended")

    # ── Stop: 会话快照 ──
    stop = hooks.setdefault("Stop", [])
    stop_json = json.dumps(stop, ensure_ascii=False)
    if "session-summary.js" not in stop_json:
        stop.append({"matcher": "", "hooks": [node_cmd("session-summary.js")]})
        changed = True
        print("[hooks] Stop session-summary appended")

    # ── SessionStart: 状态注入（loop_auto_activate 已有，追加 loop 版不冲突）──
    # 注：clawd 已注册 SessionStart；loop 的 session_brief 在 UserPromptSubmit 已覆盖，
    #     SessionStart 不再重复追加，避免双重注入。

    # ── mcpServers ──
    mcp = d.setdefault("mcpServers", {})
    if "loop-engineering" not in mcp:
        mcp["loop-engineering"] = {
            "command": "node",
            "args": [str(DIST).replace("\\", "/")],
            "env": {"LOOP_PROJECT_ROOT": "${workspaceFolder}"},
        }
        changed = True
        print("[mcp] loop-engineering registered")

    if not changed:
        print("[same] no changes needed (already wired)")

    REAL.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[write] {REAL}")

    # 校验 JSON 合法
    json.loads(REAL.read_text(encoding="utf-8"))
    print("[ok] real settings.json valid JSON")

    # 注意：不再写镜像 .qoder-cn/settings.json —— 该文件由 Qoder 插件管理
    # （aicodingPluginSettingsMigrationVersion），覆盖会丢失 enabledPlugins（P1-2 修复）
    print("[skip] mirror .qoder-cn/settings.json NOT written (Qoder-managed file)")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
