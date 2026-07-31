"""
T-0085 AC-04 — Constraint coverage matrix: trigger/allow tests through the
phase-advance entry points.

What this file covers (per constraint, one TRIGGER = violated -> advance
BLOCKED, one ALLOW = satisfied -> advance allowed):

  C1 (requirements gate)   : S1 -> S2 advance
  C2 (architecture gate)   : S2 -> S3 advance
  C5 (verification)        : S5 -> S6 advance
  C6 (independent review)  : S4 -> S5 advance
  C8 (evidence freshness)  : S2 -> S3 advance (envelope expiry / hash)
  C9 (import validity)     : S4 -> S5 advance (undeclared import)
  C10 (contract tests)     : S4 -> S5 advance (missing required tests)
  C11 (file limit)         : S4 -> S5 advance (allowed_paths > max_files)

Two entry points are exercised:

1. EnforcementHub.should_allow_phase_advance(target_phase) — the gate the
   developer wired into PhaseExecutor.execute_phase (T-0085 AC-02, executor.py
   Step 6b). Context is built from REAL disk state (.ai/state.yaml,
   .ai/gates.yaml, .ai/task_graph.yaml, .ai/evidence/**) via _build_context,
   exactly like production.
2. PhaseExecutor.execute_phase — smoke-level: gate blocks a violating advance
   WITHOUT writing .ai/state.yaml, allows a satisfied advance, and is skipped
   in fixture_mode (the TEST-ONLY escape hatch the wiring deliberately keeps).

RESOLVED DEFECT (T-0085 C5 hub fix, developer):
  should_allow_phase_advance previously called check_phase_constraints(...)
  WITHOUT verification_passed, so the phase-constraint table entry
  'C5-no-verification' (S6) always failed even when .ai/evidence shows
  test/lint/build all PASS. The developer fix (enforcement_hub.py) computes
  verification_passed from the quality_results the hub already builds
  (test/lint/build ALL == "PASS", mirroring the check_c5_verification kernel)
  and forwards it — fail-closed: absent or non-PASS evidence still blocks.
  test_allow_with_all_pass_quality_results is a real PASS now (xfail marker
  removed), and the old defect canary was flipped to pin the fixed behavior.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.enforcement_hub import EnforcementHub
from loop_core.executor import PhaseExecutor, RoleStep, StepStatus
from loop_core.hard_constraints import ConstraintID
from loop_core.state_machine import Phase


# ── Fixture builders (mirror tests/test_enforcement_hub.py conventions) ──


@pytest.fixture
def temp_project():
    """Temporary project directory with a minimal .ai/ governance dir."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".ai").mkdir()
        yield root


