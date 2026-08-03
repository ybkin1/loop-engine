"""
Intent Router — User intent analysis and automatic Loop routing.

Analyses a natural-language description to detect domains, estimate
complexity, and recommend the appropriate Loop mode.  Built on top of
the existing router.py for backward compatibility.

Core rules (as specified by the user):
1. Any high-risk factor (database / auth / payments / production data / security)
   automatically escalates to FULL — cannot be downgraded.
2. When uncertain, escalate rather than misjudge (confidence < 0.5).
3. LIGHTWEIGHT only for: single-file scripts, simple tools, one-off tasks.
4. Multi-module, external API, deployment, or ongoing iteration → at least STANDARD.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum

from loop_core.router import (
    LoopMode,
    ProjectProfile,
    RiskLevel,
    RouteResult,
    route_intent,
)

# ---------------------------------------------------------------------------
# Domain-detection keyword maps
# ---------------------------------------------------------------------------

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "web": [
        "html", "css", "javascript", "typescript", "react", "vue", "angular",
        "svelte", "next.js", "nuxt", "frontend", "front-end", "browser",
        "dom", "responsive", "webpack", "vite", "spa", "ssr", "seo",
        "tailwind", "bootstrap", "web app", "webapp", "website", "web",
    ],
    "mobile": [
        "ios", "android", "react native", "flutter", "swift", "kotlin",
        "mobile", "app store", "google play", "cordova", "capacitor",
        "pwa",
    ],
    "api": [
        "rest", "graphql", "grpc", "api", "endpoint", "openapi", "swagger",
        "http", "websocket", "rpc", "soap", "json api", "webhook",
        "backend",
    ],
    "data": [
        "database", "sql", "nosql", "postgresql", "mysql", "mongodb",
        "sqlite", "redis", "etl", "data pipeline", "analytics", "olap",
        "data warehouse", "migration", "schema", "orm", "query",
        "cassandra", "dynamodb", "bigquery", "snowflake", "databricks",
        "data lake",
    ],
    "cli": [
        "cli", "command line", "terminal", "console", "argparse", "click",
        "typer", "shell", "bash", "scripting", "cron", "batch",
    ],
    "embedded": [
        "iot", "embedded", "firmware", "microcontroller", "arduino",
        "raspberry pi", "esp32", "rtos", "hardware", "sensor",
        "bluetooth low energy", "ble", "mqtt",
    ],
    "cloud_infra": [
        "aws", "azure", "gcp", "terraform", "kubernetes", "docker",
        "ci/cd", "pipeline", "infrastructure", "serverless", "lambda",
        "ec2", "s3", "cloudfront", "iam", "vpc", "helm", "ansible",
    ],
    "ai_ml": [
        "machine learning", "ml", "ai", "deep learning", "neural network",
        "llm", "transformer", "gpt", "bert", "nlp", "computer vision",
        "training", "inference", "fine-tuning", "rag", "embedding",
        "model", "pytorch", "tensorflow", "scikit-learn", "jupyter",
        "data science",
    ],
}

# Low-risk keyword indicators (suggest LIGHTWEIGHT-eligible tasks)
LIGHTWEIGHT_KEYWORDS: list[str] = [
    "simple", "quick", "small", "one-off", "oneoff", "single file",
    "single-file", "bug fix", "bugfix", "minor", "typo", "spelling",
    "comment", "rename", "refactor single", "fix lint", "lint fix",
    "format", "add docstring", "update readme", "readme", "changelog",
    "trivial", "cosmetic", "clean up import", "organize import",
]

# High-risk keywords that trigger automatic escalation
HIGH_RISK_KEYWORDS: list[str] = [
    "payment", "billing", "invoice", "credit card", "subscription",
    "production", "live environment", "prod data",
    "auth", "authentication", "authorization", "permission", "acl", "rbac",
    "password", "secret", "token", "credential", "api key",
    "database migration", "schema migration", "data migration",
    "pii", "gdpr", "hipaa", "compliance", "regulatory",
    "encryption", "cryptography", "ssl", "tls", "certificate",
    "security", "vulnerability", "xss", "csrf", "sql injection",
    "audit", "logging sensitive", "access control",
    "deploy to production", "release to prod",
    "user data", "customer data", "personal data",
]

# Medium-risk keywords (suggest at least STANDARD)
MEDIUM_RISK_KEYWORDS: list[str] = [
    "api", "rest", "graphql", "endpoint", "backend",
    "deploy", "deployment", "ci/cd", "pipeline",
    "integration", "third-party", "external service",
    "module", "package", "library", "plugin",
    "refactor", "rewrite", "restructure",
    "test suite", "unit test", "integration test", "e2e test",
    "performance", "optimize", "cache", "caching",
    "async", "concurrency", "parallel", "threading",
    "microservice", "service",
    "breaking change", "deprecation",
    "multi-module", "monorepo",
]

# Scale indicators (each occurrence increments a complexity counter)
SCALE_INDICATORS: list[tuple[str, float]] = [
    (r"\bmicroservice", 0.05),
    (r"\bmonorepo", 0.05),
    (r"\benterprise", 0.05),
    (r"\bscal(e|able|ing|ability)", 0.04),
    (r"\breal.?time", 0.03),
    (r"\bdistributed", 0.04),
    (r"\bhigh.?availability", 0.05),
    (r"\bfault.?tolerant", 0.04),
    (r"\bmulti.?tenant", 0.04),
    (r"\blegacy", 0.03),
    (r"\bmigration", 0.03),
    (r"\bregression", 0.03),
    (r"\bzero.?downtime", 0.05),
    (r"\bblue.?green", 0.05),
    (r"\bcanary", 0.05),
    (r"\bfeature.?flag", 0.03),
    (r"\bab\s+test", 0.03),
    (r"\bobservability", 0.03),
    (r"\bmonitoring", 0.03),
    (r"\balerting", 0.03),
    (r"\breplication", 0.04),
    (r"\bsharding", 0.04),
    (r"\bpartitioning", 0.03),
    (r"\bmessage.?queue", 0.04),
    (r"\bevent.?driven", 0.04),
    (r"\bstreaming", 0.04),
    (r"\bbatch.?processing", 0.03),
    (r"\bml\b|machine.?learning|ai\b|\bllm\b", 0.05),
    (r"\bcompliance", 0.05),
    (r"\bregulatory", 0.05),
    (r"\bsox\b|\bhipaa\b|\bgdpr\b|\bpci", 0.06),
]

MAX_COMPLEXITY = 1.0
MIN_COMPLEXITY = 0.0


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

# Keyword maps for change type detection
BUG_FIX_KEYWORDS: list[str] = [
    "bug", "fix bug", "修复", "defect", "缺陷", "crash", "崩溃",
    "broken", "坏了", "不工作", "not working", "异常", "exception",
    "报错", "出错",
]

FEATURE_ADD_KEYWORDS: list[str] = [
    "新增", "添加功能", "加一个", "新功能", "new feature", "add feature",
    "implement", "实现", "增加", "支持", "support for",
]

REFACTOR_KEYWORDS: list[str] = [
    "重构", "refactor", "clean up", "整理", "restructure", "重组",
    "simplify", "简化", "优化结构", "拆分", "合并",
]

REQUIREMENT_CHANGE_KEYWORDS: list[str] = [
    "需求变了", "需求变更", "改成", "调整需求", "requirement change",
    "不再需要", "变更范围", "change scope", "修改需求",
]

QUALITY_FIX_KEYWORDS: list[str] = [
    "测试没过", "覆盖率", "lint", "type check", "类型检查",
    "性能问题", "performance issue", "加测试", "补测试", "安全漏洞",
    "security fix", "补文档", "测试", "单元测试", "集成测试",
]


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
        if len(domains) >= 4 and sum(risk_factors.values()) <= 2:
            confidence -= 0.10
            warnings.append(
                "Many domains detected but few risk factors – "
                "may be underestimating complexity."
            )

        return max(confidence, 0.0), warnings


# ---------------------------------------------------------------------------
# Module-level helpers (detection / scoring / conversion)
# ---------------------------------------------------------------------------

def _detect_domains(desc_lower: str) -> set[str]:
    """Return a set of domain labels matching the description.

    Uses word-boundary matching only for very short keywords (<= 3 chars)
    to avoid false positives (e.g. "ai" matching inside "maintain").
    Longer keywords and multi-word phrases use substring matching.
    """
    domains: set[str] = set()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            matched = False
            if " " in kw or "/" in kw or "-" in kw or len(kw) > 3:
                if kw in desc_lower:
                    matched = True
            else:
                if re.search(r'\b' + re.escape(kw) + r'\b', desc_lower):
                    matched = True
            if matched:
                domains.add(domain)
                break  # one match per domain is enough
    return domains


def _extract_risk_factors(desc_lower: str) -> dict[str, bool]:
    """Build a risk-factors dict by keyword matching against the description.

    Uses both the existing ProjectProfile fields and additional markers.
    """
    factors: dict[str, bool] = {
        # High-risk
        "has_database": False,
        "has_auth_permissions": False,
        "has_payments": False,
        "has_production_data": False,
        "has_security_requirements": False,
        # Medium-risk
        "has_multiple_modules": False,
        "has_external_api": False,
        "has_concurrency_performance": False,
        "requires_deployment": False,
        "requires_monitoring_rollback": False,
        "requires_ongoing_iteration": False,
        "has_high_uncertainty": False,
    }

    # ---- database ----
    _set_if_match(factors, "has_database", desc_lower, [
        "database", "sql", "postgresql", "mysql", "mongodb", "sqlite",
        "redis", "migration", "schema", "orm", "query",
        "cassandra", "dynamodb", "bigquery",
    ])

    # ---- auth / permissions ----
    _set_if_match(factors, "has_auth_permissions", desc_lower, [
        "auth", "authentication", "authorization", "permission",
        "acl", "rbac", "login", "logout", "session", "jwt",
        "oauth", "sso", "ldap", "role", "access control",
    ])

    # ---- payments ----
    _set_if_match(factors, "has_payments", desc_lower, [
        "payment", "billing", "invoice", "credit card", "subscription",
        "stripe", "paypal", "checkout", "transaction",
    ])

    # ---- production data ----
    _set_if_match(factors, "has_production_data", desc_lower, [
        "production", "live environment", "prod data", "prod db",
        "user data", "customer data", "personal data", "pii",
    ])

    # ---- security ----
    _set_if_match(factors, "has_security_requirements", desc_lower, [
        "security", "vulnerability", "xss", "csrf", "sql injection",
        "encryption", "cryptography", "ssl", "tls", "certificate",
        "gdpr", "hipaa", "compliance", "regulatory", "audit",
    ])

    # ---- multiple modules ----
    _set_if_match(factors, "has_multiple_modules", desc_lower, [
        "module", "multi-module", "monorepo", "package",
        "library", "plugin", "multiple components",
        "microservice", "several files",
    ])

    # ---- external API ----
    _set_if_match(factors, "has_external_api", desc_lower, [
        "api", "rest", "graphql", "grpc", "endpoint",
        "webhook", "openapi", "swagger", "http client",
        "third-party", "external service", "integration",
    ])

    # ---- concurrency / performance ----
    _set_if_match(factors, "has_concurrency_performance", desc_lower, [
        "async", "concurrency", "parallel", "thread",
        "performance", "optimize", "cache", "caching",
        "latency", "throughput", "race condition",
        "deadlock", "coroutine",
    ])

    # ---- deployment ----
    _set_if_match(factors, "requires_deployment", desc_lower, [
        "deploy", "deployment", "ci/cd", "pipeline",
        "docker", "kubernetes", "terraform", "release",
        "ship", "launch", "production",
    ])

    # ---- monitoring / rollback ----
    _set_if_match(factors, "requires_monitoring_rollback", desc_lower, [
        "rollback", "monitoring", "alerting", "observability",
        "logging", "metrics", "tracing", "dashboards",
        "blue-green", "canary", "feature flag",
    ])

    # ---- ongoing iteration ----
    _set_if_match(factors, "requires_ongoing_iteration", desc_lower, [
        "iterat", "mvp", "agile", "sprint", "roadmap",
        "ongoing", "maintain", "continue", "evolve",
        "phase 1", "phase one", "v2", "version 2",
    ])

    # ---- high uncertainty ----
    _set_if_match(factors, "has_high_uncertainty", desc_lower, [
        "maybe", "not sure", "uncertain", "explor",
        "prototype", "proof of concept", "poc",
        "experiment", "spike", "research",
    ])

    return factors


# Negation patterns — if these appear near a keyword, don't set the flag
_NEGATION_PATTERNS: list[str] = [
    r'\b(?:remove|delete|drop|eliminate|get rid of|ditch)\s+(?:the\s+)?',
    r"\b(?:don't|do not|won't|will not)\s+(?:need|use|have|want)\s+(?:a\s+)?(?:the\s+)?",
    r'\b(?:without|no)\s+(?:a\s+)?(?:the\s+)?(?:any\s+)?',
    r'\bnot\s+(?:using|needing|having)\s+(?:a\s+)?(?:the\s+)?',
]


def _is_negated(desc_lower: str, kw: str) -> bool:
    """Check if a keyword match is likely negated in context.
    
    Example: "I want to remove the database" → "database" is negated.
    """
    for pat in _NEGATION_PATTERNS:
        # Build a pattern that checks if negation appears before the keyword
        full_pat = pat + re.escape(kw)
        if re.search(full_pat, desc_lower):
            return True
    return False


def _set_if_match(
    factors: dict[str, bool],
    key: str,
    desc_lower: str,
    keywords: list[str],
) -> None:
    """Set factors[key] = True if any keyword is found in desc_lower.
    
    v3.2: Checks negation context before setting flag.
    """
    for kw in keywords:
        if " " in kw or "/" in kw or "-" in kw or len(kw) > 3:
            # Multi-word phrase or longer word — safe as substring
            if kw in desc_lower:
                if _is_negated(desc_lower, kw):
                    continue  # Skip negated match
                factors[key] = True
                return
        else:
            # Short single word — word-boundary regex match
            if re.search(r'\b' + re.escape(kw) + r'\b', desc_lower):
                if _is_negated(desc_lower, kw):
                    continue  # Skip negated match
                factors[key] = True
                return


def _compute_complexity(
    desc_lower: str,
    domains: set[str],
    risk_factors: dict[str, bool],
    domain_weight: float,
    keyword_weight: float,
    scale_weight: float,
    context: dict,
) -> float:
    """Compute a 0-1 complexity score from weighted sub-scores."""

    # ---- domain sub-score (more domains = more complex) ----------------
    domain_score = min(len(domains) / 5.0, 1.0) if domains else 0.0

    # ---- keyword sub-score --------------------------------------------
    high_count = sum(
        1 for f in [
            "has_database", "has_auth_permissions", "has_payments",
            "has_production_data", "has_security_requirements",
        ] if risk_factors.get(f)
    )
    medium_count = sum(
        1 for f in [
            "has_multiple_modules", "has_external_api",
            "has_concurrency_performance", "requires_deployment",
            "requires_monitoring_rollback", "requires_ongoing_iteration",
            "has_high_uncertainty",
        ] if risk_factors.get(f)
    )
    # High risk: each contributes 0.25, medium: 0.10
    keyword_score = min(high_count * 0.25 + medium_count * 0.10, 1.0)

    # ---- scale sub-score -----------------------------------------------
    scale_score = 0.0
    for pattern, inc in SCALE_INDICATORS:
        if re.search(pattern, desc_lower, re.IGNORECASE):
            scale_score += inc
    # Incorporate context hints
    file_count = context.get("file_count", 0)
    module_count = context.get("module_count", 0)
    if file_count > 10:
        scale_score += min(file_count / 100.0, 0.15)
    if module_count > 3:
        scale_score += min(module_count / 20.0, 0.10)
    scale_score = min(scale_score, 1.0)

    # ---- weighted sum --------------------------------------------------
    raw = (domain_weight * domain_score
           + keyword_weight * keyword_score
           + scale_weight * scale_score)

    # ---- lightweight discount ------------------------------------------
    # Check if the description looks deliberately simple
    lightweight_hint_count = sum(
        1 for kw in LIGHTWEIGHT_KEYWORDS if kw in desc_lower
    )
    if lightweight_hint_count >= 2:
        raw *= 0.5  # strong discount for explicitly simple things

    # ---- boost for high-risk overlaps ----------------------------------
    if high_count >= 2:
        raw = max(raw, 0.70)  # floor when multiple high-risk factors exist

    return max(min(raw, MAX_COMPLEXITY), MIN_COMPLEXITY)


def _build_reasoning(
    domains: set[str],
    complexity_score: float,
    risk_factors: dict[str, bool],
    mode: LoopMode,
    escalated: bool,
    escalate_reason: str,
    confidence: float,
) -> str:
    """Build human-readable reasoning for the analysis."""
    parts: list[str] = []

    if domains:
        parts.append(f"Detected domains: {', '.join(sorted(domains))}.")
    else:
        parts.append("No specific domains detected.")

    parts.append(f"Complexity score: {complexity_score:.2f}.")

    active_risks = [k for k, v in risk_factors.items() if v]
    if active_risks:
        # Group high vs medium
        high = [r for r in active_risks if r.startswith("has_") and r not in (
            "has_multiple_modules", "has_concurrency_performance",
        ) and r in [
            "has_database", "has_auth_permissions", "has_payments",
            "has_production_data", "has_security_requirements",
        ]]
        medium = [r for r in active_risks if r not in high]
        if high:
            parts.append(f"High-risk factors: {', '.join(high)}.")
        if medium:
            parts.append(f"Medium-risk factors: {', '.join(medium)}.")

    if escalated:
        parts.append(f"ESCALATION: {escalate_reason}")
    else:
        parts.append(f"Mode {mode.value} selected at confidence {confidence:.2f}.")

    return " ".join(parts)


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

# Max task frames produced in one round (defensive cap)
_MAX_TASK_FRAMES: int = 5

# Explicit invalidation conditions for sticky routing: a new-task marker
# or a task-completion/closure marker overrides the default "continue the
# active task" behaviour.  Heuristic list — kept explicit and documented.
INTENT_SWITCH_KEYWORDS: list[str] = [
    # --- new-task markers ---
    "new task", "start a new task", "start another task", "another task",
    "other task", "different task", "separate task", "unrelated task",
    "next task", "switch task", "switch to",
    "新任务", "开始新任务", "换个任务", "另一个任务", "其他任务",
    "别的任务", "下一个任务", "切换任务", "换一个任务", "换一项工作",
    # --- completion / closure markers ---
    "task is done", "task is complete", "task done", "task completed",
    "mark complete", "mark as complete", "mark completed",
    "mark as completed", "close the task", "close task",
    "cancel the task", "abort the task",
    "任务完成", "任务已完成", "任务结束", "结束任务", "关闭任务",
    "取消任务", "终止任务", "收尾任务", "已完成", "完成了",
]

_TASK_ID_RE = re.compile(r"\bT-\d{4}\b", re.IGNORECASE)


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
    def from_task(task: dict) -> "ActiveTaskSnapshot":
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


def split_intents(description: str, max_frames: int = _MAX_TASK_FRAMES) -> list[str]:
    """Heuristically split one user input into multiple intents (U5).

    Conservative, explicit-marker-only splitting (no sentence-level
    splitting) to avoid fragmenting a single intent into noise:

    - semicolons (``；`` / ``;``)
    - numbered task lists (``1. ... 2. ...``)
    - English sequential/additive connectors (``then``, ``after that``,
      ``afterwards``, ``next``, ``finally``, ``also``, ``additionally``,
      ``moreover``, ``meanwhile``)
    - Chinese connectors when preceded by punctuation (``，然后``,
      ``。接下来``, ``；之后``, ...): ``然后/接下来/之后/接着/其次/再次/
      最后/同时/另外/此外/除此之外``
    - a sentence break followed by an action starter (``。新增``,
      ``。修复``, ``。写``, ...)

    Returns the ordered intents (max ``max_frames``), or ``[]`` for
    empty/invalid input.
    """
    if not isinstance(description, str) or not description.strip():
        return []
    parts: list[str] = []
    for raw in _INTENT_SPLIT_RE.split(description):
        part = re.sub(r"^\d+\.\s*", "", raw.strip())
        # Drop leading Chinese connectors left over from a split (e.g. a
        # segment that began right after a semicolon).
        part = re.sub(
            r"^(?:然后|接下来|之后|接着|其次|再次|最后|同时|另外|此外|除此之外)\s*",
            "", part,
        )
        part = part.strip(" \t，。；;,.：:、")
        if part:
            parts.append(part)
        if len(parts) >= max_frames:
            break
    return parts


# Split markers — see split_intents() docstring.  The Chinese connector
# branch requires a preceding punctuation char (lookbehind) so phrases
# like "登录之后" (temporal reference inside one intent) are NOT split;
# the sentence-break branch uses a zero-width lookahead so the action
# verb ("新增" in "。新增...") stays attached to the follow-up frame.
_INTENT_SPLIT_RE = re.compile(
    r"[；;]"
    r"|(?:\s+\d+\.\s+)"
    r"|(?i:\s+(?:then|after\s+that|afterwards|next|finally|also|additionally|moreover|meanwhile)\s*[,，]?\s+)"
    r"|(?<=[，。；,.;：:、])(?:然后|接下来|之后|接着|其次|再次|最后|同时|另外|此外|除此之外)"
    r"|(?<=。)(?=新增|添加|加|修复|重构|实现|部署|优化|更新|写|创建|移除|删除|升级|支持|增加|设计)"
)


def detect_intent_switch(description: str) -> tuple[bool, str]:
    """Detect explicit intent-switch / task-completion signals (U5).

    These are the explicit invalidation conditions for sticky routing:
    a new-task marker or a completion/closure marker overrides the
    default "continue the active task" behaviour, allowing the route to
    cut out of the active task domain.

    Returns ``(switched, reason)``.
    """
    desc_lower = description.lower()
    for kw in INTENT_SWITCH_KEYWORDS:
        if kw in desc_lower:
            return True, f"intent-switch marker {kw!r} detected"
    return False, ""


def _other_task_refs(desc_lower: str, active_task_id: str) -> list[str]:
    """Task ids mentioned in the input that differ from the active task."""
    seen: list[str] = []
    for m in _TASK_ID_RE.finditer(desc_lower):
        tid = m.group(0).upper()
        if tid != active_task_id.upper() and tid not in seen:
            seen.append(tid)
    return seen


# Completion/closure verbs used by _active_task_completion_signal()
_COMPLETION_VERBS: list[str] = [
    "complete", "completed", "done", "finished", "close", "closed",
    "abort", "cancel", "canceled", "cancelled",
    "结束", "完成", "关闭", "取消", "终止", "收尾",
]


def _active_task_completion_signal(desc_lower: str, active_task_id: str) -> str:
    """Detect "mark <active task> complete"-style closure signals.

    When the active task id is mentioned together with a
    completion/closure verb in its vicinity (proximity window), the
    active task is being closed and stickiness must not apply.  Returns
    the evidence string, or "" when no signal is found.
    """
    upper = desc_lower.upper()
    task_pos = upper.find(active_task_id.upper())
    if task_pos < 0:
        return ""
    window = desc_lower[max(0, task_pos - 20): task_pos + len(active_task_id) + 40]
    for verb in _COMPLETION_VERBS:
        if verb in window:
            return (
                f"active task {active_task_id} referenced together with "
                f"completion/closure marker {verb!r}"
            )
    return ""


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
