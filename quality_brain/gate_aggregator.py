"""Gate 决策矩阵 — 汇总所有质量报告，做出 GO/BLOCKED/CONDITIONAL 决策。

这是整个系统最关键的部分：不依赖 LLM 的判断，只认确定性证据。
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .core import Violation


class GateDecision(Enum):
    GO = "GO"                    # 全部通过
    BLOCKED = "BLOCKED"          # 存在 BLOCKER，打回
    CONDITIONAL_GO = "CONDITIONAL_GO"  # 有 WARNING 但无 BLOCKER


@dataclass
class GateResult:
    """Gate 决策结果。"""
    decision: GateDecision
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reports: dict = field(default_factory=dict)
    summary: str = ""

    def is_go(self) -> bool:
        return self.decision == GateDecision.GO

    def is_blocked(self) -> bool:
        return self.decision == GateDecision.BLOCKED


class GateAggregator:
    """Gate 决策聚合器。"""

    # 质量门禁阈值
    THRESHOLDS = {
        'lint_errors': 0,
        'test_pass_rate': 100,
        'coverage': 80,
        'critical_vulns': 0,
    }

    def evaluate(self, quality_reports: dict, brain_violations: list[Violation],
                 phase: str = "") -> GateResult:
        """
        根据所有报告和 Quality Brain 违规做出 Gate 决策。

        Args:
            quality_reports: 各角色的质量报告 dict
            brain_violations: Quality Brain 检出违规列表
            phase: 当前阶段
        """
        blockers = []
        warnings = []

        # ── 规则 1：Quality Brain BLOCKER → 无条件阻断 ──
        brain_blockers = [v for v in brain_violations if v.is_blocker()]
        for v in brain_blockers:
            blockers.append(f"[{v.rule_id}] {v.message} ({v.file_path}:{v.line_number})")

        brain_highs = [v for v in brain_violations if v.severity.value == 'HIGH']
        for v in brain_highs:
            warnings.append(f"[{v.rule_id}] {v.message} ({v.file_path}:{v.line_number})")

        # ── 规则 2：质量门禁 ──
        quality = quality_reports.get('quality-engineer', {})
        if quality.get('lint_errors', 999) > self.THRESHOLDS['lint_errors']:
            blockers.append(f"Lint 错误: {quality['lint_errors']} > {self.THRESHOLDS['lint_errors']}")
        if quality.get('test_pass_rate', 0) < self.THRESHOLDS['test_pass_rate']:
            blockers.append(f"测试通过率: {quality['test_pass_rate']}% < {self.THRESHOLDS['test_pass_rate']}%")
        if quality.get('coverage', 0) < self.THRESHOLDS['coverage']:
            blockers.append(f"覆盖率: {quality['coverage']}% < {self.THRESHOLDS['coverage']}%")

        # ── 规则 3：安全扫描 ──
        security = quality_reports.get('security-engineer', {})
        if security.get('critical', 0) > self.THRESHOLDS['critical_vulns']:
            blockers.append(f"CRITICAL 安全漏洞: {security['critical']} 个")
        if security.get('high', 0) > 0:
            warnings.append(f"HIGH 安全漏洞: {security['high']} 个")

        # ── 规则 4：独立评审 ──
        review = quality_reports.get('independent-reviewer', {})
        if review.get('verdict') == 'REJECTED':
            blockers.append("独立评审: REJECTED")
        elif review.get('verdict') == 'CHANGES_REQUESTED':
            warnings.append("独立评审: CHANGES_REQUESTED")

        # ── 规则 5：证据完整性 ──
        evidence = quality_reports.get('evidence-verifier', {})
        if evidence.get('missing', 0) > 0:
            blockers.append(f"证据缺失: {evidence['missing']} 项")
        if evidence.get('stale', 0) > 0:
            blockers.append(f"证据过期: {evidence['stale']} 项")
        if evidence.get('forged', 0) > 0:
            blockers.append(f"疑似伪造证据: {evidence['forged']} 项")

        # ── 规则 6：合约验证 ──
        contract = quality_reports.get('contract-verifier', {})
        if contract.get('blockers', 0) > 0:
            blockers.append(f"合约违规 (BLOCKER): {contract['blockers']} 项")

        # ── 规则 7：导入检查 ──
        imports = quality_reports.get('import-checker', {})
        if imports.get('undeclared', 0) > 0:
            blockers.append(f"未声明的 import: {imports['undeclared']} 项")

        # ── 决策 ──
        if blockers:
            decision = GateDecision.BLOCKED
            summary = f"❌ BLOCKED — {len(blockers)} 个阻断项, {len(warnings)} 个警告"
        elif warnings:
            decision = GateDecision.CONDITIONAL_GO
            summary = f"⚠️ CONDITIONAL GO — {len(warnings)} 个警告需要关注"
        else:
            decision = GateDecision.GO
            summary = f"✅ GO — 全部检查通过"

        return GateResult(
            decision=decision,
            blockers=blockers,
            warnings=warnings,
            reports=quality_reports,
            summary=summary,
        )

    def present_to_user(self, result: GateResult) -> str:
        """生成人类可读的 Gate 呈现文本。"""
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"  Gate 决策: {result.summary}")
        lines.append(f"{'='*60}")

        if result.blockers:
            lines.append(f"\n🔴 阻断项 ({len(result.blockers)}):")
            for b in result.blockers:
                lines.append(f"   • {b}")

        if result.warnings:
            lines.append(f"\n🟡 警告项 ({len(result.warnings)}):")
            for w in result.warnings[:10]:
                lines.append(f"   • {w}")
            if len(result.warnings) > 10:
                lines.append(f"   ... 还有 {len(result.warnings) - 10} 项")

        lines.append(f"\n{'='*60}")
        if result.is_blocked():
            lines.append("  请修复以上阻断项后重新提交。")
        elif result.decision == GateDecision.CONDITIONAL_GO:
            lines.append("  请审阅警告项后决定是否继续。输入「批准」继续或「拒绝」返回。")
        else:
            lines.append("  输入「批准」进入下一阶段。")
        lines.append(f"{'='*60}\n")

        return '\n'.join(lines)


def evaluate_gate(phase: str, quality_reports: dict,
                  brain_violations: list[Violation]) -> GateResult:
    """便捷函数：评估 Gate。"""
    aggregator = GateAggregator()
    return aggregator.evaluate(quality_reports, brain_violations, phase)
