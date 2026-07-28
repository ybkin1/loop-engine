"""loop_certify_role — Run capability certification for a role."""
import sys
from pathlib import Path


def run(role_id: str, project_root: str = ".") -> dict:
    """Run the capability challenge for a role and return results."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from codex_loop.core.role_capability import (
        ROLE_CHALLENGES, load_all_profiles,
    )

    if role_id == "all":
        profiles = load_all_profiles(project_root)
        results = {}
        for rid, profile in profiles.items():
            if rid in ROLE_CHALLENGES:
                allowed, reason = profile.can_accept_production_task()
                results[rid] = {
                    "role_id": rid,
                    "status": profile.status.value,
                    "can_accept": allowed,
                    "reason": reason,
                    "challenge": ROLE_CHALLENGES[rid].description,
                }
        return {"overall": "summary", "roles": results}

    challenge = ROLE_CHALLENGES.get(role_id)
    if not challenge:
        return {"error": f"No challenge defined for role '{role_id}'", "available": list(ROLE_CHALLENGES.keys())}

    profiles = load_all_profiles(project_root)
    profile = profiles.get(role_id)
    if not profile:
        from codex_loop.core.role_capability import RoleCapabilityProfile
        profile = RoleCapabilityProfile(role_id=role_id)

    return {
        "role_id": role_id,
        "status": profile.status.value,
        "challenge": challenge.description,
        "seeded_defects": len(challenge.seeded_defects),
        "pass_conditions": challenge.pass_conditions,
        "can_accept_production": profile.can_accept_production_task()[0],
        "degradation_counters": profile.to_dict().get("degradation_counters", {}),
    }
