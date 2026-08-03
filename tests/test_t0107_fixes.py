# -*- coding: utf-8 -*-
"""T-0107 — 设计漏洞修复回归测试（audit-design-gaps.md 编号引用）。

覆盖（对应 .ai/evidence/T-0106/design/audit-design-gaps.md）：
- context_packager 专项：D1-1（token 预算 + AC 节优先保留 + truncated 标记）、
  D1-2/D1-3（截断标记）、D1-4（JSON 完整边界）、D2-1/D2-8（命名常量）、
  D3-2（total 死护栏真实执行）、D4-1（git diff 吞错 → 占位 + 日志）、
  D4-4（knowledge cases 损坏告警 + diff 缓存）
- P2：D2-2（intent_router 阈值常量）、D3-1/D4-5（audit_ledger 轮转 +
  损坏行计数）、D4-2（loop_enforcement state 读取失败 fail-closed）、
  D4-3（tool_constraint_check phase 告警字段）、D5-1（yaml fallback 告警
  + schema 校验 + 解析失败/无 gate 分开上报）、D5-2（front-matter 共享
  契约解析：enforcement vs context_controller 双路径一致）
- P3：D3-4（runtime_controller journal 轮转）、D3-5（async_jobs 落盘轮转）、
  D4-7（hook 哈希跳过告警）、D4-8（transaction_registry 裸 except 移除）、
  D5-5（contract_verifier fallback 收窄）
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "hooks" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "tools"))
sys.path.insert(0, str(REPO_ROOT / ".zcode" / "tools"))

from loop_core import context_packager  # noqa: E402
from loop_core.audit_ledger import AuditLedger  # noqa: E402
from loop_core.context_controller import ContextController  # noqa: E402
from loop_core.contract_verifier import _parse_yaml_content  # noqa: E402
from loop_core.front_matter import parse_task_front_matter  # noqa: E402
from loop_core.intent_router import IntentRouter  # noqa: E402

import loop_enforcement  # noqa: E402
import tool_constraint_check  # noqa: E402
import transaction_registry  # noqa: E402


@pytest.fixture
def tmp_root(tmp_path: Path) -> Path:
    return tmp_path


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# ══════════════════════════════════════════════════════════════════════
# D1-1：任务卡 token 预算 + AC 节优先保留 + truncated 标记
# ══════════════════════════════════════════════════════════════════════

def _task_card_text() -> str:
    """构造一张 AC 节在旧 1000 字符截断点之后的任务卡（T-0105.md 复现）。

    前导头部很短（< 400 字符上限），"业务范围"节约 1300 字符使 AC 节
    落在旧 [:1000] 截断点之后。
    """
    return (
        "# T-XXXX: 测试任务\n\n"
        "## 业务范围\n" + ("业务范围描述行，位于 AC 之前。\n" * 90) + "\n"  # ≈1300 chars
        "## 可验证验收标准\n"
        "1. [AC-01] 验收标准第一条完整内容必须保留\n"
        "2. [AC-02] 验收标准第二条完整内容必须保留\n"
        "3. [AC-03] 验收标准第三条完整内容必须保留\n"
    )


class TestD11TaskCardBudget:
    def test_ac_section_not_cut_when_beyond_old_1000_limit(self, tmp_root):
        """AC 节位于 1000 字符之后（旧 bug 复现场景）→ 完整保留、无截断标记。"""
        _write(tmp_root, ".ai/tasks/T-0001.md", _task_card_text())
        ctx = context_packager.build_context(str(tmp_root), "developer", task_id="T-0001")
        assert "[AC-01] 验收标准第一条完整内容必须保留" in ctx
        assert "[AC-03] 验收标准第三条完整内容必须保留" in ctx
        assert "task card truncated" not in ctx  # 预算内不截断

    def test_ac_section_survives_token_budget_truncation(self, tmp_root):
        """整卡远超预算 → 非 AC 节被丢，AC 节完整保留 + truncated 标记。"""
        big = _task_card_text() + (
            "## 详细设计\n" + ("设计细节填充内容。\n" * 400) + "\n"  # ≈4400 chars
            "## 参考文档\n" + ("参考文档填充内容。\n" * 400) + "\n"  # ≈4400 chars
        )
        _write(tmp_root, ".ai/tasks/T-0002.md", big)
        ctx = context_packager.build_context(str(tmp_root), "developer", task_id="T-0002")
        assert "[AC-01] 验收标准第一条完整内容必须保留" in ctx
        assert "…[task card truncated" in ctx
        assert "AC section preserved" in ctx

    def test_ac_section_huge_never_cut(self, tmp_root):
        """AC 节本身超过预算 → 仍完整保留（硬优先级），其余节丢弃。"""
        huge_ac = "## 可验证验收标准\n" + ("AC 内容行，必须完整保留。\n" * 700)  # > 6000 chars
        card = "# T-0003\n\n## 业务范围\n范围内容。\n" + huge_ac
        _write(tmp_root, ".ai/tasks/T-0003.md", card)
        ctx = context_packager.build_context(str(tmp_root), "developer", task_id="T-0003")
        assert "AC 内容行，必须完整保留。" in ctx
        assert "…[task card truncated" in ctx
        # 非 AC 节被丢弃（预算被 AC 占用）
        assert "范围内容。" not in ctx

    def test_plain_text_card_marker(self, tmp_root):
        """无 `## ` 节的任务卡：按 token 预算截断并带标记。"""
        long_text = "# 纯文本卡\n" + ("无节内容填充。\n" * 900)
        _write(tmp_root, ".ai/tasks/T-0004.md", long_text)
        ctx = context_packager.build_context(str(tmp_root), "developer", task_id="T-0004")
        assert "…[task card truncated" in ctx


# ══════════════════════════════════════════════════════════════════════
# D1-2 / D1-3 / D1-4：截断标记
# ══════════════════════════════════════════════════════════════════════

class TestTruncationMarkers:
    def test_role_file_truncation_marked(self, tmp_root):
        """角色指定文件超 max_content → 显式 …[truncated 标记（D1-2）。"""
        _write(tmp_root, "docs/01-requirements.md", "需求内容\n" * 700)  # > 3000 (product-manager)
        ctx = context_packager.build_context(str(tmp_root), "product-manager")
        assert "…[truncated" in ctx

    def test_extra_file_truncation_marked(self, tmp_root):
        """extra_files 超 2000 字符 → 显式标记（D1-3）。"""
        _write(tmp_root, "notes.md", "笔记内容\n" * 500)  # > 2000
        ctx = context_packager.build_context(str(tmp_root), "developer", extra_files=["notes.md"])
        assert "…[truncated" in ctx

    def test_knowledge_cases_truncated_to_valid_json(self, tmp_root):
        """knowledge cases 超限 → 按 case 边界截断，JSON 保持语法完整 + 标记（D1-4）。"""
        cases = [{"id": f"case-{i}", "summary": "案例内容" * 400, "tags": ["a", "b"]}
                 for i in range(3)]  # 3 cases × ~1650 chars > 3000 上限
        _write(tmp_root, ".ai/knowledge/cases.json", json.dumps(cases, ensure_ascii=False))
        ctx = context_packager.build_context(str(tmp_root), "developer")
        assert "## Knowledge Cases" in ctx
        assert "…[truncated" in ctx
        # 标记之前的 JSON 前缀必须是语法完整的（可 json.loads）。
        # 限定在 Knowledge Cases 节内取数组起点（diff 占位文本可能含 "["）。
        json_part = ctx.split("…[truncated")[0].split("## Knowledge Cases", 1)[1]
        json.loads(json_part[json_part.index("["):])  # 不应抛异常

    def test_small_knowledge_cases_untouched(self, tmp_root):
        """小 cases.json 原样输出，无标记。"""
        _write(tmp_root, ".ai/knowledge/cases.json",
               json.dumps([{"id": "c1", "summary": "短案例"}], ensure_ascii=False))
        ctx = context_packager.build_context(str(tmp_root), "developer")
        assert '"id": "c1"' in ctx
        assert "…[truncated" not in ctx


# ══════════════════════════════════════════════════════════════════════
# D2-1 / D2-8：命名常量
# ══════════════════════════════════════════════════════════════════════

class TestNamedConstants:
    def test_truncation_literals_named(self):
        """截断/数量字面量集中为命名常量（D2-1）。"""
        assert context_packager.TASK_CARD_TOKEN_BUDGET > 0
        assert context_packager.EXTRA_FILE_MAX_CHARS == 2000
        assert context_packager.KNOWLEDGE_CASES_MAX_CHARS == 3000
        assert context_packager.MAX_EXTRA_FILES == 5
        assert context_packager.MAX_KNOWLEDGE_CASES == 3

    def test_git_timeouts_named(self):
        """git timeout 字面量集中为命名常量（D2-8）。"""
        assert context_packager.GIT_TIMEOUT_DIFF_STAT == 5
        assert context_packager.GIT_TIMEOUT_DIFF_CODE == 10
        assert context_packager.GIT_TIMEOUT_DIFF_NAME == 5


# ══════════════════════════════════════════════════════════════════════
# D3-2：MAX_TOTAL_CHARS 死护栏真实执行
# ══════════════════════════════════════════════════════════════════════

class TestD32TotalBudget:
    def test_total_budget_enforced(self, tmp_root, monkeypatch):
        """MAX_TOTAL_CHARS 真实执行：超限带截断标记，footer 始终保留。"""
        monkeypatch.setattr(context_packager, "MAX_TOTAL_CHARS", 400)
        _write(tmp_root, ".ai/tasks/T-0005.md", _task_card_text())
        ctx = context_packager.build_context(str(tmp_root), "developer", task_id="T-0005")
        assert "…[context truncated: total budget exceeded]" in ctx
        assert "execution_mode: SIMULATED_MAIN_SESSION" in ctx  # footer 不丢

    def test_total_actually_accumulates(self, tmp_root):
        """多节累计不再静默超限（原 total 从不递增的死代码）。"""
        _write(tmp_root, "docs/01-requirements.md", "R" * 8000)
        _write(tmp_root, "docs/02-architecture.md", "A" * 8000)
        _write(tmp_root, "docs/03-interface-contract.md", "C" * 8000)
        ctx = context_packager.build_context(str(tmp_root), "developer")
        assert "execution_mode: SIMULATED_MAIN_SESSION" in ctx


# ══════════════════════════════════════════════════════════════════════
# D4-1：git diff 吞错 → 占位 + 日志
# ══════════════════════════════════════════════════════════════════════

class TestD41GitDiffFailure:
    def test_diff_unavailable_placeholder(self, tmp_root, caplog):
        """非 git 目录（git 失败）→ 占位节 + warning，不再静默。"""
        with caplog.at_level("WARNING"):
            ctx = context_packager.build_context(str(tmp_root), "developer")
        assert "diff unavailable" in ctx
        assert any("git diff unavailable" in r.message for r in caplog.records)

    def test_no_exception_when_git_missing(self, tmp_root):
        """git 不可用不抛异常。"""
        ctx = context_packager.build_context(str(tmp_root), "developer")
        assert ctx


# ══════════════════════════════════════════════════════════════════════
# D4-4：knowledge cases 损坏告警 + diff 缓存
# ══════════════════════════════════════════════════════════════════════

class TestD44KnowledgeCorruptAndDiffCache:
    def test_corrupt_knowledge_cases_warned(self, tmp_root, caplog):
        """损坏的 cases.json 不再静默丢弃（warning + 不抛异常）。"""
        _write(tmp_root, ".ai/knowledge/cases.json", "{ not valid json !!!")
        with caplog.at_level("WARNING"):
            ctx = context_packager.build_context(str(tmp_root), "developer")
        assert any("knowledge cases" in r.message for r in caplog.records)
        assert ctx  # 其余节照常

    def test_diff_cache_reuses_same_head(self, tmp_root, monkeypatch):
        """同一 HEAD 下第二次 build_context 不重跑 git diff（D4-4 缓存）。"""
        # 建一个带两个提交的 git 仓库（HEAD~1 才有效）
        repo = tmp_root / "repo"
        repo.mkdir()
        _write(repo, "file.py", "x = 1\n")
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "add", "-A"], cwd=str(repo), check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "init"], cwd=str(repo), check=True)
        _write(repo, "file.py", "x = 2\n")
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "add", "-A"], cwd=str(repo), check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "second"], cwd=str(repo), check=True)

        context_packager._DIFF_CACHE.clear()
        calls = {"n": 0}
        real_run = subprocess.run

        def counting_run(*args, **kwargs):
            argv = args[0] if args and isinstance(args[0], list) else []
            if len(argv) >= 2 and argv[0] == "git" and argv[1] == "diff":
                calls["n"] += 1
            return real_run(*args, **kwargs)

        monkeypatch.setattr(context_packager.subprocess, "run", counting_run)
        context_packager.build_context(str(repo), "developer")
        first = calls["n"]
        assert first > 0  # 首次确实执行了 git diff
        context_packager.build_context(str(repo), "developer")
        assert calls["n"] == first  # 第二次命中缓存，不再执行
        assert context_packager._DIFF_CACHE  # 缓存非空


# ══════════════════════════════════════════════════════════════════════
# D2-2：intent_router 阈值命名常量
# ══════════════════════════════════════════════════════════════════════

class TestD22EscalationThreshold:
    def test_threshold_constant(self):
        assert IntentRouter.MEDIUM_RISK_ESCALATION_MIN == 3

    def test_threshold_behavior_preserved(self):
        """≥3 个中风险因素仍升级（行为不变，魔法数已命名）。"""
        factors = {
            "has_multiple_modules": True,
            "has_external_api": True,
            "has_concurrency_performance": True,
            "requires_deployment": False,
        }
        escalate, reason = IntentRouter.should_escalate(
            risk_factors=factors, current_mode=None)
        assert escalate is True
        assert "Multiple medium-risk factors" in reason
        # 2 个不升级
        factors2 = {"has_multiple_modules": True, "has_external_api": True}
        escalate2, _ = IntentRouter.should_escalate(risk_factors=factors2)
        assert escalate2 is False


# ══════════════════════════════════════════════════════════════════════
# D3-1 / D4-5：audit_ledger 轮转 + 损坏行计数
# ══════════════════════════════════════════════════════════════════════

class TestAuditLedgerRotationAndCorrupt:
    def test_rotation_preserves_chain_integrity(self, tmp_root):
        """轮转后链哈希跨归档延续，verify_integrity 依然有效（D3-1）。"""
        ledger_path = tmp_root / ".ai" / "audit_ledger.jsonl"
        ledger = AuditLedger(ledger_path, max_lines=5, max_bytes=1024 * 1024, max_archives=2)
        for i in range(12):
            ledger.append("test_event", "system", {"i": i})
        main_lines = ledger_path.read_text(encoding="utf-8").splitlines()
        assert len(main_lines) <= 5  # 主文件被轮转限制
        assert Path(f"{ledger_path}.1").exists()
        result = ledger.verify_integrity()
        assert result.valid is True
        assert result.total_entries == 12
        # 重新加载（归档 + 主文件按序读入）后链依然完整
        reloaded = AuditLedger(ledger_path)
        assert reloaded.length == 12
        assert reloaded.verify_integrity().valid is True

    def test_archives_bounded(self, tmp_root):
        """归档数不超过 max_archives（D3-1 保留 N 份）。"""
        ledger_path = tmp_root / ".ai" / "audit_ledger.jsonl"
        ledger = AuditLedger(ledger_path, max_lines=3, max_bytes=1024 * 1024, max_archives=2)
        for i in range(30):
            ledger.append("test_event", "system", {"i": i})
        assert not Path(f"{ledger_path}.3").exists()
        assert Path(f"{ledger_path}.1").exists() and Path(f"{ledger_path}.2").exists()

    def test_corrupt_trailing_line_reported(self, tmp_root):
        """尾部损坏行：链有效但 corrupt_line_count > 0（D4-5 区分清理/篡改）。"""
        ledger_path = tmp_root / ".ai" / "audit_ledger.jsonl"
        ledger = AuditLedger(ledger_path)
        ledger.append("e1", "system")
        ledger.append("e2", "system")
        with open(ledger_path, "a", encoding="utf-8") as f:
            f.write("{corrupt garbage line}\n")
        reloaded = AuditLedger(ledger_path)
        assert reloaded.corrupt_line_count == 1
        result = reloaded.verify_integrity()
        assert result.valid is True
        assert result.corrupt_lines == 1

    def test_corrupt_middle_line_breaks_chain(self, tmp_root):
        """中段损坏行：链断裂且损坏行被计数（D4-5 篡改可检测）。"""
        ledger_path = tmp_root / ".ai" / "audit_ledger.jsonl"
        ledger = AuditLedger(ledger_path)
        ledger.append("e1", "system")
        ledger.append("e2", "system")
        ledger.append("e3", "system")
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
        lines[1] = "{tampered}\n"
        ledger_path.write_text("\n".join(lines), encoding="utf-8")
        reloaded = AuditLedger(ledger_path)
        assert reloaded.corrupt_line_count >= 1
        result = reloaded.verify_integrity()
        assert result.valid is False  # 篡改被链校验发现


# ══════════════════════════════════════════════════════════════════════
# D4-2：loop_enforcement state 读取失败 fail-closed
# ══════════════════════════════════════════════════════════════════════

class TestD42FailClosed:
    def test_state_unreadable_fails_closed(self, tmp_root, caplog):
        """state.yaml 缺失/损坏 → is_loop_mode_enforced 返回 True（fail-closed）。"""
        with caplog.at_level("WARNING"):
            assert loop_enforcement.is_loop_mode_enforced(tmp_root) is True
        assert any("STATE_UNREADABLE" in r.message for r in caplog.records)

    def test_state_corrupt_yaml_fails_closed(self, tmp_root, caplog):
        _write(tmp_root, ".ai/state.yaml", "loop_mode: [unclosed")
        with caplog.at_level("WARNING"):
            assert loop_enforcement.is_loop_mode_enforced(tmp_root) is True

    def test_modes_unchanged(self, tmp_root):
        """FULL/STANDARD → True；LIGHTWEIGHT/缺失 → False（正常路径不变）。"""
        _write(tmp_root, ".ai/state.yaml", "loop_mode: FULL\n")
        assert loop_enforcement.is_loop_mode_enforced(tmp_root) is True
        _write(tmp_root, ".ai/state.yaml", "loop_mode: STANDARD\n")
        assert loop_enforcement.is_loop_mode_enforced(tmp_root) is True
        _write(tmp_root, ".ai/state.yaml", "loop_mode: LIGHTWEIGHT\n")
        assert loop_enforcement.is_loop_mode_enforced(tmp_root) is False
        _write(tmp_root, ".ai/state.yaml", "project_name: x\n")
        assert loop_enforcement.is_loop_mode_enforced(tmp_root) is False


# ══════════════════════════════════════════════════════════════════════
# D4-7：hook 哈希跳过告警（不静默）
# ══════════════════════════════════════════════════════════════════════

class TestD47HashSkipWarned:
    def test_unreadable_hook_file_warned_once(self, tmp_root, monkeypatch, caplog):
        target = "hook_common.py"
        real_read_bytes = Path.read_bytes

        def selective_read_bytes(self_obj):
            if self_obj.name == target:
                raise OSError("simulated unreadable")
            return real_read_bytes(self_obj)

        monkeypatch.setattr(Path, "read_bytes", selective_read_bytes)
        loop_enforcement._HOOK_SHA_WARNED.clear()
        with caplog.at_level("WARNING"):
            shas = loop_enforcement._snapshot_hook_file_shas()
        assert target not in str(shas)  # 被跳过
        warned = [r for r in caplog.records if "HASH_SCAN_SKIPPED" in r.message]
        assert len(warned) >= 1  # 显式告警（was 静默 continue）
        # 再次调用不再重复告警（进程内去重）
        caplog.clear()
        with caplog.at_level("WARNING"):
            loop_enforcement._snapshot_hook_file_shas()
        assert not [r for r in caplog.records if "HASH_SCAN_SKIPPED" in r.message]
        loop_enforcement._HOOK_SHA_WARNED.clear()  # 恢复（避免污染其他测试）


# ══════════════════════════════════════════════════════════════════════
# D4-3：tool_constraint_check phase 告警字段
# ══════════════════════════════════════════════════════════════════════

class TestD43ConstraintCheckPhaseProblems:
    def test_invalid_phase_reported(self, tmp_root):
        """非法 phase 不再静默丢弃 → phase_problems 字段。"""
        result = tool_constraint_check.run(
            project_root=str(tmp_root), current_phase="NOT_A_PHASE",
            target_phase="ALSO_BAD",
        )
        assert result["phase_problem_count"] == 2
        assert result["phase_problems"]
        assert "current_phase" in result["phase_problems"][0]

    def test_valid_phase_no_problems(self, tmp_root):
        result = tool_constraint_check.run(
            project_root=str(tmp_root), current_phase="S4-implementation",
        )
        assert result["phase_problem_count"] == 0


# ══════════════════════════════════════════════════════════════════════
# D5-1：yaml fallback 显式告警 + schema 校验 + 解析失败/无 gate 分开
# ══════════════════════════════════════════════════════════════════════

def _block_yaml(monkeypatch):
    """使 `import yaml` 在目标模块内抛 ImportError（模拟 PyYAML 不可用）。"""
    monkeypatch.setitem(sys.modules, "yaml", None)


class TestD51YamlFallback:
    def test_fallback_warns_explicitly(self, tmp_root, monkeypatch, caplog):
        _block_yaml(monkeypatch)
        _write(tmp_root, ".ai/state.yaml", "schema_version: 1\ncurrent_phase: S4-implementation\n")
        ctrl = ContextController(tmp_root)
        with caplog.at_level("WARNING"):
            state = ctrl._load_state()
        assert isinstance(state, dict)
        assert any("PyYAML 不可用" in r.message for r in caplog.records)

    def test_naive_result_schema_validation(self, tmp_root, monkeypatch, caplog):
        """naive 解析结果做 schema 校验：非法 gate 显式告警（D5-1）。"""
        _block_yaml(monkeypatch)
        _write(tmp_root, ".ai/gates.yaml",
               "gates:\n  - id: G-1\n    task_id: T-0001\n")  # 缺 gate_type/status
        ctrl = ContextController(tmp_root)
        with caplog.at_level("WARNING"):
            gates = ctrl._load_gates()
        assert gates == [{"id": "G-1", "task_id": "T-0001"}]
        assert any("gate schema" in r.message for r in caplog.records)

    def test_yaml_syntax_error_warns(self, tmp_root, caplog):
        """PyYAML 语法错误 → 显式告警 + naive 降级（不再静默）。"""
        _write(tmp_root, ".ai/gates.yaml", "gates:\n  - id: [unclosed\n")
        ctrl = ContextController(tmp_root)
        with caplog.at_level("WARNING"):
            ctrl._load_gates()
        assert any("PyYAML 解析失败" in r.message for r in caplog.records)

    def test_no_gates_is_not_a_warning(self, tmp_root, caplog):
        """有效文件但无 gates 键 = 正常"无 gate"，不告警（与解析失败分开）。"""
        _write(tmp_root, ".ai/gates.yaml", "project_name: x\n")
        ctrl = ContextController(tmp_root)
        with caplog.at_level("WARNING"):
            gates = ctrl._load_gates()
        assert gates == []
        assert not [r for r in caplog.records if "gates.yaml" in r.message]

    def test_valid_yaml_no_warnings(self, tmp_root, caplog):
        """PyYAML 主路径：有效文件零告警。"""
        _write(tmp_root, ".ai/state.yaml",
               "schema_version: 1\nproject_name: t\ncurrent_phase: S4-implementation\n")
        ctrl = ContextController(tmp_root)
        with caplog.at_level("WARNING"):
            state = ctrl._load_state()
        assert state.get("current_phase") == "S4-implementation"
        assert not [r for r in caplog.records if "context_controller" in r.name]


# ══════════════════════════════════════════════════════════════════════
# D5-2：共享 front-matter 契约解析（双解析器统一 + 双路径一致）
# ══════════════════════════════════════════════════════════════════════

TABLE_FORMAT = """\
# T-0001: 表格形态任务卡

## 基本信息

| 字段 | 值 |
|------|-----|
| task_id | T-0001 |
| loop_mode | FULL |
| mcp_allowed_tools | mcp__node_repl |

## 允许路径

allowed_paths:
- loop_core/
- tests/

developer_agent_id: dev-agent-1
reviewer_agent_id: rev-agent-1
"""

LIST_FORMAT = """\
# T-0001: 列表形态任务卡

## 基本信息

task_id: T-0001
loop_mode: FULL
mcp_allowed_tools:
  - mcp__node_repl

## 允许路径

allowed_paths:
- loop_core/
- tests/

developer_agent_id: dev-agent-1
reviewer_agent_id: rev-agent-1
"""


class TestD52SharedFrontMatter:
    def test_shared_parser_table_and_list_agree(self):
        """表格 | 形态与列表形态解析结果一致（同一契约两种写法）。"""
        table = parse_task_front_matter(TABLE_FORMAT)
        listing = parse_task_front_matter(LIST_FORMAT)
        assert table == listing
        assert listing["mcp_allowed_tools"] == ["mcp__node_repl"]
        assert listing["allowed_paths"] == ["loop_core/", "tests/"]
        assert listing["developer_agent_id"] == "dev-agent-1"
        assert listing["reviewer_agent_id"] == "rev-agent-1"

    def test_dual_path_enforcement_vs_controller(self, tmp_root):
        """同一任务卡：enforcement 与 context_controller 解析结果一致（D5-2 双路径）。"""
        _write(tmp_root, ".ai/tasks/T-0001.md", TABLE_FORMAT)
        _write(tmp_root, ".ai/tasks/T-0002.md", LIST_FORMAT)
        ctrl = ContextController(tmp_root)
        for tid in ("T-0001", "T-0002"):
            assert loop_enforcement.load_task_contract(tmp_root, tid) == \
                ctrl._load_task_contract(tid)

    def test_fallback_legacy_parser_identical(self):
        """本地韧性副本与共享模块解析一致（退化环境行为相同）。"""
        for text in (TABLE_FORMAT, LIST_FORMAT):
            assert loop_enforcement._parse_task_front_matter_legacy(text) == \
                parse_task_front_matter(text)

    def test_controller_contract_includes_mcp_field(self, tmp_root):
        """context_controller 契约现含 mcp_allowed_tools（was 双解析器分歧点）。"""
        _write(tmp_root, ".ai/tasks/T-0001.md", TABLE_FORMAT)
        ctrl = ContextController(tmp_root)
        contract = ctrl._load_task_contract("T-0001")
        assert contract["mcp_allowed_tools"] == ["mcp__node_repl"]


# ══════════════════════════════════════════════════════════════════════
# D3-4：runtime_controller journal 轮转
# ══════════════════════════════════════════════════════════════════════

class TestD34JournalRotation:
    def test_journal_rotates_after_threshold(self, tmp_root, monkeypatch):
        from loop_core import runtime_controller as rc_mod
        from loop_core.runtime_controller import RuntimeController

        monkeypatch.setattr(rc_mod, "JOURNAL_MAX_BYTES", 100)
        ctrl = RuntimeController(str(tmp_root))
        for i in range(10):
            ctrl._event("state_change", {"i": i})
        assert Path(tmp_root / ".ai/runtime/runtime-events.jsonl.1").exists()
        # 主文件未删除、可继续写
        assert (tmp_root / ".ai/runtime/runtime-events.jsonl").exists()


# ══════════════════════════════════════════════════════════════════════
# D3-5：async_jobs 落盘轮转
# ══════════════════════════════════════════════════════════════════════

class TestD35PersistRotation:
    def test_persist_file_rotates(self, tmp_root):
        from loop_core.async_jobs import AsyncJobQueue

        persist = tmp_root / ".ai/evidence/observability/jobs.jsonl"
        queue = AsyncJobQueue(persist_path=str(persist),
                              persist_max_bytes=200, persist_max_archives=2)
        try:
            for i in range(6):
                outcome = queue.submit(lambda x=i: x, i)
                assert outcome.accepted
            queue.shutdown(wait=True)
        finally:
            queue._shutdown = True
        assert persist.exists()
        assert Path(f"{persist}.1").exists()  # 落盘侧已轮转
        assert not Path(f"{persist}.3").exists()  # 归档有界


# ══════════════════════════════════════════════════════════════════════
# D4-8：transaction_registry 裸 except 移除
# ══════════════════════════════════════════════════════════════════════

class TestD48TransactionRegistry:
    def test_acknowledge_with_path_and_str_root(self, tmp_root, monkeypatch):
        """Path 与 str 形态 root 都能写（裸 except 冗余分支已移除）。"""
        fake_registry = {
            "schema": "TransactionRegistry/v1",
            "contract_id": "TEST-1",
            "data": {"checkpoint_acknowledgments": []},
        }
        monkeypatch.setattr(
            transaction_registry, "load_transaction_registry",
            lambda root, relative=".ai/transaction_registry.yaml": fake_registry,
        )
        (tmp_root / ".ai").mkdir(parents=True, exist_ok=True)  # 真实流程中 registry 已存在
        for root in (tmp_root, str(tmp_root)):
            ack = transaction_registry.acknowledge_checkpoint(
                root, "CP-TEST", 1, "H" * 64, session_id="s")
            assert ack["checkpoint_id"] == "CP-TEST"
        assert (tmp_root / ".ai/transaction_registry.yaml").exists()

    def test_no_bare_except_remains(self):
        """源码中该函数不再含裸 except（D4-8 正确性回归）。"""
        src = Path(transaction_registry.__file__).read_text(encoding="utf-8")
        assert "except:" not in src


# ══════════════════════════════════════════════════════════════════════
# D5-5：contract_verifier fallback 收窄
# ══════════════════════════════════════════════════════════════════════

class TestD55ContractVerifierFallback:
    def test_yaml_syntax_error_returns_empty(self, caplog):
        """PyYAML 解析失败（非 ImportError）→ 空结构 + 告警，不再 pattern 降级。"""
        with caplog.at_level("WARNING"):
            result = _parse_yaml_content("- function: broken\n  : : [unclosed")
        assert result == {"contracts": []}
        assert any("no pattern fallback" in r.message for r in caplog.records)

    def test_import_error_uses_pattern_fallback(self, monkeypatch, caplog):
        """仅 ImportError → pattern fallback，产出去向标注 _parsed_by。"""
        monkeypatch.setitem(sys.modules, "yaml", None)
        text = (
            "- function: compute_total\n"
            "  tests_required:\n"
            "    - test_compute_total\n"
            "    - test_compute_total_empty\n"
            "- function: other_fn\n"
        )
        with caplog.at_level("WARNING"):
            result = _parse_yaml_content(text)
        assert result["_parsed_by"] == "pattern-fallback"
        funcs = [c["function"] for c in result["contracts"]]
        assert funcs == ["compute_total", "other_fn"]
        assert result["contracts"][0]["tests_required"] == [
            "test_compute_total", "test_compute_total_empty"]
        assert any("PyYAML unavailable" in r.message for r in caplog.records)

    def test_pyyaml_path_untouched(self):
        """PyYAML 正常路径：无 _parsed_by 标注、无告警。"""
        result = _parse_yaml_content(
            "contracts:\n  - function: f\n    tests_required: [t_f]\n")
        assert "_parsed_by" not in result
        assert result["contracts"][0]["function"] == "f"
