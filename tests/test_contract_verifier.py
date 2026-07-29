"""
Unit tests for loop_core.contract_verifier — Contract-to-Test Coverage Verifier.

Covers:
  - Valid contract with all required tests found → no violations
  - Contract with missing required tests → violations returned
  - No contract file → skipped (empty results, not a blocker)
  - YAML and JSON contract formats
  - Test function detection in test files
  - HardConstraints C10 integration
  - HardConstraints C11 integration
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Ensure the parent directory is on sys.path so we can import loop_core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from loop_core.contract_verifier import (
    ContractTestDef,
    ContractTestResult,
    check_contract_test_coverage,
    find_contract_files,
    find_test_files,
    find_test_functions,
    parse_contract,
    verify_contract_coverage,
)
from loop_core.hard_constraints import (
    ConstraintID,
    Severity,
    ConstraintViolation,
    HardConstraints,
    _parse_allowed_paths_from_markdown,
)


# ── Helpers ─────────────────────────────────────────────────────────────

def _write_file(path: Path, content: str) -> None:
    """Write content to a file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _setup_temp_project(
    tmp: Path,
    *,
    contract_content: str | None = None,
    contract_format: str = "yaml",
    test_files: dict[str, str] | None = None,
    task_id: str = "T-0100",
    task_md_content: str | None = None,
) -> Path:
    """Create a minimal project structure for testing.

    Args:
        tmp: Temporary directory root.
        contract_content: Content for the interface-contract file (None = skip).
        contract_format: "yaml" or "json".
        test_files: Dict of filename -> content for test files.
        task_id: Task identifier.
        task_md_content: Content for the task markdown file.

    Returns:
        The project root Path.
    """
    root = tmp / "project"
    root.mkdir(parents=True, exist_ok=True)

    # Create .ai/ directory structure
    ai_dir = root / ".ai"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "state.yaml").write_text("current_phase: S4-implementation\n", encoding="utf-8")

    # Create task directory
    task_dir = ai_dir / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    if task_md_content is not None:
        (task_dir / f"{task_id}.md").write_text(task_md_content, encoding="utf-8")

    # Create evidence directory
    evidence_dir = ai_dir / "evidence" / task_id
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # Create contract file if content provided
    if contract_content is not None:
        ext = ".yaml" if contract_format == "yaml" else ".json"
        contract_path = evidence_dir / f"interface-contract{ext}"
        contract_path.write_text(contract_content, encoding="utf-8")

    # Create test directory and files
    if test_files:
        test_dir = root / "tests"
        test_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in test_files.items():
            _write_file(test_dir / filename, content)

    return root


# ═══════════════════════════════════════════════════════════════════════════
# parse_contract tests
# ═══════════════════════════════════════════════════════════════════════════


class TestParseContract:
    """Tests for parse_contract with YAML and JSON formats."""

    def test_parse_yaml_contract(self, tmp_path: Path):
        """Parse a valid YAML contract file."""
        content = """contracts:
  - function: register
    tests_required:
      - test_register_success
      - test_register_duplicate
      - test_register_invalid_email
  - function: login
    tests_required:
      - test_login_success
      - test_login_invalid_password
"""
        contract_path = tmp_path / "contract.yaml"
        contract_path.write_text(content, encoding="utf-8")

        entries = parse_contract(contract_path)
        assert len(entries) == 2
        assert entries[0].function == "register"
        assert entries[0].tests_required == [
            "test_register_success",
            "test_register_duplicate",
            "test_register_invalid_email",
        ]
        assert entries[1].function == "login"
        assert entries[1].tests_required == [
            "test_login_success",
            "test_login_invalid_password",
        ]

    def test_parse_json_contract(self, tmp_path: Path):
        """Parse a valid JSON contract file."""
        content = json.dumps({
            "contracts": [
                {
                    "function": "register",
                    "tests_required": [
                        "test_register_success",
                        "test_register_duplicate",
                    ],
                },
            ],
        })
        contract_path = tmp_path / "contract.json"
        contract_path.write_text(content, encoding="utf-8")

        entries = parse_contract(contract_path)
        assert len(entries) == 1
        assert entries[0].function == "register"
        assert entries[0].tests_required == [
            "test_register_success",
            "test_register_duplicate",
        ]

    def test_parse_missing_file(self, tmp_path: Path):
        """Parsing a non-existent file returns empty list."""
        entries = parse_contract(tmp_path / "nonexistent.yaml")
        assert entries == []

    def test_parse_empty_contract(self, tmp_path: Path):
        """Parsing a contract with no contracts list returns empty."""
        content = "description: Just a description, no contracts list\n"
        contract_path = tmp_path / "empty.yaml"
        contract_path.write_text(content, encoding="utf-8")
        entries = parse_contract(contract_path)
        assert entries == []


