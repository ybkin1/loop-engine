"""T-0100 (F-04): 依赖扫描环境不可用 → SKIPPED（不合成 HIGH/BLOCKED）。

- AC-03a: pip-audit 环境不可用（缺 venv → 崩溃 exit=2 / 命令缺失 / 超时）→
  dependency_scan status=skipped + 明确 reason；counts 无合成 HIGH；overall
  不 BLOCKED（exit 0）。
- AC-03b: 真实 CVE 扫描结果照常判定 —— pip-audit 退出码 1 + JSON 漏洞列表 →
  blocked（HIGH），阻断语义不变（AC-07：SKIP 不掩盖真实阻断）。
- AC-03c: 干净结果（exit 0 / JSON 空列表）→ pass。
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCAN_SCRIPT = PROJECT_ROOT / "agents" / "security-engineer" / "scripts" / "run_security_scan.py"


def _load_scan_module():
    """按文件路径加载 run_security_scan.py（脚本非包，与既有测试同风格）。"""
    spec = importlib.util.spec_from_file_location("run_security_scan_t0100", SCAN_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


scan = _load_scan_module()


class FakeProc:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture
def python_project(tmp_path: Path) -> Path:
    """带 pyproject.toml + requirements.txt 的 python 项目根（触发 pip-audit 分支）。"""
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "1.0.0"\n',
                                         encoding="utf-8")
    (root / "requirements.txt").write_text("PyYAML>=6.0\n", encoding="utf-8")
    return root


def _run_dependency_scan(root: Path, fake, monkeypatch) -> dict:
    monkeypatch.setattr(scan.subprocess, "run", lambda *a, **k: fake)
    return scan.run_dependency_scan(root)


class TestDependencyScanSkipped:
    def test_pip_audit_crash_venv_missing_skips_not_high(self, python_project: Path,
                                                         monkeypatch):
        """T-0099 现场：pip-audit 缺 venv 崩溃（exit=2 + ModuleNotFoundError）——
        修复前合成 HIGH:1 → BLOCKED；修复后 SKIPPED + reason，零合成计数。"""
        fake = FakeProc(
            returncode=2,
            stdout="",
            stderr="Traceback (most recent call last):\n"
                   "ModuleNotFoundError: No module named 'venv'\n",
        )
        result = _run_dependency_scan(python_project, fake, monkeypatch)
        assert result["status"] == "skipped"
        assert result["skipped"] is True
        assert result["counts"]["HIGH"] == 0, "环境不可用不得合成 HIGH"
        assert result["counts"]["CRITICAL"] == 0
        assert "venv" in result["reason"] and "pip-audit" in result["reason"]
        assert "环境不可用" in result["reason"]

    def test_pip_audit_command_missing_skips(self, python_project: Path, monkeypatch):
        def missing(*a, **k):
            raise FileNotFoundError("pip-audit")

        monkeypatch.setattr(scan.subprocess, "run", missing)
        result = scan.run_dependency_scan(python_project)
        assert result["status"] == "skipped"
        assert result["counts"]["HIGH"] == 0
        assert "不可用" in result["reason"]

    def test_pip_audit_timeout_skips(self, python_project: Path, monkeypatch):
        def timeout(*a, **k):
            raise subprocess.TimeoutExpired(cmd="pip-audit", timeout=120)

        monkeypatch.setattr(scan.subprocess, "run", timeout)
        result = scan.run_dependency_scan(python_project)
        assert result["status"] == "skipped"
        assert result["counts"]["HIGH"] == 0
        assert "超时" in result["reason"]

    def test_unparseable_nonzero_exit_skips(self, python_project: Path, monkeypatch):
        fake = FakeProc(returncode=3, stdout="[garbage", stderr="boom")
        result = _run_dependency_scan(python_project, fake, monkeypatch)
        assert result["status"] == "skipped"
        assert result["counts"]["HIGH"] == 0
        assert "exit=3" in result["reason"]

    def test_skipped_scan_does_not_block_overall(self, python_project: Path,
                                                 monkeypatch, tmp_path: Path):
        """SKIPPED 不阻断：整体 PASS、exit 0、报告含原因。"""
        fake = FakeProc(
            returncode=2,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'venv'\n",
        )
        monkeypatch.setattr(scan.subprocess, "run", lambda *a, **k: fake)
        # 其余三类扫描用空项目数据（无密钥/无注入/无路由）→ 均 pass
        scans = [
            scan.run_dependency_scan(python_project),
            scan.run_secret_scan(python_project),
            scan.run_injection_scan(python_project),
            scan.run_permission_audit(python_project),
        ]
        out_dir = tmp_path / "out"
        overall = scan.generate_report(scans, python_project, out_dir)
        assert overall == "PASS"
        report = json.loads((out_dir / "security_report.json").read_text(encoding="utf-8"))
        dep = next(s for s in report["scans"] if s["name"] == "dependency_scan")
        assert dep["status"] == "skipped"
        assert dep["reason"]
        assert report["blocked_by"] == []
        summary = (out_dir / "security_summary.md").read_text(encoding="utf-8")
        assert "SKIPPED" in summary and "venv" in summary


class TestDependencyScanRealResults:
    def test_real_cve_findings_still_block(self, python_project: Path, monkeypatch):
        """AC-07：真实 CVE 结果不被 SKIP 掩盖 —— 退出码 1 + JSON 漏洞列表 →
        blocked（HIGH），判定语义与修复前一致。"""
        fake = FakeProc(
            returncode=1,
            stdout=json.dumps([
                {"name": "PyYAML", "version": "5.4", "vulns": [
                    {"id": "VULN-1", "severity": "HIGH", "description": "real CVE"},
                ]},
            ]),
            stderr="",
        )
        result = _run_dependency_scan(python_project, fake, monkeypatch)
        assert result["status"] == "blocked"
        assert result["skipped"] is False
        assert result["counts"]["HIGH"] == 1
        assert result["counts"]["CRITICAL"] == 0

    def test_real_clean_result_passes(self, python_project: Path, monkeypatch):
        fake = FakeProc(returncode=0, stdout="[]", stderr="")
        result = _run_dependency_scan(python_project, fake, monkeypatch)
        assert result["status"] == "pass"
        assert result["counts"]["HIGH"] == 0

    def test_no_requirements_file_not_blocking(self, tmp_path: Path, monkeypatch):
        root = tmp_path / "project"
        root.mkdir()
        (root / "pyproject.toml").write_text("[project]\nname='x'\nversion='1.0.0'\n",
                                             encoding="utf-8")
        result = scan.run_dependency_scan(root)
        assert result["status"] == "pass"  # 无依赖清单 → 无可审依赖（非漏洞）
        assert "requirements.txt" in result["raw"]

    def test_real_blocked_still_blocks_overall(self, python_project: Path,
                                               monkeypatch, tmp_path: Path):
        """AC-07：真实阻断不被弱化 —— 真实 CVE → overall BLOCKED + exit 2 路径。"""
        fake = FakeProc(
            returncode=1,
            stdout=json.dumps([{"name": "x", "version": "1", "vulns": [
                {"id": "V-1", "severity": "CRITICAL", "description": "real"},
            ]}]),
            stderr="",
        )
        monkeypatch.setattr(scan.subprocess, "run", lambda *a, **k: fake)
        scans = [scan.run_dependency_scan(python_project)]
        out_dir = tmp_path / "out"
        assert scan.generate_report(scans, python_project, out_dir) == "BLOCKED"
