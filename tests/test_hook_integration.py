"""
Integration tests for HardConstraints consumption in Hook scripts.

Verifies:
  1. loop_enforcement delegates to HardConstraints.check_all() when available
  2. loop_enforcement falls back to existing logic when HardConstraints unavailable
  3. gate_guard uses check_c7_blockers to detect blockers
  4. Old and new logic produce the same result for the same input (regression)
  5. Graceful degradation on ImportError

Tests are split into:
  - Unit: direct import of hook_common helpers
  - Integration: subprocess-based E2E tests of hook scripts
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "hooks" / "scripts"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _make_project(
    tmp: str,
    state_content: str | None = None,
    gates_content: str | None = None,
    task_graph_content: str | None = None,
    task_files: dict[str, str] | None = None,
    extra_files: dict[str, str] | None = None,
) -> Path:
    """Create a minimal governed project in a temp directory."""
    root = Path(tmp)
    ai_dir = root / ".ai"
    ai_dir.mkdir(parents=True, exist_ok=True)

    if state_content is not None:
        (ai_dir / "state.yaml").write_text(state_content, encoding="utf-8")
    if gates_content is not None:
        (ai_dir / "gates.yaml").write_text(gates_content, encoding="utf-8")
    if task_graph_content is not None:
        (ai_dir / "task_graph.yaml").write_text(task_graph_content, encoding="utf-8")

    if task_files:
        tasks_dir = ai_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        for fname, content in task_files.items():
            (tasks_dir / fname).write_text(content, encoding="utf-8")

    if extra_files:
        for fname, content in extra_files.items():
            fpath = root / fname
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")

    return root


def _run_hook(
    script_name: str,
    root: Path,
    hook_input: dict | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run a hook script as a subprocess, similar to ZCode's invocation."""
    env = dict(os.environ)
    env["ZCODE_PROJECT_DIR"] = str(root)
    if extra_env:
        env.update(extra_env)
    payload = json.dumps(hook_input or {})
    return subprocess.run(
        [PYTHON, str(SCRIPTS / script_name)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def _write_input(file_path: str) -> dict:
    """Build a PreToolUse hook input for a Write operation."""
    return {"tool_name": "Write", "tool_input": {"file_path": file_path}}


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

STATE_FULL = """\
schema_version: 1
project_name: test-full
current_phase: S0-init
loop_mode: FULL
current_task_id: T-0001
"""

STATE_FULL_NO_TASK = """\
schema_version: 1
project_name: test-full
current_phase: S0-init
loop_mode: FULL
"""

STATE_LIGHTWEIGHT = """\
schema_version: 1
project_name: test-light
current_phase: S0-init
loop_mode: LIGHTWEIGHT
"""

TASK_IN_SCOPE = """\
# Task T-0001: Implement feature X
allowed_paths:
- src/
- tests/

developer_agent_id: "agent-001"
reviewer_agent_id: "agent-002"
"""

GATES_NONE_PENDING = """\
gates:
  - id: G-T-0006-DESIGN
    task_id: T-0006
    gate_type: design
    status: approved
"""

GATES_WITH_BLOCKER = """\
gates:
  - id: G-T-0007-BLOCKED
    task_id: T-0007
    gate_type: implementation
    status: blocked
  - id: G-T-0006-DESIGN
    task_id: T-0006
    gate_type: design
    status: approved
"""

GATES_PENDING = """\
gates:
  - id: G-T-0007-IMPLEMENTATION
    task_id: T-0007
    gate_type: implementation
    status: pending
"""

TASK_GRAPH_ACTIVE = """\
tasks:
  - id: T-0001
    name: "Implement feature X"
    status: active
    allowed_paths:
      - src/
      - tests/
"""

TASK_GRAPH_BLOCKED = """\
tasks:
  - id: T-0001
    name: "Implement feature X"
    status: blocked
  - id: T-0002
    name: "Fix bug Y"
    status: completed
"""

TASK_GRAPH_NONE = """\
tasks:
  - id: T-0001
    name: "Implement feature X"
    status: completed
  - id: T-0002
    name: "Fix bug Y"
    status: pending
"""


# ═══════════════════════════════════════════════════════════════════════════
# Unit Tests — hook_common helpers
# ═══════════════════════════════════════════════════════════════════════════

class LoadTasksForContextTest(unittest.TestCase):
    """Tests for hook_common.load_tasks_for_context()."""

    @classmethod
    def setUpClass(cls):
        # Add scripts dir to path so we can import hook_common
        sys.path.insert(0, str(SCRIPTS))
        from hook_common import load_tasks_for_context as _load_tf
        cls._load_tf = staticmethod(_load_tf)

    def test_parses_active_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, task_graph_content=TASK_GRAPH_ACTIVE)
            tasks = self._load_tf(root)
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0]["id"], "T-0001")
            self.assertEqual(tasks[0]["status"], "active")

    def test_parses_blocked_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, task_graph_content=TASK_GRAPH_BLOCKED)
            tasks = self._load_tf(root)
            self.assertEqual(len(tasks), 2)
            statuses = {t["id"]: t["status"] for t in tasks}
            self.assertEqual(statuses.get("T-0001"), "blocked")
            self.assertEqual(statuses.get("T-0002"), "completed")

    def test_no_task_graph_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ai").mkdir()
            tasks = self._load_tf(root)
            self.assertEqual(tasks, [])

    def test_missing_ai_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks = self._load_tf(root)
            self.assertEqual(tasks, [])


