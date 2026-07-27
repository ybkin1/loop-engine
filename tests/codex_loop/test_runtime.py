import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from codex_loop.core.models import ProjectProfile
from codex_loop.core.store import LoopStore
from codex_loop.planning.work_packets import packet_for_role
from codex_loop.runtime.runner import CodexRuntime, RoleRunRequest


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        LoopStore(self.root).initialize(ProjectProfile("runtime", "bounded runtime test"))
        self.runtime = CodexRuntime(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_tool_blocks_without_invocation_spec(self):
        request = RoleRunRequest("run-missing", "system-architect", "T-1", "P3", "design boundaries")
        envelope = self.runtime.prepare_run(request)
        self.assertEqual(envelope.verdict, "BLOCKED")
        self.assertFalse((self.root / ".loop/runs/run-missing.invocation.json").exists())
        self.assertIn("missing_tools", envelope.tool_preflight)

    def test_ready_run_is_explicitly_not_a_capability_pass(self):
        request = RoleRunRequest(
            "run-ready", "system-architect", "T-1", "P3", "design boundaries",
            available_tools=("workspace_read", "graph_check", "schema_check", "structured_write"),
            write_targets=(".loop/packets/architecture/design.json",),
        )
        envelope = self.runtime.prepare_run(request)
        self.assertEqual(envelope.verdict, "READY_TO_INVOKE")
        self.assertEqual(envelope.capability_probe["status"], "NOT_RUN")
        self.assertTrue((self.root / ".loop/runs/run-ready.json").exists())
        self.assertTrue((self.root / ".loop/runs/run-ready.invocation.json").exists())

    def test_write_boundary_blocks_role_output_escape(self):
        request = RoleRunRequest(
            "run-escape", "system-architect", "T-1", "P3", "design boundaries",
            available_tools=("workspace_read", "graph_check", "schema_check", "structured_write"),
            write_targets=("../outside.json",),
        )
        envelope = self.runtime.prepare_run(request)
        self.assertEqual(envelope.verdict, "BLOCKED")
        self.assertEqual(envelope.permission_preflight["status"], "BLOCKED")

    def test_developer_alias_cannot_target_loop_state(self):
        request = RoleRunRequest(
            "run-state-alias", "developer", "T-1", "P7", "implement bounded change",
            available_tools=("workspace_read", "bounded_write", "command_runner", "test_runner"),
            write_targets=("project_declared_worktree",),
            declared_write_aliases=(("project_declared_worktree", ".loop/state/forged.json"),),
        )
        envelope = self.runtime.prepare_run(request)
        self.assertEqual(envelope.verdict, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
