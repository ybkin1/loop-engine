#!/usr/bin/env python3
"""
loop_enforcement.py — PreToolUse hook: enforce Loop mode (hard constraint).

When state.yaml has loop_mode=FULL or STANDARD, this hook blocks any
write operation that is not explicitly within an approved task's scope.

This is the hard mechanism that prevents the AI from "doing everything
myself" — it forces the Loop process: task creation → gate approval →
role assignment → execution within approved scope.

Blocking logic:
1. loop_mode is LIGHTWEIGHT or unset → pass (no enforcement)
2. Write to .ai/ governance files → pass (same exemption as gate_guard)
3. Write within an active task's allowed_paths → pass
4. Everything else in FULL/STANDARD mode → exit 2 BLOCKED

Exit codes: 0 = allow, 2 = block
"""
import json
import logging
import sys
from pathlib import Path

sys.dont_write_bytecode = True

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING, format='[%(name)s] %(levelname)s: %(message)s')

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Also add loop-engine project root so loop_core is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from hook_common import (
    DEFAULT_CONFIG,
    extract_target_path,
    is_governance_project,
    is_path_safe,
    is_readonly_command,
    load_config,
    load_gates_for_context,
    load_phase_gates_for_context,
    load_state,
    load_tasks_for_context,
    normalize_rel,
    project_root,
    read_stdin_json,
    should_fail_closed,
    try_import_hard_constraints,
)

# 自愈同步函数首次 sync 前不可用 → 安全退化
try:
    from hook_common import auto_sync_to_plugin_cache  # noqa: F811
    _AUTO_SYNC_AVAILABLE = True
except ImportError:
    _AUTO_SYNC_AVAILABLE = False
    def auto_sync_to_plugin_cache(root):  # type: ignore
        pass

_HardConstraints, _Severity = try_import_hard_constraints()
_HARD_CONSTRAINTS_AVAILABLE = _HardConstraints is not None

EXIT_PASS = 0
EXIT_BLOCK = 2

# Governance files that are always writable (same exemption as gate_guard)
GOVERNANCE_EXEMPT = [
    ".ai/gates.yaml",
    ".ai/state.yaml",
    ".ai/task_graph.yaml",
    ".ai/HANDOFF.md",
    ".ai/PROGRESS.md",
    ".ai/project_continuity.yaml",
    ".zcode/config.json",
]

# Files that the main-thread can always write (evidence, handoff)
MAIN_THREAD_ALLOWED = [
    ".ai/evidence/",
    ".ai/tasks/",
    ".ai/certifications/",
]


def is_loop_mode_enforced(root: Path) -> bool:
    """Check if Loop mode enforcement is active for this project."""
    try:
        state = load_state(root)
    except Exception:
        return False

    loop_mode = state.get("loop_mode", "")
    return loop_mode in ("FULL", "STANDARD")


def load_task_contract(root: Path, task_id: str) -> dict | None:
    """Load the task contract to check allowed paths."""
    task_path = root / ".ai" / "tasks" / f"{task_id}.md"
    if not task_path.exists():
        return None

    text = task_path.read_text(encoding="utf-8")
    contract = {
        "allowed_paths": [],
        "developer_agent_id": None,
        "reviewer_agent_id": None,
    }

    in_allowed_section = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("allowed_paths:") or line.startswith("allowed_actions:"):
            in_allowed_section = True
            continue
        if in_allowed_section and line.startswith("- "):
            path = line[2:].strip().strip('"')
            contract["allowed_paths"].append(path)
        elif in_allowed_section and not line.startswith("- "):
            in_allowed_section = False
        if line.startswith("developer_agent_id:"):
            contract["developer_agent_id"] = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("reviewer_agent_id:"):
            contract["reviewer_agent_id"] = line.split(":", 1)[1].strip().strip('"')

    return contract


def is_governance_write(rel_path: str | None) -> bool:
    """Check if the target is a governance file (always allowed)."""
    if rel_path is None:
        return False
    rel = rel_path.replace("\\", "/")
    for exempt in GOVERNANCE_EXEMPT:
        if rel == exempt or rel.startswith(exempt.rstrip("/") + "/"):
            return True
    for allowed in MAIN_THREAD_ALLOWED:
        if rel.startswith(allowed):
            return True
    return False