# ═══════════════════════════════════════════════════════════════════════════
# find_contract_files tests
# ═══════════════════════════════════════════════════════════════════════════


class TestFindContractFiles:
    """Tests for find_contract_files."""

    def test_finds_standard_contract(self, tmp_path: Path):
        """Find interface-contract.yaml in the task evidence directory."""
        root = _setup_temp_project(
            tmp_path,
            contract_content="contracts: []\n",
            contract_format="yaml",
        )
        files = find_contract_files(root, "T-0100")
        assert len(files) == 1
        assert files[0].name == "interface-contract.yaml"

    def test_no_contract_returns_empty(self, tmp_path: Path):
        """No contract file in evidence directory returns empty list."""
        root = _setup_temp_project(tmp_path)
        files = find_contract_files(root, "T-0100")
        assert files == []

    def test_missing_evidence_dir_returns_empty(self, tmp_path: Path):
        """Missing evidence directory returns empty list."""
        root = tmp_path / "project"
        root.mkdir()
        files = find_contract_files(root, "T-9999")
        assert files == []


# ═══════════════════════════════════════════════════════════════════════════
# find_test_files tests
# ═══════════════════════════════════════════════════════════════════════════


class TestFindTestFiles:
    """Tests for find_test_files."""

    def test_finds_test_files(self, tmp_path: Path):
        """Find test files in the test directory."""
        root = tmp_path / "project"
        test_dir = root / "tests"
        test_dir.mkdir(parents=True)
        (test_dir / "test_auth.py").write_text("", encoding="utf-8")
        (test_dir / "test_users.py").write_text("", encoding="utf-8")
        (test_dir / "helpers.py").write_text("", encoding="utf-8")  # not a test file
        (test_dir / "conftest.py").write_text("", encoding="utf-8")  # not test_*.py or *_test.py

        files = find_test_files(root)
        names = [f.name for f in files]
        assert "test_auth.py" in names
        assert "test_users.py" in names
        assert "helpers.py" not in names
        assert "conftest.py" not in names

    def test_missing_test_dir_returns_empty(self, tmp_path: Path):
        """Missing test directory returns empty list."""
        root = tmp_path / "project"
        root.mkdir()
        files = find_test_files(root)
        assert files == []


# ═══════════════════════════════════════════════════════════════════════════
# find_test_functions tests
# ═══════════════════════════════════════════════════════════════════════════


