# -*- coding: utf-8 -*-
"""
Unit tests for loop_core.context_controller — ContextController authorization engine.

Covers:
  - Governance file writes with / without pending gates
  - Protected path ASK_USER
  - High-risk action DENY
  - Task scope: in allowed_paths → ALLOW, out of scope → DENY
  - Pending gate + allowed_paths → ALLOW (design doc deadlock fix)
  - No task, non-governance write → DENY (fail-closed)
  - Decision-recording exemption (.ai/gates.yaml always allowed)
  - Non-file actions (LAUNCH_ROLE etc.)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# Ensure loop_core is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.context_controller import (  # noqa: E402
    Action,
    AuthRequest,
    AuthResult,
    ContextController,
    Decision,
)


# ── Fixture Helpers ─────────────────────────────────────────────────────

def _make_project(tmp: str, **files: str) -> Path:
    """Create a minimal project directory with given file contents.

    Key-value pairs: relative_path -> content.
    Directories are created automatically.
    """
    root = Path(tmp)
    for rel_path, content in files.items():
        fpath = root / rel_path
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding="utf-8")
    return root


def _ctrl(root: Path) -> ContextController:
    return ContextController(root)


# ── State / Gate / Task fixtures ────────────────────────────────────────

STATE_NO_TASK = """\
schema_version: 1
project_name: test
current_phase: S4-implementation
loop_mode: FULL
"""

STATE_WITH_TASK = """\
schema_version: 1
project_name: test
current_phase: S4-implementation
loop_mode: FULL
current_task_id: T-0001
"""

STATE_WITH_TASK_AND_GATE = """\
schema_version: 1
project_name: test
current_phase: S2-architecture
loop_mode: FULL
current_task_id: T-0001
current_gate_id: G-DESIGN
"""

GATES_NONE_PENDING = """\
gates:
  - id: G-IMPLEMENTATION
    task_id: T-0001
    gate_type: implementation
    status: approved
    allowed_paths:
      - src/
"""

GATES_ONE_PENDING = """\
gates:
  - id: G-DESIGN
    task_id: T-0001
    gate_type: design
    status: pending
    allowed_paths:
      - .ai/evidence/design/
      - docs/design/
  - id: G-IMPLEMENTATION
    task_id: T-0001
    gate_type: implementation
    status: approved
    allowed_paths:
      - src/
"""

GATES_PENDING_NO_PATHS = """\
gates:
  - id: G-DESIGN
    task_id: T-0001
    gate_type: design
    status: pending
"""

GATES_MULTI_PENDING = """\
gates:
  - id: G-DESIGN
    task_id: T-0001
    gate_type: design
    status: pending
    allowed_paths:
      - .ai/evidence/design/
  - id: G-REVIEW
    task_id: T-0001
    gate_type: review
    status: pending
    allowed_paths:
      - .ai/evidence/review/
"""

TASK_CONTRACT = """\
# Task T-0001

allowed_paths:
  - src/
  - lib/
  - tests/
  - docs/

developer_agent_id: dev-001
reviewer_agent_id: rev-001
"""

TASK_CONTRACT_SMALL = """\
# Task T-0001

allowed_paths:
  - src/module/
"""

TASK_CONTRACT_NO_PATHS = """\
# Task T-0001

