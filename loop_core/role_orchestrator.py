"""role_orchestrator.py — T-0075: Auto-dispatch roles based on phase requirements.

Each phase has required roles. The orchestrator determines which roles are needed,
builds context for each, and dispatches them automatically.
"""
import json, logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Phase → required roles mapping
PHASE_ROLES = {
    "S0-init": ["main-thread"],
    "S1-requirements": ["product-manager", "project-manager"],
    "S2-architecture": ["system-architect", "module-architect"],
    "S3-interface": ["module-architect", "system-architect"],
    "S4-implementation": ["developer"],
    "S5-quality": ["quality-engineer", "test-engineer", "security-engineer", "independent-reviewer"],
    "S6-delivery": ["delivery-manager", "release-engineer"],
    "S7-integration": ["test-engineer", "system-architect"],
    "S8-functional-test": ["test-engineer", "quality-engineer"],
    "S9-fix-optimize": ["developer", "quality-engineer"],
    "S10-performance": ["test-engineer", "system-architect"],
    "S11-maintenance": ["developer", "quality-engineer"],
}

# ── Memory injection switch (T-0104 设计-5 §5.3.2) ─────────────────────────
# 非 hook 配置：skills/loop-governance/config.yaml 的 memory_injection 节。
# enabled=false 或配置缺失/损坏 → 完全回退到现状（不注入）。
# T-0105 B-4-4: 进程内读盘缓存（按配置路径 + mtime），mtime 变化才重读。
_MEMORY_INJECTION_DEFAULT = {"enabled": False, "phases": [], "memory_limit": 5}

# T-0105 B-4-4: 配置缓存 — path -> (mtime_ns, cfg)。读取失败清缓存回退 fail-closed。
_CONFIG_CACHE: dict[str, tuple[int, dict]] = {}


def _validated_phases(value) -> list[str]:
    """T-0105 B-4-2: phases 必须是 list；误写为字符串视为非法。

    非法时返回 None，由调用方按 fail-closed 回退 disabled 默认
    （避免 "S4" 被逐字符展开为 ["S", "4"] 的静默错误）。
    """
    if not isinstance(value, list):
        return None
    return [str(p) for p in value]


