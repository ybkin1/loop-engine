from __future__ import annotations

import os
import sys
import time
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from codex_loop.governance.governor_lib import (
    GovernanceError, REQUIRED_FILES, ai_dir, current_task_id,
    governance_invariant_errors,
    load_yaml, pending_gates, project_root_arg, read_text,
)


# ── Role Contract Checks ──────────────────────────────────────────────────

# Known top-level dimensions of PROJECT_MAP (from loop_core/project_map_schema.py)
KNOWN_PROJECT_MAP_DIMENSIONS = {"project", "pages", "api_endpoints", "modules", "database"}

# Required fields every CONTRACT.yaml must include
CONTRACT_REQUIRED_FIELDS = [
    "identity",
    "fixed_stance",
    "responsibilities",
    "prohibitions",
    "veto_power",
    "input_artifacts",
    "output_artifacts",
    "quality_standards",
    "projection_rules",
]

# Markers indicating a potentially stale contract
STALE_MARKERS = [
    "deprecated", "obsolete", "todo: update", "outdated",
    "待更新", "已废弃", "过时",
]

# Maximum age (days) before a contract is flagged as stale
MAX_CONTRACT_AGE_DAYS = 90


def _agent_role_dirs(root: Path) -> list[Path]:
    """Return sorted list of agent role directories under agents/, excluding references/."""
    agents_dir = root / "agents"
    if not agents_dir.exists():
        return []
    result = []
    for entry in sorted(agents_dir.iterdir()):
        if entry.is_dir() and entry.name != "references":
            result.append(entry)
    return result


def check_role_contract_freshness(root: Path) -> list[str]:
    """检查所有角色合同的新鲜度。

    检查项：
    1. 每个 agents/{role_id}/CONTRACT.yaml 是否存在
    2. 合同的 last_modified 时间是否在合理范围内
    3. 合同的 phase 字段（如有）是否与当前项目阶段匹配
    4. 合同内容是否有明显过时标记
    """
    errors: list[str] = []
    base = ai_dir(root)
    state = load_yaml(base / "state.yaml")
    current_phase = state.get("current_phase", "")

    for role_dir in _agent_role_dirs(root):
        role_name = role_dir.name
        contract_path = role_dir / "CONTRACT.yaml"

        if not contract_path.exists():
            continue  # handled by check_role_file_existence

        # 1. Check last_modified time
        try:
            mtime = contract_path.stat().st_mtime
            age_days = (time.time() - mtime) / 86400.0
            if age_days > MAX_CONTRACT_AGE_DAYS:
                errors.append(
                    f"[warn] Role contract for '{role_name}' is {age_days:.0f} days old "
                    f"(threshold: {MAX_CONTRACT_AGE_DAYS} days — may need review)"
                )
        except OSError:
            errors.append(f"[warn] Cannot read modification time for '{role_name}/CONTRACT.yaml'")

        # 2. Check phase field matches current project phase
        try:
            contract = load_yaml(contract_path)
        except Exception:
            errors.append(f"[warn] Cannot parse '{role_name}/CONTRACT.yaml' (possibly corrupt)")
            continue
        if isinstance(contract, dict):
            contract_phase = contract.get("phase", "")
            if contract_phase and current_phase and str(contract_phase) != current_phase:
                errors.append(
                    f"[warn] Role '{role_name}' contract phase '{contract_phase}' "
                    f"does not match current project phase '{current_phase}'"
                )

        # 3. Check for obvious stale markers in contract content
        try:
            content = read_text(contract_path).lower()
        except Exception:
            errors.append(f"[warn] Cannot read '{role_name}/CONTRACT.yaml' (possibly corrupt)")
            continue
        for marker in STALE_MARKERS:
            if marker in content:
                errors.append(
                    f"[warn] Role '{role_name}' contract contains stale marker: '{marker}'"
                )
                break

    return errors


def check_role_contract_completeness(root: Path) -> list[str]:
    """检查所有角色合同的完整性。

    每个 CONTRACT.yaml 至少包含：
    - identity, fixed_stance, responsibilities, prohibitions,
      veto_power, input_artifacts, output_artifacts,
      quality_standards, projection_rules
    """
    errors: list[str] = []

    for role_dir in _agent_role_dirs(root):
        role_name = role_dir.name
        contract_path = role_dir / "CONTRACT.yaml"

        if not contract_path.exists():
            continue  # handled by check_role_file_existence

        try:
            contract = load_yaml(contract_path)
        except Exception:
            errors.append(f"[warn] Cannot parse '{role_name}/CONTRACT.yaml' (possibly corrupt or empty)")
            continue

        if not isinstance(contract, dict):
            errors.append(f"[warn] '{role_name}/CONTRACT.yaml' is not a valid YAML mapping")
            continue

        if not contract:
            errors.append(f"[warn] '{role_name}/CONTRACT.yaml' is empty")
            continue

        missing = [field for field in CONTRACT_REQUIRED_FIELDS if field not in contract]
        if missing:
            errors.append(
                f"[warn] Role '{role_name}' CONTRACT.yaml missing required fields: {', '.join(missing)}"
            )

    return errors


