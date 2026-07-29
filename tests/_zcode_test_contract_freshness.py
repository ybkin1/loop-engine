import pytest; pytest.skip('zcode-specific: requires .zcode/tools',allow_module_level=True)
"""
Unit tests for role contract freshness and completeness checks in validate_state.

Covers:
- check_role_contract_freshness: age, phase mismatch, stale markers
- check_role_contract_completeness: missing required fields
- check_role_file_existence: missing CONTRACT.yaml / THINKING_FRAMEWORK.md / INTERNAL_LOOP.md
- check_cross_role_consistency: duplicate role_ids, projection coverage, quality dims, veto cycles
"""
from __future__ import annotations

import os
import sys
import tempfile
import textwrap
import time
from pathlib import Path

# Ensure the project root is on sys.path so we can import .zcode.tools modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".zcode" / "tools"))

import pytest

from validate_state import (
    _agent_role_dirs,
    check_role_contract_freshness,
    check_role_contract_completeness,
    check_role_file_existence,
    check_cross_role_consistency,
    CONTRACT_REQUIRED_FIELDS,
    MAX_CONTRACT_AGE_DAYS,
)


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_project(
    agents: dict[str, dict[str, str | None]] | None = None,
    state_yaml: str | None = None,
) -> Path:
    """Create a temp project directory with agents/ and .ai/ subdirectories.

    Args:
        agents: dict mapping role_dir_name -> dict of filename -> content (or None to skip file).
        state_yaml: optional content for .ai/state.yaml.

    Returns:
        Path to the temporary project root.
    """
    root = Path(tempfile.mkdtemp())
    ai_dir = root / ".ai"
    ai_dir.mkdir(parents=True, exist_ok=True)

    # Write state.yaml
    if state_yaml is None:
        state_yaml = "current_phase: S6-delivery\ncurrent_task_id: T-0001\n"
    (ai_dir / "state.yaml").write_text(state_yaml, encoding="utf-8")

    # Create agent directories and files
    if agents:
        agents_dir = root / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        for role_name, files in agents.items():
            role_dir = agents_dir / role_name
            role_dir.mkdir(parents=True, exist_ok=True)
            for fname, content in files.items():
                if content is not None:
                    (role_dir / fname).write_text(content, encoding="utf-8")

    return root


def _contract_yaml(**overrides) -> str:
    """Build a minimal valid CONTRACT.yaml with sensible defaults."""
    import yaml

    data = {
        "role_id": overrides.pop("role_id", "test-role"),
        "identity": overrides.pop("identity", {"title": "Test Role", "experience": "1 year"}),
        "fixed_stance": overrides.pop("fixed_stance", ["I test things."]),
        "responsibilities": overrides.pop("responsibilities", ["Write tests."]),
        "prohibitions": overrides.pop("prohibitions", ["No cheating."]),
        "veto_power": overrides.pop("veto_power", ["If tests fail -> veto"]),
        "input_artifacts": overrides.pop("input_artifacts", ["code"]),
        "output_artifacts": overrides.pop("output_artifacts", ["report"]),
        "quality_standards": overrides.pop("quality_standards", ["80% coverage"]),
        "projection_rules": overrides.pop(
            "projection_rules",
            {
                "include_sections": ["project", "modules"],
                "exclude_sections": ["pages"],
                "quality_dimensions": ["Is testing complete?"],
            },
        ),
    }
    # Merge any remaining overrides at top level
    data.update(overrides)
    return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)


# ── Tests: _agent_role_dirs ────────────────────────────────────────────────


class TestAgentRoleDirs:
    def test_empty_project_no_agents_dir(self):
        root = _make_project()
        result = _agent_role_dirs(root)
        assert result == []

    def test_ignores_references_dir(self):
        root = _make_project(agents={
            "ref-role": {"CONTRACT.yaml": _contract_yaml(role_id="ref-role")},
        })
        ref_dir = root / "agents" / "references"
        ref_dir.mkdir(parents=True, exist_ok=True)
        (ref_dir / "README.md").write_text("ref", encoding="utf-8")

        result = _agent_role_dirs(root)
        names = [d.name for d in result]
        assert "references" not in names
        assert "ref-role" in names

    def test_skips_files_in_agents_root(self):
        root = _make_project()
        agents_dir = root / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "README.md").write_text("readme", encoding="utf-8")
        result = _agent_role_dirs(root)
        assert result == []


# ── Tests: check_role_contract_freshness ───────────────────────────────────