class LoadGatesForContextTest(unittest.TestCase):
    """Tests for hook_common.load_gates_for_context()."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        from hook_common import load_gates_for_context as _load_gf
        cls._load_gf = staticmethod(_load_gf)

    def test_parses_approved_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, gates_content=GATES_NONE_PENDING)
            gates = self._load_gf(root)
            self.assertIn("G-T-0006-DESIGN", gates)
            self.assertEqual(gates["G-T-0006-DESIGN"], "approved")

    def test_parses_blocked_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, gates_content=GATES_WITH_BLOCKER)
            gates = self._load_gf(root)
            self.assertIn("G-T-0007-BLOCKED", gates)
            self.assertEqual(gates["G-T-0007-BLOCKED"], "blocked")

    def test_no_gates_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ai").mkdir()
            gates = self._load_gf(root)
            self.assertEqual(gates, {})


class LoadPhaseGatesForContextTest(unittest.TestCase):
    """Tests for hook_common.load_phase_gates_for_context()."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        from hook_common import load_phase_gates_for_context as _load_pgf
        cls._load_pgf = staticmethod(_load_pgf)

    def test_maps_gate_type_to_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, gates_content=GATES_NONE_PENDING)
            phase_gates = self._load_pgf(root)
            # G-T-0006-DESIGN has gate_type=design, which is NOT in our mapping
            # (only specific gate_types map to phases). Result should be empty.
            self.assertNotIn("S1-requirements", phase_gates)
            self.assertNotIn("S2-architecture", phase_gates)

    def test_maps_implementation_gate(self):
        gates_yaml = """\
gates:
  - id: G-T-0001-IMPL
    task_id: T-0001
    gate_type: implementation
    status: approved
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, gates_content=gates_yaml)
            phase_gates = self._load_pgf(root)
            self.assertIn("S4-implementation", phase_gates)
            self.assertEqual(phase_gates["S4-implementation"], "approved")

    def test_maps_requirements_gate(self):
        gates_yaml = """\
