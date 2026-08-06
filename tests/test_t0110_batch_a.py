# -*- coding: utf-8 -*-
"""T-0110 批 A — 魔法数字集中化（M-1~17）+ P3 消解测试。

覆盖：
- loop_core/constants.py 常量表单测（截断族/超时族/阈值族/exit code 族）+
  截断辅助函数（D1-5/6/8 统一标记约定）；
- hooks/scripts/loop_enforcement_constants.py 常量表单测（M-1/M-3/M-4）；
- P3 消解行为测试：
  * D2-3/D2-4/D2-5 阈值常量接线（intent_router / veto_escalation 边界）；
  * D1-5 违规 snippet 截断标记（security_scanner / design_reviewer）；
  * D1-6 executor 失败 stderr 截断标记；
  * D1-8/D2-7 loop_self_audit 尾部截断命名常量 + 标记；
  * D3-8 loop_self_audit git_commit timeout + 异常兜底；
  * D3-6 role_checkers git diff timeout + 异常兜底；
  * D4-9 role_checkers 裸 except 收窄 + 记原因；
- AC-01 grep `timeout=[0-9]` 零新散落断言（touched 文件）；
- M-16 .ai/slo.yaml score_caps 与 DEFAULT_SCORE_CAPS 一致性核对（T-0109 覆盖）。
"""
from __future__ import annotations

import builtins
import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "hooks" / "scripts"))  # hook 常量表（M-1/M-3/M-4）

from loop_core import constants as C
from loop_core.constants import tail_with_marker, truncate_with_marker
from loop_core.schemas.evidence_state import DEFAULT_SCORE_CAPS
import loop_enforcement_constants as HKC  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════
# 1. loop_core/constants.py 常量表单测（AC-01）
# ═══════════════════════════════════════════════════════════════════════


class TestLoopCoreConstants:
    def test_exit_code_family_m2(self):
        """M-2 治理工具返回码：validate_state/close_session 0/2/3 语义。"""
        assert C.EXIT_OK == 0
        assert C.EXIT_VALIDATION_FAILED == 2
        assert C.EXIT_IDLE_BLOCKED == 3

    def test_truncation_family_m10_m11(self):
        """M-10/M-11 截断族：值与原字面量逐一对应（行为等价）。"""
        assert C.SNIPPET_MAX_CHARS == 100            # D1-5 security_scanner/design_reviewer
        assert C.FAILED_STDERR_MAX_CHARS == 500      # D1-6 executor
        assert C.AUDIT_STDOUT_TAIL_CHARS == 4000     # D2-7 loop_self_audit.run
        assert C.AUDIT_STDERR_TAIL_CHARS == 2000     # D2-7 loop_self_audit.run
        assert C.AUDIT_SUMMARY_STDOUT_TAIL_CHARS == 800   # build_llm_summary
        assert C.AUDIT_SUMMARY_STDERR_TAIL_CHARS == 400   # build_llm_summary
        assert C.TRUNCATION_ELLIPSIS == "…"

    def test_timeout_family_d3_6_d3_8(self):
        """超时族：role_checkers / loop_self_audit git 命令 timeout=10。"""
        assert C.GIT_DIFF_NAME_ONLY_TIMEOUT_SECONDS == 10
        assert C.GIT_SHORT_SHA_TIMEOUT_SECONDS == 10
        assert C.AUDIT_RUN_TIMEOUT_SECONDS == 300

    def test_threshold_family_m7_m8_m9(self):
        """M-7/8/9 阈值族。"""
        assert C.CONFIDENCE_CONFLICT_MIN_DOMAINS == 4
        assert C.CONFIDENCE_CONFLICT_MAX_RISK_FACTORS == 2
        assert C.KEYWORD_BOUNDARY_MAX_LEN == 3
        assert C.USER_GATE_MIN_DISTINCT_ROLES == 3


