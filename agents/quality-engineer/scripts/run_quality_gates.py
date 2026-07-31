#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_quality_gates.py — 质量门禁编排脚本（LEGACY WRAPPER）。

LEGACY WRAPPER — delegates to loop_core canonical APIs; retained for
evidence-format compatibility.

B4 (T-0083) single-source consolidation: 本脚本仍是 quality-engineer 角色调用、
并产出 enforcement hook 所需 quality_report.json 的运营链路。为避免
"deprecated 脚本" 与 "canonical API" 双实现漂移（gap-analysis §3.3），
本脚本现在把 loop_core.static_analyzer.analyze_project() 与
loop_core.security_scanner.scan_security() 的规范结果折入同一份报告
（static_analysis + security 两个 check），使 legacy 脚本与 canonical API
产出 ONE consistent report。

确定性代码，不依赖 LLM。被质量工程师 agent 通过 Bash 调用。
读取项目 config.yaml 的 quality_gates 节，依次运行各检查工具，
解析输出，与阈值对比，生成结构化质量报告。

用法：
    python run_quality_gates.py [--project-root <dir>] [--output-dir <dir>]

输出文件（写入 --output-dir 或 .ai/evidence/quality/）：
    quality_report.json  — 机器可读（给 hook/validator 用）
    quality_summary.md   — 人可读（给用户看）

退出码：0 = 全 PASS；2 = 有 BLOCKED 项。

配置来源（优先级从高到低）：
    1. 项目根 .zcode/skills/loop-governance/config.yaml 的 quality_gates 节
    2. 项目根 .zcode/skills/loop-governance/config.yaml 的 quality_gates.templates 节（按 project_type 匹配）
    3. 内置默认值
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.dont_write_bytecode = True

# --------------- Canonical status semantics ---------------
# Every quality gate result MUST carry exactly one of these statuses.
# PASS:       check executed and passed threshold
# FAIL:       check executed and did NOT pass threshold
# BLOCKED:    regression detected — must be resolved before proceeding
# UNAVAILABLE: tool or command not configured / not installed — cannot execute
# NOT_VERIFIED: check ran but result cannot be independently verified
# ABSTAIN:    explicit decision not to run this check (e.g., out of scope)

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_BLOCKED = "BLOCKED"
STATUS_UNAVAILABLE = "UNAVAILABLE"
STATUS_NOT_VERIFIED = "NOT_VERIFIED"
STATUS_ABSTAIN = "ABSTAIN"

CANONICAL_STATUSES = frozenset([STATUS_PASS, STATUS_FAIL, STATUS_BLOCKED, STATUS_UNAVAILABLE, STATUS_NOT_VERIFIED, STATUS_ABSTAIN])

# --------------- 默认配置 ---------------

DEFAULT_QUALITY_GATES = {
    "lint_command": None,          # 例: "ruff check --output-format json ."
    "lint_threshold": 0,
    "typecheck_command": None,     # 例: "mypy --strict src/"
    "typecheck_threshold": 0,
    "test_command": None,          # 例: "pytest --cov=src --cov-report=term --tb=short -q"
    "test_threshold": 0,           # 允许的最大失败数
    "coverage_threshold": 80,      # 覆盖率百分比
    "audit_command": None,         # 例: "pip-audit -r requirements.txt --format json"
    "audit_threshold": {"HIGH": 0, "CRITICAL": 0},
    "build_command": None,         # 例: "python -m build"
    "build_threshold": 0,          # exit code 上限
    "compile_command": None,       # 例: "python .ai/checkers/compile_gate.py . --paths loop_core"
    "compile_threshold": 0,        # 允许的最大编译失败文件数
    "project_type": "auto",        # python | javascript | auto
}

# --------------- 解析器 ---------------

