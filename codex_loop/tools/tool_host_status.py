"""loop_host_status -- Report host integration capabilities and enforcement level."""
import sys
from pathlib import Path


def run(host_preset: str = "codex") -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from codex_loop.core.enforcement import HOST_PRESETS, validate_host_capabilities

    caps = HOST_PRESETS.get(host_preset)
    if caps is None:
        return {"error": f"Unknown host preset: {host_preset}", "available": list(HOST_PRESETS.keys())}

    level = caps.enforcement_level()
    result = validate_host_capabilities(caps)

    return {
        "host": host_preset,
        "enforcement_level": level.value,
        "capabilities": {
            "can_intercept_writes": caps.can_intercept_writes,
            "can_intercept_commands": caps.can_intercept_commands,
            "can_isolate_agents": caps.can_isolate_agents,
            "can_enforce_exit_codes": caps.can_enforce_exit_codes,
            "has_hooks_api": caps.has_hooks_api,
        },
        "is_honest": result.is_honest,
        "available_presets": list(HOST_PRESETS.keys()),
    }
