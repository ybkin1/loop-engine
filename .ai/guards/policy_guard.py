import argparse
import json
from pathlib import Path

import yaml


DECISIONS = {
    "allow",
    "deny",
    "require_user_gate",
    "require_repair",
    "require_checker",
    "allow_decision_recording_only",
}
LAB_LOCAL_PREFIXES = (
    ".ai/checkers/",
    ".ai/guards/",
    ".ai/policies/",
    ".ai/schemas/",
    ".ai/tests/",
)


def _policy_path():
    return Path(__file__).resolve().parents[1] / "policies" / "tool-entry-restrictions.yaml"


def _load_policy():
    with _policy_path().open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _normalize_path(path):
    normalized = str(path).replace("\\", "/")
    if normalized.startswith("./"):
        return normalized[2:]
    return normalized


def _policy_matches(action_family):
    matches = []
    for policy in _load_policy().get("policies", []):
        if policy.get("action_family") == action_family:
            matches.append(policy)
    return matches


def _decision(decision, action_family, target_path, reason, policies):
    if decision not in DECISIONS:
        decision = "require_repair"
        reason = "unknown guard decision enum"
    return {
        "decision": decision,
        "action_family": action_family,
        "target_path": target_path,
        "reason": reason,
        "required_gate_classes": [item["required_gate_class"] for item in policies],
        "matched_policy_ids": [item["id"] for item in policies],
    }


def decide_action(action_family, target_path, gate_status, allowed_action_classes=None):
    allowed_action_classes = set(allowed_action_classes or [])
    target_path = _normalize_path(target_path)
    policies = _policy_matches(action_family)

    if action_family == "gate_decision_recording" and gate_status == "pending":
        return _decision(
            "allow_decision_recording_only",
            action_family,
            target_path,
            "pending gate allows exact user decision recording only",
            [],
        )

    if policies or target_path == "AGENTS.md":
        if target_path == "AGENTS.md" and not policies:
            policies = [{"id": "agents-md-target-requires-rule-change-gate", "required_gate_class": "agents_md_change"}]
        return _decision("require_user_gate", action_family, target_path, "sensitive action requires a separate gate", policies)

    is_lab_local_path = any(target_path.startswith(prefix) for prefix in LAB_LOCAL_PREFIXES)
    if (
        gate_status == "approved"
        and action_family in allowed_action_classes
        and action_family == "lab_local_prototype_implementation"
        and is_lab_local_path
    ):
        return _decision("allow", action_family, target_path, "approved lab-local prototype scope", [])

    return _decision("require_user_gate", action_family, target_path, "action is outside approved prototype scope", [])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-family", required=True)
    parser.add_argument("--target-path", required=True)
    parser.add_argument("--gate-status", default="none")
    parser.add_argument("--allowed-action-class", action="append", default=[])
    args = parser.parse_args()
    decision = decide_action(
        args.action_family,
        args.target_path,
        args.gate_status,
        allowed_action_classes=args.allowed_action_class,
    )
    print(json.dumps(decision, indent=2))
    return 0 if decision["decision"].startswith("allow") else 1


if __name__ == "__main__":
    raise SystemExit(main())
