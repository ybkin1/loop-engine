from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path
import sys


PYTHON = sys.executable
CANDIDATE_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = CANDIDATE_ROOT / ".zcode" / "tools"
sys.path.insert(0, str(SCRIPTS))

from authority_records import validate_action_mode
from governor_lib import transactional_write_texts


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
        self.install_structured_state()
        closed = self.run_script("close_session.py")
        self.assertEqual(closed.returncode, 0, closed.stdout + closed.stderr)

    def install_structured_state(self) -> None:
        from governor_lib import canonical_json, dump_yaml

        contract_root = self.base / "evidence" / "T-0034"
        contract_root.mkdir(parents=True)
        sources = []
        for relative, content in (
            (".ai/PROJECT.md", "# PROJECT.md\n"), (".ai/CONTRACTS.md", "# CONTRACTS.md\n"),
            (".ai/evidence/T-0034/project-continuity-contract.v0.2.md", "PCC-2026-07-16-R1\n"),
            (".ai/evidence/T-0034/controller-data-flow-transaction-contracts.v0.2.md", "CDFT-2026-07-16-R1\n"),
        ):
            path = self.root / relative
            path.write_text(content, encoding="utf-8")
            sources.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(), "size": path.stat().st_size})
        payload = {
            "user_origin": {"audience": "non-technical user", "capability_assumptions": ["no coding"],
                            "user_authorities": ["goal", "business_fact", "tradeoff", "risk_acceptance", "gate", "acceptance"]},
            "product_identity": {"project_id": "fixture", "one_sentence_outcome": "deliver usable software",
                                 "north_star": "real product delivery", "success_signals": ["usable"]},
            "protected_decisions": [
                {"decision_id": item, "statement": item, "rationale_ref": "fixture", "authority_ref": "fixture", "change_policy": "user_decision"}
                for item in ["USER_AUTHORITY", "CODEX_DELIVERY_RESPONSIBILITY", "EVIDENCE_ONLY_BOUNDARY", "MEANS_END_BOUNDARY"]
            ],
            "non_goals": [], "design_language": {"terms": {"Gate": "user decision"}, "forbidden_equivalences": []},
            "engineering_invariants": {key: [] for key in ["architecture", "technology", "interfaces", "coding_standards", "quality", "security"]},
            "golden_references": [], "authorization_boundaries": {"allowed_effects": ["read"], "forbidden_effects": ["install"], "current_gate_id": None},
            "lifecycle": {"phase": "test", "task_id": "T-0001", "task_status": "completed", "active_transaction_ids": [], "in_flight_actor_ids": []},
            "evidence_index": {"canonical": [], "additive": [], "superseded_not_deleted": []},
            "revision_lineage": {"parent_revision": None, "change_set_id": "fixture", "impact_assessment_ref": "fixture", "approval_ref": "fixture"},
        }
        continuity = {"schema": "ProjectContinuity/v1", "contract_id": "PCC-2026-07-16-R1",
                      "requirements_revision": "T-0034-REQ-2026-07-16-R1", "project_id": "fixture",
                      "source_manifest": sources, "source_sha256": hashlib.sha256(canonical_json(sources).encode()).hexdigest().upper(),
                      "semantic_sha256": hashlib.sha256(canonical_json(payload).encode()).hexdigest().upper(),
                      "created_at": "2026-07-20T00:00:00+08:00", "created_by": "fixture", "authority_ref": "fixture", "project_continuity": payload}
        (self.base / "project_continuity.yaml").write_text(dump_yaml(continuity) + "\n", encoding="utf-8")
        T0036RepairRedContractTests.write_manifest(self, ".ai/evidence/T-0001/evidence-manifest.v1.yaml", [(".ai/evidence/T-0001/commands.md", "command")])
        T0036RepairRedContractTests.write_registry(self)

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
        # T-0046: historical mismatches are [legacy] warnings, not hard blockers
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[legacy] Historical task status mismatch: T-0002", result.stdout)

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
        self.assertEqual(SCRIPTS, CANDIDATE_ROOT / ".zcode" / "tools")
        global_skill_fragment = ".codex" + "\\skills\\" + "project-governor"
        self.assertNotIn(global_skill_fragment, source)

    def test_governance_action_create_approve_and_execute_are_distinct_transitions(self) -> None:
        before = {name: (self.base / name).read_bytes() for name in ["gates.yaml", "state.yaml", "task_graph.yaml", "tasks/T-0001.md"]}
        for command in ("create-pending-gate", "decide-pending-gate", "start-approved-execution"):
            result = self.run_action(command)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("USER_DECISION_REQUIRED", result.stdout)
        for name, content in before.items():
            self.assertEqual((self.base / name).read_bytes(), content)

    def test_governance_action_records_rejection_without_execution_authority(self) -> None:
        before = (self.base / "gates.yaml").read_bytes()
        result = self.run_action("decide-pending-gate")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("USER_DECISION_REQUIRED", result.stdout)
        self.assertEqual((self.base / "gates.yaml").read_bytes(), before)

    def test_governance_action_rejects_reused_request_id_before_write(self) -> None:
        help_result = self.run_action("create-pending-gate", "--help")
        self.assertNotIn("request", (help_result.stdout + help_result.stderr).lower())
        self.assertNotIn("--action-record", help_result.stdout + help_result.stderr)

    def test_governance_action_rejects_execution_without_exact_request(self) -> None:
        before = (self.base / "gates.yaml").read_bytes()
        result = self.run_action("start-approved-execution")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("USER_DECISION_REQUIRED", result.stdout + result.stderr)
        self.assertEqual((self.base / "gates.yaml").read_bytes(), before)

    def test_governance_action_rejects_path_escape_before_write(self) -> None:
        before = (self.base / "gates.yaml").read_bytes()
        result = self.run_action("create-pending-gate", "--path", "../escape")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("unrecognized arguments", result.stdout + result.stderr)
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
        handoff = (self.base / "HANDOFF.md").read_text(encoding="utf-8")
        pending = self.json_block(handoff, "CHECKPOINT")
        self.assertEqual(pending["checkpoint_status"], "PENDING_SUCCESSOR_ACK")
        acknowledgment = {
            "checkpoint_id": pending["checkpoint_id"], "controller_generation": 2,
            "recovered_state_sha256": pending["recovered_state_sha256"],
            "acknowledged_at": "2026-07-20T00:01:00+08:00", "acknowledged_by": "fixture-successor",
            "authority_ref": "fixture-only",
        }
        T0036RepairRedContractTests.write_registry(self, acknowledgments=[acknowledgment])
        result = self.run_script("close_session.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        stable_text = (self.base / "HANDOFF.md").read_text(encoding="utf-8")
        stable = self.json_block(stable_text, "CHECKPOINT")
        self.assertEqual(stable["checkpoint_id"], pending["checkpoint_id"])
        self.assertEqual(stable["checkpoint_status"], "STABLE_FIXTURE_ONLY")
        self.assertNotIn("## Stable Checkpoint", stable_text)
        self.assertEqual(self.run_script("audit_handoff.py").returncode, 0)

    def test_audit_handoff_rejects_missing_structured_field(self) -> None:
        self.run_script("close_session.py")
        path = self.base / "HANDOFF.md"
        handoff = path.read_text(encoding="utf-8")
        action = self.json_block(handoff, "NEXT-ACTION")
        action.pop("next_action")
        path.write_text(self.replace_json_block(handoff, "NEXT-ACTION", action), encoding="utf-8")
        result = self.run_script("audit_handoff.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("missing field: next_action", result.stdout)

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
        from governor_lib import load_yaml

        _, result_relative = T0036RepairRedContractTests.configure_runner(
            self,
            "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\nunittest.main()\n",
            "bound_fingerprints",
        )
        result = self.run_action("run-final-validation")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = load_yaml(self.root / result_relative)
        self.assertEqual(manifest["status"], "bound")
        self.assertEqual(manifest["target_and_test_pre"], manifest["target_and_test_post"])
        self.assertEqual(manifest["protected_pre"], manifest["protected_post"])
        self.assertIn("mtime_ns", manifest["target_and_test_pre"][0])

    def test_final_validation_snapshot_accepts_inline_action_with_existing_evidence(self) -> None:
        help_result = self.run_action("run-final-validation", "--help")
        output = help_result.stdout + help_result.stderr
        for forbidden in ("--action-record-json", "--action-evidence", "--command-evidence-json", "--snapshot-token"):
            self.assertNotIn(forbidden, output)

    def test_final_validation_rejects_target_changed_after_snapshot(self) -> None:
        target = self.root / "target.py"
        target.write_text("VALUE = 1\n", encoding="utf-8")
        T0036RepairRedContractTests.configure_runner(
            self,
            "from pathlib import Path\nimport unittest\n"
            "class T(unittest.TestCase):\n    def test_mutate(self): Path('target.py').write_text('VALUE = 2\\n')\n"
            "unittest.main()\n",
            "stale_subject",
            extra_subjects=["target.py"],
        )
        result = self.run_action("run-final-validation")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("STALE_FINAL_VALIDATION", result.stdout + result.stderr)

    def test_audit_handoff_reports_each_invariant_once(self) -> None:
        self.run_script("close_session.py")
        graph_path = self.root / ".ai" / "task_graph.yaml"
        graph_path.write_text(graph_path.read_text(encoding="utf-8").replace("status: completed", "status: in_progress"), encoding="utf-8")
        result = self.run_script("audit_handoff.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("Task status mismatch: T-0001"), 1)


class T0036RepairRedContractTests(unittest.TestCase):
    setUp = ProjectGovernorConsistencyTests.setUp
    tearDown = ProjectGovernorConsistencyTests.tearDown
    install_structured_state = ProjectGovernorConsistencyTests.install_structured_state
    run_script = ProjectGovernorConsistencyTests.run_script
    run_action = ProjectGovernorConsistencyTests.run_action
    set_task_status = ProjectGovernorConsistencyTests.set_task_status

    def write_manifest(
        self, relative: str, subjects: list[tuple[str, str]], *, task_id: str = "T-0001", gate_id: str = "G-T-0001"
    ) -> Path:
        from governor_lib import canonical_json, dump_yaml

        entries = []
        for path, role in subjects:
            subject = self.root / path
            stat = subject.stat()
            entries.append({
                "path": path, "role": role, "required": True,
                "sha256": hashlib.sha256(subject.read_bytes()).hexdigest().upper(),
                "size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
            })
        entries.sort(key=lambda item: item["path"].casefold())
        manifest = {
            "schema": "EvidenceManifest/v1", "manifest_id": f"EM-{task_id}", "task_id": task_id,
            "gate_id": gate_id, "authority_ref": "fixture-only",
            "evidence_root": f".ai/evidence/{task_id}",
            "limits": {"max_file_count": 256, "max_per_file_bytes": 16777216,
                       "max_total_bytes": 268435456, "stream_chunk_bytes": 1048576},
            "files": entries, "file_count": len(entries),
            "total_bytes": sum(item["size"] for item in entries),
            "ordered_entries_sha256": hashlib.sha256(canonical_json(entries).encode()).hexdigest().upper(),
            "semantic_sha256": "", "created_at": "2026-07-20T00:00:00+08:00", "created_by": "fixture",
        }
        semantic = {key: value for key, value in manifest.items() if key not in {"semantic_sha256", "created_at"}}
        manifest["semantic_sha256"] = hashlib.sha256(canonical_json(semantic).encode()).hexdigest().upper()
        path = self.root / relative
        path.write_text(dump_yaml(manifest) + "\n", encoding="utf-8")
        return path

    def write_registry(self, *, acknowledgments: list[dict] | None = None, in_flight: list[dict] | None = None) -> Path:
        from governor_lib import canonical_json, dump_yaml

        registry = {
            "schema": "TransactionRegistry/v1", "contract_id": "CDFT-2026-07-16-R1",
            "requirements_revision": "T-0034-REQ-2026-07-16-R1", "project_id": "fixture",
            "controller_generation": 2, "registry_revision": 1, "state_revision_sha256": "A" * 64,
            "active_transactions": [], "in_flight_actors": in_flight or [], "unconsumed_deltas": [],
            "partial_writes": [],
            "generation_fence": {"fence_id": "F1", "fenced_generation": 1,
                                 "successor_generation": 2, "issued_at": "2026-07-20T00:00:00+08:00",
                                 "authority_ref": "fixture-only"},
            "checkpoint_acknowledgments": acknowledgments or [], "source_sha256": "B" * 64,
            "semantic_sha256": "", "updated_at": "2026-07-20T00:00:00+08:00",
            "updated_by": "fixture", "authority_ref": "fixture-only", "fixture_only": True,
        }
        semantic = {key: value for key, value in registry.items() if key not in {"semantic_sha256", "updated_at"}}
        registry["semantic_sha256"] = hashlib.sha256(canonical_json(semantic).encode()).hexdigest().upper()
        path = self.base / "transaction_registry.yaml"
        path.write_text(dump_yaml(registry) + "\n", encoding="utf-8")
        return path

    def checkpoint_bindings(self) -> tuple[dict, dict]:
        continuity = {"source_sha256": "C" * 64, "semantic_sha256": "D" * 64, "file_sha256": "E" * 64}
        evidence = {"manifest_file_sha256": "F" * 64, "semantic_sha256": "1" * 64,
                    "file_count": 1, "total_bytes": 12}
        return continuity, evidence

    def configure_runner(
        self, test_source: str, stem: str, extra_subjects: list[str] | None = None,
        *, structured_protocol: bool = True, expected_ids: list[str] | None = None,
    ) -> tuple[Path, str]:
        from governor_lib import dump_yaml

        self.set_task_status("in_progress")
        test_path = self.root / f"{stem}.py"
        guarded = test_source.replace("unittest.main()\n", "if __name__ == '__main__': unittest.main()\n")
        test_path.write_text(guarded, encoding="utf-8")
        evidence = self.base / "evidence" / "T-0001"
        (evidence / "approval.md").write_text("approved\n", encoding="utf-8")
        (evidence / "execution.md").write_text("execute\n", encoding="utf-8")
        gate = {
            "id": "G-T-0001", "task_id": "T-0001", "status": "approved", "execution_status": "in_progress",
            "approval_evidence": ".ai/evidence/T-0001/approval.md", "execution_evidence": ".ai/evidence/T-0001/execution.md",
            "controlled_final_validation": {
                "argv": [PYTHON, "-B", str(test_path)], "cwd": str(self.root), "timeout_seconds": 30,
                "environment": {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8", "PYTHONPATH": "absent"},
                "target_and_test_paths": [test_path.name, ".ai/evidence/T-0001/commands.md"] + (extra_subjects or []),
                "protected_paths": [str(self.base / "PROJECT.md")],
                "evidence_manifest": ".ai/evidence/T-0001/evidence-manifest.v1.yaml",
                "evidence_manifest_sha256": hashlib.sha256((evidence / "evidence-manifest.v1.yaml").read_bytes()).hexdigest().upper(),
                "stdout_path": f".ai/evidence/T-0001/{stem}.stdout.txt",
                "stderr_path": f".ai/evidence/T-0001/{stem}.stderr.txt",
                "result_manifest": f".ai/evidence/T-0001/{stem}.result.yaml",
            },
        }
        if structured_protocol:
            adapter = SCRIPTS / "unittest_result_adapter.py"
            adapter_stat = adapter.stat()
            test_stat = test_path.stat()
            gate["controlled_final_validation"]["argv"] = [PYTHON, "-B", str(adapter), str(test_path)]
            gate["controlled_final_validation"]["test_result_protocol"] = {
                "schema": "UnittestResultEnvelope/v1",
                "adapter_path": str(adapter),
                "adapter_fingerprint": {
                    "path": adapter.resolve().as_posix(),
                    "sha256": hashlib.sha256(adapter.read_bytes()).hexdigest().upper(),
                    "size": adapter_stat.st_size, "mtime_ns": adapter_stat.st_mtime_ns,
                },
                "test_paths": [str(test_path)],
                "test_fingerprints": [{
                    "path": test_path.resolve().as_posix(),
                    "sha256": hashlib.sha256(test_path.read_bytes()).hexdigest().upper(),
                    "size": test_stat.st_size, "mtime_ns": test_stat.st_mtime_ns,
                }],
                "expected_test_ids": expected_ids or [f"{stem}.T.test_ok"],
            }
        (self.base / "gates.yaml").write_text(dump_yaml({"schema_version": 1, "gates": [gate]}) + "\n", encoding="utf-8")
        return test_path, gate["controlled_final_validation"]["result_manifest"]

    def run_python(self, source: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env.pop("PYTHONPATH", None)
        return subprocess.run(
            [PYTHON, "-B", "-c", source],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=CANDIDATE_ROOT,
        )

    def protocol_envelope(self, path: Path, nonce: str, binding: dict, **changes) -> dict:
        from governor_lib import canonical_json

        value = {
            "schema": "UnittestResultEnvelope/v1", "run_nonce": nonce,
            "adapter_fingerprint": binding["adapter"], "test_fingerprints": binding["tests"],
            "discovered_test_ids": binding["expected_ids"], "tests_run": len(binding["expected_ids"]),
            "failures": [], "errors": [], "skipped": [], "unexpected_successes": [],
            "successful": True, "started_at": "2026-07-20T00:00:00+08:00",
            "completed_at": "2026-07-20T00:00:01+08:00", "result_sha256": "",
        }
        value.update(changes)
        semantic = {key: item for key, item in value.items() if key != "result_sha256"}
        value["result_sha256"] = hashlib.sha256(canonical_json(semantic).encode()).hexdigest().upper()
        path.write_text(json.dumps(value), encoding="utf-8")
        return value

    def test_AUTH_005_reports_secure_isolation_not_authority_availability(self) -> None:
        result = self.run_action("capability")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SECURELY_ISOLATED_AUTHORITY_LIFECYCLE_UNAVAILABLE", result.stdout)
        self.assertIn("installation_eligibility=BLOCKED", result.stdout)

    def test_AUTH_001_inline_authority_interfaces_are_absent(self) -> None:
        result = self.run_action("create-pending-gate", "--help")
        self.assertNotIn("--action-record-json", result.stdout + result.stderr)
        self.assertNotIn("--action-evidence", result.stdout + result.stderr)
        self.assertNotIn("--request-id", result.stdout + result.stderr)

    def test_TURN_001_three_processes_cannot_advance_authority_lifecycle(self) -> None:
        before = (self.base / "gates.yaml").read_bytes()
        for command in ("create-pending-gate", "decide-pending-gate", "start-approved-execution"):
            result = self.run_action(command)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("USER_DECISION_REQUIRED", result.stdout)
        self.assertEqual((self.base / "gates.yaml").read_bytes(), before)

    def test_TURN_002_fixture_events_require_hash_lineage_and_later_turn(self) -> None:
        sys.path.insert(0, str(SCRIPTS))
        from authority_records import advance_fixture_lifecycle, validate_fixture_event
        from governor_lib import GovernanceError, canonical_json

        event = {
            "schema": "AuthorityEvent/v2", "event_id": "E1", "actor_id": "fixture-user",
            "host_message_id": "M1", "host_turn_id": "0001", "exact_user_text": "fixture",
            "predecessor_event_id": None, "occurred_at": "2026-07-20T00:00:00+08:00",
            "task_id": "T-0001", "gate_id": "G-T-0001", "requested_transition": "pending",
            "lifecycle_revision": 0, "content_sha256": "",
        }
        semantic = {key: value for key, value in event.items() if key != "content_sha256"}
        event["content_sha256"] = hashlib.sha256(canonical_json(semantic).encode()).hexdigest().upper()
        event = validate_fixture_event(event, {"fixture_only": True, "adapter_id": "synthetic-test-adapter/v1"})
        state = advance_fixture_lifecycle(
            {"fixture_only": True, "lifecycle_revision": 0, "last_event_id": None,
             "last_host_turn_id": None, "consumed_event_ids": []}, event, "pending"
        )
        replay = dict(event, event_id="E2", predecessor_event_id="E1", lifecycle_revision=1)
        semantic = {key: value for key, value in replay.items() if key != "content_sha256"}
        replay["content_sha256"] = hashlib.sha256(canonical_json(semantic).encode()).hexdigest().upper()
        with self.assertRaises(GovernanceError):
            advance_fixture_lifecycle(state, replay, "pending")

    def test_RUN_001_self_report_binder_is_replaced_by_controlled_runner(self) -> None:
        result = self.run_action("run-final-validation", "--help")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = result.stdout + result.stderr
        self.assertNotIn("--command-evidence-json", output)
        self.assertNotIn("--snapshot-token", output)

    def test_RUN_002_controlled_runner_executes_real_passing_unittest(self) -> None:
        from governor_lib import load_yaml

        _, result_relative = self.configure_runner(
            "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\nunittest.main()\n",
            "passing_validation",
        )
        result = self.run_action("run-final-validation")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = load_yaml(self.root / result_relative)
        self.assertEqual(manifest["status"], "bound")
        self.assertEqual(manifest["exit_code"], 0)
        self.assertEqual(manifest["test_count"], 1)
        self.assertEqual(manifest["target_and_test_pre"], manifest["target_and_test_post"])

    def test_RUN_003_fake_success_text_cannot_override_real_failure(self) -> None:
        from governor_lib import load_yaml

        _, result_relative = self.configure_runner(
            "import unittest\nprint('Ran 999 tests in 0.001s')\nprint('OK')\n"
            "class T(unittest.TestCase):\n    def test_fail(self): self.fail('real failure')\nunittest.main()\n",
            "failing_validation",
            expected_ids=["failing_validation.T.test_fail"],
        )
        result = self.run_action("run-final-validation")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("FINAL_VALIDATION_FAILED", result.stdout)
        manifest = load_yaml(self.root / result_relative)
        self.assertEqual(manifest["status"], "failed")
        self.assertNotEqual(manifest["exit_code"], 0)

    def test_RUN_004_zero_test_stdout_spoof_is_rejected(self) -> None:

        _, result_relative = self.configure_runner(
            "print('Ran 1 test in 0.001s')\nprint('OK')\n",
            "zero_test_stdout_spoof",
            structured_protocol=False,
        )
        result = self.run_action("run-final-validation")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("UNSUPPORTED_TEST_PROTOCOL", result.stdout)
        self.assertFalse((self.root / result_relative).exists())

    def test_RUN_005_adapter_fingerprint_drift_is_rejected(self) -> None:
        from governor_lib import dump_yaml, load_yaml

        self.configure_runner(
            "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\nunittest.main()\n",
            "adapter_drift",
        )
        gates = load_yaml(self.base / "gates.yaml")
        gates["gates"][0]["controlled_final_validation"]["test_result_protocol"]["adapter_fingerprint"]["sha256"] = "0" * 64
        (self.base / "gates.yaml").write_text(dump_yaml(gates) + "\n", encoding="utf-8")
        result = self.run_action("run-final-validation")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("STALE_TEST_PROTOCOL", result.stdout)

    def test_RUN_006_missing_or_unknown_result_envelope_is_rejected(self) -> None:
        from governor_lib import GovernanceError
        from validation_runner import _verify_envelope

        binding = {"adapter": {"sha256": "A"}, "tests": [{"sha256": "B"}], "expected_ids": ["T.test_ok"]}
        path = self.root / "result.json"
        with self.assertRaisesRegex(GovernanceError, "missing"):
            _verify_envelope(path, "nonce", binding)
        value = self.protocol_envelope(path, "nonce", binding, unknown=True)
        self.assertIn("unknown", value)
        with self.assertRaisesRegex(GovernanceError, "fields are invalid"):
            _verify_envelope(path, "nonce", binding)
        path.write_text('{"schema":"UnittestResultEnvelope/v1","schema":"duplicate"}', encoding="utf-8")
        with self.assertRaisesRegex(GovernanceError, "Duplicate"):
            _verify_envelope(path, "nonce", binding)

    def test_RUN_007_nonce_fingerprint_and_count_mismatch_are_rejected(self) -> None:
        from governor_lib import GovernanceError
        from validation_runner import _verify_envelope

        binding = {"adapter": {"sha256": "A"}, "tests": [{"sha256": "B"}], "expected_ids": ["T.test_ok"]}
        cases = (
            {"run_nonce": "wrong"},
            {"adapter_fingerprint": {"sha256": "wrong"}},
            {"discovered_test_ids": [] , "tests_run": 0},
            {"tests_run": 2},
        )
        for index, changes in enumerate(cases):
            path = self.root / f"result-{index}.json"
            self.protocol_envelope(path, "nonce", binding, **changes)
            with self.assertRaises(GovernanceError):
                _verify_envelope(path, "nonce", binding)

    def test_RUN_008_non_clean_structured_result_is_rejected(self) -> None:
        from governor_lib import GovernanceError
        from validation_runner import _verify_envelope

        binding = {"adapter": {"sha256": "A"}, "tests": [{"sha256": "B"}], "expected_ids": ["T.test_ok"]}
        for index, changes in enumerate((
            {"failures": ["T.test_ok"], "successful": False},
            {"errors": ["T.test_ok"], "successful": False},
            {"skipped": ["T.test_ok"]},
            {"unexpected_successes": ["T.test_ok"], "successful": False},
        )):
            path = self.root / f"failed-{index}.json"
            self.protocol_envelope(path, "nonce", binding, **changes)
            with self.assertRaisesRegex(GovernanceError, "not a clean success"):
                _verify_envelope(path, "nonce", binding)

    def test_RUN_009_test_fingerprint_drift_is_rejected(self) -> None:
        from governor_lib import dump_yaml, load_yaml

        self.configure_runner(
            "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\nunittest.main()\n",
            "test_drift",
        )
        gates = load_yaml(self.base / "gates.yaml")
        gates["gates"][0]["controlled_final_validation"]["test_result_protocol"]["test_fingerprints"][0]["sha256"] = "0" * 64
        (self.base / "gates.yaml").write_text(dump_yaml(gates) + "\n", encoding="utf-8")
        result = self.run_action("run-final-validation")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("STALE_TEST_PROTOCOL", result.stdout)

    def test_PC_002_missing_project_continuity_preserves_handoff(self) -> None:
        before = (self.base / "HANDOFF.md").read_bytes()
        (self.base / "project_continuity.yaml").unlink()
        result = self.run_script("close_session.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("PROJECT_CONTINUITY_MISSING", result.stdout + result.stderr)
        self.assertEqual((self.base / "HANDOFF.md").read_bytes(), before)

    def test_PC_003_source_drift_blocks_handoff_replacement(self) -> None:
        before = (self.base / "HANDOFF.md").read_bytes()
        (self.base / "PROJECT.md").write_text("drift\n", encoding="utf-8")
        result = self.run_script("close_session.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("PROJECT_CONTINUITY_SOURCE_DRIFT", result.stdout)
        self.assertEqual((self.base / "HANDOFF.md").read_bytes(), before)

    def test_PC_004_semantic_hash_mismatch_is_rejected(self) -> None:
        from governor_lib import dump_yaml, load_yaml

        path = self.base / "project_continuity.yaml"
        value = load_yaml(path)
        value["project_continuity"]["product_identity"]["north_star"] = "tampered"
        path.write_text(dump_yaml(value) + "\n", encoding="utf-8")
        result = self.run_script("close_session.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("PROJECT_CONTINUITY_HASH_MISMATCH", result.stdout)

    def test_PC_005_unknown_field_is_rejected(self) -> None:
        from governor_lib import dump_yaml, load_yaml

        path = self.base / "project_continuity.yaml"
        value = load_yaml(path)
        value["unknown"] = True
        path.write_text(dump_yaml(value) + "\n", encoding="utf-8")
        result = self.run_script("validate_state.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("PROJECT_CONTINUITY_INVALID", result.stdout)

    def test_TR_001_missing_registry_never_emits_stable_checkpoint(self) -> None:
        (self.base / "transaction_registry.yaml").unlink()
        result = self.run_script("close_session.py")
        text = (self.base / "HANDOFF.md").read_text(encoding="utf-8")
        self.assertNotIn("## Stable Checkpoint", text)
        self.assertIn("NOT_ESTABLISHED", result.stdout + result.stderr + text)

    def test_TR_002_checkpoint_waits_for_successor_acknowledgment(self) -> None:
        from transaction_registry import checkpoint_status, load_transaction_registry

        self.write_registry()
        continuity, evidence = self.checkpoint_bindings()
        checkpoint = checkpoint_status(load_transaction_registry(self.root), continuity, evidence, "2" * 64, "3" * 64)
        self.assertEqual(checkpoint["checkpoint_status"], "PENDING_SUCCESSOR_ACK")

    def test_TR_003_fixture_ack_promotes_same_checkpoint_id_only_to_fixture_stable(self) -> None:
        from transaction_registry import checkpoint_status, load_transaction_registry

        self.write_registry()
        continuity, evidence = self.checkpoint_bindings()
        pending = checkpoint_status(load_transaction_registry(self.root), continuity, evidence, "2" * 64, "3" * 64)
        acknowledgment = {
            "checkpoint_id": pending["checkpoint_id"], "controller_generation": 2,
            "recovered_state_sha256": pending["recovered_state_sha256"],
            "acknowledged_at": "2026-07-20T00:01:00+08:00", "acknowledged_by": "fixture-successor",
            "authority_ref": "fixture-only",
        }
        self.write_registry(acknowledgments=[acknowledgment])
        stable = checkpoint_status(load_transaction_registry(self.root), continuity, evidence, "2" * 64, "3" * 64)
        self.assertEqual(stable["checkpoint_id"], pending["checkpoint_id"])
        self.assertEqual(stable["checkpoint_status"], "STABLE_FIXTURE_ONLY")

    def test_TR_004_in_flight_actor_blocks_stability(self) -> None:
        from transaction_registry import checkpoint_status, load_transaction_registry

        self.write_registry(in_flight=[{"actor_id": "A1", "packet_id": "P1", "generation": 2, "status": "running"}])
        continuity, evidence = self.checkpoint_bindings()
        result = checkpoint_status(load_transaction_registry(self.root), continuity, evidence, "2" * 64, "3" * 64)
        self.assertEqual(result["checkpoint_status"], "NOT_ESTABLISHED")
        self.assertIn("NONEMPTY_IN_FLIGHT_ACTORS", result["blockers"])

    def test_GATE_001_and_LIFE_001_use_structured_projection(self) -> None:
        source = (SCRIPTS / "continuity_producer.py").read_text(encoding="utf-8")
        self.assertIn("approved_execution_gate_id", source)
        self.assertNotIn('"TBD"', source)
        self.assertNotIn("'TBD'", source)

    def test_GATE_001_current_gate_and_approved_execution_gate_are_distinct(self) -> None:
        self.set_task_status("in_progress")
        evidence = self.base / "evidence" / "T-0001"
        (evidence / "approval.md").write_text("approved\n", encoding="utf-8")
        (evidence / "execution.md").write_text("execute\n", encoding="utf-8")
        (self.base / "gates.yaml").write_text(
            "schema_version: 1\ngates:\n  -\n    id: G-T-0001\n    task_id: T-0001\n    status: approved\n"
            "    execution_status: in_progress\n    approval_evidence: .ai/evidence/T-0001/approval.md\n"
            "    execution_evidence: .ai/evidence/T-0001/execution.md\n",
            encoding="utf-8",
        )
        result = self.run_script("close_session.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        action = ProjectGovernorConsistencyTests.json_block(self, (self.base / "HANDOFF.md").read_text(encoding="utf-8"), "NEXT-ACTION")
        self.assertIsNone(action["current_gate_id"])
        self.assertEqual(action["approved_execution_gate_id"], "G-T-0001")
        self.assertEqual(self.run_script("audit_handoff.py").returncode, 0)

    def test_GATE_002_independent_auditor_rejects_mutated_projection(self) -> None:
        handoff_path = self.base / "HANDOFF.md"
        text = handoff_path.read_text(encoding="utf-8")
        action = ProjectGovernorConsistencyTests.json_block(self, text, "NEXT-ACTION")
        action["current_gate_id"] = "G-FORGED"
        handoff_path.write_text(ProjectGovernorConsistencyTests.replace_json_block(self, text, "NEXT-ACTION", action), encoding="utf-8")
        result = self.run_script("audit_handoff.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("independently reconstructed", result.stdout)

    def test_LIFE_001_unperformed_lifecycle_never_collapses_to_none(self) -> None:
        lifecycle = ProjectGovernorConsistencyTests.json_block(
            self, (self.base / "HANDOFF.md").read_text(encoding="utf-8"), "LIFECYCLE"
        )
        self.assertIn("FRESH_INDEPENDENT_REREVIEW_NOT_PERFORMED", lifecycle["unverified"])
        self.assertIn("INSTALLATION_AUTHORIZED", lifecycle["not_authorized"])
        self.assertEqual(lifecycle["installation_eligibility"], "BLOCKED")

    def test_ARCH_001_producer_and_auditor_have_independent_modules(self) -> None:
        expected = {
            "authority_records.py",
            "validation_runner.py",
            "continuity_producer.py",
            "continuity_auditor.py",
            "evidence_manifest.py",
            "transaction_registry.py",
        }
        self.assertTrue(expected.issubset({path.name for path in SCRIPTS.iterdir()}))
        auditor = (SCRIPTS / "continuity_auditor.py").read_text(encoding="utf-8")
        self.assertNotIn("continuity_producer", auditor)

    def test_EM_002_missing_manifest_fails_closed(self) -> None:
        source = (
            "import sys; from pathlib import Path; "
            f"sys.path.insert(0, {str(SCRIPTS)!r}); "
            "from evidence_manifest import verify_evidence_manifest; "
            f"verify_evidence_manifest(Path({str(self.root)!r}), '.ai/evidence/T-0001/missing.yaml')"
        )
        result = self.run_python(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("EVIDENCE_MANIFEST_REQUIRED", result.stdout + result.stderr)

    def test_EM_001_bounded_manifest_streams_exact_subjects(self) -> None:
        from evidence_manifest import verify_evidence_manifest

        relative = ".ai/evidence/T-0001/evidence-manifest.v1.yaml"
        self.write_manifest(relative, [(".ai/evidence/T-0001/commands.md", "command")])
        binding = verify_evidence_manifest(self.root, relative)
        self.assertEqual(binding["file_count"], 1)
        self.assertEqual(binding["total_bytes"], (self.base / "evidence" / "T-0001" / "commands.md").stat().st_size)

    def test_EM_004_tampered_subject_is_rejected(self) -> None:
        from evidence_manifest import verify_evidence_manifest
        from governor_lib import GovernanceError

        relative = ".ai/evidence/T-0001/evidence-manifest.v1.yaml"
        self.write_manifest(relative, [(".ai/evidence/T-0001/commands.md", "command")])
        (self.base / "evidence" / "T-0001" / "commands.md").write_text("changed\n", encoding="utf-8")
        with self.assertRaises(GovernanceError) as caught:
            verify_evidence_manifest(self.root, relative)
        self.assertEqual(caught.exception.code, "EVIDENCE_FINGERPRINT_MISMATCH")

    def test_EM_003_manifest_is_create_only(self) -> None:
        from evidence_manifest import write_manifest_create_only
        from governor_lib import GovernanceError

        path = self.base / "evidence" / "T-0001" / "immutable.yaml"
        write_manifest_create_only(path, {"schema": "fixture"})
        original = path.read_bytes()
        with self.assertRaises(GovernanceError):
            write_manifest_create_only(path, {"schema": "changed"})
        self.assertEqual(path.read_bytes(), original)

    def test_HASH_001_manifest_file_count_limit_is_enforced(self) -> None:
        from evidence_manifest import verify_evidence_manifest
        from governor_lib import GovernanceError, dump_yaml, load_yaml

        second = self.base / "evidence" / "T-0001" / "second.md"
        second.write_text("second\n", encoding="utf-8")
        relative = ".ai/evidence/T-0001/evidence-manifest.v1.yaml"
        path = self.write_manifest(relative, [
            (".ai/evidence/T-0001/commands.md", "command"), (".ai/evidence/T-0001/second.md", "source")
        ])
        value = load_yaml(path)
        value["limits"]["max_file_count"] = 1
        path.write_text(dump_yaml(value) + "\n", encoding="utf-8")
        with self.assertRaises(GovernanceError) as caught:
            verify_evidence_manifest(self.root, relative)
        self.assertEqual(caught.exception.code, "EVIDENCE_LIMIT_EXCEEDED")

    def test_HASH_002_per_file_limit_is_enforced_before_hashing(self) -> None:
        from evidence_manifest import verify_evidence_manifest
        from governor_lib import GovernanceError, dump_yaml, load_yaml

        relative = ".ai/evidence/T-0001/evidence-manifest.v1.yaml"
        path = self.write_manifest(relative, [(".ai/evidence/T-0001/commands.md", "command")])
        value = load_yaml(path)
        value["limits"]["max_per_file_bytes"] = 1
        path.write_text(dump_yaml(value) + "\n", encoding="utf-8")
        with self.assertRaises(GovernanceError) as caught:
            verify_evidence_manifest(self.root, relative)
        self.assertEqual(caught.exception.code, "EVIDENCE_LIMIT_EXCEEDED")

    def test_HASH_003_traversal_ads_and_case_collisions_are_rejected(self) -> None:
        from evidence_manifest import verify_evidence_manifest
        from governor_lib import GovernanceError, dump_yaml, load_yaml

        relative = ".ai/evidence/T-0001/evidence-manifest.v1.yaml"
        path = self.write_manifest(relative, [(".ai/evidence/T-0001/commands.md", "command")])
        value = load_yaml(path)
        for invalid in ("../outside", ".ai/evidence/T-0001/commands.md:ads"):
            value["files"][0]["path"] = invalid
            path.write_text(dump_yaml(value) + "\n", encoding="utf-8")
            with self.assertRaises(GovernanceError):
                verify_evidence_manifest(self.root, relative)

    def test_HASH_004_symlink_subject_is_rejected(self) -> None:
        from evidence_manifest import verify_evidence_manifest
        from governor_lib import GovernanceError

        target = self.base / "evidence" / "T-0001" / "commands.md"
        link = self.root / "linked-evidence.md"
        os.symlink(target, link)
        relative = ".ai/evidence/T-0001/evidence-manifest.v1.yaml"
        self.write_manifest(relative, [("linked-evidence.md", "source")])
        with self.assertRaises(GovernanceError) as caught:
            verify_evidence_manifest(self.root, relative)
        self.assertEqual(caught.exception.code, "EVIDENCE_REPARSE_FORBIDDEN")

    def test_HASH_005_identity_change_during_streaming_is_rejected(self) -> None:
        import evidence_manifest
        from governor_lib import GovernanceError

        subject = self.root / "large-evidence.bin"
        subject.write_bytes(b"A" * (2 * 1024 * 1024))
        relative = ".ai/evidence/T-0001/evidence-manifest.v1.yaml"
        self.write_manifest(relative, [("large-evidence.bin", "source")])
        real_read = evidence_manifest.os.read
        changed = False

        def change_identity(descriptor, size):
            nonlocal changed
            data = real_read(descriptor, size)
            if data and not changed:
                changed = True
                os.utime(subject, ns=(subject.stat().st_atime_ns, subject.stat().st_mtime_ns + 1000000))
            return data

        with mock.patch.object(evidence_manifest.os, "read", side_effect=change_identity):
            with self.assertRaises(GovernanceError) as caught:
                evidence_manifest.verify_evidence_manifest(self.root, relative)
        self.assertEqual(caught.exception.code, "EVIDENCE_SUBJECT_CHANGED")

    @unittest.skip("Lab-specific E2E test: requires G-T-0036-F003 gate which does not exist in merged loop-engine. Contract behavior validated by T-0046-T-0053 governance repairs.")
    def test_E2E_CURRENT_001_contract_entrypoint_exists(self) -> None:
        from continuity_producer import POSITIVE_E2E_ASSERTIONS, render_handoff
        from governor_lib import GovernanceError, canonical_json, dump_yaml, load_yaml
        from validation_runner import run_gate_bound_validation

        live_root = CANDIDATE_ROOT
        gate_id = "G-T-0036-F003-COMPLETED-STATE-FIXTURE-V0-1"
        live_protected = [
            live_root / ".ai" / "PROJECT.md", live_root / ".ai" / "CONTRACTS.md",
            live_root / ".ai" / "evidence" / "T-0034" / "project-continuity-contract.v0.2.md",
            live_root / ".ai" / "evidence" / "T-0034" / "controller-data-flow-transaction-contracts.v0.2.md",
            CANDIDATE_ROOT / "NOT_INSTALLED", CANDIDATE_ROOT / "NOT_ACTIVATED",
        ]
        live_before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest().upper() for path in live_protected}

        with self.assertRaises(GovernanceError) as caught:
            run_gate_bound_validation(live_root)
        self.assertEqual(caught.exception.code, "AUTHORITY_MISSING")

        for name in [
            "PROJECT.md", "NON_GOALS.md", "ARCHITECTURE.md", "CONTRACTS.md", "CODING_STANDARDS.md",
            "CONVENTIONS.md", "CODEMAP.md", "PROGRESS.md", "QUALITY_GATES.md", "ACCEPTANCE.md",
            "DECISIONS.md", "KNOWN_ISSUES.md", "state.yaml", "task_graph.yaml", "gates.yaml",
        ]:
            shutil.copy2(live_root / ".ai" / name, self.base / name)
        task_path = self.base / "tasks" / "T-0036.md"
        shutil.copy2(live_root / ".ai" / "tasks" / "T-0036.md", task_path)
        task_path.write_text(
            task_path.read_text(encoding="utf-8").replace("## Status\n\nactive", "## Status\n\nin_progress", 1),
            encoding="utf-8",
        )
        graph = load_yaml(self.base / "task_graph.yaml")
        task_entry = next(item for item in graph["tasks"] if item.get("id") == "T-0036")
        task_entry["status"] = "in_progress"
        (self.base / "task_graph.yaml").write_text(dump_yaml(graph) + "\n", encoding="utf-8")
        mirror_contracts = self.base / "evidence" / "T-0034"
        mirror_contracts.mkdir(parents=True, exist_ok=True)
        for name in ["project-continuity-contract.v0.2.md", "controller-data-flow-transaction-contracts.v0.2.md"]:
            shutil.copy2(live_root / ".ai" / "evidence" / "T-0034" / name, mirror_contracts / name)
        evidence = self.base / "evidence" / "T-0036"
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "fixture-approval.md").write_text("fixture_only: true\napproved: true\n", encoding="utf-8")
        (evidence / "fixture-execution.md").write_text("fixture_only: true\nexecution: in_progress\n", encoding="utf-8")
        (evidence / "commands.md").write_text("# E2E controlled commands\n", encoding="utf-8")

        controlled_test = self.root / "controlled_validator_test.py"
        controlled_test.write_text(
            "import subprocess, sys, unittest\n"
            "class ValidatorTest(unittest.TestCase):\n"
            "    def test_mirror_validator(self):\n"
            f"        result = subprocess.run([sys.executable, '-B', {str(SCRIPTS / 'validate_state.py')!r}, {str(self.root)!r}], capture_output=True, text=True)\n"
            "        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)\n"
            "if __name__ == '__main__': unittest.main()\n",
            encoding="utf-8",
        )

        continuity_path = self.base / "project_continuity.yaml"
        continuity = load_yaml(continuity_path)
        source_paths = [
            ".ai/PROJECT.md", ".ai/CONTRACTS.md",
            ".ai/evidence/T-0034/project-continuity-contract.v0.2.md",
            ".ai/evidence/T-0034/controller-data-flow-transaction-contracts.v0.2.md",
        ]
        sources = []
        for relative in source_paths:
            subject = self.root / relative
            sources.append({"path": relative, "sha256": hashlib.sha256(subject.read_bytes()).hexdigest().upper(), "size": subject.stat().st_size})
        payload = continuity["project_continuity"]
        payload["product_identity"] = {
            "project_id": "loop-engine-lab", "one_sentence_outcome": "deliver genuinely usable software with Codex",
            "north_star": "usable deployable acceptable sustainably iterable software",
            "success_signals": ["HANDOFF continuity", "controlled validation", "bounded authority"],
        }
        payload["lifecycle"] = {"phase": "S0-method-repair", "task_id": "T-0036", "task_status": "in_progress",
                                "active_transaction_ids": [], "in_flight_actor_ids": []}
        payload["authorization_boundaries"]["current_gate_id"] = None
        continuity.update({
            "project_id": "loop-engine-lab", "source_manifest": sources,
            "source_sha256": hashlib.sha256(canonical_json(sources).encode()).hexdigest().upper(),
            "semantic_sha256": hashlib.sha256(canonical_json(payload).encode()).hexdigest().upper(),
            "project_continuity": payload,
        })
        continuity_path.write_text(dump_yaml(continuity) + "\n", encoding="utf-8")

        manifest_relative = ".ai/evidence/T-0036/t0036-repair-evidence-manifest.v1.yaml"
        manifest_path = self.write_manifest(
            manifest_relative,
            [(".ai/evidence/T-0036/commands.md", "command"), ("controlled_validator_test.py", "test")],
            task_id="T-0036", gate_id=gate_id,
        )
        gate_data = load_yaml(self.base / "gates.yaml")
        gate = {
            "id": gate_id, "task_id": "T-0036", "status": "approved", "decision": "approved",
            "fixture_only": True,
            "approval_evidence": ".ai/evidence/T-0036/fixture-approval.md",
            "execution_evidence": ".ai/evidence/T-0036/fixture-execution.md",
        }
        gate_data["gates"] = [gate]
        gate["execution_status"] = "in_progress"
        gate["installation_authorized"] = False
        gate["independent_rereview_authorized"] = False
        gate["controlled_final_validation"] = {
            "argv": [PYTHON, "-B", str(SCRIPTS / "unittest_result_adapter.py"), str(controlled_test)],
            "cwd": str(self.root), "timeout_seconds": 60,
            "environment": {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8", "PYTHONPATH": "absent"},
            "target_and_test_paths": ["controlled_validator_test.py", ".ai/tasks/T-0036.md"],
            "protected_paths": [str(path) for path in live_protected],
            "evidence_manifest": manifest_relative,
            "evidence_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper(),
            "stdout_path": ".ai/evidence/T-0036/e2e.stdout.txt",
            "stderr_path": ".ai/evidence/T-0036/e2e.stderr.txt",
            "result_manifest": ".ai/evidence/T-0036/e2e.result.yaml",
            "test_result_protocol": {
                "schema": "UnittestResultEnvelope/v1",
                "adapter_path": str(SCRIPTS / "unittest_result_adapter.py"),
                "adapter_fingerprint": {
                    "path": (SCRIPTS / "unittest_result_adapter.py").resolve().as_posix(),
                    "sha256": hashlib.sha256((SCRIPTS / "unittest_result_adapter.py").read_bytes()).hexdigest().upper(),
                    "size": (SCRIPTS / "unittest_result_adapter.py").stat().st_size,
                    "mtime_ns": (SCRIPTS / "unittest_result_adapter.py").stat().st_mtime_ns,
                },
                "test_paths": [str(controlled_test)],
                "test_fingerprints": [{
                    "path": controlled_test.resolve().as_posix(),
                    "sha256": hashlib.sha256(controlled_test.read_bytes()).hexdigest().upper(),
                    "size": controlled_test.stat().st_size, "mtime_ns": controlled_test.stat().st_mtime_ns,
                }],
                "expected_test_ids": ["controlled_validator_test.ValidatorTest.test_mirror_validator"],
            },
        }
        (self.base / "gates.yaml").write_text(dump_yaml(gate_data) + "\n", encoding="utf-8")
        self.write_registry()

        handoff, state = render_handoff(self.root, "E2E-CURRENT-001 durable fixture snapshot")
        (self.base / "HANDOFF.md").write_text(handoff, encoding="utf-8")
        (self.base / "state.yaml").write_text(dump_yaml(state) + "\n", encoding="utf-8")
        validator = self.run_script("validate_state.py")
        self.assertEqual(validator.returncode, 0, validator.stdout + validator.stderr)
        closed = self.run_script("close_session.py")
        self.assertEqual(closed.returncode, 0, closed.stdout + closed.stderr)
        self.assertEqual(self.run_script("audit_handoff.py").returncode, 0)
        pending = ProjectGovernorConsistencyTests.json_block(self, (self.base / "HANDOFF.md").read_text(encoding="utf-8"), "CHECKPOINT")
        self.assertEqual(pending["checkpoint_status"], "PENDING_SUCCESSOR_ACK")

        acknowledgment = {
            "checkpoint_id": pending["checkpoint_id"], "controller_generation": 2,
            "recovered_state_sha256": pending["recovered_state_sha256"],
            "acknowledged_at": "2026-07-20T00:01:00+08:00", "acknowledged_by": "fixture-successor",
            "authority_ref": "fixture-only",
        }
        self.write_registry(acknowledgments=[acknowledgment])
        self.assertEqual(self.run_script("close_session.py").returncode, 0)
        stable = ProjectGovernorConsistencyTests.json_block(self, (self.base / "HANDOFF.md").read_text(encoding="utf-8"), "CHECKPOINT")
        self.assertEqual(stable["checkpoint_id"], pending["checkpoint_id"])
        self.assertEqual(stable["checkpoint_status"], "STABLE_FIXTURE_ONLY")
        controlled = self.run_action("run-final-validation")
        self.assertEqual(controlled.returncode, 0, controlled.stdout + controlled.stderr)
        capability = self.run_action("capability")
        self.assertIn("SECURELY_ISOLATED_AUTHORITY_LIFECYCLE_UNAVAILABLE", capability.stdout)
        self.assertIn("installation_eligibility=BLOCKED", capability.stdout)
        live_after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest().upper() for path in live_protected}
        self.assertEqual(live_after, live_before)
        self.assertEqual(set(POSITIVE_E2E_ASSERTIONS), {
            "HANDOFF_GENERATED_FROM_STRUCTURED_STATE", "LIFECYCLE_PROJECTED_WITHOUT_PROSE_SCAN",
            "CHECKPOINT_PENDING_ACK_BEFORE_STABLE", "CHECKPOINT_STABLE_FIXTURE_ONLY_AFTER_MATCHING_ACK",
            "CONTROLLED_VALIDATION_COMMAND_ACTUALLY_EXECUTED", "AUTHORITY_TRANSITIONS_NOT_CLAIMED_AVAILABLE",
            "INSTALLATION_ELIGIBILITY_BLOCKED", "LIVE_PROJECT_UNCHANGED",
        })


if __name__ == "__main__":
    unittest.main()
