"""
Review packet data models — shared by loop_core.human_review_packet (shell).

T-0110 批 B-2 拆分（行为等价，纯外提 re-export）：
- 原 loop_core/human_review_packet.py 的数据模型层（PacketType / KeyChoice /
  RiskItem / DecisionRequired / DecisionPoint / ResumeSnapshot / ResumePayload /
  ResumeContext 及 to/from_dict 序列化）逐字迁移至此（design-common-weakness.md
  1.4 拆分边界表 :34-254）。
- 本模块是依赖图叶子：零 loop_core 内部依赖，仅标准库。
- 壳文件通过 ``from loop_core.review_models import ...`` re-export 保持公开面
  （含私有名）逐名一致，行为不变。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


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
    deadline: str | None    # Suggested decision deadline


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
