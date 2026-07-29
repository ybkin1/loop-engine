"""Tests for loop_core/status_dashboard.py — Status Dashboard."""
import sys, os, tempfile, unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestDashboard(unittest.TestCase):
    def setUp(self):
        import yaml
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / ".ai").mkdir(parents=True, exist_ok=True)
        # Create minimal state
        state = {"schema_version": 1, "project_name": "Test", "current_phase": "S6-delivery", "loop_mode": "FULL"}
        with open(self.root / ".ai" / "state.yaml", "w") as f:
            yaml.safe_dump(state, f)
        # Create minimal task_graph
        graph = {"schema_version": 1, "tasks": [
            {"id": "T-0001", "title": "T1", "status": "completed", "phase": "S1-requirements"},
            {"id": "T-0002", "title": "T2", "status": "pending", "phase": "S4-implementation"},
        ], "edges": [{"from": "T-0001", "to": "T-0002"}]}
        with open(self.root / ".ai" / "task_graph.yaml", "w") as f:
            yaml.safe_dump(graph, f)
        # Create empty gates
        with open(self.root / ".ai" / "gates.yaml", "w") as f:
            yaml.safe_dump({"schema_version": 1, "gates": []}, f)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_generate(self):
        from loop_core.status_dashboard import Dashboard
        status = Dashboard(str(self.root)).generate()
        self.assertEqual(status.project_name, "Test")
        self.assertEqual(status.current_phase, "S6-delivery")
        self.assertIsNotNone(status.health_indicator)

    def test_to_dict(self):
        from loop_core.status_dashboard import Dashboard
        d = Dashboard(str(self.root)).to_dict()
        self.assertIn("generated_at", d)
        self.assertIn("task_stats", d)
        self.assertIn("health_indicator", d)

    def test_to_markdown(self):
        from loop_core.status_dashboard import Dashboard
        md = Dashboard(str(self.root)).to_markdown()
        self.assertIn("Test", md)
        self.assertIn("Task Progress", md)

    def test_no_state_file(self):
        from loop_core.status_dashboard import Dashboard
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            status = Dashboard(td).generate()
            self.assertEqual(status.project_name, "unknown")

    def test_phase_progress(self):
        from loop_core.status_dashboard import Dashboard
        status = Dashboard(str(self.root)).generate()
        self.assertIn("S1-requirements", status.phase_progress)
        self.assertEqual(status.phase_progress["S1-requirements"], 1.0)

    def test_health_indicator_with_completed_tasks(self):
        from loop_core.status_dashboard import Dashboard
        status = Dashboard(str(self.root)).generate()
        self.assertIn(status.health_indicator, ["GREEN", "YELLOW", "RED"])

if __name__ == "__main__":
    unittest.main()
