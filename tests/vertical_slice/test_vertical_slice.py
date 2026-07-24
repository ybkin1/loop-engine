"""
Vertical Slice End-to-End Validation for Loop Engine Governance.

This test suite validates that Loop's governance system is effective in a
realistic scenario by checking the integrity and completeness of pre-generated
evidence data for a mini web application project ("Simple Task Manager").

The tests verify governance data integrity — that phases exist, gates are
approved, seeded defects are detected by the correct roles, blocked delivery
is prevented, repairs work, and human review packets are readable.

These tests do NOT call AI agents. They verify the governance framework's
checking logic against structured evidence files.

Design:
- Evidence files are pre-generated structured data (YAML, JSON, Markdown)
- Tests validate data completeness, cross-references, and governance rules
- At least 15 test cases covering the full lifecycle
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Ensure the parent (loop-engine root) is on sys.path for loop_core imports
_SRC_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_SRC_ROOT))

import pytest

# Optional: validate PROJECT_MAP against schema if yaml is available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from loop_core.state_machine import Phase, GateStatus


# ---------------------------------------------------------------------------
# Path Helpers
# ---------------------------------------------------------------------------

EVIDENCE_DIR = Path(__file__).resolve().parent / "evidence"
SAMPLE_DIR = Path(__file__).resolve().parent / "sample_project"
PROJECT_MAP_PATH = SAMPLE_DIR / "PROJECT_MAP.yaml"
CHECKLIST_PATH = Path(__file__).resolve().parent / "checklist.json"


def _read_json(path: Path) -> dict:
    """Read and parse a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_text(path: Path) -> str:
    """Read a text file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# 1. Phase and File Existence
# ---------------------------------------------------------------------------

class TestPhaseExistence:
    """Verify that all required lifecycle phase evidence files exist."""

    REQUIRED_PHASES = ["S1-requirements", "S2-architecture", "S4-implementation",
                       "S5-quality", "S6-delivery"]

    REQUIRED_FILES = {
        "S1-requirements": ["requirements.md", "gate-approval.md"],
        "S2-architecture": ["architecture.md", "gate-approval.md"],
        "S4-implementation": ["code_diff.patch", "test_results.json"],
        "S5-quality": ["quality_report.json", "lint_results.json"],
        "S6-delivery": ["delivery_decision.json", "human_review_packet.md"],
    }

    @pytest.mark.parametrize("phase", REQUIRED_PHASES)
    def test_phase_directory_exists(self, phase):
        """Each required phase must have an evidence subdirectory."""
        phase_dir = EVIDENCE_DIR / phase
        assert phase_dir.is_dir(), (
            f"Missing phase directory: {phase_dir}"
        )

    @pytest.mark.parametrize("phase", REQUIRED_PHASES)
    def test_phase_evidence_files_exist(self, phase):
        """Each phase must contain its required evidence files."""
        phase_dir = EVIDENCE_DIR / phase
        required = self.REQUIRED_FILES[phase]
        for filename in required:
            file_path = phase_dir / filename
            assert file_path.is_file(), (
                f"Missing evidence file: {file_path}"
            )

    def test_all_required_phases_present_in_evidence(self):
        """The evidence directory must contain exactly the expected phases."""
        actual_dirs = sorted(
            d.name for d in EVIDENCE_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        for phase in self.REQUIRED_PHASES:
            assert phase in actual_dirs, (
                f"Phase '{phase}' not found in evidence directory. Found: {actual_dirs}"
            )

    def test_no_extra_phases_in_evidence(self):
        """No unexpected phase directories should exist."""
        actual_dirs = sorted(
            d.name for d in EVIDENCE_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        for d in actual_dirs:
            assert d in self.REQUIRED_PHASES, (
                f"Unexpected phase directory: {d}"
            )


# ---------------------------------------------------------------------------
# 2. PROJECT_MAP Validation
# ---------------------------------------------------------------------------

class TestProjectMap:
    """Validate that the sample PROJECT_MAP.yaml is well-formed and complete."""

    def test_project_map_file_exists(self):
        """PROJECT_MAP.yaml must exist."""
        assert PROJECT_MAP_PATH.is_file(), (
            f"PROJECT_MAP.yaml not found at {PROJECT_MAP_PATH}"
        )

    def test_project_map_is_valid_yaml(self):
        """PROJECT_MAP.yaml must be parseable YAML."""
        if not HAS_YAML:
            pytest.skip("PyYAML not installed")
        with open(PROJECT_MAP_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), "PROJECT_MAP must be a YAML object"
        assert "project" in data, "PROJECT_MAP missing 'project' key"

    def test_project_map_has_3_pages(self):
        """Sample project must define exactly 3 pages."""
        if not HAS_YAML:
            pytest.skip("PyYAML not installed")
        with open(PROJECT_MAP_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        pages = data.get("pages", [])
        assert len(pages) == 3, (
            f"Expected 3 pages, got {len(pages)}: {[p.get('id') for p in pages]}"
        )

    def test_project_map_has_5_api_endpoints(self):
        """Sample project must define exactly 5 API endpoints."""
        if not HAS_YAML:
            pytest.skip("PyYAML not installed")
        with open(PROJECT_MAP_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        endpoints = data.get("api_endpoints", [])
        assert len(endpoints) == 5, (
            f"Expected 5 API endpoints, got {len(endpoints)}"
        )

    def test_project_map_has_3_modules(self):
        """Sample project must define exactly 3 modules."""
        if not HAS_YAML:
            pytest.skip("PyYAML not installed")
        with open(PROJECT_MAP_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        modules = data.get("modules", [])
        assert len(modules) == 3, (
            f"Expected 3 modules, got {len(modules)}"
        )

    def test_project_map_has_2_database_tables(self):
        """Sample project must define exactly 2 database tables."""
        if not HAS_YAML:
            pytest.skip("PyYAML not installed")
        with open(PROJECT_MAP_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        tables = data.get("database", {}).get("tables", [])
        assert len(tables) == 2, (
            f"Expected 2 database tables, got {len(tables)}"
        )

    def test_project_map_passes_schema_validation(self):
        """PROJECT_MAP must pass the Loop PROJECT_MAP_SCHEMA validation."""
        if not HAS_YAML:
            pytest.skip("PyYAML not installed")
        with open(PROJECT_MAP_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        from loop_core.project_map_schema import ProjectMapValidator
        validator = ProjectMapValidator()
        is_valid, errors = validator.validate(data)
        assert is_valid, (
            f"PROJECT_MAP schema validation failed: {errors}"
        )

    def test_project_map_referential_integrity(self):
        """PROJECT_MAP must have valid cross-references (no dangling refs)."""
        if not HAS_YAML:
            pytest.skip("PyYAML not installed")
        with open(PROJECT_MAP_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        from loop_core.project_map_schema import ProjectMapValidator
        validator = ProjectMapValidator()
        ref_errors = validator.check_referential_integrity(data)
        assert len(ref_errors) == 0, (
            f"PROJECT_MAP referential integrity errors: {ref_errors}"
        )


# ---------------------------------------------------------------------------
# 3. Gate Approval Integrity
# ---------------------------------------------------------------------------

class TestGateApproval:
    """Verify that all phase gates have proper approval records."""

    GATE_PHASES = ["S1-requirements", "S2-architecture"]

    @pytest.mark.parametrize("phase", GATE_PHASES)
    def test_gate_approval_file_exists(self, phase):
        """Each gated phase must have a gate-approval.md."""
        gate_file = EVIDENCE_DIR / phase / "gate-approval.md"
        assert gate_file.is_file(), f"Missing gate approval: {gate_file}"

    @pytest.mark.parametrize("phase", GATE_PHASES)
    def test_gate_status_is_approved(self, phase):
        """Each gate approval must state APPROVED status."""
        gate_file = EVIDENCE_DIR / phase / "gate-approval.md"
        content = _read_text(gate_file)
        assert "APPROVED" in content, (
            f"Gate approval for {phase} does not contain APPROVED status"
        )

    @pytest.mark.parametrize("phase", GATE_PHASES)
    def test_gate_approval_has_timestamp(self, phase):
        """Each gate approval must have a timestamp."""
        gate_file = EVIDENCE_DIR / phase / "gate-approval.md"
        content = _read_text(gate_file)
        # Look for ISO timestamp pattern
        ts_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?"
        assert re.search(ts_pattern, content), (
            f"Gate approval for {phase} missing ISO timestamp"
        )

    @pytest.mark.parametrize("phase", GATE_PHASES)
    def test_gate_approval_has_approval_record_id(self, phase):
        """Each gate approval must reference an ApprovalRecord ID (AR- prefix)."""
        gate_file = EVIDENCE_DIR / phase / "gate-approval.md"
        content = _read_text(gate_file)
        assert "AR-" in content, (
            f"Gate approval for {phase} missing ApprovalRecord ID"
        )

    def test_gates_are_in_correct_order(self):
        """Gate approvals must reference the correct previous gate."""
        s1_content = _read_text(EVIDENCE_DIR / "S1-requirements" / "gate-approval.md")
        s2_content = _read_text(EVIDENCE_DIR / "S2-architecture" / "gate-approval.md")
        # S1 should be root (no parent or state "None (root)")
        # S2 should reference S1
        assert "GATE-S1-001" in s2_content or "S1-requirements" in s2_content, (
            "S2 gate approval does not reference S1 as parent"
        )


# ---------------------------------------------------------------------------
# 4. Seeded Defect Detection
# ---------------------------------------------------------------------------

class TestSeededDefects:
    """Verify that all 3 seeded defects exist and are detected by correct roles."""

    def test_quality_report_contains_three_defects(self):
        """Quality report must list exactly 3 seeded defects."""
        qr = _read_json(EVIDENCE_DIR / "S5-quality" / "quality_report.json")
        defects = qr["quality_report"]["defects_found"]
        assert len(defects) == 3, (
            f"Expected 3 seeded defects, found {len(defects)}"
        )

    def test_security_defect_detected_by_security_engineer(self):
        """VS-SEC-001 must be detected by security-engineer."""
        qr = _read_json(EVIDENCE_DIR / "S5-quality" / "quality_report.json")
        sec_defects = [
            d for d in qr["quality_report"]["defects_found"]
            if d["defect_id"] == "VS-SEC-001"
        ]
        assert len(sec_defects) == 1, "VS-SEC-001 not found in quality report"
        defect = sec_defects[0]
        assert defect["detected_by"] == "security-engineer", (
            f"VS-SEC-001 detected by {defect['detected_by']}, expected security-engineer"
        )
        assert defect["type"] == "security", (
            f"VS-SEC-001 type is {defect['type']}, expected 'security'"
        )

    def test_quality_defect_detected_by_quality_engineer(self):
        """VS-QUAL-001 must be detected by quality-engineer."""
        qr = _read_json(EVIDENCE_DIR / "S5-quality" / "quality_report.json")
        qual_defects = [
            d for d in qr["quality_report"]["defects_found"]
            if d["defect_id"] == "VS-QUAL-001"
        ]
        assert len(qual_defects) == 1, "VS-QUAL-001 not found in quality report"
        defect = qual_defects[0]
        assert defect["detected_by"] == "quality-engineer", (
            f"VS-QUAL-001 detected by {defect['detected_by']}, expected quality-engineer"
        )
        assert defect["type"] == "quality", (
            f"VS-QUAL-001 type is {defect['type']}, expected 'quality'"
        )

    def test_architecture_defect_detected_by_system_architect(self):
        """VS-ARCH-001 must be detected by system-architect."""
        qr = _read_json(EVIDENCE_DIR / "S5-quality" / "quality_report.json")
        arch_defects = [
            d for d in qr["quality_report"]["defects_found"]
            if d["defect_id"] == "VS-ARCH-001"
        ]
        assert len(arch_defects) == 1, "VS-ARCH-001 not found in quality report"
        defect = arch_defects[0]
        assert defect["detected_by"] == "system-architect", (
            f"VS-ARCH-001 detected by {defect['detected_by']}, expected system-architect"
        )
        assert defect["type"] == "architecture", (
            f"VS-ARCH-001 type is {defect['type']}, expected 'architecture'"
        )

    def test_all_seeded_defects_are_unresolved_initially(self):
        """Before repair, all seeded defects must be marked as unresolved."""
        qr = _read_json(EVIDENCE_DIR / "S5-quality" / "quality_report.json")
        for defect in qr["quality_report"]["defects_found"]:
            assert defect["status"] == "unresolved", (
                f"Defect {defect['defect_id']} should be unresolved, "
                f"got {defect['status']}"
            )

    def test_all_seeded_defects_have_veto_records(self):
        """Each seeded defect must have a corresponding veto record."""
        qr = _read_json(EVIDENCE_DIR / "S5-quality" / "quality_report.json")
        for defect in qr["quality_report"]["defects_found"]:
            veto = defect.get("veto")
            assert veto is not None, (
                f"Defect {defect['defect_id']} missing veto record"
            )
            assert "veto_id" in veto, (
                f"Defect {defect['defect_id']} veto missing veto_id"
            )
            assert veto["severity"] == "blocker", (
                f"Defect {defect['defect_id']} veto severity should be 'blocker'"
            )

    def test_code_diff_contains_defect_markers(self):
        """The code diff must contain comments marking all 3 seeded defects."""
        diff = _read_text(EVIDENCE_DIR / "S4-implementation" / "code_diff.patch")
        assert "VS-SEC-001" in diff, "code_diff.patch missing VS-SEC-001 marker"
        assert "VS-QUAL-001" in diff, "code_diff.patch missing VS-QUAL-001 marker"
        assert "VS-ARCH-001" in diff, "code_diff.patch missing VS-ARCH-001 marker"

    def test_lint_results_identify_all_defects(self):
        """Lint results must flag issues corresponding to all 3 defects."""
        lint = _read_json(EVIDENCE_DIR / "S5-quality" / "lint_results.json")
        defect_refs = set()
        for issue in lint["lint_results"]["issues"]:
            ref = issue.get("defect_ref")
            if ref:
                defect_refs.add(ref)
        assert "VS-SEC-001" in defect_refs, "Lint results do not flag VS-SEC-001"
        assert "VS-QUAL-001" in defect_refs, "Lint results do not flag VS-QUAL-001"
        assert "VS-ARCH-001" in defect_refs, "Lint results do not flag VS-ARCH-001"


# ---------------------------------------------------------------------------
# 5. Delivery Blocking and Repair
# ---------------------------------------------------------------------------

class TestDeliveryBlocking:
    """Verify that delivery is correctly blocked with unresolved defects,
    and that repairs unblock it."""

    def test_initial_delivery_decision_is_nogo(self):
        """First delivery attempt must be NOGO due to unresolved defects."""
        dd = _read_json(EVIDENCE_DIR / "S6-delivery" / "delivery_decision.json")
        history = dd["delivery_decision"]["decision_history"]
        assert len(history) >= 2, (
            f"Expected at least 2 delivery attempts, got {len(history)}"
        )
        first = history[0]
        assert first["decision"] == "NOGO", (
            f"First delivery decision should be NOGO, got {first['decision']}"
        )

    def test_nogo_decision_lists_all_blockers(self):
        """The NOGO decision must list all 3 seeded defects as blockers."""
        dd = _read_json(EVIDENCE_DIR / "S6-delivery" / "delivery_decision.json")
        first = dd["delivery_decision"]["decision_history"][0]
        blocked_ids = {b["defect_id"] for b in first["blocked_by"]}
        expected = {"VS-SEC-001", "VS-QUAL-001", "VS-ARCH-001"}
        assert blocked_ids == expected, (
            f"Blocked defects {blocked_ids} != expected {expected}"
        )

    def test_nogo_specifies_required_repairs(self):
        """The NOGO decision must specify what repairs are needed."""
        dd = _read_json(EVIDENCE_DIR / "S6-delivery" / "delivery_decision.json")
        first = dd["delivery_decision"]["decision_history"][0]
        repairs = first.get("required_repairs", [])
        assert len(repairs) == 3, (
            f"Expected 3 required repairs, got {len(repairs)}"
        )

    def test_second_delivery_decision_is_go_after_repair(self):
        """After repairs, the second delivery attempt must be GO."""
        dd = _read_json(EVIDENCE_DIR / "S6-delivery" / "delivery_decision.json")
        second = dd["delivery_decision"]["decision_history"][1]
        assert second["decision"] == "GO", (
            f"Second delivery decision should be GO after repair, got {second['decision']}"
        )

    def test_repairs_are_verified_by_vetoing_roles(self):
        """Each repair must be verified by the role that issued the veto."""
        dd = _read_json(EVIDENCE_DIR / "S6-delivery" / "delivery_decision.json")
        second = dd["delivery_decision"]["decision_history"][1]
        repairs = second["repairs_completed"]

        verified_by = {r["defect_id"]: r["verified_by"] for r in repairs}
        assert verified_by.get("VS-SEC-001") == "security-engineer", (
            "VS-SEC-001 repair not verified by security-engineer"
        )
        assert verified_by.get("VS-QUAL-001") == "quality-engineer", (
            "VS-QUAL-001 repair not verified by quality-engineer"
        )
        assert verified_by.get("VS-ARCH-001") == "system-architect", (
            "VS-ARCH-001 repair not verified by system-architect"
        )

    def test_regression_tests_all_pass_after_repair(self):
        """All regression tests must pass after repair (18/18)."""
        dd = _read_json(EVIDENCE_DIR / "S6-delivery" / "delivery_decision.json")
        second = dd["delivery_decision"]["decision_history"][1]
        reg = second["regression_results"]
        assert reg["total"] == 18, f"Expected 18 regression tests, got {reg['total']}"
        assert reg["passed"] == 18, f"Expected 18 passed, got {reg['passed']}"
        assert reg["failed"] == 0, f"Expected 0 failed, got {reg['failed']}"

    def test_final_decision_is_go(self):
        """The final delivery decision must be GO."""
        dd = _read_json(EVIDENCE_DIR / "S6-delivery" / "delivery_decision.json")
        assert dd["delivery_decision"]["final_decision"] == "GO", (
            f"Final decision should be GO, got {dd['delivery_decision']['final_decision']}"
        )

    def test_all_quality_gates_pass_after_repair(self):
        """All quality gates must pass after repair."""
        dd = _read_json(EVIDENCE_DIR / "S6-delivery" / "delivery_decision.json")
        second = dd["delivery_decision"]["decision_history"][1]
        gates = second["quality_gates"]
        for gate_name, gate_status in gates.items():
            assert gate_status == "PASS", (
                f"Quality gate '{gate_name}' is {gate_status}, expected PASS"
            )


# ---------------------------------------------------------------------------
# 6. Human Review Packet Readability
# ---------------------------------------------------------------------------

class TestHumanReviewPacket:
    """Verify that the S6-delivery human review packet is readable by
    non-technical stakeholders."""

    # Technical terms that must NOT appear in the human review packet
    FORBIDDEN_TERMS = [
        "sql injection",
        "xss",
        "cross-site scripting",
        "race condition",
        "buffer overflow",
        "null pointer",
        "memory leak",
        "deadlock",
        "ddos",
        "privilege escalation",
        "csrf",
        "regex",
        "regexp",
        "deserialization",
        "integer overflow",
        "f-string",
        "parameterized query",
        "dependency injection",
        "abstract base class",
        "interface segregation",
        "middleware",
        "middleware hook",
        "jwt",
        "json web token",
        "bearer token",
        "endpoint",
        "rest",
        "restful",
        "api gateway",
        "dependency graph",
        "acyclic",
        "circular import",
        "import cycle",
        "module contract",
        "schema",
        "orm",
        "session token",
        "auth middleware",
        "rate limiting",
        "bandit",
        "ruff",
        "lint",
        "linting",
    ]

    def test_human_review_packet_exists(self):
        """S6-delivery human_review_packet.md must exist."""
        hrp = EVIDENCE_DIR / "S6-delivery" / "human_review_packet.md"
        assert hrp.is_file(), f"Missing human review packet: {hrp}"

    def test_human_review_packet_has_required_sections(self):
        """The human review packet must contain all required sections."""
        content = _read_text(EVIDENCE_DIR / "S6-delivery" / "human_review_packet.md")
        required_sections = [
            "What We Did",
            "What Changed",
            "Key Choices",
            "Main Risks",
            "Quality Check",
            "Who Reviewed This Work",
            "You Need to Decide",
        ]
        for section in required_sections:
            assert section in content, (
                f"Human review packet missing section: '{section}'"
            )

    def test_human_review_packet_has_decision_checklist(self):
        """The human review packet must present a decision with checkbox options."""
        content = _read_text(EVIDENCE_DIR / "S6-delivery" / "human_review_packet.md")
        assert "- [ ]" in content, (
            "Human review packet missing decision checklist (- [ ] items)"
        )
        # Should have at least 3 options
        checkbox_count = content.count("- [ ]")
        assert checkbox_count >= 3, (
            f"Expected at least 3 checkbox options, found {checkbox_count}"
        )

    @pytest.mark.parametrize("term", [
        "sql injection", "f-string", "parameterized query", "circular import",
        "middleware", "jwt", "endpoint", "dependency graph", "lint",
    ])
    def test_human_review_packet_avoids_technical_term(self, term):
        """The human review packet must not contain specific technical terms."""
        content = _read_text(
            EVIDENCE_DIR / "S6-delivery" / "human_review_packet.md"
        ).lower()
        assert term not in content, (
            f"Human review packet contains forbidden technical term: '{term}'"
        )

    def test_human_review_packet_uses_analogies(self):
        """The human review packet must use everyday analogies to explain risks."""
        content = _read_text(EVIDENCE_DIR / "S6-delivery" / "human_review_packet.md")
        assert "Analogy:" in content or "*Analogy:*" in content, (
            "Human review packet should include analogies for risks"
        )

    def test_human_review_packet_has_recommendation(self):
        """The human review packet must include a recommendation."""
        content = _read_text(EVIDENCE_DIR / "S6-delivery" / "human_review_packet.md")
        assert "recommend" in content.lower(), (
            "Human review packet missing recommendation"
        )


# ---------------------------------------------------------------------------
# 7. Role Participation
# ---------------------------------------------------------------------------

class TestRoleParticipation:
    """Verify that all required roles participated in the governance process."""

    REQUIRED_ROLES = [
        "product-manager",
        "system-architect",
        "developer",
        "quality-engineer",
        "security-engineer",
        "independent-reviewer",
        "delivery-manager",
    ]

    def test_quality_report_has_all_role_verdicts(self):
        """The S5 quality report must record verdicts from all core roles."""
        qr = _read_json(EVIDENCE_DIR / "S5-quality" / "quality_report.json")
        verdicts = qr["quality_report"]["role_verdicts"]
        for role in self.REQUIRED_ROLES:
            assert role in verdicts, (
                f"Quality report missing verdict from required role: {role}"
            )

    def test_vetoing_roles_are_blocked(self):
        """Roles that found defects must have BLOCKED verdicts."""
        qr = _read_json(EVIDENCE_DIR / "S5-quality" / "quality_report.json")
        verdicts = qr["quality_report"]["role_verdicts"]
        expected_blocked = {"security-engineer", "quality-engineer",
                            "system-architect", "independent-reviewer",
                            "delivery-manager"}
        for role in expected_blocked:
            assert verdicts[role]["verdict"] == "BLOCKED", (
                f"Role '{role}' should be BLOCKED, got {verdicts[role]['verdict']}"
            )

    def test_post_repair_all_roles_pass(self):
        """After repair, all vetoing roles must switch to PASS."""
        dd = _read_json(EVIDENCE_DIR / "S6-delivery" / "delivery_decision.json")
        second = dd["delivery_decision"]["decision_history"][1]
        post_verdicts = second["role_verdicts_post_repair"]
        for role, verdict in post_verdicts.items():
            assert verdict == "PASS", (
                f"Role '{role}' post-repair verdict should be PASS, got {verdict}"
            )

    def test_at_least_seven_roles_in_quality_report(self):
        """Quality report must have verdicts from at least 7 roles."""
        qr = _read_json(EVIDENCE_DIR / "S5-quality" / "quality_report.json")
        verdicts = qr["quality_report"]["role_verdicts"]
        assert len(verdicts) >= 7, (
            f"Expected at least 7 role verdicts, got {len(verdicts)}"
        )


# ---------------------------------------------------------------------------
# 8. Evidence Chain Integrity
# ---------------------------------------------------------------------------

class TestEvidenceChainIntegrity:
    """Verify the evidence chain is intact and properly linked."""

    def test_evidence_chain_has_root(self):
        """The evidence chain must have a root (S1 requirements)."""
        checklist = _read_json(CHECKLIST_PATH)
        chain = checklist["evidence_chain"]
        assert chain["root"] is not None, "Evidence chain missing root"
        assert "S1-requirements" in chain["root"], (
            f"Evidence chain root should start with S1-requirements: {chain['root']}"
        )

    def test_evidence_chain_has_links(self):
        """The evidence chain must have at least 3 links connecting phases."""
        checklist = _read_json(CHECKLIST_PATH)
        links = checklist["evidence_chain"]["links"]
        assert len(links) >= 3, (
            f"Expected at least 3 evidence chain links, got {len(links)}"
        )

    def test_evidence_chain_links_are_ordered(self):
        """Evidence chain links must be in phase order (S1 -> S2 -> S5 -> S6)."""
        checklist = _read_json(CHECKLIST_PATH)
        links = checklist["evidence_chain"]["links"]
        phase_order = ["S1-requirements", "S2-architecture", "S5-quality", "S6-delivery"]
        for i, expected_phase in enumerate(phase_order):
            if i < len(links):
                assert expected_phase in links[i], (
                    f"Link {i} should reference {expected_phase}, got: {links[i]}"
                )

    def test_evidence_files_are_readable(self):
        """All evidence files must be valid readable files (JSON or markdown)."""
        for phase_dir in EVIDENCE_DIR.iterdir():
            if not phase_dir.is_dir() or phase_dir.name.startswith("."):
                continue
            for ev_file in phase_dir.iterdir():
                if ev_file.suffix in (".json", ".md", ".yaml", ".patch"):
                    content = _read_text(ev_file)
                    assert len(content) > 0, (
                        f"Evidence file is empty: {ev_file}"
                    )


# ---------------------------------------------------------------------------
# 9. Checklist Consistency
# ---------------------------------------------------------------------------

class TestChecklistConsistency:
    """Verify that the checklist.json is internally consistent."""

    def test_checklist_exists(self):
        """checklist.json must exist."""
        assert CHECKLIST_PATH.is_file(), f"Missing checklist: {CHECKLIST_PATH}"

    def test_checklist_has_required_fields(self):
        """Checklist must have all required top-level fields."""
        checklist = _read_json(CHECKLIST_PATH)
        required = [
            "required_phases", "required_roles", "seeded_defects",
            "expected_detection_rate", "expected_blocks",
            "expected_repairs", "expected_final_decision",
        ]
        for field in required:
            assert field in checklist, f"Checklist missing field: {field}"

    def test_checklist_seeded_defect_count_matches_evidence(self):
        """Checklist seeded_defects.count must be 3."""
        checklist = _read_json(CHECKLIST_PATH)
        assert checklist["seeded_defects"]["count"] == 3, (
            f"Checklist defect count should be 3, got {checklist['seeded_defects']['count']}"
        )

    def test_checklist_expected_final_decision_is_go(self):
        """Checklist expected_final_decision must be GO."""
        checklist = _read_json(CHECKLIST_PATH)
        assert checklist["expected_final_decision"] == "GO", (
            f"Expected final decision should be GO, got {checklist['expected_final_decision']}"
        )

    def test_checklist_defect_ids_match_quality_report(self):
        """Checklist defect IDs must match those in the quality report."""
        checklist = _read_json(CHECKLIST_PATH)
        qr = _read_json(EVIDENCE_DIR / "S5-quality" / "quality_report.json")

        cl_ids = {d["id"] for d in checklist["seeded_defects"]["defects"]}
        qr_ids = {d["defect_id"] for d in qr["quality_report"]["defects_found"]}
        assert cl_ids == qr_ids, (
            f"Checklist defect IDs {cl_ids} != quality report IDs {qr_ids}"
        )

    def test_checklist_governance_checks_all_true(self):
        """All governance_checks in checklist must be true."""
        checklist = _read_json(CHECKLIST_PATH)
        gov_checks = checklist.get("governance_checks", {})
        for check_name, check_value in gov_checks.items():
            assert check_value is True, (
                f"Governance check '{check_name}' is {check_value}, expected True"
            )


# ---------------------------------------------------------------------------
# 10. Full Traceability
# ---------------------------------------------------------------------------

class TestEndToEndTraceability:
    """Verify end-to-end traceability from requirements to delivery."""

    def test_requirements_reference_in_architecture(self):
        """Architecture document must reference requirements."""
        arch = _read_text(EVIDENCE_DIR / "S2-architecture" / "architecture.md")
        assert "FR-01" in arch or "FR-0" in arch or "requirements" in arch.lower(), (
            "Architecture document does not reference requirements"
        )

    def test_implementation_references_architecture(self):
        """Code diff must contain references to architecture decisions."""
        diff = _read_text(EVIDENCE_DIR / "S4-implementation" / "code_diff.patch")
        # The diff references architecture violation VS-ARCH-001, which ties
        # back to S2-architecture design
        assert "VS-ARCH-001" in diff, (
            "Implementation diff does not contain architecture defect reference"
        )

    def test_quality_report_references_implementation(self):
        """Quality report must reference implementation artifacts."""
        qr = _read_json(EVIDENCE_DIR / "S5-quality" / "quality_report.json")
        for defect in qr["quality_report"]["defects_found"]:
            assert "file" in defect, (
                f"Defect {defect['defect_id']} missing file reference"
            )
            assert defect["file"].startswith("src/"), (
                f"Defect {defect['defect_id']} file not in src/: {defect['file']}"
            )

    def test_delivery_references_all_prior_phases(self):
        """Delivery decision must reference defects found in S5-quality."""
        dd = _read_json(EVIDENCE_DIR / "S6-delivery" / "delivery_decision.json")
        first = dd["delivery_decision"]["decision_history"][0]
        blocked_ids = {b["defect_id"] for b in first["blocked_by"]}
        assert "VS-SEC-001" in blocked_ids
        assert "VS-QUAL-001" in blocked_ids
        assert "VS-ARCH-001" in blocked_ids

    def test_full_phase_ordering_is_correct(self):
        """Evidence phase ordering must follow Loop's lifecycle (S1->S2->S4->S5->S6)."""
        expected_order = [
            "S1-requirements",
            "S2-architecture",
            "S4-implementation",
            "S5-quality",
            "S6-delivery",
        ]
        # Verify via checklist
        checklist = _read_json(CHECKLIST_PATH)
        phase_map = checklist["phase_mapping"]
        phases_in_order = [
            phase_map[p] for p in ["S1", "S2", "S4", "S5", "S6"]
        ]
        assert phases_in_order == expected_order, (
            f"Phase order {phases_in_order} != expected {expected_order}"
        )


