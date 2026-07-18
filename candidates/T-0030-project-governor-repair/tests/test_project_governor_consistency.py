from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path
import sys


PYTHON = r"C:\Python312\python.exe"
SCRIPTS = Path(r"C:\Users\Administrator\.codex\skills\project-governor\scripts")
TEMPLATES = Path(r"C:\Users\Administrator\.codex\skills\project-governor\templates\ai")
sys.path.insert(0, str(SCRIPTS))

from governor_lib import transactional_write_texts, validate_action_mode


class ProjectGovernorConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        shutil.copytree(TEMPLATES, self.root / ".ai")
        (self.root / ".ai" / "tasks").mkdir(exist_ok=True)
        (self.root / ".ai" / "evidence" / "T-0001").mkdir(parents=True)
        (self.root / ".ai" / "evidence" / "T-0001" / "commands.md").write_text("# Commands\n", encoding="utf-8")
        (self.root / ".ai" / "tasks" / "T-0001.md").write_text(
            "# Task T-0001: Fixture\n\n## Status\n\ncompleted\n", encoding="utf-8"
        )
        (self.root / ".ai" / "state.yaml").write_text(
            "schema_version: 1\nproject_name: Fixture\ncurrent_phase: test\ncurrent_task_id: T-0001\ncurrent_gate_id: null\n",
            encoding="utf-8",
        )
        (self.root / ".ai" / "task_graph.yaml").write_text(
            "schema_version: 1\ntasks:\n  -\n    id: T-0001\n    title: Fixture\n    status: completed\nedges: []\n",
            encoding="utf-8",
        )
        (self.root / ".ai" / "gates.yaml").write_text("schema_version: 1\ngates: []\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_script(self, name: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(SCRIPTS / name), str(self.root)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_close_session_preserves_completed_task_graph_status(self) -> None:
        result = self.run_script("close_session.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        graph = (self.root / ".ai" / "task_graph.yaml").read_text(encoding="utf-8")
        self.assertIn("status: completed", graph)
        self.assertNotIn("status: in_progress", graph)

    def test_close_session_preserves_each_supported_status(self) -> None:
        for status in ["pending", "approved_not_started", "in_progress", "blocked", "completed"]:
            with self.subTest(status=status):
                task_path = self.root / ".ai" / "tasks" / "T-0001.md"
                task_path.write_text(f"# Task T-0001: Fixture\n\n## Status\n\n{status}\n", encoding="utf-8")
                graph_path = self.root / ".ai" / "task_graph.yaml"
                graph_path.write_text(
                    f"schema_version: 1\ntasks:\n  -\n    id: T-0001\n    title: Fixture\n    status: {status}\nedges: []\n",
                    encoding="utf-8",
                )
                if status in {"approved_not_started", "in_progress"}:
                    approval = self.root / ".ai" / "evidence" / "T-0001" / "approval.md"
                    approval.write_text("approved", encoding="utf-8")
                    execution = self.root / ".ai" / "evidence" / "T-0001" / "execution.md"
                    if status == "in_progress":
                        execution.write_text("execute", encoding="utf-8")
                    execution_line = "\n    execution_evidence: .ai/evidence/T-0001/execution.md" if status == "in_progress" else ""
                    (self.root / ".ai" / "gates.yaml").write_text(
                        "schema_version: 1\ngates:\n  -\n    id: G-T-0001\n    task_id: T-0001\n"
                        "    status: approved\n    approval_evidence: .ai/evidence/T-0001/approval.md"
                        f"{execution_line}\n",
                        encoding="utf-8",
                    )
                else:
                    (self.root / ".ai" / "gates.yaml").write_text("schema_version: 1\ngates: []\n", encoding="utf-8")
                result = self.run_script("close_session.py")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f"status: {status}", graph_path.read_text(encoding="utf-8"))
                self.assertIn(f"Status: `{status}`", (self.root / ".ai" / "HANDOFF.md").read_text(encoding="utf-8"))

    def test_validate_state_rejects_task_graph_status_mismatch(self) -> None:
        graph_path = self.root / ".ai" / "task_graph.yaml"
        graph_path.write_text(graph_path.read_text(encoding="utf-8").replace("status: completed", "status: in_progress"), encoding="utf-8")
        result = self.run_script("validate_state.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("Task status mismatch", result.stdout)

    def test_validate_state_inventories_non_current_historical_mismatch(self) -> None:
        historical = self.root / ".ai" / "tasks" / "T-0002.md"
        historical.write_text("# Task T-0002\n\n## Status\n\ncompleted\n", encoding="utf-8")
        graph_path = self.root / ".ai" / "task_graph.yaml"
        graph = graph_path.read_text(encoding="utf-8").replace(
            "edges: []",
            "  -\n    id: T-0002\n    title: Historical\n    status: in_progress\nedges: []",
        )
        graph_path.write_text(graph, encoding="utf-8")
        result = self.run_script("validate_state.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("Historical task status mismatch: T-0002", result.stdout)

    def test_audit_handoff_rejects_semantic_task_status_mismatch(self) -> None:
        self.run_script("close_session.py")
        handoff_path = self.root / ".ai" / "HANDOFF.md"
        handoff = handoff_path.read_text(encoding="utf-8").replace("Status: `completed`", "Status: `in_progress`")
        handoff_path.write_text(handoff, encoding="utf-8")
        result = self.run_script("audit_handoff.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("HANDOFF task status mismatch", result.stdout)

    def test_action_mode_requires_matching_gate_and_explicit_execution(self) -> None:
        self.assertEqual(validate_action_mode("read_only"), [])
        self.assertEqual(validate_action_mode("prompt_generation_only"), [])
        self.assertEqual(validate_action_mode("create_pending_gate"), [])
        self.assertEqual(validate_action_mode("approve_pending_gate", gate_status="pending"), [])
        self.assertEqual(
            validate_action_mode("execute_approved_gate", gate_status="approved", explicit_execution_request=True),
            [],
        )
        self.assertTrue(validate_action_mode("approve_pending_gate", gate_status="approved"))
        self.assertTrue(validate_action_mode("execute_approved_gate", gate_status="pending", explicit_execution_request=True))
        self.assertTrue(validate_action_mode("execute_approved_gate", gate_status="approved"))

    def test_validate_state_requires_execution_evidence_for_in_progress(self) -> None:
        task_path = self.root / ".ai" / "tasks" / "T-0001.md"
        task_path.write_text("# Task T-0001\n\n## Status\n\nin_progress\n", encoding="utf-8")
        graph_path = self.root / ".ai" / "task_graph.yaml"
        graph_path.write_text(graph_path.read_text(encoding="utf-8").replace("status: completed", "status: in_progress"), encoding="utf-8")
        approval = self.root / ".ai" / "evidence" / "T-0001" / "approval.md"
        approval.write_text("approved", encoding="utf-8")
        (self.root / ".ai" / "gates.yaml").write_text(
            "schema_version: 1\ngates:\n  -\n    id: G-T-0001\n    task_id: T-0001\n    status: approved\n"
            "    approval_evidence: .ai/evidence/T-0001/approval.md\n",
            encoding="utf-8",
        )
        result = self.run_script("validate_state.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("in_progress requires execution evidence", result.stdout)

    def test_transaction_rolls_back_after_partial_replace(self) -> None:
        first = self.root / "first.txt"
        second = self.root / "second.txt"
        first.write_text("before-first", encoding="utf-8")
        second.write_text("before-second", encoding="utf-8")
        import governor_lib

        real_replace = governor_lib.os.replace
        calls = 0

        def fail_second_commit(source, destination):
            nonlocal calls
            if str(source).endswith(".tmp"):
                calls += 1
                if calls == 2:
                    raise OSError("injected partial commit failure")
            return real_replace(source, destination)

        with mock.patch.object(governor_lib.os, "replace", side_effect=fail_second_commit):
            with self.assertRaises(OSError):
                transactional_write_texts(self.root, {first: "after-first", second: "after-second"})
        self.assertEqual(first.read_text(encoding="utf-8"), "before-first")
        self.assertEqual(second.read_text(encoding="utf-8"), "before-second")
        self.assertFalse((self.root / ".project-governor-transaction.json").exists())

    def test_transaction_removes_new_file_after_partial_replace(self) -> None:
        first = self.root / "new.txt"
        second = self.root / "existing.txt"
        second.write_text("before", encoding="utf-8")
        import governor_lib

        real_replace = governor_lib.os.replace
        calls = 0

        def fail_second_commit(source, destination):
            nonlocal calls
            if str(source).endswith(".tmp"):
                calls += 1
                if calls == 2:
                    raise OSError("injected failure")
            return real_replace(source, destination)

        with mock.patch.object(governor_lib.os, "replace", side_effect=fail_second_commit):
            with self.assertRaises(OSError):
                transactional_write_texts(self.root, {first: "created", second: "after"})
        self.assertFalse(first.exists())
        self.assertEqual(second.read_text(encoding="utf-8"), "before")

    def test_transaction_preserves_concurrent_uncommitted_change(self) -> None:
        first = self.root / "first.txt"
        second = self.root / "second.txt"
        first.write_text("before-first", encoding="utf-8")
        second.write_text("before-second", encoding="utf-8")
        import governor_lib

        real_replace = governor_lib.os.replace
        calls = 0

        def modify_second_after_first_commit(source, destination):
            nonlocal calls
            result = real_replace(source, destination)
            if str(source).endswith(".tmp"):
                calls += 1
                if calls == 1:
                    second.write_text("concurrent-newer", encoding="utf-8")
            return result

        with mock.patch.object(governor_lib.os, "replace", side_effect=modify_second_after_first_commit):
            with self.assertRaisesRegex(RuntimeError, "Concurrent modification detected"):
                transactional_write_texts(self.root, {first: "after-first", second: "after-second"})
        self.assertEqual(first.read_text(encoding="utf-8"), "before-first")
        self.assertEqual(second.read_text(encoding="utf-8"), "concurrent-newer")

    def test_transaction_refuses_unresolved_recovery_marker(self) -> None:
        marker = self.root / ".project-governor-transaction.json"
        marker.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "Unresolved Project Governor transaction"):
            transactional_write_texts(self.root, {self.root / "target.txt": "value"})

    def test_audit_handoff_rejects_stale_next_action(self) -> None:
        self.run_script("close_session.py")
        handoff_path = self.root / ".ai" / "HANDOFF.md"
        handoff = handoff_path.read_text(encoding="utf-8").replace(
            "Ask the user whether to continue with a new task or change direction.",
            "Resume the current task inside its approved scope.",
        )
        handoff_path.write_text(handoff, encoding="utf-8")
        result = self.run_script("audit_handoff.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("HANDOFF next action mismatch", result.stdout)

    def test_audit_handoff_reports_each_invariant_once(self) -> None:
        self.run_script("close_session.py")
        graph_path = self.root / ".ai" / "task_graph.yaml"
        graph_path.write_text(graph_path.read_text(encoding="utf-8").replace("status: completed", "status: in_progress"), encoding="utf-8")
        result = self.run_script("audit_handoff.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("Task status mismatch: T-0001"), 1)


if __name__ == "__main__":
    unittest.main()
