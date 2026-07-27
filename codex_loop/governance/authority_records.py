from __future__ import annotations

import copy
import hashlib

from codex_loop.governance.governor_lib import GovernanceError, canonical_json


CAPABILITY_RESULT = "SECURELY_ISOLATED_AUTHORITY_LIFECYCLE_UNAVAILABLE"
AUTHORITY_FIELDS = {
    "schema", "event_id", "actor_id", "host_message_id", "host_turn_id",
    "exact_user_text", "predecessor_event_id", "occurred_at", "task_id",
    "gate_id", "requested_transition", "lifecycle_revision", "content_sha256",
}
ACTION_MODES = {"read_only", "prompt_generation_only", "create_pending_gate", "approve_pending_gate", "execute_approved_gate"}


def production_capability() -> dict:
    return {
        "authority_lifecycle": CAPABILITY_RESULT,
        "production_authority_lifecycle_available": False,
        "installation_eligibility": "BLOCKED",
        "trusted_host_adapter_present": False,
    }


def require_production_authority() -> None:
    raise GovernanceError(
        "USER_DECISION_REQUIRED",
        "Trusted Codex host message/turn identity is unavailable in the isolated candidate",
    )


def validate_action_mode(mode: str, *, gate_status: str | None = None, explicit_execution_request: bool = False) -> list[str]:
    if mode not in ACTION_MODES:
        return [f"Unknown action mode: {mode}"]
    errors = []
    if mode == "approve_pending_gate" and gate_status != "pending":
        errors.append("approve_pending_gate requires a pending gate")
    if mode == "execute_approved_gate":
        if gate_status != "approved":
            errors.append("execute_approved_gate requires an approved gate")
        if not explicit_execution_request:
            errors.append("execute_approved_gate requires an explicit execution request")
    return errors


def validate_fixture_event(event: dict, attestation: dict) -> dict:
    if set(event) != AUTHORITY_FIELDS or event.get("schema") != "AuthorityEvent/v2":
        raise GovernanceError("AUTHORITY_EVIDENCE_MISMATCH", "AuthorityEvent/v2 fields are invalid")
    if attestation != {"fixture_only": True, "adapter_id": "synthetic-test-adapter/v1"}:
        raise GovernanceError("AUTHORITY_IDENTITY_MISMATCH", "Only the labelled synthetic fixture adapter is accepted")
    semantic = {key: value for key, value in event.items() if key != "content_sha256"}
    expected = hashlib.sha256(canonical_json(semantic).encode("utf-8")).hexdigest().upper()
    if event["content_sha256"] != expected:
        raise GovernanceError("AUTHORITY_EVIDENCE_MISMATCH", "Authority event content hash mismatch")
    required_text = ["event_id", "actor_id", "host_message_id", "host_turn_id", "exact_user_text", "task_id", "gate_id"]
    if any(not isinstance(event.get(field), str) or not event[field] for field in required_text):
        raise GovernanceError("AUTHORITY_IDENTITY_MISMATCH", "Authority identity fields must be non-empty strings")
    if not isinstance(event.get("lifecycle_revision"), int) or event["lifecycle_revision"] < 0:
        raise GovernanceError("AUTHORITY_EVIDENCE_MISMATCH", "Lifecycle revision is invalid")
    return copy.deepcopy(event)


def advance_fixture_lifecycle(snapshot: dict, event: dict, transition: str) -> dict:
    if snapshot.get("fixture_only") is not True:
        raise GovernanceError("USER_DECISION_REQUIRED", "Fixture lifecycle cannot establish production authority")
    if event["requested_transition"] != transition:
        raise GovernanceError("AUTHORITY_IDENTITY_MISMATCH", "Requested transition mismatch")
    if event["lifecycle_revision"] != snapshot.get("lifecycle_revision"):
        raise GovernanceError("STALE_AUTHORITY_EVENT", "Lifecycle compare-and-swap revision mismatch")
    if event["predecessor_event_id"] != snapshot.get("last_event_id"):
        raise GovernanceError("STALE_AUTHORITY_EVENT", "Authority predecessor mismatch")
    if event["event_id"] in snapshot.get("consumed_event_ids", []):
        raise GovernanceError("AUTHORITY_REPLAY", "Authority event was already consumed")
    previous_turn = snapshot.get("last_host_turn_id")
    if previous_turn is not None and event["host_turn_id"] <= previous_turn:
        raise GovernanceError("AUTHORITY_REPLAY", "Authority transitions require a distinct later host turn")
    result = copy.deepcopy(snapshot)
    result["lifecycle_revision"] += 1
    result["last_event_id"] = event["event_id"]
    result["last_host_turn_id"] = event["host_turn_id"]
    result.setdefault("consumed_event_ids", []).append(event["event_id"])
    result["state"] = transition
    return result