gates:
  - id: G-T-0001-REQ
    task_id: T-0001
    gate_type: requirements
    status: approved
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, gates_content=gates_yaml)
            phase_gates = self._load_pgf(root)
            self.assertIn("S1-requirements", phase_gates)
            self.assertEqual(phase_gates["S1-requirements"], "approved")

    def test_blocked_overrides_approved_for_same_phase(self):
        gates_yaml = """\
gates:
  - id: G-T-0001-IMPL
    task_id: T-0001
    gate_type: implementation
    status: approved
  - id: G-T-0002-IMPL
    task_id: T-0002
    gate_type: implementation
    status: blocked
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, gates_content=gates_yaml)
            phase_gates = self._load_pgf(root)
            self.assertEqual(phase_gates["S4-implementation"], "blocked")

    def test_no_gates_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ai").mkdir()
            phase_gates = self._load_pgf(root)
            self.assertEqual(phase_gates, {})


class TryImportHardConstraintsTest(unittest.TestCase):
    """Tests for hook_common.try_import_hard_constraints()."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        sys.path.insert(0, str(PROJECT_ROOT))
        from hook_common import try_import_hard_constraints as _try_hc
        cls._try_hc = staticmethod(_try_hc)

    def test_returns_valid_classes_when_available(self):
        HC, Sev = self._try_hc()
        self.assertIsNotNone(HC, "HardConstraints should be importable from project root")
        self.assertIsNotNone(Sev, "Severity should be importable from project root")

    def test_returns_none_when_unavailable(self):
        # Simulate ImportError by temporarily removing project root from sys.path
        # AND clearing cached modules — other tests may have already imported
        # HardConstraints into sys.modules, making it available regardless of path.
        saved_path = list(sys.path)
        saved_modules = {
            k: sys.modules.pop(k)
            for k in list(sys.modules)
            if k.startswith("loop_core")
        }
        try:
            # Remove entries that contain the project root
            sys.path = [p for p in sys.path if str(PROJECT_ROOT.resolve()) not in str(Path(p).resolve())]
            # Also ensure the scripts dir is still accessible
            sys.path.insert(0, str(SCRIPTS))
            from hook_common import try_import_hard_constraints as try_import_hc_fallback
            HC, Sev = try_import_hc_fallback()
            self.assertIsNone(HC)
            self.assertIsNone(Sev)
        finally:
            sys.path[:] = saved_path
            sys.modules.update(saved_modules)


# ═══════════════════════════════════════════════════════════════════════════
# Integration Tests — loop_enforcement with HardConstraints
# ═══════════════════════════════════════════════════════════════════════════

class LoopEnforcementHardConstraintsIntegration(unittest.TestCase):
    """E2E tests: loop_enforcement.py delegates to HardConstraints when available."""

    SCRIPT = "loop_enforcement.py"

    def test_allows_valid_write_with_active_task_and_scope(self):
        """When HardConstraints passes, write in allowed scope is permitted."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                task_graph_content=TASK_GRAPH_ACTIVE,
                gates_content=GATES_NONE_PENDING,
                task_files={"T-0001.md": TASK_IN_SCOPE},
            )
            r = _run_hook(self.SCRIPT, root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 0, f"Expected pass, got: {r.stderr}")

    def test_blocks_write_when_no_active_task(self):
        """C3: No active task should block writes (HardConstraints C3)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                task_graph_content=TASK_GRAPH_NONE,  # no active/in_progress tasks
                gates_content=GATES_NONE_PENDING,
                task_files={"T-0001.md": TASK_IN_SCOPE},
            )
            r = _run_hook(self.SCRIPT, root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 2, f"Expected block, got: {r.stderr}")
            self.assertIn("BLOCKED", r.stderr)

    def test_blocks_write_when_path_out_of_scope(self):
        """C4: Path outside allowed_paths should block."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                task_graph_content=TASK_GRAPH_ACTIVE,
                gates_content=GATES_NONE_PENDING,
                task_files={"T-0001.md": TASK_IN_SCOPE},
            )
            r = _run_hook(self.SCRIPT, root, _write_input(str(root / "docs" / "readme.md")))
            self.assertEqual(r.returncode, 2, f"Expected block, got: {r.stderr}")
            self.assertIn("BLOCKED", r.stderr)

    def test_blocks_write_when_no_task_id_in_state(self):
        """C3 via HardConstraints: no task_id should block."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL_NO_TASK,
                task_graph_content=TASK_GRAPH_ACTIVE,
                gates_content=GATES_NONE_PENDING,
            )
            r = _run_hook(self.SCRIPT, root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 2, f"Expected block, got: {r.stderr}")

    def test_governance_write_exempt_before_hardconstraints(self):
        """Governance files are exempt before HardConstraints check runs."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL_NO_TASK,  # no task → would block normally
            )
            r = _run_hook(self.SCRIPT, root, _write_input(str(root / ".ai" / "state.yaml")))
            self.assertEqual(r.returncode, 0, f"Expected pass for governance, got: {r.stderr}")

    def test_lightweight_mode_skips_hardconstraints(self):
        """LIGHTWEIGHT loop_mode exits early before HardConstraints."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_LIGHTWEIGHT)
            r = _run_hook(self.SCRIPT, root, _write_input(str(root / "any.py")))
            self.assertEqual(r.returncode, 0, f"Expected pass in LIGHTWEIGHT, got: {r.stderr}")


