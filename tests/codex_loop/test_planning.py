import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from codex_loop.core.models import ProjectProfile
from codex_loop.core.store import LoopStore
from codex_loop.planning.graph import GraphError, TaskGraph, TaskNode, default_task_graph
from codex_loop.planning.phases import default_phases
from codex_loop.planning.work_packets import packet_for_role
from codex_loop.core.contracts import RoleRegistry


REGISTRY = ROOT / "codex_loop" / "roles" / "registry.json"


class PlanningTests(unittest.TestCase):
    def test_default_phases_have_user_decisions_only_at_product_boundaries(self):
        phases = default_phases()
        self.assertEqual(len(phases), 13)
        self.assertEqual([phase.phase_id for phase in phases if phase.user_decision], ["P1", "P2", "P3", "P11"])

    def test_graph_rejects_missing_dependency_and_cycles(self):
        graph = TaskGraph()
        graph.add(TaskNode("a", "A", "P1", "product-manager", ("missing",)))
        with self.assertRaises(GraphError):
            graph.validate()
        cyclic = TaskGraph()
        cyclic.add(TaskNode("a", "A", "P1", "product-manager", ("b",)))
        cyclic.add(TaskNode("b", "B", "P1", "product-manager", ("a",)))
        with self.assertRaises(GraphError):
            cyclic.validate()

    def test_graph_ready_is_deterministic(self):
        graph = TaskGraph()
        graph.add(TaskNode("a", "A", "P1", "product-manager"))
        graph.add(TaskNode("b", "B", "P2", "quality-engineer", ("a",)))
        self.assertEqual([node.task_id for node in graph.ready(set())], ["a"])
        self.assertEqual([node.task_id for node in graph.ready({"a"})], ["b"])

    def test_default_task_graph_covers_each_phase_role_and_gate(self):
        graph = default_task_graph()
        graph.validate()
        self.assertTrue(any(node.user_gate for node in graph.nodes.values()))
        self.assertTrue(any(node.phase_id == "P12" for node in graph.nodes.values()))

    def test_store_initializes_isolated_loop_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = LoopStore(root)
            store.initialize(ProjectProfile("T-0036", "build material library"))
            self.assertTrue(store.exists())
            self.assertEqual(store.read_json("state/current.json")["phase_id"], "P0")
            self.assertEqual(len(store.read_json("phases/default.json")["phases"]), 13)
            self.assertTrue((root / ".loop" / "tasks").exists())

    def test_work_packet_inherits_role_boundaries(self):
        role = RoleRegistry.load(REGISTRY).get("quality-engineer")
        packet = packet_for_role(role, "T-1", "P5", "design quality gates")
        self.assertEqual(packet.role_id, "quality-engineer")
        self.assertIn(".loop/packets/quality/", packet.allowed_write)
        self.assertIn("pass_without_evidence", packet.forbidden_actions)


if __name__ == "__main__":
    unittest.main()
