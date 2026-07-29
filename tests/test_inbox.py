"""Tests for loop_core/inbox.py — Requirement Inbox."""
import sys, os, tempfile, unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestRequirement(unittest.TestCase):
    def test_create_minimal(self):
        from loop_core.inbox import Requirement
        req = Requirement(requirement_id="REQ-20260729-001", title="Test", description="Desc.")
        self.assertEqual(req.requirement_id, "REQ-20260729-001")
        self.assertEqual(req.status.value, "NEW")
        self.assertTrue(req.created_at)

    def test_to_dict_and_back(self):
        from loop_core.inbox import Requirement, RequirementType, Priority, InboxStatus
        req = Requirement(requirement_id="REQ-20260729-002", title="RT", description="Round-trip.",
                         type=RequirementType.BUG_FIX, priority=Priority.P0, status=InboxStatus.ACCEPTED,
                         tags=["web"], clarification_questions=["Q?"])
        d = req.to_dict()
        r2 = Requirement.from_dict(d)
        self.assertEqual(r2.type, RequirementType.BUG_FIX)
        self.assertEqual(r2.priority, Priority.P0)
        self.assertEqual(r2.tags, ["web"])

class TestInbox(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / ".ai" / "inbox").mkdir(parents=True, exist_ok=True)
        from loop_core.inbox import Inbox
        self.inbox = Inbox(str(self.root))

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_submit_and_get(self):
        req = self.inbox.submit("Feature", "Implement feature.")
        self.assertTrue(req.requirement_id.startswith("REQ-"))
        r2 = self.inbox.get(req.requirement_id)
        self.assertEqual(r2.title, "Feature")

    def test_submit_empty_raises(self):
        from loop_core.inbox import InboxError
        with self.assertRaises(InboxError): self.inbox.submit("", "Desc")
        with self.assertRaises(InboxError): self.inbox.submit("Title", "")

    def test_list_all(self):
        self.inbox.submit("A", "Desc A.")
        self.inbox.submit("B", "Desc B.")
        self.assertGreaterEqual(len(self.inbox.list_all()), 2)

    def test_list_filtered(self):
        from loop_core.inbox import InboxStatus
        req = self.inbox.submit("Filter", "Test.")
        self.inbox.update_status(req.requirement_id, InboxStatus.ACCEPTED)
        accepted = self.inbox.list_all(status="ACCEPTED")
        self.assertTrue(any(r.requirement_id == req.requirement_id for r in accepted))

    def test_update_status_valid(self):
        from loop_core.inbox import InboxStatus
        req = self.inbox.submit("Status", "Test.")
        u = self.inbox.update_status(req.requirement_id, InboxStatus.ACCEPTED)
        self.assertEqual(u.status, InboxStatus.ACCEPTED)

    def test_update_status_invalid(self):
        from loop_core.inbox import InboxStatus, InboxError
        req = self.inbox.submit("Bad", "Test.")
        self.inbox.update_status(req.requirement_id, InboxStatus.ACCEPTED)
        with self.assertRaises(InboxError):
            self.inbox.update_status(req.requirement_id, InboxStatus.CLARIFYING)

    def test_add_clarification(self):
        req = self.inbox.submit("Ambiguous", "Short.")
        u = self.inbox.add_clarification_questions(req.requirement_id, ["Q1", "Q2"])
        self.assertEqual(len(u.clarification_questions), 2)
        self.assertEqual(u.status.value, "CLARIFYING")

    def test_link_task(self):
        req = self.inbox.submit("Link", "Test.")
        u = self.inbox.link_task(req.requirement_id, "T-0099")
        self.assertIn("T-0099", u.linked_task_ids)

    def test_persistence(self):
        from loop_core.inbox import Inbox
        req = self.inbox.submit("Persist", "Test.")
        inbox2 = Inbox(str(self.root))
        self.assertEqual(inbox2.get(req.requirement_id).title, "Persist")

    def test_inbox_summary(self):
        from loop_core.inbox import inbox_summary
        self.inbox.submit("Sum", "Test.")
        s = inbox_summary(str(self.root))
        self.assertGreaterEqual(s["total"], 1)

if __name__ == "__main__":
    unittest.main()
