"""Negative and positive tests for the canonical runtime controller."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from loop_core.runtime_controller import (
    ExecutionContext,
    RuntimeController,
    RuntimeControllerError,
    RuntimeState,
)


class RuntimeControllerTests(unittest.TestCase):
    def test_onboard_is_idempotent_and_starts_without_active_task(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.py").write_text("value = 1\n", encoding="utf-8")
            controller = RuntimeController(root)
            first = controller.onboard_project("start Loop")
            second = controller.onboard_project("start Loop")
            self.assertEqual(first.runtime_state, RuntimeState.NO_ACTIVE_TASK)
            self.assertEqual(second.runtime_state, RuntimeState.NO_ACTIVE_TASK)
            self.assertIsNone(second.task_id)

    def test_proposal_does_not_activate_task(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = RuntimeController(Path(directory))
            controller.onboard_project("start Loop")
            proposal = controller.create_work_package_proposal(
                "T-X", "G-X", "Implement feature", ["src/"]
            )
            self.assertEqual(proposal.runtime_state, RuntimeState.USER_APPROVAL_REQUIRED)
            self.assertEqual(controller.snapshot().task_id, "T-X")

    def test_approve_and_execute_is_one_transition_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = RuntimeController(Path(directory))
            controller.onboard_project("start Loop")
            controller.create_work_package_proposal("T-X", "G-X", "Implement feature", ["src/"])
            started = controller.approve_and_execute("G-X", approval="批准")
            repeated = controller.approve_and_execute("G-X", approval="批准")
            self.assertEqual(started.runtime_state, RuntimeState.DEVELOPER_EXECUTION)
            self.assertEqual(started.execution_id, repeated.execution_id)
            self.assertEqual(started.capability_id, repeated.capability_id)

    def test_main_thread_denied_and_assigned_developer_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = RuntimeController(Path(directory))
            controller.onboard_project("start Loop")
            controller.create_work_package_proposal("T-X", "G-X", "Implement feature", ["src/"])
            snapshot = controller.approve_and_execute("G-X", approval="批准")
            main = ExecutionContext("main", "main-thread", "main-thread", "T-X", snapshot.execution_id, capability_id=snapshot.capability_id)
            self.assertEqual(controller.authorize_write(main, "src/app.py"), (False, "MAIN_THREAD_BUSINESS_WRITE_DENIED"))
            developer = ExecutionContext("developer:T-X", "developer", "agent", "T-X", snapshot.execution_id, capability_id=snapshot.capability_id)
            self.assertEqual(controller.authorize_write(developer, "src/app.py"), (True, "AUTHORIZED"))

    def test_no_active_task_denies_business_write(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = RuntimeController(Path(directory))
            controller.onboard_project("start Loop")
            context = ExecutionContext("developer:T-X", "developer", "agent")
            self.assertEqual(controller.authorize_write(context, "src/app.py"), (False, "NO_ACTIVE_TASK_OR_PROPOSAL"))

    def test_wrong_scope_and_reviewer_are_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = RuntimeController(Path(directory))
            controller.onboard_project("start Loop")
            controller.create_work_package_proposal("T-X", "G-X", "Implement feature", ["src/"])
            snapshot = controller.approve_and_execute("G-X", approval="批准")
            reviewer = ExecutionContext("reviewer:T-X", "reviewer", "agent", "T-X", snapshot.execution_id, capability_id=snapshot.capability_id)
            self.assertEqual(controller.authorize_write(reviewer, "src/app.py"), (False, "ROLE_NOT_ALLOWED_TO_WRITE"))
            developer = ExecutionContext("developer:T-X", "developer", "agent", "T-X", snapshot.execution_id, capability_id=snapshot.capability_id)
            self.assertEqual(controller.authorize_write(developer, "README.md"), (False, "PATH_OUTSIDE_APPROVED_SCOPE"))


if __name__ == "__main__":
    unittest.main()
