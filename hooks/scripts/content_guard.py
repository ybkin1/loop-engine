#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""content_guard.py — ZCode PreToolUse hook：内容质量拦截。

对 Write/Edit 操作执行：
1. 编码规范检查（ruff check）
2. 禁止硬编码密钥（正则扫描）
3. 架构合规检查（新文件路径校验）

退出码：0 = 放行；2 = 阻断。
"""

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING, format='[%(name)s] %(levelname)s: %(message)s')

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from hook_common import (
    extract_target_path,
    is_governance_project,
    load_config,
    normalize_rel,
    project_root,
    read_stdin_json,
)

EXIT_PASS = 0
EXIT_BLOCK = 2

# —— 硬编码密钥检测模式 ——————————————————————————————
_SECRET_PATTERNS = [
    (re.compile(r'(?:password|passwd|pwd)\s*[=:]\s*["\x27](?!\$\{)[^"\x27]+["\x27]', re.IGNORECASE), "硬编码密码"),
    (re.compile(r'(?:api[_-]?key|apikey)\s*[=:]\s*["\x27](?!\$\{)[^"\x27]{8,}["\x27]', re.IGNORECASE), "硬编码 API Key"),
    (re.compile(r'(?:secret|token|auth[_-]?token)\s*[=:]\s*["\x27](?!\$\{)[^"\x27]{8,}["\x27]', re.IGNORECASE), "硬编码密钥/Token"),
    (re.compile(r'(?:private[_-]?key|privkey)\s*[=:]\s*["\x27](?!\$\{)[^"\x27]{20,}["\x27]', re.IGNORECASE), "硬编码私钥"),
    (re.compile(r'(?:access[_-]?key)\s*[=:]\s*["\x27](?!\$\{)[^"\x27]{8,}["\x27]', re.IGNORECASE), "硬编码 Access Key"),
]


def _is_governance_path(rel):
    return rel.replace("\\", "/").startswith(".ai/")


def _run_ruff_check(file_path):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", file_path, "--output-format", "text"],
            capture_output=True, text=True, timeout=30,
        )
        output = result.stdout.strip()
        if result.returncode == 0 or not output:
            return True, []
        return False, [line.strip() for line in output.split("\n") if line.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True, []
    except Exception as _e:
        import logging; logging.getLogger("content_guard").warning("%s check failed: %s", "content_guard", _e)
        return True, []


def _scan_secrets(content):
    violations = []
    for line_no, line in enumerate(content.split("\n"), 1):
        for pattern, name in _SECRET_PATTERNS:
            if pattern.search(line):
                violations.append(f"L{line_no}: {name} — {line.strip()[:80]}")
    return violations


def _check_architecture_compliance(root, target_rel):
    arch_doc = root / "docs" / "02-architecture.md"
    if not arch_doc.exists():
        return True, []
    try:
        arch_content = arch_doc.read_text(encoding="utf-8")
    except Exception as _e:
        import logging; logging.getLogger("content_guard").warning("%s check failed: %s", "content_guard", _e)
        return True, []
    known_modules = set()
    mod_pat = re.compile(r'[\-*]\s+`?([a-zA-Z_][\w/]*\.py)`?')
    dir_pat = re.compile(r'[\-*]\s+`?([a-zA-Z_][\w/]+/)`?')
    for line in arch_content.split("\n"):
        m = mod_pat.search(line) or dir_pat.search(line)
        if m:
            known_modules.add(m.group(1))
    if not known_modules:
        return True, []
    nt = target_rel.replace("\\", "/")
    for m in known_modules:
        mn = m.replace("\\", "/")
        if nt.startswith(mn.rstrip("/")):
            return True, []
        if mn.endswith("/") and nt.startswith(mn):
            return True, []
    return False, [f"文件 '{nt}' 不在架构设计定义的模块中"]


def main():
    try:
        hook_input = read_stdin_json()
    except Exception as _e:
        import logging; logging.getLogger("content_guard").warning("%s fatal: %s", "content_guard", _e)
        return EXIT_PASS

    root = project_root()
    if not root or not is_governance_project(root):
        return EXIT_PASS

    config = load_config(root)
    cc = config.get("content_guard", {})
    if not cc.get("enabled", True):
        return EXIT_PASS

    tool_name = str(hook_input.get("tool_name", ""))
    if tool_name not in ("Write", "Edit"):
        return EXIT_PASS

    target_path = extract_target_path(hook_input)
    if not target_path:
        return EXIT_PASS

    rel = normalize_rel(root, target_path)
    if not rel or _is_governance_path(rel) or not rel.endswith(".py"):
        return EXIT_PASS

    tool_input = hook_input.get("tool_input", {})
    if tool_name == "Write":
        content = tool_input.get("content", "")
    elif tool_name == "Edit":
        content = tool_input.get("new_string", "")
    else:
        return EXIT_PASS

    if not content:
        return EXIT_PASS

    violations = []
    fail_on_error = cc.get("fail_on_checker_error", False)

    # 1. Lint check
    if cc.get("checks", {}).get("lint", True):
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(content)
                tmp_path = f.name
            ok, v = _run_ruff_check(tmp_path)
            if not ok:
                violations.extend(f"[编码规范] {x}" for x in v[:10])
        except Exception as e:
            if fail_on_error:
                violations.append(f"[编码规范] 检查失败: {e}")
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    # 2. Secrets scan
    if cc.get("checks", {}).get("secrets", True):
        violations.extend(f"[安全] {x}" for x in _scan_secrets(content))

    # 3. Architecture compliance (new files only)
    if cc.get("checks", {}).get("architecture", True):
        if not (root / rel).exists():
            ok, v = _check_architecture_compliance(root, rel)
            if not ok:
                violations.extend(f"[架构合规] {x}" for x in v)

    if violations:
        msg = (
            "=== content_guard: 内容质量检查未通过 ===\n"
            f"文件: {rel}\n"
            + "\n".join(violations)
            + f"\n共 {len(violations)} 项违规。请修复后重试。"
        )
        logger.warning(msg)
        print(json.dumps({"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason": msg}}))
        return EXIT_BLOCK

    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
