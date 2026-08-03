"""
Governance metrics — 数据加载层（T-0110 批 B-1 拆分产物）。

从 loop_core/governance_metrics.py 外提（design-common-weakness.md 1.2 边界：
"数据加载器（_load_jsonl/load_gates/load_tasks/load_guard_events/
load_phase_transitions/load_executions/load_runtime_events）:215-370"，
含同节的 DataSourceUnavailableError :216-218）。

语义必须保持（拆分硬门槛）：
- ``load_guard_events`` 的 strict-parse fail-closed（:303-322，损坏行 →
  DataSourceUnavailableError 而非静默跳过）；
- 其余加载器缺失/不可解析一律 DataSourceUnavailableError（NOT_AVAILABLE，
  绝不猜零）——slo_gate.py 依赖该异常语义。

依赖：governance_aggregations（叶子）——记录数据类 / _parse_dt /
classify_gate_phase。public 面由 governance_metrics 壳 re-export 保持。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import yaml

from loop_core.governance_aggregations import (
    GateMetric,
    PhaseTransition,
    TaskRecord,
    _parse_dt,
    classify_gate_phase,
)
from loop_core.observability import GuardCheckEvent

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
