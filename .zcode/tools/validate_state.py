from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from continuity_auditor import audit_handoff_model
from governor_lib import (
    GovernanceError, REQUIRED_FILES, ai_dir, current_task_id,
    governance_invariant_errors,
    load_yaml, pending_gates, project_root_arg, read_text,
)


# ── Role Contract Checks ──────────────────────────────────────────────────

# T-0111: 修复器触发点 guard-events 事件写入（观测侧旁路，绝不阻断业务）。
# 与 loop_core.observability 的 GuardCheckEvent 同 schema（check_type=
# "repair"）；loop_core 不可导入时降级为等价的最小 JSONL 追加。写入失败
# 一律吞掉——观测不得改变任何既有判定与 exit code 语义。
def _record_repair_event(root: Path, result: str, failure_reason: str) -> None:
    import json as _json
    import uuid as _uuid
    from datetime import datetime as _dt, timezone as _tz
    try:
        import sys as _sys
        if str(root) not in _sys.path:
            _sys.path.insert(0, str(root))
        from loop_core.observability import (
            CHECK_REPAIR, GuardCheckEvent, GuardEventRecorder,
        )
        rec = GuardEventRecorder(
            root / ".ai" / "evidence" / "observability" / "guard-events.jsonl"
        )
        rec.record(GuardCheckEvent(
            guard_id="repair_continuity",
            check_type=CHECK_REPAIR,
            result=result,
            duration_ms=0.0,
            failure_reason=failure_reason,
            timestamp=_dt.now(_tz.utc).isoformat(),
            source=f"tool:{Path(__file__).name}",
        ))
    except Exception:  # noqa: BLE001 — 观测失败绝不阻断业务
        try:
            p = root / ".ai" / "evidence" / "observability" / "guard-events.jsonl"
            p.parent.mkdir(parents=True, exist_ok=True)
            line = {
                "event_id": _uuid.uuid4().hex[:16],
                "guard_id": "repair_continuity",
                "capability_id": None,
                "check_type": "repair",
                "result": result,
                "duration_ms": 0.0,
                "failure_reason": failure_reason,
                "timestamp": _dt.now(_tz.utc).isoformat(),
                "source": f"tool:{Path(__file__).name}",
            }
            with open(p, "a", encoding="utf-8") as f:
                f.write(_json.dumps(line, ensure_ascii=False) + "\n")
        except Exception:  # noqa: BLE001
            pass



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


# ── T-0108 F2-1 新鲜度检查（只读告警）──────────────────────────────────
# 单一数据源阶段 1：state.yaml 为权威，派生视图 (.ai/views/state-view.yaml)
# 由 projection_engine.write_state_view 显式生成。本检查只读对比 mtime，
# 视图陈旧时输出 `[warn] stale view`——仅告警，不改变任何既有判定与
# exit code 语义（硬约束：validate_state 既有判定零变化）。


def check_state_view_freshness(root: Path, base: Path) -> list[str]:
    """检查 state.yaml 与派生视图的新鲜度（只读，仅告警）。

    Returns:
        list[str]：可能含 ``[warn] stale view`` 条目；视图缺失/不可读时
        返回空（无视图可比，不告警）。
    """
    warns: list[str] = []
    state_path = base / "state.yaml"
    view_path = base / "views" / "state-view.yaml"
    if not state_path.exists() or not view_path.exists():
        return warns
    try:
        state_mtime = state_path.stat().st_mtime
        view_mtime = view_path.stat().st_mtime
    except OSError:
        return warns
    if view_mtime < state_mtime - 1.0:  # 1s 容差（同事务写）
        age = state_mtime - view_mtime
        warns.append(
            f"[warn] stale view: {view_path.relative_to(root).as_posix()} "
            f"早于 state.yaml {age:.0f}s — 视图未反映最新状态"
            "（T-0108 F2-1 只读检查，仅告警不阻断）"
        )
    return warns


