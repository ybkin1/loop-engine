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
    EXIT_PASS,
    EXIT_BLOCK,
    extract_target_path,
    is_governance_project,
    load_config,
    normalize_rel,
    project_root,
    read_stdin_json,
)


# —— 硬编码密钥检测模式 ——————————————————————————————
_SECRET_PATTERNS = [
    (re.compile(r'(?:password|passwd|pwd)\s*[=:]\s*["\x27](?!\$\{)[^"\x27]+["\x27]', re.IGNORECASE), "硬编码密码"),
    (re.compile(r'(?:api[_-]?key|apikey)\s*[=:]\s*["\x27](?!\$\{)[^"\x27]{8,}["\x27]', re.IGNORECASE), "硬编码 API Key"),
    (re.compile(r'(?:secret|token|auth[_-]?token)\s*[=:]\s*["\x27](?!\$\{)[^"\x27]{8,}["\x27]', re.IGNORECASE), "硬编码密钥/Token"),
    (re.compile(r'(?:private[_-]?key|privkey)\s*[=:]\s*["\x27](?!\$\{)[^"\x27]{20,}["\x27]', re.IGNORECASE), "硬编码私钥"),
    (re.compile(r'(?:access[_-]?key)\s*[=:]\s*["\x27](?!\$\{)[^"\x27]{8,}["\x27]', re.IGNORECASE), "硬编码 Access Key"),
]

# —— 注入/动态执行检查模式（T-0082 Phase 5 GAP-4c，镜像 security_scanner SS-010/SS-011）——
# 元组: (pattern, rule_id, severity, description)。severity=high 阻断，medium 仅记录。
_EDIT_INJECTION_PATTERNS = [
    (re.compile(r'os\.system\s*\(|subprocess\.(?:call|run|Popen)\s*\(|os\.popen\s*\('),
     "SS-010", "medium", "OS command execution"),
    (re.compile(r'(?:exec|eval)\s*\(\s*["\x27][^"\x27]*\{'),
     "SS-011", "high", "Dynamic code execution with interpolation"),
]


def _is_governance_path(rel):
    return rel.replace("\\", "/").startswith(".ai/")


