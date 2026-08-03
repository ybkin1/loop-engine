from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

REQUIRED_FILES = [
    "PROJECT.md", "NON_GOALS.md", "ARCHITECTURE.md", "CONTRACTS.md", "CODING_STANDARDS.md",
    "CONVENTIONS.md", "CODEMAP.md", "PROGRESS.md", "QUALITY_GATES.md", "ACCEPTANCE.md",
    "DECISIONS.md", "KNOWN_ISSUES.md", "state.yaml", "task_graph.yaml", "gates.yaml", "HANDOFF.md",
]
TASK_STATUSES = {"pending", "active", "approved_not_started", "in_progress", "blocked", "completed", "rejected"}
# T-0046: Standardized error codes
ERROR_CODES = {
    "CURRENT_TASK_FILE_MISSING": "Current task file does not exist",
    "CURRENT_TASK_NOT_IN_GRAPH": "Current task not found in task_graph.yaml",
    "TASK_GRAPH_NODE_WITHOUT_TASK_FILE": "Task in graph has no corresponding task file",
    "TASK_STATUS_MISMATCH": "Task file status differs from task_graph status",
    "GATE_TASK_MISMATCH": "Gate task_id does not match state current_task_id",
    "GATE_EXECUTION_STATUS_MISSING": "Approved gate missing execution_status",
    "HANDOFF_STATE_MISMATCH": "HANDOFF.md content differs from state.yaml",
    "CONTINUITY_SOURCE_DRIFT": "Continuity source file hash differs from recorded",
}

# Legacy/historical error classification
LEGACY_ERROR_PREFIXES = ("Historical task",)



class GovernanceError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def now_precise() -> str:
    return datetime.now().astimezone().isoformat()


def project_root_arg() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", help="Project root containing .ai")
    parser.add_argument("--repair", action="store_true",
                        help="Auto-repair continuity hash drift instead of blocking")
    return parser