def is_in_task_scope(rel_path: str | None, contract: dict | None) -> bool:
    """Check if the target path is within the task's allowed scope."""
    if rel_path is None or contract is None:
        return False
    allowed = contract.get("allowed_paths", [])
    if not allowed:
        return False  # Missing explicit scope is unsafe; fail closed.
    for path in allowed:
        path = path.replace("\\", "/")
        # Strip only "./" prefix, not individual '.' characters (v3.5 fix)
        # lstrip("./") would corrupt paths like ".zcode/" -> "zcode/"
        if path.startswith("./"):
            path = path[2:]
        if rel_path == path or rel_path.startswith(path.rstrip("/") + "/"):
            return True
    return False


# ── C11: File Write Counter ────────────────────────────────────────────

def _read_task_max_files(root: Path, task_id: str) -> int | None:
    """Parse max_files from the task contract markdown.

    Looks for 'max_files:' field in the task's .md file.
    Returns None if not specified (no limit).
    """
    task_path = root / ".ai" / "tasks" / f"{task_id}.md"
    if not task_path.is_file():
        return None

    try:
        text = task_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("max_files:"):
            value = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            try:
                return int(value)
            except ValueError:
                return None

    return None


def _get_file_write_count_file(root: Path, task_id: str) -> Path:
    """Get the path to the file write counter for a task."""
    evidence_dir = root / ".ai" / "evidence" / task_id
    return evidence_dir / "file_write_count.json"


def _read_file_write_count(root: Path, task_id: str) -> int:
    """Read the current file write count for a task. Returns 0 if no counter exists."""
    counter_file = _get_file_write_count_file(root, task_id)
    if not counter_file.is_file():
        return 0

    try:
        data = json.loads(counter_file.read_text(encoding="utf-8"))
        return data.get("count", 0)
    except (json.JSONDecodeError, OSError):
        return 0


def _increment_file_write_count(root: Path, task_id: str, file_path: str) -> int:
    """Increment the file write counter for a task and return the new count.

    Creates the evidence directory if it doesn't exist.
    """
    evidence_dir = root / ".ai" / "evidence" / task_id
    evidence_dir.mkdir(parents=True, exist_ok=True)

    current_count = _read_file_write_count(root, task_id)
    new_count = current_count + 1

    counter_file = _get_file_write_count_file(root, task_id)
    counter_file.write_text(
        json.dumps({"count": new_count, "last_file": file_path}, indent=2),
        encoding="utf-8",
    )

    return new_count


# ── Phase Gate Enforcement ──


def check_quality_gate_evidence(root: Path) -> tuple[bool, str]:
    """Check that S5-quality phase has quality-engineer structured evidence.

    Returns (has_evidence, reason).
    Evidence: .ai/evidence/quality/quality_report.json with non-empty 'overall' field.
    """
    quality_json = root / ".ai" / "evidence" / "quality" / "quality_report.json"
    if not quality_json.exists():
        return False, (
            "缺少 quality-engineer 的结构化输出："
            f"{quality_json.relative_to(root)} 不存在。"
            "请运行 quality-engineer 质量门禁检查（run_quality_gates.py）"
            "并生成 quality_report.json。"
        )

    try:
        report = json.loads(quality_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError) as e:
        return False, (
            f"quality_report.json 无法解析：{e}。"
            "请重新运行 quality-engineer 生成有效报告。"
        )

    overall = report.get("overall")
    if overall is None or (isinstance(overall, str) and not overall.strip()):
        return False, (
            "quality_report.json 存在但 'overall' 字段为空。"
            "quality-engineer 报告不完整，请重新运行质量门禁。"
        )

    return True, f"质量证据已通过（overall={overall}）"


