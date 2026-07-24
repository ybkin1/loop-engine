"""loop_load_context — Load progressive role context based on task complexity."""
import sys
from pathlib import Path


def run(role_id: str, complexity: float = 0.5) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    # Context levels based on complexity
    if complexity <= 0.25:
        level = "minimal"
        sections = ["task_contract", "immediate_inputs"]
    elif complexity <= 0.60:
        level = "standard"
        sections = ["task_contract", "immediate_inputs", "architecture_relevant", "coding_standards"]
    else:
        level = "full"
        sections = ["task_contract", "immediate_inputs", "architecture_full", "coding_standards", "test_requirements", "security_boundaries"]

    # Get role-specific context from contracts
    contract_path = Path(__file__).resolve().parent.parent / "agents" / role_id / "CONTRACT.yaml"
    contract_info = {}
    if contract_path.exists():
        try:
            import yaml
            contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
            contract_info = {
                "role_id": contract.get("role_id", role_id),
                "fixed_stance": contract.get("fixed_stance", [])[:3],
                "prohibitions": contract.get("prohibitions", [])[:3],
            }
        except Exception:
            pass

    return {
        "role_id": role_id,
        "level": level,
        "complexity": complexity,
        "loaded_sections": sections,
        "estimated_sections": len(sections),
        "contract": contract_info,
    }
