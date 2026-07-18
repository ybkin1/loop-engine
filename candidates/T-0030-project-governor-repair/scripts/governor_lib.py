from __future__ import annotations

import argparse
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


def today() -> str:
    return _dt.date.today().isoformat()


def now() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


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
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


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