def _write_state(root: Path, **kwargs) -> None:
    """Write a minimal .ai/state.yaml."""
    lines = ["schema_version: 1", "project_name: test"]
    for k, v in kwargs.items():
        lines.append(f"{k}: {v}")
    (root / ".ai" / "state.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_gates(root: Path, gates: list[dict]) -> None:
    """Write .ai/gates.yaml."""
    (root / ".ai" / "gates.yaml").write_text(
        yaml.dump({"schema_version": 1, "gates": gates}), encoding="utf-8")


def _write_tasks(root: Path, tasks: list[dict]) -> None:
    """Write .ai/task_graph.yaml."""
    (root / ".ai" / "task_graph.yaml").write_text(
        yaml.dump({"schema_version": 1, "tasks": tasks}), encoding="utf-8")


def _write_quality_results(root: Path, td: str, checks: list[dict]) -> None:
    """Write .ai/evidence/<td>/quality/quality_report.json.

    This is the exact path EnforcementHub._load_quality_results reads
    (evidence_dir/<top-level-dir>/quality/quality_report.json).
    """
    d = root / ".ai" / "evidence" / td / "quality"
    d.mkdir(parents=True, exist_ok=True)
    (d / "quality_report.json").write_text(
        json.dumps({"checks": checks}), encoding="utf-8")


def _write_review(root: Path, td: str, verdict: str) -> None:
    """Write .ai/evidence/<td>/review.json (independent-reviewer verdict)."""
    d = root / ".ai" / "evidence" / td
    d.mkdir(parents=True, exist_ok=True)
    (d / "review.json").write_text(
        json.dumps({"role": "independent-reviewer", "verdict": verdict,
                    "findings": []}),
        encoding="utf-8")


def _write_envelope(root: Path, td: str, payload: dict) -> None:
    """Write .ai/evidence/<td>/evidence_envelope.json."""
    d = root / ".ai" / "evidence" / td
    d.mkdir(parents=True, exist_ok=True)
    (d / "evidence_envelope.json").write_text(
        json.dumps(payload), encoding="utf-8")


def _write_source(root: Path, rel_path: str, content: str) -> None:
    """Write a project source file (used by the C9 import scanner)."""
    p = root / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _violations_of(decision, cid: ConstraintID) -> list:
    """All violations of a given constraint in a hub decision."""
    return [v for v in decision.violations if v.constraint_id == cid]


def _violation_ids(decision) -> set[str]:
    """Set of constraint-id values present in a hub decision (any severity)."""
    return {v.constraint_id.value for v in decision.violations}


def _hub(root: Path) -> EnforcementHub:
    return EnforcementHub(root)


# ── Shared "everything else satisfied" gates for S4 -> S5 fixtures ────────

_S4_TO_S5_OK_GATES = [
    {"id": "G-S1-requirements-approved", "gate_type": "requirements",
     "status": "approved"},
    {"id": "G-S2-architecture-approved", "gate_type": "architecture",
     "status": "approved"},
    {"id": "G-S4-implementation-approved", "gate_type": "implementation",
     "status": "approved"},
]


# ═══════════════════════════════════════════════════════════════════════
# C1 — S1 requirements gate (S1 -> S2)
# ═══════════════════════════════════════════════════════════════════════


class TestC1PhaseAdvance:
    def test_trigger_blocked_without_approved_s1_gate(self, temp_project):
        """S2 advance with no approved S1 requirements gate -> BLOCKED (C1)."""
        _write_state(temp_project, current_phase="S1-requirements", loop_mode="FULL")
        _write_gates(temp_project, [
            {"id": "G-S2-architecture-approved", "gate_type": "architecture",
             "status": "approved"},
        ])
        _write_tasks(temp_project, [{"id": "T1", "status": "active"}])

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S2_ARCHITECTURE)

        assert decision.allowed is False
        assert _violations_of(decision, ConstraintID.C1_NO_REQUIREMENTS), \
            f"expected C1 violation, got {_violation_ids(decision)}"

    def test_allow_with_approved_s1_gate(self, temp_project):
        """S1 gate approved (plus S2 gate) -> S2 advance ALLOWED."""
        _write_state(temp_project, current_phase="S1-requirements", loop_mode="FULL")
        _write_gates(temp_project, [
            {"id": "G-S1-requirements-approved", "gate_type": "requirements",
             "status": "approved"},
            {"id": "G-S2-architecture-approved", "gate_type": "architecture",
             "status": "approved"},
        ])
        _write_tasks(temp_project, [{"id": "T1", "status": "active"}])

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S2_ARCHITECTURE)

        assert decision.allowed is True, decision.reason
        assert decision.blocker_count == 0


# ═══════════════════════════════════════════════════════════════════════
# C2 — S2 architecture gate (S2 -> S3)
# ═══════════════════════════════════════════════════════════════════════


class TestC2PhaseAdvance:
    def test_trigger_blocked_without_approved_s2_gate(self, temp_project):
        """S3 advance with no approved S2 architecture gate -> BLOCKED (C2)."""
        _write_state(temp_project, current_phase="S2-architecture", loop_mode="FULL")
        _write_gates(temp_project, [
            {"id": "G-S1-requirements-approved", "gate_type": "requirements",
             "status": "approved"},
        ])
        _write_tasks(temp_project, [{"id": "T1", "status": "active"}])

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S3_INTERFACE)

        assert decision.allowed is False
        assert _violations_of(decision, ConstraintID.C2_NO_ARCHITECTURE), \
            f"expected C2 violation, got {_violation_ids(decision)}"

    def test_allow_with_approved_s2_gate(self, temp_project):
        """S1 + S2 gates approved -> S3 advance ALLOWED."""
        _write_state(temp_project, current_phase="S2-architecture", loop_mode="FULL")
        _write_gates(temp_project, [
            {"id": "G-S1-requirements-approved", "gate_type": "requirements",
             "status": "approved"},
            {"id": "G-S2-architecture-approved", "gate_type": "architecture",
             "status": "approved"},
        ])
        _write_tasks(temp_project, [{"id": "T1", "status": "active"}])

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S3_INTERFACE)

        assert decision.allowed is True, decision.reason
        assert decision.blocker_count == 0


