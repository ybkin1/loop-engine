"""Integration tests for the product layer modules."""
import sys, os, tempfile, unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestProductLayerIntegration(unittest.TestCase):
    def setUp(self):
        import yaml
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / ".ai").mkdir(parents=True, exist_ok=True)
        (self.root / ".ai" / "inbox").mkdir(exist_ok=True)
        (self.root / ".ai" / "plans").mkdir(exist_ok=True)
        graph = {"schema_version": 1, "tasks": [
            {"id": "T-0001", "title": "T1", "status": "completed", "phase": "S1"},
            {"id": "T-0002", "title": "T2", "status": "pending", "phase": "S4"},
        ], "edges": [{"from": "T-0001", "to": "T-0002"}]}
        with open(self.root / ".ai" / "task_graph.yaml", "w") as f:
            yaml.safe_dump(graph, f)
        with open(self.root / ".ai" / "state.yaml", "w") as f:
            yaml.safe_dump({"project_name": "Test", "current_phase": "S6", "loop_mode": "FULL"}, f)
        with open(self.root / ".ai" / "gates.yaml", "w") as f:
            yaml.safe_dump({"schema_version": 1, "gates": []}, f)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_full_flow_inbox_to_dashboard(self):
        """End-to-end: submit requirement → plan → queue → dashboard."""
        from loop_core.inbox import Inbox, InboxStatus
        from loop_core.planner import Planner
        from loop_core.task_queue import TaskQueue
        from loop_core.status_dashboard import Dashboard

        # 1. Submit requirement
        inbox = Inbox(str(self.root))
        req = inbox.submit("E2E Feature", "Implement end-to-end test flow.")
        inbox.update_status(req.requirement_id, InboxStatus.ACCEPTED)

        # 2. Generate plan
        planner = Planner(str(self.root))
        draft = planner.generate("E2E Feature", "Implement end-to-end test flow.", req.requirement_id)

        # 3. Queue analysis
        queue = TaskQueue(str(self.root))
        order = queue.topological_order()
        self.assertEqual(order, ["T-0001", "T-0002"])

        # 4. Dashboard
        dashboard = Dashboard(str(self.root))
        status = dashboard.generate()
        self.assertEqual(status.project_name, "Test")
        self.assertIsNotNone(status.health_indicator)

    def test_inbox_persistence_across_instances(self):
        from loop_core.inbox import Inbox
        inbox1 = Inbox(str(self.root))
        req = inbox1.submit("Persist", "Cross-instance test.")
        inbox2 = Inbox(str(self.root))
        self.assertEqual(inbox2.get(req.requirement_id).title, "Persist")

    def test_queue_and_dashboard_consistency(self):
        from loop_core.task_queue import TaskQueue
        from loop_core.status_dashboard import Dashboard
        queue_stats = TaskQueue(str(self.root)).task_stats()
        dash_stats = Dashboard(str(self.root)).generate().task_stats
        self.assertEqual(queue_stats["total"], dash_stats["total"])

if __name__ == "__main__":
    unittest.main()
