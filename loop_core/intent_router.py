"""
Intent Router — User intent analysis and automatic Loop routing.

Analyses a natural-language description to detect domains, estimate
complexity, and recommend the appropriate Loop mode.  Built on top of
the existing router.py for backward compatibility.

T-0110 批 B-1 拆分后本文件为 **re-export 壳**：路由主流程与数据模型保留
在本文件（IntentRouter 类 / IntentAnalysis / ActiveTaskSnapshot / TaskFrame /
RoutedIntent / route_user_input / analyse_intent / _route_internal 等），
检测/评分/切分辅助外提至新模块并由本壳 re-export（行为与拆分前
逐字节/逐字段等价）：

- ``loop_core/intent_keywords.py`` — 词表常量（D5-4 外提：DOMAIN_KEYWORDS/
  SCALE_INDICATORS/变更类型词表/_NEGATION_PATTERNS 等）
- ``loop_core/intent_detection.py`` — 检测/评分辅助（_detect_domains/
  _extract_risk_factors/_is_negated/_set_if_match/_compute_complexity/
  _build_reasoning）
- ``loop_core/intent_split.py`` — 意图切分/切换辅助（split_intents/
  _INTENT_SPLIT_RE/detect_intent_switch/_other_task_refs/
  _active_task_completion_signal + 专属常量）

Core rules (as specified by the user):
1. Any high-risk factor (database / auth / payments / production data / security)
   automatically escalates to FULL — cannot be downgraded.
2. When uncertain, escalate rather than misjudge (confidence < 0.5).
3. LIGHTWEIGHT only for: single-file scripts, simple tools, one-off tasks.
4. Multi-module, external API, deployment, or ongoing iteration → at least STANDARD.
"""
from __future__ import annotations

import math  # noqa: F401 — 命名空间保持（拆分前同源绑定，dir() 面不变）
import re  # noqa: F401 — 命名空间保持
from collections import Counter  # noqa: F401 — 命名空间保持
from dataclasses import dataclass, field
from enum import Enum

from loop_core.constants import (
    CONFIDENCE_CONFLICT_MAX_RISK_FACTORS,
    CONFIDENCE_CONFLICT_MIN_DOMAINS,
    KEYWORD_BOUNDARY_MAX_LEN,  # noqa: F401 — 命名空间保持（检测逻辑已外提）
)
from loop_core.intent_detection import (
    _build_reasoning,
    _compute_complexity,
    _detect_domains,
    _extract_risk_factors,
    _is_negated,
    _set_if_match,
)
from loop_core.intent_keywords import (
    _NEGATION_PATTERNS,
    BUG_FIX_KEYWORDS,
    DOMAIN_KEYWORDS,
    FEATURE_ADD_KEYWORDS,
    HIGH_RISK_KEYWORDS,
    LIGHTWEIGHT_KEYWORDS,
    MAX_COMPLEXITY,
    MEDIUM_RISK_KEYWORDS,
    MIN_COMPLEXITY,
    QUALITY_FIX_KEYWORDS,
    REFACTOR_KEYWORDS,
    REQUIREMENT_CHANGE_KEYWORDS,
    SCALE_INDICATORS,
)
from loop_core.intent_split import (
    _COMPLETION_VERBS,
    _INTENT_SPLIT_RE,
    _MAX_TASK_FRAMES,
    _TASK_ID_RE,
    INTENT_SWITCH_KEYWORDS,
    _active_task_completion_signal,
    _other_task_refs,
    detect_intent_switch,
    split_intents,
)
from loop_core.router import (
    LoopMode,
    ProjectProfile,
    RiskLevel,
    RouteResult,
    route_intent,
)

# ---------------------------------------------------------------------------
# Change Type Detection (v3.1 — iteration support)
# ---------------------------------------------------------------------------

class ChangeType(str, Enum):
    """What kind of change the user is requesting on an existing project."""
    NEW_PROJECT = "new_project"
    BUG_FIX = "bug_fix"
    FEATURE_ADD = "feature_add"
    REFACTOR = "refactor"
    REQUIREMENT_CHANGE = "requirement_change"
    QUALITY_FIX = "quality_fix"
    UNKNOWN = "unknown"


# Entry phase per change type
CHANGE_TYPE_TO_ENTRY_PHASE: dict[ChangeType, str] = {
    ChangeType.NEW_PROJECT:         "S0-init",
    ChangeType.BUG_FIX:             "S9-fix-optimize",
    ChangeType.FEATURE_ADD:         "S4-implementation",
    ChangeType.REFACTOR:            "S4-implementation",
    ChangeType.REQUIREMENT_CHANGE:  "S1-requirements",
    ChangeType.QUALITY_FIX:         "S5-quality",
    ChangeType.UNKNOWN:             "S0-init",
}

