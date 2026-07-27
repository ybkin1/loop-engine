from __future__ import annotations

import hashlib
from pathlib import Path

from evidence_manifest import verify_evidence_manifest
from governor_lib import (
    GovernanceError, canonical_json, current_task_id, gates, load_yaml,
    now_precise, render_json_block, safe_project_path, task_status,
)
from transaction_registry import checkpoint_status, load_transaction_registry


POSITIVE_E2E_ASSERTIONS = (
    "HANDOFF_GENERATED_FROM_STRUCTURED_STATE",
    "LIFECYCLE_PROJECTED_WITHOUT_PROSE_SCAN",
    "CHECKPOINT_PENDING_ACK_BEFORE_STABLE",
    "CHECKPOINT_STABLE_FIXTURE_ONLY_AFTER_MATCHING_ACK",
    "CONTROLLED_VALIDATION_COMMAND_ACTUALLY_EXECUTED",
    "AUTHORITY_TRANSITIONS_NOT_CLAIMED_AVAILABLE",
    "INSTALLATION_ELIGIBILITY_BLOCKED",
    "LIVE_PROJECT_UNCHANGED",
)
PC_FIELDS = {
    "schema", "contract_id", "requirements_revision", "project_id", "source_manifest",
    "source_sha256", "semantic_sha256", "created_at", "created_by", "authority_ref",
    "project_continuity",
}
PAYLOAD_FIELDS = {
    "user_origin", "product_identity", "protected_decisions", "non_goals", "design_language",
    "engineering_invariants", "golden_references", "authorization_boundaries", "lifecycle",
    "evidence_index", "revision_lineage",
}
REQUIRED_DECISIONS = {
    "USER_AUTHORITY", "CODEX_DELIVERY_RESPONSIBILITY", "EVIDENCE_ONLY_BOUNDARY", "MEANS_END_BOUNDARY",
}


def _sha(value) -> str:
    payload = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _closed(value, fields: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise GovernanceError("PROJECT_CONTINUITY_INVALID", f"{label} fields are invalid")


def load_project_continuity(root: Path) -> dict:
    root = root.resolve()
    path = safe_project_path(root, ".ai/project_continuity.yaml")
    if not path.is_file():
        raise GovernanceError("PROJECT_CONTINUITY_MISSING", "ProjectContinuity/v1 is required")
    before = path.stat()
    if before.st_size > 2 * 1024 * 1024:
        raise GovernanceError("PROJECT_CONTINUITY_INVALID", "ProjectContinuity exceeds 2 MiB")
    raw = path.read_bytes()
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    ):
        raise GovernanceError("PROJECT_CONTINUITY_CHANGED", "ProjectContinuity changed while reading")
    data = load_yaml(path)
    _closed(data, PC_FIELDS, "ProjectContinuity/v1")
    if data["schema"] != "ProjectContinuity/v1" or data["contract_id"] != "PCC-2026-07-16-R1":
        raise GovernanceError("PROJECT_CONTINUITY_INVALID", "Project continuity contract identity mismatch")
    payload = data["project_continuity"]
    _closed(payload, PAYLOAD_FIELDS, "project_continuity")
    _closed(payload["user_origin"], {"audience", "capability_assumptions", "user_authorities"}, "user_origin")
    _closed(payload["product_identity"], {"project_id", "one_sentence_outcome", "north_star", "success_signals"}, "product_identity")
    _closed(payload["design_language"], {"terms", "forbidden_equivalences"}, "design_language")
    _closed(payload["engineering_invariants"], {"architecture", "technology", "interfaces", "coding_standards", "quality", "security"}, "engineering_invariants")
    _closed(payload["authorization_boundaries"], {"allowed_effects", "forbidden_effects", "current_gate_id"}, "authorization_boundaries")
    _closed(payload["lifecycle"], {"phase", "task_id", "task_status", "active_transaction_ids", "in_flight_actor_ids"}, "lifecycle")
    _closed(payload["evidence_index"], {"canonical", "additive", "superseded_not_deleted"}, "evidence_index")
    _closed(payload["revision_lineage"], {"parent_revision", "change_set_id", "impact_assessment_ref", "approval_ref"}, "revision_lineage")
    decisions = payload["protected_decisions"]
    if not isinstance(decisions, list) or any(
        not isinstance(item, dict) or set(item) != {"decision_id", "statement", "rationale_ref", "authority_ref", "change_policy"}
        for item in decisions
    ):
        raise GovernanceError("PROJECT_CONTINUITY_INVALID", "Protected decisions are invalid")
    if {item["decision_id"] for item in decisions} != REQUIRED_DECISIONS:
        raise GovernanceError("PROJECT_CONTINUITY_INVALID", "Required protected decision IDs are missing or unknown")
    sources = data["source_manifest"]
    if not isinstance(sources, list) or not sources or any(
        not isinstance(item, dict) or set(item) != {"path", "sha256", "size"} for item in sources
    ):
        raise GovernanceError("PROJECT_CONTINUITY_INVALID", "Source manifest is invalid")
    seen = set()
    for source in sources:
        folded = source["path"].casefold()
        if folded in seen:
            raise GovernanceError("PROJECT_CONTINUITY_INVALID", "Duplicate continuity source path")
        seen.add(folded)
        subject = safe_project_path(root, source["path"])
        if not subject.is_file() or subject.stat().st_size != source["size"] or _sha(subject.read_bytes()) != source["sha256"]:
            raise GovernanceError("PROJECT_CONTINUITY_SOURCE_DRIFT", f"Continuity source drift: {source['path']}")
    if data["source_sha256"] != _sha(sources):
        raise GovernanceError("PROJECT_CONTINUITY_HASH_MISMATCH", "Continuity source-manifest hash mismatch")
    hash_payload = {k: v for k, v in payload.items() if k != "lifecycle"}
    semantic_hash = _sha(hash_payload)
    # Legacy fixtures hashed the complete payload. Accept that historical
    # contract while keeping mismatch detection strict for both forms.
    legacy_semantic_hash = _sha(payload)
    if data["semantic_sha256"] not in {semantic_hash, legacy_semantic_hash}:
        raise GovernanceError("PROJECT_CONTINUITY_HASH_MISMATCH", "Continuity semantic hash mismatch")
    return {
        "data": data, "payload": payload, "source_sha256": data["source_sha256"],
        "semantic_sha256": data["semantic_sha256"], "file_sha256": _sha(raw),
    }


