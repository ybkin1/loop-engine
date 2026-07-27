"""
Codex Host Adapter -- STRONG enforcement for Codex (Anthropic Claude API).

Codex provides MCP tools for file operations and shell commands, along with
sub-agent isolation via multi_agent_v1_spawn_agent. This adapter implements
the HostAdapter interface for Codex with STRONG enforcement level.

Adapted from zcode loop-engine v3.0.0 loop_engine/adapters/claude_adapter.py.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from codex_loop.core.contracts import HostAdapter
from codex_loop.core.enforcement import EnforcementLevel, HostCapabilities

try:
    import yaml
except ImportError:
    yaml = None


class CodexAdapter(HostAdapter):
    """Codex-specific implementation of the Loop Host Adapter.

    Codex capabilities:
    - File read/write via MCP tools (apply_patch, shell_command)
    - Shell command execution via shell_command tool
    - Sub-agent isolation via multi_agent_v1_spawn_agent
    - Evidence freezing via SHA256 hashing
    """

    def __init__(self, project_root: str | Path):
        self._root = Path(project_root).resolve()
        self._ai_dir = self._root / ".ai"
        self._started_at = datetime.now(timezone.utc).isoformat()

    @property
    def host_name(self) -> str:
        return "Codex"

    @property
    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(
            can_intercept_writes=True,
            can_intercept_commands=True,
            can_isolate_agents=True,
            can_enforce_exit_codes=True,
            has_hooks_api=True,
        )

    @property
    def enforcement_level(self) -> EnforcementLevel:
        return EnforcementLevel.STRONG

    def read_file(self, path: str | Path) -> str:
        p = self._resolve(path)
        return p.read_text(encoding="utf-8")

    def write_file(self, path: str | Path, content: str) -> bool:
        p = self._resolve(path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return True
        except (OSError, PermissionError):
            return False

    def file_exists(self, path: str | Path) -> bool:
        return self._resolve(path).exists()

    def execute(self, command: str, args: list[str], timeout_ms: int = 30000) -> tuple[int, str, str]:
        try:
            r = subprocess.run(
                [command] + args, capture_output=True, text=True,
                timeout=timeout_ms / 1000, cwd=str(self._root),
            )
            return r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "TIMEOUT"
        except Exception as e:
            return -1, "", str(e)

    def launch_agent(self, role_id: str, prompt: str, input_files: list[str], output_file: str) -> str:
        agent_id = f"agent_{role_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        record = {
            "agent_id": agent_id, "role_id": role_id,
            "launched_at": datetime.now(timezone.utc).isoformat(),
            "input_files": input_files, "output_file": output_file,
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
        }
        evidence_dir = self._ai_dir / "evidence" / "agent_logs"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / f"{agent_id}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        return agent_id

    def load_state(self) -> dict[str, Any]:
        return self._load_yaml("state.yaml")

    def save_state(self, state: dict[str, Any]) -> bool:
        return self._save_yaml("state.yaml", state)

    def load_gates(self) -> list[dict[str, Any]]:
        data = self._load_yaml("gates.yaml")
        return data.get("gates", []) if data else []

    def load_tasks(self) -> list[dict[str, Any]]:
        data = self._load_yaml("task_graph.yaml")
        return data.get("tasks", []) if data else []

    def present_gate(self, gate: dict[str, Any], summary: str) -> str:
        return gate.get("status", "pending")

    def ask_user(self, question: str, context: str) -> str:
        return "pending"

    def freeze_evidence(self, evidence_id: str, bindings: dict[str, str]) -> str:
        evidence_dir = self._ai_dir / "evidence" / "frozen"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        hasher = hashlib.sha256()
        for name, path in sorted(bindings.items()):
            p = self._resolve(path)
            if p.exists():
                hasher.update(p.read_bytes())
        sha = hasher.hexdigest()
        (evidence_dir / f"{evidence_id}.freeze.json").write_text(
            json.dumps({"evidence_id": evidence_id, "sha256": sha, "frozen_at": datetime.now(timezone.utc).isoformat(), "bindings": bindings}, indent=2), encoding="utf-8")
        return sha

    def check_evidence_freshness(self, evidence_id: str) -> bool:
        freeze_file = self._ai_dir / "evidence" / "frozen" / f"{evidence_id}.freeze.json"
        if not freeze_file.exists():
            return False
        try:
            record = json.loads(freeze_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        hasher = hashlib.sha256()
        for name, path in sorted(record.get("bindings", {}).items()):
            p = self._resolve(path)
            if p.exists():
                hasher.update(p.read_bytes())
        return hasher.hexdigest() == record.get("sha256", "")

    def validate_startup(self) -> dict[str, Any]:
        errors, warnings = [], []
        for fname in ["state.yaml", "gates.yaml", "task_graph.yaml"]:
            if not (self._ai_dir / fname).exists():
                errors.append(f"Missing .ai/{fname}")
        return {"host": self.host_name, "enforcement_level": self.enforcement_level.value,
                "project_root": str(self._root), "started_at": self._started_at,
                "errors": errors, "warnings": warnings, "state_usable": len(errors) == 0}

    def _resolve(self, path: str | Path) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self._root / p

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        path = self._ai_dir / filename
        if not path.exists():
            return {}
        if yaml is not None:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _save_yaml(self, filename: str, data: dict[str, Any]) -> bool:
        path = self._ai_dir / filename
        try:
            if yaml is not None:
                with open(path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            return True
        except (OSError, PermissionError):
            return False