class TestTruncationHelpers:
    """D1-5/6/8 统一 `…` 标记约定（截断辅助纯函数）。"""

    def test_truncate_with_marker_short_unchanged(self):
        assert truncate_with_marker("short", 100) == "short"

    def test_truncate_with_marker_at_limit_unchanged(self):
        text = "x" * 100
        assert truncate_with_marker(text, 100) == text

    def test_truncate_with_marker_long_appends_ellipsis(self):
        out = truncate_with_marker("x" * 120, 100)
        assert len(out) == 100
        assert out == "x" * 99 + "…"

    def test_tail_with_marker_short_unchanged(self):
        assert tail_with_marker("short", 100) == "short"

    def test_tail_with_marker_long_prefix_ellipsis(self):
        out = tail_with_marker("x" * 120, 100)
        assert len(out) == 100
        assert out == "…" + "x" * 99


# ═══════════════════════════════════════════════════════════════════════
# 2. hooks/scripts/loop_enforcement_constants.py 常量表单测（M-1/M-3/M-4）
# ═══════════════════════════════════════════════════════════════════════


class TestHookEnforcementConstants:
    def test_exit_codes_m1(self):
        """M-1 hook 裁决返回码与 loop_enforcement 现值一致。"""
        assert HKC.EXIT_PASS == 0
        assert HKC.EXIT_BLOCK == 2
        assert HKC.REEXEC_MAX == 1

    def test_timeout_family_m3_m4(self):
        assert HKC.COMMAND_TIMEOUT_SECONDS == 30   # M-3 六文件七处同值
        assert HKC.GUARD_HEALTH_PROBE_TIMEOUT_SECONDS == 20  # M-4 guard_health

    def test_defaults_and_whitelists(self):
        assert HKC.MAX_DIFF_FILES == 15
        assert HKC.DEFAULT_MAX_FILES == 10
        assert ".ai/gates.yaml" in HKC.GOVERNANCE_EXEMPT
        assert "AGENTS.md" in HKC.MINIMAL_METADATA_READ
        assert ".ai/evidence/" in HKC.MAIN_THREAD_ALLOWED
        assert ".zcode/tools/" in HKC.GOVERNANCE_TOOL_DIRS
        assert "hooks/" in HKC.GOVERNANCE_TOOL_DIRS


# ═══════════════════════════════════════════════════════════════════════
# 3. D2-3/D2-4 阈值常量接线（intent_router）
# ═══════════════════════════════════════════════════════════════════════


class TestIntentRouterThresholds:
    def _confidence(self, domains, risk_factors, complexity=0.25):
        from loop_core.intent_router import IntentRouter

        router = IntentRouter()
        return router._calculate_confidence(
            complexity_score=complexity,
            risk_factors=risk_factors,
            domains=set(domains),
            context={"k1": 1, "k2": 2},
        )

    def test_conflict_penalty_fires_at_min_domains_and_max_risks(self):
        """M-7 边界：4 域 + 2 风险 → 惩罚触发（原字面量 >= 4 且 <= 2）。"""
        _, warnings = self._confidence(
            ["a", "b", "c", "d"], {"r1": True, "r2": True})
        assert any("Many domains detected" in w for w in warnings)

    def test_conflict_penalty_off_below_min_domains(self):
        _, warnings = self._confidence(
            ["a", "b", "c"], {"r1": True, "r2": True})
        assert not any("Many domains detected" in w for w in warnings)

    def test_conflict_penalty_off_above_max_risks(self):
        _, warnings = self._confidence(
            ["a", "b", "c", "d"], {"r1": True, "r2": True, "r3": True})
        assert not any("Many domains detected" in w for w in warnings)

    def test_keyword_boundary_len3_word_boundary(self):
        """M-8 边界：len(kw)=3 → 词边界匹配（"api" 不命中 "apicall"）。"""
        from loop_core.intent_router import _set_if_match

        factors = {"has_external_api": False}
        _set_if_match(factors, "has_external_api", "the apicall endpoint",
                      ["api", "rest", "webhook", "http client"])
        assert factors["has_external_api"] is False

    def test_keyword_boundary_len4_substring(self):
        """M-8 边界：len(kw)=4 > KEYWORD_BOUNDARY_MAX_LEN → 子串匹配。"""
        from loop_core.intent_router import _set_if_match

        factors = {"has_external_api": False}
        _set_if_match(factors, "has_external_api", "a crest on the wall",
                      ["rest"])
        assert factors["has_external_api"] is True