class TestFindTestFunctions:
    """Tests for find_test_functions."""

    def test_finds_all_required_functions(self, tmp_path: Path):
        """All required test functions are found."""
        test_content = """
def test_register_success():
    pass

def test_register_duplicate():
    pass

def test_login_success():
    pass
"""
        root = _setup_temp_project(
            tmp_path,
            test_files={"test_auth.py": test_content},
        )
        found, missing = find_test_functions(
            root,
            ["test_register_success", "test_register_duplicate", "test_login_success"],
        )
        assert set(found) == {"test_register_success", "test_register_duplicate", "test_login_success"}
        assert missing == []

    def test_reports_missing_functions(self, tmp_path: Path):
        """Missing test functions are reported."""
        test_content = """
def test_register_success():
    pass
"""
        root = _setup_temp_project(
            tmp_path,
            test_files={"test_auth.py": test_content},
        )
        found, missing = find_test_functions(
            root,
            ["test_register_success", "test_register_duplicate"],
        )
        assert found == ["test_register_success"]
        assert missing == ["test_register_duplicate"]

    def test_all_missing_when_no_test_files(self, tmp_path: Path):
        """All functions are missing when there are no test files."""
        root = _setup_temp_project(tmp_path)
        found, missing = find_test_functions(
            root,
            ["test_register_success", "test_login_success"],
        )
        assert found == []
        assert set(missing) == {"test_register_success", "test_login_success"}

    def test_finds_method_functions(self, tmp_path: Path):
        """Test functions defined as class methods are found."""
        test_content = """
class TestAuth:
    def test_register_success(self):
        pass

    def test_register_duplicate(self):
        pass
"""
        root = _setup_temp_project(
            tmp_path,
            test_files={"test_auth.py": test_content},
        )
        found, missing = find_test_functions(
            root,
            ["test_register_success", "test_register_duplicate"],
        )
        assert set(found) == {"test_register_success", "test_register_duplicate"}
        assert missing == []


# ═══════════════════════════════════════════════════════════════════════════
# verify_contract_coverage tests (integration)
# ═══════════════════════════════════════════════════════════════════════════


class TestVerifyContractCoverage:
    """Integration tests for verify_contract_coverage."""

    def test_valid_contract_all_tests_found(self, tmp_path: Path):
        """Valid contract with all required tests found → no missing tests."""
        contract_yaml = """contracts:
  - function: register
    tests_required:
      - test_register_success
      - test_register_duplicate
"""
        test_content = """
def test_register_success():
    pass

def test_register_duplicate():
    pass
"""
        root = _setup_temp_project(
            tmp_path,
            contract_content=contract_yaml,
            contract_format="yaml",
            test_files={"test_auth.py": test_content},
        )

        results = verify_contract_coverage(root, "T-0100")
        assert len(results) == 1
        assert results[0].is_clean
        assert results[0].missing_tests == []
        assert set(results[0].found_tests) == {"test_register_success", "test_register_duplicate"}

    def test_contract_missing_required_test(self, tmp_path: Path):
        """Contract requires a test that does not exist → violation."""
        contract_yaml = """contracts:
  - function: register
    tests_required:
      - test_register_success
      - test_register_duplicate
      - test_register_invalid_email
"""
        test_content = """
def test_register_success():
    pass

def test_register_duplicate():
    pass
"""
        root = _setup_temp_project(
            tmp_path,
            contract_content=contract_yaml,
            contract_format="yaml",
            test_files={"test_auth.py": test_content},
        )

        results = verify_contract_coverage(root, "T-0100")
        assert len(results) == 1
        assert not results[0].is_clean
        assert "test_register_invalid_email" in results[0].missing_tests

    def test_no_contract_file_returns_empty(self, tmp_path: Path):
        """No contract file → empty results (not a blocker for projects without contracts)."""
        root = _setup_temp_project(tmp_path)
        results = verify_contract_coverage(root, "T-0100")
        assert results == []

    def test_no_evidence_dir_returns_empty(self, tmp_path: Path):
        """No evidence directory → empty results."""
        root = tmp_path / "project"
        root.mkdir()
        results = verify_contract_coverage(root, "T-9999")
        assert results == []