def check_role_file_existence(root: Path) -> list[str]:
    """检查每个已注册角色是否都有完整的 3 个文件。

    对于 agents/ 下每个目录（排除 references/）：
    - CONTRACT.yaml 必须存在
    - THINKING_FRAMEWORK.md 必须存在
    - INTERNAL_LOOP.md 必须存在
    """
    errors: list[str] = []
    REQUIRED_ROLE_FILES = ["CONTRACT.yaml", "THINKING_FRAMEWORK.md", "INTERNAL_LOOP.md"]

    for role_dir in _agent_role_dirs(root):
        role_name = role_dir.name
        missing_files = [f for f in REQUIRED_ROLE_FILES if not (role_dir / f).exists()]
        if missing_files:
            errors.append(
                f"[warn] Role '{role_name}' missing files: {', '.join(missing_files)}"
            )

    return errors


def check_cross_role_consistency(root: Path) -> list[str]:
    """跨角色一致性检查。

    1. 没有两个角色有相同的 role_id
    2. 角色的投影规则覆盖所有 PROJECT_MAP 维度
    3. 每个质量维度至少有一个角色负责
    4. veto_power 没有循环依赖
    """
    errors: list[str] = []
    role_data: dict[str, dict] = {}  # role_id -> contract dict

    for role_dir in _agent_role_dirs(root):
        contract_path = role_dir / "CONTRACT.yaml"
        if not contract_path.exists():
            continue
        try:
            contract = load_yaml(contract_path)
        except Exception:
            continue
        if not isinstance(contract, dict):
            continue

        role_id = contract.get("role_id", role_dir.name)

        # 1. Check for duplicate role_ids
        if role_id in role_data:
            errors.append(
                f"[warn] Duplicate role_id '{role_id}': found in both "
                f"'{role_data[role_id].get('_dir', '?')}' and '{role_dir.name}'"
            )
        else:
            contract["_dir"] = role_dir.name
            role_data[role_id] = contract

    # 2. Projection rules coverage: check that known PROJECT_MAP dimensions
    #    are covered by at least one role's include_sections
    covered_dimensions: set[str] = set()
    all_include_sections: list[set[str]] = []
    all_exclude_sections: list[set[str]] = []

    for role_id, contract in role_data.items():
        proj = contract.get("projection_rules", {})
        if isinstance(proj, dict):
            includes = proj.get("include_sections", [])
            excludes = proj.get("exclude_sections", [])
            if isinstance(includes, list):
                sections = set()
                for item in includes:
                    # Normalize: strip wildcard path (e.g. "modules.*.id" -> "modules")
                    sections.add(str(item).split(".")[0])
                all_include_sections.append(sections)
                covered_dimensions |= sections
            if isinstance(excludes, list):
                sections = set(str(item).split(".")[0] for item in excludes)
                all_exclude_sections.append(sections)

    # Dimensions not covered by any role's include_sections
    uncovered = KNOWN_PROJECT_MAP_DIMENSIONS - covered_dimensions
    if uncovered:
        # Check if all roles collectively exclude a dimension (meaning it's not needed)
        universally_excluded: set[str] = KNOWN_PROJECT_MAP_DIMENSIONS.copy()
        for exc_set in all_exclude_sections:
            universally_excluded &= exc_set
        truly_uncovered = uncovered - universally_excluded
        if truly_uncovered:
            errors.append(
                f"[warn] PROJECT_MAP dimensions not covered by any role projection: "
                f"{', '.join(sorted(truly_uncovered))}"
            )

    # 3. Each quality dimension should have at least one role responsible.
    #    Quality dimensions are roles whose projection_rules contain quality-related
    #    dimension fields (quality_dimensions, etc.)
    has_quality_role = False
    for role_id, contract in role_data.items():
        proj = contract.get("projection_rules", {})
        if isinstance(proj, dict):
            for key in proj:
                if str(key).endswith("_dimensions"):
                    has_quality_role = True
                    break
        if has_quality_role:
            break
    if not has_quality_role and role_data:
        errors.append(
            "[warn] No role has quality-related dimensions (e.g. quality_dimensions) "
            "in their projection_rules — quality coverage may be unassigned"
        )

    # 4. Veto power circular dependency check (requires at least 2 roles).
    if len(role_data) >= 2:
        veto_refs: dict[str, set[str]] = {}  # role_id -> set of referenced role_ids
        for role_id, contract in role_data.items():
            refs: set[str] = set()
            # Check veto_power for references to other roles
            veto_power = contract.get("veto_power", [])
            if isinstance(veto_power, list):
                for condition in veto_power:
                    condition_str = str(condition).lower()
                    for other_id in role_data:
                        if other_id != role_id and other_id in condition_str:
                            refs.add(other_id)
            # Check veto_escalation
            veto_esc = contract.get("veto_escalation", [])
            if isinstance(veto_esc, list):
                for item in veto_esc:
                    item_str = str(item).lower()
                    for other_id in role_data:
                        if other_id != role_id and other_id in item_str:
                            refs.add(other_id)
            if refs:
                veto_refs[role_id] = refs

        # Detect cycles in veto_refs using DFS
        if veto_refs:
            def _has_cycle(node: str, visited: set[str], stack: set[str]) -> bool:
                visited.add(node)
                stack.add(node)
                for neighbor in veto_refs.get(node, set()):
                    if neighbor not in visited:
                        if _has_cycle(neighbor, visited, stack):
                            return True
                    elif neighbor in stack:
                        return True
                stack.discard(node)
                return False

            visited: set[str] = set()
            for role_id in veto_refs:
                if role_id not in visited:
                    if _has_cycle(role_id, visited, set()):
                        errors.append(
                            f"[warn] Circular veto dependency detected involving role '{role_id}'"
                        )
                        break  # one cycle is enough to flag

    return errors