developer_agent_id: dev-001
"""


# ── Tests ───────────────────────────────────────────────────────────────

class TestGovernanceFileWrite(unittest.TestCase):
    """Governance file writes: .ai/, .zcode/tools/, .zcode/skills/."""

    def test_governance_no_pending_gate_allows(self):
        """Governance file write with no pending gate → ALLOW."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/gates.yaml": GATES_NONE_PENDING})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".ai/evidence/test.md"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)
            self.assertIn("no pending gates", result.reason.lower())

    def test_governance_no_gates_file_allows(self):
        """Governance file write without gates.yaml → ALLOW."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".ai/evidence/test.md"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)
            self.assertIn("no pending gates", result.reason.lower())

    def test_governance_pending_gate_in_allowed_paths_allows(self):
        """Governance file in pending gate's allowed_paths → ALLOW."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK_AND_GATE,
                   ".ai/gates.yaml": GATES_ONE_PENDING})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".ai/evidence/design/arch.md"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)
            self.assertIn("allowed_paths", result.reason.lower())
            self.assertIn("G-DESIGN", result.reason)

    def test_governance_pending_gate_not_in_allowed_paths_denies(self):
        """Governance file NOT in pending gate's allowed_paths → DENY."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK_AND_GATE,
                   ".ai/gates.yaml": GATES_ONE_PENDING})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".ai/other/random.md"),
            ))
            self.assertEqual(result.decision, Decision.DENY)

    def test_governance_pending_gate_no_allowed_paths_denies(self):
        """Governance file with pending gate that has no allowed_paths → DENY."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK_AND_GATE,
                   ".ai/gates.yaml": GATES_PENDING_NO_PATHS})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".ai/evidence/test.md"),
            ))
            self.assertEqual(result.decision, Decision.DENY)

    def test_governance_zcode_tools_prefix(self):
        """Write to .zcode/tools/ → DENY by loop_core (host paths handled by hooks)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".zcode/tools/mytool/config.json"),
            ))
            # loop_core does not know about .zcode/ — governance decisions
            # for host-specific paths are injected by hooks/path_guard
            self.assertEqual(result.decision, Decision.DENY)

    def test_governance_zcode_skills_prefix(self):
        """Write to .zcode/skills/ → DENY by loop_core (host paths handled by hooks)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".zcode/skills/myskill/SKILL.md"),
            ))
            self.assertEqual(result.decision, Decision.DENY)

    def test_gates_yaml_always_allowed(self):
        """.ai/gates.yaml is always ALLOW (decision-recording exemption)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK_AND_GATE,
                   ".ai/gates.yaml": GATES_ONE_PENDING})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".ai/gates.yaml"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)
            self.assertIn("decision-recording", result.reason.lower())

    def test_multi_pending_gate_second_has_path(self):
        """Target in second pending gate's allowed_paths → ALLOW."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK_AND_GATE,
                   ".ai/gates.yaml": GATES_MULTI_PENDING})
            ctrl = _ctrl(root)
            # In G-REVIEW's scope
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".ai/evidence/review/report.md"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)
            self.assertIn("G-REVIEW", result.reason)


class TestProtectedPath(unittest.TestCase):
    """Protected paths trigger ASK_USER."""

    def test_agents_md_triggers_ask_user(self):
        """Write to AGENTS.md → ASK_USER."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / "AGENTS.md"),
            ))
            self.assertEqual(result.decision, Decision.ASK_USER)
            self.assertIn("AGENTS.md", result.reason)

    def test_zcode_config_json_triggers_ask_user(self):
        """Write to .zcode/config.json → DENY by loop_core (host paths handled by hooks/path_guard)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".zcode/config.json"),
            ))
            # loop_core does not know about .zcode/ — protection decisions
            # for host-specific paths are injected by hooks/path_guard
            self.assertEqual(result.decision, Decision.DENY)


class TestHighRiskAction(unittest.TestCase):
    """High-risk actions trigger DENY."""

    def test_install_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.INSTALL,
            ))
            self.assertEqual(result.decision, Decision.DENY)
            self.assertIn("high-risk", result.reason.lower())

    def test_upgrade_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.UPGRADE,
            ))
            self.assertEqual(result.decision, Decision.DENY)

    def test_rollback_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.ROLLBACK,
            ))
            self.assertEqual(result.decision, Decision.DENY)

    def test_gate_transition_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.GATE_TRANSITION,
            ))
            self.assertEqual(result.decision, Decision.DENY)


