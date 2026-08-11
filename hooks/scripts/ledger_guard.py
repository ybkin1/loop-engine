#!/usr/bin/env python3
"""
ledger_guard.py — PreToolUse hook: 强制校验 .ai/ledger/ 完整性。

拦截所有对 .ai/ledger/ 的 Write/Edit 操作，强制：
  1. 只允许追加（open("a") 语义）—— 禁止修改已有行
  2. 写入内容必须通过 chain_hash 验证（hash 连续）
  3. 禁止删除、截断、覆盖
  4. Edit 工具不可用于 ledger 文件（必须用 Write 追加）

死锁预防：
  - chain 断裂时，block 消息中包含恢复方法（删除 ledger 文件重置）
  - 空文件或新文件不校验 chain（允许从零重建）
  - 所有 block 消息提供可操作的下一步

Exit codes: 0 = allow, 2 = block
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.dont_write_bytecode = True

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.WARNING, format="[%(name)s] %(levelname)s: %(message)s"
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from hook_common import (
    EXIT_PASS,
    EXIT_BLOCK,
    extract_target_path,
    normalize_rel,
    project_root,
    read_stdin_json,
    should_fail_closed,
)


LEDGER_DIR = ".ai/ledger"

_RECOVERY_HINT = (
    "Recovery: delete .ai/ledger/executions.jsonl to reset the ledger, "
    "then re-run the agent executions. The ledger is an audit trail, "
    "not a source of truth for code or governance state."
)


def is_ledger_target(rel: str | None) -> bool:
    if rel is None:
        return False
    return rel == LEDGER_DIR or rel.startswith(LEDGER_DIR + "/")


def is_append_only(new_content: str, existing_content: str) -> bool:
    """新内容是否是现有内容的纯追加（不改已有行）。"""
    if not existing_content:
        return True
    return new_content.startswith(existing_content)


def is_edit_operation(hook_input: dict) -> bool:
    """检测是否为 Edit 操作（非 Write）。"""
    ti = hook_input.get("tool_input") or {}
    # Edit 发送 old_string + new_string；Write 发送 content
    return "old_string" in ti and "new_string" in ti


def verify_ledger_chain(new_content: str) -> tuple[bool, str]:
    """校验 JSONL 文件的 chain_hash 链。

    chain_hash = SHA256(上一条.chain_hash || 本条不含chain_hash的JSON)
    """
    import hashlib

    root_hash = hashlib.sha256(
        b"LOOP_ENGINE_EXECUTION_LEDGER_V1_ROOT"
    ).hexdigest()

    lines = [l.strip() for l in new_content.splitlines() if l.strip()]
    if not lines:
        return True, "empty ledger"

    prev = root_hash
    for i, line in enumerate(lines, 1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            return False, f"line {i}: invalid JSON — {e}"

        chain_key = "chain_hash"
        stored = entry.pop(chain_key, None)
        if stored is None:
            return False, f"line {i}: missing chain_hash"

        row_json = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        computed = hashlib.sha256(
            prev.encode() + row_json.encode("utf-8")
        ).hexdigest()

        if computed != stored:
            return False, (
                f"line {i}: chain broken — "
                f"computed {computed[:16]}..., stored {stored[:16]}..."
            )
        prev = stored

    return True, f"chain verified ({len(lines)} entries)"


def main():
    return _main()


def _main():
    try:
        hook_input = read_stdin_json()
        root = project_root(hook_input)

        target = extract_target_path(hook_input)
        rel = normalize_rel(root, target) if target else None

        if not is_ledger_target(rel):
            return EXIT_PASS

        # ── 对 .ai/ledger/ 下的文件强制校验 ──

        # 检查 0：Edit 工具不可用于 ledger
        if is_edit_operation(hook_input):
            logger.warning(
                "BLOCKED: Edit tool cannot be used on ledger file '%s'. "
                "Ledger files are append-only. Use the Write tool to append new entries. "
                "%s",
                rel, _RECOVERY_HINT,
            )
            return EXIT_BLOCK

        tool_input = hook_input.get("tool_input") or {}

        # 获取即将写入的内容
        new_content = tool_input.get("content") or ""

        # 读取当前文件内容
        target_path = root / rel
        existing = ""
        if target_path.exists():
            try:
                existing = target_path.read_text(encoding="utf-8")
            except OSError:
                pass

        # 检查 1：禁止截断/覆盖
        if existing and (not new_content or len(new_content) < len(existing)):
            logger.warning(
                "BLOCKED: truncation or overwrite of ledger file '%s' detected. "
                "Ledger files accept only append operations. "
                "%s",
                rel, _RECOVERY_HINT,
            )
            return EXIT_BLOCK

        # 检查 2：追加写
        if existing and new_content and not is_append_only(new_content, existing):
            logger.warning(
                "BLOCKED: non-append write to ledger file '%s'. "
                "New content must contain all existing entries plus new ones. "
                "%s",
                rel, _RECOVERY_HINT,
            )
            return EXIT_BLOCK

        # 检查 3：chain hash 连续
        if new_content:
            valid, reason = verify_ledger_chain(new_content)
            if not valid:
                logger.warning(
                    "BLOCKED: ledger chain verification failed for '%s': %s. "
                    "%s",
                    rel, reason, _RECOVERY_HINT,
                )
                return EXIT_BLOCK

        return EXIT_PASS

    except Exception:
        if should_fail_closed(root):
            return EXIT_BLOCK
        return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
