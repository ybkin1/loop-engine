"""
Intent Router — 域检测 / 风险提取 / 复杂度评分辅助（T-0110 批 B-1 拆分产物）。

从 loop_core/intent_router.py 外提（design-common-weakness.md 1.3 边界：
"检测/评分辅助（_detect_domains/_extract_risk_factors/_is_negated/
_set_if_match/_compute_complexity/_build_reasoning）:626-872"，
含 _NEGATION_PATTERNS :770 起的否定语境匹配）。

内容（原文件逐字迁移，行为零变化）：_detect_domains / _extract_risk_factors /
_is_negated / _set_if_match / _compute_complexity / _build_reasoning。

依赖（均为叶子/既有模块）：
- loop_core.intent_keywords（D5-4 词表外提）
- loop_core.constants（KEYWORD_BOUNDARY_MAX_LEN —— T-0110 批 A 接线保持）
- loop_core.router（LoopMode 仅用于 _build_reasoning 的 mode.value 呈现）

public 面由 intent_router 壳 re-export 保持（from loop_core.
intent_router import * 兼容）。
"""
from __future__ import annotations

import re

from loop_core.constants import KEYWORD_BOUNDARY_MAX_LEN
from loop_core.intent_keywords import (
    _NEGATION_PATTERNS,
    DOMAIN_KEYWORDS,
    LIGHTWEIGHT_KEYWORDS,
    MAX_COMPLEXITY,
    MIN_COMPLEXITY,
    SCALE_INDICATORS,
)
from loop_core.router import LoopMode


def _detect_domains(desc_lower: str) -> set[str]:
    """Return a set of domain labels matching the description.

    Uses word-boundary matching only for very short keywords
    (<= KEYWORD_BOUNDARY_MAX_LEN chars) to avoid false positives
    (e.g. "ai" matching inside "maintain").
    Longer keywords and multi-word phrases use substring matching.
    """
    domains: set[str] = set()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            matched = False
            if " " in kw or "/" in kw or "-" in kw or len(kw) > KEYWORD_BOUNDARY_MAX_LEN:
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
        if " " in kw or "/" in kw or "-" in kw or len(kw) > KEYWORD_BOUNDARY_MAX_LEN:
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
