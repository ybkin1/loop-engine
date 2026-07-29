"""Manifest Generator -- creates SubagentManifest from task + phase."""
from pathlib import Path
from loop_core.subagent_manifest import SubagentManifest, SubagentSpec, ManifestExecutor

PHASE_ROLE_MAP = {
    "S1-requirements":    ["product-manager", "project-manager"],
    "S2-architecture":    ["system-architect", "independent-reviewer"],
    "S3-interface":       ["module-architect"],
    "S4-implementation":  ["developer", "independent-reviewer", "quality-engineer", "test-engineer", "security-engineer"],
    "S5-quality":         ["quality-engineer", "security-engineer", "independent-reviewer"],
    "S6-delivery":        ["delivery-manager", "release-engineer"],
}

AGENT_MAP = {
    "developer": "code-agent", "independent-reviewer": "code-reviewer",
    "quality-engineer": "test-reviewer", "security-engineer": "explorer",
    "test-engineer": "test-reviewer", "system-architect": "designer-agent",
    "module-architect": "designer-agent", "product-manager": "researcher",
    "project-manager": "default", "delivery-manager": "default",
    "release-engineer": "default",
}

def generate_manifest(phase, task_id, task_title, allowed_paths, project_root=None):
    root = Path(project_root) if project_root else Path(__file__).resolve().parent.parent.parent
    role_ids = PHASE_ROLE_MAP.get(phase, ["developer", "independent-reviewer"])
    specs = []
    for role_id in role_ids:
        contract = _read_contract(root, role_id)
        deps = _get_dependencies(role_ids, role_id)
        prompt = _build_prompt(role_id, task_id, task_title, allowed_paths, contract)
        specs.append(SubagentSpec(
            subagent_id=role_id,
            role_hint=AGENT_MAP.get(role_id, "default"),
            prompt=prompt,
            input_files=[str(root / ".ai/state.yaml"), str(root / ".ai" / "tasks" / (task_id + ".md"))],
            max_parallel=len(deps) == 0,
            timeout_seconds=300, max_retries=2, retry_on_failure=True,
        ))
    agg = "Aggregate all role outputs and present gate decision."
    fp = SubagentManifest.compute_fingerprint(specs, agg)
    return SubagentManifest(
        manifest_id="m-" + task_id, parent_role_id="main-thread",
        parent_task_id=task_id, phase=phase, subagents=specs,
        aggregation_prompt=agg, input_fingerprint=fp, max_parallel_subagents=5,
    )

def _read_contract(root, role_id):
    try:
        import yaml
        p = root / "agents" / role_id / "CONTRACT.yaml"
        if p.exists():
            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        pass
    return {}

def _build_prompt(role_id, task_id, task_title, allowed_paths, contract):
    identity = contract.get("identity", {})
    title = identity.get("title", role_id) if isinstance(identity, dict) else role_id
    resp = contract.get("responsibilities", [])
    forb = contract.get("prohibitions", [])
    paths = ", ".join(allowed_paths) if allowed_paths else "project scope"
    ctx = _load_context(role_id, task_id, allowed_paths)
    base = " | ".join([
        "Role: " + str(title),
        "Task: " + task_title + " (" + task_id + ")",
        "Paths: " + paths,
        "Do: " + "; ".join(resp),
        "Do NOT: " + "; ".join(forb),
        "Output structured JSON per contract schema.",
    ])
    if ctx:
        return base + "\n\n--- REVIEW MATERIALS ---\n" + ctx
    return base

def _get_dependencies(all_roles, current_role):
    deps = []
    if current_role == "independent-reviewer" and "developer" in all_roles:
        deps.append("developer")
    if current_role == "quality-engineer":
        for r in ["developer", "independent-reviewer"]:
            if r in all_roles:
                deps.append(r)
    return deps


def _load_context(role_id, task_id, allowed_paths):
    ctx = []
    try:
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent.parent
        tf = root / ".ai" / "tasks" / (task_id + ".md")
        if tf.exists():
            ctx.append("TASK: " + tf.read_text(encoding="utf-8")[:2000])
        sf = root / ".ai" / "state.yaml"
        if sf.exists():
            ctx.append("STATE: " + sf.read_text(encoding="utf-8"))
        if role_id == "independent-reviewer" and allowed_paths:
            for ap in allowed_paths[:3]:
                p = root / ap
                if p.is_file() and p.exists():
                    content = p.read_text(encoding="utf-8")[:3000]
                    ctx.append("FILE " + ap + ":\n" + content)
    except Exception as e:
        ctx.append("Context load error: " + str(e))
    return "\n\n".join(ctx)