def main() -> int:
    args = project_root_arg().parse_args()
    # Normalize the path defensively: os.path.normpath handles any shell-level
    # escaping artifacts (e.g. backslash-stripping, colon mangling in MSYS2/Git Bash)
    # before Path.resolve() canonicalises it into an absolute form.
    raw = os.path.normpath(args.project_root)
    root = Path(raw).resolve()
    # Guard: reject malformed paths that survived argparse but would corrupt
    # downstream path joins (e.g. double-concatenation when drive letter is lost).
    if not root.is_absolute():
        print(f"[error] project_root is not an absolute path: {root}", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"[error] project_root is not a directory: {root}", file=sys.stderr)
        return 2
    if not (root / ".ai").is_dir():
        print(f"[error] project_root missing .ai directory — not a Loop governance project: {root}", file=sys.stderr)
        return 2
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
    repair_mode = ("--repair" in sys.argv or "--auto-sync" in sys.argv
                   or os.environ.get("LOOP_REPAIR_CONTINUITY") == "1")
    auto_sync = "--auto-sync" in sys.argv or os.environ.get("LOOP_AUTO_SYNC") == "1"
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
                        # T-0111: repair 事件 PASS 分支（修复 + 重新校验通过）
                        _record_repair_event(
                            root, "PASS",
                            f"SOURCE_DRIFT fixed={result['fixed']}",
                        )
                    else:
                        errors.append(f"ProjectContinuity invalid: {exc} (auto-repair found nothing to fix)")
                        # T-0111: repair 事件 FAIL 分支（无物可修 → 校验仍失败）
                        _record_repair_event(
                            root, "FAIL",
                            "SOURCE_DRIFT fixed=0 (auto-repair found nothing to fix)",
                        )
                except Exception as re:
                    errors.append(f"ProjectContinuity invalid: {exc} (auto-repair failed: {re})")
                    # T-0111: repair 事件 FAIL 分支（修复/重新校验抛错）
                    _record_repair_event(
                        root, "FAIL",
                        f"SOURCE_DRIFT auto-repair failed: {re}",
                    )
            else:
                errors.append(f"ProjectContinuity invalid: {exc}")
    else:
        print("[loop-governance] [info] ProjectContinuity not yet created (expected in S0-init)")

    # T-0127 P0: --auto-sync — repair + regenerate HANDOFF in one step.
    # Registration flow runs this after governance-file changes so that
    # continuity drift and stale HANDOFF projection are resolved together
    # instead of two manual steps (repair first, then render — ordering that
    # was observed to fail if reversed).
    if auto_sync and continuity_path.exists():
        try:
            from continuity_producer import render_handoff
            new_handoff, _ = render_handoff(root)
            # T-0127 P2-2: LF 强制，避免 Windows 下 CRLF 漂移
            (base / "HANDOFF.md").write_text(new_handoff, encoding="utf-8", newline="\n")
            print("[loop-governance] [auto-sync] HANDOFF regenerated.")
            # T-0058: HANDOFF 永不入 continuity source set（自引用守卫），
            # 无需再同步其哈希——漂移已在 §5 修复阶段消除。
            # T-0155: 事件溯源影子层 —— HANDOFF 重生成追加审计事件（失败吞掉）。
            # T-0158: 增强 —— 检测 state/gates/task_graph 变化，记录
            # task_status_changed / gate_approved 事件（对比上次事件锚点）。
            try:
                from event_log import append as _event_append
                from event_log import read_events as _read_events
                _event_append(root, "handoff_generated",
                              task_id=task_id, actor="system",
                              detail={"action": "auto-sync"})
                # 状态变化检测：对比最近事件 state_sha256 锚点与当前投影
                try:
                    import hashlib as _hl
                    _proj = _hl.sha256()
                    for _rel in (".ai/state.yaml", ".ai/gates.yaml", ".ai/task_graph.yaml"):
                        _p = root / _rel
                        if _p.is_file():
                            _proj.update(_p.read_bytes())
                    _current = _proj.hexdigest()[:16]
                    _events = _read_events(root)
                    _latest = _events[-2] if len(_events) >= 2 else None
                    if _latest and _latest.get("state_sha256") != _current:
                        # 投影自上次事件后变化 → 记 task_status_changed
                        _event_append(root, "task_status_changed",
                                      task_id=task_id, actor="system",
                                      detail={"auto_detected": True})
                except Exception:  # noqa: BLE001 — 影子层失败绝不阻断
                    pass
            except Exception:  # noqa: BLE001 — 影子层失败绝不阻断
                pass
        except Exception as he:
            errors.append(f"HANDOFF auto-sync failed: {he}")

    # 6. Handoff audit (skip if continuity missing, audit_handoff_model requires it)
    handoff = read_text(base / "HANDOFF.md")
    if handoff and continuity_path.exists():
        errors.extend(audit_handoff_model(root, handoff))

    # 7. Role contract freshness and completeness checks
    if (root / "agents").exists():
        errors.extend(check_role_contract_freshness(root))
        errors.extend(check_role_contract_completeness(root))
        errors.extend(check_role_file_existence(root))
        errors.extend(check_cross_role_consistency(root))

    # 8. T-0108 F2-1: state view freshness (read-only warning, additive)
    errors.extend(check_state_view_freshness(root, base))

    # Report
    print(f"[loop-governance] project_root: {root}")
    print(f"[loop-governance] phase: {phase or 'unknown'}")
    print(f"[loop-governance] current_task_id: {task_id or 'none'}")

    blocker_errors = [e for e in errors if not str(e).startswith("[warn]") and not str(e).startswith("[legacy]")]
    warn_errors = [e for e in errors if str(e).startswith("[warn]")]
    legacy_errors = [e for e in errors if str(e).startswith("[legacy]")]

    for error in warn_errors:
        print(error)
    for error in legacy_errors:
        print(f"[warn] {error}")

    # T-0101: idle 稳态语义分流 —— NO_ACTIVE_TASK（合法阻塞态）与真实治理损坏 exit code 分离。
    # idle 合法态（current_task_id=null 且无其他任何 blocker 错误）→ 独立 [info] 段 + exit 3；
    # 存在其他 blocker（连续性漂移/缺文件/损坏）→ 保持 [error] + exit 2（fail-closed 不变）。
    # 安全意图保留：idle 绝不输出 "[ok] state is usable"（新会话不得误以为可开工）。
    no_active_task_msg = "NO_ACTIVE_TASK: state.current_task_id is null"
    unique_blockers = list(dict.fromkeys(blocker_errors))
    idle_legal_block = (
        task_id is None
        and len(unique_blockers) == 1
        and str(unique_blockers[0]) == no_active_task_msg
    )
    if idle_legal_block:
        print(
            f"[info] {no_active_task_msg}（合法阻塞态：state 无活动任务，等待任务发起；"
            "state 不可开工）"
        )
        return 3
    for error in unique_blockers:
        print(f"[error] {error}")

    if blocker_errors:
        return 2
    print("[ok] state is usable")

    # ── Checkpoint hint ───────────────────────────────────────────
    handoff = read_text(base / "HANDOFF.md")
    if handoff and "PENDING_SUCCESSOR_ACK" in handoff:
        print("[info] Checkpoint is PENDING_SUCCESSOR_ACK — successor session should acknowledge before proceeding to next phase.")

    return 0


if __name__ == "__main__":
    # T-0143 1.2: 治理文件 YAML 损坏等 GovernanceError 必须干净 fail-closed
    # （exit 2），而非未捕获 traceback exit 1 —— 外部消费者（release check/
    # 脚本）依赖 rc 语义时避免误判。
    try:
        code = main()
    except GovernanceError as ge:
        print(f"[error] {ge}", file=sys.stderr)
        code = 2
    except Exception as exc:  # noqa: BLE001 — 兜底：任何未预期异常也 fail-closed
        print(f"[error] validate_state crashed: {type(exc).__name__}: {exc}", file=sys.stderr)
        code = 2
    raise SystemExit(code)