# Min phases required per change type (from entry to delivery)
CHANGE_TYPE_MIN_PHASES: dict[ChangeType, list[str]] = {
    ChangeType.NEW_PROJECT:         [],
    ChangeType.BUG_FIX:             ["S9-fix-optimize", "S5-quality", "S6-delivery"],
    ChangeType.FEATURE_ADD:         ["S4-implementation", "S5-quality", "S6-delivery"],
    ChangeType.REFACTOR:            ["S4-implementation", "S5-quality", "S6-delivery"],
    ChangeType.REQUIREMENT_CHANGE:  ["S1-requirements", "S2-architecture", "S4-implementation", "S5-quality", "S6-delivery"],
    ChangeType.QUALITY_FIX:         ["S5-quality", "S6-delivery"],
    ChangeType.UNKNOWN:             [],
}


def _detect_change_type(desc_lower: str) -> ChangeType:
    """Detect change type from user description keywords.

    Returns NEW_PROJECT if no change keywords detected.
    Input should already be lowercased.
    """
    # Ensure lowercase (defense in depth)
    desc_lower = desc_lower.lower()

    scores: dict[ChangeType, int] = {
        ChangeType.BUG_FIX: 0,
        ChangeType.FEATURE_ADD: 0,
        ChangeType.REFACTOR: 0,
        ChangeType.REQUIREMENT_CHANGE: 0,
        ChangeType.QUALITY_FIX: 0,
    }

    for kw in BUG_FIX_KEYWORDS:
        if kw in desc_lower:
            scores[ChangeType.BUG_FIX] += 1
    for kw in FEATURE_ADD_KEYWORDS:
        if kw in desc_lower:
            scores[ChangeType.FEATURE_ADD] += 1
    for kw in REFACTOR_KEYWORDS:
        if kw in desc_lower:
            scores[ChangeType.REFACTOR] += 1
    for kw in REQUIREMENT_CHANGE_KEYWORDS:
        if kw in desc_lower:
            scores[ChangeType.REQUIREMENT_CHANGE] += 1
    for kw in QUALITY_FIX_KEYWORDS:
        if kw in desc_lower:
            scores[ChangeType.QUALITY_FIX] += 1

    max_score = max(scores.values())
    if max_score == 0:
        return ChangeType.NEW_PROJECT

    # Return the highest-scoring change type
    for ct, score in scores.items():
        if score == max_score:
            return ct
    return ChangeType.NEW_PROJECT


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class IntentAnalysis:
    """Result of analysing a user's intent description.

    Attributes:
        description: The original (or cleaned) intent description.
        complexity_score: 0.0 – 1.0 estimated complexity.
        detected_domains: List of domain labels the intent touches.
        risk_factors: Detailed risk-factor flags (key -> True/False).
        recommended_mode: Suggested LoopMode based on analysis.
        confidence: 0.0 – 1.0 confidence in the analysis.
        reasoning: Human-readable explanation of the decision.
        suggested_phases: Recommended phases (strings) for the Loop.
        warnings: Any warnings or disclaimers.
        change_type: Detected change type (v3.1 iteration support).
        is_existing_project: Whether this is an existing project with .ai/state.yaml.
        suggested_entry_phase: Entry phase for re-entry (v3.1).
        requires_full_loop: Whether full loop re-execution is needed.
        affected_modules: Modules affected by this change.
    """
    description: str
    complexity_score: float
    detected_domains: list[str] = field(default_factory=list)
    risk_factors: dict[str, bool] = field(default_factory=dict)
    recommended_mode: LoopMode = LoopMode.LIGHTWEIGHT
    confidence: float = 1.0
    reasoning: str = ""
    suggested_phases: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    change_type: ChangeType = ChangeType.NEW_PROJECT
    is_existing_project: bool = False
    suggested_entry_phase: str = ""
    requires_full_loop: bool = False
    affected_modules: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# IntentRouter
# ---------------------------------------------------------------------------

