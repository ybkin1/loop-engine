from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum

from codex_loop.planning.router import (
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
        if len(triggered_medium) >= 3:
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
