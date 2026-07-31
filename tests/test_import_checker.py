"""
Unit tests for loop_core.import_checker — Import authenticity verification (C9).

Tests cover:
- Declared dependencies pass without violations
- Undeclared third-party imports produce violations
- Stdlib imports are always valid
- Relative imports are always valid
- Submodule imports check only the top-level package
- Multi-file scanning aggregates all violations
- Missing dependency files produce warnings (not errors)
- check_c9_import_validity in HardConstraints
- C9 ConstraintID enum value
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

# Ensure loop_core is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.import_checker import (
    ImportChecker,
    ImportViolation,
    ImportCheckResult,
)
from loop_core.hard_constraints import (
    ConstraintID,
    HardConstraints,
    Severity,
)
from loop_core.state_machine import Phase


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def temp_project():
    """Create a temporary project directory with pyproject.toml and src/."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        yield root


def _write_file(path: Path, content: str):
    """Write content to a file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_pyproject(root: Path, dependencies: list[str] | None = None,
                     opt_deps: dict | None = None):
    """Write a minimal pyproject.toml with project dependencies."""
    lines = ['[build-system]', 'requires = ["setuptools>=68.0", "wheel"]',
             'build-backend = "setuptools.build_meta"', '',
             '[project]', 'name = "test-project"', 'version = "0.1.0"',
             'requires-python = ">=3.10"']
    if dependencies:
        deps_str = ", ".join(f'"{d}"' for d in dependencies)
        lines.append(f"dependencies = [{deps_str}]")
    if opt_deps:
        lines.append("")
        lines.append("[project.optional-dependencies]")
        for group, deps in opt_deps.items():
            deps_str = ", ".join(f'"{d}"' for d in deps)
            lines.append(f'{group} = [{deps_str}]')
    (root / "pyproject.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_requirements(root: Path, packages: list[str]):
    """Write a minimal requirements.txt."""
    (root / "requirements.txt").write_text(
        "\n".join(packages) + "\n", encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# ImportChecker Unit Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestImportCheckerBasics:
    """Basic import scanning functionality."""

    def test_valid_imports_in_declared_deps(self, temp_project):
        """Imports that match declared dependencies produce no violations."""
        _write_pyproject(temp_project, dependencies=["requests>=2.28", "numpy>=1.24"])
        _write_file(temp_project / "src" / "main.py",
                    "import requests\nimport numpy as np\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert len(result.violations) == 0
        assert result.total_files_scanned == 2  # __init__.py + main.py

    def test_undeclared_third_party_import(self, temp_project):
        """Undeclared third-party imports produce violations."""
        _write_pyproject(temp_project, dependencies=["requests>=2.28"])
        _write_file(temp_project / "src" / "main.py",
                    "import pandas\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert len(result.violations) == 1
        v = result.violations[0]
        assert v.import_name == "pandas"
        assert v.declared is False
        assert v.is_stdlib is False
        assert v.is_relative is False
        assert "main.py" in v.file_path

    def test_stdlib_import_no_violation(self, temp_project):
        """Stdlib imports (os, sys, pathlib) never produce violations."""
        _write_pyproject(temp_project, dependencies=[])  # no deps declared
        _write_file(temp_project / "src" / "main.py",
                    "import os\nimport sys\nfrom pathlib import Path\n"
                    "import json\nimport datetime\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert len(result.violations) == 0

    def test_relative_import_no_violation(self, temp_project):
        """Relative imports (from .module import X) are always valid."""
        _write_pyproject(temp_project, dependencies=[])
        _write_file(temp_project / "src" / "__init__.py", "")
        _write_file(temp_project / "src" / "main.py",
                    "from .utils import helper\nfrom .. import sibling\n")
        _write_file(temp_project / "src" / "utils.py", "def helper(): pass\n")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert len(result.violations) == 0

    def test_submodule_import_checks_top_level(self, temp_project):
        """Importing a submodule (e.g., numpy.linalg) checks the top-level package."""
        _write_pyproject(temp_project, dependencies=["numpy>=1.24"])
        _write_file(temp_project / "src" / "main.py",
                    "import numpy.linalg\nfrom scipy import optimize\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        # numpy is declared, scipy is not
        assert len(result.violations) == 1
        assert result.violations[0].import_name == "scipy"

    def test_multiple_files_aggregated(self, temp_project):
        """Scanning multiple files aggregates all violations."""
        _write_pyproject(temp_project, dependencies=["requests"])
        _write_file(temp_project / "src" / "__init__.py", "")
        _write_file(temp_project / "src" / "a.py", "import pandas\n")
        _write_file(temp_project / "src" / "b.py", "import flask\n")
        _write_file(temp_project / "src" / "sub" / "c.py", "import django\n")
        _write_file(temp_project / "src" / "sub" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        # 3 undeclared imports: pandas, flask, django
        assert len(result.violations) == 3
        import_names = {v.import_name for v in result.violations}
        assert import_names == {"pandas", "flask", "django"}

    def test_no_deps_file_warns(self, temp_project):
        """When no pyproject.toml or requirements.txt exists, warn but don't block."""
        # No pyproject.toml, no requirements.txt
        _write_file(temp_project / "src" / "main.py",
                    "import pandas\nimport numpy\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        # All third-party imports are flagged as undeclared
        assert len(result.violations) == 2
        # But warnings are present
        assert len(result.warnings) >= 1
        assert "pyproject.toml" in result.warnings[0].lower() or \
               "requirements.txt" in result.warnings[0].lower()

    def test_requirements_txt_parsed(self, temp_project):
        """Dependencies from requirements.txt are recognized."""
        _write_requirements(temp_project, ["requests>=2.28", "numpy"])
        _write_file(temp_project / "src" / "main.py",
                    "import requests\nimport numpy\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        # requests and numpy are declared in requirements.txt
        assert len(result.violations) == 0

    def test_project_local_modules_valid(self, temp_project):
        """Imports of project-local packages are always valid."""
        _write_pyproject(temp_project, dependencies=[])
        _write_file(temp_project / "my_package" / "__init__.py", "")
        _write_file(temp_project / "my_package" / "core.py", "VALUE = 42\n")
        _write_file(temp_project / "src" / "main.py",
                    "import my_package\nfrom my_package.core import VALUE\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert len(result.violations) == 0

    def test_optional_dependencies_recognized(self, temp_project):
        """Dependencies in [project.optional-dependencies] are recognized."""
        _write_pyproject(temp_project, dependencies=["requests"],
                         opt_deps={"dev": ["pytest>=7.0", "ruff>=0.1"]})
        _write_file(temp_project / "src" / "main.py",
                    "import pytest\nimport ruff\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert len(result.violations) == 0

    def test_scan_path_not_exist(self, temp_project):
        """Non-existent scan paths are skipped gracefully."""
        _write_pyproject(temp_project, dependencies=["requests"])
        _write_file(temp_project / "src" / "main.py", "import requests\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src", temp_project / "nonexistent"],
        )
        assert len(result.violations) == 0
        assert result.total_files_scanned >= 1

    def test_from_import_with_alias(self, temp_project):
        """'from X import Y as Z' is handled correctly."""
        _write_pyproject(temp_project, dependencies=["numpy"])
        _write_file(temp_project / "src" / "main.py",
                    "from numpy import array as arr\n"
                    "from pandas import DataFrame as df\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert len(result.violations) == 1
        assert result.violations[0].import_name == "pandas"

    def test_empty_files_no_error(self, temp_project):
        """Empty .py files produce no errors."""
        _write_pyproject(temp_project, dependencies=[])
        _write_file(temp_project / "src" / "__init__.py", "")
        _write_file(temp_project / "src" / "empty.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert len(result.violations) == 0

    def test_syntax_error_file_skipped(self, temp_project):
        """Files with syntax errors are skipped gracefully."""
        _write_pyproject(temp_project, dependencies=[])
        _write_file(temp_project / "src" / "broken.py",
                    "this is not valid Python {{{")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        # No crash, just no violations from the broken file
        assert result.total_files_scanned >= 1

    def test_hidden_dirs_skipped(self, temp_project):
        """Files in hidden directories (.__dotdir__) are skipped."""
        _write_pyproject(temp_project, dependencies=[])
        _write_file(temp_project / "src" / ".hidden" / "secret.py",
                    "import pandas\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        # .hidden directory is skipped
        assert len(result.violations) == 0

    def test_case_insensitive_dep_matching(self, temp_project):
        """Dependency matching is case-insensitive."""
        _write_pyproject(temp_project, dependencies=["Numpy>=1.24"])
        _write_file(temp_project / "src" / "main.py",
                    "import numpy\nimport NUMPY\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        # "numpy" and "NUMPY" match "Numpy" (case-insensitive)
        assert len(result.violations) == 0

    def test_import_statistics(self, temp_project):
        """Result contains accurate scan statistics."""
        _write_pyproject(temp_project, dependencies=["requests"])
        _write_file(temp_project / "src" / "__init__.py", "")
        _write_file(temp_project / "src" / "a.py",
                    "import os\nimport sys\nimport requests\nimport pandas\n")
        _write_file(temp_project / "src" / "b.py",
                    "from flask import Flask\n")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert result.total_files_scanned == 3  # __init__, a.py, b.py
        # 4 imports in a.py (os, sys, requests, pandas) + 1 in b.py (flask) = 5
        assert result.total_imports_checked == 5
        # pandas and flask are undeclared (os and sys are stdlib, requests declared)
        assert len(result.violations) == 2


# ═══════════════════════════════════════════════════════════════════════════
# C9 Constraint Integration Tests (HardConstraints)
# ═══════════════════════════════════════════════════════════════════════════


class TestC9HardConstraint:
    """Tests for C9 integration in HardConstraints.check_c9_import_validity."""

    def test_c9_constraint_id_exists(self):
        """C9_IMPORT_NOT_DECLARED is a valid ConstraintID."""
        cid = ConstraintID.C9_IMPORT_NOT_DECLARED
        assert cid.value == "C9-import-not-declared"
        assert isinstance(cid, ConstraintID)

    def test_check_c9_no_violations(self, temp_project):
        """check_c9_import_validity with valid deps returns no violations."""
        _write_pyproject(temp_project, dependencies=["requests>=2.28"])
        _write_file(temp_project / "src" / "__init__.py", "")
        _write_file(temp_project / "src" / "main.py", "import requests\n")

        hc = HardConstraints()
        violations = hc.check_c9_import_validity(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert len(violations) == 0

    def test_check_c9_with_undeclared_import(self, temp_project):
        """check_c9_import_validity flags undeclared imports as BLOCKER."""
        _write_pyproject(temp_project, dependencies=["requests"])
        _write_file(temp_project / "src" / "__init__.py", "")
        _write_file(temp_project / "src" / "main.py", "import pandas\n")

        hc = HardConstraints()
        violations = hc.check_c9_import_validity(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert len(violations) == 1
        v = violations[0]
        assert v.constraint_id == ConstraintID.C9_IMPORT_NOT_DECLARED
        assert v.severity == Severity.BLOCKER
        assert "pandas" in v.message

    def test_check_c9_with_no_deps_files(self, temp_project):
        """check_c9_import_validity warns when no dep files exist."""
        # No pyproject.toml or requirements.txt
        _write_file(temp_project / "src" / "__init__.py", "")
        _write_file(temp_project / "src" / "main.py", "import pandas\n")

        hc = HardConstraints()
        violations = hc.check_c9_import_validity(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        # All third-party imports are flagged
        blocker_violations = [v for v in violations if v.severity == Severity.BLOCKER]
        warning_violations = [v for v in violations if v.severity == Severity.WARNING]
        assert len(blocker_violations) >= 1  # undeclared import
        assert len(warning_violations) >= 1   # missing dep files warning

    def test_c9_in_check_all_s4_phase(self, temp_project):
        """check_all runs C9 when current_phase is S4_IMPLEMENTATION."""
        _write_pyproject(temp_project, dependencies=["requests"])
        _write_file(temp_project / "src" / "__init__.py", "")
        _write_file(temp_project / "src" / "main.py", "import pandas\n")

        hc = HardConstraints()
        ctx = {
            "current_phase": Phase.S4_IMPLEMENTATION,
            "target_phase": Phase.S5_QUALITY,
            "phase_gates": {},
            "gates": {},
            "tasks": [],
            "quality_results": {},
            "review_status": {},
            "evidence_list": [],
            "current_hashes": {},
            "root": temp_project,
            "scan_paths": [temp_project / "src"],
        }
        result = hc.check_all(ctx)
        c9_violations = [
            v for v in result.violations
            if v.constraint_id == ConstraintID.C9_IMPORT_NOT_DECLARED
        ]
        assert len(c9_violations) >= 1

    def test_c9_not_run_outside_s4_s5(self, temp_project):
        """check_all skips C9 when not in S4 or S5."""
        _write_pyproject(temp_project, dependencies=["requests"])
        _write_file(temp_project / "src" / "main.py", "import pandas\n")

        hc = HardConstraints()
        ctx = {
            "current_phase": Phase.S1_REQUIREMENTS,
            "target_phase": Phase.S2_ARCHITECTURE,
            "phase_gates": {},
            "gates": {},
            "tasks": [],
            "quality_results": {},
            "review_status": {},
            "evidence_list": [],
            "current_hashes": {},
            "root": temp_project,
            "scan_paths": [temp_project / "src"],
        }
        result = hc.check_all(ctx)
        c9_violations = [
            v for v in result.violations
            if v.constraint_id == ConstraintID.C9_IMPORT_NOT_DECLARED
        ]
        assert len(c9_violations) == 0


# ═══════════════════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge case handling for the import checker."""

    def test_future_import_no_violation(self, temp_project):
        """from __future__ import annotations is stdlib and valid."""
        _write_pyproject(temp_project, dependencies=[])
        _write_file(temp_project / "src" / "main.py",
                    "from __future__ import annotations\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert len(result.violations) == 0

    def test_dataclasses_import_valid(self, temp_project):
        """Importing dataclasses (stdlib) is valid."""
        _write_pyproject(temp_project, dependencies=[])
        _write_file(temp_project / "src" / "main.py",
                    "from dataclasses import dataclass, field\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert len(result.violations) == 0

    def test_typing_imports_valid(self, temp_project):
        """Typing-related imports (typing, collections.abc) are valid."""
        _write_pyproject(temp_project, dependencies=[])
        _write_file(temp_project / "src" / "main.py",
                    "from typing import Any, Optional\n"
                    "from collections import defaultdict\n"
                    "from collections.abc import Mapping\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert len(result.violations) == 0

    def test_predeclared_deps_override(self, temp_project):
        """Providing declared_deps parameter skips auto-detection from files."""
        # No pyproject.toml or requirements.txt
        _write_file(temp_project / "src" / "main.py",
                    "import numpy\nimport pandas\n")
        _write_file(temp_project / "src" / "__init__.py", "")

        # Pass declared_deps explicitly
        result = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
            declared_deps={"numpy"},
        )
        # numpy is declared, pandas is not
        assert len(result.violations) == 1
        assert result.violations[0].import_name == "pandas"


# ═══════════════════════════════════════════════════════════════════════════
# Cache freshness (T-0085 conditional-GO item 3)
# ═══════════════════════════════════════════════════════════════════════════


class TestLocalModuleCacheFreshness:
    """The project-local module snapshot must be per-scan, not a module-level
    cache: files created after the first scan per root must be recognized on
    the next scan instead of being falsely flagged as undeclared."""

    def test_new_module_created_after_first_scan_is_local(self, temp_project):
        """Run C9 twice in the same process; a nested .py file created between
        the runs must be treated as project-local on the second run.

        The module is created NESTED (src/nested/freshmod.py) so detection
        requires the tree-walk snapshot — the exact code path the old
        _LOCAL_MODULE_CACHE served with a never-invalidated per-root value.
        """
        _write_pyproject(temp_project, dependencies=[])
        _write_file(temp_project / "src" / "__init__.py", "")
        _write_file(temp_project / "src" / "main.py", "import freshmod\n")

        # Run 1: freshmod does not exist yet -> undeclared
        first = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert any(v.import_name == "freshmod" for v in first.violations), \
            [v.import_name for v in first.violations]

        # Create the module AFTER the first scan (same root, same process)
        _write_file(temp_project / "src" / "nested" / "freshmod.py", "VALUE = 1\n")

        # Run 2: freshmod must now be recognized as project-local
        second = ImportChecker.check_directory(
            root=temp_project,
            scan_paths=[temp_project / "src"],
        )
        assert not any(v.import_name == "freshmod" for v in second.violations), \
            [v.import_name for v in second.violations]

    def test_new_module_recognized_through_c9_kernel(self, temp_project):
        """Reviewer probe shape: run the C9 kernel check
        (HardConstraints.check_c9_import_validity, the entry point
        EnforcementHub uses) before and after creating a new nested module —
        the second run must NOT flag it as undeclared."""
        _write_pyproject(temp_project, dependencies=[])
        _write_file(temp_project / "src" / "__init__.py", "")
        _write_file(temp_project / "src" / "app.py", "import newmod\n")

        hc = HardConstraints()
        first = hc.check_c9_import_validity(
            root=temp_project, scan_paths=[temp_project / "src"])
        assert any("newmod" in v.message for v in first), [v.message for v in first]

        _write_file(temp_project / "src" / "sub" / "newmod.py", "VALUE = 1\n")

        second = hc.check_c9_import_validity(
            root=temp_project, scan_paths=[temp_project / "src"])
        assert not any("newmod" in v.message for v in second), \
            [v.message for v in second]
