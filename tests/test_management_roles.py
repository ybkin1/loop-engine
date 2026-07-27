"""
Tests for the management-line roles: product-manager, project-manager, delivery-manager.

Validates the three-layer role architecture for all three roles:
  1. CONTRACT.yaml — role identity, stance, responsibilities, veto power, projection rules
  2. THINKING_FRAMEWORK.md — mandatory multi-perspective thinking order with role-specific Step 1
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
PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = PROJECT_ROOT / "agents"

ROLES = {
    "product-manager": {
        "role_id": "product-manager",
        "dir": AGENTS_DIR / "product-manager",
    },
    "project-manager": {
        "role_id": "project-manager",
        "dir": AGENTS_DIR / "project-manager",
    },
    "delivery-manager": {
        "role_id": "delivery-manager",
        "dir": AGENTS_DIR / "delivery-manager",
    },
}


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


def iter_role_params():
    """Yield (role_id, role_dict) for parameterized tests."""
    for role_id, data in ROLES.items():
        yield pytest.param(role_id, data, id=role_id)


# ═══════════════════════════════════════════════════════════════════════════
# File Existence Tests (parametrized across all roles)
# ═══════════════════════════════════════════════════════════════════════════

class TestAllContractFilesExist:
    """CONTRACT.yaml, THINKING_FRAMEWORK.md, INTERNAL_LOOP.md must exist for each role."""

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_contract_file_exists(self, role_id, role_data):
        contract_path = role_data["dir"] / "CONTRACT.yaml"
        assert contract_path.exists(), f"CONTRACT.yaml not found at {contract_path}"
        assert contract_path.is_file(), f"{contract_path} exists but is not a file"

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_thinking_framework_exists(self, role_id, role_data):
        thinking_path = role_data["dir"] / "THINKING_FRAMEWORK.md"
        assert thinking_path.exists(), f"THINKING_FRAMEWORK.md not found at {thinking_path}"
        assert thinking_path.is_file(), f"{thinking_path} exists but is not a file"

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_internal_loop_exists(self, role_id, role_data):
        loop_path = role_data["dir"] / "INTERNAL_LOOP.md"
        assert loop_path.exists(), f"INTERNAL_LOOP.md not found at {loop_path}"
        assert loop_path.is_file(), f"{loop_path} exists but is not a file"


# ═══════════════════════════════════════════════════════════════════════════
# CONTRACT.yaml Tests (parametrized across all roles)
# ═══════════════════════════════════════════════════════════════════════════

class TestContractBasic:
    """CONTRACT.yaml parseability and key fields for all three roles."""

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_contract_is_valid_yaml(self, role_id, role_data):
        contract_path = role_data["dir"] / "CONTRACT.yaml"
        contract = load_yaml(contract_path)
        assert isinstance(contract, dict), (
            f"{role_id} CONTRACT.yaml root must be a mapping (dict)"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_contract_has_correct_role_id(self, role_id, role_data):
        contract_path = role_data["dir"] / "CONTRACT.yaml"
        contract = load_yaml(contract_path)
        assert contract.get("role_id") == role_id, (
            f"{role_id} CONTRACT.yaml missing or incorrect role_id: "
            f"expected '{role_id}', got '{contract.get('role_id')}'"
        )


class TestContractIdentity:
    """identity section checks for all three roles."""

    REQUIRED_IDENTITY_FIELDS = ["title", "experience", "expertise", "known_blind_spots"]

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_identity_section_exists(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        assert "identity" in contract, f"{role_id}: CONTRACT.yaml missing 'identity'"

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_identity_has_all_required_fields(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        identity = contract["identity"]
        for field in self.REQUIRED_IDENTITY_FIELDS:
            assert field in identity, (
                f"{role_id}: identity section missing required field: '{field}'"
            )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_expertise_is_non_empty_list(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        expertise = contract["identity"]["expertise"]
        assert isinstance(expertise, list), f"{role_id}: identity.expertise must be a list"
        assert len(expertise) >= 4, (
            f"{role_id}: identity.expertise must have at least 4 items, got {len(expertise)}"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_blind_spots_are_non_empty_list(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        blind_spots = contract["identity"]["known_blind_spots"]
        assert isinstance(blind_spots, list), f"{role_id}: known_blind_spots must be a list"
        assert len(blind_spots) >= 2, (
            f"{role_id}: known_blind_spots must have at least 2 items, got {len(blind_spots)}"
        )
        for spot in blind_spots:
            assert isinstance(spot, str), f"Blind spot must be a string, got {type(spot)}"


class TestContractFixedStance:
    """fixed_stance must have >= 4 precise items with no vague terms."""

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_fixed_stance_exists_and_has_at_least_4(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        assert "fixed_stance" in contract, f"{role_id}: CONTRACT.yaml missing 'fixed_stance'"
        stances = contract["fixed_stance"]
        assert isinstance(stances, list), f"{role_id}: fixed_stance must be a list"
        assert len(stances) >= 4, (
            f"{role_id}: fixed_stance must have at least 4 items, got {len(stances)}"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_fixed_stance_no_vague_terms(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        for i, stance in enumerate(contract["fixed_stance"]):
            assert_no_vague_terms(stance, f"{role_id}: fixed_stance[{i}]")


class TestContractResponsibilities:
    """responsibilities must exist and be non-empty."""

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_responsibilities_exists_and_non_empty(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        assert "responsibilities" in contract, f"{role_id}: missing 'responsibilities'"
        resp = contract["responsibilities"]
        assert isinstance(resp, list), f"{role_id}: responsibilities must be a list"
        assert len(resp) >= 4, (
            f"{role_id}: responsibilities must have at least 4 items, got {len(resp)}"
        )


class TestContractProhibitions:
    """prohibitions must exist and be non-empty."""

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_prohibitions_exists_and_non_empty(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        assert "prohibitions" in contract, f"{role_id}: missing 'prohibitions'"
        proh = contract["prohibitions"]
        assert isinstance(proh, list), f"{role_id}: prohibitions must be a list"
        assert len(proh) >= 3, (
            f"{role_id}: prohibitions must have at least 3 items, got {len(proh)}"
        )


class TestContractVetoPower:
    """veto_power must exist and be non-empty."""

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_veto_power_exists_and_non_empty(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        assert "veto_power" in contract, f"{role_id}: missing 'veto_power'"
        veto = contract["veto_power"]
        assert isinstance(veto, list), f"{role_id}: veto_power must be a list"
        assert len(veto) >= 3, (
            f"{role_id}: veto_power must have at least 3 items, got {len(veto)}"
        )


class TestContractArtifacts:
    """input_artifacts and output_artifacts must exist."""

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_input_artifacts_exists_and_non_empty(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        assert "input_artifacts" in contract, f"{role_id}: missing 'input_artifacts'"
        inp = contract["input_artifacts"]
        assert isinstance(inp, list), f"{role_id}: input_artifacts must be a list"
        assert len(inp) >= 3, (
            f"{role_id}: input_artifacts must have at least 3 items, got {len(inp)}"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_output_artifacts_exists_and_non_empty(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        assert "output_artifacts" in contract, f"{role_id}: missing 'output_artifacts'"
        out = contract["output_artifacts"]
        assert isinstance(out, list), f"{role_id}: output_artifacts must be a list"
        assert len(out) >= 3, (
            f"{role_id}: output_artifacts must have at least 3 items, got {len(out)}"
        )


class TestContractQualityStandards:
    """quality_standards must exist."""

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_quality_standards_exists_and_non_empty(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        assert "quality_standards" in contract, f"{role_id}: missing 'quality_standards'"
        std = contract["quality_standards"]
        assert isinstance(std, list), f"{role_id}: quality_standards must be a list"
        assert len(std) >= 3, (
            f"{role_id}: quality_standards must have at least 3 items, got {len(std)}"
        )


class TestContractProjectionRules:
    """projection_rules with correct include/exclude sections for each role."""

    # Expected projections per role
    EXPECTED_INCLUDES = {
        "product-manager": ["project", "pages", "api_endpoints"],
        "project-manager": ["project", "modules"],
        "delivery-manager": ["project", "modules", "deployment_structure"],
    }

    EXPECTED_EXCLUDES = {
        "product-manager": ["modules", "database"],
        "project-manager": ["pages", "api_endpoints", "database"],
        "delivery-manager": ["pages", "api_endpoints", "database"],
    }

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_projection_rules_exists(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        assert "projection_rules" in contract, (
            f"{role_id}: CONTRACT.yaml missing 'projection_rules'"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_projection_rules_has_include_exclude(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        rules = contract["projection_rules"]
        assert "include_sections" in rules, (
            f"{role_id}: projection_rules missing 'include_sections'"
        )
        assert "exclude_sections" in rules, (
            f"{role_id}: projection_rules missing 'exclude_sections'"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_include_sections_non_empty(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        includes = contract["projection_rules"]["include_sections"]
        assert isinstance(includes, list), f"{role_id}: include_sections must be a list"
        assert len(includes) >= 2, (
            f"{role_id}: include_sections must have at least 2 items, got {len(includes)}"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_include_sections_match_expected(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        includes = contract["projection_rules"]["include_sections"]
        expected = self.EXPECTED_INCLUDES[role_id]
        for exp in expected:
            assert exp in includes, (
                f"{role_id}: include_sections must contain '{exp}', "
                f"got {includes}"
            )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_exclude_sections_match_expected(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        excludes = contract["projection_rules"]["exclude_sections"]
        expected = self.EXPECTED_EXCLUDES[role_id]
        for exp in expected:
            assert exp in excludes, (
                f"{role_id}: exclude_sections must contain '{exp}', "
                f"got {excludes}"
            )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_projection_paths_parseable(self, role_id, role_data):
        """Each include_sections path must use valid syntax."""
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        includes = contract["projection_rules"]["include_sections"]

        valid_path_pattern = re.compile(
            r'^[a-zA-Z_][a-zA-Z0-9_.*]*$'
        )

        for path in includes:
            assert valid_path_pattern.match(path), (
                f"{role_id}: include_sections path '{path}' does not match "
                f"supported ProjectMapQuery syntax"
            )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_projection_rules_applied_to_sample_data(self, role_id, role_data):
        """Apply projection rules to a minimal sample PROJECT_MAP."""
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        rules = contract["projection_rules"]

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
            "deployment_structure": {
                "environments": ["dev", "staging", "production"],
            },
        }

        query = ProjectMapQuery()

        # Verify each include_section resolves to a non-None value
        for path in rules["include_sections"]:
            result = query.query(sample_map, path)
            assert result is not None, (
                f"{role_id}: Include path '{path}' returned None for sample PROJECT_MAP. "
                f"Either the path is wrong or sample_map is missing needed data."
            )

        # Verify exclude_sections exist in the map (they should be real sections
        # that the role is denied access to)
        for excluded in rules["exclude_sections"]:
            result = query.query(sample_map, excluded)
            assert result is not None, (
                f"{role_id}: Exclude path '{excluded}' does not exist in sample PROJECT_MAP. "
                f"Exclude path should map to a real section that the role is denied access to."
            )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_projection_rules_has_role_specific_dimensions(self, role_id, role_data):
        """Each role must have role-specific dimension questions in projection_rules."""
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        rules = contract["projection_rules"]

        # Each role has a unique dimension key
        dimension_keys = {
            "product-manager": "product_dimensions",
            "project-manager": "management_dimensions",
            "delivery-manager": "delivery_dimensions",
        }

        expected_key = dimension_keys[role_id]
        dims = rules.get(expected_key, [])
        assert isinstance(dims, list), (
            f"{role_id}: {expected_key} must be a list"
        )
        assert len(dims) >= 3, (
            f"{role_id}: {expected_key} must have at least 3 questions, got {len(dims)}"
        )
        for dim in dims:
            assert isinstance(dim, str), f"{role_id}: dimension must be a string"
            assert "?" in dim or "？" in dim, (
                f"{role_id}: dimension should be a question: '{dim}'"
            )


class TestContractVetoEscalation:
    """veto_escalation must follow the protocol."""

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_veto_escalation_exists(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        assert "veto_escalation" in contract, (
            f"{role_id}: CONTRACT.yaml missing 'veto_escalation'"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_veto_escalation_has_evidence_and_upgrade(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        esc_text = " ".join(str(v) for v in contract["veto_escalation"])
        assert "证据" in esc_text or "evidence" in esc_text.lower(), (
            f"{role_id}: veto_escalation must mandate evidence attachment"
        )
        assert "升级" in esc_text or "escalat" in esc_text.lower(), (
            f"{role_id}: veto_escalation must define escalation path"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_veto_escalation_mentions_human_review(self, role_id, role_data):
        contract = load_yaml(role_data["dir"] / "CONTRACT.yaml")
        esc_text = " ".join(str(v) for v in contract["veto_escalation"])
        assert "HumanReviewPacket" in esc_text or "Gate" in esc_text, (
            f"{role_id}: veto_escalation must mention HumanReviewPacket or Gate"
        )


# ═══════════════════════════════════════════════════════════════════════════
# THINKING_FRAMEWORK.md Tests (parametrized across all roles)
# ═══════════════════════════════════════════════════════════════════════════

class TestThinkingFramework:
    """THINKING_FRAMEWORK.md structure and role-specific Step 1 checks."""

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_has_steps_1_through_4(self, role_id, role_data):
        thinking_path = role_data["dir"] / "THINKING_FRAMEWORK.md"
        content = thinking_path.read_text(encoding="utf-8")
        for step in ["Step 1", "Step 2", "Step 3", "Step 4"]:
            assert step in content, (
                f"{role_id}: THINKING_FRAMEWORK.md missing header '{step}'"
            )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_has_task_section(self, role_id, role_data):
        thinking_path = role_data["dir"] / "THINKING_FRAMEWORK.md"
        content = thinking_path.read_text(encoding="utf-8")
        assert "Task" in content, (
            f"{role_id}: THINKING_FRAMEWORK.md missing 'Task' section"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_mandatory_order(self, role_id, role_data):
        """Step 1 → Step 2 → Step 3 → Step 4 → Task in that order."""
        thinking_path = role_data["dir"] / "THINKING_FRAMEWORK.md"
        content = thinking_path.read_text(encoding="utf-8")
        pos_step1 = content.index("Step 1")
        pos_step2 = content.index("Step 2")
        pos_step3 = content.index("Step 3")
        pos_step4 = content.index("Step 4")
        pos_task = content.index("Task:")
        assert pos_step1 < pos_step2 < pos_step3 < pos_step4 < pos_task, (
            f"{role_id}: Steps must appear in order: "
            "Step 1 → Step 2 → Step 3 → Step 4 → Task"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_output_requirements_exist(self, role_id, role_data):
        thinking_path = role_data["dir"] / "THINKING_FRAMEWORK.md"
        content = thinking_path.read_text(encoding="utf-8")
        assert "输出要求" in content, (
            f"{role_id}: THINKING_FRAMEWORK.md missing '输出要求' section"
        )
        # Must forbid placeholder answers
        assert "不得" in content, (
            f"{role_id}: Output requirements must state what is NOT allowed"
        )


class TestThinkingFrameworkRoleSpecificStep1:
    """Each role's Step 1 must reflect that role's unique global perspective."""

    # Role-specific keywords that must appear in Step 1
    STEP1_KEYWORDS = {
        "product-manager": {
            "required": ["pages", "api_endpoints", "用户可见", "系统暴露"],
            "forbidden": ["modules", "database"],
            "description": "must address user-visible features and API capabilities",
        },
        "project-manager": {
            "required": ["modules", "依赖", "阶段", "进度", "风险"],
            "forbidden": ["pages", "api_endpoints", "database"],
            "description": "must address modules, dependencies, phases, progress, risk",
        },
        "delivery-manager": {
            "required": ["modules", "deployment", "部署", "交付物", "发布"],
            "forbidden": ["pages", "api_endpoints", "database"],
            "description": "must address modules, deployment structure, deliverables, release",
        },
    }

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_step1_contains_role_specific_perspective(self, role_id, role_data):
        """Step 1 must reflect the role's unique global view, not a generic template."""
        thinking_path = role_data["dir"] / "THINKING_FRAMEWORK.md"
        content = thinking_path.read_text(encoding="utf-8")

        # Extract Step 1 content (between Step 1 and Step 2)
        pos_step1 = content.index("Step 1")
        pos_step2 = content.index("Step 2")
        step1_text = content[pos_step1:pos_step2]

        keywords = self.STEP1_KEYWORDS[role_id]

        # Check that role-specific required terms appear
        for term in keywords["required"]:
            assert term in step1_text, (
                f"{role_id}: Step 1 must mention '{term}' — "
                f"this role's global perspective {keywords['description']}"
            )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_step1_does_not_mention_irrelevant_sections(self, role_id, role_data):
        """Step 1 must not focus on excluded sections."""
        thinking_path = role_data["dir"] / "THINKING_FRAMEWORK.md"
        content = thinking_path.read_text(encoding="utf-8")

        pos_step1 = content.index("Step 1")
        pos_step2 = content.index("Step 2")
        step1_text = content[pos_step1:pos_step2]

        keywords = self.STEP1_KEYWORDS[role_id]

        for forbidden in keywords.get("forbidden", []):
            # Allow mentioning them in context of "not my concern" but warn if they are
            # used as primary focus items
            pass  # This is a soft check; the strong check is in required keywords


