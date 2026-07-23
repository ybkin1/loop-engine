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
import sys
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_common import (
    DEFAULT_CONFIG,
    extract_target_path,
    is_governance_project,
    load_config,
    load_state,
    normalize_rel,
    project_root,
    read_stdin_json,
)

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
        return True  # No explicit restrictions = allow (backward compatible)
    for path in allowed:
        path = path.replace("\\", "/").lstrip("./")
        if rel_path == path or rel_path.startswith(path.rstrip("/") + "/"):
            return True
    return False


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

    if not is_governance_project(root):
        return EXIT_PASS

    if not is_loop_mode_enforced(root):
        return EXIT_PASS  # LIGHTWEIGHT mode or unset

    target = extract_target_path(hook_input)
    rel = normalize_rel(root, target) if target else None

    # Always allow governance file writes
    if is_governance_write(rel):
        return EXIT_PASS

    # ── Phase Gate Enforcement ──
    # Check if current phase requires mandatory evidence before writes.
    try:
        state = load_state(root)
    except Exception:
        state = {}

    current_phase = state.get("current_phase", "")
    task_id = state.get("current_task_id")

    if current_phase:
        can_proceed, reason = check_phase_gate_enforcement(root, current_phase)
        if not can_proceed:
            print(
                f"[loop_enforcement] BLOCKED: 当前阶段 {current_phase} 需要门禁证据，"
                f"但证据不完整。{reason}",
                file=sys.stderr,
            )
            return EXIT_BLOCK

    # ── Task Scope Enforcement ──

    if not task_id:
        print(
            "[loop_enforcement] BLOCKED: Loop mode is FULL/STANDARD, "
            "but no current_task_id is set. Create a task and get gate approval first.",
            file=sys.stderr,
        )
        return EXIT_BLOCK

    contract = load_task_contract(root, task_id)
    if contract is None:
        print(
            f"[loop_enforcement] BLOCKED: Task file {task_id}.md not found. "
            "Cannot verify write scope.",
            file=sys.stderr,
        )
        return EXIT_BLOCK

    if not is_in_task_scope(rel, contract):
        print(
            f"[loop_enforcement] BLOCKED: Target '{rel}' is NOT in the allowed scope "
            f"of task {task_id}. Allowed: {contract.get('allowed_paths', [])}. "
            "Update the task contract or create a new task with appropriate scope.",
            file=sys.stderr,
        )
        return EXIT_BLOCK

    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