def ai_dir(project_root: str | Path) -> Path:
    # Normalize defensively: os.path.normpath guards against shell-level
    # backslash-stripping / colon-mangling before Path.resolve() canonicalises.
    return Path(os.path.normpath(str(project_root))).resolve() / ".ai"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def file_fingerprint(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


# T-0089 U7: reliable evidence delivery — idempotency + backoff retry + stale recovery
TRANSACTION_MARKER_NAME = ".project-governor-transaction.json"
IDEMPOTENCY_TABLE_NAME = ".project-governor-idempotency.json"
# Settle interval for the no-concurrent-writer double read during stale recovery.
_STALE_CHECK_SETTLE_SECONDS = 0.05


@dataclass
class RetryPolicy:
    """Exponential backoff policy for transactional writes (T-0089 U7)."""

    max_attempts: int = 3
    backoff_base_seconds: float = 1.0
    backoff_multiplier: float = 2.0


@dataclass
class TransactionResult:
    """Outcome of a transactional write (T-0089 U7).

    ``written`` lists paths actually (re)written; ``skipped`` lists paths
    deduplicated by the idempotency table; ``attempts`` counts attempts used
    when a retry policy is active.
    """

    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    attempts: int = 1


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def transactional_write_texts(
    base: Path,
    changes: dict[Path, str],
    *,
    idempotent: bool = False,
    retry: object = None,
    stale_timeout_seconds: float | None = None,
) -> TransactionResult | None:
    """Atomically write several files with journal-based rollback (T-0089 U7).

    Backward-compatible superset of the original transactional write; with all
    defaults it behaves exactly like the legacy implementation and returns None.

    - ``idempotent=True``: per-path content fingerprint (sha256) is recorded in
      an idempotency table; resubmitting identical content skips the write and
      is reported through ``TransactionResult.skipped`` (no duplicate records).
    - ``retry``: ``RetryPolicy`` / dict / bool — exponential backoff retries for
      transient failures (IO errors, concurrent-modification conflicts). The
      final error is re-raised once ``max_attempts`` is exhausted; failures are
      never silently dropped. Default ``None``/``False`` disables retries.
    - ``stale_timeout_seconds``: when set, an unresolved journal marker older
      than the threshold is reset (marked stale, leftovers cleaned) after
      verifying no concurrent writer; fresh or actively-written markers are
      refused with a clear error.
    """
    policy = _coerce_retry_policy(retry)
    if policy is None:
        result = _transactional_write_texts_once(
            base, changes,
            idempotent=idempotent,
            stale_timeout_seconds=stale_timeout_seconds,
        )
        return result if idempotent else None
    last_error: BaseException | None = None
    for attempt in range(1, policy.max_attempts + 1):
        transaction_id = uuid.uuid4().hex
        try:
            result = _transactional_write_texts_once(
                base, changes,
                idempotent=idempotent,
                stale_timeout_seconds=stale_timeout_seconds,
                transaction_id=transaction_id,
            )
            result.attempts = attempt
            return result
        except (OSError, RuntimeError) as exc:
            last_error = exc
            if attempt < policy.max_attempts:
                _recover_marker_for_retry(base, transaction_id, stale_timeout_seconds)
                _sleep(policy.backoff_base_seconds * (policy.backoff_multiplier ** (attempt - 1)))
    if last_error is None:
        raise RuntimeError("Retry policy exhausted without an underlying error")
    raise last_error


def _coerce_retry_policy(retry: object) -> RetryPolicy | None:
    if retry is None or retry is False:
        return None
    if retry is True:
        return RetryPolicy()
    if isinstance(retry, RetryPolicy):
        policy = retry
    elif isinstance(retry, dict):
        unknown = set(retry) - {"max_attempts", "backoff_base_seconds", "backoff_multiplier"}
        if unknown:
            raise GovernanceError("INVALID_RETRY_POLICY", f"Unknown retry policy keys: {sorted(unknown)}")
        policy = RetryPolicy(**dict(retry))
    else:
        raise GovernanceError(
            "INVALID_RETRY_POLICY",
            f"retry must be RetryPolicy, dict, bool or None, got {type(retry).__name__}",
        )
    if not isinstance(policy.max_attempts, int) or isinstance(policy.max_attempts, bool) or policy.max_attempts < 1:
        raise GovernanceError("INVALID_RETRY_POLICY", "retry.max_attempts must be an integer >= 1")
    if not isinstance(policy.backoff_base_seconds, (int, float)) or isinstance(policy.backoff_base_seconds, bool) or policy.backoff_base_seconds < 0:
        raise GovernanceError("INVALID_RETRY_POLICY", "retry.backoff_base_seconds must be a number >= 0")
    if not isinstance(policy.backoff_multiplier, (int, float)) or isinstance(policy.backoff_multiplier, bool) or policy.backoff_multiplier < 1:
        raise GovernanceError("INVALID_RETRY_POLICY", "retry.backoff_multiplier must be a number >= 1")
    return policy


def _transactional_write_texts_once(
    base: Path,
    changes: dict[Path, str],
    *,
    idempotent: bool,
    stale_timeout_seconds: float | None,
    transaction_id: str | None = None,
) -> TransactionResult:
    marker = base / TRANSACTION_MARKER_NAME
    if marker.exists():
        if stale_timeout_seconds is None:
            raise RuntimeError(f"Unresolved Project Governor transaction: {marker}")
        _recover_stale_transaction(base, timeout_seconds=stale_timeout_seconds)
    if transaction_id is None:
        transaction_id = uuid.uuid4().hex
    table = _load_idempotency_table(base) if idempotent else {}
    planned: list[tuple[Path, str, str]] = []
    skipped: list[str] = []
    for path, text in changes.items():
        fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()
        record = table.get(str(path))
        if idempotent and isinstance(record, dict) and record.get("fingerprint") == fingerprint:
            skipped.append(str(path))
            continue
        planned.append((path, text, fingerprint))
    if not planned:
        return TransactionResult(written=[], skipped=skipped)
    entries = []
    committed = []
    recovered = True
    try:
        for path, text, _fingerprint in planned:
            path.parent.mkdir(parents=True, exist_ok=True)
            staged = path.with_name(f".{path.name}.{transaction_id}.tmp")
            backup = path.with_name(f".{path.name}.{transaction_id}.bak")
            staged.write_text(text, encoding="utf-8", newline="\n")
            if path.exists():
                shutil.copy2(path, backup)
            entries.append({
                "path": str(path), "staged": str(staged), "backup": str(backup),
                "existed": path.exists(), "fingerprint": file_fingerprint(path),
            })
        journal = {
            "transaction_id": transaction_id,
            "entries": entries,
            "committed": [],
            "created_at": now_precise(),
        }
        write_text(marker, json.dumps(journal, indent=2))
        for entry in entries:
            path = Path(entry["path"])
            if file_fingerprint(path) != entry["fingerprint"]:
                raise RuntimeError(f"Concurrent modification detected: {path}")
            os.replace(entry["staged"], entry["path"])
            committed.append(entry)
            journal["committed"].append(entry["path"])
            write_text(marker, json.dumps(journal, indent=2))
        if idempotent and planned:
            for path, _text, fingerprint in planned:
                table[str(path)] = {
                    "fingerprint": fingerprint,
                    "written_at": now_precise(),
                    "transaction_id": transaction_id,
                }
            _save_idempotency_table(base, table)
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
    return TransactionResult(written=[str(path) for path, _text, _fp in planned], skipped=skipped)


def _load_idempotency_table(base: Path) -> dict:
    path = base / IDEMPOTENCY_TABLE_NAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Corrupt idempotency table (write refused): {path}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"Corrupt idempotency table (write refused): {path}")
    return data


