"""
EnforcementHub — Bridge between Hook system and Loop Core governance state.

This module eliminates "model self-discipline reliance": hooks call these
methods to make enforcement decisions based on actual governance state
(gate status, role verdicts, evidence freshness), NOT on whether the
main-thread "chooses" to check and respect constraints.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from loop_core.hard_constraints import (
    ConstraintID,
    ConstraintViolation,
    EvidenceEnvelope,
    HardConstraints,
    Severity,
)
from loop_core.state_machine import (
    GateStatus,
    Phase,
    can_approve_gate,
    can_enter_phase,
    can_transition_phase,
    check_phase_constraints,
    check_self_review,
    resolve_gate_status,
)

logger = logging.getLogger(__name__)


class EnforcementLevel(str, Enum):
    """What level of enforcement this adapter/host provides."""
    HARD = "HARD"
    PARTIAL = "PARTIAL"
    ADVISORY = "ADVISORY"


@dataclass
class EnforcementDecision:
    """Result of an enforcement check — what the hook should do."""
    allowed: bool
    reason: str
    enforcement_level: EnforcementLevel = EnforcementLevel.HARD
    violations: list[ConstraintViolation] = field(default_factory=list)
    blocker_count: int = 0
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_hook_output(self) -> dict[str, Any]:
        """Convert to hook-compatible JSON output."""
        return {
            "permissionDecision": "allow" if self.allowed else "deny",
            "permissionDecisionReason": self.reason,
            "enforcement_level": self.enforcement_level.value,
            "blocker_count": self.blocker_count,
            "violations": [
                {"constraint_id": v.constraint_id.value, "severity": v.severity.value,
                 "message": v.message, "remediation": v.remediation}
                for v in self.violations if v.severity == Severity.BLOCKER
            ],
        }


class EnforcementHub:
    """Hook-callable enforcement decisions — does NOT rely on main-thread.

    Each method independently reads governance state from .ai/ files
    and runs constraint checks. Designed for import by hook scripts.
    """

    def __init__(self, project_root: Path | str):
        self._root = Path(project_root)
        self._hc = HardConstraints()
        self._state_cache: dict[str, Any] | None = None
        self._gates_cache: list[dict] | None = None
        self._tasks_cache: list[dict] | None = None

    @property
    def root(self) -> Path:
        return self._root

    def _read_state(self) -> dict[str, Any]:
        if self._state_cache is not None:
            return self._state_cache
        sp = self._root / ".ai" / "state.yaml"
        if not sp.exists():
            return {}
        try:
            import yaml
            with open(sp, "r", encoding="utf-8") as f:
                self._state_cache = yaml.safe_load(f) or {}
        except Exception:
            self._state_cache = {}
            for line in sp.read_text(encoding="utf-8").splitlines():
                if ":" in line and not line.strip().startswith("#"):
                    k, _, v = line.partition(":")
                    self._state_cache[k.strip()] = v.strip().strip('"').strip("'")
        return self._state_cache

    def _read_gates(self) -> list[dict]:
        if self._gates_cache is not None:
            return self._gates_cache
        gp = self._root / ".ai" / "gates.yaml"
        if not gp.exists():
            self._gates_cache = []
            return self._gates_cache
        try:
            import yaml
            with open(gp, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self._gates_cache = data.get("gates", []) or []
        except Exception:
            self._gates_cache = []
        return self._gates_cache

    def _read_tasks(self) -> list[dict]:
        if self._tasks_cache is not None:
            return self._tasks_cache
        tp = self._root / ".ai" / "task_graph.yaml"
        if not tp.exists():
            self._tasks_cache = []
            return self._tasks_cache
        try:
            import yaml
            with open(tp, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self._tasks_cache = data.get("tasks", []) or []
        except Exception:
            self._tasks_cache = []
        return self._tasks_cache

    def _get_current_phase(self) -> Phase | None:
        ps = self._read_state().get("current_phase")
        if not ps:
            return None
        try:
            return Phase(ps)
        except ValueError:
            return None

    def _get_phase_gates(self) -> dict:
        gates = self._read_gates()
        result: dict = {}
        gt_map = {
            "requirements": Phase.S1_REQUIREMENTS, "architecture": Phase.S2_ARCHITECTURE,
            "interface": Phase.S3_INTERFACE, "implementation": Phase.S4_IMPLEMENTATION,
            "quality": Phase.S5_QUALITY, "delivery": Phase.S6_DELIVERY,
            "integration": Phase.S7_INTEGRATION, "functional_test": Phase.S8_FUNCTIONAL_TEST,
            "fix_optimize": Phase.S9_FIX_OPTIMIZE, "performance": Phase.S10_PERFORMANCE,
            "maintenance": Phase.S11_MAINTENANCE,
        }
        for g in gates:
            if not isinstance(g, dict):
                continue
            gt = str(g.get("gate_type", "")).lower()
            gs = str(g.get("status", ""))
            if gt in gt_map and gs:
                phase = gt_map[gt]
                existing = result.get(phase)
                if existing is None or gs == GateStatus.BLOCKED.value:
                    result[phase] = gs
        return result

    def _get_approved_gate_ids(self) -> set[str]:
        return {g["id"] for g in self._read_gates()
                if isinstance(g, dict) and g.get("status") == "approved" and g.get("id")}

    @staticmethod
    def _get_roles_for_phase(phase: Phase | None) -> list[str]:
        """Get required roles for a phase."""
        if phase is None:
            return []
        return {
            Phase.S0_INIT: ["product-manager", "project-manager"],
            Phase.S1_REQUIREMENTS: ["product-manager", "system-architect", "quality-engineer"],
            Phase.S2_ARCHITECTURE: ["system-architect", "module-architect", "independent-reviewer"],
            Phase.S3_INTERFACE: ["module-architect", "developer"],
            Phase.S4_IMPLEMENTATION: ["developer", "independent-reviewer", "quality-engineer"],
            Phase.S5_QUALITY: ["quality-engineer", "security-engineer"],
            Phase.S6_DELIVERY: ["delivery-manager", "release-engineer"],
            Phase.S7_INTEGRATION: ["developer", "quality-engineer"],
            Phase.S8_FUNCTIONAL_TEST: ["quality-engineer", "product-manager"],
            Phase.S9_FIX_OPTIMIZE: ["developer", "independent-reviewer", "quality-engineer"],
            Phase.S10_PERFORMANCE: ["quality-engineer", "system-architect"],
            Phase.S11_MAINTENANCE: ["product-manager"],
        }.get(phase, [])

    def _build_context(self, target_path=None, allowed_paths=None, target_phase=None) -> dict:
        cp = self._get_current_phase()
        pg = self._get_phase_gates()
        tasks = self._read_tasks()
        gd = {g["id"]: g["status"] for g in self._read_gates()
              if isinstance(g, dict) and g.get("id") and g.get("status")}
        ctx: dict[str, Any] = {
            "current_phase": cp if cp else target_phase,
            "target_phase": target_phase if target_phase else cp,
            "phase_gates": pg, "gates": gd, "tasks": tasks,
            "quality_results": self._load_quality_results(),
            "review_status": self._load_review_status(),
            "evidence_list": self._load_evidence_envelopes(),
            "current_hashes": self._compute_evidence_hashes(),
        }
        if target_path:
            ctx["target_path"] = target_path
        if allowed_paths is not None:
            ctx["allowed_paths"] = allowed_paths
        return ctx

    def _load_quality_results(self) -> dict[str, Any]:
        ed = self._root / ".ai" / "evidence"
        results: dict[str, Any] = {}
        if not ed.exists():
            return results
        for td in ed.iterdir():
            if not td.is_dir():
                continue
            qp = td / "quality" / "quality_report.json"
            if qp.exists():
                try:
                    data = json.loads(qp.read_text(encoding="utf-8"))
                    for c in data.get("checks", []):
                        if c.get("name") and c.get("status"):
                            results[c["name"]] = c["status"].upper()
                except (json.JSONDecodeError, OSError):
                    continue
        return results

    def _load_review_status(self) -> dict[str, Any]:
        ed = self._root / ".ai" / "evidence"
        status: dict[str, Any] = {}
        if not ed.exists():
            return status
        for td in ed.iterdir():
            if not td.is_dir():
                continue
            for f in td.iterdir():
                if not f.suffix == ".json":
                    continue
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if data.get("role") == "independent-reviewer":
                        status["independent-reviewer"] = data.get("verdict", "UNKNOWN")
                        status["findings"] = data.get("findings", [])
                        break
                except (json.JSONDecodeError, OSError):
                    continue
        return status

    def _load_evidence_envelopes(self) -> list[EvidenceEnvelope]:
        envelopes: list[EvidenceEnvelope] = []
        ed = self._root / ".ai" / "evidence"
        if not ed.exists():
            return envelopes
        for td in ed.iterdir():
            if not td.is_dir():
                continue
            ep = td / "evidence_envelope.json"
            if not ep.exists():
                continue
            try:
                data = json.loads(ep.read_text(encoding="utf-8"))
                envelopes.append(EvidenceEnvelope(
                    evidence_id=data.get("evidence_id", td.name),
                    content_hash=data.get("content_hash", ""),
                    created_at=data.get("created_at", ""),
                    expires_at=data.get("expires_at"),
                    phase=Phase(data["phase"]) if data.get("phase") else None,
                ))
            except (json.JSONDecodeError, OSError, ValueError):
                continue
        return envelopes

    def _compute_evidence_hashes(self) -> dict[str, str]:
        hashes: dict[str, str] = {}
        ed = self._root / ".ai" / "evidence"
        if not ed.exists():
            return hashes
        for td in ed.iterdir():
            if not td.is_dir():
                continue
            ep = td / "evidence_envelope.json"
            if ep.exists():
                try:
                    hashes[td.name] = hashlib.sha256(ep.read_bytes()).hexdigest()
                except OSError:
                    continue
        return hashes

    # ═══════════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════════

    def should_allow_write(self, target_path: str,
                           allowed_paths: list[str] | None = None) -> EnforcementDecision:
        """Check whether a file write should be allowed (C4+C3+C7+phase)."""
        ctx = self._build_context(target_path=target_path, allowed_paths=allowed_paths or [])
        result = self._hc.check_all(ctx)
        violations = list(result.violations)
        cp = self._get_current_phase()
        if cp is not None:
            approved = self._get_approved_gate_ids()
            tasks = self._read_tasks()
            ha = any(t.get("status") in ("active", "in_progress") for t in tasks)
            pr = check_phase_constraints(cp, approved, task_has_active=ha)
            if not pr.allowed:
                for err in pr.errors:
                    violations.append(ConstraintViolation(
                        constraint_id=ConstraintID.C7_BLOCKER_EXISTS,
                        severity=Severity.BLOCKER, message=err,
                        detail="Phase constraint violation",
                        remediation="Satisfy phase constraints before writing.",
                    ))
        bc = sum(1 for v in violations if v.severity == Severity.BLOCKER)
        if bc > 0:
            msgs = [v.message for v in violations if v.severity == Severity.BLOCKER]
            return EnforcementDecision(allowed=False, reason=f"Write blocked: {'; '.join(msgs)}",
                                       violations=violations, blocker_count=bc)
        return EnforcementDecision(allowed=True, reason="All constraints satisfied",
                                   violations=violations)

    def should_allow_phase_advance(self, target_phase: Phase | str) -> EnforcementDecision:
        """Check whether advancing to a new phase should be allowed."""
        if isinstance(target_phase, str):
            try:
                target_phase = Phase(target_phase)
            except ValueError:
                return EnforcementDecision(allowed=False, reason=f"Invalid: {target_phase}",
                                           blocker_count=1)
        cp = self._get_current_phase()
        violations: list[ConstraintViolation] = []
        if cp is not None:
            tr = can_transition_phase(cp, target_phase)
            if not tr.allowed:
                for err in tr.errors:
                    violations.append(ConstraintViolation(
                        constraint_id=ConstraintID.C7_BLOCKER_EXISTS,
                        severity=Severity.BLOCKER, message=err,
                        detail=f"Cannot transition {cp.value} → {target_phase.value}",
                        remediation="Follow defined phase transition graph.",
                    ))
        gates = self._read_gates()
        cgi = self._read_state().get("current_gate_id")
        pgs = resolve_gate_status(cgi, gates) if cgi else None
        tasks = self._read_tasks()
        hb = any(t.get("status") == "blocked" for t in tasks)
        entry = can_enter_phase(target_phase, pgs, hb)
        if not entry.allowed:
            for err in entry.errors:
                violations.append(ConstraintViolation(
                    constraint_id=ConstraintID.C7_BLOCKER_EXISTS,
                    severity=Severity.BLOCKER, message=err,
                    detail="Phase entry precondition not satisfied",
                    remediation="Resolve blockers and approve previous gate.",
                ))
        approved = self._get_approved_gate_ids()
        ha = any(t.get("status") in ("active", "in_progress") for t in tasks)
        pc = check_phase_constraints(target_phase, approved, task_has_active=ha)
        if not pc.allowed:
            for err in pc.errors:
                violations.append(ConstraintViolation(
                    constraint_id=ConstraintID.C7_BLOCKER_EXISTS,
                    severity=Severity.BLOCKER, message=err,
                    detail="Phase constraint not satisfied",
                    remediation="Satisfy required constraints.",
                ))
        ctx = self._build_context(target_phase=target_phase)
        violations.extend(self._hc.check_all(ctx).violations)
        bc = sum(1 for v in violations if v.severity == Severity.BLOCKER)
        if bc > 0:
            msgs = [v.message for v in violations if v.severity == Severity.BLOCKER]
            return EnforcementDecision(allowed=False,
                                       reason=f"Phase advance blocked: {'; '.join(msgs)}",
                                       violations=violations, blocker_count=bc)
        return EnforcementDecision(allowed=True,
                                   reason=f"Phase advance to {target_phase.value} allowed",
                                   violations=violations)

    def check_role_isolation_enforcement(self, developer_id=None,
                                         reviewer_id=None) -> EnforcementDecision:
        """Hard-check role isolation — BLOCK if developer == reviewer."""
        violations: list[ConstraintViolation] = []
        sr = check_self_review(developer_id, reviewer_id)
        if not sr.allowed:
            violations.append(ConstraintViolation(
                constraint_id=ConstraintID.C6_NO_INDEPENDENT_REVIEW,
                severity=Severity.BLOCKER,
                message=f"SELF_REVIEW_VIOLATION: {sr.errors[0]}",
                detail=f"Developer ({developer_id}) == Reviewer ({reviewer_id})",
                remediation="Assign a different agent as independent reviewer.",
            ))
        bc = len([v for v in violations if v.severity == Severity.BLOCKER])
        if bc > 0:
            return EnforcementDecision(allowed=False,
                                       reason="Role isolation violation: developer == reviewer",
                                       violations=violations, blocker_count=bc)
        return EnforcementDecision(allowed=True, reason="Role isolation satisfied",
                                   violations=violations)

    def check_evidence_freshness_enforcement(self) -> EnforcementDecision:
        """Check whether all evidence for the current phase is fresh."""
        el = self._load_evidence_envelopes()
        ch = self._compute_evidence_hashes()
        violations = self._hc.check_c8_evidence_freshness(el, ch)
        bc = sum(1 for v in violations if v.severity == Severity.BLOCKER)
        if bc > 0:
            sids = [v.message.split("'")[1] if "'" in v.message else "?"
                    for v in violations if v.severity == Severity.BLOCKER]
            return EnforcementDecision(allowed=False,
                                       reason=f"Stale evidence: {sids}",
                                       violations=list(violations), blocker_count=bc)
        return EnforcementDecision(allowed=True, reason="All evidence fresh",
                                   violations=list(violations))

    def get_enforcement_level(self) -> EnforcementLevel:
        return EnforcementLevel.HARD


def quick_check(project_root: Path | str) -> EnforcementDecision:
    """Quick check — are we clear to operate?"""
    hub = EnforcementHub(project_root)
    violations: list[ConstraintViolation] = []
    for g in hub._read_gates():
        if isinstance(g, dict) and g.get("status") == "blocked":
            violations.append(ConstraintViolation(
                constraint_id=ConstraintID.C7_BLOCKER_EXISTS, severity=Severity.BLOCKER,
                message=f"Blocked gate: {g.get('id', 'unknown')}",
                detail="Cannot proceed while gates are blocked",
                remediation=f"Resolve blockers for {g.get('id', 'unknown')}.",
            ))
    bc = sum(1 for v in violations if v.severity == Severity.BLOCKER)
    if bc > 0:
        return EnforcementDecision(allowed=False, reason=f"Blocked: {bc} blocker(s)",
                                   violations=violations, blocker_count=bc)
    return EnforcementDecision(allowed=True, reason="All checks passed",
                               violations=violations)