def parse_lint_output(raw: str, exit_code: int, command: str) -> Tuple[int, str]:
    """解析 lint 工具输出，返回 (error_count, raw_snippet)。"""
    raw_clean = raw.strip()
    # ruff --output-format json
    if "ruff" in command and raw_clean.startswith("["):
        try:
            items = json.loads(raw_clean)
            return len(items), raw[:500]
        except json.JSONDecodeError:
            pass
    # eslint --format json
    if "eslint" in command and raw_clean.startswith("["):
        try:
            items = json.loads(raw_clean)
            total = sum(len(f.get("messages", [])) for f in items)
            return total, raw[:500]
        except json.JSONDecodeError:
            pass
    # 空 JSON 数组 = 零 error
    if raw_clean == "[]":
        return 0, ""
    # 退化为计数非空行（不包括空行和摘要行）
    lines = [l for l in raw_clean.splitlines() if l.strip() and not l.strip().startswith("Found")]
    return len(lines), raw[:500]


def parse_test_output(raw: str, exit_code: int, command: str) -> Tuple[int, int, int, str, bool]:
    """解析测试输出，返回 (passed, total, coverage_pct, raw_snippet, zero_collected)。

    zero_collected = True 表示测试收集数量为 0——这不等价于"全部通过"，
    通常意味着 pytest 未找到测试文件或收集配置错误。
    """
    coverage = 0
    passed = 0
    total = 0
    zero_collected = False
    raw_clean = raw.strip()

    # pytest --collect-only 风格：检测 "no tests ran" / "collected 0 items"
    import re
    m_collected = re.search(r"collected\s+(\d+)\s+item", raw_clean)
    if m_collected and int(m_collected.group(1)) == 0:
        zero_collected = True

    if "no tests ran" in raw_clean.lower():
        zero_collected = True

    # pytest --cov 输出
    for line in raw_clean.splitlines():
        if "passed" in line and ("failed" in line or "=" in line):
            m_passed = re.search(r"(\d+)\s*passed", line)
            m_failed = re.search(r"(\d+)\s*failed", line)
            if m_passed:
                passed = int(m_passed.group(1))
            if m_failed:
                total = passed + int(m_failed.group(1))
            elif m_passed:
                total = passed  # all passed
        if "TOTAL" in line and "%" in line:
            # coverage.py 的 TOTAL 行
            parts = line.split()
            for p in parts:
                if p.endswith("%"):
                    try:
                        coverage = int(float(p.replace("%", "")))
                    except ValueError:
                        pass

    if total == 0:
        total = passed

    # Zero-collected override: if nothing was collected, total=0 is real
    if zero_collected and total == 0:
        pass  # correct signal

    return passed, total, coverage, raw[:500], zero_collected


def parse_audit_output(exit_code: int, raw: str) -> dict:
    """Parse dependency audit output.

    Returns {LOW: n, MEDIUM: n, MODERATE: n, HIGH: n, CRITICAL: n, blocked: bool}.
    """
    counts = {"LOW": 0, "MEDIUM": 0, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0}

    try:
        data = json.loads(raw)
    except Exception:
        data = None

    if isinstance(data, list):
        # pip-audit --format json: [{name, version, resolved, vulnerabilities:[{id, severity}]}]
        for pkg in data:
            if not isinstance(pkg, dict):
                continue
            for vuln in pkg.get("vulnerabilities", []):
                if not isinstance(vuln, dict):
                    continue
                sev = str(vuln.get("severity", "")).upper()
                if sev in counts:
                    counts[sev] += 1
    elif isinstance(data, dict):
        # npm audit --json: {"vulnerabilities": {name: {"severity": ...}}}
        vulns = data.get("vulnerabilities", {})
        for v in (vulns.values() if isinstance(vulns, dict) else []):
            if isinstance(v, dict):
                sev = str(v.get("severity", "")).upper()
                if sev in counts:
                    counts[sev] += 1

    # JSON 解析失败或未解析出任何漏洞 → 退化：仅按退出码推断
    if not any(counts.get(k) for k in ("LOW", "MEDIUM", "MODERATE", "HIGH", "CRITICAL")):
        if exit_code != 0:
            counts["HIGH"] = max(1, len(raw.splitlines()))

    counts["blocked"] = counts["HIGH"] > 0 or counts["CRITICAL"] > 0
    return counts


