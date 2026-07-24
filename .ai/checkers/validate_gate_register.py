import argparse
import json
from pathlib import Path

import yaml


HIGH_RISK_FLAGS = {
    "deployment",
    "rollback",
    "database",
    "permission",
    "secret",
    "payment",
    "production_data",
    "migration",
    "runtime_behavior",
}
VALID_STATUSES = {"pending", "approved", "rejected", "blocked"}
APPROVAL_FIELDS = {
    "approval_actor": "user",
    "approval_source": "explicit_user_message",
}


def _resolve(project_root, candidate):
    path = Path(str(candidate))
    if path.is_absolute():
        return path
    return Path(project_root) / path


def _finding(check_id, message, gate_id=None):
    if gate_id:
        message = f"{gate_id}: {message}"
    return {"check_id": check_id, "severity": "error", "message": message}


def _warning(check_id, message, gate_id=None):
    if gate_id:
        message = f"{gate_id}: {message}"
    return {"check_id": check_id, "severity": "warning", "message": message}


def _result(checker_id, findings, metadata):
    # Only errors block; warnings are reported but do not cause failure.
    errors = [item for item in findings if item.get("severity") == "error"]
    failed_ids = sorted({item["check_id"] for item in errors})
    return {
        "checker_id": checker_id,
        "passed": not errors,
        "status": "passed" if not errors else "failed",
        "failed_check_ids": failed_ids,
        "findings": findings,
        "metadata": metadata,
    }


def _approved_gate_has_separate_high_risk_gate(gate, flag):
    gate_type = str(gate.get("gate_type", "")).replace("_", "-")
    return flag.replace("_", "-") in gate_type


def validate_gate_register(gates_path, project_root=None):
    gates_path = Path(gates_path)
    project_root = Path(project_root or gates_path.parent)
    findings = []

    with gates_path.open("r", encoding="utf-8") as handle:
        register = yaml.safe_load(handle) or {}

    gates = register.get("gates")
    if not isinstance(gates, list):
        findings.append(_finding("gate-register-schema-check", "`gates` must be a list"))
        gates = []

    for gate in gates:
        gate_id = gate.get("id", "<missing-id>") if isinstance(gate, dict) else "<invalid>"
        if not isinstance(gate, dict):
            findings.append(_finding("gate-register-schema-check", "gate must be a mapping"))
            continue

        for field in ["id", "task_id", "gate_type", "status", "decision", "evidence"]:
            if not gate.get(field):
                findings.append(_finding("gate-register-schema-check", f"missing `{field}`", gate_id))

        status = gate.get("status")
        if status not in VALID_STATUSES:
            findings.append(_finding("gate-register-schema-check", f"invalid status `{status}`", gate_id))
        if status == "pending":
            findings.append(_finding("pending-gate-check", "pending gate blocks continuation", gate_id))

        for artifact_field in ["evidence", "decision_packet", "startup_validation"]:
            artifact = gate.get(artifact_field)
            if artifact and not _resolve(project_root, artifact).exists():
                findings.append(_finding("required-artifact-presence-check", f"missing `{artifact_field}` artifact", gate_id))

        if status == "approved":
            if not gate.get("approval_text") or not gate.get("approval_evidence"):
                findings.append(_warning("approval-evidence-check", "approved gate lacks approval text or evidence", gate_id))
            for field, expected in APPROVAL_FIELDS.items():
                if gate.get(field) != expected:
                    findings.append(_warning("approval-evidence-check", f"`{field}` should be `{expected}`", gate_id))
            approval_evidence = gate.get("approval_evidence")
            if approval_evidence and not _resolve(project_root, approval_evidence).exists():
                findings.append(_warning("approval-evidence-check", "approval evidence file is missing", gate_id))

        high_risk_flags = gate.get("high_risk_flags") or {}
        for flag in HIGH_RISK_FLAGS:
            if high_risk_flags.get(flag) is True and not _approved_gate_has_separate_high_risk_gate(gate, flag):
                findings.append(_warning("high-risk-gate-separation-check", f"`{flag}` is true; verify a separate gate or explicit scope covers this risk", gate_id))

    return _result(
        "validate_gate_register",
        findings,
        {"gates_path": str(gates_path), "gate_count": len(gates)},
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("gates_path")
    parser.add_argument("--project-root", default=None)
    args = parser.parse_args()
    result = validate_gate_register(args.gates_path, args.project_root)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
