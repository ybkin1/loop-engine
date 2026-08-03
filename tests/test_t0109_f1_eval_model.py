"""
T-0109 F1 评估模型 — 证据七态 / GateLesson evidence 字段 / 评分上限表 /
Repair-Loop 分离 / advisory-only 静态断言（AC-03）。

覆盖：
- 七态枚举：值域、coerce 规整（大小写/连字符/空值）、非法值 fail-closed。
- GateLesson.evidence_state：round-trip、旧记录缺字段 → N-A（向后兼容）、
  非法值拒绝。
- 评分上限表：59/74/84/94/100 分档边界等值断言 + slo.yaml score_caps
  显式化解析（含 fail-closed 校验）。
- Repair Progress / Loop Effectiveness 分离指标。
- AC-03 静态断言：评分字段不出现在任何 gate 判定路径
  （state_machine.can_approve_gate / gate_guard / enforcement /
  hard_constraints / guard_health / slo_gate / approval_ledger）。
"""
from __future__ import annotations

import ast
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

from loop_core.gate_feedback import (
    GateLesson,
    InvalidLessonError,
    record_gate_lesson,
)
from loop_core.governance_metrics import (
    DEFAULT_SCORE_CAPS,
    SCORE_BANDS,
    build_loop_effectiveness,
    build_repair_progress,
    load_slo_config,
)
from loop_core.schemas.evidence_state import (
    EvidenceState,
    apply_score_cap,
    score_cap_for_state,
)

# 评分/证据 advisory 符号黑名单 —— gate 判定路径模块源码中不得出现。
ADVISORY_SYMBOLS = (
    "score_cap", "score_band", "evidence_score", "apply_score_cap",
    "evidence_state", "EvidenceState",
)
GATE_DECISION_MODULES = (
    "loop_core/state_machine.py",
    "hooks/scripts/gate_guard.py",
    "loop_core/enforcement.py",
    "loop_core/hard_constraints.py",
    "loop_core/guard_health.py",
    "loop_core/slo_gate.py",
    "loop_core/approval_ledger.py",
)


# ═══════════════════════════════════════════════════════════════════════════
# 七态枚举
# ═══════════════════════════════════════════════════════════════════════════

class TestEvidenceStateEnum:
    def test_seven_states_exact(self):
        assert EvidenceState.values() == (
            "Present", "Wired", "Exercised", "Outcome-supported",
            "Missing", "Unobserved", "N-A",
        )
        assert len(EvidenceState) == 7

    def test_coerce_roundtrip(self):
        for state in EvidenceState:
            assert EvidenceState.coerce(state.value) is state
            assert EvidenceState.coerce(state) is state

    def test_coerce_normalizes_variants(self):
        assert EvidenceState.coerce("outcome-supported") is EvidenceState.OUTCOME_SUPPORTED
        assert EvidenceState.coerce("Outcome Supported") is EvidenceState.OUTCOME_SUPPORTED
        assert EvidenceState.coerce("n-a") is EvidenceState.N_A
        assert EvidenceState.coerce("") is EvidenceState.N_A
        assert EvidenceState.coerce(None) is EvidenceState.N_A

    def test_coerce_fail_closed(self):
        with pytest.raises(ValueError):
            EvidenceState.coerce("Definitely-Not-A-State")


# ═══════════════════════════════════════════════════════════════════════════
# GateLesson.evidence_state
# ═══════════════════════════════════════════════════════════════════════════

class TestGateLessonEvidenceState:
    def test_record_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            lesson, created = record_gate_lesson(
                td, gate_id="G-TEST-1", task_id="T-1", decision="rejected",
                reason_category="evidence", reason_text="no proof",
                evidence_state="Unobserved",
            )
            assert created is True
            assert lesson.evidence_state == "Unobserved"
            # to_dict -> from_dict 往返
            again = GateLesson.from_dict(lesson.to_dict())
            assert again.evidence_state == "Unobserved"

    def test_default_is_n_a(self):
        with tempfile.TemporaryDirectory() as td:
            lesson, _ = record_gate_lesson(
                td, gate_id="G-TEST-2", task_id="T-1", decision="approved",
                reason_category="scope", reason_text="ok",
            )
            assert lesson.evidence_state == "N-A"

    def test_legacy_record_without_field_loads_as_n_a(self):
        """旧记录（无 evidence_state 字段）向后兼容 → N-A。"""
        legacy = {
            "lesson_id": "GL-LEGACY",
            "gate_id": "G-TEST-3", "task_id": "T-1",
            "decision": "approved", "reason_category": "scope",
            "reason_text": "ok", "recorded_at": "2026-01-01T00:00:00+00:00",
        }
        lesson = GateLesson.from_dict(legacy)
        assert lesson.evidence_state == "N-A"

    def test_invalid_state_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(InvalidLessonError):
                record_gate_lesson(
                    td, gate_id="G-TEST-4", task_id="T-1", decision="rejected",
                    reason_category="evidence", reason_text="x",
                    evidence_state="NotAState",
                )