# ═══════════════════════════════════════════════════════════════════════
# C5 — verification (S5 -> S6)
# ═══════════════════════════════════════════════════════════════════════


class TestC5PhaseAdvance:
    @staticmethod
    def _ready_fixture(temp_project: Path, current_gate_id: str | None = "G-S6-user-approval"):
        """S5 project where EVERYTHING except verification is satisfied."""
        _write_state(
            temp_project, current_phase="S5-quality", loop_mode="FULL",
            current_gate_id=current_gate_id,
        )
        _write_gates(temp_project, [
            {"id": "G-S5-quality-approved", "gate_type": "quality",
             "status": "approved"},
            # satisfies phase-constraint C6-no-independent-review for S6
            {"id": "G-S5-independent-review-approved", "gate_type": "quality",
             "status": "approved"},
            # explicit user approval for S6 (USER_GATE_PHASES)
            {"id": "G-S6-user-approval", "gate_type": "user-delivery",
             "phase": "S6-delivery", "status": "approved",
             "approval_actor": "user"},
        ])
        _write_tasks(temp_project, [{"id": "T1", "status": "active"}])
        _write_review(temp_project, "T1", "PASS")
        (temp_project / "requirements.txt").write_text("requests>=2.0\n", encoding="utf-8")

    def test_trigger_blocked_without_quality_results(self, temp_project):
        """S6 advance with absent quality evidence -> BLOCKED (C5)."""
        self._ready_fixture(temp_project)

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S6_DELIVERY)

        assert decision.allowed is False
        assert _violations_of(decision, ConstraintID.C5_NO_VERIFICATION), \
            f"expected C5 violation, got {_violation_ids(decision)}"

    def test_trigger_blocked_with_failed_quality_results(self, temp_project):
        """S6 advance with lint=FAIL -> BLOCKED (C5)."""
        self._ready_fixture(temp_project)
        _write_quality_results(temp_project, "T1", [
            {"name": "test", "status": "PASS"},
            {"name": "lint", "status": "FAIL"},
            {"name": "build", "status": "PASS"},
        ])

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S6_DELIVERY)

        assert decision.allowed is False
        assert _violations_of(decision, ConstraintID.C5_NO_VERIFICATION), \
            f"expected C5 violation, got {_violation_ids(decision)}"

    def test_allow_with_all_pass_quality_results(self, temp_project):
        """S6 advance with test/lint/build all PASS -> ALLOWED (C5).

        This test was xfail-pinned to the C5 hub defect (verification_passed
        never forwarded to check_phase_constraints). The developer fix wires
        verification_passed through enforcement_hub.should_allow_phase_advance,
        so the S6 phase-constraint 'C5-no-verification' now evaluates True
        with all-PASS evidence and the advance is allowed.
        """
        self._ready_fixture(temp_project)
        _write_quality_results(temp_project, "T1", [
            {"name": "test", "status": "PASS"},
            {"name": "lint", "status": "PASS"},
            {"name": "build", "status": "PASS"},
        ])

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S6_DELIVERY)

        assert decision.allowed is True, decision.reason
        assert decision.blocker_count == 0

    def test_pass_evidence_clears_c5_kernel_and_phase_table(self, temp_project):
        """PASS evidence clears the C5 kernel check (check_all) AND the
        phase-constraint table 'C5-no-verification' for S6.

        Previously this test pinned the hub defect (allowed=False with
        'C5-no-verification' in the reason despite all-PASS evidence). After
        the T-0085 fix it pins the FIXED behavior: verification_passed is
        forwarded, so neither the kernel nor the phase table blocks S5->S6.
        """
        self._ready_fixture(temp_project)
        _write_quality_results(temp_project, "T1", [
            {"name": "test", "status": "PASS"},
            {"name": "lint", "status": "PASS"},
            {"name": "build", "status": "PASS"},
        ])

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S6_DELIVERY)

        # C5 kernel satisfied — no C5 violation comes from check_all
        assert not _violations_of(decision, ConstraintID.C5_NO_VERIFICATION)
        # ...and the phase-constraint table 'C5-no-verification' is also
        # satisfied (verification_passed forwarded) — no C7-mapped block
        assert decision.allowed is True
        assert "C5-no-verification" not in decision.reason
        assert not _violations_of(decision, ConstraintID.C7_BLOCKER_EXISTS)


