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
    check_role_isolation,
    check_self_review,
    phase_needs_user_gate,
    resolve_gate_status,
)
# Unified EnforcementLevel (v3.5) — single source of truth in enforcement.py
from loop_core.enforcement import EnforcementLevel

logger = logging.getLogger(__name__)

# ── Sentinel values for corrupted governance state ─────────────────────
# When governance YAML files are missing or unparseable, the system MUST
# FAIL CLOSED — not silently return empty defaults that bypass all checks.
# These sentinels propagate through the read methods and are detected by
# _governance_state_healthy() before any enforcement decision is made.
_CORRUPT_SENTINEL = object()  # single shared sentinel for all three files


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

    # ── Role domain separation (v3.3 — from Qoder enforcement_hub.ts) ──
    DEVELOPMENT_ROLES = frozenset({
        "developer", "system-architect", "module-architect",
    })
    QUALITY_ROLES = frozenset({
        "quality-engineer", "security-engineer", "independent-reviewer",
    })
    GOVERNANCE_ROLES = frozenset({
        "product-manager", "project-manager", "delivery-manager",
        "release-engineer", "main-thread",
    })

    @classmethod
    def check_cross_domain_review(cls, developer_role: str, reviewer_role: str) -> bool:
        """Ensure reviewer is from a different domain than developer (Qoder pattern)."""
        dev_domains = []
        if developer_role in cls.DEVELOPMENT_ROLES: dev_domains.append("development")
        if developer_role in cls.QUALITY_ROLES: dev_domains.append("quality")
        if developer_role in cls.GOVERNANCE_ROLES: dev_domains.append("governance")

        rev_domains = []
        if reviewer_role in cls.DEVELOPMENT_ROLES: rev_domains.append("development")
        if reviewer_role in cls.QUALITY_ROLES: rev_domains.append("quality")
        if reviewer_role in cls.GOVERNANCE_ROLES: rev_domains.append("governance")

        # At least one domain must differ
        return len(set(dev_domains) & set(rev_domains)) < len(dev_domains)

    def __init__(self, project_root: Path | str):
        self._root = Path(project_root)
        self._hc = HardConstraints()
        self._state_cache: dict[str, Any] | None = None
        self._gates_cache: list[dict] | None = None
        self._tasks_cache: list[dict] | None = None
        self._state_error: str | None = None
        self._gates_error: str | None = None
        self._tasks_error: str | None = None

    @property
    def _governance_state_healthy(self) -> bool:
        """True iff governance state is intact OR project is not governed at all.

        If .ai/ directory doesn't exist, this is not a governance project
        and enforcement is skipped (healthy).  If .ai/ exists but any core
        YAML file is missing or unparseable, FAIL CLOSED.
        """
        ai_dir = self._root / ".ai"
        if not ai_dir.is_dir():
            return True  # Not a governance project — nothing to enforce

        # Force read to populate error flags
        self._read_state()
        self._read_gates()
        self._read_tasks()
        return not (self._state_error or self._gates_error or self._tasks_error)

    def _governance_error_reason(self) -> str:
        """Human-readable summary of governance file errors."""
        parts = []
        if self._state_error:
            parts.append(f"state.yaml: {self._state_error}")
        if self._gates_error:
            parts.append(f"gates.yaml: {self._gates_error}")
        if self._tasks_error:
            parts.append(f"task_graph.yaml: {self._tasks_error}")
        return "; ".join(parts) if parts else "unknown governance error"

    @property
    def root(self) -> Path:
        return self._root

    def _read_state(self) -> dict[str, Any]:
        if self._state_cache is not None:
            return self._state_cache
        sp = self._root / ".ai" / "state.yaml"
        if not sp.exists():
            self._state_error = "file not found"
            self._state_cache = {}
            return self._state_cache
        try:
            import yaml
            with open(sp, "r", encoding="utf-8") as f:
                self._state_cache = yaml.safe_load(f) or {}
            self._state_error = None
        except Exception as e:
            self._state_error = f"parse error: {e}"
            self._state_cache = {}
        return self._state_cache

    def _read_gates(self) -> list[dict]:
        if self._gates_cache is not None:
            return self._gates_cache
        gp = self._root / ".ai" / "gates.yaml"
        if not gp.exists():
            self._gates_error = "file not found"
            self._gates_cache = []
            return self._gates_cache
        try:
            import yaml
            with open(gp, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self._gates_cache = data.get("gates", []) or []
            self._gates_error = None
        except Exception as e:
            self._gates_error = f"parse error: {e}"
            self._gates_cache = []
        return self._gates_cache

    def _read_tasks(self) -> list[dict]:
        if self._tasks_cache is not None:
            return self._tasks_cache
        tp = self._root / ".ai" / "task_graph.yaml"
        if not tp.exists():
            self._tasks_error = "file not found"
            self._tasks_cache = []
            return self._tasks_cache
        try:
            import yaml
            with open(tp, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self._tasks_cache = data.get("tasks", []) or []
            self._tasks_error = None
        except Exception as e:
            self._tasks_error = f"parse error: {e}"
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

    def _has_approved_user_gate(self, phase: Phase) -> bool:
        """Return whether the target phase has an explicit user-approved gate.

        Cross-validates two independent evidence sources:
        1. Heuristic: gate_type/approval_actor/approval_source fields in gates.yaml
        2. Structural: state.yaml current_gate_id points to an approved user gate
           matching this phase.
        """
        phase_value = phase.value.lower()
        phase_slug = phase_value.split("-", 1)[-1] if "-" in phase_value else phase_value

        # ── Evidence source 1: heuristic gate scan ──
        heuristic_match = False
        for gate in self._read_gates():
            if not isinstance(gate, dict) or gate.get("status") != "approved":
                continue
            gate_phase = str(gate.get("phase", "")).lower()
            gate_type = str(gate.get("gate_type", "")).lower()
            approval_actor = str(gate.get("approval_actor", "")).lower()
            approval_source = str(gate.get("approval_source", "")).lower()
            phase_matches = (
                gate_phase in {phase_value, phase_slug}
                or phase_slug in gate_type
                or phase_value in gate_type
            )
            explicit_user = (
                approval_actor == "user"
                or approval_source == "explicit_user_message"
                or gate_type.startswith("user-")
            )
            if phase_matches and explicit_user:
                heuristic_match = True
                break

        # ── Evidence source 2: cross-reference with state.yaml ──
        state = self._read_state()
        current_gate_id = state.get("current_gate_id")
        current_gate_id = None if current_gate_id in (None, "", "null") else current_gate_id
        structural_match = False
        if current_gate_id:
            cgi = str(current_gate_id)
            for gate in self._read_gates():
                if not isinstance(gate, dict) or gate.get("status") != "approved":
                    continue
                if str(gate.get("id", "")) != cgi:
                    continue
                gate_type = str(gate.get("gate_type", "")).lower()
                gate_phase = str(gate.get("phase", "")).lower()
                approval_actor = str(gate.get("approval_actor", "")).lower()
                approval_source = str(gate.get("approval_source", "")).lower()
                phase_matches = (
                    gate_phase in {phase_value, phase_slug}
                    or phase_slug in gate_type
                    or phase_value in gate_type
                )
                explicit_user = (
                    approval_actor == "user"
                    or approval_source == "explicit_user_message"
                    or gate_type.startswith("user-")
                )
                if phase_matches and explicit_user:
                    structural_match = True
                break

        return heuristic_match and structural_match

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
            "root": self._root,
            "scan_paths": [self._root],
            # T-0085 (Fix 3): check_all gates C10/C11 behind context["task_id"];
            # without it they returned early in every integration path. Wire
            # the active task id from state so C10 (contract tests) and C11
            # (file limit) actually run through should_allow_write /
            # should_allow_phase_advance. Both are SOFT (WARNING) by default.
            "task_id": self._read_state().get("current_task_id"),
            # C11 file limit: project-tunable via state.yaml (max_files key);
            # default 10. Coerced to int with a fail-safe default so a corrupt
            # value never disables the check (a bad value keeps the default).
            "max_files": self._state_max_files(),
        }
        if target_path:
            ctx["target_path"] = target_path
        if allowed_paths is not None:
            ctx["allowed_paths"] = allowed_paths
        return ctx

    def _state_max_files(self) -> int:
        """C11 max_files from state.yaml, fail-safe to the default (10).

        A non-numeric or non-positive value keeps the default — a corrupt
        value must never silently disable the file-limit check.
        """
        raw = self._read_state().get("max_files", 10)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return 10
        return value if value > 0 else 10

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
        """Check whether a file write should be allowed (C4+C3+C7+phase).

        FAILS CLOSED: if any governance file (.ai/state.yaml, .ai/gates.yaml,
        .ai/task_graph.yaml) is missing or unparseable, all writes are denied.
        """
        # ── Fail-closed: governance state integrity check ──────────────
        if not self._governance_state_healthy:
            return EnforcementDecision(
                allowed=False,
                reason=f"Governance state corrupted — FAIL CLOSED: {self._governance_error_reason()}",
                blocker_count=1,
            )
        # ── Normal enforcement ─────────────────────────────────────────
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
        """Check whether advancing to a new phase should be allowed.

        FAILS CLOSED: if any governance file is missing or unparseable,
        phase advance is denied.
        """
        # ── Fail-closed: governance state integrity check ──────────────
        if not self._governance_state_healthy:
            return EnforcementDecision(
                allowed=False,
                reason=f"Governance state corrupted — FAIL CLOSED: {self._governance_error_reason()}",
                blocker_count=1,
            )
        # ── Normal enforcement ─────────────────────────────────────────
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
        # Build context early — used by compile check and check_all below
        ctx = self._build_context(target_phase=target_phase)
        qr = ctx.get("quality_results", {})
        # Check compile evidence from quality results
        compile_ok = qr.get("compile", "") == "PASS"
        # T-0085 C5 hub fix: deterministic verification (tests/lint/build all
        # PASS) for the S6 phase-constraint 'C5-no-verification'. Mirrors the
        # check_c5_verification kernel semantics exactly (hard_constraints.py):
        # ALL of test/lint/build must equal "PASS" — any missing or non-PASS
        # evidence fails closed (verification_passed=False) and blocks.
        verification_passed = all(
            qr.get(check_name) == "PASS"
            for check_name in ("test", "lint", "build")
        )

        # Determine whether user gate is required and satisfied for this phase
        user_gate_approved = None  # None = not applicable
        if phase_needs_user_gate(target_phase):
            user_gate_approved = self._has_approved_user_gate(target_phase)

        pc = check_phase_constraints(target_phase, approved, task_has_active=ha,
                                      compile_passed=compile_ok,
                                      verification_passed=verification_passed,
                                      user_gate_approved=user_gate_approved)
        if not pc.allowed:
            for err in pc.errors:
                violations.append(ConstraintViolation(
                    constraint_id=ConstraintID.C7_BLOCKER_EXISTS,
                    severity=Severity.BLOCKER, message=err,
                    detail="Phase constraint not satisfied",
                    remediation="Satisfy required constraints.",
                ))
        # C9: Import validity check — enforced on S4→S5 transition.
        # T-0085 conditional-GO fix (C9 dedup): the explicit branch below runs
        # the kernel check, but check_all ALSO runs C9 whenever
        # context.current_phase is S4/S5 (hard_constraints.py check_all) — so
        # the same undeclared import would otherwise be reported TWICE and
        # blocker_count doubled (over-blocking direction). The explicit branch
        # is the single source of C9 for S4→S5; C9 is dropped from the
        # check_all aggregation here so each undeclared import produces exactly
        # ONE C9 violation.
        ran_explicit_c9 = (
            cp == Phase.S4_IMPLEMENTATION and target_phase == Phase.S5_QUALITY
        )
        if ran_explicit_c9:
            violations.extend(self._hc.check_c9_import_validity(
                root=self._root,
                scan_paths=[self._root],
            ))

        check_all_violations = self._hc.check_all(ctx).violations
        if ran_explicit_c9:
            check_all_violations = [
                v for v in check_all_violations
                if v.constraint_id != ConstraintID.C9_IMPORT_NOT_DECLARED
            ]
        violations.extend(check_all_violations)
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
    """Quick check — are we clear to operate?

    FAILS CLOSED: if any governance file is missing or unparseable,
    operation is denied.
    """
    hub = EnforcementHub(project_root)

    # ── Fail-closed: governance state integrity check ──────────────────
    if not hub._governance_state_healthy:
        return EnforcementDecision(
            allowed=False,
            reason=f"Governance state corrupted — FAIL CLOSED: {hub._governance_error_reason()}",
            blocker_count=1,
        )
    # ── Normal checks ──────────────────────────────────────────────────
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
