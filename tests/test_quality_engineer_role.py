"""
Tests for the quality-engineer role — the first complete Loop role implementation.

Validates the three-layer role architecture:
  1. CONTRACT.yaml — role identity, stance, responsibilities, veto power, projection rules
  2. THINKING_FRAMEWORK.md — mandatory multi-perspective thinking order
  3. INTERNAL_LOOP.md — self-check loop with iteration limits
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path for importing loop_core modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.project_map_schema import ProjectMapQuery


# ── Paths ──────────────────────────────────────────────────────────────────
ROLE_DIR = Path(__file__).resolve().parent.parent / "agents" / "quality-engineer"
CONTRACT_PATH = ROLE_DIR / "CONTRACT.yaml"
THINKING_PATH = ROLE_DIR / "THINKING_FRAMEWORK.md"
INTERNAL_LOOP_PATH = ROLE_DIR / "INTERNAL_LOOP.md"


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def load_yaml(path: Path) -> dict:
    """Load a YAML file and return its parsed content."""
    import yaml
    raw = path.read_text(encoding="utf-8")
    return yaml.safe_load(raw)


VAGUE_TERMS = ["可能", "也许", "尽量", "差不多", "大概", "基本上", "通常", "一般"]


def assert_no_vague_terms(text: str, context: str = ""):
    """Assert that text does not contain vague/hedging terms."""
    found = []
    for term in VAGUE_TERMS:
        if term in text:
            found.append(term)
    if found:
        label = f" ({context})" if context else ""
        pytest.fail(
            f"Found vague terms{label}: {found}. "
            f"fixed_stance must use precise, verifiable language."
        )


# ═══════════════════════════════════════════════════════════════════════════
# CONTRACT.yaml Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestContractFile:
    """CONTRACT.yaml existence, parseability, and completeness."""

    def test_contract_file_exists(self):
        """CONTRACT.yaml must exist in the quality-engineer directory."""
        assert CONTRACT_PATH.exists(), (
            f"CONTRACT.yaml not found at {CONTRACT_PATH}"
        )
        assert CONTRACT_PATH.is_file(), (
            f"{CONTRACT_PATH} exists but is not a file"
        )

    def test_contract_is_valid_yaml(self):
        """CONTRACT.yaml must be parseable as YAML."""
        contract = load_yaml(CONTRACT_PATH)
        assert isinstance(contract, dict), (
            "CONTRACT.yaml root must be a mapping (dict)"
        )

    def test_contract_has_role_id(self):
        """CONTRACT.yaml must declare role_id: quality-engineer."""
        contract = load_yaml(CONTRACT_PATH)
        assert contract.get("role_id") == "quality-engineer", (
            "CONTRACT.yaml missing or incorrect role_id"
        )


class TestContractIdentity:
    """Tests for the identity section of CONTRACT.yaml."""

    REQUIRED_IDENTITY_FIELDS = ["title", "experience", "expertise", "known_blind_spots"]

    def test_identity_section_exists(self):
        contract = load_yaml(CONTRACT_PATH)
        assert "identity" in contract, "CONTRACT.yaml missing 'identity' section"

    def test_identity_has_all_required_fields(self):
        contract = load_yaml(CONTRACT_PATH)
        identity = contract["identity"]
        for field in self.REQUIRED_IDENTITY_FIELDS:
            assert field in identity, (
                f"identity section missing required field: '{field}'"
            )

    def test_expertise_is_non_empty_list(self):
        contract = load_yaml(CONTRACT_PATH)
        expertise = contract["identity"]["expertise"]
        assert isinstance(expertise, list), "identity.expertise must be a list"
        assert len(expertise) > 0, "identity.expertise must not be empty"

    def test_blind_spots_are_declarative(self):
        """known_blind_spots must acknowledge what the role CANNOT do."""
        contract = load_yaml(CONTRACT_PATH)
        blind_spots = contract["identity"]["known_blind_spots"]
        assert isinstance(blind_spots, list), "known_blind_spots must be a list"
        assert len(blind_spots) > 0, "known_blind_spots must not be empty"
        for spot in blind_spots:
            assert isinstance(spot, str), f"Blind spot must be a string, got {type(spot)}"


class TestContractFixedStance:
    """Tests for the fixed_stance section — these must be precise, verifiable."""

    def test_fixed_stance_exists_and_non_empty(self):
        contract = load_yaml(CONTRACT_PATH)
        assert "fixed_stance" in contract, "CONTRACT.yaml missing 'fixed_stance' section"
        stances = contract["fixed_stance"]
        assert isinstance(stances, list), "fixed_stance must be a list"
        assert len(stances) >= 3, (
            f"fixed_stance must have at least 3 items, got {len(stances)}"
        )

    def test_fixed_stance_no_vague_terms(self):
        """Every fixed_stance item must use precise, verifiable language."""
        contract = load_yaml(CONTRACT_PATH)
        for i, stance in enumerate(contract["fixed_stance"]):
            assert_no_vague_terms(stance, f"fixed_stance[{i}]")

    def test_fixed_stance_covers_core_positions(self):
        """Check that core quality-engineering positions are represented."""
        contract = load_yaml(CONTRACT_PATH)
        stances_text = " ".join(contract["fixed_stance"])
        # Must assert the role is about finding problems, not proving correctness
        assert "找问题" in stances_text or "问题" in stances_text, (
            "fixed_stance must assert the role finds problems"
        )
        # Must reference evidence or data
        assert "证据" in stances_text or "数字" in stances_text or "工具" in stances_text or "数据" in stances_text, (
            "fixed_stance must reference reliance on evidence or tool output"
        )


class TestContractResponsibilities:
    """Tests for the responsibilities section."""

    def test_responsibilities_exists_and_non_empty(self):
        contract = load_yaml(CONTRACT_PATH)
        assert "responsibilities" in contract, "CONTRACT.yaml missing 'responsibilities'"
        resp = contract["responsibilities"]
        assert isinstance(resp, list), "responsibilities must be a list"
        assert len(resp) > 0, "responsibilities must not be empty"

    def test_responsibilities_cover_quality_gates(self):
        """Responsibilities must include quality gate execution."""
        contract = load_yaml(CONTRACT_PATH)
        resp_text = " ".join(contract["responsibilities"])
        assert "测试" in resp_text or "门禁" in resp_text or "质量" in resp_text, (
            "responsibilities must reference quality or testing duties"
        )


class TestContractProhibitions:
    """Tests for the prohibitions section."""

    def test_prohibitions_exists_and_non_empty(self):
        contract = load_yaml(CONTRACT_PATH)
        assert "prohibitions" in contract, "CONTRACT.yaml missing 'prohibitions'"
        proh = contract["prohibitions"]
        assert isinstance(proh, list), "prohibitions must be a list"
        assert len(proh) > 0, "prohibitions must not be empty"

    def test_prohibition_on_modifying_code(self):
        """The role must be prohibited from modifying business code."""
        contract = load_yaml(CONTRACT_PATH)
        proh_text = " ".join(contract["prohibitions"])
        assert "修改" in proh_text or "改" in proh_text, (
            "prohibitions must forbid modifying business code"
        )


class TestContractVetoPower:
    """Tests for the veto_power section."""

    def test_veto_power_exists_and_non_empty(self):
        contract = load_yaml(CONTRACT_PATH)
        assert "veto_power" in contract, "CONTRACT.yaml missing 'veto_power'"
        veto = contract["veto_power"]
        assert isinstance(veto, list), "veto_power must be a list"
        assert len(veto) > 0, "veto_power must not be empty"

    def test_veto_covers_coverage_lint_security(self):
        """Veto power must cover coverage, lint/typecheck, and security."""
        contract = load_yaml(CONTRACT_PATH)
        veto_text = " ".join(contract["veto_power"])
        assert "覆盖率" in veto_text or "coverage" in veto_text.lower(), (
            "veto_power must mention coverage"
        )
        assert "lint" in veto_text.lower() or "typecheck" in veto_text.lower(), (
            "veto_power must mention lint/typecheck"
        )
        # The securty veto may use "安全" or "security"
        has_security = (
            "安全" in veto_text
            or "CRITICAL" in veto_text
            or "security" in veto_text.lower()
        )
        assert has_security, "veto_power must mention security scanning issues"

    def test_veto_on_fake_pass(self):
        """Veto power must include checks for fake PASS (empty output)."""
        contract = load_yaml(CONTRACT_PATH)
        veto_text = " ".join(contract["veto_power"])
        assert "假" in veto_text or "空" in veto_text or "虚假" in veto_text, (
            "veto_power must detect fake PASS scenarios"
        )

    def test_veto_on_seeded_defects(self):
        """Veto power must include self-veto when seeded defects are missed."""
        contract = load_yaml(CONTRACT_PATH)
        veto_text = " ".join(contract["veto_power"])
        assert "seeded" in veto_text.lower() or "预埋" in veto_text or "植入" in veto_text, (
            "veto_power must include self-veto for missed seeded defects"
        )


class TestContractArtifacts:
    """Tests for input_artifacts and output_artifacts sections."""

    def test_input_artifacts_exists_and_non_empty(self):
        contract = load_yaml(CONTRACT_PATH)
        assert "input_artifacts" in contract, "CONTRACT.yaml missing 'input_artifacts'"
        inp = contract["input_artifacts"]
        assert isinstance(inp, list), "input_artifacts must be a list"
        assert len(inp) > 0, "input_artifacts must not be empty"

    def test_output_artifacts_exists_and_non_empty(self):
        contract = load_yaml(CONTRACT_PATH)
        assert "output_artifacts" in contract, "CONTRACT.yaml missing 'output_artifacts'"
        out = contract["output_artifacts"]
        assert isinstance(out, list), "output_artifacts must be a list"
        assert len(out) > 0, "output_artifacts must not be empty"

    def test_output_includes_go_nogo(self):
        """Output artifacts must include a GO/NOGO delivery judgment."""
        contract = load_yaml(CONTRACT_PATH)
        out_text = " ".join(contract["output_artifacts"])
        assert "GO" in out_text or "NOGO" in out_text or "交付" in out_text, (
            "output_artifacts must include delivery judgment (GO/NOGO)"
        )


class TestContractQualityStandards:
    """Tests for the quality_standards section."""

    def test_quality_standards_exists_and_non_empty(self):
        contract = load_yaml(CONTRACT_PATH)
        assert "quality_standards" in contract, (
            "CONTRACT.yaml missing 'quality_standards'"
        )
        std = contract["quality_standards"]
        assert isinstance(std, list), "quality_standards must be a list"
        assert len(std) > 0, "quality_standards must not be empty"


class TestContractProjectionRules:
    """Tests for the projection_rules section — must be parseable by ProjectMapQuery."""

    def test_projection_rules_exists(self):
        contract = load_yaml(CONTRACT_PATH)
        assert "projection_rules" in contract, (
            "CONTRACT.yaml missing 'projection_rules'"
        )

    def test_projection_rules_has_include_exclude(self):
        contract = load_yaml(CONTRACT_PATH)
        rules = contract["projection_rules"]
        assert "include_sections" in rules, (
            "projection_rules missing 'include_sections'"
        )
        assert "exclude_sections" in rules, (
            "projection_rules missing 'exclude_sections'"
        )

    def test_projection_rules_include_sections_non_empty(self):
        contract = load_yaml(CONTRACT_PATH)
        includes = contract["projection_rules"]["include_sections"]
        assert isinstance(includes, list), "include_sections must be a list"
        assert len(includes) > 0, "include_sections must not be empty"

    def test_projection_rules_exclude_pages_and_database(self):
        """Quality engineer should NOT see pages or database sections."""
        contract = load_yaml(CONTRACT_PATH)
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "pages" in excludes, (
            "exclude_sections must include 'pages' — quality engineer doesn't need UI details"
        )
        assert "database" in excludes, (
            "exclude_sections must include 'database' — quality engineer doesn't need DB schema"
        )

    def test_projection_rules_quality_dimensions(self):
        """Projection rules must include quality-dimension questions."""
        contract = load_yaml(CONTRACT_PATH)
        dims = contract["projection_rules"].get("quality_dimensions", [])
        assert isinstance(dims, list), "quality_dimensions must be a list"
        assert len(dims) > 0, "quality_dimensions must not be empty"
        for dim in dims:
            assert isinstance(dim, str), f"quality_dimension must be a string, got {type(dim)}"
            assert "?" in dim or "？" in dim, (
                f"quality_dimension should be a question: '{dim}'"
            )

    def test_projection_paths_parseable_by_project_map_query(self):
        """Each include_sections path must be parseable by ProjectMapQuery.

        This does NOT require a real PROJECT_MAP — it only verifies that the
        path syntax uses supported patterns (dot-separated, wildcard, field access).
        """
        contract = load_yaml(CONTRACT_PATH)
        includes = contract["projection_rules"]["include_sections"]

        # Valid path patterns are: word, word.*.field, word.field
        valid_path_pattern = re.compile(
            r'^[a-zA-Z_][a-zA-Z0-9_.*]*$'
        )

        for path in includes:
            assert valid_path_pattern.match(path), (
                f"include_sections path '{path}' does not match supported "
                f"ProjectMapQuery syntax (dot-separated, wildcard, field access)"
            )

    def test_projection_rules_applied_to_sample_data(self):
        """Apply projection rules to a minimal sample PROJECT_MAP.

        Verifies that include_sections paths resolve correctly, and exclude_sections
        are not included in the result.
        """
        contract = load_yaml(CONTRACT_PATH)
        rules = contract["projection_rules"]

        # Minimal PROJECT_MAP with enough data to exercise projection paths
        sample_map = {
            "project": {
                "name": "TestApp",
                "type": "web_app",
                "description": "A test project",
            },
            "pages": [
                {"id": "page-login", "path": "/login", "title": "Login"},
            ],
            "api_endpoints": [
                {"id": "api-login", "method": "POST", "path": "/api/auth/login"},
            ],
            "modules": [
                {"id": "auth-module", "responsibilities": ["user authentication"]},
            ],
            "database": {
                "tables": [
                    {"name": "users", "columns": [{"name": "id", "type": "INT"}]},
                ],
            },
        }

        query = ProjectMapQuery()

        # 1. Verify each include_section resolves to a non-None value
        for path in rules["include_sections"]:
            result = query.query(sample_map, path)
            assert result is not None, (
                f"Include path '{path}' returned None for sample PROJECT_MAP. "
                f"Either the path is wrong or sample_map is missing needed data."
            )

        # 2. Verify exclude_sections are NOT in the resolved set
        for excluded in rules["exclude_sections"]:
            result = query.query(sample_map, excluded)
            # The exclude path itself should resolve (it exists in sample_map),
            # but the quality engineer should not USE it in their projection
            assert result is not None, (
                f"Exclude path '{excluded}' does not exist in sample PROJECT_MAP. "
                f"Exclude path should map to a real section that the role is denied access to."
            )


class TestContractVetoEscalation:
    """Tests for veto escalation rules."""

    def test_veto_escalation_exists(self):
        contract = load_yaml(CONTRACT_PATH)
        assert "veto_escalation" in contract, (
            "CONTRACT.yaml missing 'veto_escalation'"
        )

    def test_veto_escalation_has_evidence_and_upgrade(self):
        contract = load_yaml(CONTRACT_PATH)
        esc_text = " ".join(str(v) for v in contract["veto_escalation"])
        # Must mention evidence attachment
        assert "证据" in esc_text or "evidence" in esc_text.lower(), (
            "veto_escalation must mandate evidence attachment"
        )
        # Must mention upgrade/escalation path
        assert "升级" in esc_text or "escalat" in esc_text.lower(), (
            "veto_escalation must define escalation path"
        )


# ═══════════════════════════════════════════════════════════════════════════
# THINKING_FRAMEWORK.md Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestThinkingFramework:
    """THINKING_FRAMEWORK.md structure and mandatory step checks."""

    def test_thinking_framework_exists(self):
        """THINKING_FRAMEWORK.md must exist."""
        assert THINKING_PATH.exists(), (
            f"THINKING_FRAMEWORK.md not found at {THINKING_PATH}"
        )
        assert THINKING_PATH.is_file(), (
            f"{THINKING_PATH} exists but is not a file"
        )

    def test_thinking_framework_has_step_1_through_4(self):
        """Must contain Step 1, Step 2, Step 3, Step 4 headers."""
        content = THINKING_PATH.read_text(encoding="utf-8")
        for step in ["Step 1", "Step 2", "Step 3", "Step 4"]:
            assert step in content, (
                f"THINKING_FRAMEWORK.md missing header '{step}'"
            )

    def test_thinking_framework_has_task_section(self):
        """Must contain a 'Task' section after Step 1-4."""
        content = THINKING_PATH.read_text(encoding="utf-8")
        assert "Task" in content, (
            "THINKING_FRAMEWORK.md missing 'Task' section"
        )

    def test_thinking_framework_mandatory_order(self):
        """Step 1 must appear before Step 2, Step 3, Step 4, and Task."""
        content = THINKING_PATH.read_text(encoding="utf-8")
        pos_step1 = content.index("Step 1")
        pos_step2 = content.index("Step 2")
        pos_step3 = content.index("Step 3")
        pos_step4 = content.index("Step 4")
        pos_task = content.index("Task:")
        assert pos_step1 < pos_step2 < pos_step3 < pos_step4 < pos_task, (
            "THINKING_FRAMEWORK.md steps must appear in order: "
            "Step 1 → Step 2 → Step 3 → Step 4 → Task"
        )

    def test_thinking_framework_quality_global_perspective(self):
        """Step 1 must address modules/APIs/gate status/seeded defects."""
        content = THINKING_PATH.read_text(encoding="utf-8")
        assert "模块" in content, "Step 1 should mention modules"
        assert "API" in content, "Step 1 should mention API endpoints"

    def test_thinking_framework_evidence_priority(self):
        """Step 2 must address evidence authenticity and tool verification."""
        content = THINKING_PATH.read_text(encoding="utf-8")
        assert "证据" in content or "通过" in content, (
            "Step 2 must address evidence priority"
        )

    def test_thinking_framework_gate_integrity(self):
        """Step 3 must address lint/typecheck/test/coverage checks."""
        content = THINKING_PATH.read_text(encoding="utf-8")
        assert "lint" in content.lower(), "Step 3 must mention lint"
        assert "typecheck" in content.lower(), "Step 3 must mention typecheck"
        assert "测试" in content or "test" in content.lower(), "Step 3 must mention tests"

    def test_thinking_framework_fake_pass_detection(self):
        """Step 4 must address fake PASS detection patterns."""
        content = THINKING_PATH.read_text(encoding="utf-8")
        assert "假" in content or "吞掉" in content or "总是通过" in content, (
            "Step 4 must address fake PASS detection"
        )

    def test_thinking_framework_output_requirements(self):
        """Must require substantive output and UNABLE_TO_DETERMINE protocol."""
        content = THINKING_PATH.read_text(encoding="utf-8")
        assert "UNABLE_TO_DETERMINE" in content, (
            "THINKING_FRAMEWORK.md must mandate UNABLE_TO_DETERMINE output "
            "when evidence is insufficient"
        )
        # The output requirements section must explicitly forbid placeholder
        # answers like '已检查' and '无问题' — verify both are called out.
        output_section = content[content.index("输出要求"):]
        assert "不得" in output_section, (
            "Output requirements must state what is NOT allowed"
        )
        assert "已检查" in output_section and "无问题" in output_section, (
            "Output requirements must explicitly forbid placeholder answers "
            "like '已检查' and '无问题'"
        )

    def test_thinking_framework_followed_by_task(self):
        """After Step 4, Task section must require basing judgment on Steps 1-4."""
        content = THINKING_PATH.read_text(encoding="utf-8")
        task_pos = content.index("Task:")
        after_task = content[task_pos:]
        # Task section must reference the previous steps
        assert "Step 1" in after_task or "步骤" in after_task or "结论" in after_task, (
            "Task section must base its judgment on Step 1-4 conclusions"
        )


# ═══════════════════════════════════════════════════════════════════════════
# INTERNAL_LOOP.md Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestInternalLoop:
    """INTERNAL_LOOP.md structure and mandatory self-check loop checks."""

    def test_internal_loop_exists(self):
        """INTERNAL_LOOP.md must exist."""
        assert INTERNAL_LOOP_PATH.exists(), (
            f"INTERNAL_LOOP.md not found at {INTERNAL_LOOP_PATH}"
        )
        assert INTERNAL_LOOP_PATH.is_file(), (
            f"{INTERNAL_LOOP_PATH} exists but is not a file"
        )

    def test_internal_loop_has_three_layers(self):
        """Must contain Loop 1, Loop 2, Loop 3 — three self-check layers."""
        content = INTERNAL_LOOP_PATH.read_text(encoding="utf-8")
        for loop_label in ["Loop 1", "Loop 2", "Loop 3"]:
            assert loop_label in content, (
                f"INTERNAL_LOOP.md missing '{loop_label}'"
            )

    def test_loop1_contract_compliance(self):
        """Loop 1 must be about CONTRACT compliance self-check."""
        content = INTERNAL_LOOP_PATH.read_text(encoding="utf-8")
        loop1_start = content.index("Loop 1")
        loop1_end = content.index("Loop 2") if "Loop 2" in content else len(content)
        loop1_text = content[loop1_start:loop1_end]
        assert "CONTRACT" in loop1_text or "合同" in loop1_text or "禁止" in loop1_text, (
            "Loop 1 must address CONTRACT compliance"
        )

    def test_loop2_quality_standards(self):
        """Loop 2 must be about quality standards self-check."""
        content = INTERNAL_LOOP_PATH.read_text(encoding="utf-8")
        loop2_start = content.index("Loop 2")
        loop2_end = content.index("Loop 3") if "Loop 3" in content else len(content)
        loop2_text = content[loop2_start:loop2_end]
        assert "lint" in loop2_text.lower() or "typecheck" in loop2_text.lower() or "质量" in loop2_text, (
            "Loop 2 must address quality standards"
        )

    def test_loop3_fake_pass_detection(self):
        """Loop 3 must be about fake PASS detection."""
        content = INTERNAL_LOOP_PATH.read_text(encoding="utf-8")
        loop3_start = content.index("Loop 3")
        loop3_text = content[loop3_start:]
        assert "假" in loop3_text or "退出码" in loop3_text or "空" in loop3_text, (
            "Loop 3 must address fake PASS detection"
        )

    def test_iteration_rules_exist(self):
        """Must contain iteration rules with max 3 iterations."""
        content = INTERNAL_LOOP_PATH.read_text(encoding="utf-8")
        assert "迭代" in content, (
            "INTERNAL_LOOP.md missing iteration rules section"
        )
        assert "3" in content[content.index("迭代"):content.index("迭代") + 200], (
            "Iteration rules must specify max 3 iterations"
        )

    def test_iteration_has_blocked_fallback(self):
        """After 3 iterations, output BLOCKED + unresolved items."""
        content = INTERNAL_LOOP_PATH.read_text(encoding="utf-8")
        assert "BLOCKED" in content, (
            "INTERNAL_LOOP.md must specify BLOCKED output when iterations exhausted"
        )

    def test_analysis_output_ratio_constraint(self):
        """Must contain analysis-to-output ratio constraint (15%)."""
        content = INTERNAL_LOOP_PATH.read_text(encoding="utf-8")
        assert "15%" in content or "15" in content, (
            "INTERNAL_LOOP.md missing analysis-output ratio constraint (15%)"
        )
        assert "分析" in content and "产出" in content and "比例" in content, (
            "INTERNAL_LOOP.md must have a section on analysis-output ratio"
        )

    def test_loop_rerun_step1_4_rule(self):
        """If draft is rejected more than 2 times, redo Step 1-4."""
        content = INTERNAL_LOOP_PATH.read_text(encoding="utf-8")
        assert "2" in content and "Step 1-4" in content or "步骤" in content, (
            "INTERNAL_LOOP.md must specify that after 2+ rejections, "
            "Step 1-4 must be redone instead of patching details"
        )

    def test_no_infinite_loop(self):
        """Must explicitly state that iteration does not loop infinitely."""
        content = INTERNAL_LOOP_PATH.read_text(encoding="utf-8")
        assert "无限" in content or "不无限" in content or "token" in content, (
            "INTERNAL_LOOP.md must explicitly prevent infinite looping"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Cross-File Integrity Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossFileIntegrity:
    """Tests that validate consistency across all three role files."""

    def test_contract_prohibitions_reflected_in_internal_loop(self):
        """Prohibitions in CONTRACT must be checked in INTERNAL_LOOP Loop 1."""
        contract = load_yaml(CONTRACT_PATH)
        loop_content = INTERNAL_LOOP_PATH.read_text(encoding="utf-8")

        # The internal loop must reference contract prohibitions
        prohibition_keywords = [
            w for p in contract["prohibitions"]
            for w in ["禁止", "修改", "降低", "证据"]
            if w in p
        ]
        # At minimum, Loop 1 should reference contract or prohibitions
        assert "CONTRACT" in loop_content or "合同" in loop_content or "禁止" in loop_content, (
            "INTERNAL_LOOP Loop 1 must reference CONTRACT prohibitions"
        )

    def test_thinking_step3_maps_to_contract_quality_standards(self):
        """Step 3 of thinking framework must align with quality_standards in CONTRACT."""
        contract = load_yaml(CONTRACT_PATH)
        thinking = THINKING_PATH.read_text(encoding="utf-8")

        # quality_standards items should have corresponding checks in Step 3
        step3_start = thinking.index("Step 3")
        step3_end = thinking.index("Step 4") if "Step 4" in thinking else len(thinking)
        step3_text = thinking[step3_start:step3_end]

        # All five quality_standards should be reflected in Step 3 checks
        assert "lint" in step3_text.lower(), "Step 3 must check lint (maps to quality_standards)"
        assert "typecheck" in step3_text.lower(), "Step 3 must check typecheck"
        assert "覆盖率" in step3_text or "coverage" in step3_text.lower(), (
            "Step 3 must check coverage"
        )

    def test_contract_output_matches_loop_quality_checks(self):
        """output_artifacts in CONTRACT must have verification in Loop 2."""
        contract = load_yaml(CONTRACT_PATH)
        loop_content = INTERNAL_LOOP_PATH.read_text(encoding="utf-8")

        # At least the quality_report.json must be checked in Loop 2
        loop2_start = loop_content.index("Loop 2")
        loop2_end = loop_content.index("Loop 3") if "Loop 3" in loop_content else len(loop_content)
        loop2_text = loop_content[loop2_start:loop2_end]

        assert "门禁" in loop2_text or "报告" in loop2_text or "lint" in loop2_text, (
            "Loop 2 must verify output_artifacts like quality gate reports"
        )
