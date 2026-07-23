from __future__ import annotations

import datetime
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path
import sys


PYTHON = sys.executable
CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = CANDIDATE_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from governor_lib import transactional_write_texts, validate_action_mode


class ProjectGovernorConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.base = self.root / ".ai"
        self.base.mkdir()
        for name in [
            "PROJECT.md",
            "NON_GOALS.md",
            "ARCHITECTURE.md",
            "CONTRACTS.md",
            "CODING_STANDARDS.md",
            "CONVENTIONS.md",
            "CODEMAP.md",
            "PROGRESS.md",
            "QUALITY_GATES.md",
            "ACCEPTANCE.md",
            "DECISIONS.md",
            "KNOWN_ISSUES.md",
        ]:
            (self.base / name).write_text(f"# {name}\n", encoding="utf-8")
        (self.base / "HANDOFF.md").write_text("# Handoff\n", encoding="utf-8")
        (self.base / "tasks").mkdir()
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
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env.pop("PYTHONPATH", None)
        return subprocess.run(
            [PYTHON, "-B", str(SCRIPTS / name), str(self.root)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=CANDIDATE_ROOT,
        )

    def run_action(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env.pop("PYTHONPATH", None)
        return subprocess.run(
            [PYTHON, "-B", str(SCRIPTS / "governance_action.py"), str(self.root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=CANDIDATE_ROOT,
        )

    def set_task_status(self, status: str) -> None:
        (self.base / "tasks" / "T-0001.md").write_text(
            f"# Task T-0001: Fixture\n\n## Status\n\n{status}\n", encoding="utf-8"
        )
        (self.base / "task_graph.yaml").write_text(
            "schema_version: 1\ntasks:\n  -\n    id: T-0001\n    title: Fixture\n"
            f"    status: {status}\nedges: []\n",
            encoding="utf-8",
        )

    def write_json(self, relative: str, value: dict) -> str:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return relative

    def action_record(
        self,
        *,
        action_id: str,
        request_id: str,
        mode: str,
        latest_user_text: str,
        explicit_execution_request: bool = False,
        allowed_paths: list[str] | None = None,
    ) -> dict:
        return {
            "schema": "GovernanceAction/v1",
            "action_id": action_id,
            "request_id": request_id,
            "mode": mode,
            "task_id": "T-0001",
            "gate_id": "G-T-0001-IMPLEMENT",
            "latest_user_text": latest_user_text,
            "explicit_execution_request": explicit_execution_request,
            "allowed_paths": allowed_paths
            or [
                ".ai/gates.yaml",
                ".ai/state.yaml",
                ".ai/tasks/T-0001.md",
                ".ai/task_graph.yaml",
            ],
            "allowed_actions": [mode],
            "forbidden_actions": ["install", "activate", "create_downstream_task"],
            "stop_condition": "stop after exactly one action",
        }

    def gate_packet(self) -> dict:
        return {
            "schema": "GatePacket/v1",
            "gate_id": "G-T-0001-IMPLEMENT",
            "task_id": "T-0001",
            "title": "Fixture implementation",
            "approval_phrase": "批准 G-T-0001-IMPLEMENT",
            "rejection_phrase": "拒绝 G-T-0001-IMPLEMENT",
            "exact_allowed_paths": ["candidate/fixture.py"],
            "forbidden_effects": ["installation", "activation", "downstream task creation"],
        }

    def create_pending_gate(self) -> subprocess.CompletedProcess[str]:
        self.set_task_status("active")
        action = self.write_json(
            ".ai/evidence/T-0001/create.json",
            self.action_record(
                action_id="A-CREATE",
                request_id="REQ-CREATE",
                mode="create_pending_gate",
                latest_user_text="创建 pending Gate",
            ),
        )
        packet = self.write_json(".ai/evidence/T-0001/gate.json", self.gate_packet())
        return self.run_action("create-pending-gate", "--action-record", action, "--gate-packet", packet)

    def approve_gate(self) -> subprocess.CompletedProcess[str]:
        created = self.create_pending_gate()
        self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
        action = self.write_json(
            ".ai/evidence/T-0001/approve.json",
            self.action_record(
                action_id="A-APPROVE",
                request_id="REQ-APPROVE",
                mode="approve_pending_gate",
                latest_user_text="批准 G-T-0001-IMPLEMENT",
            ),
        )
        return self.run_action(
            "decide-pending-gate", "--action-record", action, "--decision", "approved"
        )

    def start_execution(self) -> subprocess.CompletedProcess[str]:
        approved = self.approve_gate()
        self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
        action = self.write_json(
            ".ai/evidence/T-0001/execute.json",
            self.action_record(
                action_id="A-EXECUTE",
                request_id="REQ-EXECUTE",
                mode="execute_approved_gate",
                latest_user_text="执行已批准的 G-T-0001-IMPLEMENT",
                explicit_execution_request=True,
            ),
        )
        return self.run_action("start-approved-execution", "--action-record", action)

    def json_block(self, text: str, name: str) -> dict:
        begin = f"<!-- PROJECT-GOVERNOR-{name}-BEGIN -->"
        end = f"<!-- PROJECT-GOVERNOR-{name}-END -->"
        start = text.index(begin) + len(begin)
        stop = text.index(end, start)
        payload = text[start:stop].strip()
        if payload.startswith("```json") and payload.endswith("```"):
            payload = payload[len("```json") : -3].strip()
        return json.loads(payload)

    def replace_json_block(self, text: str, name: str, value: dict) -> str:
        begin = f"<!-- PROJECT-GOVERNOR-{name}-BEGIN -->"
        end = f"<!-- PROJECT-GOVERNOR-{name}-END -->"
        start = text.index(begin) + len(begin)
        stop = text.index(end, start)
        payload = "\n```json\n" + json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n```\n"
        return text[:start] + payload + text[stop:]

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

    def test_candidate_test_runner_has_no_global_project_governor_dependency(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        self.assertEqual(SCRIPTS, CANDIDATE_ROOT / "scripts")
        global_skill_fragment = ".codex" + "\\skills\\" + "project-governor"
        self.assertNotIn(global_skill_fragment, source)

    def test_governance_action_create_approve_and_execute_are_distinct_transitions(self) -> None:
        started = self.start_execution()
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        self.assertEqual(
            (self.base / "tasks" / "T-0001.md").read_text(encoding="utf-8").split("## Status", 1)[1].strip(),
            "in_progress",
        )
        state = (self.base / "state.yaml").read_text(encoding="utf-8")
        self.assertIn("current_gate_id: null", state)
        gate = (self.base / "gates.yaml").read_text(encoding="utf-8")
        self.assertIn("status: approved", gate)
        self.assertIn("execution_status: in_progress", gate)
        self.assertIn("execution_evidence: .ai/evidence/T-0001/execute.json", gate)

    def test_governance_action_records_rejection_without_execution_authority(self) -> None:
        created = self.create_pending_gate()
        self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
        action = self.write_json(
            ".ai/evidence/T-0001/reject.json",
            self.action_record(
                action_id="A-REJECT",
                request_id="REQ-REJECT",
                mode="approve_pending_gate",
                latest_user_text="拒绝 G-T-0001-IMPLEMENT",
            ),
        )
        result = self.run_action(
            "decide-pending-gate", "--action-record", action, "--decision", "rejected"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("rejected", (self.base / "tasks" / "T-0001.md").read_text(encoding="utf-8"))
        self.assertNotIn("execution_evidence", (self.base / "gates.yaml").read_text(encoding="utf-8"))

    def test_governance_action_rejects_reused_request_id_before_write(self) -> None:
        created = self.create_pending_gate()
        self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
        before = {
            name: (self.base / name).read_bytes()
            for name in ["gates.yaml", "state.yaml", "task_graph.yaml", "tasks/T-0001.md"]
        }
        action = self.write_json(
            ".ai/evidence/T-0001/reused.json",
            self.action_record(
                action_id="A-REUSED",
                request_id="REQ-CREATE",
                mode="approve_pending_gate",
                latest_user_text="批准 G-T-0001-IMPLEMENT",
            ),
        )
        result = self.run_action(
            "decide-pending-gate", "--action-record", action, "--decision", "approved"
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("REQUEST_REUSE", result.stdout + result.stderr)
        for name, content in before.items():
            self.assertEqual((self.base / name).read_bytes(), content)

    def test_governance_action_rejects_execution_without_exact_request(self) -> None:
        approved = self.approve_gate()
        self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
        before = (self.base / "gates.yaml").read_bytes()
        action = self.write_json(
            ".ai/evidence/T-0001/no-execute.json",
            self.action_record(
                action_id="A-NO-EXECUTE",
                request_id="REQ-NO-EXECUTE",
                mode="execute_approved_gate",
                latest_user_text="继续",
                explicit_execution_request=False,
            ),
        )
        result = self.run_action("start-approved-execution", "--action-record", action)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("explicit execution request", result.stdout + result.stderr)
        self.assertEqual((self.base / "gates.yaml").read_bytes(), before)

    def test_governance_action_rejects_path_escape_before_write(self) -> None:
        self.set_task_status("active")
        action_value = self.action_record(
            action_id="A-ESCAPE",
            request_id="REQ-ESCAPE",
            mode="create_pending_gate",
            latest_user_text="创建 pending Gate",
            allowed_paths=["../escape", ".ai/gates.yaml", ".ai/state.yaml"],
        )
        action = self.write_json(".ai/evidence/T-0001/escape.json", action_value)
        packet = self.write_json(".ai/evidence/T-0001/gate.json", self.gate_packet())
        before = (self.base / "gates.yaml").read_bytes()
        result = self.run_action("create-pending-gate", "--action-record", action, "--gate-packet", packet)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("SCOPE_VIOLATION", result.stdout + result.stderr)
        self.assertEqual((self.base / "gates.yaml").read_bytes(), before)

    def test_governance_action_cli_rejects_same_process_chaining(self) -> None:
        self.set_task_status("active")
        action = self.write_json(
            ".ai/evidence/T-0001/create.json",
            self.action_record(
                action_id="A-CREATE",
                request_id="REQ-CREATE",
                mode="create_pending_gate",
                latest_user_text="创建 pending Gate",
            ),
        )
        packet = self.write_json(".ai/evidence/T-0001/gate.json", self.gate_packet())
        before = (self.base / "gates.yaml").read_bytes()
        result = self.run_action(
            "create-pending-gate",
            "--action-record",
            action,
            "--gate-packet",
            packet,
            "decide-pending-gate",
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual((self.base / "gates.yaml").read_bytes(), before)

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
        handoff = handoff_path.read_text(encoding="utf-8")
        action = self.json_block(handoff, "NEXT-ACTION")
        action["next_action_mode"] = "execute_approved_gate"
        action["copyable_next_prompt"] = "继续执行"
        handoff = self.replace_json_block(handoff, "NEXT-ACTION", action)
        handoff_path.write_text(handoff, encoding="utf-8")
        result = self.run_script("audit_handoff.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("HANDOFF next-action contract mismatch", result.stdout)

    def test_close_session_writes_chinese_next_action_and_stable_checkpoint(self) -> None:
        approved = self.approve_gate()
        self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
        result = self.run_script("close_session.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        handoff = (self.base / "HANDOFF.md").read_text(encoding="utf-8")
        action = self.json_block(handoff, "NEXT-ACTION")
        checkpoint = self.json_block(handoff, "CHECKPOINT")
        self.assertEqual(action["exact_next_user_phrase"], "执行已批准的 G-T-0001-IMPLEMENT")
        self.assertTrue(action["next_action_requires_explicit_user_request"])
        self.assertEqual(checkpoint["schema"], "Checkpoint/v1.0")
        self.assertEqual(checkpoint["contract_id"], "PCC-2026-07-16-R1")
        self.assertEqual(checkpoint["requirements_revision"], "T-0034-REQ-2026-07-16-R1")
        self.assertEqual(checkpoint["active_transactions"], [])
        self.assertEqual(checkpoint["in_flight_actors"], [])
        self.assertEqual(self.run_script("audit_handoff.py").returncode, 0)

    def test_audit_handoff_rejects_missing_structured_field(self) -> None:
        self.run_script("close_session.py")
        path = self.base / "HANDOFF.md"
        handoff = path.read_text(encoding="utf-8")
        action = self.json_block(handoff, "NEXT-ACTION")
        action.pop("stop_condition")
        path.write_text(self.replace_json_block(handoff, "NEXT-ACTION", action), encoding="utf-8")
        result = self.run_script("audit_handoff.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("missing field: stop_condition", result.stdout)

    def test_audit_handoff_rejects_unknown_structured_field(self) -> None:
        self.run_script("close_session.py")
        path = self.base / "HANDOFF.md"
        handoff = path.read_text(encoding="utf-8")
        action = self.json_block(handoff, "NEXT-ACTION")
        action["unexpected"] = "forbidden"
        path.write_text(self.replace_json_block(handoff, "NEXT-ACTION", action), encoding="utf-8")
        result = self.run_script("audit_handoff.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("unknown field: unexpected", result.stdout)

    def test_audit_handoff_rejects_checkpoint_missing_authority_hash(self) -> None:
        self.run_script("close_session.py")
        path = self.base / "HANDOFF.md"
        handoff = path.read_text(encoding="utf-8")
        checkpoint = self.json_block(handoff, "CHECKPOINT")
        checkpoint.pop("authority_hash")
        path.write_text(self.replace_json_block(handoff, "CHECKPOINT", checkpoint), encoding="utf-8")
        result = self.run_script("audit_handoff.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("checkpoint missing field: authority_hash", result.stdout)

    def test_audit_handoff_rejects_marker_only_prose(self) -> None:
        self.run_script("close_session.py")
        path = self.base / "HANDOFF.md"
        handoff = path.read_text(encoding="utf-8")
        for name in ["NEXT-ACTION", "CHECKPOINT"]:
            begin = f"<!-- PROJECT-GOVERNOR-{name}-BEGIN -->"
            end = f"<!-- PROJECT-GOVERNOR-{name}-END -->"
            start = handoff.index(begin)
            stop = handoff.index(end, start) + len(end)
            handoff = handoff[:start] + handoff[stop:]
        handoff += "\nResume the current task inside its approved scope.\n"
        path.write_text(handoff, encoding="utf-8")
        result = self.run_script("audit_handoff.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("structured next-action contract", result.stdout)

    def test_final_validation_manifest_binds_hash_size_and_mtime(self) -> None:
        started = self.start_execution()
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        target = self.root / "target.py"
        test_path = self.root / "test_target.py"
        target.write_text("VALUE = 1\n", encoding="utf-8")
        test_path.write_text("assert True\n", encoding="utf-8")
        manifest = ".ai/evidence/T-0001/final-validation.yaml"
        snapshot_record = self.write_json(
            ".ai/evidence/T-0001/snapshot.json",
            self.action_record(
                action_id="A-SNAPSHOT",
                request_id="REQ-SNAPSHOT",
                mode="execute_approved_gate",
                latest_user_text="执行已批准的 G-T-0001-IMPLEMENT",
                explicit_execution_request=True,
                allowed_paths=[manifest],
            ),
        )
        snapshot = self.run_action(
            "snapshot-final-validation",
            "--action-record",
            snapshot_record,
            "--path",
            "target.py",
            "--path",
            "test_target.py",
            "--protected-path",
            str(SCRIPTS / "governor_lib.py"),
        )
        self.assertEqual(snapshot.returncode, 0, snapshot.stdout + snapshot.stderr)
        token = next(line.split(" ", 1)[1] for line in snapshot.stdout.splitlines() if line.startswith("[snapshot-token] "))
        validation_started = datetime.datetime.now().astimezone().isoformat()
        validation_completed = datetime.datetime.now().astimezone().isoformat()
        command_evidence = self.write_json(
            ".ai/evidence/T-0001/validation.json",
            {
                "validation_started_at": validation_started,
                "validation_completed_at": validation_completed,
                "exact_command_argv": [PYTHON, "-B", "test_target.py"],
                "exit_code": 0,
                "test_count": 1,
            },
        )
        bind_record = self.write_json(
            ".ai/evidence/T-0001/bind.json",
            self.action_record(
                action_id="A-BIND",
                request_id="REQ-BIND",
                mode="execute_approved_gate",
                latest_user_text="执行已批准的 G-T-0001-IMPLEMENT",
                explicit_execution_request=True,
                allowed_paths=[manifest],
            ),
        )
        bound = self.run_action(
            "bind-final-validation",
            "--action-record",
            bind_record,
            "--snapshot-token",
            token,
            "--command-evidence",
            command_evidence,
            "--manifest",
            manifest,
        )
        self.assertEqual(bound.returncode, 0, bound.stdout + bound.stderr)
        content = (self.root / manifest).read_text(encoding="utf-8")
        self.assertIn("test_count: 1", content)
        self.assertIn("mtime_ns:", content)
        self.assertIn("protected_global_hashes:", content)

    def test_final_validation_snapshot_accepts_inline_action_with_existing_evidence(self) -> None:
        started = self.start_execution()
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        (self.root / "target.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.root / "test_target.py").write_text("assert True\n", encoding="utf-8")
        record = self.action_record(
            action_id="A-INLINE-SNAPSHOT",
            request_id="REQ-INLINE-SNAPSHOT",
            mode="execute_approved_gate",
            latest_user_text="执行已批准的 G-T-0001-IMPLEMENT",
            explicit_execution_request=True,
            allowed_paths=[".ai/evidence/T-0001/final-validation.yaml"],
        )
        result = self.run_action(
            "snapshot-final-validation",
            "--action-record-json",
            json.dumps(record, ensure_ascii=False),
            "--action-evidence",
            ".ai/evidence/T-0001/execute.json",
            "--path",
            "target.py",
            "--path",
            "test_target.py",
            "--protected-path",
            "target.py",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[snapshot-token] ", result.stdout)
        token = next(line.split(" ", 1)[1] for line in result.stdout.splitlines() if line.startswith("[snapshot-token] "))
        command = {
            "validation_started_at": datetime.datetime.now().astimezone().isoformat(),
            "validation_completed_at": datetime.datetime.now().astimezone().isoformat(),
            "exact_command_argv": [PYTHON, "-B", "test_target.py"],
            "exit_code": 0,
            "test_count": 1,
        }
        bind_record = self.action_record(
            action_id="A-INLINE-BIND",
            request_id="REQ-INLINE-BIND",
            mode="execute_approved_gate",
            latest_user_text="执行已批准的 G-T-0001-IMPLEMENT",
            explicit_execution_request=True,
            allowed_paths=[".ai/evidence/T-0001/final-validation.yaml"],
        )
        bound = self.run_action(
            "bind-final-validation",
            "--action-record-json",
            json.dumps(bind_record, ensure_ascii=False),
            "--action-evidence",
            ".ai/evidence/T-0001/execute.json",
            "--snapshot-token",
            token,
            "--command-evidence-json",
            json.dumps(command),
            "--command-evidence-ref",
            ".ai/evidence/T-0001/commands.md",
            "--manifest",
            ".ai/evidence/T-0001/final-validation.yaml",
        )
        self.assertEqual(bound.returncode, 0, bound.stdout + bound.stderr)

    def test_final_validation_rejects_target_changed_after_snapshot(self) -> None:
        started = self.start_execution()
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        target = self.root / "target.py"
        test_path = self.root / "test_target.py"
        target.write_text("VALUE = 1\n", encoding="utf-8")
        test_path.write_text("assert True\n", encoding="utf-8")
        manifest = ".ai/evidence/T-0001/final-validation.yaml"
        snapshot_record = self.write_json(
            ".ai/evidence/T-0001/snapshot.json",
            self.action_record(
                action_id="A-SNAPSHOT",
                request_id="REQ-SNAPSHOT",
                mode="execute_approved_gate",
                latest_user_text="执行已批准的 G-T-0001-IMPLEMENT",
                explicit_execution_request=True,
                allowed_paths=[manifest],
            ),
        )
        snapshot = self.run_action(
            "snapshot-final-validation",
            "--action-record",
            snapshot_record,
            "--path",
            "target.py",
            "--path",
            "test_target.py",
            "--protected-path",
            "target.py",
        )
        self.assertEqual(snapshot.returncode, 0, snapshot.stdout + snapshot.stderr)
        token = next(line.split(" ", 1)[1] for line in snapshot.stdout.splitlines() if line.startswith("[snapshot-token] "))
        target.write_text("VALUE = 2\n", encoding="utf-8")
        validation_started = datetime.datetime.now().astimezone().isoformat()
        validation_completed = datetime.datetime.now().astimezone().isoformat()
        evidence = self.write_json(
            ".ai/evidence/T-0001/validation.json",
            {
                "validation_started_at": validation_started,
                "validation_completed_at": validation_completed,
                "exact_command_argv": [PYTHON, "-B", "test_target.py"],
                "exit_code": 0,
                "test_count": 1,
            },
        )
        bind_record = self.write_json(
            ".ai/evidence/T-0001/bind.json",
            self.action_record(
                action_id="A-BIND",
                request_id="REQ-BIND",
                mode="execute_approved_gate",
                latest_user_text="执行已批准的 G-T-0001-IMPLEMENT",
                explicit_execution_request=True,
                allowed_paths=[manifest],
            ),
        )
        result = self.run_action(
            "bind-final-validation",
            "--action-record",
            bind_record,
            "--snapshot-token",
            token,
            "--command-evidence",
            evidence,
            "--manifest",
            manifest,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("STALE_FINAL_VALIDATION", result.stdout + result.stderr)
        self.assertFalse((self.root / manifest).exists())

    def test_audit_handoff_reports_each_invariant_once(self) -> None:
        self.run_script("close_session.py")
        graph_path = self.root / ".ai" / "task_graph.yaml"
        graph_path.write_text(graph_path.read_text(encoding="utf-8").replace("status: completed", "status: in_progress"), encoding="utf-8")
        result = self.run_script("audit_handoff.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("Task status mismatch: T-0001"), 1)


if __name__ == "__main__":
    unittest.main()