def parse_build_output(raw: str, exit_code: int, command: str) -> int:
    """解析构建输出：exit code 0 = pass。"""
    return exit_code


def parse_compile_output(raw: str, exit_code: int, command: str) -> Tuple[int, int, list]:
    """解析编译门禁输出，返回 (compiled_count, failed_count, error_list)。"""
    raw_clean = raw.strip()
    if raw_clean.startswith("{"):
        try:
            data = json.loads(raw_clean)
            compiled = data.get("compiled_files", 0)
            total = data.get("total_files", compiled)
            failed = data.get("failed_count", total - compiled)
            errors = data.get("errors", [])
            return compiled, failed, errors
        except json.JSONDecodeError:
            pass
    # Fallback: use exit code to determine pass/fail
    if exit_code == 0:
        return 0, 0, []
    else:
        return 0, 1, [{"error": raw_clean[:500]}]


# --------------- 核心 ---------------

def load_config(project_root: Path) -> dict:
    """加载 quality_gates 配置，合并默认值。"""
    import yaml  # type: ignore
    cfg_path = project_root / ".zcode" / "skills" / "loop-governance" / "config.yaml"
    gates = dict(DEFAULT_QUALITY_GATES)
    if not cfg_path.exists():
        return gates

    with open(cfg_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    qg = raw.get("quality_gates", {})
    if isinstance(qg, dict):
        # 通用合并
        for key, default in DEFAULT_QUALITY_GATES.items():
            gates[key] = qg.get(key, default)
    # 模板覆盖：按 project_type 匹配
    templates = qg.get("templates", {})
    if isinstance(templates, dict):
        pt = gates.get("project_type", "auto")
        # Auto-detect project type if set to "auto"
        if pt == "auto":
            if (project_root / "pyproject.toml").exists() or (project_root / "setup.py").exists() or (project_root / "requirements.txt").exists():
                pt = "python"
            elif (project_root / "package.json").exists():
                pt = "javascript"
        tmpl = templates.get(pt, templates.get("default", {}))
        if isinstance(tmpl, dict):
            for key, default in DEFAULT_QUALITY_GATES.items():
                if key in tmpl:
                    gates[key] = tmpl[key]

    return gates


def run_one_check(name: str, command: Optional[str], project_root: Path, timeout: int = 120) -> Dict[str, Any]:
    """运行一个检查，返回 {exit_code, stdout, stderr, command, status}。

    T-0083 (AC-07): 工具缺失（FileNotFoundError / "No module named" /
    命令不存在）→ status=BLOCKED + gate_blocked=True + reason=
    "tool missing (fail-closed)"。超时 / 执行错误同样 fail-closed。
    collect_results 据此直接把该项标记为 BLOCKED，避免空输出被解析成
    0 错误而误判 PASS（原 lint/test 的 fail-open 路径）。
    未配置命令（command=None）→ UNAVAILABLE（合法，不阻断）。
    """
    if not command:
        return {"exit_code": 0, "stdout": "", "stderr": "", "skipped": True, "command": None, "status": STATUS_UNAVAILABLE}
    try:
        result = subprocess.run(
            shlex.split(command),
            shell=False,
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=timeout,
        )
        stderr_l = (result.stderr or "").lower()
        missing_marker = (
            "no module named" in stderr_l
            or "not recognized as an internal or external command" in stderr_l
            or "command not found" in stderr_l
        )
        if result.returncode != 0 and missing_marker:
            return {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
                    "skipped": False, "command": command, "status": STATUS_BLOCKED,
                    "gate_blocked": True, "reason": "tool missing (fail-closed)"}
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "skipped": False,
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": f"超时 ({timeout}s)", "skipped": False,
                "command": command, "status": STATUS_BLOCKED, "gate_blocked": True,
                "reason": "check timeout (fail-closed)"}
    except FileNotFoundError as exc:
        return {"exit_code": -1, "stdout": "", "stderr": str(exc), "skipped": False,
                "command": command, "status": STATUS_BLOCKED, "gate_blocked": True,
                "reason": "tool missing (fail-closed)"}
    except Exception as exc:
        return {"exit_code": -1, "stdout": "", "stderr": str(exc), "skipped": False,
                "command": command, "status": STATUS_BLOCKED, "gate_blocked": True,
                "reason": f"tool check execution failed (fail-closed): {exc}"}


