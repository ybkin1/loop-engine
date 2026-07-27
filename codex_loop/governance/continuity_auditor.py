from __future__ import annotations

import hashlib
from pathlib import Path

from codex_loop.governance.evidence_manifest import verify_evidence_manifest
from codex_loop.governance.governor_lib import GovernanceError, canonical_json, current_task_id, gates, load_yaml, parse_json_block, safe_project_path, task_status
from codex_loop.governance.transaction_registry import load_transaction_registry


def _sha(value) -> str:
    payload = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _continuity_projection(root: Path) -> tuple[dict, dict]:
    path = safe_project_path(root, ".ai/project_continuity.yaml")
    if not path.is_file():
        raise GovernanceError("PROJECT_CONTINUITY_MISSING", "ProjectContinuity/v1 is required")
    raw = path.read_bytes()
    data = load_yaml(path)
    required = {
        "schema", "contract_id", "requirements_revision", "project_id", "source_manifest",
        "source_sha256", "semantic_sha256", "created_at", "created_by", "authority_ref", "project_continuity",
    }
    if not isinstance(data, dict) or set(data) != required or data.get("schema") != "ProjectContinuity/v1":
        raise GovernanceError("PROJECT_CONTINUITY_INVALID", "Independent continuity schema check failed")
    sources = data["source_manifest"]
    if not isinstance(sources, list) or any(set(item) != {"path", "sha256", "size"} for item in sources):
        raise GovernanceError("PROJECT_CONTINUITY_INVALID", "Independent source-manifest check failed")
    for item in sources:
        subject = safe_project_path(root, item["path"])
        if not subject.is_file() or subject.stat().st_size != item["size"] or _sha(subject.read_bytes()) != item["sha256"]:
            raise GovernanceError("PROJECT_CONTINUITY_SOURCE_DRIFT", f"Continuity source drift: {item['path']}")
    payload = data["project_continuity"]
    decisions = payload.get("protected_decisions") if isinstance(payload, dict) else None
    required_ids = {"USER_AUTHORITY", "CODEX_DELIVERY_RESPONSIBILITY", "EVIDENCE_ONLY_BOUNDARY", "MEANS_END_BOUNDARY"}
    if not isinstance(decisions, list) or {item.get("decision_id") for item in decisions} != required_ids:
        raise GovernanceError("PROJECT_CONTINUITY_INVALID", "Independent protected-decision check failed")
    hash_payload = {k: v for k, v in payload.items() if k != "lifecycle"}
    if data["source_sha256"] != _sha(sources) or data["semantic_sha256"] != _sha(hash_payload):
        raise GovernanceError("PROJECT_CONTINUITY_HASH_MISMATCH", "Independent continuity hash check failed")
    hashes = {"source_sha256": data["source_sha256"], "semantic_sha256": data["semantic_sha256"], "file_sha256": _sha(raw)}
    projection = {
        "schema": "ProjectContinuityProjection/v1", "project_id": data["project_id"],
        "user_origin": payload["user_origin"], "product_identity": payload["product_identity"],
        "protected_decisions": decisions, "authorization_boundaries": payload["authorization_boundaries"],
        "source_sha256": hashes["source_sha256"], "semantic_sha256": hashes["semantic_sha256"],
        "persisted_file_sha256": hashes["file_sha256"],
    }
    return projection, hashes


def _approved_gate(root: Path, task_id: str | None) -> dict | None:
    """Find the approved gate for a task, matching all valid execution states.

    v3.5 fix: Previously only matched execution_status in {approved_not_started, in_progress}.
    Now also matches 'completed' and legacy gates with no execution_status,
    aligning with governor_lib and gate_guard lifecycle semantics.
    """
    matches = [item for item in gates(root) if item.get("task_id") == task_id and item.get("status") == "approved"]
    # Prefer in_progress/approved_not_started, fall back to completed/legacy
    active = [m for m in matches if m.get("execution_status") in {"approved_not_started", "in_progress"}]
    if active:
        return active[-1]
    completed_or_legacy = [m for m in matches if m.get("execution_status") == "completed" or not m.get("execution_status")]
    if completed_or_legacy:
        return completed_or_legacy[-1]
    return matches[-1] if matches else None