# ═══════════════════════════════════════════════════════════════════════
# C6 — independent review (S4 -> S5)
# ═══════════════════════════════════════════════════════════════════════


class TestC6PhaseAdvance:
    def test_trigger_blocked_without_review_evidence(self, temp_project):
        """S4->S5 advance without independent-review evidence -> BLOCKED (C6)."""
        _write_state(temp_project, current_phase="S4-implementation", loop_mode="FULL")
        _write_gates(temp_project, _S4_TO_S5_OK_GATES)
        _write_tasks(temp_project, [{"id": "T1", "status": "active"}])
        _write_quality_results(temp_project, "T1", [{"name": "compile", "status": "PASS"}])
        (temp_project / "requirements.txt").write_text("requests>=2.0\n", encoding="utf-8")

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S5_QUALITY)

        assert decision.allowed is False
        assert _violations_of(decision, ConstraintID.C6_NO_INDEPENDENT_REVIEW), \
            f"expected C6 violation, got {_violation_ids(decision)}"

    def test_allow_with_review_evidence(self, temp_project):
        """Independent review PASS (+ compile PASS) -> S4->S5 advance ALLOWED."""
        _write_state(temp_project, current_phase="S4-implementation", loop_mode="FULL")
        _write_gates(temp_project, _S4_TO_S5_OK_GATES)
        _write_tasks(temp_project, [{"id": "T1", "status": "active"}])
        _write_quality_results(temp_project, "T1", [{"name": "compile", "status": "PASS"}])
        _write_review(temp_project, "T1", "PASS")
        (temp_project / "requirements.txt").write_text("requests>=2.0\n", encoding="utf-8")

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S5_QUALITY)

        assert decision.allowed is True, decision.reason
        assert decision.blocker_count == 0
        assert not _violations_of(decision, ConstraintID.C6_NO_INDEPENDENT_REVIEW)

    def test_non_pass_review_verdict_is_warning_not_blocker(self, temp_project):
        """C6 semantics (hard_constraints.py FIX-3): only a MISSING review
        verdict is a BLOCKER; a submitted non-PASS verdict (e.g. FAIL) is a
        WARNING and does not block the advance by itself."""
        _write_state(temp_project, current_phase="S4-implementation", loop_mode="FULL")
        _write_gates(temp_project, _S4_TO_S5_OK_GATES)
        _write_tasks(temp_project, [{"id": "T1", "status": "active"}])
        _write_quality_results(temp_project, "T1", [{"name": "compile", "status": "PASS"}])
        _write_review(temp_project, "T1", "FAIL")
        (temp_project / "requirements.txt").write_text("requests>=2.0\n", encoding="utf-8")

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S5_QUALITY)

        c6 = _violations_of(decision, ConstraintID.C6_NO_INDEPENDENT_REVIEW)
        assert c6, f"expected C6 violation, got {_violation_ids(decision)}"
        from loop_core.hard_constraints import Severity
        assert all(v.severity == Severity.WARNING for v in c6)
        # WARNING severity alone does not block the advance
        assert decision.allowed is True


# ═══════════════════════════════════════════════════════════════════════
# C8 — evidence freshness (S2 -> S3)
# ═══════════════════════════════════════════════════════════════════════