class TestTaskScope(unittest.TestCase):
    """Task scope enforcement: in allowed_paths → ALLOW, out → DENY."""

    def test_in_allowed_paths_allows(self):
        """Target in task allowed_paths → ALLOW."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/tasks/T-0001.md": TASK_CONTRACT})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / "src/main.py"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)
            self.assertIn("allowed scope", result.reason.lower())

    def test_subdirectory_in_scope_allows(self):
        """Target in subdirectory of allowed_path → ALLOW."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/tasks/T-0001.md": TASK_CONTRACT})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / "src/sub/module.py"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)

    def test_out_of_scope_denies(self):
        """Target outside task allowed_paths → DENY."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/tasks/T-0001.md": TASK_CONTRACT_SMALL})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / "other/script.py"),
            ))
            self.assertEqual(result.decision, Decision.DENY)

    def test_no_allowed_paths_denies(self):
        """Task with no allowed_paths → DENY (fail-closed)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/tasks/T-0001.md": TASK_CONTRACT_NO_PATHS})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / "src/main.py"),
            ))
            self.assertEqual(result.decision, Decision.DENY)

    def test_no_task_id_denies(self):
        """No task_id → cannot verify scope → DENY."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_NO_TASK})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / "src/main.py"),
            ))
            self.assertEqual(result.decision, Decision.DENY)

    def test_missing_task_contract_denies(self):
        """Task contract file missing → DENY."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / "src/main.py"),
            ))
            self.assertEqual(result.decision, Decision.DENY)

    def test_explicit_task_id_overrides_state(self):
        """Explicit task_id in AuthRequest overrides state.yaml."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/tasks/T-0001.md": TASK_CONTRACT_SMALL,
                   ".ai/tasks/T-0002.md": TASK_CONTRACT})
            ctrl = _ctrl(root)
            # Request uses T-0002 explicitly; state has T-0001
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / "src/main.py"),
                task_id="T-0002",
            ))
            self.assertEqual(result.decision, Decision.ALLOW)


class TestPendingGateAllowedPaths(unittest.TestCase):
    """Pending gate + allowed_paths: the deadlock fix.

    During a pending gate, writes to paths within the gate's allowed_paths
    are ALLOWED — this lets the AI write design docs, evidence, etc.
    while waiting for gate approval.
    """

    def test_pending_gate_design_docs_allowed(self):
        """Design doc in pending gate's allowed_paths → ALLOW."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK_AND_GATE,
                   ".ai/gates.yaml": GATES_ONE_PENDING,
                   ".ai/tasks/T-0001.md": TASK_CONTRACT})
            ctrl = _ctrl(root)
            # This is a governance file (.ai/evidence/design/) AND
            # in the pending gate's allowed_paths → ALLOW
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".ai/evidence/design/architecture.md"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)
            self.assertIn("G-DESIGN", result.reason)

    def test_pending_gate_non_governance_in_task_scope_allows(self):
        """Non-governance file in task allowed_paths → ALLOW even during pending gate.

        This is the key behavior change: pending gate does NOT block
        writes within task scope.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK_AND_GATE,
                   ".ai/gates.yaml": GATES_ONE_PENDING,
                   ".ai/tasks/T-0001.md": TASK_CONTRACT})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / "src/main.py"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)
            self.assertIn("allowed scope", result.reason.lower())


class TestDefaultDeny(unittest.TestCase):
    """Default behavior: fail-closed."""

    def test_no_task_non_governance_denies(self):
        """No task_id and non-governance target → DENY."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_NO_TASK})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / "random/file.py"),
            ))
            self.assertEqual(result.decision, Decision.DENY)

    def test_no_state_file_at_all_denies(self):
        """No .ai/state.yaml at all → DENY for non-governance write."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / "src/main.py"),
            ))
            self.assertEqual(result.decision, Decision.DENY)

    def test_governance_write_without_state_allows(self):
        """Governance write without state.yaml still ALLOWs (no state → no gates)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".ai/evidence/test.md"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)


class TestNonFileActions(unittest.TestCase):
    """Actions without file targets (LAUNCH_ROLE, SUBMIT_EVIDENCE, etc.)."""

    def test_launch_role_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.LAUNCH_ROLE,
                role_id="developer",
            ))
            self.assertEqual(result.decision, Decision.ALLOW)

    def test_submit_evidence_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.SUBMIT_EVIDENCE,
            ))
            self.assertEqual(result.decision, Decision.ALLOW)

    def test_state_transition_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.STATE_TRANSITION,
            ))
            self.assertEqual(result.decision, Decision.ALLOW)


class TestActionVariants(unittest.TestCase):
    """Coverage for other Action variants with file targets."""

    def test_exec_bash_in_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/tasks/T-0001.md": TASK_CONTRACT})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.EXEC_BASH,
                target_path=str(root / "src/run.sh"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)

    def test_apply_patch_out_of_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/tasks/T-0001.md": TASK_CONTRACT_SMALL})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.APPLY_PATCH,
                target_path=str(root / "other/file.py"),
            ))
            self.assertEqual(result.decision, Decision.DENY)

    def test_mcp_tool_call_in_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/tasks/T-0001.md": TASK_CONTRACT})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.MCP_TOOL_CALL,
                target_path=str(root / "lib/utils.py"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)


