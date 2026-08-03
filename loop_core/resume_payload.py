"""
Resume payload build / resume logic (U6, T-0088) — extracted module.

T-0110 批 B-2 拆分（行为等价，纯外提 re-export）：
- 原 loop_core/human_review_packet.py 的 Resume 载荷逻辑（_load_authoritative_yaml /
  _find_task / _find_gate / build_resume_payload / resume_from_payload + 恢复字段
  常量）逐字迁移至此（design-common-weakness.md 1.4 拆分边界表 :256-526）。
- 依赖图：仅依赖 review_models（叶子）；壳文件 re-export 保持公开面逐名一致。
- fail-closed 语义保持：权威来源缺失/不可解析抛 ResumePayloadError；恢复时
  任何状态漂移抛 StateDriftError（机器从不猜测）。
"""
from __future__ import annotations

from pathlib import Path

from loop_core.review_models import (
    RESUME_PAYLOAD_PRESENTATION_VERSION,
    DecisionPoint,
    PacketType,
    ResumeContext,
    ResumePayload,
    ResumePayloadError,
    ResumeSnapshot,
    StateDriftError,
)


def _load_authoritative_yaml(project_root: str | Path, filename: str) -> dict:
    """Load one authoritative governance YAML file; fail-closed on absence."""
    import yaml

    path = Path(project_root) / ".ai" / filename
    if not path.exists():
        raise ResumePayloadError(f"来源文件缺失 (source file missing): {path}")
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:  # noqa: BLE001 — fail-closed on any parse issue
        raise ResumePayloadError(
            f"无法解析来源文件 (unparseable source) {path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ResumePayloadError(
            f"来源文件格式错误 (source is not a mapping): {path}"
        )
    return data


def _find_task(task_graph: dict, task_id: str) -> dict | None:
    for task in task_graph.get("tasks", []):
        if isinstance(task, dict) and task.get("id") == task_id:
            return task
    return None


def _find_gate(gates: dict, gate_id: str) -> dict | None:
    for gate in gates.get("gates", []):
        if isinstance(gate, dict) and gate.get("id") == gate_id:
            return gate
    return None


_TASK_RECOVERY_FIELDS = ("id", "title", "status", "phase", "priority", "note")
_GATE_RECOVERY_FIELDS = (
    "id", "task_id", "gate_type", "status", "decision",
    "recorded_at", "approval_actor", "approval_source", "evidence",
)


def _task_recovery_record(task: dict) -> dict:
    """Copy the task record verbatim from task_graph.yaml (subset of fields)."""
    record = {k: task[k] for k in _TASK_RECOVERY_FIELDS if k in task}
    if "depends_on" in task:
        record["depends_on"] = list(task["depends_on"])
    if "gates" in task:
        record["gates"] = list(task["gates"])
    return record


def _gate_recovery_record(gate: dict) -> dict:
    """Copy the gate record verbatim from gates.yaml (subset of fields)."""
    return {k: gate[k] for k in _GATE_RECOVERY_FIELDS if k in gate}


def _pending_tasks(task_graph: dict) -> list[dict]:
    """Tasks not yet completed/blocked, taken verbatim from task_graph.yaml."""
    pending: list[dict] = []
    for task in task_graph.get("tasks", []):
        if not isinstance(task, dict):
            continue
        status = str(task.get("status", "")).lower()
        if status in ("pending", "in_progress", "active"):
            pending.append({
                "id": task.get("id"),
                "title": task.get("title"),
                "status": task.get("status"),
                "priority": task.get("priority"),
            })
    pending.sort(key=lambda rec: str(rec.get("id") or ""))
    return pending


def build_resume_payload(
    project_root: str | Path,
    *,
    task_id: str,
    gate_id: str,
    phase: str,
    decision_type: str | PacketType,
    presentation_version: int = RESUME_PAYLOAD_PRESENTATION_VERSION,
    packet_id: str | None = None,
) -> ResumePayload:
    """Build a resume payload from authoritative state — never fabricated.

    Validation performed at build time (fail-closed):
    - state.yaml / task_graph.yaml / gates.yaml all exist and parse
    - state.yaml current task / gate / phase match the requested snapshot
    - task_graph.yaml contains the task
    - gates.yaml contains the gate, bound to that task

    Raises ResumePayloadError when any validation fails.
    """
    root = Path(project_root)
    state = _load_authoritative_yaml(root, "state.yaml")
    task_graph = _load_authoritative_yaml(root, "task_graph.yaml")
    gates = _load_authoritative_yaml(root, "gates.yaml")

    # state.yaml field consistency — the authoritative pointer must agree
    actual_task = state.get("current_task_id")
    actual_gate = state.get("current_gate_id")
    actual_phase = state.get("current_phase")
    if actual_task != task_id:
        raise ResumePayloadError(
            f"state.yaml 字段不一致: current_task_id={actual_task!r} "
            f"!= 请求 {task_id!r}"
        )
    if actual_gate != gate_id:
        raise ResumePayloadError(
            f"state.yaml 字段不一致: current_gate_id={actual_gate!r} "
            f"!= 请求 {gate_id!r}"
        )
    if actual_phase != phase:
        raise ResumePayloadError(
            f"state.yaml 字段不一致: current_phase={actual_phase!r} "
            f"!= 请求 {phase!r}"
        )

    # task_graph.yaml consistency
    task = _find_task(task_graph, task_id)
    if task is None:
        raise ResumePayloadError(f"task_graph.yaml 中不存在任务: {task_id}")

    # gates.yaml consistency
    gate = _find_gate(gates, gate_id)
    if gate is None:
        raise ResumePayloadError(f"gates.yaml 中不存在 gate: {gate_id}")
    if gate.get("task_id") != task_id:
        raise ResumePayloadError(
            f"gates.yaml 字段不一致: gate {gate_id} 绑定 task "
            f"{gate.get('task_id')!r} != 请求 {task_id!r}"
        )

    decision = DecisionPoint(
        decision_type=(
            decision_type.value
            if isinstance(decision_type, PacketType)
            else str(decision_type)
        ),
        presentation_version=presentation_version,
        packet_id=packet_id,
    )

    sources = {
        "state.yaml": str(root / ".ai" / "state.yaml"),
        "task_graph.yaml": str(root / ".ai" / "task_graph.yaml"),
        "gates.yaml": str(root / ".ai" / "gates.yaml"),
    }

    # Context pointers: the authoritative sources plus task file / evidence
    # dir — only paths that actually exist are pointed to.
    context_pointers = list(sources.values())
    task_file = root / ".ai" / "tasks" / f"{task_id}.md"
    evidence_dir = root / ".ai" / "evidence" / task_id
    for pointer in (task_file, evidence_dir):
        if pointer.exists():
            context_pointers.append(str(pointer))

    recovery = {
        "task": _task_recovery_record(task),
        "gate": _gate_recovery_record(gate),
        "phase": phase,
        "pending_tasks": _pending_tasks(task_graph),
    }

    return ResumePayload(
        snapshot=ResumeSnapshot(
            task_id=task_id,
            gate_id=gate_id,
            phase=phase,
            decision_point=decision,
            context_pointers=context_pointers,
            sources=sources,
        ),
        recovery=recovery,
    )


