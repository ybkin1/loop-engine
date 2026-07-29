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

    # T-0078 P0: 语义规则检查
    try:
        semantic_rules = load_semantic_rules(root)
        if semantic_rules and target:
            target_path = str(Path(root) / target) if not Path(target).is_absolute() else target
            rel_path = str(Path(target_path).relative_to(root)) if target_path.startswith(str(root)) else target
            content_to_check = hook_input.get("tool_input", {}).get("content", "")
            if content_to_check:
                findings = check_semantic_rules(content_to_check, rel_path, semantic_rules)
                suspense_findings = check_suspense_boundary(content_to_check, rel_path, semantic_rules)
                all_findings = findings + suspense_findings
                blockers = [f for f in all_findings if f["severity"] == "BLOCKER"]
                warnings = [f for f in all_findings if f["severity"] == "WARNING"]
                for w in warnings:
                    logger.warning("[SEMANTIC] %s: %s (fix: %s)", w["rule_id"], w["message"][:120], w.get("fix_suggestion", "")[:80])
                for b in blockers:
                    logger.error("[SEMANTIC BLOCKER] %s: %s (fix: %s)", b["rule_id"], b["message"][:120], b.get("fix_suggestion", "")[:80])
                if blockers:
                    logger.warning("BLOCKED: 语义规则检查发现 %d 个 BLOCKER", len(blockers))
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
