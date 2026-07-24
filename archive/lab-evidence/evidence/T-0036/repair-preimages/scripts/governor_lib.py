from __future__ import annotations

import argparse
import base64
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_AI = ROOT / "templates" / "ai"
REQUIRED_FILES = [
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
    "state.yaml",
    "task_graph.yaml",
    "gates.yaml",
    "HANDOFF.md",
]
TASK_STATUSES = {
    "pending",
    "active",
    "approved_not_started",
    "in_progress",
    "blocked",
    "completed",
    "rejected",
}
ACTION_MODES = {
    "read_only",
    "prompt_generation_only",
    "create_pending_gate",
    "approve_pending_gate",
    "execute_approved_gate",
}
ACTION_RECORD_FIELDS = {
    "schema",
    "action_id",
    "request_id",
    "mode",
    "task_id",
    "gate_id",
    "latest_user_text",
    "explicit_execution_request",
    "allowed_paths",
    "allowed_actions",
    "forbidden_actions",
    "stop_condition",
}
GATE_PACKET_FIELDS = {
    "schema",
    "gate_id",
    "task_id",
    "title",
    "approval_phrase",
    "rejection_phrase",
    "exact_allowed_paths",
    "forbidden_effects",
}
NEXT_ACTION_FIELDS = {
    "schema",
    "current_task_id",
    "current_task_status",
    "current_gate_id",
    "current_gate_status",
    "current_action_mode",
    "result",
    "next_action_mode",
    "next_action_requires_explicit_user_request",
    "exact_next_user_phrase",
    "copyable_next_prompt",
    "allowed_scope",
    "forbidden_scope",
    "stop_condition",
}
CHECKPOINT_FIELDS = {
    "schema",
    "contract_id",
    "checkpoint_id",
    "controller_generation",
    "requirements_revision",
    "project_continuity_hash",
    "task_scope_hash",
    "authority_hash",
    "active_transactions",
    "in_flight_actors",
    "blocking_findings",
    "evidence_manifest_hash",
    "unconsumed_deltas",
    "next_safe_action",
    "producer_attestation",
    "created_at",
}
NEXT_ACTION_BLOCK = "NEXT-ACTION"
CHECKPOINT_BLOCK = "CHECKPOINT"
VALIDATION_COMMAND_FIELDS = {
    "validation_started_at",
    "validation_completed_at",
    "exact_command_argv",
    "exit_code",
    "test_count",
}
VALIDATION_SNAPSHOT_FIELDS = {
    "schema",
    "task_id",
    "gate_id",
    "action_id",
    "created_at",
    "target_and_test_paths",
    "protected_global_hashes",
}


class GovernanceError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def today() -> str:
    return _dt.date.today().isoformat()


def now() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


def now_precise() -> str:
    return _dt.datetime.now().astimezone().isoformat()


def project_root_arg() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", help="Project root containing or receiving .ai")
    return parser


def ai_dir(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / ".ai"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def transactional_write_texts(base: Path, changes: dict[Path, str]) -> None:
    marker = base / ".project-governor-transaction.json"
    if marker.exists():
        raise RuntimeError(f"Unresolved Project Governor transaction: {marker}")
    transaction_id = uuid.uuid4().hex
    entries = []
    committed = []
    recovered = True
    try:
        for path, text in changes.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            staged = path.with_name(f".{path.name}.{transaction_id}.tmp")
            backup = path.with_name(f".{path.name}.{transaction_id}.bak")
            staged.write_text(text, encoding="utf-8", newline="\n")
            if path.exists():
                shutil.copy2(path, backup)
            entries.append(
                {
                    "path": str(path),
                    "staged": str(staged),
                    "backup": str(backup),
                    "existed": path.exists(),
                    "fingerprint": file_fingerprint(path),
                }
            )
        journal = {"transaction_id": transaction_id, "entries": entries, "committed": []}
        write_text(marker, json.dumps(journal, indent=2))
        for entry in entries:
            path = Path(entry["path"])
            if file_fingerprint(path) != entry["fingerprint"]:
                raise RuntimeError(f"Concurrent modification detected: {path}")
            os.replace(entry["staged"], entry["path"])
            committed.append(entry)
            journal["committed"].append(entry["path"])
            write_text(marker, json.dumps(journal, indent=2))
    except Exception:
        for entry in reversed(committed):
            try:
                backup = Path(entry["backup"])
                path = Path(entry["path"])
                if backup.exists():
                    os.replace(backup, path)
                elif not entry["existed"]:
                    path.unlink(missing_ok=True)
            except Exception:
                recovered = False
        raise
    finally:
        for entry in entries:
            Path(entry["staged"]).unlink(missing_ok=True)
            if recovered:
                Path(entry["backup"]).unlink(missing_ok=True)
        if recovered:
            marker.unlink(missing_ok=True)


def file_fingerprint(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def evidence_manifest_hash(root: Path, task_id: str | None) -> str:
    if not task_id:
        return sha256_text("")
    evidence = ai_dir(root) / "evidence" / task_id
    entries = []
    if evidence.exists():
        for path in sorted(item for item in evidence.rglob("*") if item.is_file()):
            entries.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
                }
            )
    return sha256_text(canonical_json(entries))


def current_task_gate(root: Path, task_id: str | None) -> dict | None:
    if not task_id:
        return None
    matches = [gate for gate in gates(root) if isinstance(gate, dict) and gate.get("task_id") == task_id]
    pending = [gate for gate in matches if gate.get("status") == "pending"]
    approved = [gate for gate in matches if gate.get("status") == "approved"]
    return (pending or approved or matches or [None])[-1]