# ═══════════════════════════════════════════════════════════════════════════
# 评分上限表（AC-03 分档边界 59/74/84/94/100）
# ═══════════════════════════════════════════════════════════════════════════

class TestScoreCapTable:
    def test_bands_exact(self):
        assert SCORE_BANDS == (59, 74, 84, 94, 100)

    def test_state_to_cap_mapping(self):
        assert score_cap_for_state("Missing") == 59
        assert score_cap_for_state("Unobserved") == 59
        assert score_cap_for_state("N-A") == 59
        assert score_cap_for_state("Present") == 74
        assert score_cap_for_state("Wired") == 84
        assert score_cap_for_state("Exercised") == 94
        assert score_cap_for_state("Outcome-supported") == 100

    @pytest.mark.parametrize("cap", [59, 74, 84, 94, 100])
    def test_boundary_equality(self, cap):
        """分档边界等值断言：raw == cap → score == cap（不被压档）。"""
        assert apply_score_cap(cap, cap) == cap

    @pytest.mark.parametrize("cap", [59, 74, 84, 94, 100])
    def test_above_cap_capped(self, cap):
        """raw 超过上限 → 压到 cap。"""
        assert apply_score_cap(100, cap) == cap

    def test_below_cap_kept(self):
        assert apply_score_cap(58, 59) == 58
        assert apply_score_cap(73, 74) == 73
        assert apply_score_cap(83, 84) == 83
        assert apply_score_cap(93, 94) == 93
        assert apply_score_cap(99, 100) == 99

    def test_slo_yaml_externalized_caps(self):
        """slo.yaml 显式化 score_caps（配置外置模式），与默认表一致。"""
        cfg = load_slo_config(PROJECT_ROOT)
        caps = cfg["score_caps"]
        assert caps == DEFAULT_SCORE_CAPS
        assert caps["Present"] == 74
        assert caps["Outcome-supported"] == 100

    def test_slo_yaml_caps_override(self):
        """slo.yaml 显式覆盖生效；非法上限 fail-closed。"""
        import yaml
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".ai").mkdir()
            (root / ".ai" / "slo.yaml").write_text(
                "schema_version: 1\nscore_caps:\n  Present: 80\n", encoding="utf-8"
            )
            cfg = load_slo_config(root)
            assert cfg["score_caps"]["Present"] == 80
            assert cfg["score_caps"]["Wired"] == 84  # 未覆盖项保持默认
            (root / ".ai" / "slo.yaml").write_text(
                "score_caps:\n  Bogus-State: 100\n", encoding="utf-8"
            )
            from loop_core.governance_metrics import DataSourceUnavailableError
            with pytest.raises(DataSourceUnavailableError):
                load_slo_config(root)
            (root / ".ai" / "slo.yaml").write_text(
                "score_caps:\n  Present: -5\n", encoding="utf-8"
            )
            with pytest.raises(DataSourceUnavailableError):
                load_slo_config(root)


# ═══════════════════════════════════════════════════════════════════════════
# Repair Progress / Loop Effectiveness 分离指标
# ═══════════════════════════════════════════════════════════════════════════

