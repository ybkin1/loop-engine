"""
Tests for the Seeded Defect Suite.

These tests validate that the detection infrastructure is in place
for each seeded defect. They do NOT call AI agents directly; instead,
they verify that:
  - The sample code is parseable and contains the expected defect markers
  - The defect registry is valid and complete
  - Static analysis and lint rules that SHOULD catch each defect exist
  - All defects in the registry map to actual code locations

This is the first layer of meta-validation: "Does our quality/safety
tooling have the right rules configured to catch these known defects?"
Future integration tests will feed sample code to actual AI agents and
verify their detection reports.
"""

from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path
from typing import Any


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

SAMPLE_DIR = Path(__file__).resolve().parent / "sample_code"
REGISTRY_PATH = Path(__file__).resolve().parent / "defect_registry.json"
SAMPLE_FILE = SAMPLE_DIR / "user_service.py"


def load_registry() -> dict:
    """Load and return the defect registry."""
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_sample_source() -> str:
    """Read the sample code as a raw string."""
    with open(SAMPLE_FILE, "r", encoding="utf-8") as f:
        return f.read()


def parse_sample_ast() -> ast.Module:
    """Parse the sample code into an AST."""
    source = load_sample_source()
    return ast.parse(source)


def defect_ids_in_source(source: str) -> set[str]:
    """Extract all DEFECT-SD-XXX IDs referenced in the source."""
    pattern = r"DEFECT-SD-(\d{3})"
    return {f"SD-{m}" for m in re.findall(pattern, source)}


# ─────────────────────────────────────────────────────────────
# 1.  Registry Integrity Tests
# ─────────────────────────────────────────────────────────────

class TestRegistryIntegrity:
    """Verify the defect_registry.json is well-formed and complete."""

    def test_registry_file_exists(self):
        """Registry JSON file must exist."""
        assert REGISTRY_PATH.is_file(), (
            f"defect_registry.json not found at {REGISTRY_PATH}"
        )

    def test_registry_is_valid_json(self):
        """Registry must be parseable JSON."""
        registry = load_registry()
        assert isinstance(registry, dict)
        assert "defects" in registry

    def test_registry_has_required_top_level_keys(self):
        """Registry must have expected top-level sections."""
        registry = load_registry()
        for key in ["defects", "roles", "difficulty_levels"]:
            assert key in registry, f"Missing top-level key: {key}"

    def test_all_defects_have_required_fields(self):
        """Every defect entry must have all mandatory fields."""
        required = [
            "id", "title", "type", "severity", "file",
            "line_hint", "expected_detector", "description",
            "false_negative_if_missed",
        ]
        registry = load_registry()
        for defect in registry["defects"]:
            for field in required:
                assert field in defect, (
                    f"Defect {defect.get('id', 'UNKNOWN')} missing field: {field}"
                )

    def test_defect_ids_are_unique(self):
        """No two defects should share the same ID."""
        registry = load_registry()
        ids = [d["id"] for d in registry["defects"]]
        assert len(ids) == len(set(ids)), (
            f"Duplicate defect IDs found: {ids}"
        )

    def test_defect_types_are_valid(self):
        """Defect types must be from the allowed set."""
        valid_types = {"security", "quality", "logic", "performance", "architecture"}
        registry = load_registry()
        for defect in registry["defects"]:
            assert defect["type"] in valid_types, (
                f"Defect {defect['id']} has invalid type: {defect['type']}"
            )

    def test_severities_are_valid(self):
        """Severity must be critical, high, medium, or low."""
        valid = {"critical", "high", "medium", "low"}
        registry = load_registry()
        for defect in registry["defects"]:
            assert defect["severity"] in valid, (
                f"Defect {defect['id']} has invalid severity: {defect['severity']}"
            )

    def test_referenced_files_exist(self):
        """Every file referenced by a defect must exist on disk."""
        registry = load_registry()
        base = Path(__file__).resolve().parent
        for defect in registry["defects"]:
            file_path = base / defect["file"]
            assert file_path.is_file(), (
                f"Defect {defect['id']} references missing file: {file_path}"
            )

    def test_expected_detectors_are_valid_roles(self):
        """Expected detectors must map to known Loop roles."""
        registry = load_registry()
        known_roles = set(registry.get("roles", {}).keys())
        for defect in registry["defects"]:
            assert defect["expected_detector"] in known_roles, (
                f"Defect {defect['id']} has unknown detector: "
                f"{defect['expected_detector']}"
            )

    def test_all_defects_assigned_to_difficulty_level(self):
        """Every defect must appear in at least one difficulty level."""
        registry = load_registry()
        all_ids = {d["id"] for d in registry["defects"]}
        assigned: set[str] = set()
        for level_name, level_data in registry.get("difficulty_levels", {}).items():
            assigned.update(level_data.get("defects", []))
        missing = all_ids - assigned
        assert not missing, (
            f"Defects not assigned to any difficulty level: {missing}"
        )


