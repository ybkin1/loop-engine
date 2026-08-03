"""
Governance metrics — 统计聚合与共享记录层（T-0110 批 B-1 拆分产物）。

从 loop_core/governance_metrics.py 外提（design-common-weakness.md 1.2 边界：
"统计聚合辅助（_percentile/_seconds_stats/_over_target 等）:130-157,808" 与
"保留"清单中的共享基础设施 —— 记录数据类 / 相位分类 / 时间与统计辅助 /
纯度量函数）。本模块是依赖图叶子（零 loop_core 内部依赖），供
governance_loaders / slo_evaluator / dora_metrics / governance_metrics 壳
共同消费，避免循环导入（"叶子先拆"）。

内容（原文件逐字迁移，行为零变化）：
- 相位分类：GATE_PHASE_TOKENS / classify_gate_phase
- 时间/统计辅助：_parse_dt / _percentile / _seconds_stats
- 记录数据类：GateMetric / TaskRecord / PhaseTransition / SliContext
- 纯度量函数：gate_rejection_rate / gate_decision_coverage /
  approval_latencies(_stats) / task_cycle_seconds(_stats) /
  phase_dwell_stats / rework_cycles_from_gates(_transitions) /
  guard_anomaly_rates / execution_cycle_stats / drift_event_counts
- 目标比较：_over_target

public 面由 governance_metrics 壳 re-export 保持（from loop_core.
governance_metrics import * 兼容）。
"""
from __future__ import annotations

import math
import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from loop_core.observability import GuardCheckEvent

# ── Phase classification ─────────────────────────────────────────────────
# Gate ids in this repository follow ``G-<scope>-<TASK>-<TOKEN>`` (e.g.
# G-T-0090-REQUIREMENTS).  The SLI table (B2 §1.2) is phase-scoped, so each
# gate is mapped to a phase deterministically from id tokens.  This is a
# documented naming-convention mapping (the register itself carries no phase
# field); a gate whose id matches no token is reported in the "unmapped"
# bucket and never assigned a phase by guessing.  Token order matters —
# longer/more specific tokens are tried first.
GATE_PHASE_TOKENS: tuple[tuple[str, str], ...] = (
    ("REQUIREMENTS", "S1-requirements"),
    ("REQUIREMENT", "S1-requirements"),
    ("ARCHITECTURE", "S2-architecture"),
    ("DESIGN", "S2-architecture"),
    ("INTERFACE", "S3-interface"),
    ("IMPLEMENTATION", "S4-implementation"),
    ("IMPLEMENT", "S4-implementation"),
    ("IMPL", "S4-implementation"),
    ("QUALITY", "S5-quality"),
    ("DELIVERY", "S6-delivery"),
)


def classify_gate_phase(gate_id: str | None) -> str | None:
    """Deterministic phase classification from the gate id token table.

    Returns ``None`` when no token matches — the gate is counted in the
    ``unmapped`` bucket of the report instead of being guessed into a phase.
    """
    if not gate_id:
        return None
    upper = gate_id.upper()
    for token, phase in GATE_PHASE_TOKENS:
        if token in upper:
            return phase
    return None


# ── Time helpers ─────────────────────────────────────────────────────────

def _parse_dt(value: Any) -> datetime | None:
    """Parse ISO-8601 timestamps (with tz, 'Z', or bare date).  Naive
    timestamps are treated as UTC; unparseable values yield None (the
    affected gate is excluded from timing metrics, never guessed)."""
    if value is None or value == "":
        return None
    try:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _percentile(sorted_values: Sequence[float], pct: float) -> float | None:
    """Nearest-rank percentile over an ascending-sorted sequence."""
    if not sorted_values:
        return None
    n = len(sorted_values)
    idx = max(0, min(n - 1, math.ceil(pct / 100.0 * n) - 1))
    return sorted_values[idx]


def _seconds_stats(values_seconds: Sequence[float]) -> dict[str, float] | None:
    """p50/p95/mean summary (seconds + hours) or None when empty."""
    if not values_seconds:
        return None
    s = sorted(float(v) for v in values_seconds)
    return {
        "count": len(s),
        "p50_seconds": round(_percentile(s, 50.0), 3),
        "p95_seconds": round(_percentile(s, 95.0), 3),
        "mean_seconds": round(statistics.fmean(s), 3),
        "p50_hours": round(_percentile(s, 50.0) / 3600.0, 3),
        "p95_hours": round(_percentile(s, 95.0) / 3600.0, 3),
        "mean_hours": round(statistics.fmean(s) / 3600.0, 3),
    }