def main() -> int:
    args = project_root_arg().parse_args()
    root = Path(args.project_root).resolve()
    base = ai_dir(root)
    errors = []

    # 1. Check required files
    for relative in REQUIRED_FILES:
        if not (base / relative).exists():
            errors.append(f"Missing .ai/{relative}")

    # 2. Check state
    state = load_yaml(base / "state.yaml")
    phase = state.get("current_phase")
    task_id = current_task_id(root)
    if not phase:
        errors.append("state.yaml missing current_phase")
    if task_id and not (base / "tasks" / f"{task_id}.md").is_file():
        errors.append(f"Current task file missing: .ai/tasks/{task_id}.md")

    # 3. Check pending gates (BLOCKER)
    pending = pending_gates(root)
    if pending:
        errors.append(
            "Pending gate(s) require user decision before continuing: "
            + ", ".join(str(item.get("id")) for item in pending)
        )

    # 4. Governance invariants (skip ProjectContinuity check for S0-init)
    errors.extend(governance_invariant_errors(root))

    # 4.5 Task contract checks (self-review prevention + input freezing)
    if task_id:
        try:
            from task_contract import check_self_review, check_input_freezing, load_task
            contract = load_task(root, task_id)
            if contract:
                errors.extend(check_self_review(contract))
                errors.extend(check_input_freezing(root, task_id, contract))
        except ImportError:
            pass  # task_contract.py not available yet
        except Exception as e:
            errors.append(f"[warn] task_contract check failed: {e}")

    # 5. ProjectContinuity — skip in S0-init (too heavy for fresh project)
    continuity_path = base / "project_continuity.yaml"
    repair_mode = "--repair" in sys.argv or os.environ.get("LOOP_REPAIR_CONTINUITY") == "1"
    if continuity_path.exists():
        try:
            from continuity_producer import load_project_continuity
            load_project_continuity(root)
        except (GovernanceError, ImportError) as exc:
            err_code = str(getattr(exc, 'code', ''))
            # v3.5: REPAIR_MODE — auto-repair continuity drift instead of hard-blocking
            if repair_mode and "SOURCE_DRIFT" in err_code:
                try:
                    from repair_continuity import repair_continuity
                    result = repair_continuity(root)
                    if result.get("fixed", 0) > 0:
                        print(f"[loop-governance] [repair] Auto-repaired {result['fixed']} drifted hash(es).")
                        # Re-validate after repair
                        load_project_continuity(root)
                    else:
                        errors.append(f"ProjectContinuity invalid: {exc} (auto-repair found nothing to fix)")
                except Exception as re:
                    errors.append(f"ProjectContinuity invalid: {exc} (auto-repair failed: {re})")
            else:
                errors.append(f"ProjectContinuity invalid: {exc}")
    else:
        print("[loop-governance] [info] ProjectContinuity not yet created (expected in S0-init)")

    # 6. Handoff audit - SKIPPED in S0/S1 phases
    # Structured handoff contracts require transactional writes to avoid
    # circular hash dependencies (HANDOFF <-> project_continuity).
    # Will be re-enabled when continuity_producer supports atomic writes.
    # See .ai/KNOWN_ISSUES.md
    pass

    # 7. Role contract freshness and completeness checks
    if (root / "agents").exists():
        errors.extend(check_role_contract_freshness(root))
        errors.extend(check_role_contract_completeness(root))
        errors.extend(check_role_file_existence(root))
        errors.extend(check_cross_role_consistency(root))

    # Report
    print(f"[loop-governance] project_root: {root}")
    print(f"[loop-governance] phase: {phase or 'unknown'}")
    print(f"[loop-governance] current_task_id: {task_id or 'none'}")

    blocker_errors = [e for e in errors if not str(e).startswith("[warn]") and not str(e).startswith("[legacy]")]
    warn_errors = [e for e in errors if str(e).startswith("[warn]")]

    for error in warn_errors:
        print(error)
    for error in list(dict.fromkeys(blocker_errors)):
        print(f"[error] {error}")

    if blocker_errors:
        return 2
    print("[ok] state is usable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