class TestPathNormalization(unittest.TestCase):
    """Edge cases for path normalization."""

    def test_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/tasks/T-0001.md": TASK_CONTRACT})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / "src/main.py"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)

    def test_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/tasks/T-0001.md": TASK_CONTRACT})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path="src/main.py",
            ))
            self.assertEqual(result.decision, Decision.ALLOW)

    def test_path_outside_project_root(self):
        """Path outside project root cannot be normalized → falls to default DENY."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/tasks/T-0001.md": TASK_CONTRACT})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path="/etc/passwd",
            ))
            self.assertEqual(result.decision, Decision.DENY)

    def test_backslash_path_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/tasks/T-0001.md": TASK_CONTRACT})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / "src\\sub\\module.py"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)


class TestDataclassFields(unittest.TestCase):
    """Verify dataclass fields and defaults."""

    def test_auth_request_defaults(self):
        req = AuthRequest(action=Action.WRITE_FILE)
        self.assertIsNone(req.target_path)
        self.assertIsNone(req.task_id)
        self.assertIsNone(req.role_id)

    def test_auth_result_defaults(self):
        result = AuthResult(decision=Decision.ALLOW, reason="test")
        self.assertIsNone(result.required_gate_id)

    def test_auth_result_with_gate(self):
        result = AuthResult(
            decision=Decision.ALLOW,
            reason="test",
            required_gate_id="G-001",
        )
        self.assertEqual(result.required_gate_id, "G-001")


class TestFallbackYamlParsing(unittest.TestCase):
    """Verify the naive YAML parser works without PyYAML."""

    def test_fallback_parses_state(self):
        """Naive parser extracts scalar keys from state.yaml."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK})
            ctrl = _ctrl(root)
            state = ctrl._load_state()
            self.assertEqual(state.get("current_task_id"), "T-0001")
            self.assertEqual(state.get("current_phase"), "S4-implementation")

    def test_fallback_parses_gates(self):
        """Naive parser extracts gate list with statuses."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/gates.yaml": GATES_ONE_PENDING})
            ctrl = _ctrl(root)
            gates = ctrl._load_gates()
            self.assertEqual(len(gates), 2)
            pending = ctrl._get_pending_gates()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["id"], "G-DESIGN")

    def test_fallback_parses_allowed_paths(self):
        """Naive parser extracts allowed_paths from gate entries."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK,
                   ".ai/gates.yaml": GATES_ONE_PENDING})
            ctrl = _ctrl(root)
            pending = ctrl._get_pending_gates()
            allowed = pending[0].get("allowed_paths", [])
            self.assertIn(".ai/evidence/design/", allowed)
            self.assertIn("docs/design/", allowed)


class TestDecisionChainPriority(unittest.TestCase):
    """Verify the decision chain respects priority ordering."""

    def test_high_risk_checked_before_protected(self):
        """High-risk action is checked first, even with protected path."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.INSTALL,
                target_path=str(root / "AGENTS.md"),
            ))
            self.assertEqual(result.decision, Decision.DENY)
            self.assertIn("high-risk", result.reason.lower())

    def test_protected_checked_before_governance(self):
        """Host paths (.zcode/) → DENY by loop_core (handled by hooks layer)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".zcode/config.json"),
            ))
            # loop_core does not know about .zcode/ — fail-closed
            self.assertEqual(result.decision, Decision.DENY)

    def test_decision_recording_exempt_checked_early(self):
        """.ai/gates.yaml exemption checked before protected/governance checks."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp,
                **{".ai/state.yaml": STATE_WITH_TASK_AND_GATE,
                   ".ai/gates.yaml": GATES_ONE_PENDING})
            ctrl = _ctrl(root)
            result = ctrl.authorize(AuthRequest(
                action=Action.WRITE_FILE,
                target_path=str(root / ".ai/gates.yaml"),
            ))
            self.assertEqual(result.decision, Decision.ALLOW)


if __name__ == "__main__":
    unittest.main()