class TestC8PhaseAdvance:
    @staticmethod
    def _s2_s3_fixture(temp_project: Path):
        _write_state(temp_project, current_phase="S2-architecture", loop_mode="FULL")
        _write_gates(temp_project, [
            {"id": "G-S1-requirements-approved", "gate_type": "requirements",
             "status": "approved"},
            {"id": "G-S2-architecture-approved", "gate_type": "architecture",
             "status": "approved"},
        ])
        _write_tasks(temp_project, [{"id": "T1", "status": "active"}])

    def test_trigger_blocked_with_expired_evidence(self, temp_project):
        """Expired evidence envelope -> S3 advance BLOCKED (C8)."""
        self._s2_s3_fixture(temp_project)
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        _write_envelope(temp_project, "ev1", {
            "evidence_id": "ev1", "content_hash": "x" * 64,
            "created_at": past, "expires_at": past,
            "phase": "S2-architecture",
        })

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S3_INTERFACE)

        assert decision.allowed is False
        assert _violations_of(decision, ConstraintID.C8_STALE_EVIDENCE), \
            f"expected C8 violation, got {_violation_ids(decision)}"

    def test_trigger_blocked_with_changed_evidence_hash(self, temp_project):
        """Envelope whose recorded content_hash no longer matches the on-disk
        envelope -> S3 advance BLOCKED (C8 hash change)."""
        self._s2_s3_fixture(temp_project)
        now = datetime.now(timezone.utc).isoformat()
        future = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        _write_envelope(temp_project, "ev1", {
            "evidence_id": "ev1", "content_hash": "y" * 64,
            "created_at": now, "expires_at": future,
            "phase": "S2-architecture",
        })
        # current hash of the envelope file itself != recorded "y"*64
        env_file = temp_project / ".ai" / "evidence" / "ev1" / "evidence_envelope.json"
        assert hashlib.sha256(env_file.read_bytes()).hexdigest() != "y" * 64

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S3_INTERFACE)

        assert decision.allowed is False
        assert _violations_of(decision, ConstraintID.C8_STALE_EVIDENCE), \
            f"expected C8 violation, got {_violation_ids(decision)}"

    def test_allow_with_fresh_evidence(self, temp_project):
        """Fresh envelope (unexpired, no hash mismatch) -> S3 advance ALLOWED.

        Note: EnforcementHub._compute_evidence_hashes keys the hash map by the
        evidence DIRECTORY name, so the hash-mismatch branch only applies when
        the envelope's evidence_id equals its directory name. A fresh envelope
        therefore uses an evidence_id decoupled from the dir name (the
        envelope is tracked by expiry), which is the only hash-clean form the
        current hub supports for on-disk envelopes.
        """
        self._s2_s3_fixture(temp_project)
        now = datetime.now(timezone.utc).isoformat()
        future = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        _write_envelope(temp_project, "ev1", {
            "evidence_id": "artifact-1", "content_hash": "",
            "created_at": now, "expires_at": future,
            "phase": "S2-architecture",
        })

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S3_INTERFACE)

        assert decision.allowed is True, decision.reason
        assert decision.blocker_count == 0
        assert not _violations_of(decision, ConstraintID.C8_STALE_EVIDENCE)


# ═══════════════════════════════════════════════════════════════════════
# C9 — import validity (S4 -> S5)
# ═══════════════════════════════════════════════════════════════════════


