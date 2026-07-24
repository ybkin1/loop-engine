"""
test_gate_guard_lifecycle.py — Tests for gate_guard.py Gate lifecycle logic (T-0046).

Tests the _check_gate_lifecycle function to ensure:
- pending Gate returns block
- approved + approved_not_started returns allow
- approved + in_progress returns allow
- approved + completed returns skip (not active)
- rejected/blocked returns block
- current_gate_id pointing to non-existent gate returns block_missing (fail-closed)
- current_gate_id belonging to other task returns block_task_mismatch (fail-closed)
- Gate allowed_paths still constrained by path_guard / task scope
"""
import os
import sys
import tempfile
import shutil
import pytest

# Ensure hooks/scripts is importable
HOOKS_DIR = os.path.join(os.path.dirname(__file__), "..", "hooks", "scripts")
sys.path.insert(0, os.path.abspath(HOOKS_DIR))

from gate_guard import _check_gate_lifecycle, _load_gate_data, EXIT_PASS, EXIT_BLOCK


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary governance project with .ai/state.yaml and .ai/gates.yaml."""
    ai_dir = tmp_path / ".ai"
    ai_dir.mkdir()

    state_content = (
        "schema_version: 1\n"
        "current_task_id: T-0046\n"
        "current_gate_id: G-TEST\n"
        "current_phase: S6-delivery\n"
    )
    (ai_dir / "state.yaml").write_text(state_content, encoding="utf-8")
    return tmp_path


def _write_gates(tmp_path, gates_yaml_content):
    ai_dir = tmp_path / ".ai"
    (ai_dir / "gates.yaml").write_text(gates_yaml_content, encoding="utf-8")


class TestGateLifecyclePending:
    def test_pending_gate_returns_block(self, temp_project):
        """pending Gate should return block_pending."""
        _write_gates(temp_project, (
            "gates:\n"
            "- id: G-TEST\n"
            "  task_id: T-0046\n"
            "  status: pending\n"
        ))
        state = {"current_task_id": "T-0046", "current_gate_id": "G-TEST"}
        result = _check_gate_lifecycle(temp_project, "G-TEST", state)
        assert result == "block_pending"


class TestGateLifecycleApproved:
    def test_approved_not_started_returns_allow(self, temp_project):
        """approved + approved_not_started should return allow."""
        _write_gates(temp_project, (
            "gates:\n"
            "- id: G-TEST\n"
            "  task_id: T-0046\n"
            "  status: approved\n"
            "  execution_status: approved_not_started\n"
        ))
        state = {"current_task_id": "T-0046", "current_gate_id": "G-TEST"}
        result = _check_gate_lifecycle(temp_project, "G-TEST", state)
        assert result == "allow"

    def test_approved_in_progress_returns_allow(self, temp_project):
        """approved + in_progress should return allow."""
        _write_gates(temp_project, (
            "gates:\n"
            "- id: G-TEST\n"
            "  task_id: T-0046\n"
            "  status: approved\n"
            "  execution_status: in_progress\n"
        ))
        state = {"current_task_id": "T-0046", "current_gate_id": "G-TEST"}
        result = _check_gate_lifecycle(temp_project, "G-TEST", state)
        assert result == "allow"

    def test_approved_completed_returns_skip(self, temp_project):
        """approved + completed should return skip (not active execution gate)."""
        _write_gates(temp_project, (
            "gates:\n"
            "- id: G-TEST\n"
            "  task_id: T-0046\n"
            "  status: approved\n"
            "  execution_status: completed\n"
        ))
        state = {"current_task_id": "T-0046", "current_gate_id": "G-TEST"}
        result = _check_gate_lifecycle(temp_project, "G-TEST", state)
        assert result == "skip"

    def test_approved_no_execution_status_returns_allow_legacy(self, temp_project):
        """approved with no execution_status → legacy gate, allow."""
        _write_gates(temp_project, (
            "gates:\n"
            "- id: G-TEST\n"
            "  task_id: T-0046\n"
            "  status: approved\n"
        ))
        state = {"current_task_id": "T-0046", "current_gate_id": "G-TEST"}
        result = _check_gate_lifecycle(temp_project, "G-TEST", state)
        assert result == "allow_legacy"


class TestGateLifecycleRejectedBlocked:
    def test_rejected_returns_block(self, temp_project):
        """rejected gate should return block_rejected."""
        _write_gates(temp_project, (
            "gates:\n"
            "- id: G-TEST\n"
            "  task_id: T-0046\n"
            "  status: rejected\n"
        ))
        state = {"current_task_id": "T-0046", "current_gate_id": "G-TEST"}
        result = _check_gate_lifecycle(temp_project, "G-TEST", state)
        assert result == "block_rejected"

    def test_blocked_returns_block(self, temp_project):
        """blocked gate should return block_rejected."""
        _write_gates(temp_project, (
            "gates:\n"
            "- id: G-TEST\n"
            "  task_id: T-0046\n"
            "  status: blocked\n"
        ))
        state = {"current_task_id": "T-0046", "current_gate_id": "G-TEST"}
        result = _check_gate_lifecycle(temp_project, "G-TEST", state)
        assert result == "block_rejected"


class TestGateLifecycleFailClosed:
    def test_nonexistent_gate_returns_block_missing(self, temp_project):
        """current_gate_id pointing to non-existent gate → fail-closed."""
        _write_gates(temp_project, "gates:\n- id: G-OTHER\n  status: approved\n")
        state = {"current_task_id": "T-0046", "current_gate_id": "G-NONEXISTENT"}
        result = _check_gate_lifecycle(temp_project, "G-NONEXISTENT", state)
        assert result == "block_missing"

    def test_gate_from_other_task_returns_task_mismatch(self, temp_project):
        """Gate belonging to a different task → fail-closed."""
        _write_gates(temp_project, (
            "gates:\n"
            "- id: G-TEST\n"
            "  task_id: T-0099\n"
            "  status: approved\n"
            "  execution_status: in_progress\n"
        ))
        state = {"current_task_id": "T-0046", "current_gate_id": "G-TEST"}
        result = _check_gate_lifecycle(temp_project, "G-TEST", state)
        assert result == "block_task_mismatch"

    def test_empty_gates_file_returns_block_missing(self, temp_project):
        """Empty gates.yaml → gate not found → fail-closed."""
        _write_gates(temp_project, "gates: []\n")
        state = {"current_task_id": "T-0046", "current_gate_id": "G-TEST"}
        result = _check_gate_lifecycle(temp_project, "G-TEST", state)
        assert result == "block_missing"

    def test_no_gates_file_returns_block_missing(self, temp_project):
        """Missing gates.yaml → gate not found → fail-closed."""
        gates_file = temp_project / ".ai" / "gates.yaml"
        if gates_file.exists():
            gates_file.unlink()
        state = {"current_task_id": "T-0046", "current_gate_id": "G-TEST"}
        result = _check_gate_lifecycle(temp_project, "G-TEST", state)
        assert result == "block_missing"


class TestGateScopeConstraint:
    def test_approved_gate_still_requires_path_constraint(self, temp_project):
        """Gate approved does NOT mean all paths are allowed.
        Path constraint is enforced by path_guard, not gate_guard.
        This test verifies gate_guard allows execution (exit 0)
        but path scope is a separate concern."""
        _write_gates(temp_project, (
            "gates:\n"
            "- id: G-TEST\n"
            "  task_id: T-0046\n"
            "  status: approved\n"
            "  execution_status: in_progress\n"
            "  allowed_paths:\n"
            "    - .ai/tasks/T-0046.md\n"
            "    - .ai/state.yaml\n"
        ))
        state = {"current_task_id": "T-0046", "current_gate_id": "G-TEST"}
        result = _check_gate_lifecycle(temp_project, "G-TEST", state)
        # gate_guard allows execution; path_guard constrains which files
        assert result == "allow"
