# WARNING: This module has diverged from codex_loop/core/hard_constraints.py
# codex_loop/core/hard_constraints.py is the authoritative version for Codex.
# This copy is kept for zcode backward compatibility only.
"""
Loop Core Hard Constraints — Machine-enforced control gates.

These are NOT suggestions. At STRONG enforcement level, any BLOCKER
violation must deny the operation. At MEDIUM/ADVISORY levels, they
become warnings but are still reported.

The 8 hard constraints form the "non-bypassable control kernel" of
the Loop Engine — the minimum set of checks that every host adapter
must implement to claim Loop compliance.
"""
from __future__ import annotations

import logging
import os
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Optional, TypedDict

from loop_core.state_machine import Phase, GateStatus, TaskStatus

logger = logging.getLogger(__name__)


class ConstraintContext(TypedDict, total=False):
    """Typed context for HardConstraints.check_all()."""
    current_phase: Phase | None
    target_phase: Phase | None
    phase_gates: dict[str, str]
    gates: dict[str, str]
    tasks: list[dict[str, Any]]
    target_path: str
    allowed_paths: list[str]
    quality_results: dict[str, Any]
    review_status: dict[str, Any]
    evidence_list: list[EvidenceEnvelope]
    current_hashes: dict[str, str]


class ConstraintID(str, Enum):
    """Unique identifier for each hard constraint."""
    C1_NO_REQUIREMENTS = "C1-no-requirements"
    C2_NO_ARCHITECTURE = "C2-no-architecture"
    C3_NO_TASK_PACKAGE = "C3-no-task-package"
    C4_PATH_OUT_OF_SCOPE = "C4-path-out-of-scope"
    C5_NO_VERIFICATION = "C5-no-verification"
    C6_NO_INDEPENDENT_REVIEW = "C6-no-independent-review"
    C7_BLOCKER_EXISTS = "C7-blocker-exists"
    C8_STALE_EVIDENCE = "C8-stale-evidence"


class Severity(str, Enum):
    """Severity level of a constraint violation."""
    BLOCKER = "blocker"     # Must deny the operation
    WARNING = "warning"     # Advisory, does not block


@dataclass
class ConstraintViolation:
    """A single constraint violation with remediation guidance."""
    constraint_id: ConstraintID
    severity: Severity
    message: str
    detail: str
    remediation: str


@dataclass
class ConstraintCheckResult:
    """Aggregate result of checking all hard constraints.

    Attributes:
        passed: True if no BLOCKER violations exist.
        violations: All violations found (BLOCKER + WARNING).
        checked_at: ISO 8601 timestamp of when the check was performed.
    """
    passed: bool
    violations: list[ConstraintViolation] = field(default_factory=list)
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def blocker_count(self) -> int:
        """Number of BLOCKER-level violations."""
        return sum(1 for v in self.violations if v.severity == Severity.BLOCKER)

    @property
    def warning_count(self) -> int:
        """Number of WARNING-level violations."""
        return sum(1 for v in self.violations if v.severity == Severity.WARNING)


@dataclass
class EvidenceEnvelope:
    """An evidence record with freshness tracking.

    Evidence is considered stale if:
    - It has passed its expiration timestamp (is_fresh() returns False)
    - Its content hash has changed since the evidence was created
    """
    evidence_id: str
    content_hash: str
    created_at: str   # ISO 8601
    expires_at: Optional[str] = None  # ISO 8601, None = never expires
    phase: Optional[Phase] = None

    def is_fresh(self) -> bool:
        """Check if this evidence is still within its validity window."""
        if self.expires_at is None:
            return True
        now = datetime.now(timezone.utc)
        expires = datetime.fromisoformat(self.expires_at)
        return now < expires

    def has_hash_changed(self, current_hash: str) -> bool:
        """Check if the content hash differs from when evidence was created."""
        return self.content_hash != current_hash


