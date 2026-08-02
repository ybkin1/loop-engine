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
_MEMORY_INJECTION_DEFAULT = {"enabled": False, "phases": [], "memory_limit": 5}


def _load_memory_injection_config(project_root: str | Path) -> dict:
    """Read the ``memory_injection`` config section (repo source, then installed copy).

    First readable candidate wins:
      <root>/skills/loop-governance/config.yaml
      <root>/.zcode/skills/loop-governance/config.yaml
    Missing or corrupt config → disabled (fail-closed: same as status quo).
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
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            cfg = doc.get("memory_injection")
            if not isinstance(cfg, dict):
                return dict(_MEMORY_INJECTION_DEFAULT)
            return {
                "enabled": bool(cfg.get("enabled", False)),
                "phases": [str(p) for p in (cfg.get("phases") or [])],
                "memory_limit": int(cfg.get("memory_limit", 5)),
            }
        except (OSError, yaml.YAMLError, ValueError, TypeError):
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