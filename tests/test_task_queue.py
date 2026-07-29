"""Tests for loop_core/task_queue.py — Task Queue Engine."""
import sys, os, tempfile, unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestTaskQueue(unittest.TestCase):
    def setUp(self):
        import yaml
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / ".ai").mkdir(parents=True, exist_ok=True)
        # Create minimal task_graph.yaml
        graph = {
            "schema_version": 1,
            "tasks": [
                {"id": "T-0001", "title": "Task 1", "status": "completed", "phase": "S1-requirements"},
                {"id": "T-0002", "title": "Task 2", "status": "pending", "phase": "S2-architecture"},
                {"id": "T-0003", "title": "Task 3", "status": "pending", "phase": "S4-implementation"},
            ],
            "edges": [
                {"from": "T-0001", "to": "T-0002"},
                {"from": "T-0002", "to": "T-0003"},
            ],
        }
        with open(self.root / ".ai" / "task_graph.yaml", "w") as f:
            yaml.safe_dump(graph, f)
        # Create empty gates.yaml
        with open(self.root / ".ai" / "gates.yaml", "w") as f:
            yaml.safe_dump({"schema_version": 1, "gates": []}, f)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_topological_order(self):
        from loop_core.task_queue import TaskQueue
        q = TaskQueue(str(self.root))
        order = q.topological_order()
        self.assertEqual(order, ["T-0001", "T-0002", "T-0003"])

    def test_ready_tasks(self):
        from loop_core.task_queue import TaskQueue
        q = TaskQueue(str(self.root))
        ready = q.ready_tasks()
        # T-0001 is completed, T-0002 depends on T-0001 (completed) so it's ready
        self.assertIn("T-0002", ready)
        # T-0003 depends on T-0002 (pending) so NOT ready
        self.assertNotIn("T-0003", ready)

    def test_blocked_tasks(self):
        from loop_core.task_queue import TaskQueue
        q = TaskQueue(str(self.root))
        blocked = q.blocked_tasks()
        # T-0003 is blocked by T-0002
        t3_block = [b for b in blocked if b.task_id == "T-0003"]
        self.assertTrue(len(t3_block) > 0)
        self.assertEqual(t3_block[0].reason, "DEPENDENCY")

    def test_no_cycles(self):
        from loop_core.task_queue import TaskQueue
        q = TaskQueue(str(self.root))
        cycles = q.detect_cycles()
        self.assertEqual(cycles, [])

    def test_next_recommended(self):
        from loop_core.task_queue import TaskQueue
        q = TaskQueue(str(self.root))
        rec = q.next_recommended()
        self.assertEqual(rec, "T-0002")

    def test_task_stats(self):
        from loop_core.task_queue import TaskQueue
        q = TaskQueue(str(self.root))
        stats = q.task_stats()
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["completed"], 1)

    def test_critical_path(self):
        from loop_core.task_queue import TaskQueue
        q = TaskQueue(str(self.root))
        path = q.critical_path()
        self.assertEqual(len(path), 3)

    def test_to_dict(self):
        from loop_core.task_queue import TaskQueue
        d = TaskQueue(str(self.root)).to_dict()
        self.assertIn("topological_order", d)
        self.assertIn("ready_tasks", d)

    def test_no_graph_file(self):
        from loop_core.task_queue import TaskQueue
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            q = TaskQueue(td)
            self.assertEqual(q.topological_order(), [])
            self.assertEqual(q.task_stats()["total"], 0)

    def test_cycle_detection(self):
        import yaml
        # Create graph with cycle: T-0001 -> T-0002 -> T-0001
        graph = {
            "schema_version": 1,
            "tasks": [
                {"id": "T-0001", "title": "A", "status": "pending", "phase": "S1"},
                {"id": "T-0002", "title": "B", "status": "pending", "phase": "S2"},
            ],
            "edges": [
                {"from": "T-0001", "to": "T-0002"},
                {"from": "T-0002", "to": "T-0001"},
            ],
        }
        p = self.root / ".ai" / "task_graph.yaml"
        with open(p, "w") as f:
            yaml.safe_dump(graph, f)
        from loop_core.task_queue import TaskQueue
        cycles = TaskQueue(str(self.root)).detect_cycles()
        self.assertTrue(len(cycles) > 0)

if __name__ == "__main__":
    unittest.main()