class TestC9PhaseAdvance:
    @staticmethod
    def _s4_s5_clean_fixture(temp_project: Path, *, include_src: bool = True):
        _write_state(temp_project, current_phase="S4-implementation", loop_mode="FULL")
        _write_gates(temp_project, _S4_TO_S5_OK_GATES)
        _write_tasks(temp_project, [{"id": "T1", "status": "active"}])
        _write_quality_results(temp_project, "T1", [{"name": "compile", "status": "PASS"}])
        _write_review(temp_project, "T1", "PASS")
        (temp_project / "requirements.txt").write_text("requests>=2.0\n", encoding="utf-8")
        if include_src:
            _write_source(temp_project, "src/app.py",
                          "import os\nimport json\nfrom pathlib import Path\n")

    def test_trigger_blocked_with_undeclared_import(self, temp_project):
        """S4->S5 advance with an undeclared third-party import -> BLOCKED (C9)."""
        self._s4_s5_clean_fixture(temp_project)
        # undeclared: 'requests' is not stdlib, not project-local, and NOT in
        # requirements.txt (the fixture's requirements.txt declares pyyaml)
        _write_source(temp_project, "src/app.py", "import requests\nimport os\n")
        (temp_project / "requirements.txt").write_text("pyyaml>=6.0\n", encoding="utf-8")

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S5_QUALITY)

        assert decision.allowed is False
        assert _violations_of(decision, ConstraintID.C9_IMPORT_NOT_DECLARED), \
            f"expected C9 violation, got {_violation_ids(decision)}"

    def test_single_undeclared_import_reported_exactly_once(self, temp_project):
        """C9 dedup (T-0085 conditional-GO item 2): the explicit S4->S5 C9
        branch AND check_all both run C9 — the aggregation must not
        double-report. A single undeclared import -> exactly ONE C9
        violation (previously 2, doubling blocker_count / over-blocking)."""
        self._s4_s5_clean_fixture(temp_project)
        _write_source(temp_project, "src/app.py", "import requests\nimport os\n")
        (temp_project / "requirements.txt").write_text("pyyaml>=6.0\n", encoding="utf-8")

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S5_QUALITY)

        c9 = _violations_of(decision, ConstraintID.C9_IMPORT_NOT_DECLARED)
        assert len(c9) == 1, f"expected exactly 1 C9 violation, got {len(c9)}: {c9}"
        assert decision.blocker_count == 1
        assert decision.allowed is False

    def test_allow_with_clean_imports(self, temp_project):
        """S4->S5 advance with stdlib-only imports -> ALLOWED (C9 clean)."""
        self._s4_s5_clean_fixture(temp_project)

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S5_QUALITY)

        assert decision.allowed is True, decision.reason
        assert decision.blocker_count == 0
        assert not _violations_of(decision, ConstraintID.C9_IMPORT_NOT_DECLARED)

    def test_allow_with_declared_dependency(self, temp_project):
        """S4->S5 advance with the third-party import declared in
        requirements.txt -> ALLOWED (C9 clean)."""
        self._s4_s5_clean_fixture(temp_project, include_src=False)
        _write_source(temp_project, "src/app.py",
                      "import requests\nimport os\n")
        (temp_project / "requirements.txt").write_text("requests>=2.0\n", encoding="utf-8")

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S5_QUALITY)

        assert decision.allowed is True, decision.reason
        assert not _violations_of(decision, ConstraintID.C9_IMPORT_NOT_DECLARED)


# ═══════════════════════════════════════════════════════════════════════
# C10 / C11 — real trigger/allow tests through the hub (T-0085
# conditional-GO item 1: replaces the stale NOT_VERIFIED probe)
#
# Both checks read context["task_id"] (wired by EnforcementHub._build_context
# from state.current_task_id — T-0085 Fix 3) and C11 additionally reads
# context["max_files"] (state.max_files override, default 10). Both are SOFT
# (WARNING) by default, so a trigger produces a violation but does NOT block
# the advance by itself.
# ═══════════════════════════════════════════════════════════════════════