# ---------------------------------------------------------------------------
# 11. Implementation Evidence Quality
# ---------------------------------------------------------------------------

class TestImplementationEvidence:
    """Verify the quality and completeness of S4 implementation evidence."""

    def test_test_results_is_valid_json(self):
        """S4 test_results.json must be valid JSON with expected structure."""
        tr = _read_json(EVIDENCE_DIR / "S4-implementation" / "test_results.json")
        assert "total_tests" in tr
        assert "passed" in tr
        assert "failed" in tr
        assert tr["total_tests"] == tr["passed"] + tr["failed"] + tr["skipped"]

    def test_test_results_shows_some_failures(self):
        """Before repair, test results must show failures (the defects)."""
        tr = _read_json(EVIDENCE_DIR / "S4-implementation" / "test_results.json")
        assert tr["failed"] > 0, (
            "Test results should show failures from seeded defects"
        )

    def test_code_diff_is_valid_patch(self):
        """code_diff.patch must be a valid unified diff format."""
        diff = _read_text(EVIDENCE_DIR / "S4-implementation" / "code_diff.patch")
        assert "diff --git" in diff, "Patch file should contain git diff headers"
        assert "---" in diff, "Patch file should contain --- markers"
        assert "+++" in diff, "Patch file should contain +++ markers"

    def test_code_diff_has_new_files(self):
        """Code diff must contain new file markers."""
        diff = _read_text(EVIDENCE_DIR / "S4-implementation" / "code_diff.patch")
        assert "new file mode" in diff, (
            "Patch should contain 'new file mode' for new source files"
        )

    def test_code_diff_contains_imports(self):
        """Code diff must contain Python import statements."""
        diff = _read_text(EVIDENCE_DIR / "S4-implementation" / "code_diff.patch")
        assert "import " in diff or "from " in diff, (
            "Patch should contain Python import statements"
        )

    def test_quality_report_json_is_valid(self):
        """S5 quality_report.json must have all required top-level keys."""
        qr = _read_json(EVIDENCE_DIR / "S5-quality" / "quality_report.json")
        qr_data = qr["quality_report"]
        required_keys = [
            "phase", "task_id", "overall_result", "defects_found",
            "checks", "role_verdicts",
        ]
        for key in required_keys:
            assert key in qr_data, f"Quality report missing key: {key}"

    def test_quality_report_overall_result_is_blocked(self):
        """Quality report overall_result must be BLOCKED due to defects."""
        qr = _read_json(EVIDENCE_DIR / "S5-quality" / "quality_report.json")
        assert qr["quality_report"]["overall_result"] == "BLOCKED", (
            f"Expected BLOCKED, got {qr['quality_report']['overall_result']}"
        )

    def test_lint_results_has_critical_issues(self):
        """Lint results must contain critical-severity issues."""
        lint = _read_json(EVIDENCE_DIR / "S5-quality" / "lint_results.json")
        assert lint["lint_results"]["critical"] > 0, (
            "Lint results should have at least 1 critical issue"
        )