def check_delivery_gate_evidence(root: Path) -> tuple[bool, str]:
    """Check that S6-delivery phase has delivery-manager go_nogo decision.

    Returns (has_evidence, reason).
    Evidence priority:
    1. .ai/evidence/release/<version>/release_decision.json with 'decision' field
    2. .ai/certifications/state.yaml delivery-manager state=CERTIFIED
    """
    # 1. Check for release_decision.json
    release_dir = root / ".ai" / "evidence" / "release"
    if release_dir.is_dir():
        for version_dir in sorted(release_dir.iterdir(), reverse=True):
            if version_dir.is_dir():
                decision_file = version_dir / "release_decision.json"
                if decision_file.exists():
                    try:
                        decision = json.loads(decision_file.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, IOError):
                        continue
                    go_nogo = decision.get("decision")
                    if go_nogo:
                        return True, (
                            f"交付决策已存在（decision={go_nogo}，"
                            f"版本={version_dir.name}）"
                        )

    # 2. Check certifications/state.yaml for delivery-manager
    cert_file = root / ".ai" / "certifications" / "state.yaml"
    if cert_file.exists():
        try:
            import yaml  # type: ignore
            with open(cert_file, "r", encoding="utf-8") as f:
                cert_data = yaml.safe_load(f) or {}
        except Exception:
            cert_data = {}

        # Try PyYAML first
        if cert_data:
            roles = cert_data.get("roles", {})
            dm = roles.get("delivery-manager", {})
            if isinstance(dm, dict) and dm.get("state") == "CERTIFIED":
                return True, (
                    "交付经理认证状态为 CERTIFIED（"
                    f"last_challenge={dm.get('last_challenge', 'N/A')}）"
                )
            return False, (
                "delivery-manager 尚未签署 GO/NOGO 决定。"
                "请运行 delivery-manager 完成发布决策检查并生成 release_decision.json。"
            )
        else:
            # Fallback: text scan
            try:
                text = cert_file.read_text(encoding="utf-8")
            except Exception:
                text = ""
            if "delivery-manager:" in text and "state: CERTIFIED" in text:
                return True, "交付经理认证状态为 CERTIFIED（文本检测）"

    return False, (
        "缺少 delivery-manager 的 GO/NOGO 决策证据。"
        "请运行 delivery-manager 完成发布决策检查："
        "生成 release_decision.json（decision=GO/NOGO）"
        "或确保 certifications/state.yaml 中 delivery-manager 已 CERTIFIED。"
    )


def check_phase_gate_enforcement(root: Path, phase: str) -> tuple[bool, str]:
    """Check phase-specific gate evidence requirements.

    Returns (can_proceed, reason). can_proceed=False means writes should be
    restricted to governance files only.
    """
    phase = (phase or "").strip()

    if phase == "S5-quality":
        return check_quality_gate_evidence(root)

    if phase == "S6-delivery":
        return check_delivery_gate_evidence(root)

    # Other phases: no additional gate checks at this level
    return True, ""