def _save_idempotency_table(base: Path, table: dict) -> None:
    path = base / IDEMPOTENCY_TABLE_NAME
    staged = path.with_name(f".{path.name}.tmp")
    staged.write_text(json.dumps(table, indent=2), encoding="utf-8")
    os.replace(staged, path)


def _parse_transaction_journal(marker: Path) -> dict:
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Corrupt transaction journal (reset refused): {marker}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"Corrupt transaction journal (reset refused): {marker}")
    return data


def _journal_is_stale(journal: dict, marker: Path, timeout_seconds: float) -> bool:
    created_raw = journal.get("created_at")
    created = None
    if isinstance(created_raw, str) and created_raw:
        try:
            created = datetime.fromisoformat(created_raw)
        except ValueError:
            created = None
        if created is not None and created.tzinfo is None:
            created = created.astimezone()
    if created is None:
        # Legacy journals predate created_at: fall back to file mtime.
        created = datetime.fromtimestamp(marker.stat().st_mtime).astimezone()
    age = (datetime.now().astimezone() - created).total_seconds()
    return age > timeout_seconds


def _recover_stale_transaction(base: Path, *, timeout_seconds: float) -> None:
    marker = base / TRANSACTION_MARKER_NAME
    if not marker.exists():
        return
    first_bytes = marker.read_bytes()
    journal = _parse_transaction_journal(marker)
    if not _journal_is_stale(journal, marker, timeout_seconds):
        raise RuntimeError(
            f"Active Project Governor transaction in progress: {marker} "
            "(reset refused: journal is not stale)"
        )
    # No-concurrent-writer pre-check: the journal must be byte-stable across a
    # settle interval, otherwise another writer is still committing.
    _sleep(_STALE_CHECK_SETTLE_SECONDS)
    if marker.read_bytes() != first_bytes:
        raise RuntimeError(
            f"Concurrent writer detected while resetting stale transaction: {marker}"
        )
    journal["status"] = "stale"
    journal["marked_stale_at"] = now_precise()
    write_text(marker, json.dumps(journal, indent=2))
    for entry in journal.get("entries", []):
        if isinstance(entry, dict):
            Path(entry["staged"]).unlink(missing_ok=True)
            Path(entry["backup"]).unlink(missing_ok=True)
    marker.unlink(missing_ok=True)