# ═══════════════════════════════════════════════════════════════════════
# 4. D2-5 阈值常量接线（veto_escalation）
# ═══════════════════════════════════════════════════════════════════════


class TestVetoEscalationUserGateMin:
    def _engine(self, roles):
        from loop_core.veto_escalation import (
            VetoEscalation, VetoRecord, VetoSeverity)

        engine = VetoEscalation()
        for i, role in enumerate(roles):
            engine.record_veto(VetoRecord(
                veto_id=f"v-{i}", role_id=role, target_task_id="task-1",
                target_gate_id="gate-s5-quality", severity=VetoSeverity.BLOCKER,
                reason=f"veto from {role}", recorded_at="2026-08-03T00:00:00+00:00",
            ))
        return engine

    def test_two_roles_same_domain_stays_cross_role(self):
        """边界下界：2 角色（同域）→ 不触发 USER_GATE（Rule 2 不生效）。"""
        from loop_core.veto_escalation import EscalationLevel

        engine = self._engine(["system-architect", "module-architect"])
        decision = engine.check_escalation("task-1")
        assert decision.level == EscalationLevel.CROSS_ROLE

    def test_three_distinct_roles_escalates_user_gate(self):
        """M-9 边界：3 个不同角色（非 security-engineer）→ USER_GATE。"""
        from loop_core.veto_escalation import EscalationLevel

        engine = self._engine(["quality-engineer", "delivery-manager", "developer"])
        decision = engine.check_escalation("task-1")
        assert decision.level == EscalationLevel.USER_GATE

    def test_four_distinct_roles_escalates_user_gate(self):
        from loop_core.veto_escalation import EscalationLevel

        engine = self._engine(
            ["quality-engineer", "delivery-manager", "developer", "release-engineer"])
        decision = engine.check_escalation("task-1")
        assert decision.level == EscalationLevel.USER_GATE


# ═══════════════════════════════════════════════════════════════════════
# 5. D1-5 违规 snippet 截断标记（security_scanner / design_reviewer）
# ═══════════════════════════════════════════════════════════════════════


class TestSnippetTruncationMarker:
    def test_security_scanner_long_line_gets_marker(self, tmp_path_factory):
        from loop_core.security_scanner import scan_security

        # 注意：scan_security 排除路径含 "test_" 的文件（tmp_path 含
        # test_<函数名>），故用 tmp_path_factory.mktemp 建扫描根。
        src = tmp_path_factory.mktemp("scanroot") / "src"
        src.mkdir()
        long_line = 'token = "' + "a" * 120 + '"'
        (src / "app.py").write_text(long_line + "\n", encoding="utf-8")

        report = scan_security(src)
        assert report.findings
        snippet = report.findings[0].snippet
        assert snippet.endswith("…")
        assert len(snippet) == C.SNIPPET_MAX_CHARS
        # T-0108 F7 契约视图的 truncated 标志与截断状态一致
        assert report.findings[0].to_finding()["truncated"] is True

    def test_security_scanner_short_line_no_marker(self, tmp_path_factory):
        from loop_core.security_scanner import scan_security

        src = tmp_path_factory.mktemp("scanroot") / "src"
        src.mkdir()
        (src / "app.py").write_text('token = "abcdefghij"\n', encoding="utf-8")

        report = scan_security(src)
        assert report.findings
        snippet = report.findings[0].snippet
        assert not snippet.endswith("…")
        assert report.findings[0].to_finding()["truncated"] is False

    def test_design_reviewer_long_line_gets_marker(self, tmp_path):
        from loop_core.design_reviewer import review_design

        src = tmp_path / "loop_core"
        src.mkdir()
        (src / "x.py").write_text(
            "import zcode  # " + "a" * 110 + "\n", encoding="utf-8")

        report = review_design(src)
        dr001 = [f for f in report.findings if f.rule_id == "DR-001"]
        assert dr001
        assert dr001[0].snippet.endswith("…")
        assert len(dr001[0].snippet) == C.SNIPPET_MAX_CHARS