def main():
    hook_input = read_stdin_json()
    root = project_root(hook_input)

    # ── 自愈：自动同步本地 hook → 插件缓存（解决"改本地不改缓存"的死锁）──
    auto_sync_to_plugin_cache(root)

    try:
        if not is_governance_project(root):
            return EXIT_PASS

        if not is_loop_mode_enforced(root):
            return EXIT_PASS  # LIGHTWEIGHT mode or unset

        target = extract_target_path(hook_input)
        rel = normalize_rel(root, target) if target else None

        # ── 路径安全检查：目标明确在项目根外 → 阻断 ──
        if target is not None and not is_path_safe(root, target):
            logger.warning(
                "BLOCKED: Target '%s' is outside the project root. "
                "Writing outside the project boundary is not allowed.",
                target,
            )
            return EXIT_BLOCK

        # ── Bash 只读命令：目标为 None 且命令是只读的 → 直接放行 ──
        # 注意：ZCode hook_input 中没有 tool_name 字段，直接用 command 判断
        command = (hook_input.get("tool_input") or {}).get("command", "")
        if command and target is None:
            if is_readonly_command(command):
                return EXIT_PASS

        # Always allow governance file writes
        if is_governance_write(rel):
            return EXIT_PASS

        # ── Load state for both HardConstraints and fallback ──
        try:
            state = load_state(root)
        except Exception:
            state = {}

        current_phase = state.get("current_phase", "")
        task_id = state.get("current_task_id")

        # ── HardConstraints Integration ──
        # 作为补充检查：HardConstraints 检测到 BLOCKER 时直接阻断。
        # HardConstraints 通过时，继续执行下方现有逻辑作为最终裁决。
        # 渐进式迁移：新旧逻辑并存，HardConstraints 不可用时退化到现有逻辑。
        if _HARD_CONSTRAINTS_AVAILABLE:
            try:
                hc = _HardConstraints()
                contract = load_task_contract(root, task_id) if task_id else None

                # 加载 task_graph 中的任务列表
                tasks = load_tasks_for_context(root)

                # 渐进迁移桥接：仅当 task_graph.yaml 不存在时（旧项目），
                # 若 task_id + contract 存在，合成一个 active 任务以维持兼容。
                # task_graph.yaml 存在时，完全信任其内容（不再桥接）。
                task_graph_exists = (root / ".ai" / "task_graph.yaml").exists()
                if not task_graph_exists and task_id and contract is not None:
                    active_in_graph = any(
                        t.get("status") in ("active", "in_progress")
                        for t in tasks
                    )
                    if not active_in_graph:
                        tasks.append({
                            "id": task_id,
                            "status": "active",
                            "_synthetic": True,
                        })

                # 构造 HardConstraints 所需的 context
                # 注意：loop_enforcement 负责 C3（任务范围）和 C4（路径范围），
                # 不负责阶段切换检查（C1/C2/C5/C6）。传递 current_phase=None
                # 可跳过这些阶段相关的约束检查。
                context = {
                    "current_phase": None,          # 跳过 C1/C2/C6 阶段检查
                    "target_phase": None,           # loop_enforcement 不涉及阶段切换
                    "phase_gates": {},              # 不触发 C1/C2
                    "gates": load_gates_for_context(root),
                    "tasks": tasks,
                    "target_path": rel or target,
                    "allowed_paths": contract.get("allowed_paths", []) if contract else [],
                    "quality_results": {},
                    "review_status": {},
                    "evidence_list": [],
                    "current_hashes": {},
                }

                result = hc.check_all(context)

                if not result.passed:
                    for v in result.violations:
                        if v.severity == _Severity.BLOCKER:
                            logger.warning(
                                "[HardConstraints] BLOCKER by %s: %s",
                                v.constraint_id.value, v.message,
                            )
                    # 有 BLOCKER 级别违规 → 阻断
                    logger.warning(
                        "BLOCKED: HardConstraints 检测到 %d 个 BLOCKER 违规",
                        result.blocker_count,
                    )
                    return EXIT_BLOCK

                # HardConstraints 通过 → 继续下方现有逻辑作为最终裁决
                logger.debug(
                    "HardConstraints passed (blockers=%d, warnings=%d)",
                    result.blocker_count, result.warning_count,
                )
            except Exception as e:
                # 注意：此异常处理是功能性的（非安全相关）。
                # HardConstraints 是渐进式迁移的增强层，其内部异常不应阻断
                # 现有的 fallback 逻辑。因此此处保持 fail-open（回退到下方现有逻辑）。
                logger.warning(
                    "[warn] HardConstraints 执行异常，回退到现有逻辑：%s", e
                )
                # 回退到下方的现有逻辑 —— 不 return

        # ── 现有 Phase Gate Enforcement（始终执行，作为最终裁决）──

        if current_phase:
            can_proceed, reason = check_phase_gate_enforcement(root, current_phase)
            if not can_proceed:
                logger.warning(
                    "BLOCKED: 当前阶段 %s 需要门禁证据，"
                    "但证据不完整。%s",
                    current_phase, reason,
                )
                return EXIT_BLOCK

        # ── Task Scope Enforcement ──

        if not task_id:
            logger.warning(
                "BLOCKED: Loop mode is FULL/STANDARD, "
                "but no current_task_id is set. Create a task and get gate approval first."
            )
            return EXIT_BLOCK

        # ── Agent/Skill 编排工具豁免 ──
        # Agent/Skill/Task 工具不直接写入文件；子代理/技能的每次文件写入
        # 都会被各自的 PreToolUse hook 独立拦截。
        # 此处只需确认目标任务存在且活跃，放行编排层调用。
        # 修复了原设计中 extract_target_path() 对非文件型工具返回 None
        # 导致 is_in_task_scope(None, ...) 恒返回 False 的死锁问题。
        tool_name = hook_input.get("tool_name", "")
        if tool_name in ("Agent", "Skill", "Task") and target is None and not command:
            return EXIT_PASS

        contract = load_task_contract(root, task_id)
        if contract is None:
            logger.warning(
                "BLOCKED: Task file %s.md not found. Cannot verify write scope.",
                task_id,
            )
            return EXIT_BLOCK

        # ── C11: File Write Limit Check ──
        # Governance files are already exempted above (is_governance_write),
        # so this check only applies to non-governance file writes.
        if rel is not None:
            max_files = _read_task_max_files(root, task_id)
            if max_files is not None:
                current_count = _read_file_write_count(root, task_id)
                if current_count >= max_files:
                    logger.warning(
                        "BLOCKED: Task '%s' has reached its file write limit "
                        "(%d/%d files written). "
                        "Update the task contract's max_files or split the task.",
                        task_id, current_count, max_files,
                    )
                    return EXIT_BLOCK
                # Increment the counter (write will proceed)
                _increment_file_write_count(root, task_id, rel)

        if not is_in_task_scope(rel, contract):
            logger.warning(
                "BLOCKED: Target '%s' is NOT in the allowed scope "
                "of task %s. Allowed: %s. "
                "Update the task contract or create a new task with appropriate scope.",
                rel, task_id, contract.get('allowed_paths', []),
            )
            return EXIT_BLOCK

        return EXIT_PASS

    except Exception:
        if should_fail_closed(root):
            return EXIT_BLOCK
        return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