def _recover_marker_for_retry(
    base: Path, owned_transaction_id: str, stale_timeout_seconds: float | None
) -> None:
    marker = base / TRANSACTION_MARKER_NAME
    if not marker.exists():
        return
    journal = _parse_transaction_journal(marker)
    if journal.get("transaction_id") == owned_transaction_id:
        # Leftover from this process's failed attempt (rollback failure):
        # clean it, still guarded by the no-concurrent-writer double read.
        first_bytes = marker.read_bytes()
        _sleep(_STALE_CHECK_SETTLE_SECONDS)
        if marker.read_bytes() != first_bytes:
            raise RuntimeError(
                f"Concurrent writer detected while cleaning transaction marker: {marker}"
            )
        for entry in journal.get("entries", []):
            if isinstance(entry, dict):
                Path(entry["staged"]).unlink(missing_ok=True)
                Path(entry["backup"]).unlink(missing_ok=True)
        marker.unlink(missing_ok=True)
    elif stale_timeout_seconds is not None:
        _recover_stale_transaction(base, timeout_seconds=stale_timeout_seconds)
    # else: another actor's active marker — leave untouched; the next attempt
    # surfaces "Unresolved Project Governor transaction" and retries exhaust
    # with a clear error rather than destroying foreign state.


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def render_json_block(name: str, value: dict) -> str:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    return f"<!-- PROJECT-GOVERNOR-{name}-BEGIN -->\n```json\n{payload}\n```\n<!-- PROJECT-GOVERNOR-{name}-END -->"


def _unique_json_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


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
        value = json.loads(payload[len("```json"):-3].strip(), object_pairs_hook=_unique_json_pairs)
    except (json.JSONDecodeError, ValueError) as exc:
        raise GovernanceError("VALIDATION_ERROR", f"HANDOFF {name.lower()} block is invalid JSON") from exc
    if not isinstance(value, dict):
        raise GovernanceError("VALIDATION_ERROR", f"HANDOFF {name.lower()} block must be an object")
    return value


def safe_project_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or len(relative) > 4096 or "\x00" in relative:
        raise GovernanceError("SCOPE_VIOLATION", f"Path must be project-relative: {relative!r}")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ":" in relative:
        raise GovernanceError("SCOPE_VIOLATION", f"Path must be canonical project-relative: {relative!r}")
    try:
        root = root.resolve()
        path = (root / relative_path).resolve()
        path.relative_to(root)
    except (OSError, ValueError) as exc:
        raise GovernanceError("SCOPE_VIOLATION", f"Path escapes project root: {relative!r}") from exc
    cursor = root
    for part in relative_path.parts:
        cursor = cursor / part
        is_junction = getattr(cursor, "is_junction", lambda: False)
        if cursor.exists() and (cursor.is_symlink() or is_junction()):
            raise GovernanceError("SCOPE_VIOLATION", f"Reparse/symlink path is forbidden: {relative}")
    return path


def _yaml_module():
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise GovernanceError("YAML_RUNTIME_REQUIRED", "PyYAML is required by this isolated candidate") from exc
    return yaml


def load_yaml(path: Path):
    if not path.exists():
        return {}
    yaml = _yaml_module()

    class UniqueKeyLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise GovernanceError("YAML_DUPLICATE_KEY", f"Duplicate YAML key: {key}")
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except GovernanceError:
        raise
    except Exception as exc:
        raise GovernanceError("YAML_INVALID", f"Invalid YAML: {path}") from exc
    # T-0059 F-0055-010: Validate schema_version
    if isinstance(value, dict) and "schema_version" in value:
        import logging
        if value.get("schema_version") != 1:
            logging.getLogger("governor_lib").warning(
                "Schema version mismatch in %s: expected 1, got %s. Migration may be required.",
                str(path), value.get("schema_version")
            )
    return value or {}


def dump_yaml(value) -> str:
    yaml = _yaml_module()
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, default_flow_style=False).rstrip("\n")


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
    return task_status_from_text(read_text(ai_dir(root) / "tasks" / f"{task_id}.md")) if task_id else None


def task_graph_entries(root: Path, task_id: str) -> list[dict]:
    tasks = load_yaml(ai_dir(root) / "task_graph.yaml").get("tasks", [])
    return [item for item in tasks if isinstance(item, dict) and item.get("id") == task_id] if isinstance(tasks, list) else []


def evidence_path_exists(base: Path, value) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value)
    return (path if path.is_absolute() else base.parent / path).exists()