# ═══════════════════════════════════════════════════════════════════════════
# Integration Tests — gate_guard with HardConstraints C7
# ═══════════════════════════════════════════════════════════════════════════

class GateGuardHardConstraintsIntegration(unittest.TestCase):
    """E2E tests: gate_guard.py uses HardConstraints C7 for blocker detection."""

    SCRIPT = "gate_guard.py"

    def test_pending_gate_still_blocks(self):
        """Existing pending gate check still works alongside C7."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                gates_content=GATES_PENDING,
                task_graph_content=TASK_GRAPH_ACTIVE,
            )
            r = _run_hook(self.SCRIPT, root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 2, f"Expected block on pending gate, got: {r.stderr}")
            self.assertIn("G-T-0007-IMPLEMENTATION", r.stderr)

    def test_blocked_gate_detected_by_c7(self):
        """C7: A gate with status=blocked should be detected and cause BLOCK."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                gates_content=GATES_WITH_BLOCKER,
                task_graph_content=TASK_GRAPH_ACTIVE,
            )
            r = _run_hook(self.SCRIPT, root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 2, f"Expected C7 block, got: {r.stderr}")
            self.assertIn("BLOCKED", r.stderr)

    def test_blocked_task_detected_by_c7(self):
        """C7: A task with status=blocked should also block."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                gates_content=GATES_NONE_PENDING,
                task_graph_content=TASK_GRAPH_BLOCKED,
            )
            r = _run_hook(self.SCRIPT, root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 2, f"Expected C7 block on blocked task, got: {r.stderr}")
            self.assertIn("BLOCKED", r.stderr)

    def test_no_blockers_no_pending_passes(self):
        """C7 passes when no blocked gates/tasks and no pending gates."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                gates_content=GATES_NONE_PENDING,
                task_graph_content=TASK_GRAPH_ACTIVE,
            )
            r = _run_hook(self.SCRIPT, root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 0, f"Expected pass, got: {r.stderr}")

    def test_hardconstraints_unavailable_does_not_block(self):
        """When HardConstraints is not importable, gate_guard still works (degraded).

        We copy the hook to a temp directory outside the project tree so the
        self-added sys.path doesn't find loop_core.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                gates_content=GATES_WITH_BLOCKER,
                task_graph_content=TASK_GRAPH_ACTIVE,
            )
            # Copy hook to temp location so loop_core is not found
            tmp_dir = Path(tempfile.mkdtemp())
            hook_copy = tmp_dir / "gate_guard.py"
            shutil.copy(str(SCRIPTS / "gate_guard.py"), str(hook_copy))
            # Also need hook_common.py
            shutil.copy(str(SCRIPTS / "hook_common.py"), str(tmp_dir / "hook_common.py"))
            env = dict(os.environ)
            env["ZCODE_PROJECT_DIR"] = str(root)
            payload = json.dumps(_write_input(str(root / "src" / "main.py")))
            r = subprocess.run(
                [PYTHON, str(hook_copy)],
                input=payload,
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            self.assertNotIn("Traceback", r.stderr,
                             f"Should not crash, got: {r.stderr}")
            # Without HardConstraints, blocked gates are not detected (graceful degradation).
            # The existing pending gate check passes (no pending gates in GATES_WITH_BLOCKER).
            # So the hook should PASS (known limitation of degraded mode).
            self.assertEqual(r.returncode, 0,
                             f"Degraded mode should pass (C7 skipped), got: {r.stderr}")


# ═══════════════════════════════════════════════════════════════════════════
# Regression Tests — Old logic produces same results
# ═══════════════════════════════════════════════════════════════════════════

class RegressionConsistencyTest(unittest.TestCase):
    """Verify old and new logic produce consistent results for the same inputs.

    The fallback path (when HardConstraints is unavailable) should produce the
    same pass/block result as the HardConstraints path for the core scenarios:
    task scope (C3) and path scope (C4) checks.
    """

    SCRIPT = "loop_enforcement.py"

    def _run_normally(self, root, hook_input):
        """Run with HardConstraints available (hook in its normal location)."""
        return _run_hook(self.SCRIPT, root, hook_input)

    def _run_in_isolation(self, root, hook_input):
        """Run with HardConstraints unavailable by copying hook outside project tree."""
        import shutil
        tmp_dir = Path(tempfile.mkdtemp())
        hook_copy = tmp_dir / "loop_enforcement.py"
        shutil.copy(str(SCRIPTS / "loop_enforcement.py"), str(hook_copy))
        shutil.copy(str(SCRIPTS / "hook_common.py"), str(tmp_dir / "hook_common.py"))
        env = dict(os.environ)
        env["ZCODE_PROJECT_DIR"] = str(root)
        payload = json.dumps(hook_input or {})
        return subprocess.run(
            [PYTHON, str(hook_copy)],
            input=payload,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    def test_both_paths_block_on_missing_task(self):
        """Both paths should block when no active task exists."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL_NO_TASK,
                task_graph_content=TASK_GRAPH_NONE,
                gates_content=GATES_NONE_PENDING,
            )
            hook_input = _write_input(str(root / "src" / "main.py"))

            r_hc = self._run_normally(root, hook_input)
            r_fallback = self._run_in_isolation(root, hook_input)

            self.assertEqual(r_hc.returncode, 2,
                             f"HardConstraints path should block: {r_hc.stderr}")
            self.assertEqual(r_fallback.returncode, 2,
                             f"Fallback path should block: {r_fallback.stderr}")
            self.assertEqual(r_hc.returncode, r_fallback.returncode,
                             "Both paths should return the same exit code")

    def test_both_paths_block_on_path_out_of_scope(self):
        """Both paths should block when target is outside allowed_paths."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                task_graph_content=TASK_GRAPH_ACTIVE,
                gates_content=GATES_NONE_PENDING,
                task_files={"T-0001.md": TASK_IN_SCOPE},
            )
            hook_input = _write_input(str(root / "docs" / "readme.md"))

            r_hc = self._run_normally(root, hook_input)
            r_fallback = self._run_in_isolation(root, hook_input)

            self.assertEqual(r_hc.returncode, 2,
                             f"HardConstraints path should block: {r_hc.stderr}")
            self.assertEqual(r_fallback.returncode, 2,
                             f"Fallback path should block: {r_fallback.stderr}")
            self.assertEqual(r_hc.returncode, r_fallback.returncode)

    def test_both_paths_allow_governance_write(self):
        """Both paths should allow governance file writes regardless of task state."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL_NO_TASK,  # No task → would normally block
            )
            hook_input = _write_input(str(root / ".ai" / "gates.yaml"))

            r_hc = self._run_normally(root, hook_input)
            r_fallback = self._run_in_isolation(root, hook_input)

            self.assertEqual(r_hc.returncode, 0,
                             f"HardConstraints path should allow: {r_hc.stderr}")
            self.assertEqual(r_fallback.returncode, 0,
                             f"Fallback path should allow: {r_fallback.stderr}")
            self.assertEqual(r_hc.returncode, r_fallback.returncode)


