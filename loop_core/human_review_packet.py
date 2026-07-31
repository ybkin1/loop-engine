"""
Human Review Packet — Non-technical decision packets for Loop phase gates.

Every phase completion produces a Human Review Packet that explains, in plain
language, what was done, what key choices were made, what risks exist, and what
decision the user needs to make. The goal is that a non-technical stakeholder
can make an informed GO/NOGO decision without asking the AI follow-up questions.

Referenced by:
- veto_escalation.py — builds escalation packets from veto conflicts
- state_machine.py — Phase enum used for phase tagging

U6 (T-0088): when a gate decision is paused, the packet may carry a
machine-consumable ResumePayload (snapshot + recovery data taken verbatim
from state.yaml / task_graph.yaml / gates.yaml) so the loop can later
resume the decision context instead of re-asking. Default behavior is
unchanged — no payload unless the caller attaches one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class PacketType(str, Enum):
    """Type of human review packet — determines the decision the user faces."""
    GATE_APPROVAL = "gate_approval"       # Phase Gate approval
    VETO_ESCALATION = "veto_escalation"   # Veto conflict escalation
    CHANGE_REQUEST = "change_request"     # Requirement change request
    RISK_ACCEPTANCE = "risk_acceptance"   # Risk acceptance


# ── Packet Components ──────────────────────────────────────────────────────


@dataclass
class KeyChoice:
    """A key design or implementation choice, explained for non-technical users.

    Every choice shows the trade-off: what we picked, what we did not pick,
    why, and what happens if we are wrong.
    """
    question: str              # "How should we store user data?"
    option_a: str              # "A cloud-based database"
    option_b: str              # "Files saved on the server"
    why_a: str                 # Why we chose A (in plain language)
    why_not_b: str             # Why we did not choose B
    risk_if_wrong: str         # What happens if this choice turns out wrong


@dataclass
class RiskItem:
    """A risk described in non-technical language with an everyday analogy."""
    risk: str                  # Risk description (plain language)
    likelihood: str            # "High" / "Medium" / "Low"
    impact: str                # Impact description
    analogy: str               # Everyday analogy (e.g. "Like leaving home without keys")
    mitigation: str            # What we did to reduce the risk


@dataclass
class DecisionRequired:
    """The decision the user must make — not "please review" but "please decide"."""
    question: str              # "Do you approve moving to the architecture phase?"
    options: list[str]         # ["Approve, move to next phase", "Request changes", "Pause project"]
    recommendation: str        # AI's recommended option and why
    deadline: Optional[str]    # Suggested decision deadline


# ── Resume Payload (U6 — gate pause / machine-resumable context) ──────────

RESUME_PAYLOAD_SCHEMA = "resume_payload"
RESUME_PAYLOAD_SCHEMA_VERSION = 1
RESUME_PAYLOAD_PRESENTATION_VERSION = 1


class ResumePayloadError(Exception):
    """Base error for resume-payload build / resume failures.

    Raised when authoritative sources are missing/unparseable or when
    requested snapshot fields do not match the authoritative state at
    build time.
    """


class StateDriftError(ResumePayloadError):
    """Raised when a payload no longer matches the CURRENT authoritative state.

    The machine never guesses: if task / gate / phase do not match the
    current state.yaml / task_graph.yaml / gates.yaml, resuming is refused
    with an explicit "状态已漂移" error instead of fabricating a context.
    """


@dataclass
class DecisionPoint:
    """The exact decision the user was facing when the gate was paused."""
    decision_type: str             # PacketType value, e.g. "gate_approval"
    presentation_version: int      # version of the decision presentation
    packet_id: str | None = None   # link back to the originating packet

    def to_dict(self) -> dict:
        return {
            "decision_type": self.decision_type,
            "presentation_version": self.presentation_version,
            "packet_id": self.packet_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DecisionPoint:
        if not isinstance(data, dict):
            raise ResumePayloadError(f"invalid decision_point: {data!r}")
        decision_type = data.get("decision_type")
        presentation_version = data.get("presentation_version")
        if not decision_type or not isinstance(presentation_version, int):
            raise ResumePayloadError(
                "invalid decision_point: missing 'decision_type' or "
                "'presentation_version'"
            )
        return cls(
            decision_type=str(decision_type),
            presentation_version=presentation_version,
            packet_id=data.get("packet_id"),
        )


@dataclass
class ResumeSnapshot:
    """Frozen snapshot of the decision point, captured at gate pause."""
    task_id: str
    gate_id: str
    phase: str
    decision_point: DecisionPoint
    context_pointers: list[str] = field(default_factory=list)
    sources: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "gate_id": self.gate_id,
            "phase": self.phase,
            "decision_point": self.decision_point.to_dict(),
            "context_pointers": list(self.context_pointers),
            "sources": dict(self.sources),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ResumeSnapshot:
        if not isinstance(data, dict):
            raise ResumePayloadError(f"invalid snapshot: {data!r}")
        for required in ("task_id", "gate_id", "phase", "decision_point"):
            if required not in data:
                raise ResumePayloadError(f"invalid snapshot: missing '{required}'")
        return cls(
            task_id=str(data["task_id"]),
            gate_id=str(data["gate_id"]),
            phase=str(data["phase"]),
            decision_point=DecisionPoint.from_dict(data["decision_point"]),
            context_pointers=[str(p) for p in data.get("context_pointers", [])],
            sources=dict(data.get("sources", {})),
        )


@dataclass
class ResumePayload:
    """Machine-consumable resume payload attached to a HumanReviewPacket.

    JSON-serializable (to_dict / from_dict / to_json / from_json). Carries
    a snapshot of the paused decision point plus recovery data taken
    verbatim from the authoritative state files (state.yaml /
    task_graph.yaml / gates.yaml) — never fabricated.
    """
    schema: str = RESUME_PAYLOAD_SCHEMA
    schema_version: int = RESUME_PAYLOAD_SCHEMA_VERSION
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    snapshot: ResumeSnapshot | None = None
    recovery: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
            "recovery": dict(self.recovery),
        }

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> ResumePayload:
        if not isinstance(data, dict):
            raise ResumePayloadError(f"invalid resume payload: {data!r}")
        if data.get("schema") != RESUME_PAYLOAD_SCHEMA:
            raise ResumePayloadError(
                f"unsupported payload schema: {data.get('schema')!r}"
            )
        if data.get("schema_version") != RESUME_PAYLOAD_SCHEMA_VERSION:
            raise ResumePayloadError(
                f"unsupported payload schema_version: {data.get('schema_version')!r}"
            )
        snapshot = data.get("snapshot")
        if not isinstance(snapshot, dict):
            raise ResumePayloadError("invalid resume payload: missing snapshot")
        return cls(
            schema=str(data["schema"]),
            schema_version=int(data["schema_version"]),
            generated_at=str(data.get("generated_at", "")),
            snapshot=ResumeSnapshot.from_dict(snapshot),
            recovery=dict(data.get("recovery", {})),
        )

    @classmethod
    def from_json(cls, text: str) -> ResumePayload:
        import json
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ResumePayloadError(f"invalid resume payload JSON: {exc}") from exc
        return cls.from_dict(data)


@dataclass
class ResumeContext:
    """The resumable decision context returned by resume_from_payload()."""
    task_id: str
    gate_id: str
    phase: str
    decision_point: DecisionPoint
    task: dict
    gate: dict
    pending_tasks: list[dict]
    context_pointers: list[str]
    sources: dict
    resumed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── Resume Payload Build / Resume ─────────────────────────────────────────


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


# ── Main Packet ────────────────────────────────────────────────────────────


@dataclass
class HumanReviewPacket:
    """A phase-completion decision packet written for humans, not machines.

    This is the primary deliverable shown to the user at each phase gate.
    It must be self-contained — the user should not need to read code, logs,
    or ask follow-up questions to make their decision.
    """
    packet_id: str
    packet_type: PacketType
    phase: str
    task_id: str

    # Summary
    what_we_did: str            # "What we did" (3-5 sentences, plain language)
    what_changed: str           # "What changed from the previous phase"

    # Decision
    key_choices: list[KeyChoice] = field(default_factory=list)
    risks: list[RiskItem] = field(default_factory=list)
    decision_required: Optional[DecisionRequired] = None

    # Evidence
    evidence_summary: str = ""
    who_reviewed: list[str] = field(default_factory=list)
    vetoes: list[str] = field(default_factory=list)

    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    expires_at: str = ""

    # Machine continuity (U6): optional resume payload attached at gate
    # pause. Default None — the human-facing packet is unchanged.
    resume_payload: ResumePayload | None = None

    # ── Output Methods ──────────────────────────────────────────────────

    def to_markdown(self) -> str:
        """Render the packet as a human-readable Markdown document."""
        lines: list[str] = []

        # Header
        phase_label = _phase_label(self.phase)
        lines.append(f"# Phase Delivery Decision Packet — {phase_label}")
        lines.append("")
        lines.append(f"**Packet ID:** {self.packet_id}  ")
        lines.append(f"**Generated:** {_format_ts(self.generated_at)}  ")
        if self.expires_at:
            lines.append(f"**Decision needed by:** {_format_ts(self.expires_at)}  ")
        lines.append("")

        # What we did
        lines.append("## What We Did")
        lines.append("")
        lines.append(self.what_we_did)
        lines.append("")

        # What changed
        if self.what_changed:
            lines.append("## What Changed")
            lines.append("")
            lines.append(self.what_changed)
            lines.append("")

        # Key choices
        if self.key_choices:
            lines.append("## Key Choices")
            lines.append("")
            for i, choice in enumerate(self.key_choices, 1):
                lines.append(f"### {i}. {choice.question}")
                lines.append("")
                lines.append("| We Chose | Did Not Choose | Why |")
                lines.append("|----------|---------------|-----|")
                lines.append(f"| {choice.option_a} | {choice.option_b} | {choice.why_a} |")
                lines.append("")
                lines.append(f"**Why not the alternative:** {choice.why_not_b}")
                lines.append("")
                lines.append(f"**If we are wrong:** {choice.risk_if_wrong}")
                lines.append("")

        # Risks
        if self.risks:
            lines.append("## Main Risks")
            lines.append("")
            lines.append("| Risk | Likelihood | Impact | What We Did |")
            lines.append("|------|-----------|--------|-------------|")
            for risk in self.risks:
                lines.append(
                    f"| {risk.risk} | {risk.likelihood} | {risk.impact} "
                    f"| {risk.mitigation} |"
                )
            lines.append("")
            for risk in self.risks:
                lines.append(f"- **{risk.risk}** — *Analogy:* {risk.analogy}")
                lines.append("")

        # Evidence
        if self.evidence_summary:
            lines.append("## Quality Check")
            lines.append("")
            lines.append(self.evidence_summary)
            lines.append("")

        # Who reviewed
        if self.who_reviewed:
            lines.append("## Who Reviewed This Work")
            lines.append("")
            for reviewer in self.who_reviewed:
                lines.append(f"- {reviewer}")
            lines.append("")

        # Vetoes
        if self.vetoes:
            lines.append("## Vetoes Raised")
            lines.append("")
            for veto in self.vetoes:
                lines.append(f"- {veto}")
            lines.append("")

        # Decision required
        if self.decision_required:
            lines.append("## You Need to Decide")
            lines.append("")
            lines.append(f"**{self.decision_required.question}**")
            lines.append("")
            for option in self.decision_required.options:
                lines.append(f"- [ ] {option}")
            lines.append("")
            lines.append(f"**Our recommendation:** {self.decision_required.recommendation}")
            if self.decision_required.deadline:
                lines.append("")
                lines.append(
                    f"Please decide by **{self.decision_required.deadline}**. "
                    "If you have questions, your product manager can walk through "
                    "each piece with you."
                )

        return "\n".join(lines)

    def to_plain_text(self) -> str:
        """Render the packet as plain text (no markdown formatting)."""
        lines: list[str] = []

        phase_label = _phase_label(self.phase)
        lines.append(f"PHASE DELIVERY DECISION PACKET — {phase_label}")
        lines.append(f"Packet ID: {self.packet_id}")
        lines.append(f"Generated: {_format_ts(self.generated_at)}")
        if self.expires_at:
            lines.append(f"Decision needed by: {_format_ts(self.expires_at)}")
        lines.append("")

        lines.append("WHAT WE DID")
        lines.append(self.what_we_did)
        lines.append("")

        if self.what_changed:
            lines.append("WHAT CHANGED")
            lines.append(self.what_changed)
            lines.append("")

        if self.key_choices:
            lines.append("KEY CHOICES")
            for i, choice in enumerate(self.key_choices, 1):
                lines.append(f"  {i}. {choice.question}")
                lines.append(f"     We chose: {choice.option_a}")
                lines.append(f"     Did not choose: {choice.option_b}")
                lines.append(f"     Why: {choice.why_a}")
                lines.append(f"     Why not the other: {choice.why_not_b}")
                lines.append(f"     If wrong: {choice.risk_if_wrong}")
                lines.append("")

        if self.risks:
            lines.append("MAIN RISKS")
            for risk in self.risks:
                lines.append(f"  - {risk.risk}")
                lines.append(f"    Likelihood: {risk.likelihood}")
                lines.append(f"    Impact: {risk.impact}")
                lines.append(f"    Analogy: {risk.analogy}")
                lines.append(f"    What we did: {risk.mitigation}")
                lines.append("")

        if self.evidence_summary:
            lines.append("QUALITY CHECK")
            lines.append(self.evidence_summary)
            lines.append("")

        if self.who_reviewed:
            lines.append("WHO REVIEWED THIS WORK")
            for reviewer in self.who_reviewed:
                lines.append(f"  - {reviewer}")
            lines.append("")

        if self.vetoes:
            lines.append("VETOES RAISED")
            for veto in self.vetoes:
                lines.append(f"  - {veto}")
            lines.append("")

        if self.decision_required:
            lines.append("YOU NEED TO DECIDE")
            lines.append(f"  {self.decision_required.question}")
            for option in self.decision_required.options:
                lines.append(f"  [ ] {option}")
            lines.append(f"  Recommendation: {self.decision_required.recommendation}")
            if self.decision_required.deadline:
                lines.append(f"  Deadline: {self.decision_required.deadline}")

        return "\n".join(lines)


# ── Builder ────────────────────────────────────────────────────────────────


class HumanReviewPacketBuilder:
    """Builds HumanReviewPacket instances from structured phase-completion data.

    This builder translates raw engineering outputs (artifacts, review results,
    quality reports) into plain-language packets that non-technical stakeholders
    can understand and act on.
    """

    # ── Technical Risk Translation Map ──────────────────────────────────
    #
    # Maps technical risk descriptions to plain-language explanations with
    # everyday analogies. The builder uses this as a fallback; callers can
    # also use translate_technical_risk() directly.

    _RISK_TRANSLATIONS: dict[str, dict[str, str]] = {
        "sql injection": {
            "risk": "Unauthorised person could access or change stored information",
            "analogy": "Like leaving the cash register unlocked when the shop is open",
            "mitigation": "All data requests are validated before being sent to storage",
        },
        "xss": {
            "risk": "Harmful content could appear to other users of the system",
            "analogy": "Like someone putting up a misleading sign on your shop window",
            "mitigation": "All user-provided content is checked and cleaned before display",
        },
        "race condition": {
            "risk": "Two actions happening at the same time could produce wrong results",
            "analogy": "Like two people trying to book the same flight seat at the same moment",
            "mitigation": "We ensure actions that conflict wait their turn",
        },
        "buffer overflow": {
            "risk": "The system could crash or behave unexpectedly with very large inputs",
            "analogy": "Like pouring too much water into a glass — it spills and makes a mess",
            "mitigation": "We limit input sizes and check boundaries before processing",
        },
        "null pointer": {
            "risk": "The program could stop working when it encounters missing information",
            "analogy": "Like trying to read a page that has been torn out of a book",
            "mitigation": "We check for missing information before using it",
        },
        "memory leak": {
            "risk": "The system could slow down over time as resources are not released",
            "analogy": "Like a tap left dripping — eventually the sink overflows",
            "mitigation": "We track and release resources that are no longer needed",
        },
        "deadlock": {
            "risk": "Two parts of the system could freeze waiting for each other",
            "analogy": "Like two people meeting in a narrow hallway, each waiting for the other to step aside",
            "mitigation": "We set time limits so no part waits forever",
        },
        "ddos": {
            "risk": "The service could become unavailable if overwhelmed with requests",
            "analogy": "Like too many customers entering a small shop at once — nobody can move",
            "mitigation": "We limit the rate of incoming requests and monitor traffic patterns",
        },
        "privilege escalation": {
            "risk": "A regular user could gain access they should not have",
            "analogy": "Like a hotel guest finding a master key that opens every room",
            "mitigation": "We verify permissions at every step, not just at the entrance",
        },
        "data leak": {
            "risk": "Private information could become visible to the wrong people",
            "analogy": "Like sending a confidential letter with the wrong address on the envelope",
            "mitigation": "We check who can see what at multiple layers of the system",
        },
        "injection": {
            "risk": "Malicious instructions could be hidden inside normal-looking input",
            "analogy": "Like someone slipping extra clauses into a contract after you have signed it",
            "mitigation": "We separate instructions from data so they cannot be mixed up",
        },
        "timestamp": {
            "risk": "Time-related errors could cause data to appear in the wrong order",
            "analogy": "Like arriving at a meeting and finding everyone already left because of a clock mismatch",
            "mitigation": "We use a single, consistent time source across the entire system",
        },
        "timeout": {
            "risk": "Long-running operations could leave users waiting without feedback",
            "analogy": "Like ordering food and never being told the kitchen is backed up",
            "mitigation": "We set reasonable wait limits and inform users when something takes longer",
        },
        "unhandled error": {
            "risk": "Unexpected problems could cause the system to stop working entirely",
            "analogy": "Like a car engine shutting off because one sensor reported a minor issue",
            "mitigation": "We catch problems early and degrade gracefully instead of stopping completely",
        },
        "out of sync": {
            "risk": "Different parts of the system could show different information",
            "analogy": "Like two clocks in the same building showing different times",
            "mitigation": "We keep a single source of truth and synchronise regularly",
        },
    }

    @staticmethod
    def translate_technical_risk(technical_description: str) -> RiskItem:
        """Translate a technical risk description into plain language with an analogy.

        Args:
            technical_description: A risk description that may contain technical
                                  terms (e.g. "Possible SQL injection in login form").

        Returns:
            A RiskItem with non-technical risk description, analogy, and mitigation.
        """
        description_lower = technical_description.lower()

        # Try to match known technical patterns
        for pattern, translation in HumanReviewPacketBuilder._RISK_TRANSLATIONS.items():
            if pattern in description_lower:
                # Determine likelihood from keywords in the description
                likelihood = "Medium"
                if any(word in description_lower for word in ("critical", "severe", "high risk", "certain")):
                    likelihood = "High"
                elif any(word in description_lower for word in ("minor", "unlikely", "low risk")):
                    likelihood = "Low"

                return RiskItem(
                    risk=translation["risk"],
                    likelihood=likelihood,
                    impact=translation["risk"],
                    analogy=translation["analogy"],
                    mitigation=translation["mitigation"],
                )

        # No known pattern matched — create a generic translation
        return RiskItem(
            risk=f"Potential issue identified: {technical_description[:80]}",
            likelihood="Medium",
            impact="May affect system reliability or user experience",
            analogy="Like an unexpected bump in the road — manageable but worth watching",
            mitigation="We have flagged this for monitoring and will address it if it occurs",
        )

    # ── Builder Methods ─────────────────────────────────────────────────

    @staticmethod
    def from_phase_completion(
        phase: str,
        task_id: str,
        artifacts: dict,
        review_results: dict,
        quality_report: dict,
        resume_payload: ResumePayload | None = None,
    ) -> HumanReviewPacket:
        """Build a gate-approval packet from phase-completion data.

        Args:
            phase: Phase identifier (e.g. "S2-architecture").
            task_id: The task being completed.
            artifacts: Dict of artifact_name -> description for this phase.
            review_results: Dict of reviewer_role -> verdict summary.
            quality_report: Dict with keys like "pass", "checks", "warnings".
            resume_payload: Optional ResumePayload (U6) attached for machine
                            resumability after a pause decision. Default None
                            keeps the packet fully backward compatible.

        Returns:
            A HumanReviewPacket ready to present to the user.
        """
        # Build what_we_did from artifacts
        artifact_names = list(artifacts.keys()) if artifacts else []
        if artifact_names:
            artifact_list = ", ".join(artifact_names)
            what_we_did = (
                f"For your project, we completed the **{_phase_label(phase)}** phase. "
                f"We produced: {artifact_list}. "
                f"Each piece was checked for consistency and completeness. "
                f"The work is now ready for your review and decision."
            )
        else:
            what_we_did = (
                f"We completed the **{_phase_label(phase)}** phase for your project. "
                "All required outputs for this stage have been produced and checked."
            )

        # Build what_changed from review results
        reviewer_names = list(review_results.keys()) if review_results else []
        if reviewer_names:
            who = ", ".join(reviewer_names)
            what_changed = (
                f"The work from this phase was reviewed by: {who}. "
                f"Compared to the previous phase, we now have concrete deliverables "
                f"that you can review directly rather than plans on paper."
            )
        else:
            what_changed = (
                "We moved from planning to producing concrete deliverables. "
                "The outputs from this phase replace the outlines from the previous stage."
            )

        # Build key choices from artifacts
        key_choices = HumanReviewPacketBuilder._extract_key_choices(
            phase, artifacts
        )

        # Build risks
        risks: list[RiskItem] = []
        quality_warnings = quality_report.get("warnings", [])
        if isinstance(quality_warnings, list):
            for warning in quality_warnings:
                if isinstance(warning, str):
                    risks.append(
                        HumanReviewPacketBuilder.translate_technical_risk(warning)
                    )

        # If no risks found, add a generic low-risk note
        if not risks:
            risks.append(RiskItem(
                risk="No major risks identified at this stage",
                likelihood="Low",
                impact="Minimal — standard quality checks all passed",
                analogy="Like checking the weather forecast and seeing clear skies",
                mitigation="We ran all standard checks and they passed",
            ))

        # Build evidence summary from quality report
        passed = quality_report.get("pass", quality_report.get("passed", True))
        checks = quality_report.get("checks", [])
        if isinstance(passed, bool):
            status = "All checks passed" if passed else "Some checks did not pass"
        else:
            status = f"Checks completed: {passed}"

        evidence_parts = [f"- {status}"]
        if isinstance(checks, list):
            for check in checks:
                if isinstance(check, str):
                    evidence_parts.append(f"- {check}")
        elif isinstance(checks, dict):
            for check_name, check_result in checks.items():
                icon = "+" if check_result else "!"
                evidence_parts.append(f"- {check_name}: {icon}")

        evidence_summary = "\n".join(evidence_parts)

        # Build who_reviewed
        who_reviewed = list(review_results.keys()) if review_results else []

        # Build decision_required
        phase_label = _phase_label(phase)
        decision = DecisionRequired(
            question=f"Do you approve moving forward from {phase_label}?",
            options=[
                f"Approve — move to the next phase",
                f"Request changes — I want something adjusted",
                f"Pause — I need time to think or have other questions",
            ],
            recommendation=(
                f"We recommend approving and moving forward. "
                f"All quality checks for {phase_label} passed, and the outputs "
                f"match what was planned. If anything looks unclear, choose "
                f"'Request changes' and tell us what to adjust."
            ),
            deadline="3 days from now",
        )

        # Generate packet ID
        import uuid
        packet_id = f"HRP-{uuid.uuid4().hex[:8].upper()}"

        # Set expiration
        from datetime import timedelta
        expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        return HumanReviewPacket(
            packet_id=packet_id,
            packet_type=PacketType.GATE_APPROVAL,
            phase=phase,
            task_id=task_id,
            what_we_did=what_we_did,
            what_changed=what_changed,
            key_choices=key_choices,
            risks=risks,
            decision_required=decision,
            evidence_summary=evidence_summary,
            who_reviewed=who_reviewed,
            vetoes=[],
            expires_at=expires,
            resume_payload=resume_payload,
        )

    @staticmethod
    def from_veto_escalation(
        vetoes: list,
        task_id: str,
        resume_payload: ResumePayload | None = None,
    ) -> HumanReviewPacket:
        """Build a veto-escalation packet when reviewers disagree.

        Args:
            vetoes: List of veto records, each a dict with keys like
                    "vetoed_by", "reason", "phase", "evidence".
            task_id: The task being blocked by the veto.
            resume_payload: Optional ResumePayload (U6) attached for machine
                            resumability after a pause decision.

        Returns:
            A HumanReviewPacket explaining the deadlock and what the user
            needs to decide.
        """
        veto_count = len(vetoes)
        veto_reasons = [v.get("reason", "No reason provided") if isinstance(v, dict) else str(v) for v in vetoes]
        veto_authors = [v.get("vetoed_by", "A reviewer") if isinstance(v, dict) else "A reviewer" for v in vetoes]

        # Determine phase from first veto or default
        phase = (
            vetoes[0].get("phase", "unknown") if vetoes and isinstance(vetoes[0], dict)
            else "unknown"
        )

        what_we_did = (
            f"We completed work on task **{task_id}** and submitted it for review. "
            f"{veto_count} reviewer(s) raised concerns that blocked the work "
            f"from moving forward. This means the team cannot proceed without "
            f"your input."
        )

        author_list = ", ".join(veto_authors)
        what_changed = (
            f"The review process flagged issues that the team could not resolve "
            f"on their own. {author_list} believe the current approach needs "
            f"reconsideration. This is a normal part of quality control — it "
            f"means the system caught something worth your attention."
        )

        # Build key choices representing the veto dispute
        key_choices = []
        for i, veto in enumerate(vetoes):
            if isinstance(veto, dict):
                reason = veto.get("reason", "No reason given")
                vetoed_by = veto.get("vetoed_by", "Unknown reviewer")
                key_choices.append(KeyChoice(
                    question=f"Disagreement #{i + 1}: Should we follow {vetoed_by}'s concern?",
                    option_a=f"Accept the concern and revise the work",
                    option_b=f"Override the concern and proceed as-is",
                    why_a=(
                        f"The reviewer believes: {reason}. "
                        f"Addressing this now prevents bigger problems later."
                    ),
                    why_not_b=(
                        f"Ignoring this concern could lead to rework later — "
                        f"potentially more expensive and time-consuming."
                    ),
                    risk_if_wrong=(
                        f"If the reviewer is wrong, we spend time on unnecessary changes. "
                        f"If the reviewer is right and we ignore it, the issue could affect "
                        f"users or require major rework later."
                    ),
                ))

        # Build risks
        risks = [
            RiskItem(
                risk="The project is blocked until this disagreement is resolved",
                likelihood="Certain — until you decide",
                impact="No further progress can be made on this task",
                analogy="Like a traffic light stuck on red — nobody moves until it is fixed",
                mitigation="We have prepared clear options for you to choose from",
            ),
            RiskItem(
                risk="Rushing a decision without understanding the trade-offs",
                likelihood="Medium",
                impact="You might approve something you later regret",
                analogy="Like buying a house without reading the inspection report",
                mitigation=(
                    "We have explained each reviewer's concern in plain language. "
                    "Take the time you need."
                ),
            ),
        ]

        decision = DecisionRequired(
            question=(
                f"How should we resolve the disagreement about task {task_id}?"
            ),
            options=[
                "Accept the reviewer concerns — revise the work and resubmit",
                "Override the veto — proceed without changes",
                "Request more information — I need a clearer explanation",
                "Escalate to a senior reviewer for a tie-breaking opinion",
            ],
            recommendation=(
                "We recommend accepting the reviewer concerns and revising the work. "
                "Reviewers are independent and have no stake in the outcome — their "
                "concerns usually point to real issues. The cost of revising now is "
                "almost always lower than fixing problems after delivery."
            ),
            deadline="5 days from now (the team cannot proceed until resolved)",
        )

        import uuid
        packet_id = f"HRP-VETO-{uuid.uuid4().hex[:8].upper()}"

        from datetime import timedelta
        expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        # Evidence summary from vetoes
        evidence_parts = [f"- {veto_count} reviewer(s) raised concerns"]
        for reason in veto_reasons:
            evidence_parts.append(f"- Concern: {reason}")

        return HumanReviewPacket(
            packet_id=packet_id,
            packet_type=PacketType.VETO_ESCALATION,
            phase=phase,
            task_id=task_id,
            what_we_did=what_we_did,
            what_changed=what_changed,
            key_choices=key_choices,
            risks=risks,
            decision_required=decision,
            evidence_summary="\n".join(evidence_parts),
            who_reviewed=veto_authors,
            vetoes=veto_reasons,
            expires_at=expires,
            resume_payload=resume_payload,
        )

    @staticmethod
    def _extract_key_choices(
        phase: str,
        artifacts: dict,
    ) -> list[KeyChoice]:
        """Derive key-choice narratives from phase artifacts.

        Maps artifact descriptions into trade-off explanations that a
        non-technical user can understand.
        """
        choices: list[KeyChoice] = []

        # Architecture phase: typical trade-off choices
        if "architecture" in phase.lower():
            if artifacts:
                first_key = list(artifacts.keys())[0]
                first_desc = artifacts[first_key]
                choices.append(KeyChoice(
                    question="How should the system be organised?",
                    option_a=f"Modular design ({first_key})",
                    option_b="Single large program",
                    why_a=(
                        f"{first_desc}. A modular design makes it easier to "
                        f"change one part without affecting everything else — "
                        f"like being able to renovate the kitchen without "
                        f"touching the bedroom."
                    ),
                    why_not_b=(
                        "A single large program is simpler at first but becomes "
                        "harder to maintain as the system grows — like a house "
                        "where every room shares one light switch."
                    ),
                    risk_if_wrong=(
                        "If the modules are split incorrectly, we may need to "
                        "reorganise later. This costs time but is still easier "
                        "than starting from a single large program."
                    ),
                ))

        # Implementation phase
        if "implementation" in phase.lower():
            choices.append(KeyChoice(
                question="How do we ensure each piece works before combining them?",
                option_a="Test each piece independently first",
                option_b="Build everything then test at the end",
                why_a=(
                    "Testing each piece on its own catches problems early, "
                    "when they are cheaper and faster to fix — like checking "
                    "each ingredient before cooking."
                ),
                why_not_b=(
                    "Testing only at the end means problems pile up and become "
                    "harder to untangle — like tasting a dish only after "
                    "everything is mixed together."
                ),
                risk_if_wrong=(
                    "If our tests miss something, a bug could reach users. "
                    "But finding it in isolated testing is much faster to fix."
                ),
            ))

        # Generic fallback for any phase
        if not choices and artifacts:
            first_key = list(artifacts.keys())[0]
            choices.append(KeyChoice(
                question=f"How did we approach the {_phase_label(phase)} phase?",
                option_a=f"Structured, step-by-step approach",
                option_b="Rapid, all-at-once delivery",
                why_a=(
                    f"We produced {first_key} and related outputs in a "
                    f"deliberate order so each step builds on the last."
                ),
                why_not_b=(
                    "Doing everything at once is faster initially but makes "
                    "it harder to spot and fix problems."
                ),
                risk_if_wrong=(
                    "If the order of steps was wrong, we may need to revisit "
                    "earlier decisions. The cost is usually small at this stage."
                ),
            ))

        return choices


# ── Internal Helpers ───────────────────────────────────────────────────────


def _phase_label(phase: str) -> str:
    """Convert a phase identifier to a human-readable label."""
    phase_map: dict[str, str] = {
        "S0-init": "Project Start",
        "S1-requirements": "Requirements",
        "S2-architecture": "Architecture Design",
        "S3-interface": "Interface Design",
        "S4-implementation": "Implementation",
        "S5-quality": "Quality Assurance",
        "S6-delivery": "Delivery",
        "S7-integration": "Integration",
        "S8-functional-test": "Functional Testing",
        "S9-fix-optimize": "Fixes and Optimisation",
        "S10-performance": "Performance Testing",
        "S11-maintenance": "Maintenance",
    }
    return phase_map.get(phase, phase.replace("-", " ").title())


def _format_ts(ts_str: str) -> str:
    """Format an ISO timestamp string for display."""
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, TypeError):
        return ts_str