class TestC10C11PhaseAdvance:
    @staticmethod
    def _s4_s5_fixture(temp_project: Path, *, max_files: int | None = None,
                       contract_entries: list[dict] | None = None,
                       test_files: dict[str, str] | None = None,
                       task_md: str | None = None):
        """S4 project where everything else is satisfied; C10/C11 inputs are
        added per-test via contract_entries / test_files / task_md.

        current_task_id=T1 in state.yaml is REQUIRED: without it
        _build_context leaves task_id=None and C10/C11 return early by
        design (the dead-path the old probe pinned)."""
        state_kwargs = {"current_phase": "S4-implementation",
                        "loop_mode": "FULL", "current_task_id": "T1"}
        if max_files is not None:
            state_kwargs["max_files"] = max_files
        _write_state(temp_project, **state_kwargs)
        _write_gates(temp_project, _S4_TO_S5_OK_GATES)
        _write_tasks(temp_project, [{"id": "T1", "status": "active"}])
        _write_quality_results(temp_project, "T1", [{"name": "compile", "status": "PASS"}])
        _write_review(temp_project, "T1", "PASS")
        # requirements.txt present so C9 emits no missing-deps warnings and
        # the fixture has no source files to scan — C10/C11 stay isolated.
        (temp_project / "requirements.txt").write_text("requests>=2.0\n", encoding="utf-8")
        if contract_entries is not None:
            d = temp_project / ".ai" / "evidence" / "T1"
            d.mkdir(parents=True, exist_ok=True)
            (d / "interface-contract.json").write_text(
                json.dumps({"contracts": contract_entries}), encoding="utf-8")
        for rel, content in (test_files or {}).items():
            p = temp_project / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        if task_md is not None:
            td = temp_project / ".ai" / "tasks"
            td.mkdir(parents=True, exist_ok=True)
            (td / "T1.md").write_text(task_md, encoding="utf-8")

    # ── C10: contract test coverage ────────────────────────────────────

    def test_c10_trigger_contract_missing_required_tests(self, temp_project):
        """Contract file requiring tests that do NOT exist -> C10 violation
        (WARNING, does not block by itself)."""
        self._s4_s5_fixture(temp_project, contract_entries=[
            {"function": "api", "tests_required": ["test_api_add", "test_api_get"]},
        ])

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S5_QUALITY)

        c10 = _violations_of(decision, ConstraintID.C10_CONTRACT_TEST_MISSING)
        assert c10, f"expected C10 violation, got {_violation_ids(decision)}"
        from loop_core.hard_constraints import Severity
        assert all(v.severity == Severity.WARNING for v in c10)
        # SOFT by default: a C10 violation alone does not block the advance
        assert decision.allowed is True

    def test_c10_allow_required_tests_present(self, temp_project):
        """Contract required tests present in tests/ -> NO C10 violation."""
        self._s4_s5_fixture(temp_project, contract_entries=[
            {"function": "api", "tests_required": ["test_api_add", "test_api_get"]},
        ], test_files={"tests/test_api.py":
                       "def test_api_add():\n    pass\n"
                       "def test_api_get():\n    pass\n"})

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S5_QUALITY)

        assert not _violations_of(decision, ConstraintID.C10_CONTRACT_TEST_MISSING)

    # ── C11: task file limit ───────────────────────────────────────────

    def test_c11_trigger_allowed_paths_exceed_max_files(self, temp_project):
        """Task markdown listing more allowed paths than max_files -> C11
        violation (WARNING). max_files is set low (2) via state.yaml."""
        self._s4_s5_fixture(temp_project, max_files=2, task_md=(
            "allowed_paths:\n"
            "- src/a.py\n"
            "- src/b.py\n"
            "- src/c.py\n"))

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S5_QUALITY)

        c11 = _violations_of(decision, ConstraintID.C11_TASK_FILE_LIMIT_EXCEEDED)
        assert c11, f"expected C11 violation, got {_violation_ids(decision)}"
        from loop_core.hard_constraints import Severity
        assert all(v.severity == Severity.WARNING for v in c11)
        assert decision.allowed is True

    def test_c11_allow_within_max_files(self, temp_project):
        """Task markdown within the default limit (2 <= 10) -> NO C11
        violation."""
        self._s4_s5_fixture(temp_project, task_md=(
            "allowed_paths:\n"
            "- src/a.py\n"
            "- src/b.py\n"))

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S5_QUALITY)

        assert not _violations_of(decision, ConstraintID.C11_TASK_FILE_LIMIT_EXCEEDED)

    # ── Allow: clean fixture ───────────────────────────────────────────

    def test_c10_c11_allow_clean_fixture(self, temp_project):
        """Clean fixture (no contract file, no task markdown) -> no C10/C11
        violations and the advance is allowed."""
        self._s4_s5_fixture(temp_project)

        decision = _hub(temp_project).should_allow_phase_advance(Phase.S5_QUALITY)

        assert not _violations_of(decision, ConstraintID.C10_CONTRACT_TEST_MISSING)
        assert not _violations_of(decision, ConstraintID.C11_TASK_FILE_LIMIT_EXCEEDED)
        assert decision.allowed is True, decision.reason
        assert decision.blocker_count == 0


