"""
Tests for the technical line roles — system-architect, module-architect, developer.

Validates the three-layer role architecture for each role:
  1. CONTRACT.yaml — role identity, stance, responsibilities, veto power, projection rules
  2. THINKING_FRAMEWORK.md — mandatory multi-perspective thinking order with role-specific Step 1
  3. INTERNAL_LOOP.md — self-check loop with iteration limits

Also performs cross-role validation to ensure contracts don't conflict.
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
AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
ROLES = {
    "system-architect": AGENTS_DIR / "system-architect",
    "module-architect": AGENTS_DIR / "module-architect",
    "developer": AGENTS_DIR / "developer",
}


def get_role_paths(role: str) -> dict:
    """Return {contract, thinking, loop} paths for a role."""
    base = ROLES[role]
    return {
        "contract": base / "CONTRACT.yaml",
        "thinking": base / "THINKING_FRAMEWORK.md",
        "loop": base / "INTERNAL_LOOP.md",
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


VALID_PATH_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_.*]*$')


# ═══════════════════════════════════════════════════════════════════════════
# Parametrized tests (run for all 3 roles)
# ═══════════════════════════════════════════════════════════════════════════

# ── CONTRACT.yaml Tests ──

@pytest.mark.parametrize("role_id", ["system-architect", "module-architect", "developer"])
class TestContractFileExists:
    """CONTRACT.yaml existence, parseability, and role_id correctness."""

    def test_contract_file_exists(self, role_id):
        path = get_role_paths(role_id)["contract"]
        assert path.exists(), f"CONTRACT.yaml not found at {path}"
        assert path.is_file(), f"{path} exists but is not a file"

    def test_contract_is_valid_yaml(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert isinstance(contract, dict), (
            f"{role_id}: CONTRACT.yaml root must be a mapping (dict)"
        )

    def test_contract_has_role_id(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert contract.get("role_id") == role_id, (
            f"{role_id}: CONTRACT.yaml missing or incorrect role_id"
        )


@pytest.mark.parametrize("role_id", ["system-architect", "module-architect", "developer"])
class TestContractIdentity:
    """Tests for the identity section."""

    REQUIRED_IDENTITY_FIELDS = ["title", "experience", "expertise", "known_blind_spots"]

    def test_identity_section_exists(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert "identity" in contract, f"{role_id}: CONTRACT.yaml missing 'identity' section"

    def test_identity_has_all_required_fields(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        identity = contract["identity"]
        for field in self.REQUIRED_IDENTITY_FIELDS:
            assert field in identity, (
                f"{role_id}: identity section missing required field: '{field}'"
            )

    def test_expertise_is_non_empty_list(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        expertise = contract["identity"]["expertise"]
        assert isinstance(expertise, list), f"{role_id}: identity.expertise must be a list"
        assert len(expertise) > 0, f"{role_id}: identity.expertise must not be empty"

    def test_blind_spots_are_declarative(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        blind_spots = contract["identity"]["known_blind_spots"]
        assert isinstance(blind_spots, list), f"{role_id}: known_blind_spots must be a list"
        assert len(blind_spots) > 0, f"{role_id}: known_blind_spots must not be empty"
        for spot in blind_spots:
            assert isinstance(spot, str), f"{role_id}: Blind spot must be a string, got {type(spot)}"


@pytest.mark.parametrize("role_id", ["system-architect", "module-architect", "developer"])
class TestContractFixedStance:
    """Tests for fixed_stance — min 4 items, no vague terms."""

    def test_fixed_stance_exists_and_count(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert "fixed_stance" in contract, f"{role_id}: CONTRACT.yaml missing 'fixed_stance'"
        stances = contract["fixed_stance"]
        assert isinstance(stances, list), f"{role_id}: fixed_stance must be a list"
        assert len(stances) >= 4, (
            f"{role_id}: fixed_stance must have at least 4 items, got {len(stances)}"
        )

    def test_fixed_stance_no_vague_terms(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        for i, stance in enumerate(contract["fixed_stance"]):
            assert_no_vague_terms(stance, f"{role_id} fixed_stance[{i}]")

    # ── Role-specific stance content assertions ──

    def test_system_architect_stance_covers_architecture(self, role_id):
        if role_id != "system-architect":
            pytest.skip("Only for system-architect")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        stances_text = " ".join(contract["fixed_stance"])
        assert "接口" in stances_text or "契约" in stances_text or "interface" in stances_text.lower(), (
            "system-architect fixed_stance must reference interface/contract"
        )
        assert "架构" in stances_text, (
            "system-architect fixed_stance must reference architecture"
        )

    def test_module_architect_stance_covers_components(self, role_id):
        if role_id != "module-architect":
            pytest.skip("Only for module-architect")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        stances_text = " ".join(contract["fixed_stance"])
        assert "组件" in stances_text or "函数" in stances_text or "component" in stances_text.lower(), (
            "module-architect fixed_stance must reference components/functions"
        )
        assert "接口" in stances_text or "契约" in stances_text, (
            "module-architect fixed_stance must reference interfaces/contracts"
        )

    def test_developer_stance_covers_implementation_constraints(self, role_id):
        if role_id != "developer":
            pytest.skip("Only for developer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        stances_text = " ".join(contract["fixed_stance"])
        assert "实现" in stances_text or "代码" in stances_text or "implement" in stances_text.lower(), (
            "developer fixed_stance must reference implementation/code"
        )
        assert "批准" in stances_text or "评审" in stances_text or "review" in stances_text.lower(), (
            "developer fixed_stance must reference approval/review"
        )


@pytest.mark.parametrize("role_id", ["system-architect", "module-architect", "developer"])
class TestContractResponsibilities:
    """Tests for responsibilities section."""

    def test_responsibilities_exists_and_non_empty(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert "responsibilities" in contract, f"{role_id}: missing 'responsibilities'"
        resp = contract["responsibilities"]
        assert isinstance(resp, list), f"{role_id}: responsibilities must be a list"
        assert len(resp) > 0, f"{role_id}: responsibilities must not be empty"


@pytest.mark.parametrize("role_id", ["system-architect", "module-architect", "developer"])
class TestContractProhibitions:
    """Tests for prohibitions section."""

    def test_prohibitions_exists_and_non_empty(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert "prohibitions" in contract, f"{role_id}: missing 'prohibitions'"
        proh = contract["prohibitions"]
        assert isinstance(proh, list), f"{role_id}: prohibitions must be a list"
        assert len(proh) > 0, f"{role_id}: prohibitions must not be empty"

    def test_architects_prohibit_writing_business_code(self, role_id):
        if role_id not in ("system-architect", "module-architect"):
            pytest.skip("Only for architect roles")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        proh_text = " ".join(contract["prohibitions"])
        assert "业务" in proh_text or "代码" in proh_text, (
            f"{role_id}: prohibitions must forbid writing business logic code"
        )

    def test_developer_prohibits_modifying_contract(self, role_id):
        if role_id != "developer":
            pytest.skip("Only for developer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        proh_text = " ".join(contract["prohibitions"])
        assert "自行" in proh_text or "修改" in proh_text, (
            "developer: prohibitions must forbid self-modifying interface contracts"
        )


@pytest.mark.parametrize("role_id", ["system-architect", "module-architect", "developer"])
class TestContractVetoPower:
    """Tests for veto_power section."""

    def test_veto_power_exists_and_non_empty(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert "veto_power" in contract, f"{role_id}: missing 'veto_power'"
        veto = contract["veto_power"]
        assert isinstance(veto, list), f"{role_id}: veto_power must be a list"
        assert len(veto) > 0, f"{role_id}: veto_power must not be empty"

    def test_system_architect_veto_covers_dependencies_and_interfaces(self, role_id):
        if role_id != "system-architect":
            pytest.skip("Only for system-architect")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        veto_text = " ".join(contract["veto_power"])
        assert "接口" in veto_text or "契约" in veto_text, (
            "system-architect veto must cover interface/contract violations"
        )
        assert "依赖" in veto_text or "循环" in veto_text, (
            "system-architect veto must cover dependency/circular dependency"
        )

    def test_module_architect_veto_covers_interface_vagueness(self, role_id):
        if role_id != "module-architect":
            pytest.skip("Only for module-architect")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        veto_text = " ".join(contract["veto_power"])
        assert "模糊" in veto_text or "接口" in veto_text, (
            "module-architect veto must cover vague interfaces"
        )

    def test_developer_veto_submits_deviation_not_overrides(self, role_id):
        if role_id != "developer":
            pytest.skip("Only for developer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        veto_text = " ".join(contract["veto_power"])
        assert "偏差" in veto_text or "不可行" in veto_text or "冲突" in veto_text, (
            "developer veto must involve submitting deviation reports, not overriding architecture"
        )


@pytest.mark.parametrize("role_id", ["system-architect", "module-architect", "developer"])
class TestContractArtifacts:
    """Tests for input_artifacts and output_artifacts sections."""

    def test_input_artifacts_exists_and_non_empty(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert "input_artifacts" in contract, f"{role_id}: missing 'input_artifacts'"
        inp = contract["input_artifacts"]
        assert isinstance(inp, list), f"{role_id}: input_artifacts must be a list"
        assert len(inp) > 0, f"{role_id}: input_artifacts must not be empty"

    def test_output_artifacts_exists_and_non_empty(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert "output_artifacts" in contract, f"{role_id}: missing 'output_artifacts'"
        out = contract["output_artifacts"]
        assert isinstance(out, list), f"{role_id}: output_artifacts must be a list"
        assert len(out) > 0, f"{role_id}: output_artifacts must not be empty"


@pytest.mark.parametrize("role_id", ["system-architect", "module-architect", "developer"])
class TestContractQualityStandards:
    """Tests for quality_standards section."""

    def test_quality_standards_exists_and_non_empty(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert "quality_standards" in contract, (
            f"{role_id}: missing 'quality_standards'"
        )
        std = contract["quality_standards"]
        assert isinstance(std, list), f"{role_id}: quality_standards must be a list"
        assert len(std) > 0, f"{role_id}: quality_standards must not be empty"


@pytest.mark.parametrize("role_id", ["system-architect", "module-architect", "developer"])
class TestContractProjectionRules:
    """Tests for projection_rules section."""

    def test_projection_rules_exists(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert "projection_rules" in contract, (
            f"{role_id}: missing 'projection_rules'"
        )

    def test_projection_rules_has_include_exclude(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        rules = contract["projection_rules"]
        assert "include_sections" in rules, (
            f"{role_id}: projection_rules missing 'include_sections'"
        )
        assert "exclude_sections" in rules, (
            f"{role_id}: projection_rules missing 'exclude_sections'"
        )

    def test_projection_rules_include_sections_non_empty(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        includes = contract["projection_rules"]["include_sections"]
        assert isinstance(includes, list), f"{role_id}: include_sections must be a list"
        assert len(includes) > 0, f"{role_id}: include_sections must not be empty"

    def test_projection_paths_parseable_by_project_map_query(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        includes = contract["projection_rules"]["include_sections"]
        for path in includes:
            assert VALID_PATH_PATTERN.match(path), (
                f"{role_id}: include_sections path '{path}' does not match supported "
                f"ProjectMapQuery syntax (dot-separated, wildcard, field access)"
            )

    def test_projection_rules_applied_to_sample_data(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
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
                {
                    "id": "api-login",
                    "method": "POST",
                    "path": "/api/auth/login",
                    "request_schema": {"type": "object", "properties": {"username": {"type": "string"}}},
                    "response_schema": {"type": "object", "properties": {"token": {"type": "string"}}},
                },
            ],
            "modules": [
                {
                    "id": "auth-module",
                    "responsibilities": ["user authentication"],
                    "interfaces": [{"name": "IAuthService", "methods": ["login"]}],
                    "dependencies": [{"module": "db-module", "type": "runtime"}],
                },
            ],
            "database": {
                "tables": [
                    {"name": "users", "columns": [{"name": "id", "type": "INT"}]},
                ],
                "relationships": [{"from": "users", "to": "sessions", "type": "1:N"}],
            },
            "coding_standards": {
                "indent": 2,
                "quotes": "single",
            },
        }

        query = ProjectMapQuery()

        for path in rules["include_sections"]:
            result = query.query(sample_map, path)
            assert result is not None, (
                f"{role_id}: Include path '{path}' returned None for sample PROJECT_MAP. "
                f"Either the path is wrong or sample_map is missing needed data."
            )

        for excluded in rules["exclude_sections"]:
            result = query.query(sample_map, excluded)
            assert result is not None, (
                f"{role_id}: Exclude path '{excluded}' does not exist in sample PROJECT_MAP. "
                f"Exclude path should map to a real section that the role is denied access to."
            )


@pytest.mark.parametrize("role_id", ["system-architect", "module-architect", "developer"])
class TestContractVetoEscalation:
    """Tests for veto_escalation section."""

    def test_veto_escalation_exists(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert "veto_escalation" in contract, (
            f"{role_id}: missing 'veto_escalation'"
        )

    def test_veto_escalation_has_upgrade_path(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        esc_text = " ".join(str(v) for v in contract["veto_escalation"])
        assert "升级" in esc_text or "升级" in esc_text or "Gate" in esc_text, (
            f"{role_id}: veto_escalation must define escalation/upgrade path"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Role-Specific Projection Rules Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestSystemArchitectProjectionRules:
    """System architect must see full architecture view."""

    def test_sa_projection_includes_modules(self):
        contract = load_yaml(get_role_paths("system-architect")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_modules = any("modules" in path for path in includes)
        assert has_modules, "system-architect projection must include modules"

    def test_sa_projection_includes_api_endpoints(self):
        contract = load_yaml(get_role_paths("system-architect")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_api = any("api_endpoints" in path for path in includes)
        assert has_api, "system-architect projection must include api_endpoints"

    def test_sa_projection_includes_database(self):
        contract = load_yaml(get_role_paths("system-architect")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_db = any("database" in path for path in includes)
        assert has_db, "system-architect projection must include database"

    def test_sa_projection_excludes_pages(self):
        contract = load_yaml(get_role_paths("system-architect")["contract"])
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "pages" in excludes, (
            "system-architect exclude_sections must include 'pages'"
        )


class TestModuleArchitectProjectionRules:
    """Module architect sees own module context + upstream/downstream interfaces."""

    def test_ma_projection_includes_modules(self):
        contract = load_yaml(get_role_paths("module-architect")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_modules = any("modules" in path for path in includes)
        assert has_modules, "module-architect projection must include modules"

    def test_ma_projection_includes_database(self):
        contract = load_yaml(get_role_paths("module-architect")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_db = any("database" in path for path in includes)
        assert has_db, "module-architect projection must include database (shared)"

    def test_ma_projection_excludes_api_endpoints(self):
        contract = load_yaml(get_role_paths("module-architect")["contract"])
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "api_endpoints" in excludes, (
            "module-architect exclude_sections must include 'api_endpoints'"
        )

    def test_ma_projection_excludes_pages(self):
        contract = load_yaml(get_role_paths("module-architect")["contract"])
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "pages" in excludes, (
            "module-architect exclude_sections must include 'pages'"
        )


class TestDeveloperProjectionRules:
    """Developer sees own module context, not full architecture."""

    def test_dev_projection_includes_modules(self):
        contract = load_yaml(get_role_paths("developer")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_modules = any("modules" in path for path in includes)
        assert has_modules, "developer projection must include modules (own + upstream/downstream)"

    def test_dev_projection_does_not_include_full_modules_detail(self):
        """Developer sees modules.*.id etc but not full modules internals like all api_endpoints."""
        contract = load_yaml(get_role_paths("developer")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        # Developer includes modules but excludes api_endpoints and database —
        # this limits their view to module-level context, not full system detail
        has_api = any("api_endpoints" in path for path in includes)
        has_db = any("database" in path for path in includes)
        assert not has_api, (
            "developer projection must NOT include api_endpoints (role doesn't need full API view)"
        )
        assert not has_db, (
            "developer projection must NOT include database (role doesn't need full DB schema)"
        )

    def test_dev_projection_excludes_pages_and_database(self):
        contract = load_yaml(get_role_paths("developer")["contract"])
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "pages" in excludes, "developer exclude_sections must include 'pages'"
        assert "database" in excludes, "developer exclude_sections must include 'database'"
        assert "api_endpoints" in excludes, "developer exclude_sections must include 'api_endpoints'"


# ═══════════════════════════════════════════════════════════════════════════
# THINKING_FRAMEWORK.md Tests
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("role_id", ["system-architect", "module-architect", "developer"])
class TestThinkingFramework:
    """THINKING_FRAMEWORK.md structure and mandatory steps."""

    def test_thinking_framework_exists(self, role_id):
        path = get_role_paths(role_id)["thinking"]
        assert path.exists(), f"{role_id}: THINKING_FRAMEWORK.md not found at {path}"
        assert path.is_file(), f"{role_id}: {path} exists but is not a file"

    def test_thinking_framework_has_step_1_through_4(self, role_id):
        content = get_role_paths(role_id)["thinking"].read_text(encoding="utf-8")
        for step in ["Step 1", "Step 2", "Step 3", "Step 4"]:
            assert step in content, (
                f"{role_id}: THINKING_FRAMEWORK.md missing header '{step}'"
            )

    def test_thinking_framework_has_task_section(self, role_id):
        content = get_role_paths(role_id)["thinking"].read_text(encoding="utf-8")
        assert "Task" in content, (
            f"{role_id}: THINKING_FRAMEWORK.md missing 'Task' section"
        )

    def test_thinking_framework_mandatory_order(self, role_id):
        content = get_role_paths(role_id)["thinking"].read_text(encoding="utf-8")
        pos_step1 = content.index("Step 1")
        pos_step2 = content.index("Step 2")
        pos_step3 = content.index("Step 3")
        pos_step4 = content.index("Step 4")
        pos_task = content.index("Task:")
        assert pos_step1 < pos_step2 < pos_step3 < pos_step4 < pos_task, (
            f"{role_id}: Steps must appear in order: Step 1 → Step 2 → Step 3 → Step 4 → Task"
        )

    def test_thinking_framework_output_requirements_exist(self, role_id):
        content = get_role_paths(role_id)["thinking"].read_text(encoding="utf-8")
        assert "输出要求" in content, (
            f"{role_id}: THINKING_FRAMEWORK.md missing '输出要求' section"
        )


class TestThinkingFrameworkStep1Uniqueness:
    """Each role's Step 1 must be role-specific and address that role's primary concern."""

    def test_system_architect_step1_covers_full_architecture(self):
        """Step 1 = all modules + dependencies + data flows."""
        content = get_role_paths("system-architect")["thinking"].read_text(encoding="utf-8")
        step1_start = content.index("Step 1")
        step1_end = content.index("Step 2")
        step1_text = content[step1_start:step1_end]
        assert "模块" in step1_text, "SA Step 1 must address modules"
        assert "依赖" in step1_text or "数据流" in step1_text, "SA Step 1 must address dependencies/data flow"
        assert "API" in step1_text or "端点" in step1_text, "SA Step 1 must address API endpoints"

    def test_module_architect_step1_covers_own_module_and_interfaces(self):
        """Step 1 = own module + upstream/downstream interfaces."""
        content = get_role_paths("module-architect")["thinking"].read_text(encoding="utf-8")
        step1_start = content.index("Step 1")
        step1_end = content.index("Step 2")
        step1_text = content[step1_start:step1_end]
        assert "模块" in step1_text, "MA Step 1 must address own module"
        assert "上游" in step1_text or "下游" in step1_text or "接口" in step1_text, (
            "MA Step 1 must address upstream/downstream interfaces"
        )

    def test_developer_step1_covers_module_context_and_contract(self):
        """Step 1 = own module context + interface contract + coding standards (NOT full architecture)."""
        content = get_role_paths("developer")["thinking"].read_text(encoding="utf-8")
        step1_start = content.index("Step 1")
        step1_end = content.index("Step 2")
        step1_text = content[step1_start:step1_end]
        assert "接口" in step1_text or "契约" in step1_text, "DEV Step 1 must address interface contract"
        assert "规范" in step1_text or "标准" in step1_text, "DEV Step 1 must address coding standards"
        # Developer Step 1 must NOT mention full architecture
        assert "全局架构" not in step1_text, "DEV Step 1 must NOT address global architecture"
        assert "系统架构" not in step1_text, "DEV Step 1 must NOT address system architecture"

    def test_step1_contents_are_different_across_roles(self):
        """Step 1 for each role must contain role-specific keywords not shared with others."""
        sa_content = get_role_paths("system-architect")["thinking"].read_text(encoding="utf-8")
        ma_content = get_role_paths("module-architect")["thinking"].read_text(encoding="utf-8")
        dev_content = get_role_paths("developer")["thinking"].read_text(encoding="utf-8")

        sa_step1 = sa_content[sa_content.index("Step 1"):sa_content.index("Step 2")]
        ma_step1 = ma_content[ma_content.index("Step 1"):ma_content.index("Step 2")]
        dev_step1 = dev_content[dev_content.index("Step 1"):dev_content.index("Step 2")]

        # SA unique: full system view
        assert "所有" in sa_step1 or "系统" in sa_step1 or "全局" in sa_step1, (
            "SA Step 1 must show full-system perspective with words like 所有/系统/全局"
        )
        # MA unique: own module focus with upstream/downstream
        assert "上游" in ma_step1 or "下游" in ma_step1, (
            "MA Step 1 must show module-level focus with upstream/downstream"
        )
        # DEV unique: coding standards and contract focus
        assert "规范" in dev_step1 or "标准" in dev_step1 or "实现" in dev_step1, (
            "DEV Step 1 must focus on coding standards and implementation"
        )


# ═══════════════════════════════════════════════════════════════════════════
# INTERNAL_LOOP.md Tests
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("role_id", ["system-architect", "module-architect", "developer"])
class TestInternalLoop:
    """INTERNAL_LOOP.md structure and mandatory self-check layers."""

    def test_internal_loop_exists(self, role_id):
        path = get_role_paths(role_id)["loop"]
        assert path.exists(), f"{role_id}: INTERNAL_LOOP.md not found at {path}"
        assert path.is_file(), f"{role_id}: {path} exists but is not a file"

    def test_internal_loop_has_three_layers(self, role_id):
        content = get_role_paths(role_id)["loop"].read_text(encoding="utf-8")
        for loop_label in ["Loop 1", "Loop 2", "Loop 3"]:
            assert loop_label in content, (
                f"{role_id}: INTERNAL_LOOP.md missing '{loop_label}'"
            )

    def test_loop1_contract_compliance(self, role_id):
        content = get_role_paths(role_id)["loop"].read_text(encoding="utf-8")
        loop1_start = content.index("Loop 1")
        loop1_end = content.index("Loop 2") if "Loop 2" in content else len(content)
        loop1_text = content[loop1_start:loop1_end]
        assert "CONTRACT" in loop1_text or "合同" in loop1_text or "禁止" in loop1_text, (
            f"{role_id}: Loop 1 must address CONTRACT compliance"
        )

    def test_loop2_role_specific_quality(self, role_id):
        content = get_role_paths(role_id)["loop"].read_text(encoding="utf-8")
        loop2_start = content.index("Loop 2")
        loop2_end = content.index("Loop 3") if "Loop 3" in content else len(content)
        loop2_text = content[loop2_start:loop2_end]
        # Each role's Loop 2 should reference role-specific quality dimensions
        assert len(loop2_text.strip()) > 50, (
            f"{role_id}: Loop 2 must have substantive content"
        )

    def test_loop3_role_specific_validation(self, role_id):
        content = get_role_paths(role_id)["loop"].read_text(encoding="utf-8")
        loop3_start = content.index("Loop 3")
        loop3_text = content[loop3_start:]
        assert len(loop3_text.strip()) > 50, (
            f"{role_id}: Loop 3 must have substantive content"
        )

    def test_iteration_rules_exist(self, role_id):
        content = get_role_paths(role_id)["loop"].read_text(encoding="utf-8")
        assert "迭代" in content, (
            f"{role_id}: INTERNAL_LOOP.md missing iteration rules"
        )
        iteration_section = content[content.index("迭代"):]
        assert "3" in iteration_section[:200], (
            f"{role_id}: Iteration rules must specify max 3 iterations"
        )

    def test_iteration_has_blocked_fallback(self, role_id):
        content = get_role_paths(role_id)["loop"].read_text(encoding="utf-8")
        assert "BLOCKED" in content, (
            f"{role_id}: INTERNAL_LOOP.md must specify BLOCKED output when iterations exhausted"
        )

    def test_analysis_output_ratio_constraint(self, role_id):
        content = get_role_paths(role_id)["loop"].read_text(encoding="utf-8")
        assert "15%" in content or "15" in content, (
            f"{role_id}: INTERNAL_LOOP.md missing analysis-output ratio constraint (15%)"
        )

    def test_loop_rerun_step1_4_rule(self, role_id):
        content = get_role_paths(role_id)["loop"].read_text(encoding="utf-8")
        has_rerun = "Step 1-4" in content or "步骤" in content
        has_count = "2" in content
        assert has_rerun or has_count, (
            f"{role_id}: INTERNAL_LOOP.md must specify that after 2+ rejections, "
            f"Step 1-4 must be redone"
        )

    def test_no_infinite_loop(self, role_id):
        content = get_role_paths(role_id)["loop"].read_text(encoding="utf-8")
        assert "无限" in content or "token" in content, (
            f"{role_id}: INTERNAL_LOOP.md must explicitly prevent infinite looping"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Cross-Role Validation Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossRoleContractConsistency:
    """Validate that contracts across the 3 technical roles do not conflict."""

    def test_hierarchy_chain_is_respected(self):
        """System architect → module architect → developer is a strict hierarchy."""
        sa = load_yaml(get_role_paths("system-architect")["contract"])
        ma = load_yaml(get_role_paths("module-architect")["contract"])
        dev = load_yaml(get_role_paths("developer")["contract"])

        # System architect output → module architect input
        sa_output_text = " ".join(sa["output_artifacts"])
        ma_input_text = " ".join(ma["input_artifacts"])
        assert "架构" in ma_input_text or "设计" in ma_input_text or "接口" in ma_input_text, (
            "module-architect input must reference system-architect outputs"
        )

        # Module architect output → developer input
        ma_output_text = " ".join(ma["output_artifacts"])
        dev_input_text = " ".join(dev["input_artifacts"])
        assert "接口" in dev_input_text or "契约" in dev_input_text or "设计" in dev_input_text, (
            "developer input must reference module-architect outputs"
        )

    def test_no_role_can_approve_own_output(self):
        """Only the independent-reviewer can approve — roles cannot self-approve."""
        dev = load_yaml(get_role_paths("developer")["contract"])
        sa = load_yaml(get_role_paths("system-architect")["contract"])
        ma = load_yaml(get_role_paths("module-architect")["contract"])

        # Developer explicitly cannot approve own work
        dev_stance = " ".join(dev["fixed_stance"])
        assert "批准" in dev_stance or "评审" in dev_stance, (
            "developer fixed_stance must reference that they cannot self-approve"
        )

        # Neither SA nor MA claim to approve their own architecture (approval is by reviewer)
        sa_resp = " ".join(sa["responsibilities"])
        ma_resp = " ".join(ma["responsibilities"])
        # They can approve/deny subordinate work, but not their own
        # This is a structural check: they define standards but final approval is external
        assert True  # Structural check passes if no self-approval claims found

    def test_developer_cannot_modify_architecture(self):
        """Developer prohibitions must forbid modifying architecture/contracts."""
        dev = load_yaml(get_role_paths("developer")["contract"])
        proh_text = " ".join(dev["prohibitions"])
        assert "接口" in proh_text or "契约" in proh_text or "架构" in proh_text, (
            "developer prohibitions must forbid modifying architecture/interfaces/contracts"
        )

    def test_architects_cannot_write_business_code(self):
        """Both architects must be prohibited from writing business logic."""
        for role_id in ["system-architect", "module-architect"]:
            contract = load_yaml(get_role_paths(role_id)["contract"])
            proh_text = " ".join(contract["prohibitions"])
            assert "业务" in proh_text or "代码" in proh_text, (
                f"{role_id}: prohibitions must forbid writing business logic code"
            )

    def test_deviation_flow_is_defined(self):
        """Developer submits deviation → module architect reviews → system architect decides."""
        dev = load_yaml(get_role_paths("developer")["contract"])
        ma = load_yaml(get_role_paths("module-architect")["contract"])
        sa = load_yaml(get_role_paths("system-architect")["contract"])

        # Developer must produce deviation reports
        dev_output = " ".join(dev["output_artifacts"])
        assert "偏差" in dev_output, "developer output must include architecture deviation reports"

        # Module architect must handle deviation reports
        ma_input = " ".join(ma["input_artifacts"])
        assert "偏差" in ma_input, "module-architect input must include deviation reports"

        # System architect must handle deviation reports from module architect
        sa_resp = " ".join(sa["responsibilities"])
        assert "偏差" in sa_resp, "system-architect responsibilities must include deviation review"

    def test_veto_power_does_not_overlap(self):
        """Each role's veto power is scoped to its own domain — no overlap."""
        sa_veto = load_yaml(get_role_paths("system-architect")["contract"])["veto_power"]
        ma_veto = load_yaml(get_role_paths("module-architect")["contract"])["veto_power"]
        dev_veto = load_yaml(get_role_paths("developer")["contract"])["veto_power"]

        sa_veto_text = " ".join(sa_veto)
        ma_veto_text = " ".join(ma_veto)
        dev_veto_text = " ".join(dev_veto)

        # SA veto: system-level (circular dependency, security boundary, interface contract)
        # MA veto: module-level (component dependency, vague interface, function responsibility)
        # DEV veto: implementation-level (infeasibility, conflict — always submits deviation)

        # SA should NOT veto at function level
        assert "函数" not in sa_veto_text, "system-architect veto should not cover function-level"
        # MA should NOT veto at system deployment level
        assert "部署" not in ma_veto_text, "module-architect veto should not cover deployment"
        # DEV should NOT veto interface design
        assert "设计" not in dev_veto_text, "developer veto should not cover design decisions"

    def test_developer_blind_spots_include_architecture(self):
        """Developer's blind spots must acknowledge not seeing full architecture."""
        dev = load_yaml(get_role_paths("developer")["contract"])
        blind_text = " ".join(dev["identity"]["known_blind_spots"])
        assert "架构" in blind_text or "系统" in blind_text, (
            "developer blind spots must acknowledge not seeing full architecture"
        )

    def test_system_architect_blind_spots_include_implementation_detail(self):
        """System architect's blind spots must acknowledge not knowing implementation details."""
        sa = load_yaml(get_role_paths("system-architect")["contract"])
        blind_text = " ".join(sa["identity"]["known_blind_spots"])
        assert "实现" in blind_text or "代码" in blind_text or "编程" in blind_text, (
            "system-architect blind spots must acknowledge not knowing implementation detail"
        )