def _validated_memory_limit(value) -> int:
    """T-0105 B-4-2: memory_limit 非正数/非数字 → 默认 5（其余沿用现状）。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return int(_MEMORY_INJECTION_DEFAULT["memory_limit"])
    try:
        limit = int(value)
    except (ValueError, TypeError, OverflowError):
        return int(_MEMORY_INJECTION_DEFAULT["memory_limit"])
    if limit <= 0:
        return int(_MEMORY_INJECTION_DEFAULT["memory_limit"])
    return limit


def _load_memory_injection_config(project_root: str | Path) -> dict:
    """Read the ``memory_injection`` config section (repo source, then installed copy).

    First readable candidate wins:
      <root>/skills/loop-governance/config.yaml
      <root>/.zcode/skills/loop-governance/config.yaml
    Missing or corrupt config → disabled (fail-closed: same as status quo).

    T-0105 B-4-4: 结果按 (配置路径, mtime) 进程内缓存；mtime 变化才重读；
    读取/解析失败清缓存并回退 fail-closed。
    T-0105 B-4-2: phases 非 list / memory_limit 非法值 → 校验失败回退默认。
    """
    import yaml

    candidates = [
        Path(project_root) / "skills" / "loop-governance" / "config.yaml",
        Path(project_root) / ".zcode" / "skills" / "loop-governance" / "config.yaml",
    ]
    for path in candidates:
        try:
            if not path.exists():
                continue
            key = str(path)
            mtime = path.stat().st_mtime_ns
            cached = _CONFIG_CACHE.get(key)
            if cached is not None and cached[0] == mtime:
                return dict(cached[1])
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            cfg = doc.get("memory_injection")
            if not isinstance(cfg, dict):
                result = dict(_MEMORY_INJECTION_DEFAULT)
                _CONFIG_CACHE[key] = (mtime, result)
                return result
            phases = _validated_phases(cfg.get("phases") or [])
            if phases is None:
                # T-0105 B-4-2: phases 误写为字符串等非法形态 → 整体回退 disabled
                result = dict(_MEMORY_INJECTION_DEFAULT)
                _CONFIG_CACHE[key] = (mtime, result)
                return result
            result = {
                "enabled": bool(cfg.get("enabled", False)),
                "phases": phases,
                "memory_limit": _validated_memory_limit(cfg.get("memory_limit", 5)),
            }
            _CONFIG_CACHE[key] = (mtime, result)
            return result
        except (OSError, yaml.YAMLError, ValueError, TypeError):
            _CONFIG_CACHE.pop(str(path), None)
            return dict(_MEMORY_INJECTION_DEFAULT)
    return dict(_MEMORY_INJECTION_DEFAULT)


def _memory_injection_for(
    phase: str, project_root: str | Path = ""
) -> tuple[bool, int]:
    """Return (include_memories, memory_limit) for a phase under the config switch.

    Phase matching is by prefix (e.g. "S4-implementation" ↔ config "S4"),
    so both full and short phase ids work.
    """
    cfg = _load_memory_injection_config(project_root)
    phase_key = str(phase).split("-", 1)[0]
    return (cfg["enabled"] and phase_key in set(cfg["phases"]), cfg["memory_limit"])

def get_roles_for_phase(phase: str) -> list[str]:
    """Return the list of role IDs required for a given phase."""
    return PHASE_ROLES.get(phase, [])

def build_dispatch_manifest(project_root: str, phase: str, task_id: str = "",
                            extra_files: list[str] = None) -> dict:
    """Build a SubagentManifest for the current phase.
    
    Returns a manifest ready for loop_dispatch_agents MCP tool.
    """
    roles = get_roles_for_phase(phase)
    if not roles:
        return {"manifest_id": f"auto-{phase}", "subagents": [], "note": "No roles required for this phase"}
    
    from loop_core.role_loader import load_role_prompt_with_context

    # T-0104 设计-5: S4+ 阶段（config memory_injection.phases）显式开启记忆注入；
    # enabled=false 或配置缺失 → include_memories=False，行为与现状完全一致。
    include_memories, memory_limit = _memory_injection_for(phase, project_root)

    subagents = []
    for role_id in roles:
        if role_id == "main-thread":
            continue  # main-thread is the orchestrator, not a sub-agent
        try:
            # T-0105 B-4-1: task_id 一并透传到 context_packager.build_context，
            # 记忆召回按当前任务过滤（消除跨任务不相关记忆注入）。
            prompt = load_role_prompt_with_context(
                role_id, project_root=project_root, task_id=task_id,
                extra_files=extra_files,
                include_memories=include_memories,
                memory_limit=memory_limit,
            )
            subagents.append({
                "subagent_id": f"{role_id}-{phase}",
                "role_hint": role_id,
                "prompt": prompt,
            })
        except Exception as e:
            logger.warning("Failed to build context for %s: %s", role_id, e)
    
    return {
        "manifest_id": f"auto-{phase}-{task_id}",
        "phase": phase,
        "subagents": subagents,
        "total": len(subagents),
    }

def get_next_actions(phase: str, task_id: str = "") -> dict:
    """Return the next actions the main-thread should take for a phase.
    
    Returns a dict with:
    - roles_to_dispatch: list of role IDs to dispatch
    - instruction: what the main-thread should do
    - auto_dispatch: whether roles can be auto-dispatched
    """
    roles = get_roles_for_phase(phase)
    return {
        "phase": phase,
        "task_id": task_id,
        "roles_to_dispatch": [r for r in roles if r != "main-thread"],
        "instruction": f"Phase {phase}: dispatch {len(roles)-1} role(s) and collect results.",
        "auto_dispatch": True,
    }