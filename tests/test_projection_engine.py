"""
Tests for ProjectionEngine and related data classes.

Covers:
  - Loading projection rules from CONTRACT.yaml
  - Generating projections with correct visible sections
  - Exclude patterns are correctly recorded
  - to_prompt_context() produces correct format
  - Staleness detection (source map hash change)
  - Default projection when CONTRACT.yaml is absent
  - Multiple roles get distinct projections
  - Quality checkpoints are attached and appear in prompt context
  - Edge cases: missing PROJECT_MAP, invalid YAML, empty rules
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
import textwrap
from pathlib import Path

# Ensure the parent directory is on sys.path so we can import loop_core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.projection_engine import (
    ProjectionEngine,
    ProjectionRule,
    RoleProjection,
)


# ============================================================================
# Helpers
# ============================================================================


def _write_project_map(root: Path, data: dict) -> Path:
    """Write PROJECT_MAP.yaml as JSON inside the given root."""
    import json

    map_path = root / "PROJECT_MAP.yaml"
    map_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return map_path


def _write_contract(root: Path, role_id: str, rules: dict | None) -> Path:
    """Write agents/{role_id}/CONTRACT.yaml inside the given root."""
    import json

    agent_dir = root / "agents" / role_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    contract_path = agent_dir / "CONTRACT.yaml"
    if rules is not None:
        contract_path.write_text(json.dumps(rules, ensure_ascii=False), encoding="utf-8")
    else:
        contract_path.write_text("{}", encoding="utf-8")
    return contract_path


def _build_sample_map() -> dict:
    """Return a realistic PROJECT_MAP for testing."""
    return {
        "project": {
            "name": "Loop Engine",
            "type": "cli_tool",
            "description": "AI-driven project governance engine.",
        },
        "pages": [
            {
                "id": "page-login",
                "path": "/login",
                "title": "Login",
                "elements": [
                    {
                        "id": "btn-submit",
                        "type": "button",
                        "label": "Sign In",
                        "properties": {"action": "submit_form"},
                    },
                    {
                        "id": "input-email",
                        "type": "input",
                        "label": "Email",
                        "properties": {"validation": ["required", "email"]},
                    },
                ],
                "states": [
                    {"name": "default", "description": "Login form visible."},
                    {"name": "error", "description": "Error message displayed."},
                ],
                "navigation_from": ["page-home"],
                "navigation_to": ["page-dashboard"],
            },
            {
                "id": "page-dashboard",
                "path": "/dashboard",
                "title": "Dashboard",
                "elements": [
                    {
                        "id": "link-logout",
                        "type": "link",
                        "label": "Logout",
                        "properties": {"action": "navigate", "target": "page-login"},
                    },
                ],
                "states": [
                    {"name": "default", "description": "Dashboard content."},
                    {"name": "empty", "description": "No data message."},
                ],
                "navigation_from": ["page-login"],
                "navigation_to": ["page-login"],
            },
        ],
        "api_endpoints": [
            {
                "id": "api-login",
                "method": "POST",
                "path": "/api/auth/login",
                "request": {
                    "headers": ["Content-Type: application/json"],
                    "body_schema": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string"},
                            "password": {"type": "string"},
                        },
                    },
                },
                "response": {
                    "success_schema": {
                        "type": "object",
                        "properties": {"token": {"type": "string"}},
                    },
                    "error_codes": ["401", "429"],
                },
                "auth_required": False,
            },
            {
                "id": "api-dashboard",
                "method": "GET",
                "path": "/api/dashboard",
                "request": {
                    "headers": ["Authorization: Bearer <token>"],
                },
                "response": {
                    "success_schema": {
                        "type": "object",
                        "properties": {"data": {"type": "array"}},
                    },
                    "error_codes": ["401", "403"],
                },
                "auth_required": True,
            },
        ],
        "modules": [
            {
                "id": "auth-module",
                "responsibilities": [
                    "User authentication",
                    "Session management",
                    "Permission checking",
                ],
                "depends_on": [],
                "depended_by": ["dashboard-module"],
            },
            {
                "id": "dashboard-module",
                "responsibilities": [
                    "Dashboard data aggregation",
                    "Widget rendering",
                ],
                "depends_on": ["auth-module"],
                "depended_by": [],
            },
        ],
        "database": {
            "tables": [
                {
                    "name": "users",
                    "columns": [
                        {
                            "name": "id",
                            "type": "INTEGER",
                            "nullable": False,
                            "primary_key": True,
                            "foreign_key": None,
                        },
                        {
                            "name": "email",
                            "type": "VARCHAR(255)",
                            "nullable": False,
                            "primary_key": False,
                            "foreign_key": None,
                        },
                    ],
                    "indexes": ["idx_users_email ON users(email)"],
                },
            ],
        },
    }


# ============================================================================
# Tests: ProjectionRule
# ============================================================================


class TestProjectionRule:
    """Tests for the ProjectionRule data class."""

    def test_default_rule_empty(self):
        """A default rule has empty include/exclude and no quality dimensions."""
        rule = ProjectionRule()
        assert rule.include_patterns == []
        assert rule.exclude_patterns == []
        assert rule.quality_dimensions == []

    def test_rule_with_all_fields(self):
        """All fields can be populated."""
        rule = ProjectionRule(
            include_patterns=["pages", "pages.*.elements"],
            exclude_patterns=["api_endpoints", "database"],
            quality_dimensions=["Check 1", "Check 2"],
        )
        assert len(rule.include_patterns) == 2
        assert len(rule.exclude_patterns) == 2
        assert len(rule.quality_dimensions) == 2


# ============================================================================
# Tests: RoleProjection
# ============================================================================


class TestRoleProjection:
    """Tests for the RoleProjection data class."""

    def test_construction_basic(self):
        """RoleProjection can be constructed with all fields."""
        rp = RoleProjection(
            role_id="test-role",
            phase="S5-quality",
            visible_sections={"project": {"name": "Test", "type": "web_app"}},
            quality_checkpoints=["Q1"],
            excluded_sections=["api_endpoints"],
            generated_at="2024-01-01T00:00:00+00:00",
            source_map_hash="abc123",
        )
        assert rp.role_id == "test-role"
        assert rp.phase == "S5-quality"
        assert "project" in rp.visible_sections
        assert rp.quality_checkpoints == ["Q1"]
        assert rp.excluded_sections == ["api_endpoints"]

    def test_to_dict_and_from_dict_roundtrip(self):
        """Serialisation round-trip preserves all data."""
        original = RoleProjection(
            role_id="architect",
            phase="S2-architecture",
            visible_sections={
                "project": {"name": "MyApp", "type": "web_app", "description": "Desc"},
                "modules": [
                    {"id": "m1", "responsibilities": ["auth"]},
                ],
            },
            quality_checkpoints=["Architecture review complete?"],
            excluded_sections=["pages", "api_endpoints"],
            generated_at="2024-06-15T10:00:00+00:00",
            source_map_hash="def456",
        )
        d = original.to_dict()
        restored = RoleProjection.from_dict(d)
        assert restored.role_id == original.role_id
        assert restored.phase == original.phase
        assert restored.visible_sections == original.visible_sections
        assert restored.quality_checkpoints == original.quality_checkpoints
        assert restored.excluded_sections == original.excluded_sections
        assert restored.generated_at == original.generated_at
        assert restored.source_map_hash == original.source_map_hash

    def test_to_prompt_context_includes_role_id(self):
        """Prompt context should mention the role ID."""
        rp = RoleProjection(
            role_id="frontend-test-engineer",
            phase="S5-quality",
            visible_sections={
                "project": {"name": "TestApp", "type": "web_app", "description": "A test app"},
            },
            quality_checkpoints=[],
            excluded_sections=[],
            generated_at="2024-01-01T00:00:00+00:00",
            source_map_hash="abc",
        )
        text = rp.to_prompt_context()
        assert "frontend-test-engineer" in text

    def test_to_prompt_context_includes_quality_checkpoints(self):
        """Quality checkpoints should appear as a numbered list."""
        rp = RoleProjection(
            role_id="qa",
            phase="S5-quality",
            visible_sections={
                "project": {"name": "App", "type": "web_app", "description": "Test"},
            },
            quality_checkpoints=[
                "Is test coverage above 80%?",
                "Are all lint checks passing?",
            ],
            excluded_sections=[],
            generated_at="2024-01-01T00:00:00+00:00",
            source_map_hash="abc",
        )
        text = rp.to_prompt_context()
        assert "质量检查点" in text
        assert "1. Is test coverage above 80%?" in text
        assert "2. Are all lint checks passing?" in text

    def test_to_prompt_context_includes_project_info(self):
        """Project name, type, description, and phase should all appear."""
        rp = RoleProjection(
            role_id="dev",
            phase="S4-implementation",
            visible_sections={
                "project": {
                    "name": "MyProject",
                    "type": "cli_tool",
                    "description": "A command-line tool",
                },
            },
            quality_checkpoints=[],
            excluded_sections=[],
            generated_at="2024-01-01T00:00:00+00:00",
            source_map_hash="abc",
        )
        text = rp.to_prompt_context()
        assert "MyProject" in text
        assert "cli_tool" in text
        assert "A command-line tool" in text
        assert "S4-implementation" in text

    def test_to_prompt_context_with_visible_sections(self):
        """Visible sections beyond 'project' should be rendered."""
        rp = RoleProjection(
            role_id="architect",
            phase="S2-architecture",
            visible_sections={
                "project": {"name": "App", "type": "web_app", "description": "Desc"},
                "modules": [
                    {"id": "auth-module", "responsibilities": ["auth", "session"]},
                ],
            },
            quality_checkpoints=[],
            excluded_sections=[],
            generated_at="2024-01-01T00:00:00+00:00",
            source_map_hash="abc",
        )
        text = rp.to_prompt_context()
        assert "模块" in text
        assert "auth-module" in text
        assert "auth, session" in text

    def test_to_prompt_context_section_without_project(self):
        """If project section is missing, use fallback values."""
        rp = RoleProjection(
            role_id="dev",
            phase="S4-implementation",
            visible_sections={
                "pages": [{"id": "p1", "path": "/p1", "title": "Page 1"}],
            },
            quality_checkpoints=[],
            excluded_sections=[],
            generated_at="2024-01-01T00:00:00+00:00",
            source_map_hash="abc",
        )
        text = rp.to_prompt_context()
        # Should still produce output without crashing
        assert "Unknown" in text or "dev" in text


# ============================================================================
# Tests: ProjectionEngine — Rule Loading
# ============================================================================


class TestLoadRules:
    """Tests for ProjectionEngine.load_rules()."""

    def test_loads_rules_from_contract(self):
        """Rules are correctly loaded from a CONTRACT.yaml with projection_rules."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())
            _write_contract(
                root,
                "frontend-tester",
                {
                    "role": "frontend-test-engineer",
                    "projection_rules": {
                        "include_sections": [
                            "pages",
                            "pages.*.elements",
                            "pages.*.states",
                        ],
                        "exclude_sections": [
                            "api_endpoints",
                            "database",
                        ],
                        "quality_dimensions": [
                            "Is every page element reachable?",
                            "Are all element states covered?",
                        ],
                    },
                },
            )

            engine = ProjectionEngine(root)
            rules = engine.load_rules("frontend-tester")

            assert isinstance(rules, ProjectionRule)
            assert "pages" in rules.include_patterns
            assert "pages.*.elements" in rules.include_patterns
            assert "pages.*.states" in rules.include_patterns
            assert "api_endpoints" in rules.exclude_patterns
            assert "database" in rules.exclude_patterns
            assert len(rules.quality_dimensions) == 2
            assert "Is every page element reachable?" in rules.quality_dimensions

    def test_default_rules_when_no_contract(self):
        """Returns default rules when CONTRACT.yaml does not exist."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())
            # Do NOT write any CONTRACT.yaml

            engine = ProjectionEngine(root)
            rules = engine.load_rules("nonexistent-role")

            assert isinstance(rules, ProjectionRule)
            assert rules.include_patterns == ["project"]
            assert rules.exclude_patterns == []
            assert rules.quality_dimensions == []

    def test_default_rules_when_no_projection_rules(self):
        """Returns default rules when CONTRACT.yaml exists but has no projection_rules."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())
            # Write a contract without projection_rules
            _write_contract(root, "no-rules-role", {"role": "some-role"})

            engine = ProjectionEngine(root)
            rules = engine.load_rules("no-rules-role")

            assert rules.include_patterns == ["project"]
            assert rules.exclude_patterns == []

    def test_default_rules_when_contract_is_invalid_yaml(self):
        """Returns default rules when CONTRACT.yaml has malformed content."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())

            agent_dir = root / "agents" / "corrupt-role"
            agent_dir.mkdir(parents=True, exist_ok=True)
            contract_path = agent_dir / "CONTRACT.yaml"
            # Write invalid JSON/YAML
            contract_path.write_text("{ this is not valid yaml: [", encoding="utf-8")

            engine = ProjectionEngine(root)
            rules = engine.load_rules("corrupt-role")

            assert rules.include_patterns == ["project"]

    def test_empty_rules_in_contract(self):
        """Empty include/exclude/quality lists in contract should result in empty rules."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())
            _write_contract(
                root,
                "empty-rules",
                {
                    "projection_rules": {
                        "include_sections": [],
                        "exclude_sections": [],
                        "quality_dimensions": [],
                    },
                },
            )

            engine = ProjectionEngine(root)
            rules = engine.load_rules("empty-rules")

            assert rules.include_patterns == []
            assert rules.exclude_patterns == []
            assert rules.quality_dimensions == []


