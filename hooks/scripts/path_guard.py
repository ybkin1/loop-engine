#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
path_guard.py — ZCode PreToolUse hook：保护区路径的写入需用户当场确认。

保护区（config.yaml path_guard.protected_paths，默认）：
  AGENTS.md、stable/、registry/、.zcode/config.json、.zcode/tools/

这些路径对应治理体系的权威事实与执行层本身。历史上 T-0030 曾发生
"直接修改正在使用的全局脚本"的 P0 事故——保护区拦截就是针对这类漂移。

只读豁免（T-0086）：Read/WebFetch/WebSearch 及只读 Bash 命令访问
项目外路径（如插件缓存中的 hook 协议文档）不构成写入，直接放行；
写入工具访问项目外路径仍被边界拦截（fail-closed，对写入不弱化任何检查）。
T-0086-P1 收紧：执行形态 Bash（sh/bash/dash/./php/ruby 等解释器或直接
脚本执行）引用项目外路径 → 阻断（脚本内部可写任意文件，fail-closed）。

两种模式（config.yaml path_guard.decision）：
- ask（默认）：输出 PreToolUse JSON，permissionDecision = "ask"，
  把决定权交给用户当场点击确认——用户即信任锚。
- deny：exit 2 硬阻断，需要先有对应 gate 再由用户临时切换配置。

退出码：0 = 放行（含 ask 模式，决定随 JSON 返回）；2 = deny 模式下的阻断。
JSON 输出严格只含文档认可的键；任何内部异常一律 exit 0 并在 stderr 警告，
避免 hook 自身故障瘫痪整个会话。
"""

import json
import logging
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING, format='[%(name)s] %(levelname)s: %(message)s')

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_common import (  # noqa: E402
    DEFAULT_CONFIG,
    extract_target_path,
    is_execution_command,
    is_governance_project,
    is_path_safe,
    is_readonly_command,
    load_config,
    matches_protected,
    normalize_rel,
    project_root,
    read_stdin_json,
    should_fail_closed,
)

# 只读工具：无文件写入语义。path_guard 是"写入"保护——
# 只读工具访问项目外路径不构成写入边界风险，应放行（fail-open 对只读）。
READ_ONLY_TOOLS = frozenset({"Read", "WebFetch", "WebSearch"})

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


def _references_outside(root: Path, command: str) -> bool:
    """命令是否引用项目根之外的路径（引号感知的路径形态 token 扫描）。

    与 loop_enforcement._command_references_outside 逻辑一致（镜像副本）：
    只检查路径形态 token（绝对路径、盘符、../ 逃逸或含分隔符的相对路径），
    任一 token 明确解析到项目根外即返回 True；无法判定 → False（保守）。
    """
    if not command or not isinstance(command, str):
        return False
    tokens = re.findall(r'"[^"]*"|\'[^\']*\'|\S+', command)
    for token in tokens:
        t = token.strip("\"'")
        if not t or t.startswith("-"):
            continue
        is_drive = len(t) >= 3 and t[1] == ":" and t[2] in ("\\", "/")
        if not (t.startswith("/") or t.startswith("../") or "/" in t
                or "\\" in t or is_drive):
            continue
        try:
            if not is_path_safe(root, t):
                return True
        except Exception:
            continue
    return False


def _is_governance_tool_invocation(command: str, root: Path) -> bool:
    """治理工具调用（python 家族解释器 + 白名单目录脚本 / 直接执行白名单脚本）。

    复用 loop_enforcement.is_governance_tool_command（单一判定源，避免
    两处豁免逻辑漂移）。惰性导入：仅在执行形态 Bash 且引用项目外路径
    的罕见分支触发。
    """
    if not command or not isinstance(command, str):
        return False
    try:
        from loop_enforcement import is_governance_tool_command
        return bool(is_governance_tool_command(command, root))
    except Exception:
        return False


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

        # 只读操作豁免（T-0086）：path_guard 拦截的是"项目外写入"。
        # Read/WebFetch/WebSearch 及只读 Bash（ls/cat/head/tail/grep 等）
        # 访问项目外路径（如插件 hook 协议文档）不构成写入，直接放行；
        # 写入工具访问项目外路径仍走下方边界拦截（fail-closed）。
        tool_name = hook_input.get("tool_name", "")
        command = (hook_input.get("tool_input") or {}).get("command", "")
        is_readonly_op = tool_name in READ_ONLY_TOOLS or bool(
            command and is_readonly_command(command)
        )

        # T-0086-P1 收紧：执行形态 Bash（sh/bash/dash/./php/ruby/python 等
        # 解释器或直接脚本执行）引用项目外路径 → 项目外写入风险无法从命令
        # 行判定（脚本内部可写任意文件）→ fail-closed 阻断。只读命令
        # （如 `python --version`、`cat /outside/x`）仍走上方只读豁免。
        # T-0086-P3 豁免：治理工具调用（如 `C:/Python312/python.exe
        # .zcode/tools/validate_state.py .`）的"项目外引用"只是解释器
        # 二进制路径（Windows 上解释器几乎总在项目外），脚本本身在
        # 项目白名单目录内，写入目标受 loop_enforcement 的
        # is_governance_write 与内容守卫约束 → 不构成项目外写入，放行。
        if tool_name == "Bash" and command and is_execution_command(command) \
                and not is_readonly_command(command) \
                and _references_outside(root, command) \
                and not _is_governance_tool_invocation(command, root):
            logger.warning(
                "BLOCKED: Execution-form Bash command references a path "
                "outside the project root; script execution is write-capable "
                "and its write targets cannot be verified. Command: %s",
                command[:200],
            )
            return EXIT_BLOCK

        if is_readonly_op:
            return EXIT_PASS

        target = extract_target_path(hook_input)
        if not target:
            return EXIT_PASS  # 取不到路径时不臆断，放行

        # 路径安全检查：写入目标明确在项目根外 → 阻断
        if not is_path_safe(root, target):
            logger.warning(
                "BLOCKED: Target '%s' is outside the project root. "
                "Writing outside the project boundary is not allowed.",
                target,
            )
            return EXIT_BLOCK

        rel = normalize_rel(root, target)
        rule = matches_protected(rel, path_cfg.get("protected_paths", []))
        if rule is None:
            return EXIT_PASS

        mode = path_cfg.get("decision", "ask")
        if mode == "deny":
            logger.warning(
                "BLOCKED: %s 命中保护区规则 %s，"
                "当前为 deny 模式。请先取得对应 gate，再由用户临时调整 "
                "config.yaml 的 path_guard.decision。",
                rel, rule,
            )
            return EXIT_BLOCK

        emit_ask(rule, rel)
        return EXIT_PASS
    except Exception:
        if should_fail_closed(root):
            return EXIT_BLOCK
        return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
