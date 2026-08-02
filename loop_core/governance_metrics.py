"""
Governance metrics — SLI / SLO / error budget accounting + Loop-DORA telemetry
(T-0090 D2, B2 design docs/designs/loop-v4-slo-metrics-learning.md §1/§2).

Scope (wave 1 advisory):
- SLI collection from existing data sources (.ai/gates.yaml,
  .ai/task_graph.yaml, .ai/evidence/observability/guard-events.jsonl,
  .ai/ledger/executions.jsonl, optional transition journal / guard decision
  log / runtime events ledger).
- SLO/error-budget accounting per B2 §1.4 (v1 rule: one breach event = 1 unit
  per budget-consuming SLO; ``budget_share`` scales a unit's weight; budget
  exhaustion is *reported* as FREEZE_RECOMMENDED only — release blocking is
  wave 2, out of scope here).
- DORA-style metrics report (gate rejection rate, decision coverage,
  approval latency, task cycle time, rework, guard anomaly rate, ...) as a
  structured JSON report + human-readable markdown, ReportBinding-style.

Rules:
- Read-only aggregation: this module never writes to its data sources.  The
  report artifact is written by the CLI (tools/loop_metrics.py) to the
  evidence directory.
- A missing or unparseable *wired* data source is surfaced as NOT_AVAILABLE,
  never guessed or silently zeroed, and makes the report NOT_VERIFIED
  (fail-closed, B2 §2.5).  Documented wave-2 wiring items
  (phase_transitions.jsonl / guard_decisions.jsonl / runtime-events.jsonl,
  T-0100 F-05) are surfaced as **per-source advisories** instead: computed
  items are judged on their real values, and the report is not demoted to
  NOT_VERIFIED merely because an unwired source is absent.
- Every metric is a pure function of ledger inputs so results are
  reproducible from a commit (B2 §2.3).
- Release-fee accounting lives in exactly one function
  (``release_fee_consumption``, used by ``compute_error_budget``) — the SLO
  gate references the same computation, so metrics and slo_gate budgets are
  consistent for identical inputs (T-0100 F-05).
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import subprocess
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from loop_core.observability import GuardCheckEvent

# ── Availability sentinel ────────────────────────────────────────────────
# A metric value that cannot be computed from the available data sources.
# Never conflated with a real zero (B2 §2.5 — missing data is NOT_VERIFIED,
# never a silent zero).
NOT_AVAILABLE = "NOT_AVAILABLE"

# ── Report / budget statuses ─────────────────────────────────────────────
BUDGET_HEALTHY = "HEALTHY"                      # nothing consumed
BUDGET_CONSUMING = "CONSUMING"                  # consumption > 0, budget remains
BUDGET_FREEZE_RECOMMENDED = "FREEZE_RECOMMENDED"  # remaining units <= 0 (advisory only)
REPORT_PASS = "PASS"
REPORT_NOT_VERIFIED = "NOT_VERIFIED"

# ── SLO severity classes (B2 §1.3) ───────────────────────────────────────
SEVERITY_BUDGET = "error-budget-slo"   # breaches consume error budget
SEVERITY_HARD_GATE = "hard-gate"       # not budget-consuming
SEVERITY_INFO = "informational"        # not budget-consuming

_DECIDED_STATUSES = ("approved", "rejected")
_TASK_COMPLETED_STATUS = "completed"

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


# ── Data source errors ───────────────────────────────────────────────────


class DataSourceUnavailableError(Exception):
    """A data source file is missing or cannot be parsed.  Callers treat
    this as NOT_AVAILABLE for the affected metrics (never a silent zero)."""


def _load_jsonl(path: Path, what: str) -> list[dict]:
    if not path.exists():
        raise DataSourceUnavailableError(f"{what} missing: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DataSourceUnavailableError(f"{what} unreadable: {path}: {exc}") from exc
    records: list[dict] = []
    for i, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DataSourceUnavailableError(
                f"{what} unparseable line {i}: {path}"
            ) from exc
        if not isinstance(data, dict):
            raise DataSourceUnavailableError(f"{what} non-object line {i}: {path}")
        records.append(data)
    return records


# ── Loaders (read-only) ──────────────────────────────────────────────────


def load_gates(root: str | Path, since: datetime | None = None) -> list[GateMetric]:
    """Load .ai/gates.yaml.  ``since`` filters by recorded_at when known;
    gates without a recorded_at are kept (their timing is unknown, they are
    never silently dropped)."""
    path = Path(root) / ".ai" / "gates.yaml"
    if not path.exists():
        raise DataSourceUnavailableError(f"gates register missing: {path}")
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DataSourceUnavailableError(f"gates register unparseable: {path}: {exc}") from exc
    raw_gates = doc.get("gates") if isinstance(doc, dict) else None
    if not isinstance(raw_gates, list):
        raise DataSourceUnavailableError(f"gates register has no 'gates' list: {path}")
    gates: list[GateMetric] = []
    for raw in raw_gates:
        if not isinstance(raw, dict):
            raise DataSourceUnavailableError(f"gates register entry not a mapping: {path}")
        recorded_at = _parse_dt(raw.get("recorded_at"))
        if since is not None and recorded_at is not None and recorded_at < since:
            continue
        gates.append(GateMetric(
            gate_id=str(raw.get("id", "")),
            task_id=str(raw.get("task_id", "")),
            gate_type=str(raw.get("gate_type", "")),
            status=str(raw.get("status", "")).lower(),
            decision=raw.get("decision"),
            phase=classify_gate_phase(str(raw.get("id", ""))),
            requested_at=_parse_dt(raw.get("requested_at")),
            recorded_at=recorded_at,
            evidence=str(raw.get("evidence", "")) or None,
        ))
    return gates


def load_tasks(root: str | Path) -> list[TaskRecord]:
    """Load .ai/task_graph.yaml task records."""
    path = Path(root) / ".ai" / "task_graph.yaml"
    if not path.exists():
        raise DataSourceUnavailableError(f"task graph missing: {path}")
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DataSourceUnavailableError(f"task graph unparseable: {path}: {exc}") from exc
    raw_tasks = doc.get("tasks") if isinstance(doc, dict) else None
    if not isinstance(raw_tasks, list):
        raise DataSourceUnavailableError(f"task graph has no 'tasks' list: {path}")
    tasks: list[TaskRecord] = []
    for raw in raw_tasks:
        if not isinstance(raw, dict):
            raise DataSourceUnavailableError(f"task graph entry not a mapping: {path}")
        tasks.append(TaskRecord(
            task_id=str(raw.get("id", "")),
            status=str(raw.get("status", "")).lower(),
            phase=raw.get("phase"),
            created_at=_parse_dt(raw.get("created_at")),
            updated_at=_parse_dt(raw.get("updated_at")),
        ))
    return tasks


def load_guard_events(root: str | Path) -> list[GuardCheckEvent]:
    """Load .ai/evidence/observability/guard-events.jsonl (U8 event file —
    read-only).  Strict parse: a corrupt line makes the whole source
    NOT_AVAILABLE rather than silently producing fabricated events."""
    path = Path(root) / ".ai" / "evidence" / "observability" / "guard-events.jsonl"
    if not path.exists():
        raise DataSourceUnavailableError(f"guard events missing: {path}")
    records = _load_jsonl(path, "guard events")
    events: list[GuardCheckEvent] = []
    for i, data in enumerate(records, start=1):
        for key in ("guard_id", "check_type", "result"):
            if key not in data:
                raise DataSourceUnavailableError(
                    f"guard events line {i} lacks '{key}': {path}"
                )
        if data.get("result") not in ("PASS", "FAIL", "REPORT"):
            raise DataSourceUnavailableError(
                f"guard events line {i} has unknown result: {path}"
            )
        events.append(GuardCheckEvent.from_dict(data))
    return events


def load_phase_transitions(root: str | Path) -> list[PhaseTransition]:
    """Load .ai/ledger/phase_transitions.jsonl (B2 §2.2 transition journal —
    not yet wired in wave 1, so this raises DataSourceUnavailableError when
    absent)."""
    path = Path(root) / ".ai" / "ledger" / "phase_transitions.jsonl"
    if not path.exists():
        raise DataSourceUnavailableError(
            f"phase transition journal missing: {path} (B2 §2.2 — "
            "phase_transitions.jsonl writer is a wave-2 wiring item)"
        )
    records = _load_jsonl(path, "phase transitions")
    transitions: list[PhaseTransition] = []
    for i, data in enumerate(records, start=1):
        for key in ("task_id", "from_phase", "to_phase", "at"):
            if key not in data:
                raise DataSourceUnavailableError(
                    f"phase transitions line {i} lacks '{key}': {path}"
                )
        at = _parse_dt(data.get("at"))
        if at is None:
            raise DataSourceUnavailableError(
                f"phase transitions line {i} has unparseable 'at': {path}"
            )
        transitions.append(PhaseTransition(
            task_id=str(data["task_id"]),
            from_phase=str(data["from_phase"]),
            to_phase=str(data["to_phase"]),
            at=at,
        ))
    return transitions


def load_executions(root: str | Path) -> list[dict]:
    """Load .ai/ledger/executions.jsonl (append-only execution ledger)."""
    path = Path(root) / ".ai" / "ledger" / "executions.jsonl"
    return _load_jsonl(path, "execution ledger")


def load_runtime_events(root: str | Path) -> list[dict]:
    """Load .ai/ledger/runtime-events.jsonl (B2 §2.2 drift source — absent in
    wave 1, raises DataSourceUnavailableError)."""
    path = Path(root) / ".ai" / "ledger" / "runtime-events.jsonl"
    if not path.exists():
        raise DataSourceUnavailableError(
            f"runtime events ledger missing: {path} (drift source not yet wired)"
        )
    return _load_jsonl(path, "runtime events ledger")


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


# ── SLO configuration ────────────────────────────────────────────────────
# Default targets from B2 §1.2 (proposal).  An .ai/slo.yaml (B2 §1.3) may
# override any of them; when absent the defaults apply and the report says so.

DEFAULT_SLOS: tuple[dict[str, Any], ...] = (
    {"sli_id": "req_gate_rejection_rate", "phase": "S1-requirements",
     "description": "S1 gate rejections / (approvals + rejections)",
     "target": {"op": "<=", "value": 0.35}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0, "source": ".ai/gates.yaml (S1 gates, phase-classified)"},
    {"sli_id": "design_review_rejection_rate", "phase": "S2-architecture",
     "description": "design review rejections / decisions",
     "target": {"op": "<=", "value": 0.30}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0, "source": ".ai/gates.yaml (S2 gates, phase-classified)"},
    {"sli_id": "quality_gate_rejection_rate", "phase": "S5-quality",
     "description": "S5 rejections / decisions",
     "target": {"op": "<=", "value": 0.30}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0, "source": ".ai/gates.yaml (S5 gates, phase-classified)"},
    {"sli_id": "delivery_gate_rejection_rate", "phase": "S6-delivery",
     "description": "S6 rejections (incl. NOGO) / decisions",
     "target": {"op": "<=", "value": 0.20}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0, "source": ".ai/gates.yaml (S6 gates, phase-classified)"},
    {"sli_id": "rework_cycle_rate", "phase": "S4-implementation",
     "description": "rework cycles (rejected gates or S4<->S5 bounces) / completed tasks",
     "target": {"op": "<=", "value": 0.25}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0,
     "source": ".ai/gates.yaml rejected gates (or .ai/ledger/phase_transitions.jsonl)"},
    {"sli_id": "guard_block_rate", "phase": "S4-implementation",
     "description": "guard blocks / (blocks + passes) across hooks (false-positive proxy)",
     "target": {"op": "<=", "value": 0.05}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0,
     "source": ".ai/ledger/guard_decisions.jsonl (hook decision log — not yet wired)"},
    {"sli_id": "guard_anomaly_rate", "phase": "S4-implementation",
     "description": "guard check anomalies (FAIL events) / total guard-check events — "
                    "wave-1 computable proxy for guard_block_rate (U8 guard-events.jsonl)",
     "target": {"op": "<=", "value": 0.05}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0,
     "source": ".ai/evidence/observability/guard-events.jsonl"},
    {"sli_id": "approval_latency_p95", "phase": "S6-delivery",
     "description": "p95 of gate requested_at -> recorded_at (hours)",
     "target": {"op": "<=", "value": 24.0, "unit": "h"}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0, "source": ".ai/gates.yaml requested_at/recorded_at"},
    {"sli_id": "gate_decision_coverage", "phase": "All",
     "description": "gates decided with evidence dossier / decided",
     "target": {"op": ">=", "value": 1.0}, "severity": SEVERITY_HARD_GATE,
     "budget_share": 0.0, "source": ".ai/gates.yaml evidence fields"},
    {"sli_id": "drift_event_rate", "phase": "S11-maintenance",
     "description": "governance drift events per window",
     "target": {"op": "<=", "value": 2}, "severity": SEVERITY_INFO,
     "budget_share": 0.0,
     "source": ".ai/ledger/runtime-events.jsonl (drift source — not yet wired)"},
    {"sli_id": "delta_quality_pass_rate", "phase": "S4-implementation",
     "description": "tasks passing delta gates (no new regressions on the diff)",
     "target": {"op": ">=", "value": 1.0}, "severity": SEVERITY_HARD_GATE,
     "budget_share": 0.0, "source": "delta gate results (not yet recorded)"},
    {"sli_id": "evidence_regeneration_rate", "phase": "S5-quality",
     "description": "evidence regeneration events / tasks",
     "target": {"op": "<=", "value": 0.10}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0, "source": "evidence re-run tracking (not yet recorded)"},
    {"sli_id": "defect_fail_verdict_rate", "phase": "S5-quality",
     "description": "tasks with FAIL verdicts (warning class)",
     "target": {"op": "<=", "value": 0.20}, "severity": SEVERITY_BUDGET,
     "budget_share": 1.0, "source": "FAIL verdict store (not yet recorded)"},
    {"sli_id": "ac_invest_rate", "phase": "S1-requirements",
     "description": "acceptance criteria meeting INVEST/verifiable shape",
     "target": {"op": ">=", "value": 1.0}, "severity": SEVERITY_HARD_GATE,
     "budget_share": 0.0, "source": "DoD gate acceptance-criteria check (T-0089 scope)"},
)

DEFAULT_BUDGET_TOTAL_UNITS = 100.0
DEFAULT_RELEASE_FEE_UNITS = 5.0

# ── Data-source wiring status (T-0100 F-05) ──────────────────────────────
# REPORT_SOURCE_FILES 中的三项是文档化 wave-2 接线项（B2 §2.2）：
# 缺失/未接线 → 逐项 advisory 标注（不因它们整体 NOT_VERIFIED）；
# 其余源（gates/task_graph/guard-events/executions）为已接线源 ——
# 缺失即 NOT_AVAILABLE 且报告 NOT_VERIFIED（fail-closed，语义不变）。
WAVE2_UNWIRED_SOURCES: frozenset[str] = frozenset({
    "phase_transitions.jsonl",
    "guard_decisions.jsonl",
    "runtime-events.jsonl",
})

# 依赖未接线源或尚未落盘的 SLI：其 NOT_AVAILABLE 属于 advisory 类别
# （evaluate_sli 逐分支标注 advisory=True），不驱动整体 NOT_VERIFIED。
UNWIRED_SLI_IDS: frozenset[str] = frozenset({
    "guard_block_rate",       # guard_decisions.jsonl（wave-2）
    "drift_event_rate",       # runtime-events.jsonl（wave-2）
    "delta_quality_pass_rate",      # 尚未记录
    "evidence_regeneration_rate",   # 尚未记录
    "defect_fail_verdict_rate",     # 尚未记录
    "ac_invest_rate",               # 尚未记录
})


def release_fee_consumption(release_fee_units: float, releases: int) -> float:
    """Release-fee consumption: ``releases * release_fee_units``.

    单一共享实现（T-0100 F-05）：metrics 记账（compute_error_budget）与 SLO
    门禁（loop_core.slo_gate 经 compute_error_budget 引用）使用同一函数，
    保证口径一致 —— 相同输入必然得到相同 release_consumption。
    """
    if not releases:
        return 0.0
    return round(releases * release_fee_units, 3)


def load_slo_config(root: str | Path, slo_path: str | Path | None = None) -> dict[str, Any]:
    """Merge .ai/slo.yaml (B2 §1.3) over the B2 §1.2 defaults.

    - Absent slo.yaml -> defaults apply; ``source`` says so.
    - Present but unparseable -> DataSourceUnavailableError (an explicit config
      that cannot be read must not silently fall back to defaults).
    - Per-SLI overrides are matched by sli_id; unknown sli_ids are appended.
    - T-0095 fail-closed validation: an explicit slo.yaml that is semantically
      invalid (non-numeric budget units, malformed target/severity/budget_share,
      half-set or unparseable window bounds) raises DataSourceUnavailableError
      with the field named — the config is never partially applied and never
      silently downgraded to defaults.
    """
    path = Path(slo_path) if slo_path is not None else Path(root) / ".ai" / "slo.yaml"

    def _invalid(message: str) -> DataSourceUnavailableError:
        return DataSourceUnavailableError(f"slo config invalid ({message}): {path}")

    slos: list[dict[str, Any]] = [dict(d) for d in DEFAULT_SLOS]
    by_id = {s["sli_id"]: s for s in slos}
    if not path.exists():
        return {
            "source": "defaults (B2 §1.2 table); .ai/slo.yaml absent",
            "slo_path": str(path),
            "slos": slos,
            "budget_total_units": DEFAULT_BUDGET_TOTAL_UNITS,
            "release_fee_units": DEFAULT_RELEASE_FEE_UNITS,
            "window": None,
        }
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DataSourceUnavailableError(f"slo config unparseable: {path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise DataSourceUnavailableError(f"slo config not a mapping: {path}")

    # ── T-0095: budget units validation (fail-closed) ────────────────────
    for key, minimum, exclusive in (
        ("budget_total_units", 0.0, True),
        ("release_fee_units", 0.0, False),
    ):
        if key in doc:
            raw = doc[key]
            try:
                value = float(raw)
            except (TypeError, ValueError):
                raise _invalid(f"'{key}' must be numeric, got {raw!r}") from None
            if not math.isfinite(value) or value < minimum or (exclusive and value == minimum):
                comparator = f"> {minimum:g}" if exclusive else f">= {minimum:g}"
                raise _invalid(f"'{key}' must be a finite number {comparator}, got {raw!r}")

    # ── T-0095: window bounds validation (fail-closed) ───────────────────
    # A window is honored only when both bounds are set; a half-set or
    # unparseable window would previously be *silently ignored* (treated as
    # "no window") — that ambiguity now fails closed with the field named.
    window_start = doc.get("window_start")
    window_end = doc.get("window_end")
    if (window_start or window_end) and not (window_start and window_end):
        raise _invalid(
            "'window_start' and 'window_end' must be set together "
            f"(got start={window_start!r}, end={window_end!r})"
        )
    for key in ("window_start", "window_end"):
        value = doc.get(key)
        if value and _parse_dt(value) is None:
            raise _invalid(f"'{key}' is not an ISO-8601 timestamp: {value!r}")

    raw_slos = doc.get("slos", [])
    if not isinstance(raw_slos, list):
        raise DataSourceUnavailableError(f"slo config 'slos' not a list: {path}")
    for raw in raw_slos:
        if not isinstance(raw, dict) or "sli_id" not in raw:
            raise DataSourceUnavailableError(f"slo config entry lacks sli_id: {path}")
        sli_id = str(raw["sli_id"])

        # ── T-0095: per-SLI semantic validation (fail-closed) ────────────
        target = raw.get("target")
        if target is not None:
            if not isinstance(target, dict) or "op" not in target or "value" not in target:
                raise _invalid(
                    f"entry '{sli_id}' target must be a mapping with 'op' and 'value'"
                )
            if str(target.get("op")) not in ("<=", ">=", "=="):
                raise _invalid(
                    f"entry '{sli_id}' target op must be <= | >= | ==, "
                    f"got {target.get('op')!r}"
                )
            try:
                target_value = float(target["value"])
            except (TypeError, ValueError):
                raise _invalid(
                    f"entry '{sli_id}' target value must be numeric, "
                    f"got {target.get('value')!r}"
                ) from None
            if not math.isfinite(target_value):
                raise _invalid(
                    f"entry '{sli_id}' target value must be finite, "
                    f"got {target.get('value')!r}"
                )
        severity = raw.get("severity")
        if severity is not None and severity not in (
            SEVERITY_BUDGET, SEVERITY_HARD_GATE, SEVERITY_INFO,
        ):
            raise _invalid(f"entry '{sli_id}' has unknown severity: {severity!r}")
        share = raw.get("budget_share")
        if share is not None:
            try:
                share_value = float(share)
            except (TypeError, ValueError):
                raise _invalid(
                    f"entry '{sli_id}' budget_share must be numeric, got {share!r}"
                ) from None
            if not math.isfinite(share_value) or share_value < 0:
                raise _invalid(
                    f"entry '{sli_id}' budget_share must be finite and >= 0, "
                    f"got {share!r}"
                )

        entry = by_id.get(sli_id)
        if entry is None:
            entry = {
                "sli_id": sli_id, "phase": raw.get("phase"),
                "description": raw.get("description", ""),
                "target": {"op": "<=", "value": 0.0},
                "severity": SEVERITY_BUDGET, "budget_share": 1.0,
                "source": str(path),
            }
            by_id[sli_id] = entry
            slos.append(entry)
        for key in ("target", "severity", "budget_share", "phase", "description"):
            if key in raw:
                entry[key] = raw[key]
    return {
        "source": str(path),
        "slo_path": str(path),
        "slos": slos,
        "budget_total_units": float(doc.get("budget_total_units", DEFAULT_BUDGET_TOTAL_UNITS)),
        "release_fee_units": float(doc.get("release_fee_units", DEFAULT_RELEASE_FEE_UNITS)),
        "window": (doc.get("window_start"), doc.get("window_end")),
    }


# ── SLI evaluation ───────────────────────────────────────────────────────


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


def evaluate_sli(sli: dict[str, Any], ctx: SliContext) -> dict[str, Any]:
    """Evaluate one SLO spec against the data context.

    Returns a record with status computed|NOT_AVAILABLE, value, over_target,
    breach_events and consumed_units (breach_events * budget_share for
    error-budget SLOs; B2 §1.4 v1 rule — one breach event = 1 unit)."""
    sli_id = sli["sli_id"]
    severity = sli.get("severity", SEVERITY_BUDGET)
    budget_share = float(sli.get("budget_share", 1.0))
    target = dict(sli.get("target", {"op": "<=", "value": 0.0}))
    value: float | None = None
    breach_events: int | None = None
    reason: str | None = None
    # T-0100 F-05: advisory=True 表示 NOT_AVAILABLE 源于文档化未接线数据源
    # （wave-2）或尚未落盘的 SLI —— 逐项标注，不驱动整体 NOT_VERIFIED。
    # guard_block_rate / drift_event_rate 的 advisory 仅在"源缺失（未接线）"
    # 分支成立；若源已存在但无数据，则属真实数据情形（非 advisory）。
    advisory = sli_id in UNWIRED_SLI_IDS - {"guard_block_rate", "drift_event_rate"}

    if sli_id in ("req_gate_rejection_rate", "design_review_rejection_rate",
                  "quality_gate_rejection_rate", "delivery_gate_rejection_rate"):
        phase = sli.get("phase")
        if ctx.gates is None:
            reason = "gates register unavailable"
        else:
            decided = [g for g in ctx.gates
                       if g.status in _DECIDED_STATUSES and g.phase == phase]
            if not decided:
                reason = f"no decided gates for phase {phase}"
            else:
                rejected = sum(1 for g in decided if g.status == "rejected")
                value = rejected / len(decided)
                breach_events = rejected
    elif sli_id == "rework_cycle_rate":
        if ctx.gates is None:
            reason = "gates register unavailable"
        elif ctx.completed_tasks == 0:
            reason = "no completed tasks in task graph"
        else:
            value = ctx.rework_total / ctx.completed_tasks
            breach_events = ctx.rework_total
    elif sli_id == "guard_block_rate":
        if ctx.guard_decisions is None:
            reason = ("guard_decisions.jsonl absent (hook decision log not yet "
                      "wired — B2 §2.2 wave 1)")
            advisory = True  # 未接线源缺失 → advisory
        else:
            decided = [d for d in ctx.guard_decisions
                       if d.get("decision") in ("block", "pass")]
            if not decided:
                reason = "no block/pass decisions in guard_decisions.jsonl"
            else:
                blocks = sum(1 for d in decided if d.get("decision") == "block")
                value = blocks / len(decided)
                breach_events = blocks
    elif sli_id == "guard_anomaly_rate":
        if ctx.guard_events is None:
            reason = "guard-events.jsonl unavailable"
        elif not ctx.guard_events:
            reason = "guard-events.jsonl contains no events"
        else:
            rates = guard_anomaly_rates(ctx.guard_events)
            if rates["anomaly_rate"] is None:
                reason = "no guard events recorded"
            else:
                value = rates["anomaly_rate"]
                breach_events = int(rates["by_result"].get("FAIL", 0))
    elif sli_id == "approval_latency_p95":
        if ctx.gates is None:
            reason = "gates register unavailable"
        else:
            stats = approval_latency_stats(ctx.gates)
            if stats is None:
                reason = "no gate with both requested_at and recorded_at"
            else:
                value = stats["p95_hours"]
                breach_events = sum(
                    1 for s in approval_latencies(ctx.gates) if s > 24.0 * 3600.0
                )
    elif sli_id == "gate_decision_coverage":
        if ctx.gates is None:
            reason = "gates register unavailable"
        else:
            decided = [g for g in ctx.gates if g.status in _DECIDED_STATUSES]
            if not decided:
                reason = "no decided gates"
            else:
                with_evidence = sum(1 for g in decided if g.evidence)
                value = with_evidence / len(decided)
                breach_events = len(decided) - with_evidence
    elif sli_id == "drift_event_rate":
        if ctx.drift_events is None:
            reason = "runtime-events.jsonl absent (drift source not yet wired)"
            advisory = True  # 未接线源缺失 → advisory
        else:
            value = float(len(ctx.drift_events))
            breach_events = len(ctx.drift_events)
    elif sli_id == "delta_quality_pass_rate":
        reason = "delta gate results not yet recorded"
    elif sli_id == "evidence_regeneration_rate":
        reason = "evidence re-run tracking not yet recorded"
    elif sli_id == "defect_fail_verdict_rate":
        reason = "FAIL verdict store not yet recorded"
    elif sli_id == "ac_invest_rate":
        reason = "DoD gate acceptance-criteria check not yet recorded"
    else:
        reason = f"unknown SLI id: {sli_id}"

    if value is None:
        status = NOT_AVAILABLE
        over_target: bool | None = None
    else:
        status = "computed"
        over_target = _over_target(target, value)

    consumed = 0.0
    if severity == SEVERITY_BUDGET and breach_events is not None:
        consumed = round(breach_events * budget_share, 3)

    return {
        "sli_id": sli_id,
        "phase": sli.get("phase"),
        "description": sli.get("description", ""),
        "severity": severity,
        "budget_share": budget_share,
        "target": target,
        "status": status,
        "value": value if status == "computed" else NOT_AVAILABLE,
        "reason": reason,
        "over_target": over_target,
        "breach_events": breach_events,
        "consumed_units": consumed,
        "source": sli.get("source", ""),
        "advisory": advisory,
    }


def compute_error_budget(sli_results: Sequence[dict[str, Any]],
                         total_units: float = DEFAULT_BUDGET_TOTAL_UNITS,
                         release_fee_units: float = DEFAULT_RELEASE_FEE_UNITS,
                         releases: int = 0) -> dict[str, Any]:
    """Error budget accounting (B2 §1.4).

    consumed = sum(breach_events * budget_share) over budget-consuming SLOs,
    plus ``releases * release_fee_units`` when a release count is supplied
    (release fee via the shared ``release_fee_consumption`` — identical for
    metrics accounting and the SLO gate, T-0100 F-05).
    Status: HEALTHY (nothing consumed) / CONSUMING (within budget) /
    FREEZE_RECOMMENDED (remaining <= 0 — advisory only in wave 1; release
    blocking is a wave-2 wiring item and is NOT applied here)."""
    consumed = round(sum(float(r.get("consumed_units", 0.0)) for r in sli_results), 3)
    release_units = release_fee_consumption(release_fee_units, releases)
    total_consumed = round(consumed + release_units, 3)
    remaining = round(total_units - total_consumed, 3)
    if remaining <= 0:
        status = BUDGET_FREEZE_RECOMMENDED
    elif total_consumed > 0:
        status = BUDGET_CONSUMING
    else:
        status = BUDGET_HEALTHY
    return {
        "total_units": total_units,
        "consumed_units": total_consumed,
        "breach_consumption": consumed,
        "release_fee_units": release_fee_units,
        "release_count": releases,
        "release_consumption": release_units,
        "remaining_units": remaining,
        "status": status,
        "note": ("advisory only (wave 1): budget exhaustion is reported, "
                 "no release path is blocked by this module"),
    }


# ── DORA metrics ─────────────────────────────────────────────────────────


def _metric(value: Any, status: str = "computed", **extra: Any) -> dict[str, Any]:
    return {"status": status, "value": value, **extra}


def _not_available(reason: str, advisory: bool = False) -> dict[str, Any]:
    """NOT_AVAILABLE 指标。advisory=True：源于文档化未接线源（wave-2）——
    逐项标注，不驱动整体 NOT_VERIFIED（T-0100 F-05）。"""
    return {
        "status": NOT_AVAILABLE, "value": NOT_AVAILABLE,
        "reason": reason, "advisory": advisory,
    }


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


# ── Report ───────────────────────────────────────────────────────────────

REPORT_SOURCE_FILES: tuple[tuple[str, str], ...] = (
    (".ai/gates.yaml", "gates"),
    (".ai/task_graph.yaml", "tasks"),
    (".ai/evidence/observability/guard-events.jsonl", "guard_events"),
    (".ai/ledger/executions.jsonl", "executions"),
    (".ai/ledger/phase_transitions.jsonl", "transitions"),
    (".ai/ledger/guard_decisions.jsonl", "guard_decisions"),
    (".ai/ledger/runtime-events.jsonl", "runtime_events"),
)


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


@dataclass
class MetricsReport:
    """Structured metrics report (B2 §2.3/§2.4), ReportBinding-style:
    binds git_commit + window + generated_at + tool identity.  ``status`` is
    PASS only when every *wired* metric is computed; a missing/unparseable
    wired source, or a wired-source NOT_AVAILABLE, makes it NOT_VERIFIED
    (fail-closed, B2 §2.5).  Documented unwired sources (wave-2 ledger items)
    are collected in ``advisories`` (per-source annotated, T-0100 F-05) and
    never demote the overall status by themselves."""
    window: tuple[str, str]
    generated_at: str
    git_commit: str
    task_id: str
    phase: str
    gate_id: str | None
    tool_name: str
    tool_version: str
    dora: dict[str, Any]
    sli_eval: list[dict[str, Any]]
    budget: dict[str, Any]
    slo_source: str
    sources: list[dict[str, Any]]
    status: str
    missing: list[str]
    notes: list[str] = field(default_factory=list)
    advisories: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "report_type": "loop-dora-metrics",
            "binding": {
                "task_id": self.task_id,
                "phase": self.phase,
                "gate_id": self.gate_id,
                "git_commit": self.git_commit,
                "timestamp": self.generated_at,
                "tool_name": self.tool_name,
                "tool_version": self.tool_version,
            },
            "window": {"start": self.window[0], "end": self.window[1]},
            "status": self.status,
            "missing": self.missing,
            "advisories": self.advisories,
            "dora_metrics": self.dora,
            "slo_evaluation": self.sli_eval,
            "error_budget": self.budget,
            "slo_source": self.slo_source,
            "sources": self.sources,
            "notes": self.notes,
        }


def _data_window(ctx: SliContext) -> tuple[str, str]:
    """Data bounds across the available sources (for the report header when
    no explicit window is given)."""
    stamps: list[datetime] = []
    if ctx.gates:
        stamps.extend(g.recorded_at for g in ctx.gates if g.recorded_at)
    if ctx.guard_events:
        stamps.extend(
            ts for e in ctx.guard_events
            if (ts := _parse_dt(e.timestamp)) is not None
        )
    if ctx.tasks:
        stamps.extend(t.created_at for t in ctx.tasks if t.created_at)
    if not stamps:
        return ("unknown", "unknown")
    return (min(stamps).isoformat(), max(stamps).isoformat())


def build_report(root: str | Path, window: tuple[str, str] | None = None,
                 slo_path: str | Path | None = None,
                 releases: int = 0,
                 task_id: str = "T-0090", phase: str = "S6-delivery",
                 gate_id: str | None = None) -> MetricsReport:
    """Build the full metrics report from the repository data sources.

    Read-only: never writes to any data source.  A missing/unparseable *wired*
    source is recorded in ``sources``/``missing`` and the affected metrics
    are NOT_AVAILABLE; the report status then is NOT_VERIFIED.  Documented
    unwired (wave-2) sources are recorded in ``advisories`` with per-source
    annotation and do not demote the overall status (T-0100 F-05)."""
    root_path = Path(root)
    data: dict[str, Any] = {}
    sources: list[dict[str, Any]] = []
    missing: list[str] = []       # 已接线源缺失/不可解析 → NOT_VERIFIED 驱动
    advisories: list[str] = []    # 未接线源（wave-2）→ 逐项 advisory（T-0100 F-05）
    for rel_path, key in REPORT_SOURCE_FILES:
        path = root_path / rel_path
        exists = path.exists()
        sources.append({
            "path": rel_path,
            "status": "available" if exists else "missing",
            "sha256": _sha256(path) if exists else None,
            "lines": sum(1 for _ in path.open("rb")) if exists else None,
        })
        if not exists:
            data[key] = None
            if Path(rel_path).name in WAVE2_UNWIRED_SOURCES:
                advisories.append(
                    f"数据源未接线（wave-2 项，不影响 computed 判定）: "
                    f"{key} ({rel_path})"
                )
            else:
                missing.append(f"{key} ({rel_path})")
            continue
        loader = {
            "gates": load_gates,
            "tasks": load_tasks,
            "guard_events": load_guard_events,
            "executions": load_executions,
            "transitions": load_phase_transitions,
            "guard_decisions": lambda p: _load_jsonl(
                root_path / ".ai" / "ledger" / "guard_decisions.jsonl",
                "guard decisions ledger"),
            "runtime_events": load_runtime_events,
        }[key]
        try:
            data[key] = loader(root_path)
        except DataSourceUnavailableError as exc:
            data[key] = None
            if Path(rel_path).name in WAVE2_UNWIRED_SOURCES:
                advisories.append(f"数据源未接线（wave-2 项）: {key} ({rel_path}): {exc}")
            else:
                missing.append(f"{key} ({rel_path}): {exc}")

    slo_config = load_slo_config(root_path, slo_path)

    ctx = SliContext(
        gates=data.get("gates"),
        tasks=data.get("tasks"),
        transitions=data.get("transitions"),
        guard_events=data.get("guard_events"),
        executions=data.get("executions"),
        drift_events=data.get("runtime_events"),
        guard_decisions=data.get("guard_decisions"),
        rework_by_task=(
            rework_cycles_from_gates(data["gates"]) if data.get("gates") is not None else {}
        ),
        rework_total=(
            sum(rework_cycles_from_gates(data["gates"]).values())
            if data.get("gates") is not None else 0
        ),
        completed_tasks=(
            len([t for t in data["tasks"] if t.status == _TASK_COMPLETED_STATUS])
            if data.get("tasks") is not None else 0
        ),
    )

    dora = build_dora_metrics(ctx)
    sli_eval = [evaluate_sli(sli, ctx) for sli in slo_config["slos"]]
    budget = compute_error_budget(
        sli_eval,
        total_units=slo_config["budget_total_units"],
        release_fee_units=slo_config["release_fee_units"],
        releases=releases,
    )

    # T-0100 F-05: NOT_VERIFIED 只由"已接线源"问题驱动 —— 未接线源（wave-2）
    # 的 NOT_AVAILABLE 进 advisories（逐项标注），computed 项按实值判定。
    all_not_available = [
        name for name, m in dora.items()
        if m.get("status") == NOT_AVAILABLE and not m.get("advisory")
    ] + [
        f"sli:{r['sli_id']}" for r in sli_eval
        if r.get("status") == NOT_AVAILABLE and not r.get("advisory")
    ]
    advisory_items = [
        name for name, m in dora.items()
        if m.get("status") == NOT_AVAILABLE and m.get("advisory")
    ] + [
        f"sli:{r['sli_id']} — {r.get('reason')}" for r in sli_eval
        if r.get("status") == NOT_AVAILABLE and r.get("advisory")
    ]
    status = REPORT_NOT_VERIFIED if (missing or all_not_available) else REPORT_PASS
    report_missing = missing + all_not_available

    window_tuple = window if window is not None else _data_window(ctx)

    notes = [
        "wave 1 advisory: budget exhaustion is reported (FREEZE_RECOMMENDED); "
        "no release path is blocked by this module.",
        "read-only aggregation: data sources are never modified by this report.",
        budget["note"],
    ]
    if advisories:
        notes.append(
            f"部分数据源未接线（wave-2 ledger 项，共 {len(advisories)} 个）："
            "逐项 advisory 标注，computed 项正常判定，不因未接线源整体 NOT_VERIFIED"
        )
    if releases == 0 and slo_config["release_fee_units"]:
        notes.append(
            "release fee not assessed: no release ledger exists yet; pass "
            "--releases when a release record is available. 口径提示：release.py "
            "check 的 SLO 门禁按 releases=1 评估本次发布，metrics 报告用同一 "
            "releases 值即与 slo_gate 输出一致（同一 release_fee 函数）。"
        )

    return MetricsReport(
        window=window_tuple,
        generated_at=datetime.now(timezone.utc).isoformat(),
        git_commit=git_commit(root_path),
        task_id=task_id,
        phase=phase,
        gate_id=gate_id,
        tool_name="loop_metrics",
        tool_version="1.0.0",
        dora=dora,
        sli_eval=sli_eval,
        budget=budget,
        slo_source=slo_config["source"],
        sources=sources,
        status=status,
        missing=report_missing,
        notes=notes,
        advisories=advisories + advisory_items,
    )


def _fmt(value: Any, unit: str = "") -> str:
    if value is None or value == NOT_AVAILABLE:
        return "NOT_AVAILABLE"
    if isinstance(value, float):
        return f"{value:.4f}{unit}"
    return f"{value}{unit}"


def render_markdown(report: MetricsReport) -> str:
    """Human-readable DORA-style report (B2 §2.4 dashboard/output)."""
    lines: list[str] = []
    lines.append("# Loop-DORA Metrics Report")
    lines.append("")
    lines.append(f"- **Status**: {report.status}")
    lines.append(f"- **Window**: {report.window[0]} → {report.window[1]}")
    lines.append(f"- **Generated**: {report.generated_at}")
    lines.append(f"- **Git commit**: {report.git_commit or '(unavailable)'}")
    lines.append(f"- **Task**: {report.task_id} (phase {report.phase})")
    lines.append(f"- **Tool**: {report.tool_name} v{report.tool_version}")
    lines.append(f"- **SLO source**: {report.slo_source}")
    lines.append("")
    if report.missing:
        lines.append(f"**Missing data ({len(report.missing)}):** "
                     + "; ".join(report.missing))
        lines.append("")

    if report.advisories:
        lines.append(f"**Advisories ({len(report.advisories)} — 未接线数据源/"
                     "未落盘项，不影响 computed 判定):**")
        for a in report.advisories:
            lines.append(f"- {a}")
        lines.append("")

    lines.append("## Error budget")
    lines.append("")
    lines.append(f"- **Status**: {report.budget['status']}")
    lines.append(f"- **Remaining**: {report.budget['remaining_units']} / "
                 f"{report.budget['total_units']} units")
    lines.append(f"- **Consumed**: {report.budget['consumed_units']} units "
                 f"(breaches {report.budget['breach_consumption']} + releases "
                 f"{report.budget['release_consumption']})")
    lines.append(f"- **Note**: {report.budget['note']}")
    lines.append("")

    lines.append("## DORA metrics")
    lines.append("")
    lines.append("| Metric | Value | Basis / note |")
    lines.append("|---|---|---|")
    for name, m in report.dora.items():
        if m.get("status") == NOT_AVAILABLE:
            value = "NOT_AVAILABLE"
            basis = m.get("reason", "")
        else:
            value = m.get("value")
            basis = m.get("basis", "")
            if isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            value = str(value)
        lines.append(f"| `{name}` | {value} | {basis} |")
    lines.append("")

    lines.append("## SLI / SLO evaluation")
    lines.append("")
    lines.append("| SLI | Phase | Value | Target | Over target | Breach events | "
                 "Consumed units | Severity |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in report.sli_eval:
        value = _fmt(r.get("value"))
        target = r.get("target", {})
        target_str = f"{target.get('op', '?')} {target.get('value')}" \
                     f"{target.get('unit', '')}"
        lines.append(
            f"| `{r['sli_id']}` | {r.get('phase') or '-'} | {value} | "
            f"{target_str} | {r.get('over_target')} | "
            f"{r.get('breach_events')} | {r.get('consumed_units')} | "
            f"{r.get('severity')} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for note in report.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)
