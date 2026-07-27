import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from codex_loop.context.builder import ContextBudgetError, build_context_packet, fingerprint_paths
from codex_loop.context.policy import PermissionError, assert_no_secret_markers, assert_write_allowed
from codex_loop.core.contracts import RoleRegistry
from codex_loop.core.models import ProjectOverlay, WorkPacket


REGISTRY = ROOT / "codex_loop" / "roles" / "registry.json"


class ContextIsolationTests(unittest.TestCase):
    def setUp(self):
        self.registry = RoleRegistry.load(REGISTRY)
        self.role = self.registry.get("system-architect")
        self.overlay = ProjectOverlay("fixture", "build a material library", "medium", "candidate")
        self.packet = WorkPacket(
            "WP-1", "TASK-1", "P3", self.role.role_id, "define architecture", context_budget_tokens=1800
        )

    def test_only_selected_evidence_is_loaded(self):
        context = build_context_packet(self.role, self.overlay, self.packet, [("selected", "only this evidence")])
        labels = [item["label"] for item in context["sections"]]
        self.assertIn("evidence:selected", labels)
        self.assertNotIn("evidence:unselected", labels)
        self.assertLessEqual(context["approximate_tokens"], context["budget_tokens"])

    def test_budget_overflow_is_blocked(self):
        packet = WorkPacket("WP-2", "TASK-2", "P3", self.role.role_id, "overflow", context_budget_tokens=10)
        with self.assertRaises(ContextBudgetError):
            build_context_packet(self.role, self.overlay, packet, [("large", "x" * 1000)])

    def test_write_boundary_and_secret_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            allowed = root / ".loop" / "packets" / "architecture" / "a.md"
            self.assertEqual(
                assert_write_allowed(root, allowed, (".loop/packets/architecture/",)).as_posix(),
                ".loop/packets/architecture/a.md",
            )
            with self.assertRaises(PermissionError):
                assert_write_allowed(root, root / "src" / "a.py", (".loop/packets/architecture/",))
        with self.assertRaises(PermissionError):
            assert_no_secret_markers("password=not-for-context")

    def test_file_fingerprint_changes_when_input_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "input.md"
            path.write_text("one", encoding="utf-8")
            first = fingerprint_paths(root, [path])
            path.write_text("two", encoding="utf-8")
            second = fingerprint_paths(root, [path])
            self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