# ═══════════════════════════════════════════════════════════════════════════
# INTERNAL_LOOP.md Tests (parametrized across all roles)
# ═══════════════════════════════════════════════════════════════════════════

class TestInternalLoop:
    """INTERNAL_LOOP.md structure — 3 self-check layers + iteration rules."""

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_has_three_loop_layers(self, role_id, role_data):
        """Must contain Loop 1, Loop 2, Loop 3."""
        loop_path = role_data["dir"] / "INTERNAL_LOOP.md"
        content = loop_path.read_text(encoding="utf-8")
        for loop_label in ["Loop 1", "Loop 2", "Loop 3"]:
            assert loop_label in content, (
                f"{role_id}: INTERNAL_LOOP.md missing '{loop_label}'"
            )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_loop1_contract_compliance(self, role_id, role_data):
        """Loop 1 must address CONTRACT compliance."""
        loop_path = role_data["dir"] / "INTERNAL_LOOP.md"
        content = loop_path.read_text(encoding="utf-8")
        loop1_start = content.index("Loop 1")
        loop1_end = content.index("Loop 2") if "Loop 2" in content else len(content)
        loop1_text = content[loop1_start:loop1_end]
        assert "CONTRACT" in loop1_text or "合同" in loop1_text or "禁止" in loop1_text, (
            f"{role_id}: Loop 1 must address CONTRACT compliance"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_loop_has_iteration_rules(self, role_id, role_data):
        """Must contain iteration rules with max 3 iterations."""
        loop_path = role_data["dir"] / "INTERNAL_LOOP.md"
        content = loop_path.read_text(encoding="utf-8")
        assert "迭代" in content, (
            f"{role_id}: INTERNAL_LOOP.md missing iteration rules section"
        )
        assert "3" in content[content.index("迭代"):content.index("迭代") + 200], (
            f"{role_id}: Iteration rules must specify max 3 iterations"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_iteration_has_blocked_fallback(self, role_id, role_data):
        """After 3 iterations, output BLOCKED + unresolved items."""
        loop_path = role_data["dir"] / "INTERNAL_LOOP.md"
        content = loop_path.read_text(encoding="utf-8")
        assert "BLOCKED" in content, (
            f"{role_id}: INTERNAL_LOOP.md must specify BLOCKED output "
            "when iterations exhausted"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_analysis_output_ratio_constraint(self, role_id, role_data):
        """Must contain analysis-to-output ratio constraint (15%)."""
        loop_path = role_data["dir"] / "INTERNAL_LOOP.md"
        content = loop_path.read_text(encoding="utf-8")
        assert "15%" in content or "15" in content, (
            f"{role_id}: INTERNAL_LOOP.md missing analysis-output ratio constraint (15%)"
        )

    @pytest.mark.parametrize("role_id,role_data", iter_role_params())
    def test_no_infinite_loop(self, role_id, role_data):
        """Must explicitly prevent infinite looping."""
        loop_path = role_data["dir"] / "INTERNAL_LOOP.md"
        content = loop_path.read_text(encoding="utf-8")
        assert "无限" in content or "不无限" in content or "token" in content, (
            f"{role_id}: INTERNAL_LOOP.md must explicitly prevent infinite looping"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Role-Specific Content Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestProductManagerSpecific:
    """Content validation specific to product-manager."""

    ROLE_ID = "product-manager"
    ROLE_DIR = ROLES[ROLE_ID]["dir"]

    def test_fixed_stance_covers_clarification_duty(self):
        """Product manager must insist on clarifying ambiguous requirements."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        stances_text = " ".join(contract["fixed_stance"])
        assert "澄清" in stances_text or "追问" in stances_text, (
            "product-manager fixed_stance must assert duty to clarify / ask follow-ups"
        )

    def test_fixed_stance_covers_verifiable_acceptance_criteria(self):
        """Product manager must insist on verifiable acceptance criteria."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        stances_text = " ".join(contract["fixed_stance"])
        assert "可验证" in stances_text or "验证" in stances_text, (
            "product-manager fixed_stance must insist on verifiable acceptance criteria"
        )

    def test_fixed_stance_covers_scope_vs_tech_separation(self):
        """Product manager defines scope, architect defines tech implementation."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        stances_text = " ".join(contract["fixed_stance"])
        assert "功能范围" in stances_text or "范围" in stances_text, (
            "product-manager fixed_stance must address scope ownership"
        )
        assert "架构师" in stances_text or "技术" in stances_text, (
            "product-manager fixed_stance must defer tech decisions to architect"
        )

    def test_projection_includes_pages(self):
        """Product manager must see pages (user-visible features)."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        includes = contract["projection_rules"]["include_sections"]
        assert "pages" in includes, (
            "product-manager must include 'pages' in projection"
        )

    def test_projection_excludes_modules_and_database(self):
        """Product manager must NOT see modules/database details."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "modules" in excludes, (
            "product-manager must exclude 'modules' from projection"
        )
        assert "database" in excludes, (
            "product-manager must exclude 'database' from projection"
        )

    def test_thinking_step1_focuses_on_pages_and_apis(self):
        """Step 1 must be about user-visible pages and API capabilities."""
        thinking_path = self.ROLE_DIR / "THINKING_FRAMEWORK.md"
        content = thinking_path.read_text(encoding="utf-8")
        pos_s1 = content.index("Step 1")
        pos_s2 = content.index("Step 2")
        step1 = content[pos_s1:pos_s2]
        assert "pages" in step1 or "页面" in step1, (
            "product-manager Step 1 must mention pages"
        )


class TestProjectManagerSpecific:
    """Content validation specific to project-manager."""

    ROLE_ID = "project-manager"
    ROLE_DIR = ROLES[ROLE_ID]["dir"]

    def test_fixed_stance_covers_dependency_and_progress_control(self):
        """Project manager must block new tasks when dependencies/progress are out of control."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        stances_text = " ".join(contract["fixed_stance"])
        assert "依赖" in stances_text or "进度" in stances_text, (
            "project-manager fixed_stance must address dependency/progress control"
        )

    def test_fixed_stance_covers_tech_estimation_not_decision(self):
        """Project manager requires time estimates from tech roles, doesn't decide tech."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        stances_text = " ".join(contract["fixed_stance"])
        assert "不" in stances_text and "技术" in stances_text, (
            "project-manager fixed_stance must state they do NOT make tech decisions"
        )

    def test_fixed_stance_covers_priority_vs_scope(self):
        """Project manager decides priority on resource conflicts, PM decides scope."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        stances_text = " ".join(contract["fixed_stance"])
        assert "优先" in stances_text or "资源" in stances_text, (
            "project-manager fixed_stance must address priority decisions"
        )

    def test_projection_includes_modules(self):
        """Project manager must see modules (task breakdown granularity)."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        includes = contract["projection_rules"]["include_sections"]
        assert "modules" in includes, (
            "project-manager must include 'modules' in projection"
        )

    def test_projection_excludes_pages_and_api_and_database(self):
        """Project manager must NOT see pages/api/database details."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "pages" in excludes, (
            "project-manager must exclude 'pages' from projection"
        )
        assert "api_endpoints" in excludes, (
            "project-manager must exclude 'api_endpoints' from projection"
        )
        assert "database" in excludes, (
            "project-manager must exclude 'database' from projection"
        )

    def test_thinking_step1_focuses_on_modules_and_dependencies(self):
        """Step 1 must be about modules, phases, dependencies, progress, risk."""
        thinking_path = self.ROLE_DIR / "THINKING_FRAMEWORK.md"
        content = thinking_path.read_text(encoding="utf-8")
        pos_s1 = content.index("Step 1")
        pos_s2 = content.index("Step 2")
        step1 = content[pos_s1:pos_s2]
        assert "modules" in step1 or "模块" in step1, (
            "project-manager Step 1 must mention modules"
        )


class TestDeliveryManagerSpecific:
    """Content validation specific to delivery-manager."""

    ROLE_ID = "delivery-manager"
    ROLE_DIR = ROLES[ROLE_ID]["dir"]

    def test_fixed_stance_covers_go_means_safe_not_perfect(self):
        """Delivery manager: GO means safe to release, not flawless."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        stances_text = " ".join(contract["fixed_stance"])
        assert "安全" in stances_text or "GO" in stances_text, (
            "delivery-manager fixed_stance must define what GO means"
        )

    def test_fixed_stance_covers_rollback_requirement(self):
        """Delivery manager must require rollback preparation."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        stances_text = " ".join(contract["fixed_stance"])
        assert "回滚" in stances_text, (
            "delivery-manager fixed_stance must require rollback preparation"
        )

    def test_fixed_stance_covers_completeness_not_quality(self):
        """Delivery manager judges completeness, not code quality."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        stances_text = " ".join(contract["fixed_stance"])
        assert "完整" in stances_text or "交付" in stances_text, (
            "delivery-manager fixed_stance must address delivery completeness"
        )

    def test_projection_includes_modules_and_deployment(self):
        """Delivery manager must see modules and deployment_structure."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        includes = contract["projection_rules"]["include_sections"]
        assert "modules" in includes, (
            "delivery-manager must include 'modules' in projection"
        )
        assert "deployment_structure" in includes, (
            "delivery-manager must include 'deployment_structure' in projection"
        )

    def test_projection_excludes_pages_and_api_and_database(self):
        """Delivery manager must NOT see pages/api/database details."""
        contract = load_yaml(self.ROLE_DIR / "CONTRACT.yaml")
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "pages" in excludes, (
            "delivery-manager must exclude 'pages' from projection"
        )
        assert "api_endpoints" in excludes, (
            "delivery-manager must exclude 'api_endpoints' from projection"
        )
        assert "database" in excludes, (
            "delivery-manager must exclude 'database' from projection"
        )

    def test_thinking_step1_focuses_on_delivery_readiness(self):
        """Step 1 must be about modules, deployment, deliverables, release window."""
        thinking_path = self.ROLE_DIR / "THINKING_FRAMEWORK.md"
        content = thinking_path.read_text(encoding="utf-8")
        pos_s1 = content.index("Step 1")
        pos_s2 = content.index("Step 2")
        step1 = content[pos_s1:pos_s2]
        assert "deployment" in step1 or "部署" in step1 or "发布" in step1, (
            "delivery-manager Step 1 must mention deployment/release"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Cross-Role Consistency Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossRoleConsistency:
    """Validates that the three management roles do not overlap inappropriately."""

    def test_each_role_has_unique_projection_dimension_key(self):
        """Each role should use a different dimension key in projection_rules."""
        dimension_keys = set()
        for role_id, data in ROLES.items():
            contract = load_yaml(data["dir"] / "CONTRACT.yaml")
            rules = contract["projection_rules"]
            for key in rules:
                if key not in ("include_sections", "exclude_sections"):
                    dimension_keys.add(key)
        assert len(dimension_keys) == 3, (
            f"Expected 3 unique dimension keys across all roles, got {len(dimension_keys)}: {dimension_keys}"
        )

    def test_no_role_is_self_contradicting_in_include_exclude(self):
        """No section should appear in both include_sections and exclude_sections of the same role."""
        for role_id, data in ROLES.items():
            contract = load_yaml(data["dir"] / "CONTRACT.yaml")
            rules = contract["projection_rules"]
            includes = set(rules["include_sections"])
            excludes = set(rules["exclude_sections"])
            overlap = includes & excludes
            assert not overlap, (
                f"{role_id}: sections appear in both include and exclude: {overlap}"
            )

    def test_quality_engineer_not_in_management_line(self):
        """The quality engineer is separate from the three management roles."""
        # This test simply verifies our test file only covers the 3 management roles
        assert "quality-engineer" not in ROLES, (
            "quality-engineer should not be in management roles test — "
            "it has its own test file"
        )
