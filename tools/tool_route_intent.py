"""loop_route_intent — Analyze user intent and recommend Loop mode."""
import sys
from pathlib import Path


def run(description: str = "", **risk_flags) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from loop_core.intent_router import IntentRouter

    router = IntentRouter()
    analysis = router.analyze(
        description,
        additional_context={"is_existing_project": risk_flags.get("is_existing", False)},
    )
    return {
        "recommended_mode": analysis.recommended_mode.value,
        "complexity_score": analysis.complexity_score,
        "change_type": analysis.change_type.value,
        "suggested_entry_phase": analysis.suggested_entry_phase,
        "confidence": analysis.confidence,
        "reasoning": analysis.reasoning,
        "detected_domains": analysis.detected_domains,
        "warnings": analysis.warnings,
    }