# ═══════════════════════════════════════════════════════════════════════════
# check_contract_test_coverage tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckContractTestCoverage:
    """Tests for the check_contract_test_coverage helper function."""

    def test_all_tests_found_no_violations(self, tmp_path: Path):
        """All required tests exist → no violations."""
        contract_yaml = """contracts:
  - function: register
    tests_required:
      - test_register_success
"""
        test_content = "def test_register_success():\n    pass\n"
        root = _setup_temp_project(
            tmp_path,
            contract_content=contract_yaml,
            contract_format="yaml",
            test_files={"test_auth.py": test_content},
        )

        violations, has_contracts = check_contract_test_coverage(root, "T-0100")
        assert has_contracts is True
        assert violations == []

    def test_missing_test_returns_violation(self, tmp_path: Path):
        """Missing required test → violation returned."""
        contract_yaml = """contracts:
  - function: register
    tests_required:
      - test_register_success
      - test_missing_test
"""
        test_content = "def test_register_success():\n    pass\n"
        root = _setup_temp_project(
            tmp_path,
            contract_content=contract_yaml,
            contract_format="yaml",
            test_files={"test_auth.py": test_content},
        )

        violations, has_contracts = check_contract_test_coverage(root, "T-0100")
        assert has_contracts is True
        assert len(violations) == 1
        assert "test_missing_test" in violations[0]["missing_tests"]
        assert "message" in violations[0]
        assert "remediation" in violations[0]

    def test_no_contracts_returns_empty(self, tmp_path: Path):
        """No contract files → has_contracts=False, no violations."""
        root = _setup_temp_project(tmp_path)
        violations, has_contracts = check_contract_test_coverage(root, "T-0100")
        assert has_contracts is False
        assert violations == []


# ═══════════════════════════════════════════════════════════════════════════
# HardConstraints C10 integration tests
# ═══════════════════════════════════════════════════════════════════════════


class TestHardConstraintsC10:
    """Tests for HardConstraints.check_c10_contract_test_coverage."""

    def test_c10_no_contracts_no_violation(self, tmp_path: Path):
        """C10 with no contracts produces no violation."""
        root = _setup_temp_project(tmp_path)
        hc = HardConstraints()
        violations = hc.check_c10_contract_test_coverage(
            root=root, task_id="T-0100"
        )
        assert violations == []

    def test_c10_all_tests_found_no_violation(self, tmp_path: Path):
        """C10 with all tests found produces no violation."""
        contract_yaml = """contracts:
  - function: register
    tests_required:
      - test_register_success
"""
        test_content = "def test_register_success():\n    pass\n"
        root = _setup_temp_project(
            tmp_path,
            contract_content=contract_yaml,
            contract_format="yaml",
            test_files={"test_auth.py": test_content},
        )

        hc = HardConstraints()
        violations = hc.check_c10_contract_test_coverage(
            root=root, task_id="T-0100"
        )
        assert violations == []

    def test_c10_missing_test_returns_warning(self, tmp_path: Path):
        """C10 with missing test returns WARNING-level violation (SOFT by default)."""
        contract_yaml = """contracts:
  - function: register
    tests_required:
      - test_register_success
      - test_missing_test
"""
        test_content = "def test_register_success():\n    pass\n"
        root = _setup_temp_project(
            tmp_path,
            contract_content=contract_yaml,
            contract_format="yaml",
            test_files={"test_auth.py": test_content},
        )

        hc = HardConstraints()
        violations = hc.check_c10_contract_test_coverage(
            root=root, task_id="T-0100"
        )
        assert len(violations) == 1
        assert violations[0].constraint_id == ConstraintID.C10_CONTRACT_TEST_MISSING
        assert violations[0].severity == Severity.WARNING  # SOFT by default

    def test_c10_missing_root_or_task_id_no_violation(self):
        """C10 with None root or task_id returns no violation."""
        hc = HardConstraints()
        assert hc.check_c10_contract_test_coverage(root=None, task_id=None) == []
        assert hc.check_c10_contract_test_coverage(root=None, task_id="T-0100") == []


# ═══════════════════════════════════════════════════════════════════════════
# HardConstraints C11 integration tests
# ═══════════════════════════════════════════════════════════════════════════