# T-0059 F-0055-011: Single source of truth - unified state loading
def load_unified_state(root):
    """Load governance state from authoritative sources.
    Hierarchy: state.yaml > gates.yaml > task_graph.yaml > HANDOFF.md (projection)."""
    base = ai_dir(root)
    state = load_yaml(base / "state.yaml")
    all_gates = gates(root)
    all_tasks = [t for t in task_graph_entries(root) if isinstance(t, dict)]
    task_id = state.get("current_task_id")
    task_id = None if task_id in (None, "", "null") else task_id
    task_status_val = None
    if task_id:
        for t in all_tasks:
            if t.get("id") == task_id:
                task_status_val = t.get("status")
                break
    current_gate_id = state.get("current_gate_id")
    current_gate_id = None if current_gate_id in (None, "", "null") else current_gate_id
    approved_gate = None
    if task_id:
        matches = [g for g in all_gates if isinstance(g, dict) and g.get("task_id") == task_id and g.get("status") == "approved"]
        active = [m for m in matches if m.get("execution_status") in {"approved_not_started", "in_progress"}]
        approved_gate = active[-1] if active else (matches[-1] if matches else None)
    return {"state": state, "gates": all_gates, "tasks": all_tasks, "task_id": task_id, "task_status": task_status_val, "current_gate_id": current_gate_id, "approved_gate": approved_gate, "phase": state.get("current_phase", "")}

def historical_task_inventory_errors(root: Path, exclude_task_id: str | None = None) -> list[str]:
    """T-0046: Historical task mismatches are classified as legacy warnings.

    Current task errors are hard errors (handled by governance_invariant_errors).
    Historical task inconsistencies from before T-0046 are legacy issues
    that should be recorded as correction evidence, not block current work.
    """
    errors = []
    graph = load_yaml(ai_dir(root) / "task_graph.yaml").get("tasks", [])
    graph = graph if isinstance(graph, list) else []
    for path in sorted((ai_dir(root) / "tasks").glob("T-*.md")):
        task_id = path.stem
        if task_id == exclude_task_id:
            continue
        status = task_status_from_text(read_text(path))
        matches = [item for item in graph if isinstance(item, dict) and item.get("id") == task_id]
        if status is None:
            # Legacy: task file exists but status is not parseable
            errors.append(f"[legacy] Historical task status missing or invalid: {task_id}")
        if len(matches) != 1:
            errors.append(f"Historical task must appear exactly once in task graph: {task_id} (found {len(matches)})")
        elif status is not None and matches[0].get("status") != status:
            # Legacy: task file and task_graph disagree on status
            errors.append(f"[legacy] Historical task status mismatch: {task_id} task={status} task_graph={matches[0].get('status', 'missing')}")
    return errors


def gates(root: Path) -> list[dict]:
    items = load_yaml(ai_dir(root) / "gates.yaml").get("gates", [])
    return items if isinstance(items, list) else []


def pending_gates(root: Path) -> list[dict]:
    return [gate for gate in gates(root) if isinstance(gate, dict) and gate.get("status") == "pending"]