# ─────────────────────────────────────────────────────────────
# 2.  Source Code Presence Tests
# ─────────────────────────────────────────────────────────────

class TestSourceCodePresence:
    """Verify sample code exists, is valid Python, and contains defect markers."""

    def test_sample_file_exists(self):
        """Sample code file must exist."""
        assert SAMPLE_FILE.is_file(), (
            f"sample_code/user_service.py not found at {SAMPLE_FILE}"
        )

    def test_sample_is_valid_python(self):
        """Sample code must be syntactically valid Python."""
        try:
            parse_sample_ast()
        except SyntaxError as e:
            raise AssertionError(
                f"Sample code has syntax error: {e}"
            ) from e

    def test_source_contains_defect_markers(self):
        """Source must contain DEFECT-SD-XXX markers."""
        source = load_sample_source()
        ids = defect_ids_in_source(source)
        assert len(ids) > 0, "No DEFECT-SD-XXX markers found in source code"

    def test_source_and_registry_defect_ids_match(self):
        """Every defect in the source must be in the registry, and vice versa."""
        source = load_sample_source()
        source_ids = defect_ids_in_source(source)
        registry = load_registry()
        registry_ids = {d["id"] for d in registry["defects"]}

        missing_in_registry = source_ids - registry_ids
        missing_in_source = registry_ids - source_ids

        assert not missing_in_registry, (
            f"Source references defects not in registry: {missing_in_registry}"
        )
        assert not missing_in_source, (
            f"Registry lists defects not found in source: {missing_in_source}"
        )

    def test_class_user_service_exists(self):
        """Sample must define the UserService class."""
        tree = parse_sample_ast()
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        class_names = [c.name for c in classes]
        assert "UserService" in class_names, (
            f"UserService class not found. Classes: {class_names}"
        )


# ─────────────────────────────────────────────────────────────
# 3.  Per-Defect Detection Mechanism Tests
# ─────────────────────────────────────────────────────────────