def build_next_action_contract(
    root: Path,
    status: str | None,
    pending: list[dict],
    evidence_ok: bool,
) -> dict:
    task_id = current_task_id(root)
    gate = current_task_gate(root, task_id)
    gate_id = gate.get("id") if gate else None
    gate_status = gate.get("status") if gate else None
    if gate and status in {"approved_not_started", "in_progress"}:
        allowed = (
            gate.get("exact_allowed_paths_after_later_execution_request")
            or gate.get("exact_candidate_implementation_paths")
            or gate.get("exact_allowed_paths", [])
        )
    elif gate and gate_status == "pending":
        allowed = gate.get("exact_allowed_paths_registration") or gate.get("exact_allowed_paths", [])
    else:
        allowed = gate.get("exact_allowed_paths", []) if gate else []
    forbidden = (
        gate.get("exact_forbidden_paths_effects") or gate.get("forbidden_effects", [])
        if gate
        else []
    )
    if not allowed and task_id:
        allowed = [f".ai/tasks/{task_id}.md"]
    if not forbidden:
        forbidden = ["unapproved effects", "installation", "activation"]

    if pending:
        gate = pending[0]
        gate_id = gate.get("id")
        gate_status = "pending"
        phrase = f"{gate.get('approval_phrase', f'批准 {gate_id}')} | {gate.get('rejection_phrase', f'拒绝 {gate_id}')}"
        return {
            "schema": "ProjectGovernorNextAction/v1",
            "current_task_id": task_id,
            "current_task_status": status,
            "current_gate_id": gate_id,
            "current_gate_status": gate_status,
            "current_action_mode": "create_pending_gate",
            "result": "pending_user_decision",
            "next_action_mode": "approve_pending_gate",
            "next_action_requires_explicit_user_request": True,
            "exact_next_user_phrase": phrase,
            "copyable_next_prompt": phrase,
            "allowed_scope": allowed,
            "forbidden_scope": forbidden,
            "stop_condition": "stop after recording exactly one user Gate decision",
        }
    if not evidence_ok:
        next_mode = "read_only"
        prompt = "恢复缺失的证据记录后停止。"
        result = "blocked_missing_evidence"
        requires_user = False
        current_mode = "read_only"
        stop = "stop after evidence recovery inventory"
    elif status == "approved_not_started" and gate_id:
        next_mode = "execute_approved_gate"
        prompt = gate.get("execution_phrase") or f"执行已批准的 {gate_id}"
        result = "approved_not_started"
        requires_user = True
        current_mode = "approve_pending_gate"
        stop = "stop after recording a distinct exact execution request"
    elif status == "in_progress":
        next_mode = "execute_approved_gate"
        prompt = "继续当前已授权执行，仅限批准范围。"
        result = "in_progress"
        requires_user = False
        current_mode = "execute_approved_gate"
        stop = "stop on scope, baseline, validation, or recovery failure"
    elif status == "completed":
        next_mode = "prompt_generation_only"
        prompt = "请决定是否创建新的独立任务。"
        result = "completed"
        requires_user = True
        current_mode = "read_only"
        stop = "stop before creating any downstream task or Gate"
    elif status == "blocked":
        next_mode = "read_only"
        prompt = "只读核验已记录 blocker，等待解除条件或用户决策。"
        result = "blocked"
        requires_user = True
        current_mode = "read_only"
        stop = "stop before any unapproved recovery or scope expansion"
    else:
        next_mode = "read_only"
        prompt = "继续当前任务前先核验授权和范围。"
        result = status or "unknown"
        requires_user = False
        current_mode = "read_only"
        stop = "stop on any missing or conflicting authority"
    return {
        "schema": "ProjectGovernorNextAction/v1",
        "current_task_id": task_id,
        "current_task_status": status,
        "current_gate_id": gate_id,
        "current_gate_status": gate_status,
        "current_action_mode": current_mode,
        "result": result,
        "next_action_mode": next_mode,
        "next_action_requires_explicit_user_request": requires_user,
        "exact_next_user_phrase": prompt if requires_user else "",
        "copyable_next_prompt": prompt,
        "allowed_scope": allowed,
        "forbidden_scope": forbidden,
        "stop_condition": stop,
    }


def validate_handoff_action_state(action: dict) -> list[str]:
    errors: list[str] = []
    status = action.get("current_task_status")
    gate_status = action.get("current_gate_status")
    mode = action.get("current_action_mode")
    expected = {
        "approved_not_started": ("approve_pending_gate", "approved"),
        "in_progress": ("execute_approved_gate", "approved"),
    }.get(status)
    if gate_status == "pending" and mode != "create_pending_gate":
        errors.append("pending Gate requires create_pending_gate as the recorded current mode")
    if expected and (mode, gate_status) != expected:
        errors.append(f"{status} requires current mode/status {expected[0]}/{expected[1]}")
    if status == "completed" and mode != "read_only":
        errors.append("completed task requires read_only current mode")
    return errors


def build_stable_checkpoint(root: Path, action: dict, created_at: str, state: dict) -> dict:
    base = ai_dir(root)
    marker = base / ".project-governor-transaction.json"
    if marker.exists():
        raise GovernanceError("RECOVERY_REQUIRED", f"Unresolved transaction prevents stable checkpoint: {marker}")
    task_id = action["current_task_id"]
    task_path = base / "tasks" / f"{task_id}.md" if task_id else None
    gate = current_task_gate(root, task_id)
    continuity_state = {
        "project_name": state.get("project_name"),
        "current_phase": state.get("current_phase"),
        "current_task_id": task_id,
        "current_task_status": action["current_task_status"],
    }
    checkpoint = {
        "schema": "Checkpoint/v1.0",
        "contract_id": "PCC-2026-07-16-R1",
        "controller_generation": int(state.get("controller_generation", 0)),
        "requirements_revision": "T-0034-REQ-2026-07-16-R1",
        "project_continuity_hash": sha256_text(canonical_json(continuity_state)),
        "task_scope_hash": hashlib.sha256(task_path.read_bytes()).hexdigest().upper() if task_path and task_path.exists() else sha256_text(""),
        "authority_hash": sha256_text(canonical_json(gate or {})),
        "active_transactions": [],
        "in_flight_actors": state.get("in_flight_actor_ids", []) if isinstance(state.get("in_flight_actor_ids", []), list) else [],
        "blocking_findings": state.get("blocking_findings", []) if isinstance(state.get("blocking_findings", []), list) else [],
        "evidence_manifest_hash": evidence_manifest_hash(root, task_id),
        "unconsumed_deltas": state.get("unconsumed_deltas", []) if isinstance(state.get("unconsumed_deltas", []), list) else [],
        "next_safe_action": action["copyable_next_prompt"],
        "producer_attestation": "unsigned",
        "created_at": created_at,
    }
    checkpoint["checkpoint_id"] = f"CP-{task_id or 'NONE'}-{sha256_text(canonical_json(checkpoint))[:16]}"
    return checkpoint


def render_json_block(name: str, value: dict) -> str:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    return (
        f"<!-- PROJECT-GOVERNOR-{name}-BEGIN -->\n"
        f"```json\n{payload}\n```\n"
        f"<!-- PROJECT-GOVERNOR-{name}-END -->"
    )