def governance_invariant_errors(root: Path) -> list[str]:
    errors = []
    base = ai_dir(root)
    state = load_yaml(base / "state.yaml")
    task_id = current_task_id(root)
    if not task_id:
        return errors
    status = task_status(root, task_id)
    entries = task_graph_entries(root, task_id)
    if status is None:
        errors.append(f"Current task status missing or invalid: {task_id}")
    if len(entries) != 1:
        errors.append(f"Current task must appear exactly once in task graph: {task_id} (found {len(entries)})")
    elif status is not None and entries[0].get("status") != status:
        errors.append(f"Task status mismatch: {task_id} task={status} task_graph={entries[0].get('status', 'missing')}")
    current_gate_id = state.get("current_gate_id")
    current_gate_id = None if current_gate_id in (None, "null", "") else current_gate_id
    current_matches = [gate for gate in gates(root) if gate.get("id") == current_gate_id]
    if current_gate_id and len(current_matches) != 1:
        errors.append(f"current_gate_id does not identify exactly one gate: {current_gate_id}")
    elif current_matches:
        gate = current_matches[0]
        gate_status = gate.get("status", "")
        gate_task_id = gate.get("task_id", "")
        gate_exec_status = gate.get("execution_status", "")
        # T-0046 fix: gate lifecycle semantics
        # current_gate_id must match current task
        if gate_task_id and gate_task_id != task_id:
            errors.append(f"GATE_TASK_MISMATCH: current_gate_id {current_gate_id} belongs to {gate_task_id}, not {task_id}")
        elif gate_status == "pending":
            pass  # Valid: waiting for user decision
        elif gate_status == "approved" and gate_exec_status in ("approved_not_started", "in_progress"):
            pass  # Valid: approved and executing
        elif gate_status == "approved" and gate_exec_status == "completed":
            pass  # Valid: approved and completed (not active but not contradictory)
        elif gate_status == "approved" and not gate_exec_status:
            pass  # Valid: legacy approved gate
        elif gate_status in ("rejected", "blocked"):
            errors.append(f"Current gate is {gate_status}: {current_gate_id}")
        else:
            errors.append(f"Current gate projection is contradictory: {current_gate_id}")
    task_pending = [gate for gate in pending_gates(root) if gate.get("task_id") == task_id]
    if task_pending and not current_gate_id:
        errors.append(f"Pending gate for current task is not current_gate_id: {task_pending[0].get('id')}")
    # T-0046 fix: current_gate_id pointing to approved+in_progress is valid, no pending needed
    if current_gate_id and not task_pending:
        current_gate_obj = current_matches[0] if current_matches else None
        if current_gate_obj and current_gate_obj.get("status") == "approved":
            pass  # Approved gate is valid without pending
        elif current_gate_obj and current_gate_obj.get("status") != "pending":
            errors.append(f"current_gate_id has no pending gate for current task: {current_gate_id}")
    task_gates = [gate for gate in gates(root) if gate.get("task_id") == task_id]
    approved = [gate for gate in task_gates if gate.get("status") == "approved"]
    if status in {"approved_not_started", "in_progress"}:
        if not approved:
            errors.append(f"{status} requires an approved gate for current task: {task_id}")
        elif not any(evidence_path_exists(base, gate.get("approval_evidence")) for gate in approved):
            errors.append(f"{status} requires approval evidence for current task: {task_id}")
    if status == "in_progress" and not any(evidence_path_exists(base, gate.get("execution_evidence")) for gate in approved):
        errors.append(f"in_progress requires execution evidence for current task: {task_id}")
    # v3.5: Compile evidence check — S4+ tasks must have compile output as evidence
    current_phase = state.get("current_phase", "")
    if status == "in_progress" and current_phase in (
        "S4-implementation", "S5-quality", "S6-delivery",
        "S7-integration", "S8-functional-test", "S9-fix-optimize",
        "S10-performance", "S11-maintenance",
    ):
        compile_evidence = base / "evidence" / task_id / "compile-evidence.json"
        if not compile_evidence.exists():
            errors.append(
                f"COMPILE_EVIDENCE_MISSING: Task {task_id} at phase {current_phase} "
                f"requires compile evidence at {compile_evidence.relative_to(base)}. "
                "Run .ai/checkers/compile_gate.py to generate."
            )
    errors.extend(historical_task_inventory_errors(root, exclude_task_id=task_id))

    # ── HANDOFF consistency check (v3.5) ─────────────────────────────────
    handoff_text = read_text(base / "HANDOFF.md")
    if handoff_text:
        # Detect stale prose that contradicts structured state
        stale_patterns = [
            ("Product implementation has not started", "HANDOFF contains stale 'implementation not started' claim"),
            ("implementation has not started", "HANDOFF contains stale 'implementation not started' claim"),
            ("The design baseline is approved, promoted and frozen", "HANDOFF references legacy baseline wording"),
        ]
        for pattern, warning in stale_patterns:
            if pattern.lower() in handoff_text.lower():
                errors.append(f"[warn] HANDOFF_STALE_CONTENT: {warning}. Run close_session.py to regenerate.")

    # ── PROJECT.md anchor check (v3.5) ───────────────────────────────────
    project_md = read_text(base / "PROJECT.md")
    if project_md:
        impl_started = state.get("implementation_started")
        if impl_started and "implementation has not started" in project_md.lower():
            errors.append(
                "[warn] PROJECT_ANCHOR_STALE: .ai/PROJECT.md claims 'implementation has not started' "
                "but state.yaml has implementation_started=true. Update PROJECT.md to reflect current phase."
            )

    return errors