class TestRoleContractFreshness:
    def test_complete_contract_no_errors(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": _contract_yaml(role_id="qa"),
                "THINKING_FRAMEWORK.md": "# Framework\n",
                "INTERNAL_LOOP.md": "# Loop\n",
            },
        })
        errors = check_role_contract_freshness(root)
        assert errors == []

    def test_contract_not_present_skipped(self):
        """Missing CONTRACT.yaml is handled by check_role_file_existence, not freshness."""
        root = _make_project(agents={
            "qa": {
                "THINKING_FRAMEWORK.md": "# Framework\n",
                "INTERNAL_LOOP.md": "# Loop\n",
            },
        })
        errors = check_role_contract_freshness(root)
        assert errors == []

    def test_phase_mismatch_detected(self):
        root = _make_project(
            state_yaml="current_phase: S6-delivery\n",
            agents={
                "qa": {
                    "CONTRACT.yaml": _contract_yaml(role_id="qa", phase="S0-init"),
                },
            },
        )
        errors = check_role_contract_freshness(root)
        assert any("phase" in e.lower() for e in errors)

    def test_phase_match_no_error(self):
        root = _make_project(
            state_yaml="current_phase: S6-delivery\n",
            agents={
                "qa": {
                    "CONTRACT.yaml": _contract_yaml(role_id="qa", phase="S6-delivery"),
                },
            },
        )
        errors = check_role_contract_freshness(root)
        phase_errors = [e for e in errors if "phase" in e.lower()]
        assert phase_errors == []

    def test_stale_marker_detected(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": _contract_yaml(role_id="qa") + "\n# deprecated: use new contract\n",
            },
        })
        errors = check_role_contract_freshness(root)
        assert any("stale marker" in e.lower() for e in errors)

    def test_obsolete_marker_detected(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": _contract_yaml(role_id="qa") + "\n# This contract is obsolete.\n",
            },
        })
        errors = check_role_contract_freshness(root)
        assert any("stale marker" in e.lower() for e in errors)

    def test_empty_contract_file_no_crash(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": "",
            },
        })
        errors = check_role_contract_freshness(root)
        # Should not raise; empty dict from load_yaml is fine
        assert isinstance(errors, list)

    def test_corrupt_contract_no_crash(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": "\x00\x00\x00invalid binary\ufffd",
            },
        })
        errors = check_role_contract_freshness(root)
        assert isinstance(errors, list)


# ── Tests: check_role_contract_completeness ────────────────────────────────


class TestRoleContractCompleteness:
    def test_complete_contract_no_errors(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": _contract_yaml(role_id="qa"),
            },
        })
        errors = check_role_contract_completeness(root)
        assert errors == []

    def test_missing_required_fields_reported(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": "role_id: qa\nidentity:\n  title: Test\n",
            },
        })
        errors = check_role_contract_completeness(root)
        assert len(errors) >= 1
        assert any("missing required fields" in e.lower() for e in errors)

    def test_empty_contract_reported(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": "",
            },
        })
        errors = check_role_contract_completeness(root)
        assert any("empty" in e.lower() for e in errors)

    def test_corrupt_yaml_reported(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": ":: not valid yaml :: {{[[",
            },
        })
        errors = check_role_contract_completeness(root)
        assert any("cannot parse" in e.lower() for e in errors)

    def test_non_dict_yaml_reported(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": "- item1\n- item2\n",
            },
        })
        errors = check_role_contract_completeness(root)
        assert any("not a valid yaml mapping" in e.lower() for e in errors)

    def test_missing_contract_skipped(self):
        root = _make_project(agents={
            "qa": {},
        })
        errors = check_role_contract_completeness(root)
        assert errors == []

    def test_all_fields_missing_reported_individually(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": "role_id: qa\n",
            },
        })
        errors = check_role_contract_completeness(root)
        error_text = errors[0].lower()
        # Should list the missing fields
        for field in CONTRACT_REQUIRED_FIELDS:
            assert field in error_text


# ── Tests: check_role_file_existence ───────────────────────────────────────


class TestRoleFileExistence:
    def test_all_files_present_no_errors(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": _contract_yaml(role_id="qa"),
                "THINKING_FRAMEWORK.md": "# TF\n",
                "INTERNAL_LOOP.md": "# IL\n",
            },
        })
        errors = check_role_file_existence(root)
        assert errors == []

    def test_missing_contract_reported(self):
        root = _make_project(agents={
            "qa": {
                "THINKING_FRAMEWORK.md": "# TF\n",
                "INTERNAL_LOOP.md": "# IL\n",
            },
        })
        errors = check_role_file_existence(root)
        assert any("CONTRACT.yaml" in e for e in errors)

    def test_missing_thinking_framework_reported(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": _contract_yaml(role_id="qa"),
                "INTERNAL_LOOP.md": "# IL\n",
            },
        })
        errors = check_role_file_existence(root)
        assert any("THINKING_FRAMEWORK.md" in e for e in errors)

    def test_missing_internal_loop_reported(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": _contract_yaml(role_id="qa"),
                "THINKING_FRAMEWORK.md": "# TF\n",
            },
        })
        errors = check_role_file_existence(root)
        assert any("INTERNAL_LOOP.md" in e for e in errors)

    def test_all_three_missing_reported(self):
        root = _make_project(agents={
            "qa": {},
        })
        errors = check_role_file_existence(root)
        assert len(errors) >= 1
        err = errors[0]
        assert "CONTRACT.yaml" in err
        assert "THINKING_FRAMEWORK.md" in err
        assert "INTERNAL_LOOP.md" in err

    def test_empty_agents_dir_no_errors(self):
        root = _make_project()
        agents_dir = root / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        # No subdirectories — _agent_role_dirs returns empty list
        errors = check_role_file_existence(root)
        assert errors == []

    def test_multiple_roles_each_checked(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": _contract_yaml(role_id="qa"),
                "THINKING_FRAMEWORK.md": "# TF\n",
                "INTERNAL_LOOP.md": "# IL\n",
            },
            "dev": {
                "CONTRACT.yaml": _contract_yaml(role_id="dev"),
                # missing THINKING_FRAMEWORK.md and INTERNAL_LOOP.md
            },
        })
        errors = check_role_file_existence(root)
        assert any("dev" in e for e in errors)
        assert not any("qa" in e for e in errors)