def parse_json_block(text: str, name: str) -> dict:
    begin = f"<!-- PROJECT-GOVERNOR-{name}-BEGIN -->"
    end = f"<!-- PROJECT-GOVERNOR-{name}-END -->"
    if text.count(begin) != 1 or text.count(end) != 1:
        raise GovernanceError("VALIDATION_ERROR", f"HANDOFF missing unique structured {name.lower()} contract")
    start = text.index(begin) + len(begin)
    stop = text.index(end, start)
    payload = text[start:stop].strip()
    if not payload.startswith("```json") or not payload.endswith("```"):
        raise GovernanceError("VALIDATION_ERROR", f"HANDOFF {name.lower()} block must be fenced JSON")
    try:
        value = json.loads(payload[len("```json") : -3].strip())
    except json.JSONDecodeError as exc:
        raise GovernanceError("VALIDATION_ERROR", f"HANDOFF {name.lower()} block is invalid JSON") from exc
    if not isinstance(value, dict):
        raise GovernanceError("VALIDATION_ERROR", f"HANDOFF {name.lower()} block must be an object")
    return value


def handoff_contract_errors(root: Path, text: str | None = None) -> list[str]:
    text = read_text(ai_dir(root) / "HANDOFF.md") if text is None else text
    errors: list[str] = []
    try:
        action = parse_json_block(text, NEXT_ACTION_BLOCK)
    except GovernanceError as exc:
        return [str(exc)]
    missing = sorted(NEXT_ACTION_FIELDS - set(action))
    unknown = sorted(set(action) - NEXT_ACTION_FIELDS)
    errors.extend(f"HANDOFF next-action contract missing field: {field}" for field in missing)
    errors.extend(f"HANDOFF next-action contract unknown field: {field}" for field in unknown)
    if missing or unknown:
        return errors
    errors.extend(validate_handoff_action_state(action))
    status = task_status(root, current_task_id(root))
    evidence_ok, _ = evidence_status(root, current_task_id(root))
    expected_action = build_next_action_contract(root, status, pending_gates(root), evidence_ok)
    if action != expected_action:
        errors.append("HANDOFF next-action contract mismatch with current state")

    try:
        checkpoint = parse_json_block(text, CHECKPOINT_BLOCK)
    except GovernanceError as exc:
        errors.append(str(exc))
        return errors
    missing = sorted(CHECKPOINT_FIELDS - set(checkpoint))
    unknown = sorted(set(checkpoint) - CHECKPOINT_FIELDS)
    errors.extend(f"HANDOFF checkpoint missing field: {field}" for field in missing)
    errors.extend(f"HANDOFF checkpoint unknown field: {field}" for field in unknown)
    if missing or unknown:
        return errors
    state = load_yaml(ai_dir(root) / "state.yaml")
    created_at = state.get("last_handoff_at")
    if not isinstance(created_at, str) or not created_at:
        errors.append("HANDOFF checkpoint requires state.last_handoff_at")
        return errors
    try:
        expected_checkpoint = build_stable_checkpoint(root, expected_action, created_at, state)
    except GovernanceError as exc:
        errors.append(str(exc))
        return errors
    if checkpoint != expected_checkpoint:
        errors.append("HANDOFF checkpoint mismatch with current state/evidence hashes")
    return errors


def validate_action_mode(
    mode: str,
    *,
    gate_status: str | None = None,
    explicit_execution_request: bool = False,
) -> list[str]:
    errors: list[str] = []
    if mode not in ACTION_MODES:
        return [f"Unknown action mode: {mode}"]
    if mode == "approve_pending_gate" and gate_status != "pending":
        errors.append("approve_pending_gate requires a pending gate")
    if mode == "execute_approved_gate":
        if gate_status != "approved":
            errors.append("execute_approved_gate requires an approved gate")
        if not explicit_execution_request:
            errors.append("execute_approved_gate requires an explicit execution request")
    return errors


def safe_project_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or len(relative) > 4096 or "\x00" in relative:
        raise GovernanceError("SCOPE_VIOLATION", f"Path must be project-relative: {relative!r}")
    try:
        relative_path = Path(relative)
        if relative_path.is_absolute():
            raise GovernanceError("SCOPE_VIOLATION", f"Path must be project-relative: {relative!r}")
        root = root.resolve()
        unresolved = root / relative_path
        path = unresolved.resolve()
    except (OSError, ValueError) as exc:
        raise GovernanceError("SCOPE_VIOLATION", f"Invalid project-relative path: {relative!r}") from exc
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise GovernanceError("SCOPE_VIOLATION", f"Path escapes project root: {relative}") from exc
    cursor = root
    for part in relative_path.parts:
        cursor = cursor / part
        is_junction = getattr(cursor, "is_junction", lambda: False)
        if cursor.exists() and (cursor.is_symlink() or is_junction()):
            raise GovernanceError("SCOPE_VIOLATION", f"Reparse/symlink path is forbidden: {relative}")
    return path


def load_json_record(root: Path, relative: str) -> tuple[dict, Path]:
    path = safe_project_path(root, relative)
    if not path.is_file():
        raise GovernanceError("BASELINE_MISSING", f"JSON record missing: {relative}")
    if path.stat().st_size > 1024 * 1024:
        raise GovernanceError("VALIDATION_ERROR", f"JSON record exceeds 1 MiB: {relative}")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise GovernanceError("VALIDATION_ERROR", f"Invalid UTF-8 JSON record: {relative}") from exc
    return parse_json_record(text, relative), path


def reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_record(text: str, label: str) -> dict:
    if len(text.encode("utf-8")) > 1024 * 1024:
        raise GovernanceError("VALIDATION_ERROR", f"JSON record exceeds 1 MiB: {label}")
    try:
        value = json.loads(text, object_pairs_hook=reject_duplicate_json_keys)
    except (json.JSONDecodeError, ValueError) as exc:
        raise GovernanceError("VALIDATION_ERROR", f"Invalid JSON record: {label}") from exc
    if not isinstance(value, dict):
        raise GovernanceError("VALIDATION_ERROR", f"JSON record must be an object: {label}")
    return value


def load_inline_json_record(root: Path, text: str, evidence_relative: str) -> tuple[dict, Path]:
    evidence_path = safe_project_path(root, evidence_relative)
    if not evidence_path.is_file():
        raise GovernanceError("BASELINE_MISSING", f"Inline action evidence missing: {evidence_relative}")
    return parse_json_record(text, "inline action record"), evidence_path


