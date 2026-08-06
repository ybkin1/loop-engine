"""intent_router_modes.py — 路由模式/快照类型外部模块（T-0124 拆分）。

从 loop_core/intent_router.py 拆出：`_phases_for_mode` / `_analysis_to_profile` /
`ActiveTaskSnapshot` / `TaskFrame` / `RoutedIntent`（U5 粘性路由结构，原样
提取；壳符号一律函数/方法内延迟 import，避免循环导入）。行为逐字节等价。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

def _phases_for_mode(mode) -> list[str]:
    """Return the recommended phases for a given mode.

    Mirrors the logic in router.route_intent() for consistency.
    """
    from loop_core.router import LoopMode
    if mode == LoopMode.LIGHTWEIGHT:
        return ["S0-init", "S4-implementation", "S6-delivery"]
    if mode == LoopMode.STANDARD:
        return [
            "S0-init", "S1-requirements", "S2-architecture",
            "S4-implementation", "S5-quality", "S6-delivery",
        ]
    return [
        "S0-init", "S1-requirements", "S2-architecture", "S3-interface",
        "S4-implementation", "S5-quality", "S6-delivery",
        "S7-integration", "S8-functional-test", "S9-fix-optimize",
        "S10-performance", "S11-maintenance",
    ]


def _analysis_to_profile(analysis) -> Any:
    """Convert an IntentAnalysis to a ProjectProfile for router.py compat."""
    from loop_core.router import ProjectProfile
    rf = analysis.risk_factors
    return ProjectProfile(
        description=analysis.description,
        has_multiple_modules=rf.get("has_multiple_modules", False),
        has_database=rf.get("has_database", False),
        has_auth_permissions=rf.get("has_auth_permissions", False),
        has_payments=rf.get("has_payments", False),
        has_production_data=rf.get("has_production_data", False),
        has_external_api=rf.get("has_external_api", False),
        has_concurrency_performance=rf.get("has_concurrency_performance", False),
        has_security_requirements=rf.get("has_security_requirements", False),
        requires_deployment=rf.get("requires_deployment", False),
        requires_monitoring_rollback=rf.get("requires_monitoring_rollback", False),
        requires_ongoing_iteration=rf.get("requires_ongoing_iteration", False),
        has_high_uncertainty=rf.get("has_high_uncertainty", False),
    )

@dataclass
class ActiveTaskSnapshot:
    """Immutable snapshot of the active task used for sticky routing.

    Built from state.task_graph.yaml entries via :meth:`from_task` (or
    directly by callers).  Only the fields the router needs are kept —
    this is a routing input, not an authority on task state.
    """

    task_id: str
    status: str = "active"
    title: str = ""
    domain: str = ""
    description: str = ""
    loop_mode: Any = None  # LoopMode（from_task 延迟解析）

    @property
    def is_active(self) -> bool:
        """True when the task can still receive work (sticky applies)."""
        return self.status in ("active", "in_progress", "ACTIVE", "IN_PROGRESS")

    @staticmethod
    def from_task(task: dict) -> "ActiveTaskSnapshot":
        from loop_core.router import LoopMode
        """Build a snapshot from a task_graph.yaml task entry (dict).

        Unknown/missing loop_mode falls back to LIGHTWEIGHT; unknown status
        defaults to "active" (the router never hard-fails on shape drift).
        """
        raw_mode = task.get("loop_mode") or task.get("mode")
        mode = LoopMode.LIGHTWEIGHT
        if isinstance(raw_mode, str):
            mode = {m.name: m for m in LoopMode}.get(
                raw_mode.upper(), LoopMode.LIGHTWEIGHT
            )
        return ActiveTaskSnapshot(
            task_id=str(task.get("id") or task.get("task_id") or ""),
            status=str(task.get("status") or "active"),
            title=str(task.get("title") or ""),
            domain=str(task.get("domain") or ""),
            description=str(task.get("description") or ""),
            loop_mode=mode,
        )


@dataclass
class TaskFrame:
    """One task frame in a multi-intent round (U5).

    The main frame (``is_main=True``, ``frame_id == 0``) expresses the
    first intent and carries the sticky target when sticky routing
    applies.  Follow-up frames are new tasks to orchestrate in order
    after the main one (their ``task_id`` is None until created).

    The frame shape is compatible with task files / task_graph.yaml
    entries: see :meth:`to_task_dict`.
    """

    frame_id: int
    intent: str
    task_id: str | None
    domain: str
    complexity_score: float
    recommended_mode: LoopMode
    change_type: ChangeType
    confidence: float
    reasoning: str
    is_main: bool
    detected_domains: list[str] = field(default_factory=list)
    suggested_phases: list[str] = field(default_factory=list)

    def to_task_dict(self) -> dict:
        """Return a dict compatible with task_graph.yaml task entries.

        Maps task_id/intent/domain/complexity onto the task-file shape
        (id/title/status/phase/loop_mode + routing estimates).  The
        ``phase`` follows the change-type entry-phase table used across
        the codebase.
        """
        from loop_core.intent_router import CHANGE_TYPE_TO_ENTRY_PHASE
        return {
            "id": self.task_id,
            "title": self.intent,
            "status": "planned",
            "phase": CHANGE_TYPE_TO_ENTRY_PHASE.get(self.change_type, "S0-init"),
            "loop_mode": self.recommended_mode.name,
            "domains": list(self.detected_domains),
            "complexity_score": round(self.complexity_score, 3),
        }


@dataclass
class RoutedIntent:
    """Output of the upgraded routing entry point (U5).

    Backward-compatible core: ``analysis`` is the primary
    :class:`IntentAnalysis` (frame 0) and ``route_result`` is the
    canonical :class:`RouteResult` for it — existing callers can keep
    using those two fields unchanged.

    Incremental fields:
      - ``sticky`` / ``sticky_basis`` / ``sticky_task_id`` — sticky
        routing marker + evidence.
      - ``task_frames`` — ordered frames for multi-intent rounds (main
        frame first).
      - ``degraded`` / ``degraded_reason`` — fail-safe degradation flag
        (keep-status-quo result; no new intents guessed).
    """

    analysis: IntentAnalysis | None
    route_result: RouteResult | None
    sticky: bool = False
    sticky_basis: str = ""
    sticky_task_id: str | None = None
    task_frames: list[TaskFrame] = field(default_factory=list)
    intents: list[str] = field(default_factory=list)
    degraded: bool = False
    degraded_reason: str = ""

    @property
    def main_frame(self) -> TaskFrame | None:
        """The main (first) task frame, if any."""
        return self.task_frames[0] if self.task_frames else None




def _status_quo_route_result(mode) -> Any:
    """RouteResult for the fail-safe status-quo path (no intent guessed)."""
    from loop_core.router import LoopMode, RiskLevel, RouteResult
    if mode == LoopMode.LIGHTWEIGHT:
        return RouteResult(
            mode=LoopMode.LIGHTWEIGHT,
            risk_level=RiskLevel.LOW,
            reason="Fail-safe status quo: keep lightweight routing, no new intent guessed.",
            recommended_phases=["S0-init", "S4-implementation", "S6-delivery"],
        )
    if mode == LoopMode.STANDARD:
        return RouteResult(
            mode=LoopMode.STANDARD,
            risk_level=RiskLevel.MEDIUM,
            reason="Fail-safe status quo: keep standard routing, no new intent guessed.",
            recommended_phases=[
                "S0-init", "S1-requirements", "S2-architecture",
                "S4-implementation", "S5-quality", "S6-delivery",
            ],
        )
    return RouteResult(
        mode=LoopMode.FULL,
        risk_level=RiskLevel.HIGH,
        reason="Fail-safe status quo: keep full routing, no new intent guessed.",
        recommended_phases=[
            "S0-init", "S1-requirements", "S2-architecture", "S3-interface",
            "S4-implementation", "S5-quality", "S6-delivery",
            "S7-integration", "S8-functional-test", "S9-fix-optimize",
            "S10-performance", "S11-maintenance",
        ],
    )


def _degraded_result(
    description: str,
    active_task: ActiveTaskSnapshot | None,
    reason: str,
) -> RoutedIntent:
    """Fail-safe degraded result: keep the status quo, guess nothing new.

    - With an active task → keep routing to that task (sticky) and keep
      its loop mode.
    - Without an active task → default LIGHTWEIGHT routing.

    Never raises and never fabricates new intents (``task_frames`` stays
    empty).  This is a routing-only degradation — constraint adjudication
    in the hook layer is untouched (fail-closed semantics unchanged).
    """
    from loop_core.router import LoopMode
    if active_task is not None and active_task.is_active and active_task.task_id:
        mode = active_task.loop_mode or LoopMode.LIGHTWEIGHT
        return RoutedIntent(
            analysis=None,
            route_result=_status_quo_route_result(mode),
            sticky=True,
            sticky_basis=(
                f"Fail-safe: keeping active task {active_task.task_id} "
                f"(routing error: {reason})"
            ),
            sticky_task_id=active_task.task_id,
            task_frames=[],
            intents=[],
            degraded=True,
            degraded_reason=f"Fail-safe degradation — {reason}",
        )
    return RoutedIntent(
        analysis=None,
        route_result=_status_quo_route_result(LoopMode.LIGHTWEIGHT),
        sticky=False,
        sticky_basis="",
        sticky_task_id=None,
        task_frames=[],
        intents=[],
        degraded=True,
        degraded_reason=f"Fail-safe degradation — {reason}",
    )