# ═══════════════════════════════════════════════════════════════════════
# 6. D1-6 executor 失败 stderr 截断标记
# ═══════════════════════════════════════════════════════════════════════


class TestExecutorFailedStderrMarker:
    def test_compile_fail_fallback_stderr_has_marker(self, tmp_path, caplog):
        from loop_core.executor import Executor
        from loop_core.router import LoopMode

        checker = tmp_path / ".ai" / "checkers" / "compile_gate.py"
        checker.parent.mkdir(parents=True)
        checker.write_text("", encoding="utf-8")

        def fake_runner(cmd, **kwargs):
            return SimpleNamespace(returncode=1, stdout="not-json",
                                   stderr="e" * 600)

        executor = Executor(LoopMode.FULL, subprocess_runner=fake_runner)
        with caplog.at_level(logging.WARNING):
            ok = executor._run_compile_gate_check(tmp_path)
        assert ok is False
        messages = [r.message for r in caplog.records
                    if "COMPILE_FAILED" in r.getMessage()]
        assert messages
        tail = messages[0].split("stderr: ", 1)[1]
        assert tail.endswith("…")
        assert len(tail) == C.FAILED_STDERR_MAX_CHARS


# ═══════════════════════════════════════════════════════════════════════
# 7. D1-8/D2-7 loop_self_audit 尾部截断命名常量 + 标记
# ═══════════════════════════════════════════════════════════════════════


class TestSelfAuditTails:
    def test_run_tail_markers(self, monkeypatch):
        import tools.loop_self_audit as tool

        def fake_run(cmd, **kwargs):
            assert kwargs["timeout"] == C.AUDIT_RUN_TIMEOUT_SECONDS
            return SimpleNamespace(returncode=0, stdout="x" * 5000,
                                   stderr="y" * 3000)

        monkeypatch.setattr(tool.subprocess, "run", fake_run)
        out = tool.run(["echo", "hi"])
        assert out["rc"] == 0
        assert out["stdout"] == "…" + "x" * (C.AUDIT_STDOUT_TAIL_CHARS - 1)
        assert len(out["stdout"]) == C.AUDIT_STDOUT_TAIL_CHARS
        assert out["stderr"] == "…" + "y" * (C.AUDIT_STDERR_TAIL_CHARS - 1)
        assert len(out["stderr"]) == C.AUDIT_STDERR_TAIL_CHARS

    def test_run_short_output_unchanged(self, monkeypatch):
        import tools.loop_self_audit as tool

        def fake_run(cmd, **kwargs):
            return SimpleNamespace(returncode=0, stdout="ok", stderr="")

        monkeypatch.setattr(tool.subprocess, "run", fake_run)
        out = tool.run(["echo", "hi"])
        assert out["stdout"] == "ok"
        assert out["stderr"] == ""

    def test_build_llm_summary_tail_markers(self):
        import tools.loop_self_audit as tool

        results = {
            "compile": {"rc": 0, "stdout": "o" * 2000, "stderr": "e" * 1000},
        }
        summary = tool.build_llm_summary(results, failed=[])
        assert summary["checks"]["compile"]["stdout_tail"].startswith("…")
        assert len(summary["checks"]["compile"]["stdout_tail"]) == C.AUDIT_SUMMARY_STDOUT_TAIL_CHARS
        assert summary["checks"]["compile"]["stderr_tail"].startswith("…")
        assert len(summary["checks"]["compile"]["stderr_tail"]) == C.AUDIT_SUMMARY_STDERR_TAIL_CHARS


# ═══════════════════════════════════════════════════════════════════════
# 8. D3-8 loop_self_audit git_commit timeout + 异常兜底
# ═══════════════════════════════════════════════════════════════════════


