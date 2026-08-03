"""
test_t0108_fixes.py — T-0108 BH 融合·收敛期（F4/F6/F7/F8/F2-1）逐线测试。

AC 对照：
- AC-01  README Switchboard 三节 + doc-link 全绿（断链 FAIL 见
         tests/test_ai_doc_links.py）→ TestSwitchboard
- AC-02  context_loader 节选择读路由表（golden 快照一致）+ 路由表缺失
         回退旧行为 + 告警 → TestRoutingTable
- AC-03  finding 输出通过 schema 校验 + BH harness-findings.input.json
         字段映射对照 → TestFindingContract
- AC-04  validate_state 伪造旧 mtime 视图 → [warn] stale view（仅告警，
         既有判定不变）→ 见 tests/test_projection_freshness.py（回归在此）
- AC-05  投影视图 = state.yaml 派生 → 同上
- AC-06  死文档归档 + continuity 源清单同步（无悬挂引用）+ D5-7 显式
         声明区生效 → TestArchiveAndContinuity / TestDesignedFiles

逐线：
- F6：context_budget（token 估算 / AC 节保留 / 截断标记 / D2-8 timeout
  常量 / D4-4 knowledge warning）→ TestContextBudget
- F7：agents 脚本输出收敛（D1-7 截断标志 / D4-10 madge 失败原因 /
  D4-11 宽捕获收窄）+ D5-6 报告 front-matter 契约化 → TestAgentsScripts /
  TestMemoryReportMeta
- F4：路由表 schema 语义（golden 一致）
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core import context_packager
from loop_core import context_budget
from loop_core.context_loader import (
    ContextLoader,
    _ROUTING_CACHE,
    _load_section_routing,
    _select_relevant_sections,
)
from loop_core.memory_service import (
    MemoryExtractionReport,
    _parse_acceptance_report,
    _parse_acceptance_meta,
)
from loop_core.schemas.finding_contract import (
    to_bh_finding,
    validate_finding,
    validate_finding_list,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


# ============================================================================
# AC-01 — README Switchboard
# ============================================================================


class TestSwitchboard:
    def test_readme_three_sections(self):
        readme = (REPO_ROOT / ".ai" / "README.md").read_text(encoding="utf-8")
        assert "## Owns" in readme
        assert "## Does Not Own" in readme
        assert "## Read Next" in readme

    def test_routing_table_loads(self):
        routing = _load_section_routing(REPO_ROOT)
        assert routing is not None
        assert set(routing.keys()) >= {
            "quality-engineer", "security-engineer", "developer",
            "system-architect", "module-architect", "default",
        }


# ============================================================================
# AC-02 — context_loader 路由表（golden 快照 + 缺失回退 + 告警）
# ============================================================================


class TestRoutingTable:
    def _doc(self, tmp_path: Path) -> Path:
        doc = tmp_path / "arch.md"
        doc.write_text(
            "# Arch\n\n## Testing Strategy\n内容\n\n"
            "## Security Considerations\n内容\n\n"
            "## Deployment Pipeline\n内容\n\n"
            "## Performance Targets\n内容\n\n"
            "## Overview\n内容\n",
            encoding="utf-8",
        )
        return doc

    def test_golden_snapshot_routed_equals_legacy(self, tmp_path):
        """路由表接入前后节选择一致（golden 快照）。"""
        doc = self._doc(tmp_path)
        loader = ContextLoader(tmp_path)
        idx = loader.build_document_index(str(doc))
        routed = _select_relevant_sections(
            "quality-engineer", idx, project_root=tmp_path
        )
        legacy = _select_relevant_sections("quality-engineer", idx)
        assert routed == legacy
        assert routed  # 非空
        assert "Testing Strategy" in routed

    def test_routing_missing_falls_back_with_warning(self, tmp_path, caplog):
        """README 缺失 → 回退旧行为 + 告警（AC-02）。"""
        doc = self._doc(tmp_path)
        loader = ContextLoader(tmp_path)
        idx = loader.build_document_index(str(doc))
        with caplog.at_level(logging.WARNING, logger="context_loader"):
            selected = _select_relevant_sections(
                "quality-engineer", idx, project_root=tmp_path
            )
        assert selected  # 回退旧行为：非空
        assert any(
            "section_routing" in r.message and "falling back" in r.message
            for r in caplog.records
        ), caplog.records

    def test_routing_table_drives_selection(self, tmp_path):
        """路由表存在时按表驱动（default 键生效）。"""
        doc = self._doc(tmp_path)
        ai = tmp_path / ".ai"
        ai.mkdir(exist_ok=True)
        (ai / "README.md").write_text(
            "---\nsection_routing:\n  custom-role: [security]\n"
            "  default: []\n---\n# Switchboard\n",
            encoding="utf-8",
        )
        loader = ContextLoader(tmp_path)
        idx = loader.build_document_index(str(doc))
        _ROUTING_CACHE.clear()
        selected = _select_relevant_sections(
            "custom-role", idx, project_root=tmp_path
        )
        assert selected == ["Security Considerations"]

    def test_load_for_role_uses_routing(self, tmp_path):
        """load_for_role 透传 project_root（端到端）。"""
        doc = self._doc(tmp_path)
        ai = tmp_path / ".ai"
        ai.mkdir(exist_ok=True)
        (ai / "README.md").write_text(
            "---\nsection_routing:\n  quality-engineer: [testing]\n"
            "---\n# Switchboard\n",
            encoding="utf-8",
        )
        agents = tmp_path / "agents" / "quality-engineer"
        agents.mkdir(parents=True, exist_ok=True)
        contract = {
            "role_id": "quality-engineer",
            "identity": {"title": "QE"},
            "fixed_stance": ["Evidence over opinion."],
            "responsibilities": ["Review"],
            "prohibitions": [],
            "veto_power": [],
        }
        (agents / "CONTRACT.yaml").write_text(
            json.dumps(contract), encoding="utf-8"
        )
        loader = ContextLoader(tmp_path)
        ctx = loader.load_for_role("quality-engineer", str(doc), complexity=0.8)
        _ROUTING_CACHE.clear()
        assert any("Testing Strategy" in s for s in ctx.loaded_sections)


# ============================================================================
# AC-03 — finding schema + BH 映射
# ============================================================================

_VALID_FINDING = {
    "finding_id": "DR-001",
    "source": "design_reviewer",
    "severity": "high",
    "title": "t",
    "message": "m",
    "expected_output": "o",
    "fix_boundary": {"allowed_paths": ["loop_core/"]},
    "verification_command": "pytest",
    "acceptance_checks": ["a"],
}


class TestFindingContract:
    def test_valid_finding_passes(self):
        ok, errs = validate_finding(dict(_VALID_FINDING))
        assert ok is True and errs == []

    def test_invalid_finding_fails(self):
        bad = dict(_VALID_FINDING)
        bad["finding_id"] = ""
        ok, errs = validate_finding(bad)
        assert ok is False and errs

    def test_bad_severity_fails(self):
        bad = dict(_VALID_FINDING)
        bad["severity"] = "CRITICAL!"  # 非枚举
        ok, _ = validate_finding(bad)
        assert ok is False

    def test_mark_schema_status_additive(self):
        f = dict(_VALID_FINDING)
        from loop_core.schemas.finding_contract import mark_schema_status

        out = mark_schema_status(f)
        assert out["schema_status"] == "VALID"
        # 加字段不删字段
        assert "finding_id" in out and "message" in out

    def test_bh_mapping_fields(self):
        """BH harness-findings.input.json 字段映射对照（AC-03）。"""
        le = dict(
            _VALID_FINDING,
            dimension_refs=["change-validation"],
            target={"kind": "repo-root", "owner_route": "tests"},
            expected_outputs=["输出 A", "输出 B"],
            ai_fix_prompt="修复",
            expected_artifact="Tests",
        )
        bh = to_bh_finding(le)
        assert bh["id"] == "DR-001"
        assert bh["title"] == "t"
        assert bh["severity"] == "High"  # 小写 → BH 首字母大写
        assert bh["reason"] == "m"
        assert bh["dimensionRefs"] == ["change-validation"]
        assert bh["target"] == {
            "kind": "repo-root", "packageRoute": None, "ownerRoute": "tests",
        }
        assert bh["expectedOutput"] == ["输出 A", "输出 B"]
        assert bh["aiFixPrompt"] == "修复"
        assert bh["expectedArtifact"] == "Tests"

    def test_bh_mapping_single_expected_output(self):
        le = dict(_VALID_FINDING, expected_output="单一产出")
        bh = to_bh_finding(le)
        assert bh["expectedOutput"] == ["单一产出"]


# ============================================================================
# F6 — context_budget（token 预算 / AC 节 / 截断标记 / 常量）
# ============================================================================


class TestContextBudget:
    def test_estimate_tokens_heuristic(self):
        assert context_budget.estimate_tokens("abcd") == 1
        assert context_budget.estimate_tokens("x" * 40) == 10
        assert context_budget.estimate_tokens("") == 1

    def test_ac_section_never_cut(self):
        text = (
            "# T\n## 业务范围\n" + "x" * 500 +
            "\n## 可验证验收标准\n1. AC-01\n2. AC-02\n"
        )
        out = context_budget.format_task_card(text, budget=300)
        assert "AC-02" in out
        assert "task card truncated" in out

    def test_truncation_marker_structured(self):
        """D1-3：截断标记结构化（非裸切片）。"""
        out = context_budget.slice_with_marker("x" * 100, 10)
        assert out.startswith("x" * 10)
        assert "truncated" in out and "chars" in out
        # 未超限不追加标记
        assert context_budget.slice_with_marker("short", 100) == "short"

    def test_packager_delegates_to_budget(self):
        """context_packager 与 context_budget 行为一致（黄金）。"""
        text = (
            "# T\n## 可验证验收标准\n1. AC\n"
        )
        assert (
            context_packager._format_task_card(text)
            == context_budget.format_task_card(text)
        )
        assert (
            context_packager._slice_with_marker("y" * 50, 20)
            == context_budget.slice_with_marker("y" * 50, 20)
        )

    def test_timeout_constants_named(self):
        """D2-8：git timeout 命名常量。"""
        assert context_packager.GIT_TIMEOUT_DIFF_STAT == 5
        assert context_packager.GIT_TIMEOUT_DIFF_CODE == 10
        assert context_packager.GIT_TIMEOUT_DIFF_NAME == 5

    def test_extra_file_truncation_marked(self, tmp_path):
        """D1-3（F6 确认）：extra_files 截断带标记。"""
        (tmp_path / "big.txt").write_text("z" * 5000, encoding="utf-8")
        ctx = context_packager.build_context(
            str(tmp_path), "developer", extra_files=["big.txt"]
        )
        assert "[truncated" in ctx


# ============================================================================
# F7 — agents 脚本输出收敛（D1-7 / D4-10 / D4-11）
# ============================================================================


def _load_script_module(rel_path: str):
    spec = importlib.util.spec_from_file_location(
        rel_path.replace("/", "_").replace(".py", ""),
        REPO_ROOT / rel_path,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestAgentsScripts:
    def test_run_security_scan_raw_truncation_flag(self):
        """D1-7：audit 原始输出截断标志结构化。"""
        mod = _load_script_module(
            "agents/security-engineer/scripts/run_security_scan.py"
        )
        raw = "x" * 2000
        sliced, meta = mod._slice_raw(raw)
        assert len(sliced) == mod.RAW_OUTPUT_MAX_CHARS == 500
        assert meta == {"truncated": True, "raw_length": 2000,
                        "raw_max": 500}
        sliced2, meta2 = mod._slice_raw("short")
        assert meta2["truncated"] is False

    def test_run_security_scan_finding_contract_valid(self):
        """run_security_scan findings_contract 通过 finding schema 校验。"""
        mod = _load_script_module(
            "agents/security-engineer/scripts/run_security_scan.py"
        )
        finding = mod._finding_contract(
            {"file": "src/a.py", "line": 3, "rule": "eval()",
             "description": "eval 代码注入", "severity": "HIGH",
             "truncated": False, "finding_id": "INJ-H-0001"},
            "run_security_scan", "INJ-H-0001", REPO_ROOT,
        )
        ok, errs = validate_finding(finding)
        assert ok is True, errs

    def test_analyze_dependencies_madge_failure_reasons(self):
        """D4-10：madge 失败原因区分（不再宽捕获静默 None）。"""
        mod = _load_script_module(
            "agents/system-architect/scripts/analyze_dependencies.py"
        )
        # unavailable（命令缺失）
        g, err = mod.run_madge(REPO_ROOT / "nonexistent-dir-xyz")
        # FileNotFoundError → unavailable（PATH 上无 madge 时）
        if err is None:
            # 机器装有 madge 时返回图；否则必须给出结构化原因
            assert g is not None
        else:
            assert err["status"] in {
                "unavailable", "timeout", "error", "non-zero-exit",
                "invalid-json",
            }
            assert err["reason"]

    def test_analyze_dependencies_extract_reports_source(self, tmp_path):
        """extract_dependency_graph 返回 source_info（失败透明）。"""
        mod = _load_script_module(
            "agents/system-architect/scripts/analyze_dependencies.py"
        )
        g, info = mod.extract_dependency_graph(tmp_path)
        assert isinstance(g, dict)
        assert info["mode"] in ("madge", "python-ast")
        if info.get("madge_status") and info["madge_status"] != "ok":
            assert info.get("madge_reason")

    def test_validate_contract_narrow_except(self, tmp_path):
        """D4-11：宽捕获收窄 + 失败文件记录。"""
        mod = _load_script_module(
            "agents/module-architect/scripts/validate_contract.py"
        )
        bad_py = tmp_path / "broken.py"
        bad_py.write_text("def broken(:\n", encoding="utf-8")
        exports = mod.parse_python_exports(bad_py)
        assert exports == {}
        errs = mod.parse_errors()
        assert str(bad_py) in errs, errs
        # 正常文件不产生错误记录
        mod._PARSE_ERRORS.clear()
        good_py = tmp_path / "good.py"
        good_py.write_text("def ok():\n    return 1\n", encoding="utf-8")
        mod.parse_python_exports(good_py)
        assert str(good_py) not in mod._PARSE_ERRORS


# ============================================================================
# F7 — D5-6 报告 front-matter 契约化
# ============================================================================


class TestMemoryReportMeta:
    _LEGACY = """# T-0107 验收报告（acceptance-report）