# ═══════════════════════════════════════════════════════════════════════
# PhaseExecutor.execute_phase smoke tests (the real phase-advance entry
# point, T-0085 AC-02 wiring: Step 6b consults should_allow_phase_advance
# BEFORE persist_state; BLOCKED -> no state.yaml write; skipped in
# fixture_mode / reentry)
# ═══════════════════════════════════════════════════════════════════════


class TestExecutePhaseGate:
    def test_blocked_advance_does_not_persist_state(self, temp_project, monkeypatch):
        """S1->S2 without an approved S1 gate: execute_phase returns BLOCKED
        with a phase-advance-gate step and .ai/state.yaml stays at S1."""
        _write_state(temp_project, current_phase="S1-requirements", loop_mode="FULL")
        _write_gates(temp_project, [
            {"id": "G-S2-architecture-approved", "gate_type": "architecture",
             "status": "approved"},
        ])
        _write_tasks(temp_project, [{"id": "T1", "status": "active"}])

        executor = PhaseExecutor()  # fixture_mode=False -> gate ACTIVE
        # Simulate successful role execution; the gate decides the outcome
        def _fake_execute_role(role_id, role_prompt, input_files,
                               output_file=None, required_fields=None):
            return RoleStep(role_id=role_id, status=StepStatus.COMPLETE,
                            verdict="PASS", filled_fields=list(required_fields or []),
                            output_file=output_file)
        monkeypatch.setattr(executor, "execute_role", _fake_execute_role)

        plan = executor.execute_phase(Phase.S2_ARCHITECTURE, temp_project)

        assert plan.status == StepStatus.BLOCKED
        assert any(s.role_id == "phase-advance-gate" for s in plan.steps), \
            [s.role_id for s in plan.steps]
        # state.yaml must NOT have advanced
        state_after = yaml.safe_load(
            (temp_project / ".ai" / "state.yaml").read_text(encoding="utf-8"))
        assert state_after.get("current_phase") == "S1-requirements"

    def test_allowed_advance_persists_state(self, temp_project, monkeypatch):
        """S1->S2 with S1+S2 gates approved: execute_phase COMPLETEs and
        .ai/state.yaml advances to S2."""
        _write_state(temp_project, current_phase="S1-requirements", loop_mode="FULL")
        _write_gates(temp_project, [
            {"id": "G-S1-requirements-approved", "gate_type": "requirements",
             "status": "approved"},
            {"id": "G-S2-architecture-approved", "gate_type": "architecture",
             "status": "approved"},
        ])
        _write_tasks(temp_project, [{"id": "T1", "status": "active"}])

        executor = PhaseExecutor()
        def _fake_execute_role(role_id, role_prompt, input_files,
                               output_file=None, required_fields=None):
            return RoleStep(role_id=role_id, status=StepStatus.COMPLETE,
                            verdict="PASS", filled_fields=list(required_fields or []),
                            output_file=output_file)
        monkeypatch.setattr(executor, "execute_role", _fake_execute_role)

        plan = executor.execute_phase(Phase.S2_ARCHITECTURE, temp_project)

        assert plan.status == StepStatus.COMPLETE
        state_after = yaml.safe_load(
            (temp_project / ".ai" / "state.yaml").read_text(encoding="utf-8"))
        assert state_after.get("current_phase") == "S2-architecture"

    def test_gate_skipped_in_fixture_mode(self, temp_project):
        """fixture_mode=True is the TEST-ONLY escape hatch: the gate is
        skipped and the phase advances even without an approved S1 gate."""
        _write_state(temp_project, current_phase="S1-requirements", loop_mode="FULL")
        _write_gates(temp_project, [
            {"id": "G-S2-architecture-approved", "gate_type": "architecture",
             "status": "approved"},
        ])
        _write_tasks(temp_project, [{"id": "T1", "status": "active"}])

        executor = PhaseExecutor(fixture_mode=True)

        plan = executor.execute_phase(Phase.S2_ARCHITECTURE, temp_project)

        assert plan.status == StepStatus.COMPLETE
        assert not any(s.role_id == "phase-advance-gate" for s in plan.steps)
        state_after = yaml.safe_load(
            (temp_project / ".ai" / "state.yaml").read_text(encoding="utf-8"))
        assert state_after.get("current_phase") == "S2-architecture"
