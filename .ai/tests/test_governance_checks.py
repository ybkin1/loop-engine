import json
import sys
import unittest
from pathlib import Path

import jsonschema
import yaml


AI_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = AI_ROOT.parent
SAMPLES = AI_ROOT / "tests" / "samples"
sys.path.insert(0, str(AI_ROOT / "checkers"))
sys.path.insert(0, str(AI_ROOT / "guards"))

from validate_gate_register import validate_gate_register
from run_governance_checks import run_checks
from policy_guard import decide_action


def load_yaml(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


class GovernanceCheckerTests(unittest.TestCase):
    def test_approved_gate_register_passes_and_matches_result_schema(self):
        result = validate_gate_register(
            SAMPLES / "gates" / "approved-gate-register.yaml",
            project_root=PROJECT_ROOT,
        )

        self.assertTrue(result["passed"], json.dumps(result, indent=2))
        schema = load_yaml(AI_ROOT / "schemas" / "checker-result.schema.yaml")
        jsonschema.validate(result, schema)

    def test_pending_gate_fails_closed(self):
        result = validate_gate_register(
            SAMPLES / "gates" / "pending-gate-register.yaml",
            project_root=PROJECT_ROOT,
        )

        self.assertFalse(result["passed"])
        self.assertIn("pending-gate-check", result["failed_check_ids"])

    def test_approved_gate_requires_user_approval_evidence(self):
        result = validate_gate_register(
            SAMPLES / "gates" / "missing-approval-evidence.yaml",
            project_root=PROJECT_ROOT,
        )

        self.assertFalse(result["passed"])
        self.assertIn("approval-evidence-check", result["failed_check_ids"])

    def test_high_risk_flags_require_separate_gate(self):
        result = run_checks(
            gates_path=SAMPLES / "gates" / "high-risk-without-separate-gate.yaml",
            project_root=PROJECT_ROOT,
        )

        self.assertFalse(result["passed"])
        self.assertIn("high-risk-gate-separation-check", result["failed_check_ids"])


class PolicyGuardTests(unittest.TestCase):
    def test_lab_local_prototype_path_is_allowed_with_approved_gate_scope(self):
        decision = decide_action(
            action_family="lab_local_prototype_implementation",
            target_path=".ai/checkers/run_governance_checks.py",
            gate_status="approved",
            allowed_action_classes=["lab_local_prototype_implementation"],
        )

        self.assertEqual("allow", decision["decision"])

    def test_pending_gate_allows_decision_recording_only(self):
        decision = decide_action(
            action_family="gate_decision_recording",
            target_path=".ai/gates.yaml",
            gate_status="pending",
            allowed_action_classes=[],
        )

        self.assertEqual("allow_decision_recording_only", decision["decision"])

    def test_sensitive_actions_require_separate_user_gate(self):
        for action_family in ["deployment", "agents_md_change", "runtime_tool_enablement"]:
            with self.subTest(action_family=action_family):
                decision = decide_action(
                    action_family=action_family,
                    target_path="AGENTS.md",
                    gate_status="approved",
                    allowed_action_classes=["lab_local_prototype_implementation"],
                )
                self.assertEqual("require_user_gate", decision["decision"])

    def test_guard_decision_matches_schema(self):
        decision = decide_action(
            action_family="database",
            target_path=".ai/tests/samples/example.db",
            gate_status="approved",
            allowed_action_classes=["lab_local_prototype_implementation"],
        )

        schema = load_yaml(AI_ROOT / "guards" / "guard_decision.schema.yaml")
        jsonschema.validate(decision, schema)


if __name__ == "__main__":
    unittest.main()
