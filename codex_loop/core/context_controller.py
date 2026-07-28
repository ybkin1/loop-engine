"""
ContextController — Unified Authorization Engine for Loop Engine.

All sensitive operation authorization flows through this controller.
Hooks (gate_guard, loop_enforcement) should import and call this instead
of maintaining independent authorization logic.

Decision chain (priority from high to low):
1. High-risk operations → require independent gate → DENY
2. Protected paths (AGENTS.md, .zcode/config.json) → ASK_USER
3. Governance files (.ai/, .zcode/tools/, .zcode/skills/) →
   - No pending gate → ALLOW
   - Pending gate exists → check allowed_paths → ALLOW if in scope, else DENY
4. Task scope → match allowed_paths → ALLOW (if in scope), else DENY
5. Default → DENY (fail-closed)

Key: during a pending gate, writes targeting paths within the gate's
allowed_paths are ALLOWED. This solves the "design phase needs to write
design docs but is blocked by pending gate" deadlock.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


# ── Core Types ──────────────────────────────────────────────────────────

class Action(str, Enum):
    WRITE_FILE = "write_file"
    EXEC_BASH = "exec_bash"
    APPLY_PATCH = "apply_patch"
    MCP_TOOL_CALL = "mcp_tool_call"
    LAUNCH_ROLE = "launch_role"
    SUBMIT_EVIDENCE = "submit_evidence"
    STATE_TRANSITION = "state_transition"
    GATE_TRANSITION = "gate_transition"
    INSTALL = "install"
    UPGRADE = "upgrade"
    ROLLBACK = "rollback"


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK_USER = "ask_user"


@dataclass
class AuthRequest:
    action: Action
    target_path: str | None = None
    task_id: str | None = None
    role_id: str | None = None


@dataclass
class AuthResult:
    decision: Decision
    reason: str
    required_gate_id: str | None = None


# ── ContextController ───────────────────────────────────────────────────

class ContextController:
    """Unified authorization controller.

    All Hook calls route through authorize() for write/execute decisions.
    The decision chain runs checks in priority order; the first matching
    check produces the definitive result.
    """

    # Protected paths: writing to these always requires user confirmation.
    PROTECTED_PATHS: list[str] = ["AGENTS.md", ".zcode/config.json"]

    # Governance file prefixes: files under these are governance artifacts.
    GOVERNANCE_PREFIXES: list[str] = [".ai/", ".zcode/tools/", ".zcode/skills/"]

    # High-risk actions: require an independent gate (not self-approved).
    HIGH_RISK_ACTIONS: frozenset[Action] = frozenset({
        Action.INSTALL,
        Action.UPGRADE,
        Action.ROLLBACK,
        Action.GATE_TRANSITION,
    })

    # Decision-recording exemption: gates.yaml must always be writable
    # to avoid deadlock (user approves but AI cannot write the decision).
    DECISION_RECORDING_EXEMPT: frozenset[str] = frozenset({".ai/gates.yaml"})

    # Actions that are inherently safe without a file target.
    _NON_FILE_ACTIONS: frozenset[Action] = frozenset({
        Action.LAUNCH_ROLE,
        Action.SUBMIT_EVIDENCE,
        Action.STATE_TRANSITION,
    })

    def __init__(self, project_root: Path) -> None:
        self._project_root = Path(project_root).resolve()

    # ── Public API ────────────────────────────────────────────────────

    def authorize(self, request: AuthRequest) -> AuthResult:
        """Run the full decision chain and return an authorization result.

        Checks are executed in priority order; the first check that
        produces a result wins.
        """
        # 1. High-risk action check
        result = self._check_high_risk(request.action)
        if result is not None:
            return result

        # For actions without file targets that are not high-risk:
        # allow them (they are authorized at a higher level, e.g. executor).
        if request.target_path is None:
            if request.action in self._NON_FILE_ACTIONS:
                return AuthResult(
                    decision=Decision.ALLOW,
                    reason=f"Non-file action '{request.action.value}' allowed "
                           f"(authorized at host level)",
                )
            # Unrecognised action without target → deny
            return AuthResult(
                decision=Decision.DENY,
                reason=f"Action '{request.action.value}' without target_path "
                       f"cannot be authorized (fail-closed)",
            )

        # Decision-recording exemption: .ai/gates.yaml always allowed.
        rel = self._normalize_rel(request.target_path)
        if rel is not None and rel in self.DECISION_RECORDING_EXEMPT:
            return AuthResult(
                decision=Decision.ALLOW,
                reason="Decision-recording exemption: .ai/gates.yaml always writable",
            )

        # 2. Protected path check
        result = self._check_protected(request.target_path)
        if result is not None:
            return result

        # 3. Governance file check
        result = self._check_governance(request)
        if result is not None:
            return result

        # 4. Task scope check
        result = self._check_task_scope(request)
        if result is not None:
            return result

        # 5. Default deny (fail-closed)
        return AuthResult(
            decision=Decision.DENY,
            reason="No applicable authorization rule matched — deny by default (fail-closed)",
        )

    # ── Check 1: High-Risk Actions ────────────────────────────────────

    def _check_high_risk(self, action: Action) -> AuthResult | None:
        """High-risk actions require an independent gate approval.

        These actions cannot be self-approved by the AI and must go
        through an explicit gate with user or role approval.
        """
        if action in self.HIGH_RISK_ACTIONS:
            return AuthResult(
                decision=Decision.DENY,
                reason=(
                    f"High-risk action '{action.value}' requires an "
                    f"independent gate approval"
                ),
            )
        return None

    # ── Check 2: Protected Paths ──────────────────────────────────────

    def _check_protected(self, path: str | None) -> AuthResult | None:
        """Protected paths trigger ASK_USER to confirm the write.

        AGENTS.md and .zcode/config.json are critical project files
        that the user must explicitly approve modifications to.
        """
        if path is None:
            return None
        rel = self._normalize_rel(path)
        if rel is None:
            return None
        for protected in self.PROTECTED_PATHS:
            protected_norm = protected.replace("\\", "/")
            if rel == protected_norm:
                return AuthResult(
                    decision=Decision.ASK_USER,
                    reason=f"Protected path: '{rel}' requires user confirmation",
                )
        return None

    # ── Check 3: Governance Files ─────────────────────────────────────

    def _check_governance(self, request: AuthRequest) -> AuthResult | None:
        """Governance files (.ai/, .zcode/tools/, .zcode/skills/) logic:

        - No pending gate → ALLOW (governance maintenance is always OK).
        - Pending gate → check if target is in the gate's allowed_paths:
          * In allowed_paths → ALLOW (design docs can be written during review).
          * Not in allowed_paths → DENY (prevents bypassing the gate).
        """
        if request.target_path is None:
            return None
        rel = self._normalize_rel(request.target_path)
        if rel is None:
            return None
        if not self._is_governance_path(rel):
            return None

        pending = self._get_pending_gates()
        if not pending:
            return AuthResult(
                decision=Decision.ALLOW,
                reason="Governance file write, no pending gates",
            )

        # Pending gate(s) exist — check if target is in any gate's allowed_paths
        for gate in pending:
            gate_id = gate.get("id", "<unknown>")
            allowed = gate.get("allowed_paths", [])
            if isinstance(allowed, str):
                allowed = [allowed]
            for allowed_path in allowed:
                allowed_norm = self._normalize_scope_path(str(allowed_path))
                if self._path_matches(rel, allowed_norm):
                    return AuthResult(
                        decision=Decision.ALLOW,
                        reason=(
                            f"Governance file '{rel}' is in allowed_paths "
                            f"of pending gate '{gate_id}'"
                        ),
                    )

        # In allowed_paths of no pending gate → DENY
        return AuthResult(
            decision=Decision.DENY,
            reason=(
                f"Governance file '{rel}' is not in allowed_paths of any "
                f"pending gate: {[g.get('id') for g in pending]}"
            ),
        )

    # ── Check 4: Task Scope ───────────────────────────────────────────

    def _check_task_scope(self, request: AuthRequest) -> AuthResult | None:
        """Check if the target is within the active task's allowed_paths.

        - No task_id → DENY (cannot verify scope).
        - Task contract not found → DENY.
        - No allowed_paths in contract → DENY (fail-closed).
        - Target in allowed_paths → ALLOW.
        - Target not in allowed_paths → DENY.
        """
        if request.target_path is None:
            return None
        rel = self._normalize_rel(request.target_path)
        if rel is None:
            return None

        task_id = request.task_id or self._get_current_task_id()
        if task_id is None:
            return AuthResult(
                decision=Decision.DENY,
                reason="No task_id available — cannot verify write scope",
            )

        contract = self._load_task_contract(task_id)
        if contract is None:
            return AuthResult(
                decision=Decision.DENY,
                reason=f"Task contract for '{task_id}' not found",
            )

        allowed = contract.get("allowed_paths", [])
        if not allowed:
            return AuthResult(
                decision=Decision.DENY,
                reason=f"Task '{task_id}' has no allowed_paths defined",
            )

        for allowed_path in allowed:
            allowed_norm = self._normalize_scope_path(str(allowed_path))
            if self._path_matches(rel, allowed_norm):
                return AuthResult(
                    decision=Decision.ALLOW,
                    reason=f"Path '{rel}' is in allowed scope of task '{task_id}'",
                )

        return AuthResult(
            decision=Decision.DENY,
            reason=(
                f"Path '{rel}' is not in allowed_paths of task '{task_id}': "
                f"{allowed}"
            ),
        )

    # ── Helpers ───────────────────────────────────────────────────────

    def _normalize_rel(self, target: str) -> str | None:
        """Convert target path to a posix-style relative path from project root.

        Returns None if the target cannot be resolved or is outside the
        project root.
        """
        try:
            target_path = Path(target)
            if not target_path.is_absolute():
                target_path = self._project_root / target_path
            rel = target_path.resolve().relative_to(self._project_root.resolve())
            return rel.as_posix()
        except (ValueError, OSError):
            return None

    def _is_governance_path(self, rel: str) -> bool:
        """Check whether a relative path is a governance artifact."""
        rel = rel.replace("\\", "/")
        for prefix in self.GOVERNANCE_PREFIXES:
            prefix_norm = prefix.replace("\\", "/")
            if rel.startswith(prefix_norm):
                return True
        return False

    @staticmethod
    def _path_matches(rel: str, scope: str) -> bool:
        """Check if rel is equal to or inside scope (directory prefix match)."""
        scope = scope.rstrip("/")
        if rel == scope:
            return True
        if rel.startswith(scope + "/"):
            return True
        return False

    @staticmethod
    def _normalize_scope_path(raw: str) -> str:
        """Normalize a scope/allowed path: backslashes to forward, strip ./ prefix.

        Uses startswith-based check (not lstrip) because lstrip treats its
        argument as a character set, which strips all leading '.' and '/'
        characters rather than the './' prefix.
        """
        norm = raw.replace("\\", "/")
        if norm.startswith("./"):
            norm = norm[2:]
        return norm

    # ── File I/O ──────────────────────────────────────────────────────

    def _load_state(self) -> dict:
        """Load .ai/state.yaml; return empty dict on any failure."""
        state_path = self._project_root / ".ai" / "state.yaml"
        if not state_path.exists():
            return {}
        try:
            data = self._yaml_load(state_path)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _load_gates(self) -> list[dict]:
        """Load the gates list from .ai/gates.yaml.

        Returns an empty list if the file does not exist or cannot be parsed.
        """
        gates_path = self._project_root / ".ai" / "gates.yaml"
        if not gates_path.exists():
            return []
        try:
            data = self._yaml_load(gates_path) or {}
            gates = data.get("gates", [])
            return gates if isinstance(gates, list) else []
        except Exception:
            return []

    def _load_task_contract(self, task_id: str) -> dict | None:
        """Load a task contract from .ai/tasks/{task_id}.md.

        Parses YAML-like front-matter fields:
        - allowed_paths: list of path strings
        - developer_agent_id / reviewer_agent_id: agent IDs
        """
        task_path = self._project_root / ".ai" / "tasks" / f"{task_id}.md"
        if not task_path.exists():
            return None

        text = task_path.read_text(encoding="utf-8")
        contract: dict = {
            "allowed_paths": [],
            "developer_agent_id": None,
            "reviewer_agent_id": None,
        }

        in_allowed_section = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("allowed_paths:") or stripped.startswith("allowed_actions:"):
                in_allowed_section = True
                continue
            if in_allowed_section and stripped.startswith("- "):
                path = stripped[2:].strip().strip('"')
                contract["allowed_paths"].append(path)
            elif in_allowed_section and not stripped.startswith("- "):
                in_allowed_section = False
            if stripped.startswith("developer_agent_id:"):
                contract["developer_agent_id"] = stripped.split(":", 1)[1].strip().strip('"')
            elif stripped.startswith("reviewer_agent_id:"):
                contract["reviewer_agent_id"] = stripped.split(":", 1)[1].strip().strip('"')

        return contract

    def _get_current_task_id(self) -> str | None:
        """Read current_task_id from .ai/state.yaml."""
        state = self._load_state()
        tid = state.get("current_task_id")
        return str(tid) if tid else None

    def _get_pending_gates(self) -> list[dict]:
        """Return gates with status == 'pending'."""
        gates = self._load_gates()
        return [g for g in gates if isinstance(g, dict) and g.get("status") == "pending"]

    @staticmethod
    def _yaml_load(file_path: Path) -> dict | list | None:
        """Load a YAML file, preferring PyYAML with a text-scan fallback.

        The fallback handles the common case of flat key-value pairs and
        simple list-of-dicts structures used in Loop governance files.
        """
        text = file_path.read_text(encoding="utf-8")
        try:
            import yaml  # type: ignore
            return yaml.safe_load(text)
        except ImportError:
            pass
        return ContextController._naive_yaml_parse(text)

    @staticmethod
    def _naive_yaml_parse(text: str) -> dict:
        """Conservative text-based YAML parser for Loop governance files.

        Handles:
        - Top-level scalar keys
        - Nested lists of dicts under keys (gates, tasks)
        - Within dicts: scalar keys and list values (allowed_paths)

        Uses the original line (not stripped) for indent-sensitive matches.
        Only strips when checking plain content (starts-with, key detection).
        """
        import re

        result: dict = {}
        lines = text.splitlines()

        # Pass 1: top-level scalars (no indentation required)
        for line in lines:
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
            if m:
                key = m.group(1)
                value = m.group(2).strip().strip('"').strip("'")
                if value in ("null", "~", ""):
                    result[key] = None
                else:
                    result[key] = value

        # Pass 2: list-of-dicts (gates, tasks)
        list_keys = ["gates", "tasks"]
        for list_key in list_keys:
            items: list[dict] = []
            current_item: dict | None = None
            in_list = False
            in_allowed = False

            for line in lines:
                stripped = line.strip()
                # Detect list key start (no indentation for the key itself)
                if re.match(rf"^{list_key}:\s*$", stripped):
                    in_list = True
                    current_item = None
                    continue
                if in_list:
                    # New item: "- id:" or "- name:" etc.
                    # Use original line so leading whitespace is preserved for the regex.
                    m_item = re.match(r"^\s*-\s+(\S+):\s*(.*)$", line)
                    if m_item:
                        if current_item is not None:
                            items.append(current_item)
                        current_item = {}
                        k = m_item.group(1)
                        v = m_item.group(2).strip().strip('"').strip("'")
                        current_item[k] = v if v not in ("", "~", "null") else None
                        in_allowed = False
                        continue
                    if current_item is not None:
                        # Scalar field inside item: must be indented ≥2 spaces.
                        # Use original line so leading whitespace is preserved.
                        m_field = re.match(r"^\s{2,}(\S+):\s*(.*)$", line)
                        if m_field:
                            k = m_field.group(1)
                            v = m_field.group(2).strip().strip('"').strip("'")
                            if k == "allowed_paths":
                                in_allowed = True
                                current_item[k] = []
                            elif v in ("", "~", "null"):
                                current_item[k] = None
                            else:
                                current_item[k] = v
                            continue
                        # List item under a field (e.g. allowed_paths): ≥4 spaces indent.
                        # Use original line so leading whitespace is preserved.
                        m_list_item = re.match(r"^\s{4,}-\s+(.+)$", line)
                        if m_list_item and in_allowed:
                            current_item.setdefault("allowed_paths", []).append(
                                m_list_item.group(1).strip().strip('"').strip("'")
                            )
                            continue
                        # Non-matching line may end current list membership
                        if stripped and not stripped.startswith("#"):
                            # Could be start of a different top-level section
                            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*:\s*$", stripped):
                                in_list = False
                                if current_item is not None:
                                    items.append(current_item)
                                current_item = None
                                continue

            if current_item is not None:
                items.append(current_item)
            if items:
                result[list_key] = items

        return result