def _approved_execution_gate(root: Path, task_id: str | None) -> dict | None:
    """Find the approved gate for a task, matching all valid execution states.

    v3.5 fix: Previously only matched execution_status in {approved_not_started, in_progress}.
    Now also matches 'completed' and legacy gates with no execution_status,
    aligning with governor_lib and gate_guard lifecycle semantics.
    """
    matches = [gate for gate in gates(root) if gate.get("task_id") == task_id and gate.get("status") == "approved"]
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


def _lifecycle_projection(gate: dict | None, evidence_ok: bool) -> dict:
    flags = {
        "independent_rereview_authorized": False, "installation_authorized": False,
        "activation_authorized": False, "runtime_tool_enablement_authorized": False,
        "downstream_task_creation_authorized": False, "real_project_entry_authorized": False,
    }
    if gate:
        flags.update({key: gate.get(key, False) for key in flags})
    not_authorized = [key.upper() for key, value in flags.items() if value is not True]
    unverified = [] if evidence_ok else ["EVIDENCE_MANIFEST_REQUIRED"]
    if not flags["independent_rereview_authorized"]:
        unverified.append("FRESH_INDEPENDENT_REREVIEW_NOT_PERFORMED")
    return {
        "schema": "ProjectLifecycleProjection/v1", "verified": ["STRUCTURED_STATE_HASHES_VERIFIED"] if evidence_ok else [],
        "unverified": unverified, "not_performed": ["USER_ACCEPTANCE_NOT_PERFORMED", "PRODUCTION_AUTHORITY_LIFECYCLE_UNAVAILABLE"],
        "not_authorized": not_authorized, "installation_eligibility": "BLOCKED",
    }


def build_handoff_model(root: Path) -> dict:
    root = root.resolve()
    continuity = load_project_continuity(root)
    state = load_yaml(root / ".ai" / "state.yaml")
    task_id = current_task_id(root)
    status = task_status(root, task_id)
    approved = _approved_execution_gate(root, task_id)
    current_gate = state.get("current_gate_id")
    current_gate = None if current_gate in (None, "", "null") else current_gate
    action = {
        "schema": "ProjectGovernorNextAction/v2", "current_task_id": task_id,
        "current_task_status": status, "current_gate_id": current_gate,
        "approved_execution_gate_id": approved.get("id") if approved else None,
        "approved_execution_status": approved.get("execution_status") if approved else None,
        "lifecycle_revision": approved.get("lifecycle_revision", 0) if approved else 0,
        "next_action": "CONTINUE_APPROVED_EXECUTION" if status == "in_progress" else "USER_DECISION_REQUIRED",
    }
    evidence = None
    evidence_error = None
    if task_id:
        try:
            evidence = verify_evidence_manifest(root, _manifest_path(root, task_id))
        except GovernanceError as exc:
            evidence_error = exc.code
    registry = None
    try:
        registry = load_transaction_registry(root)
    except GovernanceError as exc:
        if exc.code != "TRANSACTION_REGISTRY_MISSING":
            raise
    task_path = root / ".ai" / "tasks" / f"{task_id}.md" if task_id else None
    task_hash = _sha(task_path.read_bytes()) if task_path and task_path.is_file() else _sha(b"")
    authority_hash = _sha(approved or {})
    hashes = {key: continuity[key] for key in ("source_sha256", "semantic_sha256", "file_sha256")}
    checkpoint = checkpoint_status(registry, hashes, evidence, task_hash, authority_hash)
    lifecycle = _lifecycle_projection(approved, evidence is not None)
    if evidence_error and evidence_error not in lifecycle["unverified"]:
        lifecycle["unverified"].append(evidence_error)
    orientation = {
        "schema": "ProjectContinuityProjection/v1", "project_id": continuity["data"]["project_id"],
        "user_origin": continuity["payload"]["user_origin"],
        "product_identity": continuity["payload"]["product_identity"],
        "protected_decisions": continuity["payload"]["protected_decisions"],
        "authorization_boundaries": continuity["payload"]["authorization_boundaries"],
        "source_sha256": continuity["source_sha256"], "semantic_sha256": continuity["semantic_sha256"],
        "persisted_file_sha256": continuity["file_sha256"],
    }
    return {"orientation": orientation, "action": action, "lifecycle": lifecycle, "checkpoint": checkpoint}


