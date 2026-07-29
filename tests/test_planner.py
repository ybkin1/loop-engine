"""Tests for loop_core/planner.py — Plan Generator."""
import sys, os, tempfile, unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestPlanner(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / ".ai" / "plans").mkdir(parents=True, exist_ok=True)
        from loop_core.planner import Planner
        self.planner = Planner(str(self.root))

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_generate_basic(self):
        draft = self.planner.generate("Test Feature", "Implement a test feature.")
        self.assertTrue(draft.plan_id.startswith("PLAN-"))
        self.assertTrue(len(draft.tasks) > 0)
        self.assertEqual(draft.status.value, "DRAFT")

    def test_generate_empty_raises(self):
        from loop_core.planner import PlannerError
        with self.assertRaises(PlannerError):
            self.planner.generate("Title", "")

    def test_get(self):
        draft = self.planner.generate("Get Test", "Testing retrieval.")
        retrieved = self.planner.get(draft.plan_id)
        self.assertEqual(retrieved.plan_id, draft.plan_id)

    def test_list_all(self):
        self.planner.generate("Plan A", "Description A.")
        self.planner.generate("Plan B", "Description B.")
        drafts = self.planner.list_all()
        self.assertGreaterEqual(len(drafts), 2)

    def test_approve(self):
        draft = self.planner.generate("Approve Test", "Testing approval.")
        approved = self.planner.approve(draft.plan_id, "G-T-0099-TEST")
        self.assertEqual(approved.status.value, "APPROVED")

    def test_task_draft_has_acceptance_criteria(self):
        draft = self.planner.generate("Criteria", "Testing acceptance criteria.")
        for task in draft.tasks:
            self.assertTrue(len(task.acceptance_criteria) > 0)

    def test_edges_connect_consecutive_tasks(self):
        draft = self.planner.generate("Edges", "Testing edge derivation.")
        if len(draft.tasks) > 1:
            self.assertEqual(len(draft.edges), len(draft.tasks) - 1)

    def test_to_dict(self):
        draft = self.planner.generate("Dict", "Testing serialization.")
        d = draft.to_dict()
        self.assertEqual(d["plan_id"], draft.plan_id)
        self.assertEqual(len(d["tasks"]), len(draft.tasks))

    def test_persistence(self):
        from loop_core.planner import Planner
        draft = self.planner.generate("Persist", "Testing file persistence.")
        planner2 = Planner(str(self.root))
        retrieved = planner2.get(draft.plan_id)
        self.assertEqual(retrieved.plan_id, draft.plan_id)

    def test_get_nonexistent_raises(self):
        from loop_core.planner import PlannerError
        with self.assertRaises(PlannerError):
            self.planner.get("PLAN-99999999-999")

if __name__ == "__main__":
    unittest.main()