def _run_ruff_check(file_path):
    try:
        # T-0082 Phase 5 GAP-1: ruff >= 0.15 移除了 --output-format text（rc=2 +
        # 空 stdout 导致 lint 检查永远放行）。改用 concise；老版本 ruff 仍支持
        # text，检测到 "invalid value" 时回退。
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", file_path, "--output-format", "concise"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 2 and "invalid value" in (result.stderr or ""):
            result = subprocess.run(
                [sys.executable, "-m", "ruff", "check", file_path, "--output-format", "text"],
                capture_output=True, text=True, timeout=30,
            )
        output = (result.stdout or "").strip()
        if result.returncode == 0:
            return True, []
        if not output:
            # T-0083 (AC-06): fail-closed（was fail-open）。rc≠0 + 无输出通常
            # 意味着模块缺失（"No module named ruff"）或工具本身故障——
            # 语法/质量检查无法执行时必须阻断，不能当成"零违规"放行。
            return False, [
                f"ruff 检查执行失败（rc={result.returncode}，无输出）："
                "语法/质量检查无法执行（fail-closed）"
            ]
        return False, [line.strip() for line in output.split("\n") if line.strip()]
    except FileNotFoundError:
        # T-0083 (AC-06): fail-closed（was fail-open）。ruff 不可用 → 阻断。
        return False, ["ruff 不可用：语法/质量检查无法执行（fail-closed）"]
    except subprocess.TimeoutExpired:
        # T-0083 (AC-06): fail-closed（was fail-open）。超时 → 阻断。
        return False, ["ruff 检查超时：语法/质量检查无法执行（fail-closed）"]
    except Exception as _e:
        # T-0083 (AC-06): fail-closed（was fail-open）。执行异常 → 阻断。
        logging.getLogger("content_guard").warning("%s check failed: %s", "content_guard", _e)
        return False, [f"ruff 检查执行异常：{_e}（fail-closed）"]


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
        logging.getLogger("content_guard").warning("%s check failed: %s", "content_guard", _e)
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
        logging.getLogger("content_guard").warning("%s fatal: %s", "content_guard", _e)
        return EXIT_PASS

    # T-0082 Phase 5 GAP-1: 原代码 project_root() 缺少 hook_input 实参，
    # 导致 TypeError 使整个 hook 在启动时即崩溃（所有检查从未运行）。
    root = project_root(hook_input)
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

    # T-0082 Phase 5 GAP-4b: Edit 应检查合并后的完整文件内容（而非仅 new_string）。
    # 从磁盘读取原文件，应用 old_string → new_string 替换，lint 合并结果。
    # old_string 未找到 → 跳过合并 lint（记录 warning）；IO 失败 → 回退到仅检查 new_string。
    merged_content = None
    if tool_name == "Edit":
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")
        target_file = root / rel
        try:
            if target_file.exists():
                original = target_file.read_text(encoding="utf-8")
                if old_string and old_string in original:
                    merged_content = original.replace(old_string, new_string, 1)
                else:
                    logger.warning(
                        "content_guard: old_string 未在 %s 中找到，跳过合并后 lint", rel
                    )
                    merged_content = new_string
            else:
                merged_content = new_string
        except Exception as e:
            logger.warning(
                "content_guard: 读取 %s 失败（%s），回退到仅检查 new_string", rel, e
            )
            merged_content = new_string

    # 语义规则检查用合并内容（Edit 时），Write 时即完整内容
    semantic_content = merged_content if merged_content is not None else content
    # lint 检查合并后的完整文件（Edit 时避免新旧代码相互破坏）；
    # 密钥/注入检查只针对本次新增内容（new_string / content）
    lint_content = merged_content if merged_content is not None else content

    violations = []
    fail_on_error = cc.get("fail_on_checker_error", False)

    # 1. Lint check（Edit 时检查合并后的文件内容）
    if cc.get("checks", {}).get("lint", True):
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(lint_content)
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

    # 2b. 注入/动态执行检查（T-0082 Phase 5 GAP-4c）
    # 只检查本次新增内容；SS-011(high) 阻断，SS-010(medium) 仅记录 warning。
    if cc.get("checks", {}).get("injection", True):
        for line_no, line in enumerate(content.split("\n"), 1):
            for pattern, rule_id, severity, desc in _EDIT_INJECTION_PATTERNS:
                if pattern.search(line):
                    if severity == "high":
                        violations.append(
                            f"[安全-注入] L{line_no}: {rule_id}({severity}) {desc} — {line.strip()[:80]}"
                        )
                    else:
                        logger.warning(
                            "[安全-参考] L%d: %s(%s) %s — %s",
                            line_no, rule_id, severity, desc, line.strip()[:80],
                        )

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

    # T-0078 P0: 语义规则检查（T-0082 Phase 5 GAP-1 修复）
    # 原实现引用了未定义变量 `target`（NameError 被 except Exception 吞掉），
    # 导致 load_semantic_rules / check_semantic_rules / check_suspense_boundary
    # 从未真正执行。现在使用 main() 已计算好的相对路径 `rel` 与内容。
    try:
        semantic_rules = load_semantic_rules(root)
        if semantic_rules and rel:
            all_findings = check_semantic_rules(semantic_content, rel, semantic_rules)
            all_findings += check_suspense_boundary(semantic_content, rel, semantic_rules)
            blockers = [f for f in all_findings if str(f.get("severity", "")).upper() == "BLOCKER"]
            warnings = [f for f in all_findings if str(f.get("severity", "")).upper() == "WARNING"]
            for w in warnings:
                logger.warning(
                    "[SEMANTIC] %s: %s (fix: %s)",
                    w["rule_id"], w["message"][:120], w.get("fix_suggestion", "")[:80],
                )
            for b in blockers:
                logger.error(
                    "[SEMANTIC BLOCKER] %s: %s (fix: %s)",
                    b["rule_id"], b["message"][:120], b.get("fix_suggestion", "")[:80],
                )
            if blockers:
                msg = (
                    "=== content_guard: 语义规则检查未通过 ===\n"
                    f"文件: {rel}\n"
                    + "\n".join(
                        f"[SEMANTIC {b.get('severity', '?')}] {b['rule_id']}: {b['message']}"
                        for b in blockers[:10]
                    )
                    + f"\n共 {len(blockers)} 个 BLOCKER。请修复后重试。"
                )
                logger.warning(msg)
                print(json.dumps({
                    "hookSpecificOutput": {
                        "permissionDecision": "deny",
                        "permissionDecisionReason": msg,
                    }
                }))
                return EXIT_BLOCK
    except Exception as e:
        logger.debug("语义规则检查异常（非阻塞）: %s", e)

    return EXIT_PASS


