"""
ContextController — Unified Authorization Engine for Loop Engine.

All sensitive operation authorization flows through this controller.
Hooks (gate_guard, loop_enforcement) should import and call this instead
of maintaining independent authorization logic.

Decision chain (priority from high to low):
1. High-risk operations → require independent gate → DENY
2. Protected paths (AGENTS.md) → ASK_USER
3. Governance files (.ai/) →
   - No pending gate → ALLOW
   - Pending gate exists → check allowed_paths → ALLOW if in scope, else DENY
4. Task scope → match allowed_paths → ALLOW (if in scope), else DENY
5. Default → DENY (fail-closed)

Note: Host-specific paths (.zcode/, .claude/, etc.) are injected by the
hooks layer (path_guard.py), not hardcoded in loop_core.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


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
    PROTECTED_PATHS: list[str] = ["AGENTS.md"]

    # Governance file prefixes: files under these are governance artifacts.
    GOVERNANCE_PREFIXES: list[str] = [".ai/"]

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

        AGENTS.md is a critical project file that the user must
        explicitly approve modifications to.  Host-specific protected
        paths are handled by hooks/path_guard.py.
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
        """Governance files (.ai/) logic:

        - No pending gate → ALLOW (governance maintenance is always OK).
        - Pending gate → check if target is in the gate's allowed_paths.
        Host-specific governance prefixes are injected by hooks.
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

    _SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"

    @staticmethod
    @lru_cache(maxsize=None)
    def _load_schema(name: str) -> dict | None:
        """读取 loop_core/schemas/ 下的 JSON schema（D5-1 校验用）。"""
        path = ContextController._SCHEMA_DIR / name
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def _validate_naive_parse_result(file_name: str, data) -> list[str]:
        """T-0107 D5-1: 对 naive 降级解析结果做 schema 校验（gates/state）。

        校验失败或校验器不可用时显式返回问题（调用方负责告警）——
        不允许无感知使用降级解析结果做授权决策。仅校验 state.yaml 与
        gates.yaml（复用 loop_core/schemas/ 的 state/gate schema）。
        """
        problems: list[str] = []
        if data is None or not isinstance(data, dict):
            return ["naive 解析产出非 dict 结果，解析可能不完整"]
        schema_file = None
        if file_name == "state.yaml":
            schema_file = "state.schema.json"
        elif file_name == "gates.yaml":
            schema_file = "gate.schema.json"
        if schema_file is None:
            return problems
        try:
            import jsonschema  # type: ignore
        except ImportError:
            problems.append(f"jsonschema 不可用，无法校验 {schema_file}（naive 解析结果未经验证）")
            return problems
        schema = ContextController._load_schema(schema_file)
        if schema is None:
            problems.append(f"schema 文件 {schema_file} 不可用，无法校验 naive 解析结果")
            return problems
        try:
            if schema_file == "gate.schema.json":
                gates = data.get("gates")
                if not isinstance(gates, list):
                    problems.append("gates 键缺失或非列表（naive 解析可能漏掉列表节）")
                else:
                    for i, gate in enumerate(gates):
                        if not isinstance(gate, dict):
                            problems.append(f"gate[{i}] 非 dict（naive 解析类型丢失）")
                            continue
                        try:
                            jsonschema.validate(gate, schema)
                        except jsonschema.ValidationError as exc:
                            problems.append(f"gate[{i}] 违反 gate schema: {exc.message}")
            else:
                try:
                    jsonschema.validate(data, schema)
                except jsonschema.ValidationError as exc:
                    problems.append(f"state 违反 state schema: {exc.message}")
        except Exception as exc:  # 校验器本身异常不阻断，但必须显式上报
            problems.append(f"schema 校验异常: {type(exc).__name__}: {exc}")
        return problems

    @staticmethod
    def _yaml_load_checked(file_path: Path) -> tuple[dict | list | None, list[str]]:
        """T-0107 D5-1: 解析 YAML，返回 (数据, 问题列表)。

        PyYAML 不可用或解析失败时显式告警并降级到 naive 解析（不再静默），
        且对 naive 结果做 schema 校验（问题进 problems 由调用方上报）。
        调用方据此区分"解析失败"与"无数据"。
        """
        problems: list[str] = []
        text = file_path.read_text(encoding="utf-8")
        try:
            import yaml  # type: ignore
            try:
                return yaml.safe_load(text), problems
            except yaml.YAMLError as exc:
                problems.append(f"PyYAML 解析失败: {exc}")
        except ImportError:
            problems.append("PyYAML 不可用")
        data = ContextController._naive_yaml_parse(text)
        if problems:
            logger.warning(
                "[context_controller] %s: %s；降级到 naive 解析（结果不完整风险）",
                file_path.name, "; ".join(problems),
            )
        problems.extend(ContextController._validate_naive_parse_result(file_path.name, data))
        return data, problems

    @staticmethod
    def _yaml_load(file_path: Path) -> dict | list | None:
        """Load a YAML file, preferring PyYAML with a text-scan fallback.

        T-0107 D5-1: 兼容入口——fallback 不再静默（告警 + schema 校验见
        ``_yaml_load_checked``），返回解析结果（失败时可能为部分结果）。
        """
        data, problems = ContextController._yaml_load_checked(file_path)
        for problem in problems:
            logger.warning("[context_controller] %s: %s", file_path.name, problem)
        return data

    def _load_state(self) -> dict:
        """Load .ai/state.yaml; return empty dict on any failure.

        T-0107 D5-1: 解析失败显式告警（was 静默返回空 dict）。
        """
        state_path = self._project_root / ".ai" / "state.yaml"
        if not state_path.exists():
            return {}
        try:
            data, problems = ContextController._yaml_load_checked(state_path)
            for problem in problems:
                logger.warning("[context_controller] state.yaml: %s", problem)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.warning("[context_controller] state.yaml 读取失败: %s", exc)
            return {}

    def _load_gates(self) -> list[dict]:
        """Load the gates list from .ai/gates.yaml.

        T-0107 D5-1: 解析失败与"无 gate"分开上报——文件缺失/无 gates 键
        是正常状态（返回 []，不告警）；解析异常/校验告警显式记录。
        """
        gates_path = self._project_root / ".ai" / "gates.yaml"
        if not gates_path.exists():
            return []
        try:
            data, problems = ContextController._yaml_load_checked(gates_path)
        except Exception as exc:
            logger.warning("[context_controller] gates.yaml 读取失败: %s", exc)
            return []
        for problem in problems:
            logger.warning("[context_controller] gates.yaml: %s", problem)
        if not isinstance(data, dict):
            return []
        gates = data.get("gates", [])
        if not isinstance(gates, list):
            logger.warning(
                "[context_controller] gates.yaml 的 gates 字段不是列表——"
                "解析失败，按无 gate 处理（fail-closed 语义由调用方保持）"
            )
            return []
        return gates

    def _load_task_contract(self, task_id: str) -> dict | None:
        """Load a task contract from .ai/tasks/{task_id}.md.

        T-0107 D5-2: 统一调用共享契约解析模块 loop_core.front_matter
        （与 hooks/scripts/loop_enforcement.py 同源，消除双解析器分歧；
        支持 mcp_allowed_tools 的 markdown 表格 / 内联 / 列表三种形态）。
        """
        task_path = self._project_root / ".ai" / "tasks" / f"{task_id}.md"
        if not task_path.exists():
            return None

        text = task_path.read_text(encoding="utf-8")
        from loop_core.front_matter import parse_task_front_matter
        return parse_task_front_matter(text)

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
