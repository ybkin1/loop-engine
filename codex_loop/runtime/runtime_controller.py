from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class RuntimeState(str, Enum):
    NOT_A_PROJECT = "NOT_A_PROJECT"
    UNINITIALIZED_PROJECT = "UNINITIALIZED_PROJECT"
    LOOP_PROJECT_READY = "LOOP_PROJECT_READY"
    LOOP_PROJECT_DRIFTED = "LOOP_PROJECT_DRIFTED"
    NO_ACTIVE_TASK = "NO_ACTIVE_TASK"
    WORK_PACKAGE_PROPOSAL = "WORK_PACKAGE_PROPOSAL"
    USER_APPROVAL_REQUIRED = "USER_APPROVAL_REQUIRED"
    ACTIVE_TASK = "ACTIVE_TASK"
    DEVELOPER_EXECUTION = "DEVELOPER_EXECUTION"
    REVIEW = "REVIEW"
    REPAIR = "REPAIR"
    ACCEPTANCE = "ACCEPTANCE"
    CLOSED = "CLOSED"


class RuntimeControllerError(RuntimeError):
    """A fail-closed controller decision."""


@dataclass(frozen=True)
class ExecutionContext:
    actor_id: str
    role_id: str
    caller_class: str
    task_id: str | None = None
    execution_id: str | None = None
    session_id: str | None = None
    capability_id: str | None = None


@dataclass(frozen=True)
class ExecutionCapability:
    capability_id: str
    task_id: str
    execution_id: str
    assigned_actor_id: str
    allowed_paths: tuple[str, ...]
    issued_at: str
    idempotency_key: str


@dataclass(frozen=True)
class RuntimeSnapshot:
    runtime_state: str
    task_id: str | None
    gate_id: str | None
    execution_id: str | None
    capability_id: str | None
    proposal_hash: str | None
    checkpoint_ref: str | None = None