class TestHardConstraintsC11:
    """Tests for HardConstraints.check_c11_file_limit."""

    def test_c11_within_limit_no_violation(self, tmp_path: Path):
        """C11 with allowed_paths within max_files produces no violation."""
        task_md = """# T-0100: Test task
allowed_paths:
  - src/auth.py
  - src/login.py
  - tests/test_auth.py
"""
        root = _setup_temp_project(
            tmp_path, task_id="T-0100", task_md_content=task_md
        )
        hc = HardConstraints()
        violations = hc.check_c11_file_limit(
            root=root, task_id="T-0100", max_files=5
        )
        assert violations == []

    def test_c11_exceeds_limit_returns_warning(self, tmp_path: Path):
        """C11 with allowed_paths exceeding max_files returns WARNING."""
        task_md = """# T-0100: Large task
allowed_paths:
  - src/auth.py
  - src/login.py
  - src/register.py
  - src/profile.py
  - src/admin.py
  - src/settings.py
  - src/dashboard.py
  - src/reports.py
  - src/analytics.py
  - src/notifications.py
  - src/api.py
  - src/webhooks.py
"""
        root = _setup_temp_project(
            tmp_path, task_id="T-0100", task_md_content=task_md
        )
        hc = HardConstraints()
        violations = hc.check_c11_file_limit(
            root=root, task_id="T-0100", max_files=5
        )
        assert len(violations) == 1
        assert violations[0].constraint_id == ConstraintID.C11_TASK_FILE_LIMIT_EXCEEDED
        assert violations[0].severity == Severity.WARNING  # SOFT by default

    def test_c11_governance_files_excluded(self, tmp_path: Path):
        """C11 excludes governance files (.ai/*, .zcode/*) from count."""
        task_md = """# T-0100: Task with governance files
allowed_paths:
  - src/auth.py
  - .ai/tasks/T-0100.md
  - .ai/evidence/T-0100/
  - .zcode/config.json
  - .ai/state.yaml
  - .ai/gates.yaml
  - .ai/task_graph.yaml
"""
        root = _setup_temp_project(
            tmp_path, task_id="T-0100", task_md_content=task_md
        )
        hc = HardConstraints()
        # Only src/auth.py should count (1 file), governance files excluded
        violations = hc.check_c11_file_limit(
            root=root, task_id="T-0100", max_files=5
        )
        assert violations == []

    def test_c11_missing_root_or_task_id_no_violation(self):
        """C11 with None root or task_id returns no violation."""
        hc = HardConstraints()
        assert hc.check_c11_file_limit(root=None, task_id=None) == []
        assert hc.check_c11_file_limit(root=None, task_id="T-0100") == []

    def test_c11_missing_task_file_returns_empty(self, tmp_path: Path):
        """C11 with missing task file returns no violation."""
        root = _setup_temp_project(tmp_path)  # No task_md_content
        hc = HardConstraints()
        violations = hc.check_c11_file_limit(
            root=root, task_id="T-0100", max_files=5
        )
        assert violations == []


# ═══════════════════════════════════════════════════════════════════════════
# _parse_allowed_paths_from_markdown tests
# ═══════════════════════════════════════════════════════════════════════════


class TestParseAllowedPaths:
    """Tests for _parse_allowed_paths_from_markdown."""

    def test_parse_yaml_block(self):
        """Parse allowed_paths from a YAML code block."""
        text = """# Task
```yaml
allowed_paths:
  - src/auth.py
  - tests/test_auth.py
```
"""
        paths = _parse_allowed_paths_from_markdown(text)
        assert paths == ["src/auth.py", "tests/test_auth.py"]

    def test_parse_plain_list(self):
        """Parse allowed_paths from a plain markdown list."""
        text = """# Task
allowed_paths:
  - src/login.py
  - src/register.py
"""
        paths = _parse_allowed_paths_from_markdown(text)
        assert paths == ["src/login.py", "src/register.py"]

    def test_parse_empty(self):
        """Empty text returns empty list."""
        paths = _parse_allowed_paths_from_markdown("")
        assert paths == []

    def test_parse_no_allowed_paths(self):
        """Text without allowed_paths returns empty list."""
        text = "# Task\n\nStatus: active\n"
        paths = _parse_allowed_paths_from_markdown(text)
        assert paths == []
