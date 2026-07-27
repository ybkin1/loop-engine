"""loop_veto_escalate — Analyze vetos and determine escalation level."""
import sys
from pathlib import Path


def run(vetos: list = None, generate_summary: bool = False) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from codex_loop.core.veto_escalation import VetoEscalation

    vetos = vetos or []
    escalation = VetoEscalation()
    decision = escalation.check_escalation(vetos)

    result = {
        "escalation_level": decision.get("level", "none"),
        "requires_user_decision": decision.get("requires_user_decision", False),
        "veto_count": len(vetos),
        "unresolved_vetos": [v for v in vetos if not v.get("resolved", False)],
    }

    if generate_summary and hasattr(escalation, 'generate_human_review_summary'):
        result["human_summary"] = escalation.generate_human_review_summary(vetos)

    return result