# ============================================================================
# Tests: ProjectionEngine — Projection Generation
# ============================================================================


class TestGenerateProjection:
    """Tests for ProjectionEngine.generate_projection()."""

    def test_generates_projection_with_correct_sections(self):
        """Visible sections should contain only the data matching include_patterns."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())
            _write_contract(
                root,
                "frontend-tester",
                {
                    "projection_rules": {
                        "include_sections": [
                            "project",
                            "pages",
                            "pages.*.elements",
                        ],
                        "exclude_sections": ["api_endpoints", "modules", "database"],
                        "quality_dimensions": ["All pages tested?"],
                    },
                },
            )

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("frontend-tester", phase="S5-quality")

            assert isinstance(proj, RoleProjection)
            assert proj.role_id == "frontend-tester"
            assert proj.phase == "S5-quality"

            # Check visible sections
            assert "project" in proj.visible_sections
            assert "pages" in proj.visible_sections
            assert "pages.*.elements" in proj.visible_sections
            # These should NOT be included
            assert "api_endpoints" not in proj.visible_sections
            assert "modules" not in proj.visible_sections

            # Check project data integrity
            proj_data = proj.visible_sections["project"]
            assert proj_data["name"] == "Loop Engine"
            assert proj_data["type"] == "cli_tool"

            # Check pages data
            pages = proj.visible_sections["pages"]
            assert isinstance(pages, list)
            assert len(pages) == 2

            # Check flattened elements
            elements = proj.visible_sections["pages.*.elements"]
            assert isinstance(elements, list)
            assert len(elements) == 3  # 2 from page-login + 1 from page-dashboard

    def test_exclude_patterns_recorded(self):
        """Excluded sections should be recorded in the projection."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())
            _write_contract(
                root,
                "frontend",
                {
                    "projection_rules": {
                        "include_sections": ["project", "pages"],
                        "exclude_sections": ["api_endpoints", "database", "modules"],
                        "quality_dimensions": [],
                    },
                },
            )

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("frontend")

            assert "api_endpoints" in proj.excluded_sections
            assert "database" in proj.excluded_sections
            assert "modules" in proj.excluded_sections

    def test_quality_checkpoints_attached(self):
        """Quality dimensions from contract are attached as checkpoints."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())
            _write_contract(
                root,
                "qa",
                {
                    "projection_rules": {
                        "include_sections": ["project"],
                        "exclude_sections": [],
                        "quality_dimensions": [
                            "Coverage >= 80%",
                            "No HIGH/CRITICAL vulnerabilities",
                        ],
                    },
                },
            )

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("qa")

            assert len(proj.quality_checkpoints) == 2
            assert "Coverage >= 80%" in proj.quality_checkpoints
            assert "No HIGH/CRITICAL vulnerabilities" in proj.quality_checkpoints

    def test_default_projection_without_contract(self):
        """When no CONTRACT.yaml exists, projection includes only project info."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())
            # No agents/ directory at all

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("unknown-role")

            assert proj.role_id == "unknown-role"
            assert "project" in proj.visible_sections
            # Only project should be present
            section_keys = list(proj.visible_sections.keys())
            assert section_keys == ["project"]
            assert proj.quality_checkpoints == []
            assert proj.excluded_sections == []

    def test_multiple_roles_get_different_projections(self):
        """Different roles should get different data based on their rules."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())

            # Frontend role: sees pages
            _write_contract(
                root,
                "frontend",
                {
                    "projection_rules": {
                        "include_sections": ["project", "pages"],
                        "exclude_sections": ["api_endpoints", "modules", "database"],
                        "quality_dimensions": ["FE check"],
                    },
                },
            )

            # Backend role: sees api_endpoints
            _write_contract(
                root,
                "backend",
                {
                    "projection_rules": {
                        "include_sections": ["project", "api_endpoints", "database"],
                        "exclude_sections": ["pages", "modules"],
                        "quality_dimensions": ["BE check"],
                    },
                },
            )

            engine = ProjectionEngine(root)

            fe_proj = engine.generate_projection("frontend")
            be_proj = engine.generate_projection("backend")

            # Frontend sees pages, not API endpoints
            assert "pages" in fe_proj.visible_sections
            assert "api_endpoints" not in fe_proj.visible_sections

            # Backend sees API endpoints, not pages
            assert "api_endpoints" in be_proj.visible_sections
            assert "pages" not in be_proj.visible_sections

            # Quality checkpoints differ
            assert fe_proj.quality_checkpoints == ["FE check"]
            assert be_proj.quality_checkpoints == ["BE check"]

    def test_phase_inference_from_state_yaml(self):
        """Phase should be inferred from .ai/state.yaml when not explicitly provided."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())

            # Write state.yaml with current_phase
            ai_dir = root / ".ai"
            ai_dir.mkdir(parents=True, exist_ok=True)
            state_path = ai_dir / "state.yaml"
            state_path.write_text('current_phase: "S4-implementation"\n', encoding="utf-8")

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("any-role")

            assert proj.phase == "S4-implementation"

    def test_phase_defaults_to_unknown(self):
        """Phase should default to 'unknown' when state.yaml is absent."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("any-role")

            assert proj.phase == "unknown"

    def test_explicit_phase_overrides_inferred(self):
        """Explicitly provided phase should override state.yaml value."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())

            # Write state.yaml
            ai_dir = root / ".ai"
            ai_dir.mkdir(parents=True, exist_ok=True)
            (ai_dir / "state.yaml").write_text('current_phase: "S2-architecture"\n', encoding="utf-8")

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("any-role", phase="S6-delivery")

            assert proj.phase == "S6-delivery"


