from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from codex_loop.core.models import ProjectProfile
from codex_loop.planning.phases import default_phases
from codex_loop.planning.graph import default_task_graph


class StoreError(ValueError):
    """Raised for invalid or missing Loop store state."""


STORE_DIRS = (
    "roles",
    "phases",
    "tasks",
    "runs",
    "artifacts",
    "packets",
    "findings",
    "state",
)


class LoopStore:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.loop_root = self.project_root / ".loop"

    def initialize(self, profile: ProjectProfile) -> None:
        if profile.host != "codex":
            raise StoreError("this candidate only supports host=codex")
        self.loop_root.mkdir(parents=True, exist_ok=True)
        for name in STORE_DIRS:
            (self.loop_root / name).mkdir(parents=True, exist_ok=True)
        self.write_json("project.json", profile.to_dict())
        self.write_json("phases/default.json", {"phases": [phase.to_dict() for phase in default_phases()]})
        self.write_json("tasks/default-graph.json", default_task_graph().to_dict())
        self.write_json("state/current.json", {"phase_id": "P0", "status": "initialized", "gate": None})

    def exists(self) -> bool:
        return (self.loop_root / "project.json").exists()

    def read_json(self, relative: str) -> dict[str, Any]:
        path = self.loop_root / relative
        if not path.exists():
            raise StoreError(f"missing Loop state: {relative}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise StoreError(f"expected object in {relative}")
        return payload

    def write_json(self, relative: str, payload: dict[str, Any]) -> Path:
        target = (self.loop_root / relative).resolve()
        target.relative_to(self.loop_root.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".loop-", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            Path(temp_name).replace(target)
        except Exception:
            Path(temp_name).unlink(missing_ok=True)
            raise
        return target
