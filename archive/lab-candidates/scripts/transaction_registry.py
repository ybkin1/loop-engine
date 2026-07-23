from __future__ import annotations

import hashlib
from pathlib import Path

from governor_lib import GovernanceError, canonical_json, load_yaml, safe_project_path


REGISTRY_FIELDS = {
    "schema", "contract_id", "requirements_revision", "project_id", "controller_generation",
    "registry_revision", "state_revision_sha256", "active_transactions", "in_flight_actors",
    "unconsumed_deltas", "partial_writes", "generation_fence", "checkpoint_acknowledgments",
    "source_sha256", "semantic_sha256", "updated_at", "updated_by", "authority_ref", "fixture_only",
}
FENCE_FIELDS = {"fence_id", "fenced_generation", "successor_generation", "issued_at", "authority_ref"}
ACK_FIELDS = {
    "checkpoint_id", "controller_generation", "recovered_state_sha256", "acknowledged_at",
    "acknowledged_by", "authority_ref",
}
ACTIVE_FIELDS = {"transaction_id", "owner_actor_id", "state", "generation", "lease_id", "safe_point", "result_ref"}
ACTOR_FIELDS = {"actor_id", "packet_id", "generation", "status"}
DELTA_FIELDS = {"delta_id", "producer_id", "generation", "sha256", "status"}
PARTIAL_FIELDS = {"transaction_id", "marker_path", "status"}


def _sha(value) -> str:
    payload = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _hex(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789ABCDEF" for character in value)


def _closed_list(value, fields: set[str], label: str) -> None:
    if not isinstance(value, list) or len(value) > 256:
        raise GovernanceError("TRANSACTION_REGISTRY_INVALID", f"{label} must be a bounded list")
    if any(not isinstance(item, dict) or set(item) != fields for item in value):
        raise GovernanceError("TRANSACTION_REGISTRY_INVALID", f"{label} entry fields are invalid")


def load_transaction_registry(root: Path, relative: str = ".ai/transaction_registry.yaml") -> dict:
    root = root.resolve()
    path = safe_project_path(root, relative)
    if not path.is_file():
        raise GovernanceError("TRANSACTION_REGISTRY_MISSING", f"Transaction registry missing: {relative}")
    before = path.stat()
    if before.st_size > 1024 * 1024:
        raise GovernanceError("TRANSACTION_REGISTRY_INVALID", "Transaction registry exceeds 1 MiB")
    raw = path.read_bytes()
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    ):
        raise GovernanceError("TRANSACTION_REGISTRY_CHANGED", "Transaction registry changed while reading")
    data = load_yaml(path)
    if not isinstance(data, dict) or set(data) != REGISTRY_FIELDS or data.get("schema") != "TransactionRegistry/v1":
        raise GovernanceError("TRANSACTION_REGISTRY_INVALID", "TransactionRegistry/v1 fields are invalid")
    if data.get("contract_id") != "CDFT-2026-07-16-R1" or data.get("requirements_revision") != "T-0034-REQ-2026-07-16-R1":
        raise GovernanceError("TRANSACTION_REGISTRY_INVALID", "Transaction contract identity mismatch")
    if not isinstance(data.get("controller_generation"), int) or data["controller_generation"] < 1:
        raise GovernanceError("TRANSACTION_REGISTRY_INVALID", "Controller generation must be positive")
    if not isinstance(data.get("registry_revision"), int) or data["registry_revision"] < 0:
        raise GovernanceError("TRANSACTION_REGISTRY_INVALID", "Registry revision must be non-negative")
    for field in ("state_revision_sha256", "source_sha256", "semantic_sha256"):
        if not _hex(data.get(field)):
            raise GovernanceError("TRANSACTION_REGISTRY_INVALID", f"Invalid hash field: {field}")
    _closed_list(data["active_transactions"], ACTIVE_FIELDS, "active_transactions")
    _closed_list(data["in_flight_actors"], ACTOR_FIELDS, "in_flight_actors")
    _closed_list(data["unconsumed_deltas"], DELTA_FIELDS, "unconsumed_deltas")
    _closed_list(data["partial_writes"], PARTIAL_FIELDS, "partial_writes")
    _closed_list(data["checkpoint_acknowledgments"], ACK_FIELDS, "checkpoint_acknowledgments")
    if not isinstance(data.get("generation_fence"), dict) or set(data["generation_fence"]) != FENCE_FIELDS:
        raise GovernanceError("TRANSACTION_REGISTRY_INVALID", "Generation fence fields are invalid")
    semantic = {key: value for key, value in data.items() if key not in {"semantic_sha256", "updated_at"}}
    if data["semantic_sha256"] != _sha(semantic):
        raise GovernanceError("TRANSACTION_REGISTRY_HASH_MISMATCH", "Transaction registry semantic hash mismatch")
    checkpoint_semantic = {
        key: value for key, value in data.items()
        if key not in {"semantic_sha256", "updated_at", "checkpoint_acknowledgments"}
    }
    return {
        "data": data,
        "source_sha256": data["source_sha256"],
        "semantic_sha256": data["semantic_sha256"],
        "checkpoint_semantic_sha256": _sha(checkpoint_semantic),
        "file_sha256": _sha(raw),
    }


def checkpoint_status(registry: dict | None, continuity: dict, evidence: dict, task_scope_hash: str, authority_hash: str) -> dict:
    if registry is None:
        return {"schema": "Checkpoint/v1.0", "checkpoint_status": "NOT_ESTABLISHED", "blockers": ["TRANSACTION_REGISTRY_MISSING"]}
    data = registry["data"]
    blockers = []
    for field in ("active_transactions", "in_flight_actors", "unconsumed_deltas", "partial_writes"):
        if data[field]:
            blockers.append(f"NONEMPTY_{field.upper()}")
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
        "evidence_file_count": evidence["file_count"],
        "evidence_total_bytes": evidence["total_bytes"],
        "task_scope_hash": task_scope_hash,
        "authority_hash": authority_hash,
        "controller_generation": generation,
        "requirements_revision": data["requirements_revision"],
    }
    recovered_hash = _sha(recovered_payload)
    checkpoint_id = f"CP-{_sha({'recovered_state_sha256': recovered_hash, 'generation': generation})[:24]}"
    matches = [
        item for item in data["checkpoint_acknowledgments"]
        if item["checkpoint_id"] == checkpoint_id
        and item["controller_generation"] == generation
        and item["recovered_state_sha256"] == recovered_hash
    ]
    status = "PENDING_SUCCESSOR_ACK"
    if matches:
        status = "STABLE_FIXTURE_ONLY" if data["fixture_only"] else "STABLE"
    return {
        "schema": "Checkpoint/v1.0", "contract_id": "PCC-2026-07-16-R1",
        "checkpoint_id": checkpoint_id, "checkpoint_status": status,
        "controller_generation": generation, "requirements_revision": data["requirements_revision"],
        "recovered_state_sha256": recovered_hash, "project_continuity_hashes": continuity,
        "transaction_registry_hashes": {key: registry[key] for key in (
            "source_sha256", "semantic_sha256", "checkpoint_semantic_sha256", "file_sha256")},
        "evidence_manifest_hashes": evidence, "task_scope_hash": task_scope_hash,
        "authority_hash": authority_hash, "blockers": [], "fixture_only": data["fixture_only"],
    }