def _manifest_path(root: Path, task_id: str) -> str:
    repair = f".ai/evidence/{task_id}/t0036-repair-evidence-manifest.v1.yaml"
    return repair if safe_project_path(root, repair).exists() else f".ai/evidence/{task_id}/evidence-manifest.v1.yaml"


def _expected_lifecycle(gate: dict | None, evidence_ok: bool, evidence_error: str | None) -> dict:
    names = (
        "independent_rereview_authorized", "installation_authorized", "activation_authorized",
        "runtime_tool_enablement_authorized", "downstream_task_creation_authorized", "real_project_entry_authorized",
    )
    flags = {name: gate.get(name, False) if gate else False for name in names}
    unverified = [] if evidence_ok else ["EVIDENCE_MANIFEST_REQUIRED"]
    if not flags["independent_rereview_authorized"]:
        unverified.append("FRESH_INDEPENDENT_REREVIEW_NOT_PERFORMED")
    if evidence_error and evidence_error not in unverified:
        unverified.append(evidence_error)
    return {
        "schema": "ProjectLifecycleProjection/v1",
        "verified": ["STRUCTURED_STATE_HASHES_VERIFIED"] if evidence_ok else [],
        "unverified": unverified,
        "not_performed": ["USER_ACCEPTANCE_NOT_PERFORMED", "PRODUCTION_AUTHORITY_LIFECYCLE_UNAVAILABLE"],
        "not_authorized": [name.upper() for name, value in flags.items() if value is not True],
        "installation_eligibility": "BLOCKED",
    }


def _expected_checkpoint(registry: dict | None, continuity: dict, evidence: dict | None, task_hash: str, authority_hash: str) -> dict:
    if registry is None:
        return {"schema": "Checkpoint/v1.0", "checkpoint_status": "NOT_ESTABLISHED", "blockers": ["TRANSACTION_REGISTRY_MISSING"]}
    data = registry["data"]
    blockers = [f"NONEMPTY_{field.upper()}" for field in (
        "active_transactions", "in_flight_actors", "unconsumed_deltas", "partial_writes") if data[field]]
    fence = data["generation_fence"]
    generation = data["controller_generation"]
    if fence["successor_generation"] != generation or fence["fenced_generation"] >= generation:
        blockers.append("GENERATION_FENCE_MISMATCH")
    if evidence is None:
        blockers.append("EVIDENCE_MANIFEST_REQUIRED")
    if blockers:
        return {"schema": "Checkpoint/v1.0", "checkpoint_status": "NOT_ESTABLISHED", "blockers": blockers}
    recovered_payload = {
        "project_continuity_source_sha256": continuity["source_sha256"],
        "project_continuity_semantic_sha256": continuity["semantic_sha256"],
        "project_continuity_file_sha256": continuity["file_sha256"],
        "transaction_source_sha256": registry["source_sha256"],
        "transaction_checkpoint_semantic_sha256": registry["checkpoint_semantic_sha256"],
        "transaction_file_identity_excluding_ack": registry["checkpoint_semantic_sha256"],
        "evidence_manifest_sha256": evidence["manifest_file_sha256"],
        "evidence_semantic_sha256": evidence["semantic_sha256"],
        "evidence_file_count": evidence["file_count"], "evidence_total_bytes": evidence["total_bytes"],
        "task_scope_hash": task_hash, "authority_hash": authority_hash,
        "controller_generation": generation, "requirements_revision": data["requirements_revision"],
    }
    recovered_hash = _sha(recovered_payload)
    checkpoint_id = f"CP-{_sha({'recovered_state_sha256': recovered_hash, 'generation': generation})[:24]}"
    acknowledged = any(
        item["checkpoint_id"] == checkpoint_id and item["controller_generation"] == generation
        and item["recovered_state_sha256"] == recovered_hash
        for item in data["checkpoint_acknowledgments"]
    )
    status = "STABLE_FIXTURE_ONLY" if acknowledged and data["fixture_only"] else "STABLE" if acknowledged else "PENDING_SUCCESSOR_ACK"
    return {
        "schema": "Checkpoint/v1.0", "contract_id": "PCC-2026-07-16-R1",
        "checkpoint_id": checkpoint_id, "checkpoint_status": status,
        "controller_generation": generation, "requirements_revision": data["requirements_revision"],
        "recovered_state_sha256": recovered_hash, "project_continuity_hashes": continuity,
        "transaction_registry_hashes": {key: registry[key] for key in (
            "source_sha256", "semantic_sha256", "checkpoint_semantic_sha256", "file_sha256")},
        "evidence_manifest_hashes": evidence, "task_scope_hash": task_hash, "authority_hash": authority_hash,
        "blockers": [], "fixture_only": data["fixture_only"],
    }