class TestGenerateProjectionEdgeCases:
    """Edge case tests for projection generation."""

    def test_missing_project_map_raises(self):
        """FileNotFoundError when PROJECT_MAP.yaml is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # No PROJECT_MAP.yaml at all

            engine = ProjectionEngine(root)
            try:
                engine.generate_projection("any-role")
                assert False, "Should have raised FileNotFoundError"
            except FileNotFoundError:
                pass

    def test_include_pattern_returns_none(self):
        """If a query returns None, it should be silently skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())
            _write_contract(
                root,
                "tester",
                {
                    "projection_rules": {
                        "include_sections": [
                            "project",
                            "nonexistent_key",
                            "pages.*.nonexistent_sub",
                        ],
                        "exclude_sections": [],
                        "quality_dimensions": [],
                    },
                },
            )

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("tester")

            # Only "project" should be present
            assert "project" in proj.visible_sections
            assert "nonexistent_key" not in proj.visible_sections
            assert "pages.*.nonexistent_sub" not in proj.visible_sections

    def test_wildcard_query_on_empty_array(self):
        """Wildcard queries on empty arrays should return None."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = {
                "project": {"name": "Test", "type": "web_app", "description": "D"},
                "pages": [],
            }
            _write_project_map(root, data)
            _write_contract(
                root,
                "tester",
                {
                    "projection_rules": {
                        "include_sections": ["pages.*.elements"],
                        "exclude_sections": [],
                        "quality_dimensions": [],
                    },
                },
            )

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("tester")

            # Wildcard on empty array returns None, should not be in visible_sections
            assert "pages.*.elements" not in proj.visible_sections


# ============================================================================
# Tests: ProjectionEngine — Staleness Detection
# ============================================================================


class TestStalenessDetection:
    """Tests for ProjectionEngine.detect_staleness()."""

    def test_fresh_projection_not_stale(self):
        """A just-generated projection should not be stale."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("any-role")

            assert engine.detect_staleness("any-role", proj) is False

    def test_modified_map_detected_as_stale(self):
        """Modifying PROJECT_MAP should make the projection stale."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            map_path = _write_project_map(root, _build_sample_map())

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("any-role")

            # Modify the project map
            map_path.write_text(
                map_path.read_text(encoding="utf-8").replace("Loop Engine", "Loop Engine v2"),
                encoding="utf-8",
            )

            assert engine.detect_staleness("any-role", proj) is True

    def test_unchanged_map_not_stale(self):
        """Reading the map without changes should not trigger staleness."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("any-role")

            # Do nothing to the map, re-check
            assert engine.detect_staleness("any-role", proj) is False

    def test_missing_map_is_stale(self):
        """If the map is deleted, the projection is stale."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            map_path = _write_project_map(root, _build_sample_map())

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("any-role")

            # Delete the map
            map_path.unlink()

            assert engine.detect_staleness("any-role", proj) is True

    def test_hash_consistency(self):
        """The source_map_hash should match the SHA-256 of the file content."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            map_path = _write_project_map(root, _build_sample_map())

            raw = map_path.read_text(encoding="utf-8")
            expected_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("any-role")

            assert proj.source_map_hash == expected_hash
            assert len(proj.source_map_hash) == 64  # SHA-256 hex digest