class TestSelfAuditGitCommit:
    def test_git_missing_returns_empty(self, monkeypatch):
        import tools.loop_self_audit as tool

        def raise_missing(cmd, **kwargs):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(tool.subprocess, "run", raise_missing)
        assert tool.git_commit() == ""

    def test_git_timeout_returns_empty(self, monkeypatch):
        import tools.loop_self_audit as tool

        def raise_timeout(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, C.GIT_SHORT_SHA_TIMEOUT_SECONDS)

        monkeypatch.setattr(tool.subprocess, "run", raise_timeout)
        assert tool.git_commit() == ""

    def test_git_ok_returns_short_sha(self, monkeypatch):
        import tools.loop_self_audit as tool

        captured = {}

        def fake_run(cmd, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
            return SimpleNamespace(returncode=0, stdout="abc1234\n")

        monkeypatch.setattr(tool.subprocess, "run", fake_run)
        assert tool.git_commit() == "abc1234"
        assert captured["timeout"] == C.GIT_SHORT_SHA_TIMEOUT_SECONDS

    def test_git_nonzero_returns_empty(self, monkeypatch):
        import tools.loop_self_audit as tool

        def fake_run(cmd, **kwargs):
            return SimpleNamespace(returncode=128, stdout="fatal: not a git repo\n")

        monkeypatch.setattr(tool.subprocess, "run", fake_run)
        assert tool.git_commit() == ""


# ═══════════════════════════════════════════════════════════════════════
# 9. D3-6 role_checkers git diff timeout + 异常兜底；D4-9 except 收窄
# ═══════════════════════════════════════════════════════════════════════


def _load_role_checker(name: str):
    sys.path.insert(0, str(_REPO_ROOT / "scripts" / "role_checkers"))
    return __import__(name)


class TestScopeDriftDetector:
    def _task_graph(self, tmp_path, allowed=None):
        (tmp_path / ".ai").mkdir(parents=True)
        task = {"id": "T-0001"}
        if allowed is not None:
            task["allowed_paths"] = allowed
        (tmp_path / ".ai" / "task_graph.yaml").write_text(
            f"tasks:\n- id: T-0001\n  allowed_paths: {json.dumps(allowed or [])}\n"
            if allowed is not None else "tasks:\n- id: T-0001\n",
            encoding="utf-8")

    def test_git_timeout_returns_error_not_crash(self, tmp_path, monkeypatch):
        mod = _load_role_checker("scope_drift_detector")
        self._task_graph(tmp_path, allowed=["loop_core/"])

        def raise_timeout(cmd, **kwargs):
            assert kwargs.get("timeout") == C.GIT_DIFF_NAME_ONLY_TIMEOUT_SECONDS
            raise subprocess.TimeoutExpired(cmd, C.GIT_DIFF_NAME_ONLY_TIMEOUT_SECONDS)

        monkeypatch.setattr(mod.subprocess, "run", raise_timeout)
        result = mod.detect(str(tmp_path), "T-0001")
        assert result["error"].startswith("git diff unavailable")

    def test_git_missing_returns_error_not_crash(self, tmp_path, monkeypatch):
        mod = _load_role_checker("scope_drift_detector")
        self._task_graph(tmp_path, allowed=["loop_core/"])

        def raise_missing(cmd, **kwargs):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(mod.subprocess, "run", raise_missing)
        result = mod.detect(str(tmp_path), "T-0001")
        assert "git diff unavailable" in result["error"]

    def test_yaml_import_error_narrowed_with_reason(self, tmp_path, monkeypatch):
        mod = _load_role_checker("scope_drift_detector")
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("No module named 'yaml'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        result = mod.detect(str(tmp_path), "T-0001")
        assert result["error"].startswith("yaml not available")
        assert "No module named 'yaml'" in result["error"]


class TestReviewCoverageChecker:
    def test_git_timeout_returns_error_status(self, tmp_path, monkeypatch):
        mod = _load_role_checker("review_coverage_checker")

        def raise_timeout(cmd, **kwargs):
            assert kwargs.get("timeout") == C.GIT_DIFF_NAME_ONLY_TIMEOUT_SECONDS
            raise subprocess.TimeoutExpired(cmd, C.GIT_DIFF_NAME_ONLY_TIMEOUT_SECONDS)

        monkeypatch.setattr(mod.subprocess, "run", raise_timeout)
        result = mod.check(str(tmp_path), "nope.json")
        assert result["status"] == "ERROR"
        assert "git diff unavailable" in result["reason"]

    def test_invalid_evidence_narrowed_not_crash(self, tmp_path, monkeypatch):
        mod = _load_role_checker("review_coverage_checker")

        def fake_run(cmd, **kwargs):
            return SimpleNamespace(returncode=0, stdout="")

        monkeypatch.setattr(mod.subprocess, "run", fake_run)
        ep = tmp_path / "evidence.json"
        ep.write_text("{broken json", encoding="utf-8")
        result = mod.check(str(tmp_path), str(ep))
        assert result["status"] == "INVALID"

    def test_missing_evidence_still_reports(self, tmp_path, monkeypatch):
        mod = _load_role_checker("review_coverage_checker")

        def fake_run(cmd, **kwargs):
            return SimpleNamespace(returncode=0, stdout="")

        monkeypatch.setattr(mod.subprocess, "run", fake_run)
        result = mod.check(str(tmp_path), "nope.json")
        assert result["status"] == "MISSING"


# ═══════════════════════════════════════════════════════════════════════
# 10. AC-01 grep `timeout=[0-9]` 零新散落断言（touched 文件）
# ═══════════════════════════════════════════════════════════════════════


_TOUCHED_FILES = [
    "loop_core/executor.py",
    "loop_core/executor_compile.py",  # T-0124 拆分：编译门 timeout=120 随迁
    "loop_core/security_scanner.py",
    "loop_core/design_reviewer.py",
    "loop_core/intent_router.py",
    "loop_core/veto_escalation.py",
    "tools/loop_self_audit.py",
    "scripts/role_checkers/scope_drift_detector.py",
    "scripts/role_checkers/review_coverage_checker.py",
]

# 显式豁免（批 A 前既有散落，非 M-1~17/D2-6 清单项）：
#   executor.py / executor_compile.py 各一处 timeout=120（编译门/代理运行，
#   审计 D2-6 未列；T-0124 拆分将原 executor 两处之一随方法体迁入
#   executor_compile.py）。
# 截断字面量豁免：security_scanner.py `[:16]`（SHA-256 摘要前缀，非显示截断阈值）。


class TestGrepZeroScatter:
    def test_no_new_timeout_literals_in_touched_files(self):
        pattern = re.compile(r"timeout=\d+")
        for rel in _TOUCHED_FILES:
            content = (_REPO_ROOT / rel).read_text(encoding="utf-8")
            matches = pattern.findall(content)
            if rel == "loop_core/executor.py":
                # 既有 timeout=120（显式豁免：不在 M 清单/D2-6；T-0124 拆分
                # 后仅代理运行一处，编译门一处随迁 executor_compile.py）
                assert matches == ["timeout=120"], rel
            elif rel == "loop_core/executor_compile.py":
                assert matches == ["timeout=120"], rel
            else:
                assert matches == [], f"{rel}: 新散落 timeout 字面量 {matches}"

    def test_no_new_slice_literals_in_touched_files(self):
        pattern = re.compile(r"\[:\d+\]|\[-\d+:\]")
        for rel in _TOUCHED_FILES:
            content = (_REPO_ROOT / rel).read_text(encoding="utf-8")
            matches = pattern.findall(content)
            if rel == "loop_core/security_scanner.py":
                # 既有 `[:16]` SHA-256 摘要前缀（显式豁免：非显示截断阈值）
                assert matches == ["[:16]"], rel
            else:
                assert matches == [], f"{rel}: 新散落截断字面量 {matches}"


# ═══════════════════════════════════════════════════════════════════════
# 11. M-16 .ai/slo.yaml score_caps 与代码默认表一致性（T-0109 已落地核对）
# ═══════════════════════════════════════════════════════════════════════


class TestSloScoreCaps:
    def test_slo_yaml_matches_default_score_caps(self):
        import yaml

        doc = yaml.safe_load((_REPO_ROOT / ".ai" / "slo.yaml").read_text(
            encoding="utf-8"))
        assert doc["score_caps"] == DEFAULT_SCORE_CAPS

    def test_bands_cover_bh_caps(self):
        from loop_core.schemas.evidence_state import SCORE_BANDS

        assert SCORE_BANDS == (59, 74, 84, 94, 100)
        assert set(DEFAULT_SCORE_CAPS.values()) == set(SCORE_BANDS)
