"""
test_state_machine_gate_matching.py — T-0177 H3 回归测试。

验证 _check_single_constraint 的 gate 约束匹配从"子串匹配"改为"段边界匹配"：
- "S1-requirements-backup" 不得通过 "S1-requirements" 约束
- 真实阶段 gate（精确/前缀段/后缀段）仍能通过
- C6 独立评审约束同样走段边界匹配
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "loop_core")))

import pytest
from state_machine import _check_single_constraint, _gate_matches_phase


def _constraint(cid: str):
    """构造最小 PhaseConstraint（仅 constraint_id 字段参与匹配）。"""
    from dataclasses import dataclass, field
    from typing import Optional
    from enum import Enum

    class _Phase(Enum):
        S1 = "S1-requirements"

    @dataclass
    class _C:
        constraint_id: str
        description: str = ""
        blocker: bool = True

    return _C(constraint_id=cid)


class TestGateMatchesPhase:
    def test_exact_match(self):
        assert _gate_matches_phase("S1-requirements", "S1-requirements")

    def test_prefix_segment_match(self):
        assert _gate_matches_phase("S1-requirements-gate", "S1-requirements")

    def test_suffix_segment_match(self):
        assert _gate_matches_phase("G-T-0001-S1-requirements", "S1-requirements")

    def test_middle_segment_match(self):
        assert _gate_matches_phase("G-S1-requirements-FINAL", "S1-requirements")

    def test_backup_suffix_rejected(self):
        """H3 核心反例：S1-requirements-backup 不得通过 S1-requirements 约束。"""
        assert not _gate_matches_phase("S1-requirements-backup", "S1-requirements")

    def test_legacy_suffix_rejected(self):
        assert not _gate_matches_phase("S1-requirements-legacy", "S1-requirements")

    def test_no_boundary_rejected(self):
        assert not _gate_matches_phase("S1-requirementsbackup", "S1-requirements")

    def test_wrong_phase_rejected(self):
        assert not _gate_matches_phase("S2-architecture", "S1-requirements")


class TestCheckSingleConstraintGateMatching:
    def test_approved_exact_phase_satisfies(self):
        ok = _check_single_constraint(
            _constraint("C1-no-requirements"),
            approved_gate_ids={"S1-requirements"},
            task_has_active=False,
            verification_passed=False,
        )
        assert ok is True

    def test_approved_suffix_segment_satisfies(self):
        ok = _check_single_constraint(
            _constraint("C1-no-requirements"),
            approved_gate_ids={"G-T-0001-S1-requirements"},
            task_has_active=False,
            verification_passed=False,
        )
        assert ok is True

    def test_backup_gate_does_not_satisfy(self):
        """H3 核心反例（约束级）：仅批准 backup gate 时约束不满足。"""
        ok = _check_single_constraint(
            _constraint("C1-no-requirements"),
            approved_gate_ids={"S1-requirements-backup"},
            task_has_active=False,
            verification_passed=False,
        )
        assert ok is False

    def test_any_approved_phase_satisfies(self):
        ok = _check_single_constraint(
            _constraint("C2-no-architecture"),
            approved_gate_ids={"G-T-0001-S1-requirements", "S2-architecture"},
            task_has_active=False,
            verification_passed=False,
        )
        assert ok is True

    def test_independent_review_segment_matching(self):
        ok = _check_single_constraint(
            _constraint("C6-no-independent-review"),
            approved_gate_ids={"G-T-0001-independent-review"},
            task_has_active=True,
            verification_passed=True,
        )
        assert ok is True

    def test_independent_review_backup_rejected(self):
        ok = _check_single_constraint(
            _constraint("C6-no-independent-review"),
            approved_gate_ids={"independent-review-backup"},
            task_has_active=True,
            verification_passed=True,
        )
        assert ok is False