# ── Tests: check_cross_role_consistency ────────────────────────────────────


class TestCrossRoleConsistency:
    def test_no_errors_with_distinct_roles(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": _contract_yaml(
                    role_id="quality-engineer",
                    projection_rules={
                        "include_sections": ["project", "modules", "database"],
                        "exclude_sections": ["pages"],
                        "quality_dimensions": ["Is testing complete?"],
                    },
                ),
            },
            "dev": {
                "CONTRACT.yaml": _contract_yaml(
                    role_id="developer",
                    projection_rules={
                        "include_sections": ["project", "api_endpoints", "pages"],
                        "exclude_sections": [],
                        "developer_dimensions": ["Is interface clear?"],
                    },
                ),
            },
        })
        errors = check_cross_role_consistency(root)
        assert errors == []

    def test_duplicate_role_id_detected(self):
        root = _make_project(agents={
            "dir-a": {
                "CONTRACT.yaml": _contract_yaml(role_id="same-id"),
            },
            "dir-b": {
                "CONTRACT.yaml": _contract_yaml(role_id="same-id"),
            },
        })
        errors = check_cross_role_consistency(root)
        assert any("duplicate role_id" in e.lower() for e in errors)

    def test_uncovered_dimensions_reported(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": _contract_yaml(
                    role_id="qa",
                    projection_rules={
                        "include_sections": ["project"],
                        "exclude_sections": [],
                    },
                ),
            },
        })
        errors = check_cross_role_consistency(root)
        assert any("not covered" in e.lower() for e in errors)

    def test_no_quality_role_warns(self):
        root = _make_project(agents={
            "dev": {
                "CONTRACT.yaml": _contract_yaml(
                    role_id="dev",
                    projection_rules={
                        "include_sections": ["project"],
                        "exclude_sections": [],
                    },
                ),
            },
        })
        errors = check_cross_role_consistency(root)
        assert any("quality coverage may be unassigned" in e.lower() for e in errors)

    def test_veto_cycle_detected(self):
        root = _make_project(agents={
            "role-a": {
                "CONTRACT.yaml": _contract_yaml(
                    role_id="role-a",
                    veto_power=["If role-b approves without testing -> veto"],
                ),
            },
            "role-b": {
                "CONTRACT.yaml": _contract_yaml(
                    role_id="role-b",
                    veto_power=["If role-a approves without review -> veto"],
                ),
            },
        })
        errors = check_cross_role_consistency(root)
        assert any("circular veto" in e.lower() for e in errors)

    def test_single_role_no_consistency_errors(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": _contract_yaml(
                    role_id="qa",
                    projection_rules={
                        "include_sections": ["project", "pages", "api_endpoints", "modules", "database"],
                        "exclude_sections": [],
                        "quality_dimensions": ["Is quality OK?"],
                    },
                ),
            },
        })
        errors = check_cross_role_consistency(root)
        assert errors == []

    def test_missing_contracts_skipped_gracefully(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": _contract_yaml(role_id="qa"),
            },
            "incomplete": {
                # No CONTRACT.yaml
            },
        })
        errors = check_cross_role_consistency(root)
        # Should not crash and should process the role that has a contract
        assert isinstance(errors, list)

    def test_corrupt_contracts_skipped_gracefully(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": _contract_yaml(role_id="qa"),
            },
            "bad": {
                "CONTRACT.yaml": ":: not yaml :: [[{{",
            },
        })
        errors = check_cross_role_consistency(root)
        assert isinstance(errors, list)

    def test_all_warnings_prefixed(self):
        root = _make_project(agents={
            "qa": {
                "CONTRACT.yaml": _contract_yaml(role_id="qa", phase="S0-init"),
            },
        })
        freshness_errors = check_role_contract_freshness(root)
        completeness_errors = check_role_contract_completeness(root)
        file_errors = check_role_file_existence(root)
        consistency_errors = check_cross_role_consistency(root)

        all_errors = freshness_errors + completeness_errors + file_errors + consistency_errors
        for error in all_errors:
            assert error.startswith("[warn]"), f"Error should start with [warn]: {error[:80]}"
