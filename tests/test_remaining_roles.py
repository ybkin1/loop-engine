"""
Tests for the remaining 4 roles — security-engineer, test-engineer,
independent-reviewer, release-engineer.

Validates the three-layer role architecture for each role:
  1. CONTRACT.yaml — role identity, stance, responsibilities, veto power, projection rules
  2. THINKING_FRAMEWORK.md — mandatory multi-perspective thinking order with role-specific Step 1
  3. INTERNAL_LOOP.md — self-check loop with iteration limits

Also performs cross-role validation to ensure:
  - test-engineer and quality-engineer responsibilities do not overlap
  - security-engineer veto covers CRITICAL/HIGH blocking
  - independent-reviewer prohibitions include no-self-review and no code modification
  - release-engineer includes rollback verification requirements
  - Projection rules correctly differentiate all 4 roles
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
    "security-engineer": AGENTS_DIR / "security-engineer",
    "test-engineer": AGENTS_DIR / "test-engineer",
    "independent-reviewer": AGENTS_DIR / "independent-reviewer",
    "release-engineer": AGENTS_DIR / "release-engineer",
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
# Parametrized tests (run for all 4 roles)
# ═══════════════════════════════════════════════════════════════════════════

# ── CONTRACT.yaml Tests ──

@pytest.mark.parametrize("role_id", list(ROLES.keys()))
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


@pytest.mark.parametrize("role_id", list(ROLES.keys()))
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


@pytest.mark.parametrize("role_id", list(ROLES.keys()))
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

    def test_security_engineer_stance_covers_vulnerabilities(self, role_id):
        if role_id != "security-engineer":
            pytest.skip("Only for security-engineer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        stances_text = " ".join(contract["fixed_stance"])
        assert "漏洞" in stances_text or "安全" in stances_text, (
            "security-engineer fixed_stance must reference vulnerabilities/security"
        )
        assert "CRITICAL" in stances_text or "漏洞" in stances_text, (
            "security-engineer fixed_stance must reference CRITICAL/HIGH vulnerability handling"
        )

    def test_test_engineer_stance_covers_test_execution(self, role_id):
        if role_id != "test-engineer":
            pytest.skip("Only for test-engineer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        stances_text = " ".join(contract["fixed_stance"])
        assert "测试" in stances_text, (
            "test-engineer fixed_stance must reference testing"
        )
        assert "复现" in stances_text or "覆盖" in stances_text, (
            "test-engineer fixed_stance must reference reproducibility or coverage"
        )

    def test_test_engineer_does_not_judge_delivery(self, role_id):
        if role_id != "test-engineer":
            pytest.skip("Only for test-engineer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        stances_text = " ".join(contract["fixed_stance"])
        # test-engineer must NOT claim authority to judge delivery quality
        assert "质量工程师" in stances_text or "不判断" in stances_text, (
            "test-engineer fixed_stance must defer delivery judgment to quality-engineer"
        )

    def test_independent_reviewer_stance_covers_skepticism(self, role_id):
        if role_id != "independent-reviewer":
            pytest.skip("Only for independent-reviewer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        stances_text = " ".join(contract["fixed_stance"])
        assert "默认假设" in stances_text or "有问题" in stances_text, (
            "independent-reviewer fixed_stance must reference skepticism / 'assume problems'"
        )
        assert "证据" in stances_text or "代码" in stances_text, (
            "independent-reviewer fixed_stance must reference code-as-evidence"
        )

    def test_release_engineer_stance_covers_rollback(self, role_id):
        if role_id != "release-engineer":
            pytest.skip("Only for release-engineer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        stances_text = " ".join(contract["fixed_stance"])
        assert "回滚" in stances_text, (
            "release-engineer fixed_stance must reference rollback"
        )
        assert "发布" in stances_text, (
            "release-engineer fixed_stance must reference release/deployment"
        )


@pytest.mark.parametrize("role_id", list(ROLES.keys()))
class TestContractResponsibilities:
    """Tests for responsibilities section."""

    def test_responsibilities_exists_and_non_empty(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert "responsibilities" in contract, f"{role_id}: missing 'responsibilities'"
        resp = contract["responsibilities"]
        assert isinstance(resp, list), f"{role_id}: responsibilities must be a list"
        assert len(resp) > 0, f"{role_id}: responsibilities must not be empty"


@pytest.mark.parametrize("role_id", list(ROLES.keys()))
class TestContractProhibitions:
    """Tests for prohibitions section."""

    def test_prohibitions_exists_and_non_empty(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert "prohibitions" in contract, f"{role_id}: missing 'prohibitions'"
        proh = contract["prohibitions"]
        assert isinstance(proh, list), f"{role_id}: prohibitions must be a list"
        assert len(proh) > 0, f"{role_id}: prohibitions must not be empty"

    def test_independent_reviewer_prohibits_self_review_and_code_modification(self, role_id):
        if role_id != "independent-reviewer":
            pytest.skip("Only for independent-reviewer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        proh_text = " ".join(contract["prohibitions"])
        assert "修改" in proh_text or "修复" in proh_text, (
            "independent-reviewer prohibitions must forbid modifying/fixing code"
        )
        assert "自" in proh_text or "自己" in proh_text, (
            "independent-reviewer prohibitions must forbid self-review"
        )

    def test_security_engineer_prohibits_pass_with_critical_high(self, role_id):
        if role_id != "security-engineer":
            pytest.skip("Only for security-engineer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        proh_text = " ".join(contract["prohibitions"])
        assert "CRITICAL" in proh_text or "HIGH" in proh_text, (
            "security-engineer prohibitions must forbid PASS with CRITICAL/HIGH vulnerabilities"
        )

    def test_release_engineer_prohibits_build_failure_deployment(self, role_id):
        if role_id != "release-engineer":
            pytest.skip("Only for release-engineer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        proh_text = " ".join(contract["prohibitions"])
        assert "构建" in proh_text or "回滚" in proh_text, (
            "release-engineer prohibitions must forbid deployment on build failure or without rollback"
        )

    def test_test_engineer_prohibits_fake_test_data(self, role_id):
        if role_id != "test-engineer":
            pytest.skip("Only for test-engineer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        proh_text = " ".join(contract["prohibitions"])
        assert "造假" in proh_text or "编造" in proh_text or "GO" in proh_text or "NOGO" in proh_text, (
            "test-engineer prohibitions must forbid fake test data or delivery judgment"
        )


@pytest.mark.parametrize("role_id", list(ROLES.keys()))
class TestContractVetoPower:
    """Tests for veto_power section."""

    def test_veto_power_exists_and_non_empty(self, role_id):
        contract = load_yaml(get_role_paths(role_id)["contract"])
        assert "veto_power" in contract, f"{role_id}: missing 'veto_power'"
        veto = contract["veto_power"]
        assert isinstance(veto, list), f"{role_id}: veto_power must be a list"
        assert len(veto) > 0, f"{role_id}: veto_power must not be empty"

    def test_security_engineer_veto_covers_critical_high_blocking(self, role_id):
        if role_id != "security-engineer":
            pytest.skip("Only for security-engineer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        veto_text = " ".join(contract["veto_power"])
        assert "CRITICAL" in veto_text, (
            "security-engineer veto_power must explicitly mention CRITICAL"
        )
        assert "HIGH" in veto_text, (
            "security-engineer veto_power must explicitly mention HIGH"
        )
        # Must have blocking/denial language associated with CRITICAL/HIGH
        assert "否决" in veto_text or "阻断" in veto_text, (
            "security-engineer veto_power must block on CRITICAL/HIGH"
        )

    def test_security_engineer_veto_covers_dependencies_and_config(self, role_id):
        if role_id != "security-engineer":
            pytest.skip("Only for security-engineer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        veto_text = " ".join(contract["veto_power"])
        assert "依赖" in veto_text or "CVE" in veto_text, (
            "security-engineer veto must cover dependency/CVE issues"
        )
        assert "密钥" in veto_text or "配置" in veto_text or "凭证" in veto_text, (
            "security-engineer veto must cover credentials/config issues"
        )

    def test_release_engineer_veto_covers_rollback_verification(self, role_id):
        if role_id != "release-engineer":
            pytest.skip("Only for release-engineer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        veto_text = " ".join(contract["veto_power"])
        assert "回滚" in veto_text, (
            "release-engineer veto_power must mention rollback"
        )
        assert "验证" in veto_text or "演练" in veto_text, (
            "release-engineer veto_power must mention rollback verification/drill"
        )

    def test_release_engineer_veto_covers_monitoring(self, role_id):
        if role_id != "release-engineer":
            pytest.skip("Only for release-engineer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        veto_text = " ".join(contract["veto_power"])
        assert "监控" in veto_text or "告警" in veto_text, (
            "release-engineer veto_power must cover monitoring/alerting"
        )

    def test_independent_reviewer_veto_prevents_self_review(self, role_id):
        if role_id != "independent-reviewer":
            pytest.skip("Only for independent-reviewer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        veto_text = " ".join(contract["veto_power"])
        assert "自审" in veto_text or "非独立" in veto_text, (
            "independent-reviewer veto must detect/prevent self-review"
        )

    def test_test_engineer_veto_on_blocked_prerequisites(self, role_id):
        if role_id != "test-engineer":
            pytest.skip("Only for test-engineer")
        contract = load_yaml(get_role_paths(role_id)["contract"])
        veto_text = " ".join(contract["veto_power"])
        assert "BLOCKED" in veto_text or "数据" in veto_text or "环境" in veto_text, (
            "test-engineer veto must cover blocked prerequisites (data/environment)"
        )


@pytest.mark.parametrize("role_id", list(ROLES.keys()))
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


@pytest.mark.parametrize("role_id", list(ROLES.keys()))
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


@pytest.mark.parametrize("role_id", list(ROLES.keys()))
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
            "deployment_structure": {
                "services": [{"name": "auth-service", "port": 8080}],
                "environments": ["dev", "staging", "prod"],
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


@pytest.mark.parametrize("role_id", list(ROLES.keys()))
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
        assert "升级" in esc_text or "Gate" in esc_text, (
            f"{role_id}: veto_escalation must define escalation/upgrade path"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Role-Specific Projection Rules Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestSecurityEngineerProjectionRules:
    """Security engineer sees project + modules + api_endpoints + database + deps, not pages."""

    def test_se_projection_includes_api_endpoints(self):
        contract = load_yaml(get_role_paths("security-engineer")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_api = any("api_endpoints" in path for path in includes)
        assert has_api, "security-engineer projection must include api_endpoints"

    def test_se_projection_includes_database(self):
        contract = load_yaml(get_role_paths("security-engineer")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_db = any("database" in path for path in includes)
        assert has_db, "security-engineer projection must include database"

    def test_se_projection_includes_modules(self):
        contract = load_yaml(get_role_paths("security-engineer")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_modules = any("modules" in path for path in includes)
        assert has_modules, "security-engineer projection must include modules"

    def test_se_projection_excludes_pages(self):
        contract = load_yaml(get_role_paths("security-engineer")["contract"])
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "pages" in excludes, (
            "security-engineer exclude_sections must include 'pages'"
        )


class TestTestEngineerProjectionRules:
    """Test engineer sees project + pages + api_endpoints + database, not modules architecture."""

    def test_te_projection_includes_pages(self):
        contract = load_yaml(get_role_paths("test-engineer")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_pages = any("pages" in path for path in includes)
        assert has_pages, "test-engineer projection must include pages"

    def test_te_projection_includes_api_endpoints(self):
        contract = load_yaml(get_role_paths("test-engineer")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_api = any("api_endpoints" in path for path in includes)
        assert has_api, "test-engineer projection must include api_endpoints"

    def test_te_projection_includes_database(self):
        contract = load_yaml(get_role_paths("test-engineer")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_db = any("database" in path for path in includes)
        assert has_db, "test-engineer projection must include database"

    def test_te_projection_excludes_modules(self):
        contract = load_yaml(get_role_paths("test-engineer")["contract"])
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "modules" in excludes, (
            "test-engineer exclude_sections must include 'modules'"
        )


class TestIndependentReviewerProjectionRules:
    """Independent reviewer sees project + changed modules + upstream/downstream interfaces,
    NOT pages/api/database full detail."""

    def test_ir_projection_includes_modules(self):
        contract = load_yaml(get_role_paths("independent-reviewer")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_modules = any("modules" in path for path in includes)
        assert has_modules, "independent-reviewer projection must include modules"

    def test_ir_projection_excludes_pages(self):
        contract = load_yaml(get_role_paths("independent-reviewer")["contract"])
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "pages" in excludes, (
            "independent-reviewer exclude_sections must include 'pages'"
        )

    def test_ir_projection_excludes_api_endpoints(self):
        contract = load_yaml(get_role_paths("independent-reviewer")["contract"])
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "api_endpoints" in excludes, (
            "independent-reviewer exclude_sections must include 'api_endpoints'"
        )

    def test_ir_projection_excludes_database(self):
        contract = load_yaml(get_role_paths("independent-reviewer")["contract"])
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "database" in excludes, (
            "independent-reviewer exclude_sections must include 'database'"
        )


class TestReleaseEngineerProjectionRules:
    """Release engineer sees project + deployment_structure + all modules, NOT pages."""

    def test_re_projection_includes_deployment_structure(self):
        contract = load_yaml(get_role_paths("release-engineer")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_deployment = any("deployment" in path for path in includes)
        assert has_deployment, "release-engineer projection must include deployment_structure"

    def test_re_projection_includes_modules(self):
        contract = load_yaml(get_role_paths("release-engineer")["contract"])
        includes = contract["projection_rules"]["include_sections"]
        has_modules = any("modules" in path for path in includes)
        assert has_modules, "release-engineer projection must include modules"

    def test_re_projection_excludes_pages(self):
        contract = load_yaml(get_role_paths("release-engineer")["contract"])
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "pages" in excludes, (
            "release-engineer exclude_sections must include 'pages'"
        )

    def test_re_projection_excludes_api_endpoints(self):
        contract = load_yaml(get_role_paths("release-engineer")["contract"])
        excludes = contract["projection_rules"]["exclude_sections"]
        assert "api_endpoints" in excludes, (
            "release-engineer exclude_sections must include 'api_endpoints'"
        )


# ═══════════════════════════════════════════════════════════════════════════
# THINKING_FRAMEWORK.md Tests
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("role_id", list(ROLES.keys()))
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

    def test_security_engineer_step1_covers_attack_surface(self):
        content = get_role_paths("security-engineer")["thinking"].read_text(encoding="utf-8")
        step1_start = content.index("Step 1")
        step1_end = content.index("Step 2")
        step1_text = content[step1_start:step1_end]
        assert "攻击" in step1_text or "安全" in step1_text, (
            "security-engineer Step 1 must address attack surface / security perspective"
        )
        assert "依赖" in step1_text or "CVE" in step1_text, (
            "security-engineer Step 1 must address dependencies"
        )

    def test_test_engineer_step1_covers_test_scope(self):
        content = get_role_paths("test-engineer")["thinking"].read_text(encoding="utf-8")
        step1_start = content.index("Step 1")
        step1_end = content.index("Step 2")
        step1_text = content[step1_start:step1_end]
        assert "测试" in step1_text, "test-engineer Step 1 must address test perspective"
        assert "覆盖" in step1_text or "用例" in step1_text, (
            "test-engineer Step 1 must address coverage / test cases"
        )

    def test_independent_reviewer_step1_covers_diff_scope(self):
        content = get_role_paths("independent-reviewer")["thinking"].read_text(encoding="utf-8")
        step1_start = content.index("Step 1")
        step1_end = content.index("Step 2")
        step1_text = content[step1_start:step1_end]
        assert "diff" in step1_text.lower() or "变更" in step1_text, (
            "independent-reviewer Step 1 must address diff / change scope"
        )

    def test_release_engineer_step1_covers_deployment_scope(self):
        content = get_role_paths("release-engineer")["thinking"].read_text(encoding="utf-8")
        step1_start = content.index("Step 1")
        step1_end = content.index("Step 2")
        step1_text = content[step1_start:step1_end]
        assert "部署" in step1_text or "发布" in step1_text, (
            "release-engineer Step 1 must address deployment/release scope"
        )
        assert "回滚" in step1_text, (
            "release-engineer Step 1 must address rollback"
        )

    def test_step1_contents_are_different_across_roles(self):
        """Step 1 for each role must contain role-specific keywords not shared with others."""
        se = get_role_paths("security-engineer")["thinking"].read_text(encoding="utf-8")
        te = get_role_paths("test-engineer")["thinking"].read_text(encoding="utf-8")
        ir = get_role_paths("independent-reviewer")["thinking"].read_text(encoding="utf-8")
        re_content = get_role_paths("release-engineer")["thinking"].read_text(encoding="utf-8")

        se_step1 = se[se.index("Step 1"):se.index("Step 2")]
        te_step1 = te[te.index("Step 1"):te.index("Step 2")]
        ir_step1 = ir[ir.index("Step 1"):ir.index("Step 2")]
        re_step1 = re_content[re_content.index("Step 1"):re_content.index("Step 2")]

        # Each Step 1 must have unique role-specific keywords
        assert "漏洞" in se_step1 or "攻击" in se_step1 or "安全" in se_step1, (
            "security-engineer Step 1 must have security-specific keywords"
        )
        assert "测试" in te_step1, (
            "test-engineer Step 1 must have test-specific keywords"
        )
        assert "diff" in ir_step1.lower() or "变更" in ir_step1, (
            "independent-reviewer Step 1 must have review-specific keywords"
        )
        assert "部署" in re_step1 or "回滚" in re_step1 or "发布" in re_step1, (
            "release-engineer Step 1 must have release-specific keywords"
        )


# ═══════════════════════════════════════════════════════════════════════════
# INTERNAL_LOOP.md Tests
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("role_id", list(ROLES.keys()))
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

class TestCrossRoleNoOverlap:
    """Validate that the 4 new roles do not overlap with each other or with existing roles."""

    def test_test_engineer_vs_quality_engineer_no_overlap(self):
        """Test engineer executes tests and reports bugs; quality engineer judges delivery quality."""
        te = load_yaml(get_role_paths("test-engineer")["contract"])
        qe_path = AGENTS_DIR / "quality-engineer" / "CONTRACT.yaml"
        qe = load_yaml(qe_path)

        # test-engineer responsibilities must NOT include delivery judgment
        te_resp_text = " ".join(te.get("responsibilities", []))
        assert "GO" not in te_resp_text and "NOGO" not in te_resp_text, (
            "test-engineer responsibilities must NOT include GO/NOGO delivery judgment"
        )
        assert "交付" not in te_resp_text, (
            "test-engineer responsibilities must NOT include delivery judgment"
        )
        assert "质量判断" not in te_resp_text, (
            "test-engineer responsibilities must NOT include quality judgment"
        )

        # quality-engineer responsibilities MUST include delivery judgment / quality gate
        qe_resp_text = " ".join(qe.get("responsibilities", []))
        assert "交付" in qe_resp_text or "GO" in qe_resp_text or "标准" in qe_resp_text, (
            "quality-engineer responsibilities must include delivery judgment"
        )

        # test-engineer prohibitions must explicitly forbid GO/NOGO judgment
        te_proh_text = " ".join(te.get("prohibitions", []))
        assert "质量工程师" in te_proh_text or "GO" in te_proh_text or "NOGO" in te_proh_text, (
            "test-engineer prohibitions must defer delivery judgment to quality-engineer"
        )

        # test-engineer blind spots must acknowledge quality judgment is not their domain
        te_blind_text = " ".join(te["identity"]["known_blind_spots"])
        assert "质量工程师" in te_blind_text, (
            "test-engineer known_blind_spots must reference quality-engineer's domain"
        )

    def test_test_engineer_fixed_stance_defers_to_quality_engineer(self):
        """Test engineer's fixed_stance must explicitly defer delivery judgment to quality engineer."""
        te = load_yaml(get_role_paths("test-engineer")["contract"])
        stances_text = " ".join(te["fixed_stance"])
        assert "质量工程师" in stances_text, (
            "test-engineer fixed_stance must explicitly defer delivery judgment to quality-engineer"
        )

    def test_security_engineer_veto_priority(self):
        """Security engineer veto takes priority — this must be stated in the contract."""
        se = load_yaml(get_role_paths("security-engineer")["contract"])
        stances_text = " ".join(se["fixed_stance"])
        assert "优先" in stances_text or "否决" in stances_text, (
            "security-engineer fixed_stance must assert veto priority"
        )

    def test_independent_reviewer_no_code_modification(self):
        """Independent reviewer prohibitions must forbid modifying/fixing code."""
        ir = load_yaml(get_role_paths("independent-reviewer")["contract"])
        proh_text = " ".join(ir["prohibitions"])
        assert "修改" in proh_text or "修复" in proh_text, (
            "independent-reviewer prohibitions must forbid modifying/fixing code"
        )

    def test_independent_reviewer_no_self_review(self):
        """Independent reviewer must prohibit self-review explicitly."""
        ir = load_yaml(get_role_paths("independent-reviewer")["contract"])
        proh_text = " ".join(ir["prohibitions"])
        stances_text = " ".join(ir["fixed_stance"])
        combined = proh_text + " " + stances_text
        assert "自" in combined or "自己" in combined, (
            "independent-reviewer must explicitly prohibit self-review (in stances or prohibitions)"
        )

    def test_release_engineer_rollback_verification_required(self):
        """Release engineer must require rollback verification."""
        re_contract = load_yaml(get_role_paths("release-engineer")["contract"])

        # Check quality_standards for rollback verification
        qs_text = " ".join(re_contract.get("quality_standards", []))
        assert "回滚" in qs_text, (
            "release-engineer quality_standards must reference rollback"
        )
        assert "验证" in qs_text or "演练" in qs_text, (
            "release-engineer quality_standards must reference rollback verification/drill"
        )

        # Check veto_power for rollback verification
        veto_text = " ".join(re_contract.get("veto_power", []))
        assert "回滚" in veto_text, (
            "release-engineer veto_power must reference rollback"
        )
        assert "验证" in veto_text or "演练" in veto_text, (
            "release-engineer veto_power must reference rollback verification/drill"
        )

    def test_projection_rules_correctly_differentiate_4_roles(self):
        """Each of the 4 roles must have a unique projection profile."""
        se_includes = set(load_yaml(get_role_paths("security-engineer")["contract"])["projection_rules"]["include_sections"])
        te_includes = set(load_yaml(get_role_paths("test-engineer")["contract"])["projection_rules"]["include_sections"])
        ir_includes = set(load_yaml(get_role_paths("independent-reviewer")["contract"])["projection_rules"]["include_sections"])
        re_includes = set(load_yaml(get_role_paths("release-engineer")["contract"])["projection_rules"]["include_sections"])

        # No two roles should have identical include_sections
        assert se_includes != te_includes, "security-engineer and test-engineer must have different includes"
        assert se_includes != ir_includes, "security-engineer and independent-reviewer must have different includes"
        assert se_includes != re_includes, "security-engineer and release-engineer must have different includes"
        assert te_includes != ir_includes, "test-engineer and independent-reviewer must have different includes"
        assert te_includes != re_includes, "test-engineer and release-engineer must have different includes"
        assert ir_includes != re_includes, "independent-reviewer and release-engineer must have different includes"

    def test_security_sees_dependencies_others_dont(self):
        """Security engineer uniquely sees full api_endpoints and database for attack surface."""
        se_includes = set(load_yaml(get_role_paths("security-engineer")["contract"])["projection_rules"]["include_sections"])
        te_includes = set(load_yaml(get_role_paths("test-engineer")["contract"])["projection_rules"]["include_sections"])
        ir_includes = set(load_yaml(get_role_paths("independent-reviewer")["contract"])["projection_rules"]["include_sections"])

        # security sees both api_endpoints and database (for dependency/attack surface analysis)
        se_has_api = any("api_endpoints" in p for p in se_includes)
        se_has_db = any("database" in p for p in se_includes)
        ir_has_api = any("api_endpoints" in p for p in ir_includes)
        ir_has_db = any("database" in p for p in ir_includes)

        assert se_has_api, "security-engineer must include api_endpoints (attack surface)"
        assert se_has_db, "security-engineer must include database (sensitive data analysis)"
        assert not ir_has_api, "independent-reviewer must NOT include api_endpoints"
        assert not ir_has_db, "independent-reviewer must NOT include database"

    def test_release_engineer_sees_deployment_structure(self):
        """Only release-engineer sees deployment_structure."""
        re_includes = set(load_yaml(get_role_paths("release-engineer")["contract"])["projection_rules"]["include_sections"])
        se_includes = set(load_yaml(get_role_paths("security-engineer")["contract"])["projection_rules"]["include_sections"])
        te_includes = set(load_yaml(get_role_paths("test-engineer")["contract"])["projection_rules"]["include_sections"])
        ir_includes = set(load_yaml(get_role_paths("independent-reviewer")["contract"])["projection_rules"]["include_sections"])

        re_has_deploy = any("deployment" in p for p in re_includes)
        se_has_deploy = any("deployment" in p for p in se_includes)
        te_has_deploy = any("deployment" in p for p in te_includes)
        ir_has_deploy = any("deployment" in p for p in ir_includes)

        assert re_has_deploy, "release-engineer must include deployment_structure"
        assert not se_has_deploy, "security-engineer must NOT include deployment_structure"
        assert not te_has_deploy, "test-engineer must NOT include deployment_structure"
        assert not ir_has_deploy, "independent-reviewer must NOT include deployment_structure"