def _collect_canonical_checks(project_root: Path) -> List[Dict[str, Any]]:
    """B4 (T-0083): fold loop_core canonical API results into the report.

    Single-source consolidation (gap-analysis §3.3): the legacy script and
    the canonical API now produce ONE consistent report.  Two checks are
    added to every quality run:

    - static_analysis ← loop_core.static_analyzer.analyze_project()
        value = error-finding count; FAIL when errors > 0 (static-analysis
        errors are quality issues, not security blockers).
    - security ← loop_core.security_scanner.scan_security()
        FAIL-CLOSED: critical findings → BLOCKED; high → FAIL; else PASS.

    Both items carry execution_evidence so check_quality_gate_evidence's
    authenticity validation can verify they really ran.
    """
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    # loop_core lives in the loop-engine repo root (this script's
    # great-grandparent dir: scripts → quality-engineer → agents → root) —
    # importable even when scanning a foreign project directory.
    repo_root = str(Path(__file__).resolve().parents[3])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    checks: List[Dict[str, Any]] = []

    try:
        from loop_core.static_analyzer import analyze_project
        sa = analyze_project(project_root)
        checks.append({
            "name": "static_analysis",
            "value": sa.errors,
            "threshold": 0,
            "raw": (f"{len(sa.findings)} findings ({sa.errors} errors, "
                    f"{sa.warnings} warnings) over {sa.files_scanned} files"),
            "exit_code": 0,
            "skipped": False,
            "command": "loop_core.static_analyzer.analyze_project()",
            "status": STATUS_PASS if sa.passed else STATUS_FAIL,
            "reason": ("0 static analysis errors"
                       if sa.passed else f"{sa.errors} static analysis errors"),
            "files_scanned": sa.files_scanned,
            "findings": [
                {"rule_id": f.rule_id, "severity": f.severity, "file": f.file,
                 "line": f.line, "message": f.message}
                for f in sa.findings[:50]
            ],
            "execution_evidence": {
                "exit_code": 0,
                "command": "loop_core.static_analyzer.analyze_project()",
            },
        })
    except Exception as exc:
        checks.append({
            "name": "static_analysis",
            "value": None,
            "threshold": 0,
            "raw": str(exc)[:200],
            "exit_code": -1,
            "skipped": False,
            "command": "loop_core.static_analyzer.analyze_project()",
            "status": STATUS_BLOCKED,
            "reason": f"canonical static_analyzer unavailable (fail-closed): {exc}",
            "execution_evidence": {
                "exit_code": -1,
                "command": "loop_core.static_analyzer.analyze_project()",
            },
        })

    try:
        from loop_core.security_scanner import scan_security
        sec = scan_security(project_root)
        if sec.critical > 0:
            sec_status, sec_reason = STATUS_BLOCKED, (
                f"{sec.critical} critical security findings (fail-closed)")
        elif sec.high > 0:
            sec_status, sec_reason = STATUS_FAIL, f"{sec.high} high security findings"
        else:
            sec_status, sec_reason = STATUS_PASS, "0 critical/high security findings"
        checks.append({
            "name": "security",
            "value": {"critical": sec.critical, "high": sec.high},
            "threshold": {"critical": 0, "high": 0},
            "raw": (f"{len(sec.findings)} findings ({sec.critical} critical, "
                    f"{sec.high} high) over {sec.files_scanned} files"),
            "exit_code": 0,
            "skipped": False,
            "command": "loop_core.security_scanner.scan_security()",
            "status": sec_status,
            "reason": sec_reason,
            "files_scanned": sec.files_scanned,
            "findings": [
                {"rule_id": f.rule_id, "severity": f.severity, "file": f.file,
                 "line": f.line, "message": f.message}
                for f in sec.findings[:50]
            ],
            "execution_evidence": {
                "exit_code": 0,
                "command": "loop_core.security_scanner.scan_security()",
            },
        })
    except Exception as exc:
        checks.append({
            "name": "security",
            "value": None,
            "threshold": {"critical": 0, "high": 0},
            "raw": str(exc)[:200],
            "exit_code": -1,
            "skipped": False,
            "command": "loop_core.security_scanner.scan_security()",
            "status": STATUS_BLOCKED,
            "reason": f"canonical security_scanner unavailable (fail-closed): {exc}",
            "execution_evidence": {
                "exit_code": -1,
                "command": "loop_core.security_scanner.scan_security()",
            },
        })

    return checks