def load_semantic_rules(project_root: Path) -> dict:
    """加载 .ai/checks/ 目录下的语义检查规则文件。
    
    T-0078 P0: Domain-specific code logic checks.
    返回 {framework_name: {rules: [...], config: {...}}}
    """
    rules_dir = project_root / ".ai" / "checks"
    if not rules_dir.is_dir():
        return {}
    import yaml
    result = {}
    for rule_file in sorted(rules_dir.glob("*.rules.yaml")):
        try:
            data = yaml.safe_load(rule_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "rules" in data:
                framework = rule_file.stem.replace(".rules", "")
                result[framework] = data
        except Exception:
            continue
    return result


def check_semantic_rules(content: str, file_path: str, rules: dict) -> list[dict]:
    """对文件内容运行语义规则检查。
    
    T-0078 P0: 返回匹配的规则列表 [{rule_id, severity, message, fix_suggestion}]
    """
    import re
    from fnmatch import fnmatch
    findings = []
    for framework, rule_set in rules.items():
        for rule in rule_set.get("rules", []):
            glob_pattern = rule.get("glob", "**/*")
            # 匹配文件路径
            if not fnmatch(file_path.replace("\\", "/"), glob_pattern):
                continue
            # 排除 glob
            exclude = rule.get("exclude_glob")
            if exclude and fnmatch(file_path.replace("\\", "/"), exclude):
                continue
            # 模式匹配
            pattern = rule.get("pattern")
            if not pattern:
                continue
            try:
                if re.search(pattern, content):
                    findings.append({
                        "rule_id": rule["id"],
                        "severity": rule.get("severity", "WARNING"),
                        "message": " ".join(rule.get("message", "").split()),
                        "fix_suggestion": rule.get("fix_suggestion", ""),
                        "knowledge_case": rule.get("knowledge_case"),
                    })
            except re.error:
                continue
    return findings


def check_suspense_boundary(content: str, file_path: str, rules: dict) -> list[dict]:
    """检查 useSearchParams 是否有 Suspense 包裹 (NX-004)。"""
    import re
    from fnmatch import fnmatch
    findings = []
    for framework, rule_set in rules.items():
        for rule in rule_set.get("rules", []):
            if not rule.get("require_suspense_boundary"):
                continue
            glob_pattern = rule.get("glob", "**/*")
            if not fnmatch(file_path.replace("\\", "/"), glob_pattern):
                continue
            pattern = rule.get("pattern")
            if not pattern:
                continue
            if re.search(pattern, content):
                # 检查同一文件中是否有 Suspense 包裹
                if "<Suspense" not in content:
                    findings.append({
                        "rule_id": rule["id"],
                        "severity": rule.get("severity", "BLOCKER"),
                        "message": " ".join(rule.get("message", "").split()),
                        "fix_suggestion": rule.get("fix_suggestion", ""),
                        "knowledge_case": rule.get("knowledge_case"),
                    })
    return findings


if __name__ == "__main__":
    sys.exit(main())
