from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path


REQUIRED_FILES = [
    "PROJECT.md", "NON_GOALS.md", "ARCHITECTURE.md", "CONTRACTS.md", "CODING_STANDARDS.md",
    "CONVENTIONS.md", "CODEMAP.md", "PROGRESS.md", "QUALITY_GATES.md", "ACCEPTANCE.md",
    "DECISIONS.md", "KNOWN_ISSUES.md", "state.yaml", "task_graph.yaml", "gates.yaml", "HANDOFF.md",
]
TASK_STATUSES = {"pending", "active", "approved_not_started", "in_progress", "blocked", "completed", "rejected"}


class GovernanceError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def now_precise() -> str:
    return datetime.now().astimezone().isoformat()


def project_root_arg() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", help="Project root containing .ai")
    return parser


def ai_dir(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / ".ai"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def file_fingerprint(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


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
            entries.append({
                "path": str(path), "staged": str(staged), "backup": str(backup),
                "existed": path.exists(), "fingerprint": file_fingerprint(path),
            })
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


def historical_task_inventory_errors(root: Path, exclude_task_id: str | None = None) -> list[str]:
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
            errors.append(f"Historical task status missing or invalid: {task_id}")
        if len(matches) != 1:
            errors.append(f"Historical task must appear exactly once in task graph: {task_id} (found {len(matches)})")
        elif status is not None and matches[0].get("status") != status:
            errors.append(f"Historical task status mismatch: {task_id} task={status} task_graph={matches[0].get('status', 'missing')}")
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
    elif current_matches and (current_matches[0].get("task_id") != task_id or current_matches[0].get("status") != "pending"):
        errors.append(f"Current gate projection is contradictory: {current_gate_id}")
    task_pending = [gate for gate in pending_gates(root) if gate.get("task_id") == task_id]
    if task_pending and not current_gate_id:
        errors.append(f"Pending gate for current task is not current_gate_id: {task_pending[0].get('id')}")
    if current_gate_id and not task_pending:
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
    errors.extend(historical_task_inventory_errors(root, exclude_task_id=task_id))
    return errors