# ── Records ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GateMetric:
    """One register entry of .ai/gates.yaml."""
    gate_id: str
    task_id: str
    gate_type: str
    status: str
    decision: str | None
    phase: str | None
    requested_at: datetime | None
    recorded_at: datetime | None
    evidence: str | None


@dataclass(frozen=True)
class TaskRecord:
    """One entry of .ai/task_graph.yaml."""
    task_id: str
    status: str
    phase: str | None
    created_at: datetime | None
    updated_at: datetime | None


@dataclass(frozen=True)
class PhaseTransition:
    """One append-only entry of .ai/ledger/phase_transitions.jsonl (B2 §2.2)."""
    task_id: str
    from_phase: str
    to_phase: str
    at: datetime


@dataclass(frozen=True)
class SliContext:
    """Datasets available to SLI evaluation.  A None dataset means the
    source is missing/unparseable (NOT_AVAILABLE), not empty."""
    gates: list[GateMetric] | None
    tasks: list[TaskRecord] | None
    transitions: list[PhaseTransition] | None
    guard_events: list[GuardCheckEvent] | None
    executions: list[dict] | None
    drift_events: list[dict] | None
    guard_decisions: list[dict] | None
    rework_by_task: dict[str, int]
    rework_total: int
    completed_tasks: int


_DECIDED_STATUSES = ("approved", "rejected")


# ── Pure metric functions ────────────────────────────────────────────────


def gate_rejection_rate(gates: Sequence[GateMetric], phase: str | None = None) -> float | None:
    """rejected / (approved + rejected), optionally restricted to one phase.
    None when there are no decided gates (denominator zero)."""
    decided = [g for g in gates if g.status in _DECIDED_STATUSES]
    if phase is not None:
        decided = [g for g in decided if g.phase == phase]
    if not decided:
        return None
    rejected = sum(1 for g in decided if g.status == "rejected")
    return rejected / len(decided)


def gate_decision_coverage(gates: Sequence[GateMetric]) -> float | None:
    """decided gates with an evidence dossier / decided gates (B2 §2.2)."""
    decided = [g for g in gates if g.status in _DECIDED_STATUSES]
    if not decided:
        return None
    with_evidence = sum(1 for g in decided if g.evidence)
    return with_evidence / len(decided)


def approval_latencies(gates: Sequence[GateMetric],
                       phase: str | None = None) -> list[float]:
    """recorded_at - requested_at in seconds for gates carrying both
    timestamps (requested_at <= recorded_at; negative entries indicate clock
    skew and are excluded from the metric)."""
    out: list[float] = []
    for g in gates:
        if phase is not None and g.phase != phase:
            continue
        if g.requested_at is not None and g.recorded_at is not None:
            delta = g.recorded_at - g.requested_at
            if delta >= timedelta(0):
                out.append(delta.total_seconds())
    return out


def approval_latency_stats(gates: Sequence[GateMetric],
                           phase: str | None = None) -> dict[str, float] | None:
    """p50/p95/mean approval latency in seconds/hours.  None when no gate
    carries both timestamps (NOT_AVAILABLE, not a fabricated zero)."""
    return _seconds_stats(approval_latencies(gates, phase=phase))


def task_cycle_seconds(tasks: Sequence[TaskRecord]) -> list[float]:
    """created_at -> updated_at (last touch; tasks are single-phase records,
    no completed_at field in the current task_graph schema).  Only tasks with
    both timestamps contribute."""
    out: list[float] = []
    for t in tasks:
        if t.created_at is not None and t.updated_at is not None:
            delta = t.updated_at - t.created_at
            if delta >= timedelta(0):
                out.append(delta.total_seconds())
    return out


def task_cycle_time_stats(tasks: Sequence[TaskRecord]) -> dict[str, float] | None:
    """p50/p95/mean task cycle time in days.  None when no task carries both
    timestamps."""
    stats = _seconds_stats(task_cycle_seconds(tasks))
    if stats is None:
        return None
    return {
        "count": stats["count"],
        "p50_days": round(stats["p50_seconds"] / 86400.0, 3),
        "p95_days": round(stats["p95_seconds"] / 86400.0, 3),
        "mean_days": round(stats["mean_seconds"] / 86400.0, 3),
        "basis": "created_at -> updated_at",
    }


