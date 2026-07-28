"""
Veto Escalation Protocol — resolve conflicting role vetoes in Loop Engineering.

When multiple roles exercise their veto power simultaneously, the project may
deadlock. This module defines the escalation protocol that determines:
  - When to escalate (based on the number and domain of vetoing roles)
  - Where to escalate (role-internal, cross-role negotiation, or user gate)
  - What information to carry (evidence, remediation suggestions, human-review packet)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class VetoSeverity(str, Enum):
    """How severe a veto is."""
    BLOCKER = "blocker"    # Must be resolved before the project can proceed
    WARNING = "warning"    # Recorded for audit but does not block progress


class EscalationLevel(str, Enum):
    """How far a veto conflict has been escalated."""
    ROLE_INTERNAL = "role_internal"   # Role resolves internally (self-review)
    CROSS_ROLE = "cross_role"         # Negotiation between roles
    USER_GATE = "user_gate"           # Escalated to human user for decision


# ═══════════════════════════════════════════════════════════════════════════
# Role Domain Mapping
# ═══════════════════════════════════════════════════════════════════════════

# Each role belongs to one domain.  Roles in the same domain share a
# common perspective and can negotiate among themselves.  Roles in
# different domains may need escalation.
ROLE_DOMAINS: dict[str, str] = {
    "security-engineer":     "security",
    "quality-engineer":      "quality",
    "delivery-manager":      "delivery",
    "developer":             "development",
    "system-architect":      "architecture",
    "module-architect":      "architecture",
    "product-manager":       "product",
    "project-manager":       "management",
    "release-engineer":      "release",
    "independent-reviewer":  "review",
}


# Pairs of *domains* whose conflict should stay at CROSS_ROLE instead of
# escalating to USER_GATE.  Architecture and Development are closely
# coupled — when they disagree it is a design tension, not a deadlock.
CROSS_ROLE_ONLY_DOMAIN_PAIRS: list[frozenset[str]] = [
    frozenset({"architecture", "development"}),
]


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class VetoRecord:
    """A single veto issued by a role against a task or gate.

    Attributes:
        veto_id:                 Unique identifier for this veto.
        role_id:                 Which role issued the veto.
        target_task_id:          The task being vetoed.
        target_gate_id:          The gate being vetoed (may be None).
        severity:                How severe the veto is.
        reason:                  Human-readable explanation of the veto.
        evidence_refs:           Paths to evidence files supporting the veto.
        suggested_remediation:   What the author believes would resolve it.
        recorded_at:             ISO-8601 timestamp.
    """
    veto_id: str
    role_id: str
    target_task_id: str
    target_gate_id: str | None
    severity: VetoSeverity
    reason: str
    evidence_refs: list[str] = field(default_factory=list)
    suggested_remediation: str = ""
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary (suitable for JSON)."""
        return {
            "veto_id": self.veto_id,
            "role_id": self.role_id,
            "target_task_id": self.target_task_id,
            "target_gate_id": self.target_gate_id,
            "severity": self.severity.value,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
            "suggested_remediation": self.suggested_remediation,
            "recorded_at": self.recorded_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> VetoRecord:
        """Deserialize from a plain dictionary."""
        severity_raw = data.get("severity", "blocker")
        severity = VetoSeverity(severity_raw) if isinstance(severity_raw, str) else severity_raw
        return cls(
            veto_id=data["veto_id"],
            role_id=data["role_id"],
            target_task_id=data["target_task_id"],
            target_gate_id=data.get("target_gate_id"),
            severity=severity,
            reason=data.get("reason", ""),
            evidence_refs=data.get("evidence_refs", []),
            suggested_remediation=data.get("suggested_remediation", ""),
            recorded_at=data.get("recorded_at", ""),
        )


@dataclass
class EscalationDecision:
    """The result of checking whether a veto conflict needs escalation.

    Attributes:
        level:                How far this conflict should be escalated.
        reason:               Why this level was chosen.
        involved_roles:       Which roles are involved in the conflict.
        veto_summary:         Human-readable summary of the veto situation.
        human_review_packet:  If escalated to USER_GATE, a detailed packet
                              for the human reviewer to make a decision.
                              None otherwise.
    """
    level: EscalationLevel
    reason: str
    involved_roles: list[str] = field(default_factory=list)
    veto_summary: str = ""
    human_review_packet: str | None = None


# ═══════════════════════════════════════════════════════════════════════════
# VetoEscalation Engine
# ═══════════════════════════════════════════════════════════════════════════

class VetoEscalation:
    """Veto Escalation Protocol — manages veto conflict resolution.

    Rules (in priority order):
      1. Security-engineer veto + any other veto  →  USER_GATE (immediate)
      2. Three or more *distinct* roles veto      →  USER_GATE (auto)
      3. Two roles, same domain                   →  CROSS_ROLE
      4. Two roles, different domains:
         - architecture + development             →  CROSS_ROLE (design tension)
         - all other cross-domain pairs           →  USER_GATE
      5. Single role (one or more vetoes)         →  ROLE_INTERNAL
    """

    def __init__(self) -> None:
        # task_id → list of VetoRecord (including resolved ones)
        self._vetoes: dict[str, list[VetoRecord]] = {}
        # veto_id → resolution string
        self._resolutions: dict[str, str] = {}

    # ── Recording ──────────────────────────────────────────────────────

    def record_veto(self, veto: VetoRecord) -> None:
        """Record a new veto in the ledger."""
        task_id = veto.target_task_id
        if task_id not in self._vetoes:
            self._vetoes[task_id] = []
        self._vetoes[task_id].append(veto)

    # ── Active Vetoes ──────────────────────────────────────────────────

    def get_active_vetoes(self, task_id: str) -> list[VetoRecord]:
        """Return all *unresolved* vetoes for a task.

        A veto is considered resolved when its veto_id appears in the
        resolutions dict.
        """
        all_vetoes = self._vetoes.get(task_id, [])
        return [v for v in all_vetoes if v.veto_id not in self._resolutions]

    def _get_all_vetoes(self, task_id: str) -> list[VetoRecord]:
        """Return all vetoes (including resolved) for a task."""
        return list(self._vetoes.get(task_id, []))

    # ── Resolution ─────────────────────────────────────────────────────

    def resolve_veto(self, veto_id: str, resolution: str) -> None:
        """Mark a veto as resolved with the given resolution note."""
        self._resolutions[veto_id] = resolution

    def is_resolved(self, veto_id: str) -> bool:
        """Check whether a specific veto has been resolved."""
        return veto_id in self._resolutions

    # ── Escalation Logic ───────────────────────────────────────────────

    def check_escalation(self, task_id: str) -> EscalationDecision:
        """Check whether the current task's veto situation needs escalation.

        Only *active* (unresolved) BLOCKER vetoes count toward escalation.
        WARNING-level vetoes are recorded but do not trigger escalation.
        """
        active = self.get_active_vetoes(task_id)
        # Only BLOCKER vetoes drive escalation decisions
        blockers = [v for v in active if v.severity == VetoSeverity.BLOCKER]

        if not blockers:
            return EscalationDecision(
                level=EscalationLevel.ROLE_INTERNAL,
                reason="No active BLOCKER vetoes — nothing to escalate.",
                involved_roles=[],
                veto_summary="No blocking vetoes active.",
                human_review_packet=None,
            )

        # Collect distinct roles and their domains
        distinct_roles: list[str] = list({v.role_id for v in blockers})
        {self._domain_for(v.role_id) for v in blockers}

        # ── Rule 1: Security engineer → immediate USER_GATE ──────────
        if "security-engineer" in distinct_roles and len(distinct_roles) >= 2:
            decision = self._build_decision(
                level=EscalationLevel.USER_GATE,
                reason=(
                    "Security-engineer veto combined with vetoes from other roles. "
                    "Security concerns take precedence — immediate user review required."
                ),
                involved_roles=distinct_roles,
                blockers=blockers,
            )
            decision.human_review_packet = self.generate_human_review_packet(
                task_id,
                escalation_level=decision.level,
                escalation_reason=decision.reason,
            )
            return decision

        # ── Rule 2: 3+ distinct roles → USER_GATE ─────────────────────
        if len(distinct_roles) >= 3:
            decision = self._build_decision(
                level=EscalationLevel.USER_GATE,
                reason=(
                    f"{len(distinct_roles)} distinct roles have issued vetoes "
                    f"({', '.join(distinct_roles)}). This many vetoes indicates "
                    "a systemic conflict that requires user intervention."
                ),
                involved_roles=distinct_roles,
                blockers=blockers,
            )
            decision.human_review_packet = self.generate_human_review_packet(
                task_id,
                escalation_level=decision.level,
                escalation_reason=decision.reason,
            )
            return decision

        # ── Rule 3 & 4: Two distinct roles ─────────────────────────────
        if len(distinct_roles) == 2:
            domain_a = self._domain_for(distinct_roles[0])
            domain_b = self._domain_for(distinct_roles[1])

            # Same domain → CROSS_ROLE (negotiate within the domain)
            if domain_a == domain_b:
                return self._build_decision(
                    level=EscalationLevel.CROSS_ROLE,
                    reason=(
                        f"Both vetoes come from the '{domain_a}' domain "
                        f"({distinct_roles[0]}, {distinct_roles[1]}). "
                        "Roles should negotiate and resolve internally."
                    ),
                    involved_roles=distinct_roles,
                    blockers=blockers,
                )

            # Different domains — check special-case pairs
            domain_pair = frozenset({domain_a, domain_b})
            if domain_pair in CROSS_ROLE_ONLY_DOMAIN_PAIRS:
                return self._build_decision(
                    level=EscalationLevel.CROSS_ROLE,
                    reason=(
                        f"Vetoes from '{domain_a}' and '{domain_b}' domains "
                        f"({distinct_roles[0]}, {distinct_roles[1]}). "
                        "These domains are closely coupled — cross-role "
                        "negotiation is the appropriate forum."
                    ),
                    involved_roles=distinct_roles,
                    blockers=blockers,
                )

            # All other cross-domain pairs → USER_GATE
            decision = self._build_decision(
                level=EscalationLevel.USER_GATE,
                reason=(
                    f"Cross-domain veto conflict between '{domain_a}' and "
                    f"'{domain_b}' domains ({distinct_roles[0]}, "
                    f"{distinct_roles[1]}). Requires user decision."
                ),
                involved_roles=distinct_roles,
                blockers=blockers,
            )
            decision.human_review_packet = self.generate_human_review_packet(
                task_id,
                escalation_level=decision.level,
                escalation_reason=decision.reason,
            )
            return decision

        # ── Rule 5: Single role → ROLE_INTERNAL ────────────────────────
        return self._build_decision(
            level=EscalationLevel.ROLE_INTERNAL,
            reason=(
                f"Only '{distinct_roles[0]}' has issued vetoes "
                f"({len(blockers)} veto(es)). The role should resolve internally."
            ),
            involved_roles=distinct_roles,
            blockers=blockers,
        )

    # ── Human Review Packet ────────────────────────────────────────────

    def generate_human_review_packet(self, task_id: str,
                                      escalation_level: EscalationLevel | None = None,
                                      escalation_reason: str = "") -> str:
        """Generate a human-readable summary of the veto conflict.

        Produces a markdown-formatted packet suitable for presenting
        to a human decision-maker at the USER_GATE.

        Args:
            task_id: The task whose vetoes to summarise.
            escalation_level: Pre-computed escalation level (avoids recursion).
            escalation_reason: Pre-computed escalation reason.
        """
        blockers = [v for v in self.get_active_vetoes(task_id)
                    if v.severity == VetoSeverity.BLOCKER]
        warnings = [v for v in self.get_active_vetoes(task_id)
                    if v.severity == VetoSeverity.WARNING]

        distinct_roles = sorted({v.role_id for v in blockers})

        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("HUMAN REVIEW PACKET — Veto Escalation")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Task ID:       {task_id}")
        lines.append(f"Generated at:  {datetime.now(timezone.utc).isoformat()}")
        if escalation_level:
            lines.append(f"Escalation:    {escalation_level.value}")
        lines.append(f"Vetoing Roles: {', '.join(distinct_roles) if distinct_roles else '(none)'}")
        lines.append("")

        # Decision summary
        lines.append("─" * 60)
        lines.append("DECISION REQUIRED")
        lines.append("─" * 60)
        lines.append("")
        if escalation_reason:
            lines.append(f"{escalation_reason}")
        else:
            lines.append("Multiple roles have issued BLOCKER vetoes — human decision required.")
        lines.append("")

        # Blocking vetoes
        lines.append("─" * 60)
        lines.append(f"BLOCKER VETOES ({len(blockers)})")
        lines.append("─" * 60)
        lines.append("")

        if not blockers:
            lines.append("(No blocking vetoes active)")
            lines.append("")
        else:
            for i, v in enumerate(blockers, 1):
                lines.append(f"[{i}] Veto: {v.veto_id}")
                lines.append(f"    Role:       {v.role_id}")
                lines.append(f"    Severity:   {v.severity.value}")
                lines.append(f"    Reason:     {v.reason}")
                if v.target_gate_id:
                    lines.append(f"    Gate:       {v.target_gate_id}")
                if v.evidence_refs:
                    lines.append(f"    Evidence:   {', '.join(v.evidence_refs)}")
                if v.suggested_remediation:
                    lines.append(f"    Remediation: {v.suggested_remediation}")
                lines.append(f"    Recorded:   {v.recorded_at}")
                lines.append("")

        # Warnings
        if warnings:
            lines.append("─" * 60)
            lines.append(f"WARNINGS ({len(warnings)})")
            lines.append("─" * 60)
            lines.append("")
            for i, w in enumerate(warnings, 1):
                lines.append(f"[{i}] {w.role_id}: {w.reason}")
                lines.append("")

        # Resolution guidance
        lines.append("─" * 60)
        lines.append("SUGGESTED RESOLUTIONS")
        lines.append("─" * 60)
        lines.append("")
        for i, v in enumerate(blockers, 1):
            if v.suggested_remediation:
                lines.append(f"  [{i}] {v.role_id}: {v.suggested_remediation}")
        if not any(v.suggested_remediation for v in blockers):
            lines.append("  (No remediation suggestions provided by vetoing roles)")
        lines.append("")

        lines.append("=" * 60)
        lines.append("END OF HUMAN REVIEW PACKET")
        lines.append("=" * 60)

        return "\n".join(lines)

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _domain_for(role_id: str) -> str:
        """Return the domain for a given role ID.

        Returns 'unknown' if the role is not recognized, so that
        unrecognised roles still participate in escalation logic
        without raising errors.
        """
        return ROLE_DOMAINS.get(role_id, "unknown")

    def _build_decision(
        self,
        level: EscalationLevel,
        reason: str,
        involved_roles: list[str],
        blockers: list[VetoRecord],
    ) -> EscalationDecision:
        """Construct an EscalationDecision (without review packet — caller attaches it)."""
        summary_lines = [f"Escalation level: {level.value}"]
        for v in blockers:
            summary_lines.append(f"  - [{v.role_id}] {v.reason}")

        return EscalationDecision(
            level=level,
            reason=reason,
            involved_roles=sorted(involved_roles),
            veto_summary="\n".join(summary_lines),
            human_review_packet=None,
        )