> **T-0107: 设计漏洞修复 — | 2026-08-01**
> Gate: G-T-0107-REQUIREMENTS（user 批准）
> 独立审查：GO（6/6 AC）

## 已知遗留（P3，记录）

- 环境依赖项登记 KNOWN_ISSUES
"""

    _META = """---
acceptance_meta:
  task_id: T-0107
  title: 设计漏洞修复
  date: "2026-08-01"
  gate: {id: G-T-0107-REQUIREMENTS, decision: "user 批准"}
  review_verdict: "GO（6/6 AC）"
  legacy_items:
    - 环境依赖项登记 KNOWN_ISSUES
---

# T-0107 验收报告 — 设计漏洞修复

> **Gate: G-T-0107-REQUIREMENTS（user 批准）**（模板变化行，不再影响解析）
> 未命中行
"""

    def test_legacy_regex_unchanged(self):
        """旧格式（无 front-matter）解析行为不变。"""
        entries, unmatched = _parse_acceptance_report(self._LEGACY, "T-0107")
        assert len(entries) == 4  # title/gate/review/pitfall
        assert unmatched == 0

    def test_meta_front_matter_wins(self):
        """structured front-matter 优先于正则族（D5-6 契约化）。"""
        entries, unmatched = _parse_acceptance_report(self._META, "T-0107")
        assert len(entries) == 4
        assert any(
            e["source_id"] == "G-T-0107-REQUIREMENTS"
            and e["kind"] == "best_practice"
            for e in entries
        )
        assert any(e["tags"] == ["acceptance", "遗留"] for e in entries)
        # 模板变化的加粗行与未命中行 → 计数上报
        assert unmatched == 2

    def test_meta_parse_helper(self):
        meta = _parse_acceptance_meta(self._META)
        assert meta["title"] == "设计漏洞修复"
        assert meta["gate"]["id"] == "G-T-0107-REQUIREMENTS"
        assert _parse_acceptance_meta(self._LEGACY) is None

    def test_report_sources_include_unmatched(self, tmp_path, caplog):
        """MemoryExtractionReport 上报 unmatched_meta_lines（D5-6）。"""
        from loop_core.memory_service import (
            extract_from_acceptance_reports,
        )

        evidence = tmp_path / ".ai" / "evidence" / "T-0999" / "acceptance"
        evidence.mkdir(parents=True)
        (evidence / "acceptance-report.md").write_text(
            self._META, encoding="utf-8"
        )
        with caplog.at_level(logging.WARNING, logger="memory_service"):
            report = extract_from_acceptance_reports(tmp_path)
        assert report.sources["unmatched_meta_lines"] == 2
        assert any("unmatched_meta_lines" in r.message for r in caplog.records)


# ============================================================================
# AC-06 — 归档 + continuity 同步 + D5-7 designed_files
# ============================================================================


class TestArchiveAndContinuity:
    def test_archived_plans_moved_not_deleted(self):
        for name in ("PLAN-20260729-001.yaml", "PLAN-20260729-002.yaml"):
            archived = REPO_ROOT / ".ai" / "archive" / "plans" / name
            original = REPO_ROOT / ".ai" / "plans" / name
            assert archived.is_file()
            assert not original.exists()

    def test_continuity_manifest_synced(self):
        """归档后 continuity 源清单无悬挂条目（AC-06 无悬挂引用）。"""
        sys.path.insert(0, str(REPO_ROOT / ".zcode" / "tools"))
        from governor_lib import load_yaml

        data = load_yaml(REPO_ROOT / ".ai" / "project_continuity.yaml")
        paths = [s["path"] for s in data["source_manifest"]]
        assert ".ai/plans/PLAN-20260729-001.yaml" not in paths
        assert ".ai/plans/PLAN-20260729-002.yaml" not in paths
        # 其余清单条目路径全部存在（无悬挂引用）
        for source in data["source_manifest"]:
            assert (REPO_ROOT / source["path"]).is_file(), source["path"]

    def test_validate_state_still_passes_on_repo(self):
        """归档 + 清单同步后 validate_state 全绿（continuity 干净）。

        rc 兼容 idle 合法阻塞态（rc=3 NO_ACTIVE_TASK，T-0101 分流；
        T-0102 rollback 同款语义）：idle 稳态下 rc=3 且含 [info] NO_ACTIVE_TASK
        属预期，不视为失败。
        """
        r = subprocess.run(
            [sys.executable, str(REPO_ROOT / ".zcode" / "tools"
                                / "validate_state.py"), str(REPO_ROOT)],
            capture_output=True, text=True,
        )
        out = r.stdout + r.stderr
        assert r.returncode in (0, 3), out
        assert "[ok] state is usable" in out or "NO_ACTIVE_TASK" in out


class TestDesignedFiles:
    def test_arch_front_matter_declaration(self):
        """docs/02-architecture.md front-matter designed_files 显式声明区
        （D5-7 消解）。"""
        text = (REPO_ROOT / "docs" / "02-architecture.md").read_text(
            encoding="utf-8"
        )
        assert text.startswith("---")
        assert "designed_files:" in text.split("---")[1]
        assert "hooks/scripts/session_brief.py" in text
        assert "tools/" in text

    def test_diff_checker_reads_declaration(self):
        """implementation_design_diff 改读显式声明区（正则仅提示）。"""
        sys.path.insert(0, str(REPO_ROOT / "scripts" / "role_checkers"))
        import implementation_design_diff as idd

        result = idd.diff(str(REPO_ROOT))
        assert result["declaration"] == "front-matter designed_files"
        # 正则推断只进 hint，不进 DRIFT 判定（D5-7 误报消除：
        # evidence_chain.py/server.py 等说明性引用不再判 designed）
        assert "evidence_chain.py" in result["hint_regex_inferred"]
        assert "evidence_chain.py" not in result["designed_but_missing"]
        assert "server.py" not in result["designed_but_missing"]
        # 显式声明的 hook 文件全部存在
        assert result["designed_but_missing"] == []

    def test_diff_checker_fallback_no_declaration(self, tmp_path):
        """无 designed_files 声明 → regex 回退并标注（行为向后兼容）。"""
        sys.path.insert(0, str(REPO_ROOT / "scripts" / "role_checkers"))
        import implementation_design_diff as idd

        docs = tmp_path / "docs"
        docs.mkdir(parents=True)
        (docs / "02-architecture.md").write_text(
            "# Arch\n\n`loop_core/foo.py` 设计\n", encoding="utf-8"
        )
        result = idd.diff(str(tmp_path))
        assert result["declaration"].startswith("regex-fallback")
        assert "loop_core/foo.py" in result["designed_but_missing"]


# ============================================================================
# F2-1 — validate_state 回归（既有判定不变，已在 test_projection_freshness）
# ============================================================================


class TestValidateStateRegression:
    def test_existing_verdicts_unchanged_on_repo(self):
        """既有判定测试全绿（F2-1 回归：validate_state 判定不变）。

        rc 兼容 idle 合法阻塞态（rc=3 NO_ACTIVE_TASK，T-0101 分流）：
        idle 稳态下 rc=3 + [info] NO_ACTIVE_TASK 属预期；激活态下 rc=0。
        本测试聚焦"既有判定输出不变"（usable / NO_ACTIVE_TASK 文案），
        不绑定单一 rc；current_task_id 仅断言前缀存在，不绑定具体任务 ID
        （T-0109 独立审查 P3-1：任务态推进/复位自愈，去耦合）。
        """
        r = subprocess.run(
            [sys.executable, str(REPO_ROOT / ".zcode" / "tools"
                                / "validate_state.py"), str(REPO_ROOT)],
            capture_output=True, text=True,
        )
        assert r.returncode in (0, 3)
        out = r.stdout + r.stderr
        assert "stale view" not in out  # 无视图时不告警（默认路径）
        assert "[ok] state is usable" in out or "NO_ACTIVE_TASK" in out
        # 不绑定具体任务 ID（任务态随推进/复位自愈，closeout 后复位为 none）
        assert "current_task_id:" in out