class IntentRouter:
    """Analyses user intents and recommends a Loop mode.

    Usage::

        router = IntentRouter()
        analysis = router.analyze("Build a payment gateway with PostgreSQL")
        result = router.route(analysis)

        escalate, reason = IntentRouter.should_escalate(analysis)
    """

    # ------------------------------------------------------------------
    # Configuration knobs
    # ------------------------------------------------------------------

    # Thresholds
    LIGHTWEIGHT_COMPLEXITY_MAX: float = 0.25
    STANDARD_COMPLEXITY_MAX: float = 0.60
    # >= STANDARD_COMPLEXITY_MAX → FULL

    # Confidence thresholds
    LOW_CONFIDENCE_THRESHOLD: float = 0.50

    # T-0107 D2-2: 中风险因素累计升级阈值（was 魔法数 3）。
    # >= MEDIUM_RISK_ESCALATION_MIN 个中风险因素 → 升级到 loop 模式。
    MEDIUM_RISK_ESCALATION_MIN: int = 3

    # Complexity factors (weights)
    DOMAIN_WEIGHT: float = 0.30          # contribution from detected domains
    KEYWORD_WEIGHT: float = 0.40         # contribution from risk keywords
    SCALE_WEIGHT: float = 0.30           # contribution from scale indicators

    def __init__(self, **kwargs: float):
        """Initialise with optional overrides for threshold/weight config."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        description: str,
        additional_context: dict | None = None,
    ) -> IntentAnalysis:
        """Analyse a user description and return an IntentAnalysis.

        Parameters:
            description: Natural-language description of the user's intent.
            additional_context: Optional dict with extra keys such as:
                - file_count (int): estimated number of files touched
                - module_count (int): number of modules/components
                - team_size (int): number of contributors
                - is_greenfield (bool): if this is a brand-new project
        """
        desc_lower = description.lower()

        # ---- domain detection ------------------------------------------
        domains = _detect_domains(desc_lower)

        # ---- risk factors ----------------------------------------------
        risk_factors = _extract_risk_factors(desc_lower)

        # ---- complexity scoring ----------------------------------------
        complexity_score = _compute_complexity(
            desc_lower, domains, risk_factors,
            self.DOMAIN_WEIGHT, self.KEYWORD_WEIGHT, self.SCALE_WEIGHT,
            additional_context or {},
        )

        # ---- mode recommendation ---------------------------------------
        recommended_mode = self._mode_from_complexity(complexity_score)

        # ---- auto-escalation -------------------------------------------
        did_escalate, escalate_reason = self.should_escalate(
            risk_factors, recommended_mode,
        )
        if did_escalate:
            recommended_mode = LoopMode.FULL

        # ---- medium-risk floor -----------------------------------------
        # Tasks involving external API, multi-module work, deployment, or
        # ongoing iteration are never LIGHTWEIGHT (rule #4).
        _medium_floor_triggers = [
            risk_factors.get("has_external_api"),
            risk_factors.get("has_multiple_modules"),
            risk_factors.get("requires_deployment"),
            risk_factors.get("requires_ongoing_iteration"),
        ]
        if any(_medium_floor_triggers) and recommended_mode == LoopMode.LIGHTWEIGHT:
            recommended_mode = LoopMode.STANDARD

        # ---- confidence ------------------------------------------------
        confidence, warnings = self._calculate_confidence(
            complexity_score, risk_factors, domains, additional_context or {},
        )

        # ---- reasoning -------------------------------------------------
        reasoning = _build_reasoning(
            domains, complexity_score, risk_factors, recommended_mode,
            did_escalate, escalate_reason, confidence,
        )

        # ---- phases ----------------------------------------------------
        suggested_phases = list(
            _phases_for_mode(recommended_mode)
        )

        # ---- change type detection (v3.1) ------------------------------
        change_type = _detect_change_type(desc_lower)

        # Check if this is an existing project
        is_existing = additional_context.get("is_existing_project", False) if additional_context else False

        # Determine entry phase and full-loop requirement
        entry_phase = CHANGE_TYPE_TO_ENTRY_PHASE.get(change_type, "S0-init")
        requires_full = change_type in (
            ChangeType.REQUIREMENT_CHANGE, ChangeType.NEW_PROJECT, ChangeType.UNKNOWN,
        )

        # If re-entering existing project, adjust phases from entry point
        if is_existing and change_type != ChangeType.NEW_PROJECT:
            min_phases = CHANGE_TYPE_MIN_PHASES.get(change_type, [])
            if min_phases:
                suggested_phases = min_phases

        return IntentAnalysis(
            description=description,
            complexity_score=round(complexity_score, 3),
            detected_domains=sorted(domains),
            risk_factors=risk_factors,
            recommended_mode=recommended_mode,
            confidence=round(confidence, 3),
            reasoning=reasoning,
            suggested_phases=suggested_phases,
            warnings=warnings,
            change_type=change_type,
            is_existing_project=is_existing,
            suggested_entry_phase=entry_phase,
            requires_full_loop=requires_full,
        )

    def route(self, analysis: IntentAnalysis) -> RouteResult:
        """Convert an IntentAnalysis into the canonical RouteResult.

        This bridges the new intent_router with the existing router.py.
        Internally builds a ProjectProfile and calls route_intent() for
        consistency, then overlays the IntentAnalysis recommendations.
        """
        profile = _analysis_to_profile(analysis)
        result = route_intent(profile)

        # Honour the IntentAnalysis recommendation unless the profile
        # forces a *higher* mode (safety net: never downgrade).
        mode_order = {LoopMode.LIGHTWEIGHT: 0, LoopMode.STANDARD: 1, LoopMode.FULL: 2}
        if mode_order[analysis.recommended_mode] > mode_order[result.mode]:
            result.mode = analysis.recommended_mode
            result.recommended_phases = analysis.suggested_phases
            result.reason = analysis.reasoning

        return result

    def route_upgrade(
        self,
        description: str,
        active_task: ActiveTaskSnapshot | None = None,
        additional_context: dict | None = None,
    ) -> RoutedIntent:
        """U5 upgraded routing: sticky rules + multi-intent task frames.

        When an active task exists (``active_task`` with status
        active/in_progress) the result sticks to that task's domain
        (``sticky=True`` + ``sticky_basis``) instead of re-asking what to
        do; explicit intent-switch or completion signals invalidate the
        stickiness.  Multiple intents in one input are split into an
        ordered :class:`TaskFrame` list (main frame = first intent).

        Fail-safe: this method never raises.  Any internal error returns
        a ``degraded=True`` result that keeps the status quo (continue
        the active task, or default LIGHTWEIGHT) and guesses no new
        intents.  The degradation applies to the routing recommendation
        only — constraint/hook enforcement stays fail-closed.
        """
        try:
            return _route_internal(self, description, active_task, additional_context)
        except Exception as exc:  # fail-safe: keep status quo, never raise
            return _degraded_result(
                description, active_task, f"{type(exc).__name__}: {exc}"
            )

    @staticmethod
    def should_escalate(
        risk_factors: dict[str, bool] | None = None,
        current_mode: LoopMode | None = None,
        analysis: IntentAnalysis | None = None,
    ) -> tuple[bool, str]:
        """Determine whether the intent should be escalated.

        Accepts either an IntentAnalysis or explicit risk_factors +
        current_mode.  Priority: ``analysis`` trumps explicit args.

        Rules:
        - Any single high-risk factor → FULL (cannot be downgraded).
        - LOW confidence (< 0.5) → escalate to at least STANDARD.
        - Uncertainty → escalate rather than misjudge.
        """
        if analysis is not None:
            risk_factors = analysis.risk_factors
            current_mode = analysis.recommended_mode
            if analysis.confidence < 0.5:
                return True, (
                    f"Low confidence ({analysis.confidence:.2f}) – "
                    "escalating to avoid misjudgement."
                )

        if risk_factors is None:
            risk_factors = {}
        if current_mode is None:
            current_mode = LoopMode.LIGHTWEIGHT

        # High-risk escalation — any single flag triggers FULL
        high_risk_flags = [
            "has_database", "has_auth_permissions", "has_payments",
            "has_production_data", "has_security_requirements",
        ]
        triggered = [f for f in high_risk_flags if risk_factors.get(f)]
        if triggered:
            return True, (
                f"High-risk factors detected ({', '.join(triggered)}). "
                "Automatic escalation to FULL – cannot be downgraded."
            )

        # If we are already at FULL, nothing more to do (except the low-confidence
        # branch above which already returned).
        if current_mode == LoopMode.FULL:
            return False, ""

        # Medium-risk accumulation check: >= 3 medium-risk factors → escalate
        medium_risk_flags = [
            "has_multiple_modules", "has_external_api",
            "has_concurrency_performance", "requires_deployment",
            "requires_monitoring_rollback", "requires_ongoing_iteration",
            "has_high_uncertainty",
        ]
        triggered_medium = [f for f in medium_risk_flags if risk_factors.get(f)]
        # 静态方法：经类名引用常量（T-0107 D2-2）
        if len(triggered_medium) >= IntentRouter.MEDIUM_RISK_ESCALATION_MIN:
            return True, (
                f"Multiple medium-risk factors ({len(triggered_medium)}): "
                f"{', '.join(triggered_medium)}. Escalating."
            )

        return False, ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _mode_from_complexity(self, score: float) -> LoopMode:
        """Map a complexity score to the recommended LoopMode."""
        if score <= self.LIGHTWEIGHT_COMPLEXITY_MAX:
            return LoopMode.LIGHTWEIGHT
        if score <= self.STANDARD_COMPLEXITY_MAX:
            return LoopMode.STANDARD
        return LoopMode.FULL

    def _calculate_confidence(
        self,
        complexity_score: float,
        risk_factors: dict[str, bool],
        domains: set[str],
        context: dict,
    ) -> tuple[float, list[str]]:
        """Calculate confidence in the analysis.

        Low confidence situations:
        - Very short / vague description
        - No domains detected
        - Mid-range complexity (ambiguous territory)
        - Explicit uncertainty flags in the description
        """
        warnings: list[str] = []
        confidence = 1.0

        # Penalise when no domains are detected
        if not domains:
            confidence -= 0.15
            warnings.append("No specific domains detected – analysis may be shallow.")

        # Penalise mid-range complexity (hardest to judge)
        if 0.3 < complexity_score < 0.6:
            confidence -= 0.10
            warnings.append("Complexity in ambiguous range – consider human review.")

        # Penalise lack of context
        if not context or len(context) < 2:
            confidence -= 0.05

        # Penalise conflicting signals: many domains but few risk factors,
        # or few domains but high complexity
        if (len(domains) >= CONFIDENCE_CONFLICT_MIN_DOMAINS
                and sum(risk_factors.values()) <= CONFIDENCE_CONFLICT_MAX_RISK_FACTORS):
            confidence -= 0.10
            warnings.append(
                "Many domains detected but few risk factors – "
                "may be underestimating complexity."
            )

        return max(confidence, 0.0), warnings


# ---------------------------------------------------------------------------
# Module-level helpers (conversion)
# ---------------------------------------------------------------------------

def _phases_for_mode(mode: LoopMode) -> list[str]:
    """Return the recommended phases for a given mode.

    Mirrors the logic in router.route_intent() for consistency.
    """
    if mode == LoopMode.LIGHTWEIGHT:
        return ["S0-init", "S4-implementation", "S6-delivery"]
    if mode == LoopMode.STANDARD:
        return [
            "S0-init", "S1-requirements", "S2-architecture",
            "S4-implementation", "S5-quality", "S6-delivery",
        ]
    return [
        "S0-init", "S1-requirements", "S2-architecture", "S3-interface",
        "S4-implementation", "S5-quality", "S6-delivery",
        "S7-integration", "S8-functional-test", "S9-fix-optimize",
        "S10-performance", "S11-maintenance",
    ]


def _analysis_to_profile(analysis: IntentAnalysis) -> ProjectProfile:
    """Convert an IntentAnalysis to a ProjectProfile for router.py compat."""
    rf = analysis.risk_factors
    return ProjectProfile(
        description=analysis.description,
        has_multiple_modules=rf.get("has_multiple_modules", False),
        has_database=rf.get("has_database", False),
        has_auth_permissions=rf.get("has_auth_permissions", False),
        has_payments=rf.get("has_payments", False),
        has_production_data=rf.get("has_production_data", False),
        has_external_api=rf.get("has_external_api", False),
        has_concurrency_performance=rf.get("has_concurrency_performance", False),
        has_security_requirements=rf.get("has_security_requirements", False),
        requires_deployment=rf.get("requires_deployment", False),
        requires_monitoring_rollback=rf.get("requires_monitoring_rollback", False),
        requires_ongoing_iteration=rf.get("requires_ongoing_iteration", False),
        has_high_uncertainty=rf.get("has_high_uncertainty", False),
    )


# ===========================================================================
# U5 Routing Upgrade (T-0088) — sticky routing + task frames + fail-safe
#
# Benchmark source: StaffDeck backend/app/core/router.py (T-0086,
# staffdeck-benchmark.md U5): "9 决策类型 + 粘性规则（active 技能沿用）+
# task_frames 单轮多任务编排 + 非法目标降级".
#
# This section is purely incremental:
#   - `IntentRouter.analyze()` / `IntentRouter.route()` / `IntentAnalysis`
#     are NOT modified (backward compatible).
#   - New entry points: `IntentRouter.route_upgrade()` (instance),
#     `route_user_input()` (module-level), `analyse_intent()` (fills the
#     entry point inbox.py already imports).
#   - New structures: `ActiveTaskSnapshot`, `TaskFrame`, `RoutedIntent`,
#     `IntentBrief`.
#
# Fail-safe semantics: `route_upgrade()` never raises.  On any internal
# error it returns a `RoutedIntent(degraded=True)` that keeps the status
# quo — continue the active task if one exists, otherwise default to
# LIGHTWEIGHT — and never guesses new intents (task_frames stays empty).
# This affects ONLY the routing recommendation ("keep current state"): it
# does not relax any constraint adjudication — hook-level fail-closed
# enforcement (C1-C11, path/scope/verdict checks) is untouched.
# ===========================================================================


@dataclass
class ActiveTaskSnapshot:
    """Immutable snapshot of the active task used for sticky routing.

    Built from state.task_graph.yaml entries via :meth:`from_task` (or
    directly by callers).  Only the fields the router needs are kept —
    this is a routing input, not an authority on task state.
    """

    task_id: str
    status: str = "active"
    title: str = ""
    domain: str = ""
    description: str = ""
    loop_mode: LoopMode = LoopMode.LIGHTWEIGHT

    @property
    def is_active(self) -> bool:
        """True when the task can still receive work (sticky applies)."""
        return self.status in ("active", "in_progress", "ACTIVE", "IN_PROGRESS")

    @staticmethod
    def from_task(task: dict) -> ActiveTaskSnapshot:
        """Build a snapshot from a task_graph.yaml task entry (dict).

        Unknown/missing loop_mode falls back to LIGHTWEIGHT; unknown status
        defaults to "active" (the router never hard-fails on shape drift).
        """
        raw_mode = task.get("loop_mode") or task.get("mode")
        mode = LoopMode.LIGHTWEIGHT
        if isinstance(raw_mode, str):
            mode = {m.name: m for m in LoopMode}.get(
                raw_mode.upper(), LoopMode.LIGHTWEIGHT
            )
        return ActiveTaskSnapshot(
            task_id=str(task.get("id") or task.get("task_id") or ""),
            status=str(task.get("status") or "active"),
            title=str(task.get("title") or ""),
            domain=str(task.get("domain") or ""),
            description=str(task.get("description") or ""),
            loop_mode=mode,
        )


@dataclass
class TaskFrame:
    """One task frame in a multi-intent round (U5).

    The main frame (``is_main=True``, ``frame_id == 0``) expresses the
    first intent and carries the sticky target when sticky routing
    applies.  Follow-up frames are new tasks to orchestrate in order
    after the main one (their ``task_id`` is None until created).

    The frame shape is compatible with task files / task_graph.yaml
    entries: see :meth:`to_task_dict`.
    """

    frame_id: int
    intent: str
    task_id: str | None
    domain: str
    complexity_score: float
    recommended_mode: LoopMode
    change_type: ChangeType
    confidence: float
    reasoning: str
    is_main: bool
    detected_domains: list[str] = field(default_factory=list)
    suggested_phases: list[str] = field(default_factory=list)

    def to_task_dict(self) -> dict:
        """Return a dict compatible with task_graph.yaml task entries.

        Maps task_id/intent/domain/complexity onto the task-file shape
        (id/title/status/phase/loop_mode + routing estimates).  The
        ``phase`` follows the change-type entry-phase table used across
        the codebase.
        """
        return {
            "id": self.task_id,
            "title": self.intent,
            "status": "planned",
            "phase": CHANGE_TYPE_TO_ENTRY_PHASE.get(self.change_type, "S0-init"),
            "loop_mode": self.recommended_mode.name,
            "domains": list(self.detected_domains),
            "complexity_score": round(self.complexity_score, 3),
        }


@dataclass
class RoutedIntent:
    """Output of the upgraded routing entry point (U5).

    Backward-compatible core: ``analysis`` is the primary
    :class:`IntentAnalysis` (frame 0) and ``route_result`` is the
    canonical :class:`RouteResult` for it — existing callers can keep
    using those two fields unchanged.

    Incremental fields:
      - ``sticky`` / ``sticky_basis`` / ``sticky_task_id`` — sticky
        routing marker + evidence.
      - ``task_frames`` — ordered frames for multi-intent rounds (main
        frame first).
      - ``degraded`` / ``degraded_reason`` — fail-safe degradation flag
        (keep-status-quo result; no new intents guessed).
    """

    analysis: IntentAnalysis | None
    route_result: RouteResult | None
    sticky: bool = False
    sticky_basis: str = ""
    sticky_task_id: str | None = None
    task_frames: list[TaskFrame] = field(default_factory=list)
    intents: list[str] = field(default_factory=list)
    degraded: bool = False
    degraded_reason: str = ""

    @property
    def main_frame(self) -> TaskFrame | None:
        """The main (first) task frame, if any."""
        return self.task_frames[0] if self.task_frames else None


def _status_quo_route_result(mode: LoopMode) -> RouteResult:
    """RouteResult for the fail-safe status-quo path (no intent guessed)."""
    if mode == LoopMode.LIGHTWEIGHT:
        return RouteResult(
            mode=LoopMode.LIGHTWEIGHT,
            risk_level=RiskLevel.LOW,
            reason="Fail-safe status quo: keep lightweight routing, no new intent guessed.",
            recommended_phases=["S0-init", "S4-implementation", "S6-delivery"],
        )
    if mode == LoopMode.STANDARD:
        return RouteResult(
            mode=LoopMode.STANDARD,
            risk_level=RiskLevel.MEDIUM,
            reason="Fail-safe status quo: keep standard routing, no new intent guessed.",
            recommended_phases=[
                "S0-init", "S1-requirements", "S2-architecture",
                "S4-implementation", "S5-quality", "S6-delivery",
            ],
        )
    return RouteResult(
        mode=LoopMode.FULL,
        risk_level=RiskLevel.HIGH,
        reason="Fail-safe status quo: keep full routing, no new intent guessed.",
        recommended_phases=[
            "S0-init", "S1-requirements", "S2-architecture", "S3-interface",
            "S4-implementation", "S5-quality", "S6-delivery",
            "S7-integration", "S8-functional-test", "S9-fix-optimize",
            "S10-performance", "S11-maintenance",
        ],
    )


def _degraded_result(
    description: str,
    active_task: ActiveTaskSnapshot | None,
    reason: str,
) -> RoutedIntent:
    """Fail-safe degraded result: keep the status quo, guess nothing new.

    - With an active task → keep routing to that task (sticky) and keep
      its loop mode.
    - Without an active task → default LIGHTWEIGHT routing.

    Never raises and never fabricates new intents (``task_frames`` stays
    empty).  This is a routing-only degradation — constraint adjudication
    in the hook layer is untouched (fail-closed semantics unchanged).
    """
    if active_task is not None and active_task.is_active and active_task.task_id:
        mode = active_task.loop_mode or LoopMode.LIGHTWEIGHT
        return RoutedIntent(
            analysis=None,
            route_result=_status_quo_route_result(mode),
            sticky=True,
            sticky_basis=(
                f"Fail-safe: keeping active task {active_task.task_id} "
                f"(routing error: {reason})"
            ),
            sticky_task_id=active_task.task_id,
            task_frames=[],
            intents=[],
            degraded=True,
            degraded_reason=f"Fail-safe degradation — {reason}",
        )
    return RoutedIntent(
        analysis=None,
        route_result=_status_quo_route_result(LoopMode.LIGHTWEIGHT),
        sticky=False,
        sticky_basis="",
        sticky_task_id=None,
        task_frames=[],
        intents=[],
        degraded=True,
        degraded_reason=f"Fail-safe degradation — {reason}",
    )


def _route_internal(
    router: IntentRouter,
    description: str,
    active_task: ActiveTaskSnapshot | None,
    additional_context: dict | None,
) -> RoutedIntent:
    """Core U5 routing logic; exceptions propagate to the fail-safe caller."""
    if not isinstance(description, str):
        raise TypeError(
            f"description must be a str, got {type(description).__name__}"
        )

    desc_lower = description.lower()

    # ---- sticky decision ------------------------------------------------
    switched, switch_reason = detect_intent_switch(desc_lower)
    if not switched and active_task is not None and active_task.task_id:
        other_ids = _other_task_refs(desc_lower, active_task.task_id)
        if other_ids:
            switched = True
            switch_reason = (
                "description references a different task id "
                f"({', '.join(other_ids)})"
            )
        else:
            completion_reason = _active_task_completion_signal(
                desc_lower, active_task.task_id
            )
            if completion_reason:
                switched = True
                switch_reason = completion_reason

    sticky = False
    sticky_basis = ""
    sticky_task_id: str | None = None
    if active_task is not None and active_task.task_id:
        if active_task.is_active and not switched:
            sticky = True
            sticky_task_id = active_task.task_id
            sticky_basis = (
                f"Active task {active_task.task_id} (status={active_task.status}) "
                "— continuing its domain without re-asking what to do"
            )
        elif not active_task.is_active:
            sticky_basis = (
                f"Sticky not applied: task {active_task.task_id} status="
                f"{active_task.status!r} is not active "
                "(completion/closure invalidates stickiness)"
            )
        else:
            sticky_basis = f"Sticky invalidated: {switch_reason}"

    # ---- multi-intent frame split --------------------------------------
    intents = split_intents(description, max_frames=_MAX_TASK_FRAMES)
    if not intents:
        intents = [description]

    frames: list[TaskFrame] = []
    primary_analysis: IntentAnalysis | None = None
    primary_route: RouteResult | None = None

    for idx, intent in enumerate(intents):
        analysis = router.analyze(intent, additional_context)
        if idx == 0:
            primary_analysis = analysis
            primary_route = router.route(analysis)

        if idx == 0 and sticky:
            frame_task_id: str | None = sticky_task_id
        else:
            frame_task_id = None  # follow-up frames are new tasks
        if idx == 0 and sticky and active_task is not None and active_task.domain:
            domain: str = active_task.domain
        else:
            domain = analysis.detected_domains[0] if analysis.detected_domains else "unknown"

        frames.append(
            TaskFrame(
                frame_id=idx,
                intent=intent,
                task_id=frame_task_id,
                domain=domain,
                complexity_score=analysis.complexity_score,
                recommended_mode=analysis.recommended_mode,
                change_type=analysis.change_type,
                confidence=analysis.confidence,
                reasoning=analysis.reasoning,
                is_main=(idx == 0),
                detected_domains=list(analysis.detected_domains),
                suggested_phases=list(analysis.suggested_phases),
            )
        )

    return RoutedIntent(
        analysis=primary_analysis,
        route_result=primary_route,
        sticky=sticky,
        sticky_basis=sticky_basis,
        sticky_task_id=sticky_task_id,
        task_frames=frames,
        intents=intents,
        degraded=False,
        degraded_reason="",
    )


@dataclass
class IntentBrief:
    """Lightweight analysis summary for inbox integration (U5 back-compat).

    Provides exactly the two attributes ``loop_core/inbox.py`` consumes:
    ``domains`` (list[str]) and ``risk_level`` (uppercase name matching
    the inbox priority mapping: LOW/MEDIUM/HIGH/CRITICAL).
    """

    domains: list[str]
    risk_level: str
    recommended_mode: LoopMode


def analyse_intent(description: str) -> IntentBrief:
    """Analyse a user description and return a lightweight brief.

    Backward-compatibility entry point for ``loop_core/inbox.py``, which
    already imports ``analyse_intent`` from this module.  Runs the full
    IntentRouter pipeline and maps the result onto the inbox contract
    (``domains`` + ``risk_level``).  Never raises: on any failure it
    returns a MEDIUM-risk empty brief so the inbox keeps working.
    """
    try:
        router = IntentRouter()
        analysis = router.analyze(description)
        result = router.route(analysis)
        return IntentBrief(
            domains=list(analysis.detected_domains),
            risk_level=result.risk_level.name,
            recommended_mode=analysis.recommended_mode,
        )
    except Exception:
        return IntentBrief(
            domains=[],
            risk_level="MEDIUM",
            recommended_mode=LoopMode.STANDARD,
        )


def route_user_input(
    description: str,
    active_task: ActiveTaskSnapshot | None = None,
    additional_context: dict | None = None,
    router: IntentRouter | None = None,
) -> RoutedIntent:
    """Module-level U5 entry point: sticky routing + task frames + fail-safe.

    Parameters:
        description: Natural-language user input (may contain several
            intents, which are split into ordered task frames).
        active_task: Optional :class:`ActiveTaskSnapshot` of the current
            active task (state.current_task_id + task_graph entry).  When
            present and active, routing sticks to its domain unless an
            explicit intent-switch/completion signal invalidates it.
        additional_context: Passed through to ``analyze()``.
        router: Optional IntentRouter instance (defaults to a fresh one).

    Returns:
        :class:`RoutedIntent`.  Never raises: internal failures produce a
        fail-safe degraded result that keeps the status quo (continue the
        active task, or default LIGHTWEIGHT) and guesses no new intents.
    """
    return (router or IntentRouter()).route_upgrade(
        description, active_task, additional_context
    )
