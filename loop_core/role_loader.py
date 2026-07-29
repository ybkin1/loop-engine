"""
role_loader.py — Load role identity (SKILL.md + CONTRACT.yaml) as Agent prompt.

Usage:
    from loop_core.role_loader import load_role_prompt
    prompt = load_role_prompt("independent-reviewer", task_id="T-0061", input_files=["src/main.py"])
    # Then: Agent("general-purpose", prompt)
"""

import json
from pathlib import Path
from typing import Optional


def _find_agents_root() -> Path:
    """Find the agents/ directory from this file's location."""
    current = Path(__file__).resolve().parent.parent  # loop_core -> project root
    agents_dir = current / "agents"
    if not agents_dir.exists():
        raise FileNotFoundError(f"agents/ directory not found at {agents_dir}")
    return agents_dir


AVAILABLE_ROLES = [
    "main-thread", "product-manager", "project-manager", "system-architect",
    "module-architect", "developer", "quality-engineer", "test-engineer",
    "security-engineer", "independent-reviewer", "delivery-manager", "release-engineer",
]


def list_roles() -> list[str]:
    """List all available role IDs."""
    agents_root = _find_agents_root()
    roles = []
    for d in sorted(agents_root.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            roles.append(d.name)
    return roles


def load_role_skill(role_id: str) -> str:
    """Load a role's SKILL.md content."""
    agents_root = _find_agents_root()
    skill_path = agents_root / role_id / "SKILL.md"
    if not skill_path.exists():
        raise FileNotFoundError(f"SKILL.md not found for role '{role_id}' at {skill_path}")
    return skill_path.read_text(encoding="utf-8")


def load_role_contract(role_id: str) -> dict:
    """Load a role's CONTRACT.yaml content."""
    agents_root = _find_agents_root()
    contract_path = agents_root / role_id / "CONTRACT.yaml"
    if not contract_path.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def load_role_prompt(
    role_id: str,
    task_id: str = "",
    input_files: Optional[list[str]] = None,
    extra_instructions: str = "",
) -> str:
    """Build a complete Agent prompt that loads the role's full identity.

    The resulting prompt can be passed directly to Agent("general-purpose", prompt).
    The sub-agent will receive the role's complete SKILL.md as its system prompt
    context, plus CONTRACT.yaml constraints, plus task-specific instructions.

    Args:
        role_id: Role identifier (e.g. "independent-reviewer", "quality-engineer")
        task_id: Current task ID for context
        input_files: Files to review/analyze
        extra_instructions: Additional task-specific instructions

    Returns:
        Complete prompt string ready for Agent() tool
    """
    if role_id not in AVAILABLE_ROLES and role_id not in list_roles():
        raise ValueError(f"Unknown role: {role_id}. Available: {list_roles()}")

    skill = load_role_skill(role_id)
    contract = load_role_contract(role_id)

    parts = [skill]

    # Add contract constraints
    if contract:
        constraints = []
        for key in ["fixed_stance", "prohibitions", "veto_power", "responsibilities"]:
            if key in contract:
                val = contract[key]
                if isinstance(val, list):
                    constraints.append(f"\n## {key}\n" + "\n".join(f"- {item}" for item in val))
                elif isinstance(val, dict):
                    constraints.append(f"\n## {key}\n" + "\n".join(f"- {k}: {v}" for k, v in val.items()))
                else:
                    constraints.append(f"\n## {key}\n{val}")
        if constraints:
            parts.append("\n---\n## CONTRACT CONSTRAINTS\n" + "\n".join(constraints))

    # Task context
    if task_id:
        parts.append(f"\n---\n## TASK CONTEXT\nYou are executing as part of task **{task_id}**.")
    if input_files:
        parts.append(f"\n## FILES TO REVIEW\n" + "\n".join(f"- {f}" for f in input_files))
    if extra_instructions:
        parts.append(f"\n## ADDITIONAL INSTRUCTIONS\n{extra_instructions}")

    # Hash instruction for evidence chain
    parts.append("\n---\n## OUTPUT REQUIREMENTS\nYour output must be valid JSON matching your role's output schema as defined in your SKILL.md. Include your reviewer_session_id and the input files you reviewed.")

    return "\n".join(parts)




# T-0074: Context-aware role dispatch
def build_role_context(role_id, project_root=".", task_id="", extra_files=None):
    """Build code context for a role sub-agent."""
    from loop_core.context_packager import build_context
    return build_context(project_root, role_id, task_id, extra_files)

def load_role_prompt_with_context(role_id, project_root=".", task_id="", extra_files=None):
    """Load role identity + code context — the ONE method for agent dispatch."""
    identity = load_role_prompt(role_id, task_id)
    context = build_role_context(role_id, project_root, task_id, extra_files)
    return identity + "\n\n---\n\n" + context
# ===== 2. Agent dispatch helper =====
def build_agent_dispatch_instruction(role_id: str, task_id: str, files: list[str]) -> str:
    """Build the instruction for the MAIN agent to dispatch a sub-agent.

    Returns a string the main agent should see, telling it to call Agent().
    """
    return f"""
[LOOP GOVERNANCE — AGENT DISPATCH REQUIRED]

You must now dispatch the **{role_id}** role as a sub-agent.

Call: Agent(subagent_type="general-purpose", prompt=load_role_prompt("{role_id}", task_id="{task_id}", input_files={json.dumps(files)}))

The sub-agent will receive the full role identity and execute independently.
After it returns, validate the output against the role's JSON schema.
"""
