"""T-0117 契约测试：security_report/v1 双实现收敛。

验证要点：
1. build_v1_report / validate_v1_report 单一 schema 定义可用
2. SecurityReport.to_v1_report 符合 v1 结构（判定映射 critical/high → BLOCKED）
3. loop_core CLI（python -m loop_core.security_scanner）输出 v1 + 退出码 0/2
4. run_security_scan.py --json 输出符合 v1（MCP 契约兼容）
5. SCANNER_SELF_FILES 无已删工具路径残留（T-0113 P3-5）
6. "security_report/v1" schema 字面量仅 loop_core 单一定义（无第二套顶层 schema）
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from loop_core.security_scanner import (  # noqa: E402
    SECURITY_REPORT_V1_SCHEMA,
    SECURITY_REPORT_V1_FIELDS,
    SecurityReport,
    SecurityScanner,
    SecFinding,
    build_v1_report,
    cli_exit_code,
    scan_security,
    validate_v1_report,
)
from loop_core.verdicts import Verdict  # noqa: E402


# ── 1. 单一 schema 定义 ────────────────────────────────────────────────────

def test_single_schema_definition():
    """security_report/v1 字面量应仅在 loop_core/security_scanner.py 定义一次，
    其余引用方（run_security_scan.py）通过 import 获取。"""
    scanner_src = (PROJECT / "loop_core" / "security_scanner.py").read_text(encoding="utf-8")
    literal_count = scanner_src.count('"security_report/v1"') + scanner_src.count("'security_report/v1'")
    assert literal_count >= 1, "loop_core 必须定义 schema 字面量"
    runner_src = (PROJECT / "agents" / "security-engineer" / "scripts" / "run_security_scan.py").read_text(encoding="utf-8")
    assert '"security_report/v1"' not in runner_src, "run_security_scan.py 不得再定义 schema 字面量"
    assert "build_v1_report" in runner_src and "validate_v1_report" in runner_src


def test_build_and_validate_v1():
    """build_v1_report 输出结构与 validate_v1_report 校验。"""
    report = build_v1_report(role="security-engineer", project=str(PROJECT),
                             scans=[{"name": "secret_scan", "status": "pass"}],
                             overall="PASS", blocked_by=[])
    assert validate_v1_report(report)
    assert report["schema"] == SECURITY_REPORT_V1_SCHEMA
    assert report["overall"] == "PASS"
    assert isinstance(report["timestamp"], str) and report["timestamp"]

    bad = dict(report)
    bad["overall"] = "MAYBE"
    assert not validate_v1_report(bad)
    missing = {k: v for k, v in report.items() if k != "scans"}
    assert not validate_v1_report(missing)
    assert not validate_v1_report("not-a-dict")


def test_cli_exit_code_mapping():
    """CLI 退出码统一口径：BLOCKED→2，PASS→0（fail-closed）。"""
    assert cli_exit_code({"overall": "BLOCKED"}) == 2
    assert cli_exit_code({"overall": "PASS"}) == 0


# ── 2. SecurityReport.to_v1_report 判定映射 ────────────────────────────────

def _report_with(severity: str) -> SecurityReport:
    rep = SecurityReport(files_scanned=1)
    rep.findings.append(SecFinding(rule_id="SS-001", severity=severity,
                                   file="src/main.py", line=1, message="x"))
    rep.bind(task_id="T-test", phase="S6-delivery")
    return rep


def test_to_v1_report_pass_mapping():
    rep = _report_with("low")
    v1 = rep.to_v1_report(project=str(PROJECT))
    assert validate_v1_report(v1)
    assert v1["overall"] == "PASS"
    assert v1["blocked_by"] == []
    assert v1["scans"][0]["name"] == "secret_scan"
    assert v1["scans"][0]["status"] == "pass"
    assert v1["scans"][0]["counts"] == {"CRITICAL": 0, "HIGH": 0}


def test_to_v1_report_blocked_mapping():
    """critical/high → overall BLOCKED（fail-closed，含 high 映射 exit 2）。"""
    for severity, expected in (("critical", "BLOCKED"), ("high", "BLOCKED")):
        v1 = _report_with(severity).to_v1_report(project=str(PROJECT))
        assert v1["overall"] == expected
        assert v1["blocked_by"] == ["secret_scan"]
        assert v1["scans"][0]["status"] == "blocked"
        assert cli_exit_code(v1) == 2


def test_to_dict_unchanged_add_only():
    """to_dict 保持不变（add-only 兼容，既有消费方零破坏）。"""
    rep = _report_with("low")
    d = rep.to_dict()
    assert "schema" not in d  # to_dict 不带 v1 schema（内部结构保持）
    assert "findings_contract" in d and "verdict" in d
    assert d["verdict"] == Verdict.PASS.value


# ── 3. loop_core CLI ───────────────────────────────────────────────────────

def _run_py(args: list[str], timeout: int = 120, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """子进程运行 python。

    本机 python312._pth 使子进程处于隔离模式（sys.flags.isolated=1，
    忽略 cwd 与 PYTHONPATH），故 `python -m loop_core.*` 需改用 -c 引导，
    在子进程内显式把项目根插入 sys.path。
    """
    if len(args) >= 3 and args[0] == sys.executable and args[1] == "-m":
        bootstrap = (
            "import sys; sys.path.insert(0, {proj!r}); "
            "from loop_core.security_scanner import main; sys.exit(main())"
        ).format(proj=str(PROJECT))
        args = [sys.executable, "-c", bootstrap] + args[2 + 1:]
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                          cwd=str(cwd or PROJECT))


def test_loop_core_cli_json_v1(tmp_path):
    (tmp_path / "src").mkdir()
    r = _run_py([sys.executable, "-m", "loop_core.security_scanner",
                 "--project-root", str(tmp_path / "src"), "--json"])
    assert r.returncode in (0, 2), r.stderr[-500:]
    payload = json.loads(r.stdout)
    assert validate_v1_report(payload)
    assert payload["role"] == "security-engineer"


def test_loop_core_cli_output_dir(tmp_path):
    (tmp_path / "src").mkdir()
    out = tmp_path / "out"
    r = _run_py([sys.executable, "-m", "loop_core.security_scanner",
                 "--project-root", str(tmp_path / "src"), "--output-dir", str(out)])
    assert r.returncode == 0
    assert (out / "security_report.json").exists()


def test_loop_core_cli_missing_root():
    r = _run_py([sys.executable, "-m", "loop_core.security_scanner",
                 "--project-root", str(Path(tempfile.mkdtemp()) / "nope"), "--json"])
    assert r.returncode == 2
    assert "error" in r.stdout


# ── 4. run_security_scan.py 契约兼容（MCP）────────────────────────────────

def test_run_security_scan_json_is_v1():
    """MCP security_scan_run 输出契约：--json 输出符合 security_report/v1。"""
    script = PROJECT / "agents" / "security-engineer" / "scripts" / "run_security_scan.py"
    # T-0143 1.1: 必须传 --output-dir 到临时目录——脚本默认写
    # .ai/evidence/security/（带时间戳），直接扫 PROJECT 会重写已登记证据
    # → CONTINUITY_SOURCE_DRIFT（每次全量回归后 release check 假红）。
    out = Path(tempfile.mkdtemp())
    r = _run_py([sys.executable, str(script), "--project-root", str(PROJECT),
                 "--output-dir", str(out), "--json"],
                timeout=300)
    assert r.returncode in (0, 2), r.stderr[-500:]
    assert r.stdout.strip(), "CLI 必须输出 JSON（--json）"
    payload = json.loads(r.stdout)
    assert validate_v1_report(payload), "run_security_scan 输出必须符合 security_report/v1"
    assert payload["role"] == "security-engineer"
    assert isinstance(payload["scans"], list) and len(payload["scans"]) >= 1


# ── 5. SCANNER_SELF_FILES 无残留 ──────────────────────────────────────────

def test_scanner_self_files_no_deleted_paths():
    """T-0113 P3-5：SCANNER_SELF_FILES 集合成员不得含已删工具路径。

    用 AST 提取集合字面量（避免注释/历史说明文本干扰断言）。
    """
    import ast
    src = (PROJECT / "agents" / "security-engineer" / "scripts" / "run_security_scan.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    members: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "SCANNER_SELF_FILES":
                if isinstance(node.value, ast.Set):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            members.add(elt.value)
    assert members, "必须能解析 SCANNER_SELF_FILES 集合"
    deleted = [
        "scripts/security_scan.py",
        "tools/tool_security_scan.py",
        "tool_quality_gates", "tool_dependency_analysis",
        "tool_contract_validate", "tool_cost_tracker",
        "tool_evidence_chain", "tool_task_queue", "tool_eval",
        "loop_vertical_slice", "loop_dispatch_role",
        "scripts/evidence_chain.py",
    ]
    assert not (members & set(deleted)), f"SCANNER_SELF_FILES 残留已删路径: {members & set(deleted)}"


# ── 6. 端到端一致性：loop_core CLI 与 run_security_scan 结构同源 ─────────

def test_v1_structure_consistent_across_implementations():
    """两实现的 v1 顶层字段集合一致（单一 schema 来源）。"""
    fields = set(SECURITY_REPORT_V1_FIELDS)
    assert {"schema", "role", "timestamp", "project", "scans", "overall", "blocked_by"} == fields


def test_scanner_library_still_scans():
    """既有库 API 不受影响（scan_security/SecurityScanner.scan）。

    用 tempfile.mkdtemp 作扫描根（pytest tmp_path 目录名含 test_，
    会被扫描器整类排除；扫描器排除逻辑按绝对路径子串匹配）。
    """
    src_dir = Path(tempfile.mkdtemp()) / "src"
    src_dir.mkdir()
    probe = src_dir / "probe.py"
    probe.write_text("api_key = 'sk-secretvalue1234567890123456789012'\n", encoding="utf-8")
    rep = scan_security(src_dir)
    assert rep.files_scanned >= 1
    assert any(f.rule_id == "SS-001" for f in rep.findings)
    # Compatibility alias
    rep2 = SecurityScanner.scan(src_dir)
    assert rep2.files_scanned == rep.files_scanned