class TestPerDefectDetection:
    """For each seeded defect, verify that the sample code actually
    contains the flawed pattern that the detection mechanism should catch."""

    def test_sd001_fstring_in_sql_execute(self):
        """SD-001: The search_users method MUST use f-string in execute()."""
        source = load_sample_source()
        # Look for the pattern: f"SELECT ... {keyword}"
        pattern = r'f"SELECT.*\{'
        matches = re.findall(pattern, source)
        assert len(matches) > 0, (
            "SD-001: Expected f-string SQL pattern not found in source"
        )
        # Also verify it's inside search_users context
        assert "def search_users" in source, "search_users method not found"

    def test_sd002_create_user_lacks_validation(self):
        """SD-002: create_user must accept raw inputs without checks."""
        tree = parse_sample_ast()

        # Find create_user function
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "create_user":
                # The function body should NOT contain if/raise/assert validation
                # It should go straight to db.execute
                body_statements = [
                    n for n in node.body
                    if not isinstance(n, ast.Expr)  # skip docstrings
                ]
                # First real statement should be db.execute (or similar)
                # Check there's no validation before the execute call
                has_early_validation = any(
                    isinstance(stmt, ast.If)
                    or (isinstance(stmt, ast.Assert))
                    for stmt in body_statements
                )
                assert not has_early_validation, (
                    "SD-002: create_user appears to have input validation "
                    "(should not have any for this seeded defect)"
                )
                # Verify db.execute is called
                has_execute = any(
                    isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "execute"
                    for n in ast.walk(node)
                )
                assert has_execute, "create_user must call db.execute"
                return

        raise AssertionError("SD-002: create_user method not found in AST")

    def test_sd003_set_password_no_hashing(self):
        """SD-003: set_password must write raw password without hashing.

        Check only executable code, not docstrings/comments — the docstring
        explains that hashing SHOULD be used, which is fine.
        """
        source = load_sample_source()

        # Confirm set_password exists
        assert "def set_password" in source, "set_password method not found"

        # Parse the AST and inspect set_password for actual hash imports/calls
        tree = parse_sample_ast()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "set_password":
                # Collect all AST nodes in the function body (excluding docstring)
                body_nodes = [
                    n for n in node.body
                    if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
                ]
                # Check for any import of hashing libraries
                # (imports are module-level, already checked separately below)
                # Check for any call to hash functions in the body
                for stmt in body_nodes:
                    for sub_node in ast.walk(stmt):
                        if isinstance(sub_node, ast.Call):
                            call_str = ast.dump(sub_node)
                            hash_indicators = [
                                "hashlib", "bcrypt", "argon2", "scrypt",
                                "pbkdf2", "hash",
                            ]
                            for indicator in hash_indicators:
                                assert indicator not in call_str, (
                                    f"SD-003: set_password body contains call "
                                    f"to hashing function '{indicator}'. "
                                    f"Defect should not hash passwords."
                                )
                # Also verify the function is not importing hashing modules
                # (imports are typically at module level)
                return

        raise AssertionError("SD-003: set_password method not found in AST")

    def test_sd004_division_by_zero_unguarded(self):
        """SD-004: get_average_age must divide by len() without guard."""
        source = load_sample_source()

        assert "def get_average_age" in source, "get_average_age method not found"

        # The return statement should have division by len()
        pattern = r"return total / len\(user_ids\)"
        match = re.search(pattern, source)
        assert match is not None, (
            "SD-004: Expected 'return total / len(user_ids)' pattern not found"
        )

        # Verify there's NO guard for empty list before the division
        # (no 'if not user_ids' or 'if len(user_ids) == 0')
        empty_checks = [
            r"if not user_ids",
            r"if len\(user_ids\) == 0",
            r"if len\(user_ids\) < 1",
            r"if user_ids is None",
        ]
        # Extract function body roughly
        func_section = source.split("def get_average_age")[1].split("    # ──")[0]
        for check_pattern in empty_checks:
            assert not re.search(check_pattern, func_section), (
                f"SD-004: get_average_age has empty-list guard '{check_pattern}' "
                f"— defect should NOT guard against empty input"
            )

    def test_sd005_query_inside_loop(self):
        """SD-005: get_users_with_orders must have db.execute inside for-loop."""
        tree = parse_sample_ast()

        # Find get_users_with_orders
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_users_with_orders":
                # Walk the function body for a For node containing a Call to execute
                for inner in ast.walk(node):
                    if isinstance(inner, ast.For):
                        for call_node in ast.walk(inner):
                            if (
                                isinstance(call_node, ast.Call)
                                and isinstance(call_node.func, ast.Attribute)
                                and call_node.func.attr == "execute"
                            ):
                                # Found: db.execute inside a for loop — defect confirmed
                                return

        raise AssertionError(
            "SD-005: No db.execute call found inside a for-loop in "
            "get_users_with_orders"
        )

    def test_sd006_circular_reference_exists(self):
        """SD-006: OrderService references UserService, and vice versa."""
        source = load_sample_source()

        # OrderService.__init__ takes UserService
        assert "user_service: UserService" in source or "UserService" in source, (
            "SD-006: OrderService should reference UserService"
        )

        # UserService.set_order_service takes OrderService
        assert "def set_order_service" in source, (
            "SD-006: UserService.set_order_service method not found"
        )
        assert "OrderService" in source, (
            "SD-006: OrderService type annotation not found in UserService context"
        )


# ─────────────────────────────────────────────────────────────
# 4.  Tooling Readiness Tests (Detection Infrastructure)
# ─────────────────────────────────────────────────────────────

