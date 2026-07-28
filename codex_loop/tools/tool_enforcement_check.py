"""loop_enforcement_check -- Check host enforcement level and hard constraints."""
import sys
from pathlib import Path


def run(project_root: str = ".", host_preset: str = None, constraint_id: str = None) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from codex_loop.core.enforcement import HOST_PRESETS, validate_host_capabilities

    caps = HOST_PRESETS.get(host_preset, HOST_PRESETS["standalone"]) if host_preset else HOST_PRESETS["codex"]
    level = caps.enforcement_level()
    result = validate_host_capabilities(caps)

    return {
        "host_preset": host_preset or "codex",
        "enforcement_level": level.value,
        "capabilities": {
            "can_intercept_writes": caps.can_intercept_writes,
            "can_intercept_commands": caps.can_intercept_commands,
            "can_isolate_agents": caps.can_isolate_agents,
            "can_enforce_exit_codes": caps.can_enforce_exit_codes,
            "has_hooks_api": caps.has_hooks_api,
        },
        "is_honest": result.is_honest,
        "is_blocked": result.is_blocked,
    }