def audit_handoff_model(root: Path, text: str) -> list[str]:
    root = root.resolve()
    errors = []
    try:
        orientation, continuity_hashes = _continuity_projection(root)
        actual_orientation = parse_json_block(text, "PROJECT-CONTINUITY")
        actual_action = parse_json_block(text, "NEXT-ACTION")
        actual_lifecycle = parse_json_block(text, "LIFECYCLE")
        actual_checkpoint = parse_json_block(text, "CHECKPOINT")
    except GovernanceError as exc:
        return [f"{exc.code}: {exc}"]
    task_id = current_task_id(root)
    if task_id is None:
        # An empty active-task slot is a valid blocked governance state, not a
        # path to `.ai/tasks/None.md`. Report it structurally and stop the
        # task-specific projection before attempting task file reads.
        errors.append("NO_ACTIVE_TASK: state.current_task_id is null")
        return errors
    status = task_status(root, task_id)
    state = load_yaml(root / ".ai" / "state.yaml")
    gate = _approved_gate(root, task_id)
    current_gate = state.get("current_gate_id")
    current_gate = None if current_gate in (None, "", "null") else current_gate
    expected_action = {
        "schema": "ProjectGovernorNextAction/v2", "current_task_id": task_id,
        "current_task_status": status, "current_gate_id": current_gate,
        "approved_execution_gate_id": gate.get("id") if gate else None,
        "approved_execution_status": gate.get("execution_status") if gate else None,
        "lifecycle_revision": gate.get("lifecycle_revision", 0) if gate else 0,
        "next_action": "CONTINUE_APPROVED_EXECUTION" if status == "in_progress" else "USER_DECISION_REQUIRED",
    }
    evidence = None
    evidence_error = None
    try:
        evidence = verify_evidence_manifest(root, _manifest_path(root, task_id))
    except GovernanceError as exc:
        evidence_error = exc.code
    registry = None
    try:
        registry = load_transaction_registry(root)
    except GovernanceError as exc:
        if exc.code != "TRANSACTION_REGISTRY_MISSING":
            errors.append(f"{exc.code}: {exc}")
    task_path = root / ".ai" / "tasks" / f"{task_id}.md"
    expected_checkpoint = _expected_checkpoint(registry, continuity_hashes, evidence, _sha(task_path.read_bytes()), _sha(gate or {}))
    expected_lifecycle = _expected_lifecycle(gate, evidence is not None, evidence_error)
    for label, actual, expected in (
        ("project continuity", actual_orientation, orientation), ("next-action", actual_action, expected_action),
        ("lifecycle", actual_lifecycle, expected_lifecycle), ("checkpoint", actual_checkpoint, expected_checkpoint),
    ):
        errors.extend(f"HANDOFF {label} missing field: {field}" for field in sorted(set(expected) - set(actual)))
        errors.extend(f"HANDOFF {label} unknown field: {field}" for field in sorted(set(actual) - set(expected)))
        if actual != expected:
            errors.append(f"HANDOFF {label} contract mismatch with independently reconstructed state")
    current_section = _section(text, "## Current Task")
    if task_id and task_id not in current_section:
        errors.append(f"HANDOFF current task mismatch: expected {task_id}")
    prose_status = _prose_status(current_section)
    if status and prose_status != status:
        errors.append(f"HANDOFF task status mismatch: expected {status}, found {prose_status or 'missing'}")
    if expected_checkpoint["checkpoint_status"] != "STABLE" and "## Stable Checkpoint" in text:
        errors.append("HANDOFF claims production Stable Checkpoint without proof")
    return errors


def _section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    start += len(heading)
    end = text.find("\n## ", start)
    return text[start:] if end < 0 else text[start:end]


def _prose_status(section: str) -> str | None:
    marker = "Status: `"
    start = section.find(marker)
    if start < 0:
        return None
    start += len(marker)
    end = section.find("`", start)
    return section[start:end] if end >= 0 else None