GOVERNANCE_FILES = {
    ".ai/state.yaml",
    ".ai/gates.yaml",
    ".ai/task_graph.yaml",
    ".ai/HANDOFF.md",
    ".ai/project_continuity.yaml",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest().upper()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


class RuntimeController:
    """Single authority for onboarding, proposal, approval, and authorization."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.meta_dir = self.root / ".ai" / "runtime"
        self.snapshot_path = self.meta_dir / "runtime-state.json"
        self.journal_path = self.meta_dir / "runtime-events.jsonl"
        self.capability_path = self.meta_dir / "capability.json"
        self.checkpoint_path = self.meta_dir / "checkpoint.json"

    def inspect(self) -> RuntimeState:
        if not self.root.is_dir():
            return RuntimeState.NOT_A_PROJECT
        required = [self.root / ".ai" / name for name in ("state.yaml", "gates.yaml", "task_graph.yaml")]
        if not any(self.root.iterdir()):
            return RuntimeState.NOT_A_PROJECT
        if not all(path.exists() for path in required):
            return RuntimeState.UNINITIALIZED_PROJECT
        if self.snapshot_path.exists():
            snapshot = self._load_snapshot()
            return RuntimeState(snapshot["runtime_state"])
        state = self._read_yaml_like(self.root / ".ai" / "state.yaml")
        if not state.get("current_task_id"):
            return RuntimeState.NO_ACTIVE_TASK
        return RuntimeState.LOOP_PROJECT_READY

    def onboard_project(self, intent: str = "", *, idempotency_key: str | None = None) -> RuntimeSnapshot:
        if not self.root.is_dir():
            raise RuntimeControllerError("NOT_A_PROJECT")
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        for directory in ("tasks", "evidence", "handoffs", "runtime"):
            (self.root / ".ai" / directory).mkdir(parents=True, exist_ok=True)
        self._ensure_file(".ai/state.yaml", "schema_version: 1\ncurrent_phase: S0-init\ncurrent_task_id: null\ncurrent_gate_id: null\nloop_mode: FULL\n")
        self._ensure_file(".ai/gates.yaml", "schema_version: 1\ngates: []\n")
        self._ensure_file(".ai/task_graph.yaml", "schema_version: 1\ntasks: []\nedges: []\n")
        self._ensure_file(".ai/HANDOFF.md", "# Handoff\n\nLoop onboarding initialized; no active task.\n")
        snapshot = self._load_snapshot(default_state=RuntimeState.NO_ACTIVE_TASK.value)
        snapshot.setdefault("intent", intent)
        snapshot.setdefault("onboarding_idempotency_key", idempotency_key or _hash({"intent": intent, "root": str(self.root)}))
        snapshot["runtime_state"] = RuntimeState.NO_ACTIVE_TASK.value
        self._save_snapshot(snapshot)
        self._event("PROJECT_ONBOARDED", snapshot)
        return self.snapshot()

    def create_work_package_proposal(
        self,
        task_id: str,
        gate_id: str,
        title: str,
        allowed_paths: list[str],
        *,
        non_goals: list[str] | None = None,
        risk_flags: dict[str, bool] | None = None,
    ) -> RuntimeSnapshot:
        current = self.inspect()
        if current not in {RuntimeState.NO_ACTIVE_TASK, RuntimeState.LOOP_PROJECT_READY, RuntimeState.WORK_PACKAGE_PROPOSAL, RuntimeState.USER_APPROVAL_REQUIRED}:
            raise RuntimeControllerError(f"PROPOSAL_NOT_ALLOWED:{current.value}")
        if not task_id or not gate_id or not allowed_paths:
            raise RuntimeControllerError("PROPOSAL_INVALID")
        proposal = {
            "task_id": task_id, "gate_id": gate_id, "title": title,
            "allowed_paths": sorted(set(allowed_paths)),
            "non_goals": non_goals or [], "risk_flags": risk_flags or {},
        }
        snapshot = self._load_snapshot()
        snapshot.update({
            "runtime_state": RuntimeState.USER_APPROVAL_REQUIRED.value,
            "task_id": task_id, "gate_id": gate_id,
            "proposal": proposal, "proposal_hash": _hash(proposal),
            "execution_id": None, "capability_id": None,
        })
        self._save_snapshot(snapshot)
        self._event("WORK_PACKAGE_PROPOSED", {"proposal_hash": snapshot["proposal_hash"], "task_id": task_id, "gate_id": gate_id})
        return self.snapshot()

    def approve_and_execute(
        self,
        gate_id: str,
        *,
        approval: str,
        user_actor_id: str = "user",
        idempotency_key: str | None = None,
        start_execution: Callable[[ExecutionCapability], Any] | None = None,
    ) -> RuntimeSnapshot:
        if not approval.strip():
            raise RuntimeControllerError("USER_APPROVAL_REQUIRED")
        snapshot = self._load_snapshot()
        if snapshot.get("gate_id") != gate_id:
            raise RuntimeControllerError("GATE_MISMATCH")
        if snapshot.get("runtime_state") == RuntimeState.DEVELOPER_EXECUTION.value and snapshot.get("execution_id"):
            expected_key = snapshot.get("idempotency_key")
            requested_key = idempotency_key or _hash({"gate_id": gate_id, "proposal_hash": snapshot.get("proposal_hash"), "approval": approval})
            if expected_key == requested_key:
                return self.snapshot()
            raise RuntimeControllerError("IDEMPOTENCY_KEY_CONFLICT")
        if snapshot.get("runtime_state") not in {RuntimeState.USER_APPROVAL_REQUIRED.value, RuntimeState.WORK_PACKAGE_PROPOSAL.value}:
            raise RuntimeControllerError("APPROVAL_NOT_ALLOWED")
        proposal = snapshot.get("proposal") or {}
        key = idempotency_key or _hash({"gate_id": gate_id, "proposal_hash": snapshot.get("proposal_hash"), "approval": approval})
        existing_key = snapshot.get("idempotency_key")
        if existing_key is not None:
            if existing_key != key:
                raise RuntimeControllerError("IDEMPOTENCY_KEY_CONFLICT")
            if snapshot.get("execution_id"):
                return self.snapshot()
        execution_id = f"exec-{secrets.token_hex(10)}"
        capability = ExecutionCapability(
            capability_id=f"cap-{secrets.token_hex(10)}", task_id=proposal["task_id"],
            execution_id=execution_id, assigned_actor_id=f"developer:{proposal['task_id']}",
            allowed_paths=tuple(proposal["allowed_paths"]), issued_at="now", idempotency_key=key,
        )
        snapshot.update({
            "runtime_state": RuntimeState.DEVELOPER_EXECUTION.value,
            "execution_id": execution_id, "capability_id": capability.capability_id,
            "approved_by": user_actor_id, "approval": approval,
            "idempotency_key": key,
        })
        self._save_snapshot(snapshot)
        _atomic_json(self.capability_path, asdict(capability))
        self._event("APPROVED_AND_EXECUTION_STARTED", {"gate_id": gate_id, "task_id": proposal["task_id"], "execution_id": execution_id, "capability_id": capability.capability_id})
        if start_execution is not None:
            start_execution(capability)
        return self.snapshot()

    def resume_execution(self, context: ExecutionContext) -> RuntimeSnapshot:
        snapshot = self._load_snapshot()
        if snapshot.get("runtime_state") not in {RuntimeState.DEVELOPER_EXECUTION.value, RuntimeState.ACTIVE_TASK.value, RuntimeState.REVIEW.value, RuntimeState.REPAIR.value}:
            raise RuntimeControllerError("NO_APPROVED_EXECUTION")
        if context.task_id != snapshot.get("task_id") or context.execution_id != snapshot.get("execution_id"):
            raise RuntimeControllerError("EXECUTION_CONTEXT_MISMATCH")
        return self.snapshot()

    def authorize_write(self, context: ExecutionContext, relative_path: str) -> tuple[bool, str]:
        snapshot = self._load_snapshot()
        path = relative_path.replace("\\", "/").lstrip("/")
        if path in GOVERNANCE_FILES:
            return (context.caller_class == "controller", "GOVERNANCE_CONTROLLER_ONLY")
        if snapshot.get("runtime_state") in {RuntimeState.NO_ACTIVE_TASK.value, RuntimeState.USER_APPROVAL_REQUIRED.value, RuntimeState.WORK_PACKAGE_PROPOSAL.value}:
            return False, "NO_ACTIVE_TASK_OR_PROPOSAL"
        if context.caller_class == "main-thread" or context.role_id in {"main-thread", "orchestrator"}:
            return False, "MAIN_THREAD_BUSINESS_WRITE_DENIED"
        if context.role_id != "developer":
            return False, "ROLE_NOT_ALLOWED_TO_WRITE"
        if context.task_id != snapshot.get("task_id") or context.execution_id != snapshot.get("execution_id") or context.capability_id != snapshot.get("capability_id"):
            return False, "EXECUTION_CAPABILITY_MISMATCH"
        capability = self._load_capability()
        if not any(path == allowed or path.startswith(allowed.rstrip("/") + "/") for allowed in capability["allowed_paths"]):
            return False, "PATH_OUTSIDE_APPROVED_SCOPE"
        if context.actor_id != capability["assigned_actor_id"]:
            return False, "ACTOR_NOT_ASSIGNED"
        return True, "AUTHORIZED"

    def checkpoint(self, next_action: str, *, summary: str = "") -> Path:
        snapshot = self._load_snapshot()
        checkpoint = {
            "schema": "LoopExecutionCheckpoint/v1",
            "runtime_state": snapshot.get("runtime_state"), "task_id": snapshot.get("task_id"),
            "gate_id": snapshot.get("gate_id"), "execution_id": snapshot.get("execution_id"),
            "capability_id": snapshot.get("capability_id"), "proposal_hash": snapshot.get("proposal_hash"),
            "next_action": next_action, "summary": summary,
        }
        _atomic_json(self.checkpoint_path, checkpoint)
        snapshot["checkpoint_ref"] = str(self.checkpoint_path.relative_to(self.root))
        self._save_snapshot(snapshot)
        self._event("CHECKPOINT_CREATED", checkpoint)
        return self.checkpoint_path

    def snapshot(self) -> RuntimeSnapshot:
        data = self._load_snapshot()
        return RuntimeSnapshot(data.get("runtime_state", RuntimeState.NO_ACTIVE_TASK.value), data.get("task_id"), data.get("gate_id"), data.get("execution_id"), data.get("capability_id"), data.get("proposal_hash"), data.get("checkpoint_ref"))

    def _ensure_file(self, relative: str, content: str) -> None:
        path = self.root / relative
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def _load_snapshot(self, default_state: str = RuntimeState.NO_ACTIVE_TASK.value) -> dict[str, Any]:
        if not self.snapshot_path.exists():
            return {"schema": "LoopRuntimeState/v1", "runtime_state": default_state}
        try:
            return json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeControllerError(f"RUNTIME_STATE_INVALID:{exc}") from exc

    def _save_snapshot(self, data: dict[str, Any]) -> None:
        _atomic_json(self.snapshot_path, data)

    def _load_capability(self) -> dict[str, Any]:
        try:
            return json.loads(self.capability_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeControllerError(f"CAPABILITY_INVALID:{exc}") from exc

    def _event(self, event: str, details: dict[str, Any]) -> None:
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        with self.journal_path.open("a", encoding="utf-8") as stream:
            stream.write(_canonical({"event": event, "details": details}) + "\n")

    @staticmethod
    def _read_yaml_like(path: Path) -> dict[str, Any]:
        result: dict[str, Any] = {}
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if ":" in line and not line.startswith(" "):
                    key, value = line.split(":", 1)
                    result[key.strip()] = None if value.strip() in {"", "null"} else value.strip().strip("'")
        except OSError:
            return {}
        return result