def collect_results(gates: dict, project_root: Path) -> List[Dict[str, Any]]:
    """运行所有配置的检查，收集原始结果。

    T-0083 (AC-07): 配置了命令但工具缺失/无法执行（FileNotFoundError、
    "No module named"、命令不存在、超时、执行错误）→ 该项直接标记为
    BLOCKED（fail-closed），不再用空输出解析成 0 错误而误判 PASS。
    未配置的命令（不在 config 中）不会出现在结果里（等同 NOT_VERIFIED，
    合法不阻断）。
    """
    results = []

    def _blocked(name: str, r: Dict[str, Any], threshold: Any) -> Dict[str, Any]:
        """构造工具无法执行（缺失/超时/错误）的 fail-closed 结果项。"""
        return {
            "name": name,
            "value": None,
            "threshold": threshold,
            "raw": (r.get("stderr") or r.get("stdout") or "")[:200],
            "exit_code": r["exit_code"],
            "skipped": False,
            "command": r.get("command"),
            "status": STATUS_BLOCKED,
            "reason": r.get("reason", "tool check could not execute (fail-closed)"),
        }

    # Lint
    if gates.get("lint_command"):
        r = run_one_check("lint", gates["lint_command"], project_root)
        if r.get("gate_blocked"):
            results.append(_blocked("lint", r, gates.get("lint_threshold", 0)))
        else:
            count, snippet = parse_lint_output(r["stdout"], r["exit_code"], gates["lint_command"])
            results.append({"name": "lint", "value": count, "threshold": gates.get("lint_threshold", 0),
                            "raw": snippet, "exit_code": r["exit_code"], "skipped": r.get("skipped", False),
                            "command": r.get("command")})

    # Typecheck
    if gates.get("typecheck_command"):
        r = run_one_check("typecheck", gates["typecheck_command"], project_root)
        if r.get("gate_blocked"):
            results.append(_blocked("typecheck", r, gates.get("typecheck_threshold", 0)))
        else:
            count = 0 if r["exit_code"] == 0 else 1  # typecheck 简化为 0/1
            results.append({"name": "typecheck", "value": count, "threshold": gates.get("typecheck_threshold", 0),
                            "raw": r["stdout"][:300], "exit_code": r["exit_code"], "skipped": r.get("skipped", False),
                            "command": r.get("command")})

    # Test + Coverage
    if gates.get("test_command"):
        r = run_one_check("test", gates["test_command"], project_root, timeout=180)
        if r.get("gate_blocked"):
            results.append(_blocked("test", r, gates.get("test_threshold", 0)))
        else:
            passed, total, cov, snippet, zero_collected = parse_test_output(r["stdout"], r["exit_code"], gates["test_command"])
            results.append({"name": "test", "value": f"{passed}/{total}", "threshold": gates.get("test_threshold", 0),
                            "raw": snippet, "exit_code": r["exit_code"], "skipped": r.get("skipped", False),
                            "command": r.get("command"), "zero_collected": zero_collected})
            results.append({"name": "coverage", "value": cov, "threshold": gates.get("coverage_threshold", 80),
                            "raw": f"{cov}%", "exit_code": r["exit_code"], "skipped": r.get("skipped", False),
                            "command": r.get("command")})

    # Audit
    if gates.get("audit_command"):
        r = run_one_check("audit", gates["audit_command"], project_root)
        if r.get("gate_blocked"):
            results.append(_blocked("audit", r, gates.get("audit_threshold", {"HIGH": 0})))
        else:
            counts = parse_audit_output(r["exit_code"], r["stdout"])
            results.append({"name": "audit", "value": counts, "threshold": gates.get("audit_threshold", {"HIGH": 0}),
                            "raw": r["stdout"][:300], "exit_code": r["exit_code"], "skipped": r.get("skipped", False),
                            "command": r.get("command")})

    # Build
    if gates.get("build_command"):
        r = run_one_check("build", gates["build_command"], project_root)
        if r.get("gate_blocked"):
            results.append(_blocked("build", r, gates.get("build_threshold", 0)))
        else:
            code = parse_build_output(r["stdout"], r["exit_code"], gates["build_command"])
            results.append({"name": "build", "value": code, "threshold": gates.get("build_threshold", 0),
                            "raw": r["stdout"][:200], "exit_code": code, "skipped": r.get("skipped", False),
                            "command": r.get("command")})

    # Compile
    if gates.get("compile_command"):
        r = run_one_check("compile", gates["compile_command"], project_root, timeout=120)
        if r.get("gate_blocked"):
            results.append(_blocked("compile", r, gates.get("compile_threshold", 0)))
        else:
            compiled, failed, error_list = parse_compile_output(r["stdout"], r["exit_code"], gates["compile_command"])
            results.append({"name": "compile", "value": failed, "threshold": gates.get("compile_threshold", 0),
                            "raw": json.dumps(error_list)[:300] if error_list else "0 errors",
                            "exit_code": r["exit_code"], "skipped": r.get("skipped", False),
                            "compiled_files": compiled, "command": r.get("command")})

    # B4 (T-0083): canonical loop_core checks — single source of truth.
    # The legacy CLI chain and loop_core.static_analyzer / security_scanner
    # now fold into ONE report (gap-analysis §3.3).
    results.extend(_collect_canonical_checks(project_root))

    return results