def render_handoff(root: Path, note: str = "") -> tuple[str, dict]:
    model = build_handoff_model(root)
    action = model["action"]
    status = action["current_task_status"] or "unknown"
    task_id = action["current_task_id"] or "none"
    checkpoint = model["checkpoint"]
    state = load_yaml(root / ".ai" / "state.yaml")

    # Current gate info — distinguish pending vs active (v3.5)
    pending_gate = state.get("current_gate_id")
    pending_gate = None if pending_gate in (None, "", "null") else pending_gate
    active_gate = _approved_execution_gate(root, task_id)
    # Approved execution is not a pending user decision. Keep projections
    # mutually exclusive even while legacy state retains current_gate_id.
    if active_gate and pending_gate == active_gate.get("id"):
        pending_gate = None

    gate_lines = []
    if pending_gate:
        gate_lines.append(f"pending_gate_status: {pending_gate} (awaiting user decision)")
    else:
        gate_lines.append("pending_gate_status: none (no pending decision required)")

    if active_gate:
        gate_id = active_gate.get("id", "?")
        gate_exec = active_gate.get("execution_status", "?")
        gate_lines.append(f"active_gate: {gate_id}")
        gate_lines.append(f"active_gate_status: approved / {gate_exec}")
        gate_lines.append("")
        gate_lines.append("current_gate_id is null because no pending decision is required.")
        gate_lines.append(f"{gate_id} is approved and execution is in progress.")
    else:
        gate_lines.append("active_gate: none")

    gate_info = "\n".join(gate_lines)

    handoff = f"""# Handoff

> **权威层级**: state.yaml > gates.yaml > task_graph.yaml > HANDOFF.md
> HANDOFF 是连续性辅助信息，不得重新定义状态。所有状态以机器可读文件为准。

## Product Direction And Authority

{render_json_block('PROJECT-CONTINUITY', model['orientation'])}

## Current Phase

{load_yaml(root / '.ai' / 'state.yaml').get('current_phase', 'unknown')}

## Current Task

{task_id}

Status: `{status}`

## Current Gate

{gate_info}

## Allowed Scope

Defined by the active gate's allowed_paths in gates.yaml.

## Forbidden Scope

Defined by the active gate's forbidden_actions in gates.yaml.

## Verified

{chr(10).join('- ' + v for v in model['lifecycle'].get('verified', ['None'])) if model['lifecycle'].get('verified') else 'None'}

## Unverified

{chr(10).join('- ' + v for v in model['lifecycle'].get('unverified', ['None'])) if model['lifecycle'].get('unverified') else 'None'}

## Evidence

Evidence manifest: {f".ai/evidence/{task_id}/evidence-manifest.v1.yaml" if task_id else 'not yet created'}.

## Integration Impact

Checkpoint status: {checkpoint.get('checkpoint_status', 'UNKNOWN')}.
Blockers: {', '.join(checkpoint.get('blockers', ['none'])) if checkpoint.get('blockers') else 'none'}.

## Next Session First Step

{action['next_action']}

## Startup Prompt

Use $project-governor, validate structured state, and continue only inside the approved scope.

提醒：reviewer PASS / validator / 测试通过均为 evidence，不等于用户批准。

## Structured Lifecycle

{render_json_block('LIFECYCLE', model['lifecycle'])}

## Structured Next Action

{render_json_block('NEXT-ACTION', action)}

## Checkpoint

{render_json_block('CHECKPOINT', checkpoint)}
"""
    state["last_handoff_at"] = now_precise()
    return handoff, state