def validate_closed_fields(value: dict, expected: set[str], label: str) -> None:
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing:
        raise GovernanceError("VALIDATION_ERROR", f"{label} missing fields: {', '.join(missing)}")
    if unknown:
        raise GovernanceError("VALIDATION_ERROR", f"{label} unknown fields: {', '.join(unknown)}")


def validate_action_record(root: Path, record: dict, expected_mode: str) -> None:
    validate_closed_fields(record, ACTION_RECORD_FIELDS, "GovernanceAction/v1")
    if record.get("schema") != "GovernanceAction/v1":
        raise GovernanceError("VALIDATION_ERROR", "Unsupported action schema")
    if record.get("mode") != expected_mode or record.get("allowed_actions") != [expected_mode]:
        raise GovernanceError("AUTHORITY_MISSING", f"Action mode must be exactly {expected_mode}")
    for field in ("action_id", "request_id", "task_id", "gate_id", "latest_user_text", "stop_condition"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise GovernanceError("VALIDATION_ERROR", f"Action field must be non-empty: {field}")
        if len(record[field]) > 4096 or re.search(r"[\x00-\x1f\x7f]", record[field]):
            raise GovernanceError("VALIDATION_ERROR", f"Action field contains invalid control/oversized text: {field}")
    if not re.fullmatch(r"T-\d{4}", record["task_id"]) or not re.fullmatch(r"G-[A-Z0-9-]+", record["gate_id"]):
        raise GovernanceError("VALIDATION_ERROR", "Action task_id or gate_id format is invalid")
    for field in ("allowed_paths", "allowed_actions", "forbidden_actions"):
        if not isinstance(record.get(field), list) or not all(isinstance(item, str) for item in record[field]):
            raise GovernanceError("VALIDATION_ERROR", f"Action field must be a string list: {field}")
        if len(record[field]) > 256:
            raise GovernanceError("VALIDATION_ERROR", f"Action field exceeds 256 items: {field}")
    if not isinstance(record.get("explicit_execution_request"), bool):
        raise GovernanceError("VALIDATION_ERROR", "explicit_execution_request must be boolean")
    for relative in record["allowed_paths"]:
        safe_project_path(root, relative)


def require_allowed_targets(root: Path, record: dict, targets: list[Path]) -> None:
    allowed = {safe_project_path(root, relative) for relative in record["allowed_paths"]}
    missing = [str(path.relative_to(root)) for path in targets if path.resolve() not in allowed]
    if missing:
        raise GovernanceError("SCOPE_VIOLATION", f"Write target not authorized: {', '.join(missing)}")


def record_reference(root: Path, path: Path, task_id: str) -> str:
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    required_prefix = f".ai/evidence/{task_id}/"
    if not relative.startswith(required_prefix):
        raise GovernanceError("SCOPE_VIOLATION", f"Action evidence must be under {required_prefix}")
    return relative


def replace_task_status_text(text: str, status: str) -> str:
    if status not in TASK_STATUSES:
        raise GovernanceError("VALIDATION_ERROR", f"Unsupported task status: {status}")
    pattern = r"(?ms)(^## Status\s*$\s*^)([^#\r\n]+?)(\s*$)"
    if not re.search(pattern, text):
        raise GovernanceError("VALIDATION_ERROR", "Task file has no valid Status section")
    return re.sub(pattern, rf"\g<1>{status}\g<3>", text, count=1)


def update_task_graph_data(data: dict, task_id: str, status: str) -> None:
    tasks = data.get("tasks")
    matches = [item for item in tasks if isinstance(item, dict) and item.get("id") == task_id] if isinstance(tasks, list) else []
    if len(matches) != 1:
        raise GovernanceError("VALIDATION_ERROR", f"Task graph must contain exactly one {task_id}")
    matches[0]["status"] = status
    matches[0]["updated_at"] = now()


def exact_gate(root: Path, gate_id: str) -> dict:
    matches = [gate for gate in gates(root) if isinstance(gate, dict) and gate.get("id") == gate_id]
    if len(matches) != 1:
        raise GovernanceError("VALIDATION_ERROR", f"Gate must exist exactly once: {gate_id}")
    return matches[0]


def ensure_unused_request(gate: dict, request_id: str) -> None:
    used = gate.get("action_request_ids", [])
    if request_id in used:
        raise GovernanceError("REQUEST_REUSE", f"Request id already used: {request_id}")


def copy_templates(project_root: str | Path, force: bool = False, title: str | None = None) -> list[str]:
    target = ai_dir(project_root)
    created: list[str] = []
    for src in TEMPLATE_AI.rglob("*"):
        rel = src.relative_to(TEMPLATE_AI)
        dst = target / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        if dst.exists() and not force:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = read_text(src)
        if rel.as_posix() == "PROJECT.md" and title:
            text = text.replace("# Project", f"# {title}", 1)
        if rel.as_posix() == "state.yaml" and title:
            text = text.replace("project_name: TBD", f"project_name: {quote_yaml(title)}")
        write_text(dst, text)
        created.append(str(rel))
    for folder in ["tasks", "reviews", "evidence"]:
        (target / folder).mkdir(parents=True, exist_ok=True)
    return created


def quote_yaml(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def try_yaml_load(text: str):
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except Exception:
        return load_simple_yaml(text)


def load_yaml(path: Path):
    return try_yaml_load(read_text(path)) if path.exists() else {}


def load_simple_yaml(text: str):
    lines = []
    for raw in text.replace("\ufeff", "").splitlines():
        stripped_comment = strip_comment(raw).rstrip()
        if not stripped_comment.strip():
            continue
        indent = len(stripped_comment) - len(stripped_comment.lstrip(" "))
        lines.append((indent, stripped_comment.strip()))
    if not lines:
        return {}
    value, _ = parse_block(lines, 0, lines[0][0])
    return value if isinstance(value, dict) else {}


def strip_comment(line: str) -> str:
    single = False
    double = False
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\" and double:
            escaped = True
            continue
        if char == "'" and not double:
            single = not single
            continue
        if char == '"' and not single:
            double = not double
            continue
        if char == "#" and not single and not double:
            return line[:index]
    return line


def parse_block(lines: list[tuple[int, str]], index: int, indent: int):
    if index >= len(lines):
        return None, index
    if lines[index][1].startswith("-") and lines[index][0] == indent:
        return parse_list(lines, index, indent)
    return parse_map(lines, index, indent)


def parse_map(lines: list[tuple[int, str]], index: int, indent: int):
    data = {}
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent != indent or content.startswith("-") or ":" not in content:
            break
        key, value = content.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            data[key] = parse_scalar(value)
            index += 1
            continue
        index += 1
        if index < len(lines) and lines[index][0] > indent:
            child, index = parse_block(lines, index, lines[index][0])
            data[key] = child
        else:
            data[key] = None
    return data, index


def parse_list(lines: list[tuple[int, str]], index: int, indent: int):
    items = []
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent != indent or not content.startswith("-"):
            break
        rest = content[1:].strip()
        if not rest:
            index += 1
            if index < len(lines) and lines[index][0] > indent:
                child, index = parse_block(lines, index, lines[index][0])
                items.append(child)
            else:
                items.append(None)
            continue
        if ":" in rest and not rest.startswith(("'", '"')):
            item = {}
            key, value = rest.split(":", 1)
            item[key.strip()] = parse_scalar(value.strip()) if value.strip() else None
            index += 1
            while index < len(lines) and lines[index][0] > indent:
                child_indent, child_content = lines[index]
                if child_indent <= indent or child_content.startswith("-") or ":" not in child_content:
                    break
                child_key, child_value = child_content.split(":", 1)
                child_key = child_key.strip()
                child_value = child_value.strip()
                if child_value:
                    item[child_key] = parse_scalar(child_value)
                    index += 1
                else:
                    index += 1
                    if index < len(lines) and lines[index][0] > child_indent:
                        child, index = parse_block(lines, index, lines[index][0])
                        item[child_key] = child
                    else:
                        item[child_key] = None
            items.append(item)
            continue
        items.append(parse_scalar(rest))
        index += 1
    return items, index


def parse_scalar(value: str):
    value = value.strip()
    if value == "[]":
        return []
    if value == "{}":
        return {}
    if value in ("null", "~"):
        return None
    if value in ("true", "false"):
        return value == "true"
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            return value
    return value


def dump_yaml(value, indent: int = 0) -> str:
    pad = " " * indent
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if item == []:
                lines.append(f"{pad}{key}: []")
                continue
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.append(dump_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {format_scalar(item)}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return f"{pad}[]"
        lines = []
        for item in value:
            if isinstance(item, dict):
                lines.append(f"{pad}-")
                lines.append(dump_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}- {format_scalar(item)}")
        return "\n".join(lines)
    return f"{pad}{format_scalar(value)}"


def format_scalar(value) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    text = str(value)
    if not text or re.search(r"[:#\[\]{}]|^\s|\s$", text):
        return quote_yaml(text)
    return text


def write_yaml(path: Path, data) -> None:
    write_text(path, dump_yaml(data) + "\n")


def current_task_id(root: Path) -> str | None:
    value = load_yaml(ai_dir(root) / "state.yaml").get("current_task_id")
    return value if value and value != "null" else None


def task_status_from_text(text: str) -> str | None:
    match = re.search(r"(?ms)^## Status\s*$\s*^([^#\r\n]+?)\s*$", text)
    if not match:
        return None
    status = match.group(1).strip().strip("`")
    return status if status in TASK_STATUSES else None


def task_status(root: Path, task_id: str | None) -> str | None:
    if not task_id:
        return None
    return task_status_from_text(read_text(ai_dir(root) / "tasks" / f"{task_id}.md"))


def task_graph_entries(root: Path, task_id: str) -> list[dict]:
    tasks = load_yaml(ai_dir(root) / "task_graph.yaml").get("tasks", [])
    if not isinstance(tasks, list):
        return []
    return [task for task in tasks if isinstance(task, dict) and task.get("id") == task_id]


def governance_invariant_errors(root: Path) -> list[str]:
    errors: list[str] = []
    base = ai_dir(root)
    state = load_yaml(base / "state.yaml")
    task_id = current_task_id(root)
    if not task_id:
        return errors
    status = task_status(root, task_id)
    if status is None:
        errors.append(f"Current task status missing or invalid: {task_id}")
    entries = task_graph_entries(root, task_id)
    if len(entries) != 1:
        errors.append(f"Current task must appear exactly once in task graph: {task_id} (found {len(entries)})")
    elif status is not None and entries[0].get("status") != status:
        errors.append(
            f"Task status mismatch: {task_id} task={status} task_graph={entries[0].get('status', 'missing')}"
        )
    current_gate_id = state.get("current_gate_id")
    current_gate_id = None if current_gate_id in (None, "null", "") else current_gate_id
    matching_gates = [gate for gate in gates(root) if gate.get("id") == current_gate_id]
    if current_gate_id and len(matching_gates) != 1:
        errors.append(f"current_gate_id does not identify exactly one gate: {current_gate_id}")
    elif matching_gates:
        gate = matching_gates[0]
        if gate.get("task_id") != task_id:
            errors.append(f"Current gate task mismatch: gate={current_gate_id} task={gate.get('task_id')} current={task_id}")
        if gate.get("status") != "pending":
            errors.append(f"Current gate is not pending: {current_gate_id} status={gate.get('status')}")
    pending = pending_gates(root)
    current_pending = [gate for gate in pending if gate.get("task_id") == task_id]
    if current_pending and not current_gate_id:
        errors.append(f"Pending gate for current task is not current_gate_id: {current_pending[0].get('id')}")
    if current_gate_id and not current_pending:
        errors.append(f"current_gate_id has no pending gate for current task: {current_gate_id}")
    task_gates = [gate for gate in gates(root) if gate.get("task_id") == task_id]
    approved_gates = [gate for gate in task_gates if gate.get("status") == "approved"]
    if status in {"approved_not_started", "in_progress"}:
        if not approved_gates:
            errors.append(f"{status} requires an approved gate for current task: {task_id}")
        elif not any(evidence_path_exists(base, gate.get("approval_evidence")) for gate in approved_gates):
            errors.append(f"{status} requires approval evidence for current task: {task_id}")
    if status == "in_progress" and not any(
        evidence_path_exists(base, gate.get("execution_evidence")) for gate in approved_gates
    ):
        errors.append(f"in_progress requires execution evidence for current task: {task_id}")
    errors.extend(historical_task_inventory_errors(root, exclude_task_id=task_id))
    return errors


def evidence_path_exists(base: Path, value) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value)
    if not path.is_absolute():
        path = base.parent / path
    return path.exists()


def historical_task_inventory_errors(root: Path, exclude_task_id: str | None = None) -> list[str]:
    errors: list[str] = []
    tasks_dir = ai_dir(root) / "tasks"
    graph = load_yaml(ai_dir(root) / "task_graph.yaml").get("tasks", [])
    graph_entries = graph if isinstance(graph, list) else []
    for path in sorted(tasks_dir.glob("T-*.md")):
        task_id = path.stem
        if task_id == exclude_task_id:
            continue
        status = task_status_from_text(read_text(path))
        matches = [item for item in graph_entries if isinstance(item, dict) and item.get("id") == task_id]
        if status is None:
            errors.append(f"Historical task status missing or invalid: {task_id}")
        if len(matches) != 1:
            errors.append(f"Historical task must appear exactly once in task graph: {task_id} (found {len(matches)})")
        elif status is not None and matches[0].get("status") != status:
            errors.append(
                f"Historical task status mismatch: {task_id} task={status} task_graph={matches[0].get('status', 'missing')}"
            )
    return errors


def next_task_id(root: Path) -> str:
    tasks_dir = ai_dir(root) / "tasks"
    highest = 0
    for path in tasks_dir.glob("T-*.md"):
        match = re.match(r"T-(\d{4})\.md$", path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"T-{highest + 1:04d}"


def evidence_status(root: Path, task_id: str | None) -> tuple[bool, str]:
    if not task_id:
        return False, "No current task id"
    base = ai_dir(root) / "evidence" / task_id
    commands = base / "commands.md"
    if not base.exists():
        return False, f"Missing evidence directory: {base}"
    if not commands.exists() or not read_text(commands).strip():
        return False, f"Missing evidence commands: {commands}"
    return True, str(base)


def gates(root: Path) -> list[dict]:
    data = load_yaml(ai_dir(root) / "gates.yaml")
    items = data.get("gates", [])
    return items if isinstance(items, list) else []


def pending_gates(root: Path) -> list[dict]:
    return [gate for gate in gates(root) if isinstance(gate, dict) and gate.get("status") == "pending"]


def create_pending_gate_action(
    root: Path,
    record: dict,
    record_path: Path,
    packet: dict,
) -> None:
    root = root.resolve()
    validate_action_record(root, record, "create_pending_gate")
    validate_closed_fields(packet, GATE_PACKET_FIELDS, "GatePacket/v1")
    if packet.get("schema") != "GatePacket/v1":
        raise GovernanceError("VALIDATION_ERROR", "Unsupported gate packet schema")
    for field in ("gate_id", "task_id", "title", "approval_phrase", "rejection_phrase"):
        if not isinstance(packet.get(field), str) or not packet[field].strip():
            raise GovernanceError("VALIDATION_ERROR", f"Gate packet field must be non-empty: {field}")
        if len(packet[field]) > 4096 or re.search(r"[\x00-\x1f\x7f]", packet[field]):
            raise GovernanceError("VALIDATION_ERROR", f"Gate packet field contains invalid text: {field}")
    for field in ("exact_allowed_paths", "forbidden_effects"):
        if not isinstance(packet.get(field), list) or not packet[field] or len(packet[field]) > 256:
            raise GovernanceError("VALIDATION_ERROR", f"Gate packet field must be a non-empty bounded list: {field}")
        if not all(isinstance(item, str) and item and len(item) <= 4096 for item in packet[field]):
            raise GovernanceError("VALIDATION_ERROR", f"Gate packet field has an invalid item: {field}")
    for relative in packet["exact_allowed_paths"]:
        safe_project_path(root, relative)
    if packet.get("task_id") != record["task_id"] or packet.get("gate_id") != record["gate_id"]:
        raise GovernanceError("VALIDATION_ERROR", "Gate packet IDs do not match action record")
    if current_task_id(root) != record["task_id"] or task_status(root, record["task_id"]) != "active":
        raise GovernanceError("VALIDATION_ERROR", "Pending Gate creation requires the current task to be active")
    if pending_gates(root) or any(gate.get("id") == record["gate_id"] for gate in gates(root)):
        raise GovernanceError("VALIDATION_ERROR", "Pending Gate creation requires no pending or duplicate Gate")
    evidence = record_reference(root, record_path, record["task_id"])
    base = ai_dir(root)
    gates_path = base / "gates.yaml"
    state_path = base / "state.yaml"
    require_allowed_targets(root, record, [gates_path, state_path])
    gate_data = load_yaml(gates_path)
    gate_items = gate_data.setdefault("gates", [])
    if not isinstance(gate_items, list):
        raise GovernanceError("VALIDATION_ERROR", "gates.yaml gates must be a list")
    gate_items.append(
        {
            "id": record["gate_id"],
            "task_id": record["task_id"],
            "title": packet["title"],
            "status": "pending",
            "decision": "pending",
            "approval_phrase": packet["approval_phrase"],
            "rejection_phrase": packet["rejection_phrase"],
            "exact_allowed_paths": packet["exact_allowed_paths"],
            "forbidden_effects": packet["forbidden_effects"],
            "action_schema": "GovernanceAction/v1",
            "creation_action_id": record["action_id"],
            "creation_evidence": evidence,
            "action_request_ids": [record["request_id"]],
            "requested_at": now(),
            "implementation_authorized": False,
            "installation_authorized": False,
            "activation_authorized": False,
            "runtime_tool_enablement_authorized": False,
            "downstream_task_creation_authorized": False,
            "real_project_entry_authorized": False,
        }
    )
    state = load_yaml(state_path)
    state["current_task_id"] = record["task_id"]
    state["current_gate_id"] = record["gate_id"]
    transactional_write_texts(
        base,
        {gates_path: dump_yaml(gate_data) + "\n", state_path: dump_yaml(state) + "\n"},
    )


def decide_pending_gate_action(
    root: Path,
    record: dict,
    record_path: Path,
    decision: str,
) -> None:
    root = root.resolve()
    validate_action_record(root, record, "approve_pending_gate")
    if decision not in {"approved", "rejected"}:
        raise GovernanceError("VALIDATION_ERROR", f"Unsupported Gate decision: {decision}")
    gate = exact_gate(root, record["gate_id"])
    if gate.get("task_id") != record["task_id"] or gate.get("status") != "pending":
        raise GovernanceError("VALIDATION_ERROR", "Gate decision requires the matching pending Gate")
    state_path = ai_dir(root) / "state.yaml"
    state = load_yaml(state_path)
    if state.get("current_gate_id") != record["gate_id"] or task_status(root, record["task_id"]) != "active":
        raise GovernanceError("VALIDATION_ERROR", "Pending Gate projection is stale or contradictory")
    expected_phrase = gate["approval_phrase"] if decision == "approved" else gate["rejection_phrase"]
    if record["latest_user_text"] != expected_phrase:
        raise GovernanceError("AUTHORITY_MISSING", f"Decision text must exactly equal: {expected_phrase}")
    ensure_unused_request(gate, record["request_id"])
    evidence = record_reference(root, record_path, record["task_id"])
    base = ai_dir(root)
    gates_path = base / "gates.yaml"
    task_path = base / "tasks" / f"{record['task_id']}.md"
    graph_path = base / "task_graph.yaml"
    targets = [gates_path, state_path, task_path, graph_path]
    require_allowed_targets(root, record, targets)
    gate_data = load_yaml(gates_path)
    stored_gate = next(item for item in gate_data["gates"] if item.get("id") == record["gate_id"])
    status = "approved_not_started" if decision == "approved" else "rejected"
    stored_gate["status"] = decision
    stored_gate["decision"] = decision
    stored_gate["decided_at"] = now()
    stored_gate["action_request_ids"] = list(stored_gate.get("action_request_ids", [])) + [record["request_id"]]
    if decision == "approved":
        stored_gate["approval_action_id"] = record["action_id"]
        stored_gate["approval_evidence"] = evidence
        stored_gate["execution_status"] = "approved_not_started"
    else:
        stored_gate["rejection_action_id"] = record["action_id"]
        stored_gate["rejection_evidence"] = evidence
    state["current_gate_id"] = None
    graph = load_yaml(graph_path)
    update_task_graph_data(graph, record["task_id"], status)
    task_text = replace_task_status_text(read_text(task_path), status)
    transactional_write_texts(
        base,
        {
            gates_path: dump_yaml(gate_data) + "\n",
            state_path: dump_yaml(state) + "\n",
            task_path: task_text,
            graph_path: dump_yaml(graph) + "\n",
        },
    )


def start_approved_execution_action(root: Path, record: dict, record_path: Path) -> None:
    root = root.resolve()
    validate_action_record(root, record, "execute_approved_gate")
    gate = exact_gate(root, record["gate_id"])
    errors = validate_action_mode(
        "execute_approved_gate",
        gate_status=gate.get("status"),
        explicit_execution_request=record["explicit_execution_request"],
    )
    if errors:
        raise GovernanceError("AUTHORITY_MISSING", "; ".join(errors))
    if gate.get("task_id") != record["task_id"] or task_status(root, record["task_id"]) != "approved_not_started":
        raise GovernanceError("VALIDATION_ERROR", "Execution start requires the matching approved_not_started task")
    expected_phrase = gate.get("execution_phrase") or f"执行已批准的 {record['gate_id']}"
    if record["latest_user_text"] != expected_phrase:
        raise GovernanceError("AUTHORITY_MISSING", f"Execution text must exactly equal: {expected_phrase}")
    ensure_unused_request(gate, record["request_id"])
    evidence = record_reference(root, record_path, record["task_id"])
    base = ai_dir(root)
    gates_path = base / "gates.yaml"
    state_path = base / "state.yaml"
    task_path = base / "tasks" / f"{record['task_id']}.md"
    graph_path = base / "task_graph.yaml"
    targets = [gates_path, state_path, task_path, graph_path]
    require_allowed_targets(root, record, targets)
    gate_data = load_yaml(gates_path)
    stored_gate = next(item for item in gate_data["gates"] if item.get("id") == record["gate_id"])
    stored_gate["execution_action_id"] = record["action_id"]
    stored_gate["execution_evidence"] = evidence
    stored_gate["execution_status"] = "in_progress"
    stored_gate["execution_started_at"] = now()
    stored_gate["implementation_authorized"] = True
    stored_gate["action_request_ids"] = list(stored_gate.get("action_request_ids", [])) + [record["request_id"]]
    state = load_yaml(state_path)
    state["current_gate_id"] = None
    graph = load_yaml(graph_path)
    update_task_graph_data(graph, record["task_id"], "in_progress")
    task_text = replace_task_status_text(read_text(task_path), "in_progress")
    transactional_write_texts(
        base,
        {
            gates_path: dump_yaml(gate_data) + "\n",
            state_path: dump_yaml(state) + "\n",
            task_path: task_text,
            graph_path: dump_yaml(graph) + "\n",
        },
    )


def require_execution_action(root: Path, record: dict, record_path: Path) -> tuple[dict, str]:
    validate_action_record(root, record, "execute_approved_gate")
    gate = exact_gate(root, record["gate_id"])
    errors = validate_action_mode(
        "execute_approved_gate",
        gate_status=gate.get("status"),
        explicit_execution_request=record["explicit_execution_request"],
    )
    if errors:
        raise GovernanceError("AUTHORITY_MISSING", "; ".join(errors))
    if gate.get("task_id") != record["task_id"] or task_status(root, record["task_id"]) != "in_progress":
        raise GovernanceError("VALIDATION_ERROR", "Final validation requires the matching in_progress task")
    expected_phrase = gate.get("execution_phrase") or f"执行已批准的 {record['gate_id']}"
    if record["latest_user_text"] != expected_phrase:
        raise GovernanceError("AUTHORITY_MISSING", f"Execution text must exactly equal: {expected_phrase}")
    return gate, record_reference(root, record_path, record["task_id"])


def validation_fingerprint(root: Path, value: str, allow_external: bool = False) -> dict:
    raw_path = Path(value)
    if allow_external and raw_path.is_absolute():
        path = raw_path.resolve()
    else:
        path = safe_project_path(root, value)
    is_junction = getattr(path, "is_junction", lambda: False)
    if not path.is_file() or path.is_symlink() or is_junction():
        raise GovernanceError("BASELINE_MISSING", f"Validation path must be a regular file: {value}")
    stat = path.stat()
    try:
        recorded_path = path.relative_to(root.resolve()).as_posix()
    except ValueError:
        recorded_path = path.as_posix()
    return {
        "path": recorded_path,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def snapshot_final_validation(
    root: Path,
    record: dict,
    record_path: Path,
    paths: list[str],
    protected_paths: list[str],
) -> str:
    root = root.resolve()
    require_execution_action(root, record, record_path)
    if len(paths) < 2 or not protected_paths:
        raise GovernanceError("VALIDATION_ERROR", "Validation requires target/test paths and protected fingerprints")
    if len(paths) > 256 or len(protected_paths) > 256 or len(paths) != len(set(paths)) or len(protected_paths) != len(set(protected_paths)):
        raise GovernanceError("VALIDATION_ERROR", "Validation paths must be bounded and unique")
    snapshot = {
        "schema": "FinalValidationSnapshot/v1",
        "task_id": record["task_id"],
        "gate_id": record["gate_id"],
        "action_id": record["action_id"],
        "created_at": now_precise(),
        "target_and_test_paths": [validation_fingerprint(root, relative) for relative in paths],
        "protected_global_hashes": [
            validation_fingerprint(root, relative, allow_external=True) for relative in protected_paths
        ],
    }
    encoded = base64.urlsafe_b64encode(canonical_json(snapshot).encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def decode_validation_snapshot(token: str) -> dict:
    if not token or len(token) > 4 * 1024 * 1024:
        raise GovernanceError("VALIDATION_ERROR", "Invalid final-validation snapshot token size")
    try:
        padding = "=" * (-len(token) % 4)
        value = json.loads(
            base64.urlsafe_b64decode(token + padding).decode("utf-8"),
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise GovernanceError("VALIDATION_ERROR", "Invalid final-validation snapshot token") from exc
    if not isinstance(value, dict):
        raise GovernanceError("VALIDATION_ERROR", "Final-validation snapshot must be an object")
    validate_closed_fields(value, VALIDATION_SNAPSHOT_FIELDS, "FinalValidationSnapshot/v1")
    if value.get("schema") != "FinalValidationSnapshot/v1":
        raise GovernanceError("VALIDATION_ERROR", "Unsupported final-validation snapshot schema")
    return value


def bind_final_validation(
    root: Path,
    record: dict,
    record_path: Path,
    token: str,
    command_record: dict,
    command_path: Path,
    manifest_relative: str,
) -> None:
    root = root.resolve()
    _, action_evidence = require_execution_action(root, record, record_path)
    command_evidence = record_reference(root, command_path, record["task_id"])
    validate_closed_fields(command_record, VALIDATION_COMMAND_FIELDS, "FinalValidationCommand/v1")
    if command_record.get("exit_code") != 0 or not isinstance(command_record.get("test_count"), int) or command_record["test_count"] <= 0:
        raise GovernanceError("VALIDATION_ERROR", "Final validation requires exit_code 0 and positive test_count")
    argv = command_record.get("exact_command_argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
        raise GovernanceError("VALIDATION_ERROR", "exact_command_argv must be a non-empty string list")
    snapshot = decode_validation_snapshot(token)
    if snapshot["task_id"] != record["task_id"] or snapshot["gate_id"] != record["gate_id"]:
        raise GovernanceError("VALIDATION_ERROR", "Snapshot authority IDs do not match bind action")
    try:
        snap_at = _dt.datetime.fromisoformat(snapshot["created_at"])
        started = _dt.datetime.fromisoformat(command_record["validation_started_at"])
        completed = _dt.datetime.fromisoformat(command_record["validation_completed_at"])
    except (TypeError, ValueError) as exc:
        raise GovernanceError("VALIDATION_ERROR", "Validation timestamps must be ISO-8601") from exc
    if not (snap_at <= started <= completed):
        raise GovernanceError("VALIDATION_ERROR", "Validation timestamps must follow snapshot <= start <= completion")
    for group in ("target_and_test_paths", "protected_global_hashes"):
        entries = snapshot[group]
        if not isinstance(entries, list):
            raise GovernanceError("VALIDATION_ERROR", f"Snapshot field must be a list: {group}")
        for expected in entries:
            if not isinstance(expected, dict) or set(expected) != {"path", "sha256", "size", "mtime_ns"}:
                raise GovernanceError("VALIDATION_ERROR", f"Malformed validation fingerprint in {group}")
            actual = validation_fingerprint(root, expected["path"], allow_external=group == "protected_global_hashes")
            if actual != expected:
                raise GovernanceError("STALE_FINAL_VALIDATION", f"Fingerprint changed after snapshot: {expected['path']}")
    manifest_path = safe_project_path(root, manifest_relative)
    require_allowed_targets(root, record, [manifest_path])
    manifest_reference = record_reference(root, manifest_path, record["task_id"])
    if not manifest_reference.endswith((".yaml", ".yml")):
        raise GovernanceError("VALIDATION_ERROR", "Final validation manifest must be YAML evidence")
    if manifest_path.exists():
        raise GovernanceError("CONFLICT", f"Final validation manifest is immutable: {manifest_relative}")
    manifest = {
        "schema": "FinalValidationManifest/v1",
        "status": "bound",
        "task_id": record["task_id"],
        "gate_id": record["gate_id"],
        "snapshot_created_at": snapshot["created_at"],
        "validation_started_at": command_record["validation_started_at"],
        "validation_completed_at": command_record["validation_completed_at"],
        "exact_command_argv": argv,
        "exit_code": 0,
        "test_count": command_record["test_count"],
        "target_and_test_paths": snapshot["target_and_test_paths"],
        "protected_global_hashes": snapshot["protected_global_hashes"],
        "binding_action_id": record["action_id"],
        "action_evidence": action_evidence,
        "command_evidence": command_evidence,
        "bound_at": now_precise(),
    }
    transactional_write_texts(ai_dir(root), {manifest_path: dump_yaml(manifest) + "\n"})


def git_status(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--short"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        return f"git status unavailable: {exc}"
    if result.returncode != 0:
        return "not a git repository"
    return result.stdout.strip() or "clean"


def append_task_graph_status(root: Path, task_id: str, status: str, note: str) -> None:
    path = ai_dir(root) / "task_graph.yaml"
    data = load_yaml(path)
    tasks = data.setdefault("tasks", [])
    if not isinstance(tasks, list):
        tasks = []
        data["tasks"] = tasks
    for task in tasks:
        if isinstance(task, dict) and task.get("id") == task_id:
            task["status"] = status
            task["updated_at"] = now()
            task["note"] = note
            break
    else:
        tasks.append({"id": task_id, "status": status, "updated_at": now(), "note": note})
    write_yaml(path, data)