class HardConstraints:
    """Hard constraint checker — the non-bypassable control kernel.

    Each constraint is an independent check function. Any BLOCKER-level
    violation means the operation MUST be denied.

    Usage:
        hc = HardConstraints()
        result = hc.check_all(context)
        if not result.passed:
            for v in result.violations:
                if v.severity == Severity.BLOCKER:
                    raise OperationDeniedError(v)
    """

    # ── Aggregate Check ─────────────────────────────────────────────────

    def check_all(self, context: dict[str, Any]) -> ConstraintCheckResult:
        """Run all hard constraint checks against the given context.

        Args:
            context: Dictionary containing all data needed for checks.
                Common keys:
                    - current_phase: Phase enum (current project phase)
                    - target_phase: Phase enum (phase being entered)
                    - phase_gates: dict[Phase|str, GateStatus|str]
                    - gates: dict of gate statuses
                    - tasks: list of task dicts with 'status' and 'id'/'name'
                    - target_path: str path being written to
                    - allowed_paths: list[str] of permitted paths
                    - quality_results: dict with keys 'test','lint','build'
                    - review_status: dict with 'independent-reviewer' verdict
                    - evidence_list: list[EvidenceEnvelope]
                    - current_hashes: dict[evidence_id, hash_str]

        Returns:
            ConstraintCheckResult with passed=True only if zero BLOCKER violations.
        """
        all_violations: list[ConstraintViolation] = []

        # C1: Requirements baseline check
        all_violations.extend(
            self.check_c1_requirements_baseline(context)
        )

        # C2: Architecture baseline check
        all_violations.extend(
            self.check_c2_architecture_baseline(context)
        )

        # C3: Task package check
        all_violations.extend(
            self.check_c3_task_package(context.get("tasks", []))
        )

        # C4: Path scope check (only when a write target is provided)
        # v3.3: Aggregate allowed_paths from task definitions (Qoder pattern)
        target_path = context.get("target_path")
        if target_path is not None:
            all_allowed = list(context.get("allowed_paths", []))
            # Also collect from active task definitions
            for task in context.get("tasks", []):
                if isinstance(task, dict) and task.get("status") in ("active", "in_progress"):
                    task_paths = task.get("allowed_paths", [])
                    if isinstance(task_paths, list):
                        all_allowed.extend(task_paths)
            all_violations.extend(
                self.check_c4_path_scope(target_path, all_allowed)
            )

        # C5: Verification check
        all_violations.extend(
            self.check_c5_verification(
                context.get("quality_results", {}),
                target_phase=context.get("target_phase"),
            )
        )

        # C6: Independent review check
        all_violations.extend(
            self.check_c6_independent_review(
                context.get("review_status", {}),
                current_phase=context.get("current_phase"),
            )
        )

        # C7: Blocker check
        all_violations.extend(
            self.check_c7_blockers(
                context.get("gates", {}),
                context.get("tasks", []),
            )
        )

        # C8: Evidence freshness check
        all_violations.extend(
            self.check_c8_evidence_freshness(
                context.get("evidence_list", []),
                context.get("current_hashes", {}),
            )
        )

        has_blockers = any(
            v.severity == Severity.BLOCKER for v in all_violations
        )

        return ConstraintCheckResult(
            passed=not has_blockers,
            violations=all_violations,
        )

    # ── C1: Requirements Baseline ───────────────────────────────────────

    def check_c1_requirements_baseline(
        self, context: dict[str, Any]
    ) -> list[ConstraintViolation]:
        """C1: No requirements baseline -> cannot enter formal implementation.

        S1-requirements phase must be completed and its gate approved
        before entering S2-architecture, S3-interface, or S4-implementation.
        """
        return self._check_phase_gate_baseline(
            context,
            gate_phase=Phase.S1_REQUIREMENTS,
            fallback_key="S1-requirements",
            constraint_id=ConstraintID.C1_NO_REQUIREMENTS,
            message="Cannot enter next phase without approved requirements baseline",
            detail_suffix="All requirements must be documented and the gate explicitly approved.",
            remediation=(
                "Complete S1-requirements phase: "
                "ensure product-manager, system-architect, and quality-engineer "
                "roles have all submitted PASS verdicts. Then request gate approval."
            ),
        )

    # ── C2: Architecture Baseline ───────────────────────────────────────

    def check_c2_architecture_baseline(
        self, context: dict[str, Any]
    ) -> list[ConstraintViolation]:
        """C2: No architecture baseline -> cannot enter development.

        S2-architecture phase must be completed and its gate approved
        before entering S2-architecture, S3-interface, or S4-implementation.
        """
        return self._check_phase_gate_baseline(
            context,
            gate_phase=Phase.S2_ARCHITECTURE,
            fallback_key="S2-architecture",
            constraint_id=ConstraintID.C2_NO_ARCHITECTURE,
            message="Cannot enter next phase without approved architecture baseline",
            detail_suffix="Architecture must be designed and reviewed before implementation begins.",
            remediation=(
                "Complete S2-architecture phase: "
                "ensure system-architect, module-architect, and independent-reviewer "
                "roles have all submitted PASS verdicts. Then request gate approval."
            ),
        )

    # ── Shared: Phase Gate Baseline Check ────────────────────────────────

    def _check_phase_gate_baseline(
        self,
        context: dict[str, Any],
        gate_phase: Phase,
        fallback_key: str,
        constraint_id: ConstraintID,
        message: str,
        detail_suffix: str,
        remediation: str,
    ) -> list[ConstraintViolation]:
        """Shared implementation for C1 and C2 phase-gate baseline checks.

        Checks that a prerequisite phase gate is APPROVED before entering
        architecture, interface, or implementation phases.
        """
        violations: list[ConstraintViolation] = []
        target_phase = context.get("target_phase")
        current_phase = context.get("current_phase")

        # Constraint applies when entering or in S2/S3/S4
        relevant_phases = {
            Phase.S2_ARCHITECTURE,
            Phase.S3_INTERFACE,
            Phase.S4_IMPLEMENTATION,
        }
        if target_phase not in relevant_phases and current_phase not in relevant_phases:
            return violations

        phase_gates = context.get("phase_gates", {})
        req_gate = phase_gates.get(gate_phase)
        # Also check by string key for flexibility
        if req_gate is None:
            req_gate = phase_gates.get(fallback_key)

        # FIX-4: Type guard — reject unexpected value types
        if req_gate is not None and not isinstance(req_gate, (GateStatus, str)):
            logger.warning(
                "Unexpected type for %s gate: %s. Expected GateStatus, str, or None. "
                "Treating as None.",
                gate_phase.value,
                type(req_gate).__name__,
            )
            req_gate = None

        # Normalize to GateStatus if string
        if isinstance(req_gate, str):
            try:
                req_gate = GateStatus(req_gate)
            except ValueError:
                req_gate = None

        if req_gate is None or req_gate != GateStatus.APPROVED:
            gate_label = req_gate.value if req_gate else "MISSING"
            violations.append(ConstraintViolation(
                constraint_id=constraint_id,
                severity=Severity.BLOCKER,
                message=message,
                detail=(
                    f"{gate_phase.value} gate status: {gate_label}. "
                    f"{detail_suffix}"
                ),
                remediation=remediation,
            ))

        return violations

    # ── C3: Task Package ────────────────────────────────────────────────

    def check_c3_task_package(
        self, tasks: list[dict[str, Any]]
    ) -> list[ConstraintViolation]:
        """C3: No active task package -> cannot write code.

        At least one task in task_graph.yaml must have status 'active' or
        'in_progress' before any Write/Edit/Bash operations are permitted.
        """
        violations: list[ConstraintViolation] = []

        active_tasks = [
            t for t in tasks
            if t.get("status") in (
                TaskStatus.ACTIVE.value,
                TaskStatus.IN_PROGRESS.value,
            )
        ]

        if not active_tasks:
            violations.append(ConstraintViolation(
                constraint_id=ConstraintID.C3_NO_TASK_PACKAGE,
                severity=Severity.BLOCKER,
                message="No active task found — cannot write code without an active task package",
                detail=(
                    f"Total tasks in graph: {len(tasks)}. "
                    "At least one task must be in 'active' or 'in_progress' status "
                    "before Write/Edit/Bash operations are allowed."
                ),
                remediation=(
                    "Activate a task in task_graph.yaml: "
                    "set status to 'active' for the task you intend to work on. "
                    "If no task exists, create one first via the product-manager role."
                ),
            ))

        return violations

    # ── C4: Path Scope ──────────────────────────────────────────────────

    def check_c4_path_scope(
        self, target_path: str, allowed_paths: list[str]
    ) -> list[ConstraintViolation]:
        """C4: Target path outside allowed scope -> write denied.

        Every file write operation must target a path within the
        allowed_paths defined by the active task.
        """
        violations: list[ConstraintViolation] = []

        # FIX-2: Normalize paths for the current OS, then convert to
        # forward slashes for PurePosixPath compatibility on Windows.
        target_path = os.path.normpath(target_path).replace("\\", "/")
        allowed_paths = [
            os.path.normpath(p).replace("\\", "/")
            for p in allowed_paths
            if p and p.strip()
        ]

        if not allowed_paths:
            violations.append(ConstraintViolation(
                constraint_id=ConstraintID.C4_PATH_OUT_OF_SCOPE,
                severity=Severity.BLOCKER,
                message="No allowed_paths defined — all write operations are out of scope",
                detail=(
                    f"Target path: {target_path}. "
                    "The active task has no allowed_paths configuration."
                ),
                remediation=(
                    "Define allowed_paths in the active task: "
                    "list the directories and file patterns the task is permitted to modify."
                ),
            ))
            return violations

        # Check if target_path is within any of the allowed paths
        target = PurePosixPath(target_path)
        in_scope = any(
            target == PurePosixPath(allowed)
            or str(target).startswith(str(PurePosixPath(allowed)) + "/")
            or str(target).startswith(str(PurePosixPath(allowed)) + "\\")
            for allowed in allowed_paths
        )

        if not in_scope:
            violations.append(ConstraintViolation(
                constraint_id=ConstraintID.C4_PATH_OUT_OF_SCOPE,
                severity=Severity.BLOCKER,
                message=f"Path '{target_path}' is outside allowed scope",
                detail=(
                    f"Target path: {target_path}. "
                    f"Allowed paths: {allowed_paths}. "
                    "Write operations are restricted to task-defined allowed_paths."
                ),
                remediation=(
                    f"Either modify the task's allowed_paths to include '{target_path}', "
                    f"or write to one of the allowed locations: {allowed_paths}."
                ),
            ))

        return violations

    # ── C5: Verification ────────────────────────────────────────────────

    def check_c5_verification(
        self,
        quality_results: dict[str, Any],
        target_phase: Phase | None = None,
    ) -> list[ConstraintViolation]:
        """C5: No deterministic verification -> cannot deliver.

        Before entering S6-delivery, tests, lint, and build must all
        have PASS status. Any failure blocks delivery.
        """
        violations: list[ConstraintViolation] = []

        # FIX-7: Warn when target_phase is None — caller may have omitted
        # phase context, making the check a no-op.
        if target_phase is None:
            warnings.warn(
                "C5 verification check called with target_phase=None. "
                "Verification enforcement is skipped because no target phase "
                "was provided. This may indicate a missing context in the caller."
            )
            return violations

        # Only enforced when targeting S6-delivery
        if target_phase != Phase.S6_DELIVERY:
            return violations

        checks_required = ["test", "lint", "build"]
        failed_checks: list[str] = []
        missing_checks: list[str] = []

        for check_name in checks_required:
            result = quality_results.get(check_name)
            if result is None:
                missing_checks.append(check_name)
            elif result != "PASS":
                failed_checks.append(f"{check_name}={result}")

        if missing_checks:
            violations.append(ConstraintViolation(
                constraint_id=ConstraintID.C5_NO_VERIFICATION,
                severity=Severity.BLOCKER,
                message="Cannot enter S6-delivery: verification evidence is incomplete",
                detail=(
                    f"Missing verification results for: {missing_checks}. "
                    f"Required checks: {checks_required}. "
                    "All verification checks must produce PASS results before delivery."
                ),
                remediation=(
                    f"Run the missing checks: {missing_checks}. "
                    "Ensure tests pass, linting is clean, and the build succeeds "
                    "before attempting to advance to S6-delivery."
                ),
            ))

        if failed_checks:
            violations.append(ConstraintViolation(
                constraint_id=ConstraintID.C5_NO_VERIFICATION,
                severity=Severity.BLOCKER,
                message="Cannot enter S6-delivery: verification checks have not all passed",
                detail=(
                    f"Failed checks: {failed_checks}. "
                    "All of [test, lint, build] must return PASS."
                ),
                remediation=(
                    f"Fix the failing checks: {failed_checks}. "
                    "Re-run verification after fixes and ensure all return PASS."
                ),
            ))

        return violations

    # ── C6: Independent Review ──────────────────────────────────────────

    def check_c6_independent_review(
        self,
        review_status: dict[str, Any],
        current_phase: Phase | None = None,
    ) -> list[ConstraintViolation]:
        """C6: No independent review -> cannot pass implementation gate.

        The implementation phase gate requires an independent-reviewer
        to submit a PASS verdict before the gate can be approved.
        """
        violations: list[ConstraintViolation] = []

        # FIX-7: Warn when current_phase is None — caller may have omitted
        # phase context, making the check a no-op.
        if current_phase is None:
            warnings.warn(
                "C6 independent review check called with current_phase=None. "
                "Review enforcement is skipped because no current phase "
                "was provided. This may indicate a missing context in the caller."
            )
            return violations

        # This constraint applies specifically to S4-implementation phase
        if current_phase != Phase.S4_IMPLEMENTATION:
            return violations

        reviewer_verdict = review_status.get("independent-reviewer")

        # FIX-3: Explicitly check PASS to pass; None → BLOCKER;
        # all other non-None values → WARNING.
        if reviewer_verdict is None:
            violations.append(ConstraintViolation(
                constraint_id=ConstraintID.C6_NO_INDEPENDENT_REVIEW,
                severity=Severity.BLOCKER,
                message="Cannot advance implementation gate: no independent review submitted",
                detail=(
                    "The independent-reviewer role has not submitted a verdict. "
                    "S4-implementation requires an independent review before the gate can pass."
                ),
                remediation=(
                    "Launch the independent-reviewer role to review the implementation. "
                    "The reviewer must be a different agent than the developer to avoid self-review."
                ),
            ))
        elif reviewer_verdict == "PASS":
            pass  # No violation
        else:
            findings = review_status.get("findings", "Not provided")
            violations.append(ConstraintViolation(
                constraint_id=ConstraintID.C6_NO_INDEPENDENT_REVIEW,
                severity=Severity.WARNING,
                message=(
                    f"Cannot advance implementation gate: "
                    f"independent review returned '{reviewer_verdict}'"
                ),
                detail=(
                    f"Independent-reviewer verdict: {reviewer_verdict}. "
                    f"Findings: {findings}. "
                    "A PASS verdict is required to clear this constraint."
                ),
                remediation=(
                    "Address the reviewer's findings, re-implement as needed, "
                    "and request a re-review. All findings must be resolved "
                    "and the reviewer must issue a PASS verdict."
                ),
            ))

        return violations

    # ── C7: Blockers ────────────────────────────────────────────────────

    def check_c7_blockers(
        self,
        gates: dict[Phase | str, GateStatus | str] | None,
        tasks: list[dict[str, Any]],
    ) -> list[ConstraintViolation]:
        """C7: Unresolved blockers exist -> cannot advance to next phase.

        Any gate with status=BLOCKED or any task with status=blocked
        prevents phase advancement.
        """
        violations: list[ConstraintViolation] = []

        # FIX-9: Type guard — reject non-dict, non-None gates parameter
        if gates is not None and not isinstance(gates, dict):
            raise TypeError(
                f"gates must be a dict or None, got {type(gates).__name__}"
            )

        gates = gates or {}

        blocked_gates: list[str] = []
        for phase_key, status in gates.items():
            gate_status = status
            if isinstance(gate_status, str):
                try:
                    gate_status = GateStatus(gate_status)
                except ValueError:
                    # FIX-5: Report unrecognized status as WARNING instead
                    # of silently skipping.
                    phase_name = (
                        phase_key.value
                        if isinstance(phase_key, Phase)
                        else str(phase_key)
                    )
                    violations.append(ConstraintViolation(
                        constraint_id=ConstraintID.C7_BLOCKER_EXISTS,
                        severity=Severity.WARNING,
                        message=(
                            f"Unrecognized gate status '{gate_status}' "
                            f"for phase '{phase_name}'"
                        ),
                        detail=(
                            f"Phase '{phase_name}' has an unrecognized "
                            f"gate status value: '{gate_status}'. "
                            "Valid statuses are: pending, approved, "
                            "rejected, blocked."
                        ),
                        remediation=(
                            f"Correct the gate status for '{phase_name}' "
                            "to one of the recognized values: "
                            "pending, approved, rejected, or blocked."
                        ),
                    ))
                    continue

            if gate_status == GateStatus.BLOCKED:
                phase_name = phase_key.value if isinstance(phase_key, Phase) else str(phase_key)
                blocked_gates.append(phase_name)

        blocked_tasks = [
            t.get("id", t.get("name", "unknown"))
            for t in tasks
            if t.get("status") == TaskStatus.BLOCKED.value
        ]

        if blocked_gates:
            violations.append(ConstraintViolation(
                constraint_id=ConstraintID.C7_BLOCKER_EXISTS,
                severity=Severity.BLOCKER,
                message="Cannot advance: blocked gates must be resolved first",
                detail=(
                    f"Blocked gates: {blocked_gates}. "
                    "Phase advancement is forbidden while any gate is in BLOCKED status."
                ),
                remediation=(
                    f"Resolve blockers for gates: {blocked_gates}. "
                    "Address the issues that caused the BLOCKED status "
                    "and request re-evaluation."
                ),
            ))

        if blocked_tasks:
            violations.append(ConstraintViolation(
                constraint_id=ConstraintID.C7_BLOCKER_EXISTS,
                severity=Severity.BLOCKER,
                message="Cannot advance: blocked tasks must be resolved first",
                detail=(
                    f"Blocked tasks: {blocked_tasks}. "
                    "Phase advancement is forbidden while any task is in blocked status."
                ),
                remediation=(
                    f"Resolve blockers for tasks: {blocked_tasks}. "
                    "Unblock the tasks by addressing dependencies or issues, "
                    "then change their status from 'blocked'."
                ),
            ))

        return violations

    # ── C8: Evidence Freshness ──────────────────────────────────────────

    def check_c8_evidence_freshness(
        self,
        evidence_list: list[EvidenceEnvelope],
        current_hashes: dict[str, str] | None = None,
    ) -> list[ConstraintViolation]:
        """C8: Stale evidence -> old results invalidated.

        Evidence is stale if:
        - EvidenceEnvelope.is_fresh() returns False (past expiration)
        - The content_hash differs from the current hash of the source data

        Stale evidence must be marked STALE and regenerated.
        """
        violations: list[ConstraintViolation] = []
        current_hashes = current_hashes or {}

        for evidence in evidence_list:
            # FIX-6: Validate that each element is an EvidenceEnvelope
            if not isinstance(evidence, EvidenceEnvelope):
                violations.append(ConstraintViolation(
                    constraint_id=ConstraintID.C8_STALE_EVIDENCE,
                    severity=Severity.WARNING,
                    message=(
                        f"Non-EvidenceEnvelope object in evidence_list: "
                        f"{type(evidence).__name__}"
                    ),
                    detail=(
                        f"Expected EvidenceEnvelope instance, got "
                        f"{type(evidence).__name__}: {evidence!r}. "
                        "This item will be skipped."
                    ),
                    remediation=(
                        "Ensure all items in evidence_list are "
                        "EvidenceEnvelope instances."
                    ),
                ))
                continue

            is_stale = False
            reasons: list[str] = []

            if not evidence.is_fresh():
                is_stale = True
                reasons.append(
                    f"expired at {evidence.expires_at}"
                )

            current_hash = current_hashes.get(evidence.evidence_id)
            if current_hash is not None and evidence.has_hash_changed(current_hash):
                is_stale = True
                reasons.append(
                    f"content hash changed "
                    f"(recorded: {evidence.content_hash[:12]}..., "
                    f"current: {current_hash[:12]}...)"
                )

            if is_stale:
                phase_label = evidence.phase.value if evidence.phase else "unknown"
                violations.append(ConstraintViolation(
                    constraint_id=ConstraintID.C8_STALE_EVIDENCE,
                    severity=Severity.BLOCKER,
                    message=f"Evidence '{evidence.evidence_id}' is stale and must be regenerated",
                    detail=(
                        f"Evidence ID: {evidence.evidence_id}. "
                        f"Reasons: {'; '.join(reasons)}. "
                        f"Phase: {phase_label}. "
                        "Stale evidence no longer reflects the current state of the project."
                    ),
                    remediation=(
                        f"Re-run the verification or review that produced '{evidence.evidence_id}'. "
                        "Evidence must be regenerated whenever source data changes "
                        "or the evidence's validity window expires."
                    ),
                ))

        return violations