def phase_dwell_stats(transitions: Sequence[PhaseTransition]) -> dict[str, dict] | None:
    """Per-phase dwell times from the transition journal (B2 §2.2): for each
    task, dwell in ``from_phase`` = time until the task's next transition.
    Returns phase -> seconds-stats, or None when the journal is empty."""
    if not transitions:
        return None
    per_task: dict[str, list[PhaseTransition]] = {}
    for tr in transitions:
        per_task.setdefault(tr.task_id, []).append(tr)
    dwells: dict[str, list[float]] = {}
    for task_transitions in per_task.values():
        ordered = sorted(task_transitions, key=lambda t: t.at)
        for i in range(len(ordered) - 1):
            delta = (ordered[i + 1].at - ordered[i].at).total_seconds()
            if delta >= 0:
                dwells.setdefault(ordered[i].from_phase, []).append(delta)
    if not dwells:
        return None
    return {
        phase: stats
        for phase, values in sorted(dwells.items())
        if (stats := _seconds_stats(values)) is not None
    }


def rework_cycles_from_gates(gates: Sequence[GateMetric]) -> dict[str, int]:
    """Per-task rework cycles derived from the gate register: each rejected
    gate = one rejection -> fix -> re-audit cycle (B2 §1.2 rework_cycle_rate
    data source when the transition journal is absent)."""
    counter: Counter[str] = Counter()
    for g in gates:
        if g.status == "rejected":
            counter[g.task_id] += 1
    return dict(counter)


def rework_cycles_from_transitions(transitions: Sequence[PhaseTransition],
                                   a: str = "S4-implementation",
                                   b: str = "S5-quality") -> dict[str, int]:
    """Per-task bounce count between phases ``a`` and ``b``: each b -> a
    transition is one rework cycle (a task that bounced S4->S5->S4 has 1;
    B2 AC-MET)."""
    counter: Counter[str] = Counter()
    for tr in transitions:
        if tr.from_phase == b and tr.to_phase == a:
            counter[tr.task_id] += 1
    return dict(counter)


def guard_anomaly_rates(events: Sequence[GuardCheckEvent]) -> dict[str, Any]:
    """Per-guard and overall anomaly rate (FAIL / total) from the U8 guard
    event file, plus result and check-type distributions."""
    by_guard: dict[str, dict[str, Any]] = {}
    results: Counter[str] = Counter()
    check_types: Counter[str] = Counter()
    for e in events:
        results[e.result] += 1
        check_types[e.check_type] += 1
        g = by_guard.setdefault(e.guard_id, {"total": 0, "fail": 0})
        g["total"] += 1
        if e.result == "FAIL":
            g["fail"] += 1
    per_guard: dict[str, Any] = {}
    for gid, g in sorted(by_guard.items()):
        per_guard[gid] = {
            "total": g["total"],
            "fail": g["fail"],
            "anomaly_rate": round(g["fail"] / g["total"], 4),
        }
    total = len(events)
    failures = sum(1 for e in events if e.result == "FAIL")
    return {
        "total_events": total,
        "anomaly_rate": round(failures / total, 4) if total else None,
        "by_guard": per_guard,
        "by_result": dict(results),
        "by_check_type": dict(check_types),
    }


def execution_cycle_stats(executions: Sequence[dict]) -> dict[str, float] | None:
    """launched_at -> completed_at for completed executions (execution
    ledger).  None when no completed execution carries both timestamps."""
    seconds: list[float] = []
    for rec in executions:
        if str(rec.get("status", "")).upper() != "COMPLETED":
            continue
        launched = _parse_dt(rec.get("launched_at"))
        completed = _parse_dt(rec.get("completed_at"))
        if launched is not None and completed is not None:
            delta = (completed - launched).total_seconds()
            if delta >= 0:
                seconds.append(delta)
    return _seconds_stats(seconds)


def drift_event_counts(events: Sequence[dict]) -> dict[str, Any]:
    """Counts of drift events from the runtime events ledger (B2 §2.2)."""
    types: Counter[str] = Counter()
    for e in events:
        types[str(e.get("event_type", e.get("type", "unknown")))] += 1
    return {
        "total": len(events),
        "by_type": dict(types),
    }


# ── Target comparison ────────────────────────────────────────────────────


def _over_target(target: dict[str, Any], value: float) -> bool | None:
    """Compare an observed value against a target {op, value}.  None when
    value is not available (never a silent pass/fail)."""
    op = target.get("op")
    tvalue = float(target["value"])
    if op == "<=":
        return value > tvalue
    if op == ">=":
        return value < tvalue
    if op == "==":
        return abs(value - tvalue) > 1e-9
    return None