# ============================================================================
# Tests: ProjectionEngine — Role Discovery
# ============================================================================


class TestListRolesWithProjections:
    """Tests for ProjectionEngine.list_roles_with_projections()."""

    def test_no_agents_directory(self):
        """Should return empty list when no agents/ directory exists."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())
            # No agents/ directory

            engine = ProjectionEngine(root)
            roles = engine.list_roles_with_projections()

            assert roles == []

    def test_list_roles_with_rules(self):
        """Should list all roles that have projection_rules in their CONTRACT.yaml."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())

            # Role with rules
            _write_contract(
                root,
                "frontend",
                {"projection_rules": {"include_sections": ["pages"]}},
            )
            # Role without rules
            _write_contract(root, "no-rules", {"role": "basic"})
            # Role directory but no CONTRACT.yaml
            (root / "agents" / "empty-role").mkdir(parents=True, exist_ok=True)

            engine = ProjectionEngine(root)
            roles = engine.list_roles_with_projections()

            assert "frontend" in roles
            assert "no-rules" not in roles
            assert "empty-role" not in roles
            assert len(roles) == 1

    def test_empty_agents_directory(self):
        """Empty agents/ directory returns empty list."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())
            (root / "agents").mkdir(parents=True, exist_ok=True)

            engine = ProjectionEngine(root)
            roles = engine.list_roles_with_projections()

            assert roles == []


# ============================================================================
# Tests: to_prompt_context format
# ============================================================================


class TestPromptContextFormat:
    """Detailed format checks for to_prompt_context()."""

    def test_output_contains_expected_sections(self):
        """Full projection output should contain all expected sections."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())
            _write_contract(
                root,
                "qa-engineer",
                {
                    "projection_rules": {
                        "include_sections": ["project", "modules"],
                        "exclude_sections": ["pages", "api_endpoints", "database"],
                        "quality_dimensions": [
                            "All modules reviewed?",
                            "Dependency graph valid?",
                        ],
                    },
                },
            )

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("qa-engineer", phase="S5-quality")
            text = proj.to_prompt_context()

            # Verify structural elements
            assert "qa-engineer" in text
            assert "Loop Engine" in text
            assert "cli_tool" in text
            assert "S5-quality" in text
            assert "质量检查点" in text
            assert "All modules reviewed?" in text
            assert "Dependency graph valid?" in text
            assert "模块" in text
            assert "auth-module" in text
            assert "dashboard-module" in text

    def test_output_with_no_quality_checkpoints(self):
        """When there are no quality checkpoints, the section should be omitted."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project_map(root, _build_sample_map())

            engine = ProjectionEngine(root)
            proj = engine.generate_projection("any-role")
            text = proj.to_prompt_context()

            assert "质量检查点" not in text

    def test_output_with_flat_list_sections(self):
        """Sections that are flat lists should render correctly."""
        rp = RoleProjection(
            role_id="dev",
            phase="S4-implementation",
            visible_sections={
                "project": {"name": "Test", "type": "web_app", "description": "D"},
                "pages.*.elements": [
                    {"id": "btn-1", "type": "button", "label": "Click"},
                    {"id": "input-1", "type": "input", "label": "Name"},
                ],
            },
            quality_checkpoints=[],
            excluded_sections=[],
            generated_at="2024-01-01T00:00:00+00:00",
            source_map_hash="abc",
        )
        text = rp.to_prompt_context()
        assert "btn-1" in text
        assert "input-1" in text
        assert "共 2 个" in text

    def test_output_is_stripped(self):
        """The output should not have leading/trailing whitespace beyond content."""
        rp = RoleProjection(
            role_id="dev",
            phase="S4",
            visible_sections={"project": {"name": "A", "type": "web_app", "description": "B"}},
            quality_checkpoints=[],
            excluded_sections=[],
            generated_at="2024-01-01T00:00:00+00:00",
            source_map_hash="abc",
        )
        text = rp.to_prompt_context()
        assert text == text.strip()
        assert not text.startswith("\n")
        assert not text.endswith("\n")