# ============================================================================
# T-0109 F2-2 状态写入收敛：统一经 governor_lib 事务写 + projection 刷新
# ============================================================================
#
# 状态五写（state.yaml / task_graph.yaml / 任务卡 Status / HANDOFF / PROGRESS）
# 收敛为 state.yaml 权威 + 派生视图（.ai/views/state-view.yaml）：
# - 写路径统一经 `write_state_files`（内部 = transactional_write_texts 事务写
#   + 派生视图刷新）；close_session 等既有事务写路径已天然满足。
# - 状态转换（state_machine.atomic_write_state）触发 projection 刷新。
# - 派生视图是只读派生产物，不参与语义哈希（T-0108 F2-1 约束保持）。

# 状态相关路径（静态检查「仅 governor_lib 写 state 相关路径」的覆盖清单）
STATE_RELATED_FILES = (
    "state.yaml",
    "task_graph.yaml",
    "HANDOFF.md",
    "PROGRESS.md",
    # tasks/{id}.md（任务卡 Status 权威源是 task_graph，任务卡为派生视图）
)


def refresh_state_view(root: str | Path) -> bool:
    """刷新派生状态视图 `.ai/views/state-view.yaml`（F2-2 projection 刷新）。

    复用 T-0108 的 ``loop_core.projection_engine.write_state_view``；
    独立运行环境（loop_core 不可导入）时显式告警并返回 False——
    刷新失败不阻断（权威写已提交），但绝不静默吞错。

    Returns:
        True 刷新成功；False loop_core 不可用或刷新失败（已告警）。
    """
    root_p = Path(os.path.normpath(str(root))).resolve()
    try:
        # loop_core 以仓库根为包根；独立运行（如 hooks 直接调用）时补路径
        if str(root_p) not in sys.path:
            sys.path.insert(0, str(root_p))
        from loop_core.projection_engine import write_state_view
        write_state_view(root_p)
        return True
    except Exception as exc:  # noqa: BLE001 — 防御：刷新失败必须显式上报
        import logging
        logging.getLogger("governor_lib").warning(
            "STATE_VIEW_REFRESH_FAILED: %s — derived view not refreshed "
            "(authoritative write already committed)", exc
        )
        return False


def write_state_files(
    root: str | Path,
    changes: dict[Path, str],
    *,
    refresh_projection: bool = True,
    **kwargs,
) -> TransactionResult | None:
    """F2-2 收敛写入入口：state 相关路径统一经 governor_lib 事务写。

    ``changes`` 的每个路径都必须是 ``.ai/`` 下的 state 相关文件
    （state.yaml / task_graph.yaml / HANDOFF.md / PROGRESS.md /
    tasks/{id}.md）；事务写成功后默认刷新派生视图（projection 刷新）。

    除 ``refresh_projection`` 外，其余关键字参数原样透传给
    ``transactional_write_texts``（idempotent / retry / stale_timeout_seconds）。
    """
    base = ai_dir(root)
    changes = {Path(p) if not isinstance(p, Path) else p: text for p, text in changes.items()}
    for path in changes:
        try:
            path.resolve().relative_to(base.resolve())
        except (OSError, ValueError) as exc:
            raise GovernanceError(
                "SCOPE_VIOLATION",
                f"write_state_files 仅接受 .ai/ 下 state 相关路径: {path}",
            ) from exc
        rel = path.resolve().relative_to(base.resolve()).as_posix()
        if not (
            rel in STATE_RELATED_FILES
            or rel.startswith("tasks/")
        ):
            raise GovernanceError(
                "SCOPE_VIOLATION",
                f"write_state_files 仅接受 state 相关路径（state.yaml/task_graph/"
                f"HANDOFF/PROGRESS/tasks/*.md）: {rel}",
            )
    result = transactional_write_texts(base, changes, **kwargs)
    if result is None:
        # 兼容默认（非 idempotent）模式：底层返回 None 表示写入完成
        result = TransactionResult(written=[str(p) for p in changes])
    if refresh_projection:
        refresh_state_view(root)
    return result
