"""
Governance metrics — DORA 指标构建层（T-0110 批 B-1 拆分产物）。

从 loop_core/governance_metrics.py 外提（design-common-weakness.md 1.2 边界：
"DORA 指标构建（build_dora_metrics/_sha256/git_commit）:1012-1183"）。

语义必须保持：
- ``build_dora_metrics`` 的 NOT_AVAILABLE / advisory 逐项标注（T-0100 F-05，
  未接线源不驱动整体 NOT_VERIFIED）；
- ``_sha256``/``git_commit`` 供报告绑定（ReportBinding-style）使用，语义不变。

依赖：governance_aggregations（叶子）→ slo_evaluator（_metric/_not_available/
NOT_AVAILABLE）→ 本模块。public 面由 governance_metrics 壳 re-export 保持。
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from loop_core.governance_aggregations import (
    _DECIDED_STATUSES,
    SliContext,
    approval_latency_stats,
    drift_event_counts,
    execution_cycle_stats,
    gate_decision_coverage,
    gate_rejection_rate,
    guard_anomaly_rates,
    phase_dwell_stats,
    rework_cycles_from_transitions,
    task_cycle_time_stats,
)
from loop_core.slo_evaluator import NOT_AVAILABLE, _metric, _not_available


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(root: str | Path) -> str:
    """HEAD commit of the repository, or '' when unavailable."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def build_dora_metrics(ctx: SliContext) -> dict[str, Any]:
    """Loop-DORA metric catalog (B2 §2.2) computed from the loaded datasets."""
    dora: dict[str, Any] = {}

    # gate rejection rate — overall / per phase / per gate type
    if ctx.gates is None:
        dora["gate_rejection_rate"] = _not_available("gates register unavailable")
        dora["gate_rejection_rate_by_phase"] = _not_available("gates register unavailable")
        dora["gate_rejection_rate_by_gate_type"] = _not_available("gates register unavailable")
    else:
        overall = gate_rejection_rate(ctx.gates)
        by_phase: dict[str, Any] = {}
        for phase in sorted({g.phase for g in ctx.gates if g.phase}):
            rate = gate_rejection_rate(ctx.gates, phase=phase)
            if rate is not None:
                by_phase[phase] = round(rate, 4)
        by_type: dict[str, Any] = {}
        for gtype in sorted({g.gate_type for g in ctx.gates if g.gate_type}):
            subset = [g for g in ctx.gates if g.gate_type == gtype]
            rate = gate_rejection_rate(subset)
            if rate is not None:
                by_type[gtype] = round(rate, 4)
        unmapped = len([g for g in ctx.gates if g.phase is None])
        decided = len([g for g in ctx.gates if g.status in _DECIDED_STATUSES])
        dora["gate_rejection_rate"] = _metric(
            round(overall, 4) if overall is not None else None,
            status="computed" if overall is not None else NOT_AVAILABLE,
            basis="rejected / (approved + rejected)",
        )
        dora["gate_rejection_rate_by_phase"] = _metric(
            by_phase, phase_unmapped_gates=unmapped, decided_gates=decided,
        )
        dora["gate_rejection_rate_by_gate_type"] = _metric(by_type)

    # gate decision coverage
    if ctx.gates is None:
        dora["gate_decision_coverage"] = _not_available("gates register unavailable")
    else:
        coverage = gate_decision_coverage(ctx.gates)
        dora["gate_decision_coverage"] = _metric(
            round(coverage, 4) if coverage is not None else None,
            status="computed" if coverage is not None else NOT_AVAILABLE,
            basis="decided with evidence / decided",
        )

    # approval latency
    if ctx.gates is None:
        dora["approval_latency"] = _not_available("gates register unavailable")
    else:
        stats = approval_latency_stats(ctx.gates)
        dora["approval_latency"] = (
            _metric(stats) if stats is not None
            else _not_available("no gate with both requested_at and recorded_at")
        )

    # task cycle time (created_at -> updated_at; task_graph schema has no
    # completed_at — basis is explicit so the number is not over-claimed)
    if ctx.tasks is None:
        dora["task_cycle_time"] = _not_available("task graph unavailable")
    else:
        stats = task_cycle_time_stats(ctx.tasks)
        dora["task_cycle_time"] = (
            _metric(stats) if stats is not None
            else _not_available("no task with both created_at and updated_at")
        )

    # phase dwell time — needs the transition journal (B2 §2.2)
    if ctx.transitions is None:
        dora["phase_dwell_time"] = _not_available(
            "phase_transitions.jsonl absent (transition journal not yet wired — "
            "wave 2 item per B2 §2.2)",
            advisory=True,
        )
    else:
        stats = phase_dwell_stats(ctx.transitions)
        dora["phase_dwell_time"] = (
            _metric(stats) if stats is not None
            else _not_available("transition journal has no dwell intervals")
        )

    # rework cycles — gates-based (register) + transitions-based (journal)
    if ctx.gates is None:
        dora["task_rework_cycles"] = _not_available("gates register unavailable")
    else:
        dora["task_rework_cycles"] = _metric(
            ctx.rework_by_task,
            total=ctx.rework_total,
            basis="rejected gates per task (rejection -> fix -> re-audit)",
        )
    if ctx.transitions is None:
        dora["rework_cycles_from_transitions"] = _not_available(
            "phase_transitions.jsonl absent", advisory=True
        )
    else:
        bounces = rework_cycles_from_transitions(ctx.transitions)
        dora["rework_cycles_from_transitions"] = _metric(
            bounces, total=sum(bounces.values()),
            basis="S5-quality -> S4-implementation bounces per task",
        )

    # guard anomaly rate — from the U8 guard event file
    if ctx.guard_events is None:
        dora["guard_anomaly_rate"] = _not_available("guard-events.jsonl unavailable")
        dora["guard_events_summary"] = _not_available("guard-events.jsonl unavailable")
    elif not ctx.guard_events:
        dora["guard_anomaly_rate"] = _not_available(
            "guard-events.jsonl contains no events"
        )
        dora["guard_events_summary"] = _not_available(
            "guard-events.jsonl contains no events"
        )
    else:
        rates = guard_anomaly_rates(ctx.guard_events)
        dora["guard_anomaly_rate"] = _metric(
            rates["anomaly_rate"], total_events=rates["total_events"],
            by_guard=rates["by_guard"],
            basis="FAIL events / total guard-check events (U8 guard-events.jsonl)",
        )
        dora["guard_events_summary"] = _metric({
            "by_result": rates["by_result"],
            "by_check_type": rates["by_check_type"],
        })

    # guard block/pass/error rates — needs the hook decision log
    dora["guard_block_pass_error_rates"] = _not_available(
        "guard_decisions.jsonl absent (hook decision log not yet wired — B2 §2.2)",
        advisory=True,
    )

    # drift events — needs the runtime events ledger
    if ctx.drift_events is None:
        dora["drift_events"] = _not_available(
            "runtime-events.jsonl absent (drift source not yet wired)",
            advisory=True,
        )
    else:
        dora["drift_events"] = _metric(drift_event_counts(ctx.drift_events))

    # evidence regeneration — no reliable source in wave 1 (empty
    # evidence_refs would fabricate a meaningless zero)
    dora["evidence_regeneration_events"] = _not_available(
        "evidence freshness (C8) re-run events not yet recorded",
        advisory=True,
    )

    # execution cycle time — from the execution ledger
    if ctx.executions is None:
        dora["execution_cycle_time"] = _not_available("execution ledger unavailable")
    else:
        stats = execution_cycle_stats(ctx.executions)
        dora["execution_cycle_time"] = (
            _metric(stats) if stats is not None
            else _not_available("no completed execution with launched_at/completed_at")
        )

    return dora