def generate_report(results: List[Dict[str, Any]], project_root: Path, output_dir: Path) -> Tuple[str, List[str]]:
    """生成 quality_report.json 和 quality_summary.md，返回 (overall, blocked_by)。"""
    # ensure scripts dir is importable (caller may be in any cwd)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from check_thresholds import check

    checks_out = []
    blocked_by = []

    for r in results:
        if r.get("status") in CANONICAL_STATUSES:
            # Pre-computed status (B4 canonical loop_core checks, or
            # fail-closed tool blocks): honor it verbatim instead of
            # routing unknown check names through check() (which would
            # have turned a canonical FAIL into a spurious PASS).
            item = {
                "name": r["name"],
                "status": r["status"],
                "value": r.get("value"),
                "threshold": r.get("threshold"),
                "reason": r.get("reason", ""),
            }
        else:
            item = check(r["name"], r["value"], r["threshold"])
        item["raw"] = r.get("raw", "")[:200]
        item["skipped"] = r.get("skipped", False)
        item["command"] = r.get("command")
        # Propagate execution_evidence (B4: lets check_quality_gate_evidence
        # verify canonical checks really ran; tolerated for legacy items
        # that omit it)
        if r.get("execution_evidence"):
            item["execution_evidence"] = r["execution_evidence"]
        # Propagate canonical finding detail for machine consumers
        if r.get("findings"):
            item["findings"] = r["findings"]
        if r.get("files_scanned"):
            item["files_scanned"] = r["files_scanned"]
        # Propagate zero_collected if present
        if r.get("zero_collected"):
            item["zero_collected"] = True
            if item["status"] == STATUS_PASS:
                item["status"] = STATUS_FAIL
                item["reason"] = (item.get("reason", "") + "; zero tests collected").strip("; ")
        checks_out.append(item)
        if item["status"] in (STATUS_BLOCKED, STATUS_FAIL):
            blocked_by.append(f"{r['name']}: {item.get('reason', 'unknown')}")

    overall = STATUS_PASS if not blocked_by else STATUS_BLOCKED

    # 计算源码树 SHA256（用于证据链绑定）
    src_hash = _compute_src_hash(project_root)

    # JSON report
    report = {
        "schema": "quality_report/v1",
        "role": "quality-engineer",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": str(project_root.resolve()),
        "checks": checks_out,
        "overall": overall,
        "blocked_by": blocked_by,
        "input_hashes": {
            "source_code": f"sha256:{src_hash}" if src_hash else "unavailable",
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "quality_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown summary
    md_lines = [
        f"# 质量报告 · {project_root.name} · {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "| 检查项 | 结果 | 门槛 | 状态 |",
        "|--------|------|------|------|",
    ]
    for item in checks_out:
        status_icon = "✅" if item["status"] in ("pass", STATUS_PASS) else ("❌" if item["status"] in ("blocked", "fail", STATUS_BLOCKED, STATUS_FAIL) else "⚠️")
        value_str = str(item.get("value", "—"))
        thresh_str = str(item.get("threshold", "—"))
        if isinstance(value_str, dict):
            value_str = json.dumps(value_str)
        if isinstance(thresh_str, dict):
            thresh_str = json.dumps(thresh_str)
        md_lines.append(f"| {item['name']} | {value_str} | {thresh_str} | {status_icon} |")

    md_lines.append("")
    md_lines.append(f"**结论：{overall}**")
    if blocked_by:
        md_lines.append("")
        md_lines.append("## 阻断项")
        for b in blocked_by:
            md_lines.append(f"- {b}")
    else:
        md_lines.append("")
        md_lines.append("全部检查通过，质量门放行。")

    md_path = output_dir / "quality_summary.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return overall, blocked_by


def main():
    parser = argparse.ArgumentParser(description="运行质量门禁检查")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--output-dir", default=None, help="报告输出目录（默认 .ai/evidence/quality/）")
    parser.add_argument("--json", action="store_true", help="同时输出 JSON 到 stdout")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    output_dir = Path(args.output_dir) if args.output_dir else project_root / ".ai" / "evidence" / "quality"

    gates = load_config(project_root)
    results = collect_results(gates, project_root)
    overall, blocked_by = generate_report(results, project_root, output_dir)

    if args.json:
        json_report = output_dir / "quality_report.json"
        if json_report.exists():
            print(json_report.read_text(encoding="utf-8"))

    if overall == "BLOCKED":
        print(f"\n[quality-engineer] BLOCKED — {len(blocked_by)} 项不合格:", file=sys.stderr)
        for b in blocked_by:
            print(f"  - {b}", file=sys.stderr)
        sys.exit(2)
    else:
        print("\n[quality-engineer] PASS — 全部质量门通过")
        sys.exit(0)


def _compute_src_hash(project_root: Path) -> str:
    """计算源码树 SHA256（排除 .ai/ .git/ node_modules/ __pycache__ 等目录）。"""
    import hashlib
    src_dir = project_root / "src"
    if not src_dir.is_dir():
        return ""
    h = hashlib.sha256()
    exclude = {"__pycache__", ".git", "node_modules", ".venv", "venv", "dist", "build", ".ai"}
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = sorted(d for d in dirs if d not in exclude and not d.startswith("."))
        for fname in sorted(files):
            fpath = Path(root) / fname
            try:
                h.update(fpath.read_bytes())
                h.update(fname.encode())
            except (OSError, PermissionError):
                pass
    return h.hexdigest()


if __name__ == "__main__":
    main()