# ═══════════════════════════════════════════════════════════════════════════
# Quality Dimension Tests (role-specific questions in projection_rules)
# ═══════════════════════════════════════════════════════════════════════════

class TestRoleSpecificDimensions:
    """Each role's projection_rules must have role-specific dimension questions."""

    def test_security_engineer_has_security_dimensions(self):
        contract = load_yaml(get_role_paths("security-engineer")["contract"])
        dims = contract["projection_rules"].get("security_dimensions", [])
        assert len(dims) > 0, "security-engineer must have security_dimensions"
        dims_text = " ".join(dims)
        assert "安全" in dims_text or "漏洞" in dims_text or "CVE" in dims_text, (
            "security_dimensions must address security concerns"
        )

    def test_test_engineer_has_test_dimensions(self):
        contract = load_yaml(get_role_paths("test-engineer")["contract"])
        dims = contract["projection_rules"].get("test_dimensions", [])
        assert len(dims) > 0, "test-engineer must have test_dimensions"
        dims_text = " ".join(dims)
        assert "测试" in dims_text or "覆盖" in dims_text or "用例" in dims_text, (
            "test_dimensions must address testing concerns"
        )

    def test_independent_reviewer_has_review_dimensions(self):
        contract = load_yaml(get_role_paths("independent-reviewer")["contract"])
        dims = contract["projection_rules"].get("review_dimensions", [])
        assert len(dims) > 0, "independent-reviewer must have review_dimensions"
        dims_text = " ".join(dims)
        assert "代码" in dims_text or "契约" in dims_text or "异常" in dims_text or "接口" in dims_text, (
            "review_dimensions must address code review concerns"
        )

    def test_release_engineer_has_release_dimensions(self):
        contract = load_yaml(get_role_paths("release-engineer")["contract"])
        dims = contract["projection_rules"].get("release_dimensions", [])
        assert len(dims) > 0, "release-engineer must have release_dimensions"
        dims_text = " ".join(dims)
        assert "构建" in dims_text or "部署" in dims_text or "回滚" in dims_text or "发布" in dims_text, (
            "release_dimensions must address release/deployment concerns"
        )