def resume_from_payload(
    payload: ResumePayload | dict,
    project_root: str | Path,
) -> ResumeContext:
    """Resume a paused decision context from its resume payload.

    Verifies the payload against the CURRENT authoritative state:
    - state.yaml current task / gate / phase must match the payload snapshot
    - the task must still exist in task_graph.yaml
    - the gate must still exist, be bound to the task, and still be
      awaiting a decision (status == "pending")

    Any mismatch raises StateDriftError (状态已漂移) — the machine never
    guesses. Returns a ResumeContext with recovery data refreshed from the
    current authoritative state.
    """
    if isinstance(payload, dict):
        payload = ResumePayload.from_dict(payload)
    if not isinstance(payload, ResumePayload):
        raise ResumePayloadError(f"无效 resume payload: {type(payload).__name__}")
    if payload.snapshot is None:
        raise ResumePayloadError("无效 resume payload: 缺少 snapshot")

    root = Path(project_root)
    snap = payload.snapshot
    state = _load_authoritative_yaml(root, "state.yaml")
    task_graph = _load_authoritative_yaml(root, "task_graph.yaml")
    gates = _load_authoritative_yaml(root, "gates.yaml")

    # 1. state.yaml drift checks — task / gate / phase
    actual_task = state.get("current_task_id")
    actual_gate = state.get("current_gate_id")
    actual_phase = state.get("current_phase")
    if actual_task != snap.task_id:
        raise StateDriftError(
            f"状态已漂移 (STATE_DRIFT): state.yaml current_task_id="
            f"{actual_task!r} != payload task_id={snap.task_id!r} — 无法恢复，不猜测"
        )
    if actual_gate != snap.gate_id:
        raise StateDriftError(
            f"状态已漂移 (STATE_DRIFT): state.yaml current_gate_id="
            f"{actual_gate!r} != payload gate_id={snap.gate_id!r} — 无法恢复，不猜测"
        )
    if actual_phase != snap.phase:
        raise StateDriftError(
            f"状态已漂移 (STATE_DRIFT): state.yaml current_phase="
            f"{actual_phase!r} != payload phase={snap.phase!r} — 无法恢复，不猜测"
        )

    # 2. the task must still exist
    task = _find_task(task_graph, snap.task_id)
    if task is None:
        raise StateDriftError(
            f"状态已漂移 (STATE_DRIFT): task_graph.yaml 中已不存在任务 "
            f"{snap.task_id} — 无法恢复"
        )

    # 3. the gate must still exist, be bound to the task, and still be pending
    gate = _find_gate(gates, snap.gate_id)
    if gate is None:
        raise StateDriftError(
            f"状态已漂移 (STATE_DRIFT): gates.yaml 中已不存在 gate "
            f"{snap.gate_id} — 无法恢复"
        )
    if gate.get("task_id") != snap.task_id:
        raise StateDriftError(
            f"状态已漂移 (STATE_DRIFT): gate {snap.gate_id} 现绑定 task "
            f"{gate.get('task_id')!r} != payload task_id={snap.task_id!r} — 无法恢复"
        )
    if str(gate.get("status", "")).lower() != "pending":
        raise StateDriftError(
            f"状态已漂移 (STATE_DRIFT): gate {snap.gate_id} 已裁决 "
            f"(status={gate.get('status')!r}) — 决策已完成，无需恢复"
        )

    return ResumeContext(
        task_id=snap.task_id,
        gate_id=snap.gate_id,
        phase=snap.phase,
        decision_point=snap.decision_point,
        task=_task_recovery_record(task),
        gate=_gate_recovery_record(gate),
        pending_tasks=_pending_tasks(task_graph),
        context_pointers=list(snap.context_pointers),
        sources=dict(snap.sources),
    )