class TestRepairLoopSeparation:
    @staticmethod
    def _ctx(gates, tasks=None):
        from loop_core.governance_metrics import SliContext
        return SliContext(
            gates=gates, tasks=tasks or [], transitions=None,
            guard_events=None, executions=None, drift_events=None,
            guard_decisions=None, rework_by_task={}, rework_total=0,
            completed_tasks=0,
        )
    @staticmethod
    def _gate(gid, task, status, recorded_at):
        from loop_core.governance_metrics import GateMetric
        from datetime import datetime, timezone
        return GateMetric(
            gate_id=gid, task_id=task, gate_type="user-approval",
            status=status, decision=status, phase="S6-delivery",
            requested_at=None, recorded_at=datetime.fromisoformat(recorded_at),
            evidence=None,
        )

    def test_repair_progress_counts(self):
        gates = [
            self._gate("G-1", "T-1", "rejected", "2026-07-01T00:00:00+00:00"),
            self._gate("G-2", "T-1", "approved", "2026-07-02T00:00:00+00:00"),  # 修复 GO
            self._gate("G-3", "T-2", "rejected", "2026-07-03T00:00:00+00:00"),  # 未修复
            self._gate("G-4", "T-3", "approved", "2026-07-04T00:00:00+00:00"),  # 无 prior
        ]
        # rework_total 与 build_report 同源口径（rework_cycles_from_gates 合计）
        from loop_core.governance_metrics import SliContext
        ctx = SliContext(
            gates=gates, tasks=[], transitions=None,
            guard_events=None, executions=None, drift_events=None,
            guard_decisions=None, rework_by_task={"T-1": 1, "T-2": 1},
            rework_total=2, completed_tasks=0,
        )
        report = build_repair_progress(ctx)
        assert report["repair_triggers"] == 2
        assert report["fixed_gates"] == 1
        assert report["repair_progress"] == 0.5
        # 分离：Loop Effectiveness 独立字段（4 个已决 gate，2 approved）
        eff = build_loop_effectiveness(ctx)
        assert eff["gate_pass_rate"]["value"] == 2 / 4
        assert eff["rework_total"]["value"] == 2

    def test_repair_progress_not_available(self):
        ctx = self._ctx(None)
        assert build_repair_progress(ctx)["status"] == "NOT_AVAILABLE"
        eff = build_loop_effectiveness(ctx)
        assert eff["gate_pass_rate"]["status"] == "NOT_AVAILABLE"

    def test_cycle_time_in_loop_effectiveness(self):
        from loop_core.governance_metrics import TaskRecord
        tasks = [
            TaskRecord(task_id="T-1", status="completed", phase="S6-delivery",
                       created_at=None, updated_at=None),
        ]
        ctx = self._ctx([self._gate("G-1", "T-1", "approved",
                                    "2026-07-01T00:00:00+00:00")], tasks=tasks)
        eff = build_loop_effectiveness(ctx)
        assert eff["status"] == "computed"
        assert "task_cycle_time" in eff
        assert eff["gate_pass_rate"]["value"] == 1.0


# ═══════════════════════════════════════════════════════════════════════════
# AC-03 静态断言：评分不进 gate 决策
# ═══════════════════════════════════════════════════════════════════════════

class TestAdvisoryStaticAssertions:
    def test_gate_decision_modules_do_not_reference_advisory_symbols(self):
        """AST 扫描：gate 判定路径模块源码不含任何评分/证据状态符号。"""
        for rel in GATE_DECISION_MODULES:
            source = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            tree = ast.parse(source)
            identifiers: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    identifiers.add(node.id)
                elif isinstance(node, ast.Attribute):
                    identifiers.add(node.attr)
            hit = identifiers & set(ADVISORY_SYMBOLS)
            assert not hit, f"{rel} 引用了 advisory 评分符号: {sorted(hit)}"

    def test_can_approve_gate_body_has_no_score_logic(self):
        """state_machine.can_approve_gate 函数体不含评分符号（函数级断言）。"""
        source = (PROJECT_ROOT / "loop_core" / "state_machine.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        targets = {"can_approve_gate", "can_transition_phase"}
        found = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                 and n.name in targets]
        assert found, "state_machine 未找到判定函数"
        for fn in found:
            identifiers: set[str] = set()
            for node in ast.walk(fn):
                if isinstance(node, ast.Name):
                    identifiers.add(node.id)
                elif isinstance(node, ast.Attribute):
                    identifiers.add(node.attr)
            hit = identifiers & set(ADVISORY_SYMBOLS)
            assert not hit, (
                f"state_machine.{fn.name} 引用了 advisory 评分符号: {sorted(hit)}"
            )

    def test_hooks_do_not_gain_score_symbols(self):
        """hooks/ 目录（除白名单常量表外零改动）不含评分符号。"""
        hooks_dir = PROJECT_ROOT / "hooks"
        offenders = []
        for path in sorted(hooks_dir.rglob("*.py")):
            text = path.read_text(encoding="utf-8", errors="replace")
            for sym in ADVISORY_SYMBOLS:
                if sym in text:
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{sym}")
        assert not offenders, f"hooks/ 出现 advisory 符号: {offenders}"