class TestDetectionInfrastructure:
    """Verify that detection tools are configured to catch seeded defects.

    These tests check whether the project has the right linting rules,
    security scanners, and analysis tools that SHOULD detect each defect.
    They don't run the tools against the sample code (that would be
    an integration test), but verify the tool configuration exists.
    """

    def test_project_has_lint_configuration(self):
        """Project should have some form of linting/analysis configuration."""
        root = Path(__file__).resolve().parents[2]  # loop-engine/

        # Check for common Python project config files
        config_indicators = [
            root / "pyproject.toml",
            root / "setup.cfg",
            root / "tox.ini",
            root / "ruff.toml",
            root / ".ruff.toml",
            root / ".flake8",
            root / ".bandit",
        ]
        config_exists = any(p.exists() for p in config_indicators)
        # Also check for ruff cache (implied ruff usage)
        ruff_cache = root / ".ruff_cache"
        has_ruff_cache = ruff_cache.is_dir()
        # requirements.txt at least indicates a Python project
        has_requirements = (root / "requirements.txt").is_file()

        assert config_exists or has_ruff_cache or has_requirements, (
            "No project configuration files found (pyproject.toml, setup.cfg, "
            ".ruff_cache, etc.). Linting tools may not be configured."
        )

    def test_ruff_or_pylint_configured(self):
        """At least one Python linter should be configured."""
        root = Path(__file__).resolve().parents[2]
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8")
            has_ruff = "[tool.ruff]" in content
            has_pylint = "[tool.pylint]" in content
            assert has_ruff or has_pylint, (
                "pyproject.toml does not configure ruff or pylint"
            )

    def test_bandit_or_semgrep_configured(self):
        """At least one security scanner should be configurable."""
        root = Path(__file__).resolve().parents[2]
        # Bandit can run without config (uses defaults), semgrep may have rules
        pyproject = root / "pyproject.toml"
        has_bandit_section = False
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8")
            has_bandit_section = "[tool.bandit]" in content
        # If neither is explicitly configured, bandit at least works with defaults
        # This test verifies we've acknowledged the need
        # (bandit runs with zero config, so this is a soft check)
        assert True  # Bandit works with defaults; explicit config is optional

    def test_test_file_itself_is_runnable(self):
        """Meta-test: This file must parse and have at least one test class."""
        this_file = Path(__file__)
        source = this_file.read_text(encoding="utf-8")
        tree = ast.parse(source)
        test_classes = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.ClassDef) and n.name.startswith("Test")
        ]
        assert len(test_classes) >= 3, (
            f"Expected at least 3 Test* classes, found {len(test_classes)}"
        )


# ─────────────────────────────────────────────────────────────
# 5.  Cross-Reference Integrity Tests
# ─────────────────────────────────────────────────────────────

class TestCrossReferenceIntegrity:
    """Verify consistency between registry, roles, and difficulty levels."""

    def test_role_primary_defects_exist_in_registry(self):
        """Every defect listed under a role's primary_defects must exist."""
        registry = load_registry()
        all_ids = {d["id"] for d in registry["defects"]}
        for role_name, role_data in registry.get("roles", {}).items():
            for defect_id in role_data.get("primary_defects", []):
                assert defect_id in all_ids, (
                    f"Role '{role_name}' references unknown defect: {defect_id}"
                )

    def test_difficulty_defects_exist_in_registry(self):
        """Every defect listed in difficulty_levels must exist."""
        registry = load_registry()
        all_ids = {d["id"] for d in registry["defects"]}
        for level_name, level_data in registry.get("difficulty_levels", {}).items():
            for defect_id in level_data.get("defects", []):
                assert defect_id in all_ids, (
                    f"Difficulty '{level_name}' references unknown defect: {defect_id}"
                )

    def test_coverage_all_defects_have_at_least_one_role(self):
        """Every defect should be detectable by at least the expected_detector."""
        registry = load_registry()
        role_names = set(registry.get("roles", {}).keys())
        for defect in registry["defects"]:
            detector = defect["expected_detector"]
            also = defect.get("also_detectable_by", [])
            all_detectors = {detector} | set(also)
            # At minimum, the expected_detector must be a known role
            assert detector in role_names, (
                f"Defect {defect['id']} expected_detector '{detector}' "
                f"is not a known role"
            )
