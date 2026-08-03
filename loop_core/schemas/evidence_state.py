"""
EvidenceState — 证据七态枚举（T-0109 F1 评估模型）。

七态描述一条 gate 证据从"登记存在"到"结果支撑结论"的成熟度阶梯，
**只用于呈现/度量（advisory），不进入任何 gate 判定路径**：

    Present            证据已登记/存在（文件或记录在案）
    Wired              证据已接线到消费方（被 gate 检查路径实际引用）
    Exercised          证据已被实际执行/触发（有运行记录）
    Outcome-supported  证据有结果支撑（运行输出直接支撑 gate 结论）
    Missing            应存在但缺失（fail-closed 描述，不替代哈希校验）
    Unobserved         未观测（源不可用/未接线，绝不生成行为性结论）
    N-A                不适用（该 gate 不需要此类证据）

设计约束（design-bh-integration.md F1「必须保持」）：
- 七态仅描述验证结果，不替代 evidence_chain/execution_ledger 的
  root_hash 哈希校验（防篡改机制不动）。
- Missing/Unobserved 不得"自动通过"任何门禁（fail-closed 语义不变）；
  本模块不提供任何 gate 判定函数，评分消费方仅做呈现。
- 审批闭环（approval_ledger / state_machine.can_approve_gate）零改动。

对齐：gate_feedback.GateLesson.evidence_state、governance_metrics 评分
上限表（.ai/slo.yaml score_caps）按本枚举分档。
"""
from __future__ import annotations

from enum import Enum


class EvidenceState(str, Enum):
    """Gate 证据成熟度七态。str-Enum：可直接序列化进 lessons/报告。"""

    PRESENT = "Present"
    WIRED = "Wired"
    EXERCISED = "Exercised"
    OUTCOME_SUPPORTED = "Outcome-supported"
    MISSING = "Missing"
    UNOBSERVED = "Unobserved"
    N_A = "N-A"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        """全部七态字符串值（顺序即成熟度阶梯，测试与文档共用）。"""
        return (
            cls.PRESENT.value,
            cls.WIRED.value,
            cls.EXERCISED.value,
            cls.OUTCOME_SUPPORTED.value,
            cls.MISSING.value,
            cls.UNOBSERVED.value,
            cls.N_A.value,
        )

    @classmethod
    def coerce(cls, value: object) -> "EvidenceState":
        """把任意输入（str 值/枚举/None）规整为 EvidenceState。

        - 已是 EvidenceState → 原样返回。
        - 字符串（含大小写/连字符变体）匹配七态之一 → 返回对应枚举。
        - 空值/None → N_A（不适用，最保守的呈现档）。
        - 未知字符串 → ValueError（fail-closed：未知状态绝不静默猜测）。

        仅供呈现/记录用；任何判定路径不得消费本函数结果。
        """
        if isinstance(value, EvidenceState):
            return value
        if value is None or str(value).strip() == "":
            return cls.N_A
        text = str(value).strip()
        for state in cls:
            if text == state.value:
                return state
        lowered = text.casefold().replace("_", "-").replace(" ", "-")
        for state in cls:
            if state.value.casefold() == lowered:
                return state
        raise ValueError(
            f"非法 EvidenceState: {value!r}（允许 {cls.values()}）"
        )

    @classmethod
    def score_cap(cls, state: "EvidenceState | str | None") -> int:
        """证据成熟度对应的评分上限（59/74/84/94/100，advisory-only）。

        上限表（与 .ai/slo.yaml `score_caps` 节同源，本函数为代码默认值）：
            Missing / Unobserved / N-A  → 59（未验证，最高只能呈现 59 档）
            Present                      → 74（仅登记存在）
            Wired                        → 84（已接线到消费方）
            Exercised                    → 94（已实际执行）
            Outcome-supported            → 100（结果支撑结论）

        语义：evidence 评分 = min(原始评分, 状态上限)——证据成熟度决定
        评分天花板。**评分只呈现/度量，不进 gate 决策**（AC-03 静态断言
        覆盖：本函数与 gate 判定路径无引用关系）。
        """
        caps: dict[EvidenceState, int] = {
            cls.MISSING: 59,
            cls.UNOBSERVED: 59,
            cls.N_A: 59,
            cls.PRESENT: 74,
            cls.WIRED: 84,
            cls.EXERCISED: 94,
            cls.OUTCOME_SUPPORTED: 100,
        }
        return caps[cls.coerce(state)]


# 评分上限表（与 .ai/slo.yaml score_caps 默认值同源；slo.yaml 显式化后
# 以配置文件为准，本常量仅作代码默认兜底 —— 对齐 slo.yaml 既有配置外置模式）。
DEFAULT_SCORE_CAPS: dict[str, int] = {
    "Missing": 59,
    "Unobserved": 59,
    "N-A": 59,
    "Present": 74,
    "Wired": 84,
    "Exercised": 94,
    "Outcome-supported": 100,
}

# 分档断点（升序）——governance_metrics 分档边界单测按此断言。
SCORE_BANDS: tuple[int, ...] = (59, 74, 84, 94, 100)


def apply_score_cap(raw_score: float | int, cap: int) -> int:
    """raw_score 取上限后四舍五入为整数（advisory 呈现值）。

    apply_score_cap(raw, cap) == min(round(raw), cap) —— 分档边界等值
    断言：raw == cap 时结果 == cap；raw > cap 时被压到 cap。
    """
    value = int(round(float(raw_score)))
    return min(value, int(cap))


def score_cap_for_state(state: "EvidenceState | str | None",
                        caps: dict[str, int] | None = None) -> int:
    """按证据状态取评分上限（默认表 = DEFAULT_SCORE_CAPS，可注入
    .ai/slo.yaml 显式化后的 score_caps 配置）。"""
    table = dict(caps) if caps is not None else dict(DEFAULT_SCORE_CAPS)
    return int(table[EvidenceState.coerce(state).value])
