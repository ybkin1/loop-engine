from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PhaseSpec:
    phase_id: str
    name: str
    outcome: str
    required_roles: tuple[str, ...]
    internal_checks: tuple[str, ...]
    user_decision: str | None
    status: str = "required"
    merge_target: str | None = None
    tailoring_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_phases() -> tuple[PhaseSpec, ...]:
    return (
        PhaseSpec("P0", "启动与分级", "恢复上下文并确定项目模式", ("controller", "project-manager"), ("intent", "risk"), None),
        PhaseSpec("P1", "产品发现", "明确用户问题和目标", ("product-manager",), ("goal_traceability",), "目标是否正确"),
        PhaseSpec("P2", "需求基线", "冻结范围、验收和变更规则", ("product-manager", "quality-engineer"), ("requirements", "acceptance"), "是否接受需求基线"),
        PhaseSpec("P3", "整体架构", "冻结系统边界和重大架构取舍", ("system-architect", "security-engineer"), ("architecture", "security_boundary"), "是否接受重大架构方向"),
        PhaseSpec("P4", "详细设计", "冻结组件、接口、数据和调用契约", ("module-architect", "quality-engineer"), ("contract", "dependency"), None),
        PhaseSpec("P5", "质量与安全设计", "冻结测试策略、质量门禁和威胁控制", ("quality-engineer", "security-engineer"), ("quality", "security"), None),
        PhaseSpec("P6", "任务规划", "形成依赖图和工作包", ("project-manager", "controller"), ("acyclic_graph", "budget"), None),
        PhaseSpec("P7", "实现与单测", "实现批准的工作包并完成局部验证", ("developer", "quality-engineer"), ("write_scope", "tests"), None),
        PhaseSpec("P8", "集成与功能测试", "验证跨模块和用户路径", ("quality-engineer", "independent-reviewer"), ("integration", "regression"), None),
        PhaseSpec("P9", "非功能验证", "验证性能、安全、恢复和运行边界", ("quality-engineer", "security-engineer", "release-operations"), ("nonfunctional", "recovery"), None),
        PhaseSpec("P10", "交付准备", "形成可交付和可交接的完整包", ("delivery-manager", "release-operations"), ("readiness", "rollback"), None),
        PhaseSpec("P11", "用户验收", "让用户判断产品目标和可见行为是否满足", ("controller", "delivery-manager"), ("packet_complete",), "是否接受产品并继续"),
        PhaseSpec("P12", "运行维护", "处理监控、缺陷、变更和演进", ("project-manager", "release-operations"), ("change_traceability",), None),
    )
