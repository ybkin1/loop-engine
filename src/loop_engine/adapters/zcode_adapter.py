"""
ZCode Host Adapter — Concrete implementation of HostAdapter for ZCode.

Bridges Loop Core's host-independent protocol to ZCode's actual capabilities:
- STRONG enforcement (PreToolUse hooks intercept Write/Edit/Bash/ApplyPatch/Agent)
- Agent isolation via ZCode's Agent tool
- State/gate/task management via .ai/ YAML files
- Evidence freezing via SHA256 hashing

Declares: ENFORCEMENT_LEVEL = STRONG (hooks.json has PreToolUse interception for Write+Edit+Bash+ApplyPatch+Agent)
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Loop Core imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from loop_core.contracts import HostAdapter
from loop_core.enforcement import EnforcementLevel, HostCapabilities

try:
    import yaml
except ImportError:
    yaml = None


class ZCodeAdapter(HostAdapter):
    """
    ZCode-specific implementation of the Loop Host Adapter.

    Uses:
    - ZCode hooks (gate_guard, path_guard) for write interception
    - ZCode Agent tool for role isolation
    - .ai/ YAML files for state management
    - SHA256 for evidence freezing
    """

    def __init__(self, project_root: str | Path):
        self._root = Path(project_root).resolve()
        self._ai_dir = self._root / ".ai"
        self._zcode_dir = self._root / ".zcode"
        self._started_at = datetime.now(timezone.utc).isoformat()

    # ── Identity ──

    @property
    def host_name(self) -> str:
        return "ZCode"

    @property
    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(
            can_intercept_writes=True,       # PreToolUse hooks intercept Write/Edit
            can_intercept_commands=True,      # PreToolUse hooks intercept Bash (hooks.json matcher includes "Bash")
            can_isolate_agents=True,          # Agent tool = fresh context
            can_enforce_exit_codes=True,      # exit 2 = deny in hooks
            has_hooks_api=True,               # hooks.json + events schema
        )

    @property
    def enforcement_level(self) -> EnforcementLevel:
        # ZCode's PreToolUse hooks intercept Write/Edit/Bash/ApplyPatch/Agent.
        # Per enforcement.py: STRONG requires write + command + exit_code enforcement.
        # ZCode qualifies for STRONG because hooks.json matcher includes all operation types.
        return self.capabilities.enforcement_level()

    # ── File System ──

    def read_file(self, path: str | Path) -> str:
        p = self._resolve(path)
        return p.read_text(encoding="utf-8")

    def write_file(self, path: str | Path, content: str) -> bool:
        """Write file. Hook interception is handled by ZCode engine at PreToolUse."""
        p = self._resolve(path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return True
        except (OSError, PermissionError):
            return False

    def file_exists(self, path: str | Path) -> bool:
        return self._resolve(path).exists()

    # ── Command Execution ──

    def execute(self, command: str, args: list[str], timeout_ms: int = 30000) -> tuple[int, str, str]:
        """Execute command. At STRONG level, dangerous commands may be blocked by hooks."""
        try:
            r = subprocess.run(
                [command] + args,
                capture_output=True,
                text=True,
                timeout=timeout_ms / 1000,
                cwd=str(self._root),
            )
            return r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "TIMEOUT"
        except Exception as e:
            return -1, "", str(e)

    # ── Agent Management ──

    def launch_agent(
        self,
        role_id: str,
        prompt: str,
        input_files: list[str],
        output_file: str,
    ) -> str:
        """
        Launch an isolated agent via ZCode's Agent tool.

        Returns the agent_id. The caller must use ZCode's actual Agent tool
        to launch — this method prepares and records the invocation.

        In a real ZCode session, this would be:
            Agent(subagent_type="general-purpose", prompt=prompt)
        """
        # Record the agent launch in evidence
        agent_id = f"agent_{role_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        record = {
            "agent_id": agent_id,
            "role_id": role_id,
            "launched_at": datetime.now(timezone.utc).isoformat(),
            "input_files": input_files,
            "output_file": output_file,
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
        }
        evidence_dir = self._ai_dir / "evidence" / "agent_logs"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / f"{agent_id}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return agent_id

    # ── State Management ──

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

    # ── User Interaction ──

    def present_gate(self, gate: dict[str, Any], summary: str) -> str:
        """
        Present a gate to the user. In ZCode, this is done via the chat interface.
        Returns the user's decision as recorded in gates.yaml.
        """
        # In practice, the main-thread presents this to the user
        # and records the decision. This method just checks the current status.
        # mypy 门禁（A1）：dict.get 返回 Any → 显式 str（no-any-return 消解）
        return str(gate.get("status", "pending"))

    def ask_user(self, question: str, context: str) -> str:
        """Ask user a question. In ZCode, via chat interface."""
        # In practice, this goes through the main-thread's chat interaction
        return "pending"

    # ── Evidence ──

    def freeze_evidence(self, evidence_id: str, bindings: dict[str, str]) -> str:
        """Freeze evidence by computing and storing SHA256."""
        evidence_dir = self._ai_dir / "evidence" / "frozen"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        # Compute combined hash of all bound files
        hasher = hashlib.sha256()
        for name, path in sorted(bindings.items()):
            p = self._resolve(path)
            if p.exists():
                hasher.update(p.read_bytes())

        sha = hasher.hexdigest()
        freeze_record = {
            "evidence_id": evidence_id,
            "sha256": sha,
            "frozen_at": datetime.now(timezone.utc).isoformat(),
            "bindings": bindings,
        }
        (evidence_dir / f"{evidence_id}.freeze.json").write_text(
            json.dumps(freeze_record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return sha

    def check_evidence_freshness(self, evidence_id: str) -> bool:
        """Check if frozen evidence matches current file state."""
        freeze_file = self._ai_dir / "evidence" / "frozen" / f"{evidence_id}.freeze.json"
        if not freeze_file.exists():
            return False

        try:
            record = json.loads(freeze_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False

        hasher = hashlib.sha256()
        bindings = record.get("bindings", {})
        for name, path in sorted(bindings.items()):
            p = self._resolve(path)
            if p.exists():
                hasher.update(p.read_bytes())

        # mypy 门禁（A1）：record.get 返回 Any → 显式 str（no-any-return 消解）
        return hasher.hexdigest() == str(record.get("sha256", ""))

    # ── Internal Helpers ──

    def _resolve(self, path: str | Path) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return self._root / p

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        path = self._ai_dir / filename
        if not path.exists():
            return {}
        if yaml is not None:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        # Fallback: basic line parsing
        return {}

    def _save_yaml(self, filename: str, data: dict[str, Any]) -> bool:
        path = self._ai_dir / filename
        try:
            if yaml is not None:
                with open(path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except (OSError, PermissionError):
            return False

    # ── Startup Validation ──

    def validate_startup(self) -> dict[str, Any]:
        """Run startup validation checks."""
        errors = []
        warnings = []

        # Check required files
        for fname in ["state.yaml", "gates.yaml", "task_graph.yaml"]:
            if not (self._ai_dir / fname).exists():
                errors.append(f"Missing .ai/{fname}")

        # Check enforcement level honesty
        if self.enforcement_level == EnforcementLevel.STRONG:
            if not self.capabilities.can_intercept_writes:
                warnings.append("STRONG level claimed but write interception unverified")
            if not self.capabilities.can_enforce_exit_codes:
                warnings.append("STRONG level claimed but exit code enforcement unverified")

        return {
            "host": self.host_name,
            "enforcement_level": self.enforcement_level.value,
            "project_root": str(self._root),
            "started_at": self._started_at,
            "errors": errors,
            "warnings": warnings,
            "state_usable": len(errors) == 0,
        }
