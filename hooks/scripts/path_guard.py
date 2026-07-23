#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
path_guard.py — ZCode PreToolUse hook：保护区路径的写入需用户当场确认。

保护区（config.yaml path_guard.protected_paths，默认）：
  AGENTS.md、stable/、registry/、.zcode/config.json、.zcode/tools/

这些路径对应治理体系的权威事实与执行层本身。历史上 T-0030 曾发生
"直接修改正在使用的全局脚本"的 P0 事故——保护区拦截就是针对这类漂移。

两种模式（config.yaml path_guard.decision）：
- ask（默认）：输出 PreToolUse JSON，permissionDecision = "ask"，
  把决定权交给用户当场点击确认——用户即信任锚。
- deny：exit 2 硬阻断，需要先有对应 gate 再由用户临时切换配置。

退出码：0 = 放行（含 ask 模式，决定随 JSON 返回）；2 = deny 模式下的阻断。
JSON 输出严格只含文档认可的键；任何内部异常一律 exit 0 并在 stderr 警告，
避免 hook 自身故障瘫痪整个会话。
"""

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_common import (  # noqa: E402
    DEFAULT_CONFIG,
    extract_target_path,
    is_governance_project,
    load_config,
    matches_protected,
    normalize_rel,
    project_root,
    read_stdin_json,
)

EXIT_PASS = 0
EXIT_BLOCK = 2


def emit_ask(rule, rel):
    decision = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                f"[path_guard] 目标 {rel} 命中保护区规则 {rule}。"
                "该路径属于治理权威事实或执行层，写入需要你当场确认。"
            ),
        }
    }
    sys.stdout.write(json.dumps(decision, ensure_ascii=False))


def main():
    hook_input = read_stdin_json()
    root = project_root(hook_input)

    if not is_governance_project(root):
        return EXIT_PASS

    try:
        cfg = load_config(root)
        path_cfg = cfg.get("path_guard", DEFAULT_CONFIG["path_guard"])
        if not path_cfg.get("enabled", True):
            return EXIT_PASS

        target = extract_target_path(hook_input)
        if not target:
            return EXIT_PASS  # 取不到路径时不臆断，放行

        rel = normalize_rel(root, target)
        rule = matches_protected(rel, path_cfg.get("protected_paths", []))
        if rule is None:
            return EXIT_PASS

        mode = path_cfg.get("decision", "ask")
        if mode == "deny":
            print(
                f"[path_guard] BLOCKED: {rel} 命中保护区规则 {rule}，"
                "当前为 deny 模式。请先取得对应 gate，再由用户临时调整 "
                "config.yaml 的 path_guard.decision。",
                file=sys.stderr,
            )
            return EXIT_BLOCK

        emit_ask(rule, rel)
        return EXIT_PASS
    except Exception as e:
        # hook 自身故障不应瘫痪会话；记录后放行（ZCode 日志可见）
        print(f"[path_guard] WARN: 内部异常（{e}），放行。", file=sys.stderr)
        return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