# ═══════════════════════════════════════════════════════════════════════════
# Graceful Degradation Tests
# ═══════════════════════════════════════════════════════════════════════════

class GracefulDegradationTest(unittest.TestCase):
    """Verify hooks degrade gracefully when HardConstraints raises exceptions.

    Since the hooks now add the loop-engine project root to sys.path,
    HardConstraints is normally available. We test graceful degradation
    by verifying that exceptions in the HardConstraints try block are
    caught and the fallback logic is invoked instead.
    """

    def _run_loop_enforcement_with_broken_hardconstraints(self, root, hook_input):
        """Run loop_enforcement from a temp location where loop_core can't be found."""
        import shutil
        tmp_dir = Path(tempfile.mkdtemp())
        hook_copy = tmp_dir / "loop_enforcement.py"
        shutil.copy(str(SCRIPTS / "loop_enforcement.py"), str(hook_copy))
        shutil.copy(str(SCRIPTS / "hook_common.py"), str(tmp_dir / "hook_common.py"))
        env = dict(os.environ)
        env["ZCODE_PROJECT_DIR"] = str(root)
        payload = json.dumps(hook_input or {})
        return subprocess.run(
            [PYTHON, str(hook_copy)],
            input=payload,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    def test_loop_enforcement_fallback_works(self):
        """When HardConstraints is unimportable, the hook falls back gracefully."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                task_graph_content=TASK_GRAPH_ACTIVE,
                gates_content=GATES_NONE_PENDING,
                task_files={"T-0001.md": TASK_IN_SCOPE},
            )
            r = self._run_loop_enforcement_with_broken_hardconstraints(
                root, _write_input(str(root / "src" / "main.py"))
            )
            # Should not crash — fallback logic should work
            self.assertNotIn("Traceback", r.stderr,
                             f"Should not crash on ImportError, got: {r.stderr}")
            # In fallback, task scope check passes (active task + in scope path)
            self.assertEqual(r.returncode, 0,
                             f"Fallback should allow valid write, got: {r.stderr}")

    def test_loop_enforcement_fallback_blocks_out_of_scope(self):
        """Fallback logic still blocks out-of-scope writes when no HardConstraints."""
        import shutil
        with tempfile.TemporaryDirectory() as tmp_proj:
            root = _make_project(
                tmp_proj,
                state_content=STATE_FULL,
                task_graph_content=TASK_GRAPH_ACTIVE,
                gates_content=GATES_NONE_PENDING,
                task_files={"T-0001.md": TASK_IN_SCOPE},
            )
            tmp_dir = Path(tempfile.mkdtemp())
            hook_copy = tmp_dir / "loop_enforcement.py"
            shutil.copy(str(SCRIPTS / "loop_enforcement.py"), str(hook_copy))
            shutil.copy(str(SCRIPTS / "hook_common.py"), str(tmp_dir / "hook_common.py"))
            env = dict(os.environ)
            env["ZCODE_PROJECT_DIR"] = str(root)
            payload = json.dumps(_write_input(str(root / "docs" / "readme.md")))
            r = subprocess.run(
                [PYTHON, str(hook_copy)],
                input=payload,
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            self.assertNotIn("Traceback", r.stderr,
                             f"Should not crash on ImportError, got: {r.stderr}")
            # Fallback should block (docs/readme.md is not in allowed scope)
            self.assertEqual(r.returncode, 2,
                             f"Fallback should block out-of-scope, got: {r.stderr}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
