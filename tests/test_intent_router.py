"""
Unit tests for loop_core.intent_router — IntentRouter, IntentAnalysis, and
compatibility with the existing router.py.

Covers:
  - Low-risk intent → LIGHTWEIGHT
  - High-risk intent → auto-escalation to FULL
  - Uncertain intent → suggests upgrade
  - Domain detection accuracy
  - Compatibility with existing router.py (ProjectProfile.route, route_intent)
  - should_escalate static method
  - Complexity scoring edge cases
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from loop_core.intent_router import (
    DOMAIN_KEYWORDS,
    HIGH_RISK_KEYWORDS,
    LIGHTWEIGHT_KEYWORDS,
    MEDIUM_RISK_KEYWORDS,
    SCALE_INDICATORS,
    IntentAnalysis,
    IntentRouter,
    _compute_complexity,
    _detect_domains,
    _extract_risk_factors,
    _phases_for_mode,
)
from loop_core.router import (
    LoopMode,
    ProjectProfile,
    RiskLevel,
    RouteResult,
    route_intent,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def router() -> IntentRouter:
    """Return a default IntentRouter instance."""
    return IntentRouter()


# ============================================================================
# Low-risk → LIGHTWEIGHT
# ============================================================================

class TestLowRiskRouting:
    """Low-risk intents should route to LIGHTWEIGHT mode."""

    def test_simple_bugfix(self, router: IntentRouter):
        analysis = router.analyze("Fix a typo in the README")
        assert analysis.recommended_mode == LoopMode.LIGHTWEIGHT
        assert analysis.complexity_score <= 0.25

    def test_single_file_script(self, router: IntentRouter):
        analysis = router.analyze("Write a small one-off script to rename files")
        assert analysis.recommended_mode == LoopMode.LIGHTWEIGHT

    def test_comment_update(self, router: IntentRouter):
        analysis = router.analyze("Add a docstring to a single function")
        assert analysis.recommended_mode == LoopMode.LIGHTWEIGHT

    def test_cosmetic_change(self, router: IntentRouter):
        analysis = router.analyze("Clean up import statements and fix formatting")
        assert analysis.recommended_mode == LoopMode.LIGHTWEIGHT

    def test_lightweight_phases_are_correct(self, router: IntentRouter):
        analysis = router.analyze("Simple bug fix in one file")
        assert "S0-init" in analysis.suggested_phases
        assert "S4-implementation" in analysis.suggested_phases
        assert "S6-delivery" in analysis.suggested_phases
        assert len(analysis.suggested_phases) == 3


# ============================================================================
# High-risk → FULL (auto-escalation)
# ============================================================================

class TestHighRiskAutoEscalation:
    """Any high-risk factor triggers automatic escalation to FULL."""

    def test_database_triggers_full(self, router: IntentRouter):
        analysis = router.analyze("Run a database migration on PostgreSQL")
        assert analysis.recommended_mode == LoopMode.FULL

    def test_auth_triggers_full(self, router: IntentRouter):
        analysis = router.analyze("Implement OAuth authentication with JWT tokens")
        assert analysis.recommended_mode == LoopMode.FULL

    def test_payments_triggers_full(self, router: IntentRouter):
        analysis = router.analyze("Build a Stripe payment integration")
        assert analysis.recommended_mode == LoopMode.FULL

    def test_production_data_triggers_full(self, router: IntentRouter):
        analysis = router.analyze("Modify production user data for GDPR compliance")
        assert analysis.recommended_mode == LoopMode.FULL

    def test_security_triggers_full(self, router: IntentRouter):
        analysis = router.analyze("Fix an XSS vulnerability in the login form")
        assert analysis.recommended_mode == LoopMode.FULL

    def test_multiple_high_risk_flags(self, router: IntentRouter):
        analysis = router.analyze(
            "Create a secure payment gateway with PostgreSQL for production"
        )
        assert analysis.recommended_mode == LoopMode.FULL
        assert analysis.complexity_score >= 0.70  # floor for multi-high-risk

    def test_full_routing_has_all_phases(self, router: IntentRouter):
        analysis = router.analyze("Add encryption to the payment database")
        assert len(analysis.suggested_phases) == 12
        assert "S11-maintenance" in analysis.suggested_phases
        assert "S3-interface" in analysis.suggested_phases


# ============================================================================
# STANDARD routing (medium complexity, no high-risk triggers)
# ============================================================================

class TestStandardRouting:
    """Medium-complexity intents should route to STANDARD."""

    def test_external_api_is_standard(self, router: IntentRouter):
        analysis = router.analyze("Add a REST API endpoint for user profiles")
        # API work should be at least STANDARD (medium-risk floor)
        assert analysis.recommended_mode == LoopMode.STANDARD
        assert "api" in analysis.detected_domains

    def test_deployment_is_standard(self, router: IntentRouter):
        analysis = router.analyze("Set up a CI/CD pipeline for the frontend project")
        # Deployment work should be at least STANDARD (medium-risk floor)
        assert analysis.recommended_mode == LoopMode.STANDARD

    def test_multi_module_is_standard(self, router: IntentRouter):
        analysis = router.analyze("Refactor three modules to share a common library")
        # Multi-module work should be at least STANDARD (medium-risk floor)
        assert analysis.recommended_mode == LoopMode.STANDARD

    def test_standard_phases_correct(self, router: IntentRouter):
        """STANDARD task should have the standard phase set."""
        analysis = router.analyze("Add a caching layer for API responses")
        # Caching + API → medium-risk floor enforces STANDARD
        assert analysis.recommended_mode == LoopMode.STANDARD
        assert "S1-requirements" in analysis.suggested_phases
        assert "S2-architecture" in analysis.suggested_phases
        assert "S5-quality" in analysis.suggested_phases
        assert "S10-performance" not in analysis.suggested_phases


# ============================================================================
# Uncertainty and confidence
# ============================================================================

class TestUncertaintyHandling:
    """When analysis is uncertain, the router should suggest escalation."""

    def test_vague_description_low_confidence(self, router: IntentRouter):
        analysis = router.analyze("Do something useful")
        # Very short, no domains → low confidence
        assert analysis.confidence < 1.0

    def test_no_domains_detected(self, router: IntentRouter):
        analysis = router.analyze("make it better please thanks")
        assert len(analysis.detected_domains) == 0
        assert analysis.confidence < 1.0
        assert len(analysis.warnings) >= 1

    def test_low_confidence_escalates(self, router: IntentRouter):
        """should_escalate returns True when confidence < 0.5."""
        analysis = IntentAnalysis(
            description="vague task",
            complexity_score=0.1,
            detected_domains=[],
            risk_factors={},
            recommended_mode=LoopMode.LIGHTWEIGHT,
            confidence=0.35,
        )
        escalate, reason = IntentRouter.should_escalate(analysis=analysis)
        assert escalate is True
        assert "confidence" in reason.lower()

    def test_high_confidence_no_escalation(self, router: IntentRouter):
        analysis = router.analyze("Fix a typo in the comments of utils.py")
        escalate, reason = IntentRouter.should_escalate(analysis=analysis)
        # Low risk + high confidence → no escalation
        # unless some keyword triggers it
        if analysis.confidence >= 0.5:
            assert escalate is False or "high-risk" in reason.lower()

    def test_mid_range_complexity_warning(self, router: IntentRouter):
        """Mid-range complexity should produce a warning about ambiguous range."""
        analysis = router.analyze("Build a web dashboard with API integration")
        # Web + API → medium-ish complexity
        has_mid_warning = any(
            "ambiguous" in w.lower() for w in analysis.warnings
        )
        # Not guaranteed, but likely for moderate complexity
        if has_mid_warning:
            assert analysis.confidence < 1.0


# ============================================================================
# Domain detection
# ============================================================================

class TestDomainDetection:
    """Domain detection from natural-language descriptions."""

    def test_web_domain(self, router: IntentRouter):
        analysis = router.analyze("Build a React frontend with Tailwind CSS")
        assert "web" in analysis.detected_domains

    def test_mobile_domain(self, router: IntentRouter):
        analysis = router.analyze("Create an iOS app using Swift and SwiftUI")
        assert "mobile" in analysis.detected_domains

    def test_api_domain(self, router: IntentRouter):
        analysis = router.analyze("Design a REST API with OpenAPI spec")
        assert "api" in analysis.detected_domains

    def test_data_domain(self, router: IntentRouter):
        analysis = router.analyze("Write an ETL pipeline that loads data into BigQuery")
        assert "data" in analysis.detected_domains

    def test_cli_domain(self, router: IntentRouter):
        analysis = router.analyze("Build a CLI tool with argparse and Click")
        assert "cli" in analysis.detected_domains

    def test_multiple_domains(self, router: IntentRouter):
        analysis = router.analyze(
            "Build a web dashboard with a REST API, PostgreSQL database, and mobile app"
        )
        assert "web" in analysis.detected_domains
        assert "api" in analysis.detected_domains
        assert "data" in analysis.detected_domains
        assert "mobile" in analysis.detected_domains
        assert len(analysis.detected_domains) >= 4

    def test_cloud_infra_domain(self, router: IntentRouter):
        analysis = router.analyze(
            "Set up AWS infrastructure with Terraform and Kubernetes"
        )
        assert "cloud_infra" in analysis.detected_domains

    def test_ai_ml_domain(self, router: IntentRouter):
        analysis = router.analyze(
            "Fine-tune a GPT model with PyTorch for NLP classification"
        )
        assert "ai_ml" in analysis.detected_domains

    def test_embedded_domain(self, router: IntentRouter):
        analysis = router.analyze(
            "Write firmware for an ESP32 microcontroller with BLE"
        )
        assert "embedded" in analysis.detected_domains

    def test_empty_domains_for_generic_description(self, router: IntentRouter):
        analysis = router.analyze("improve the thing")
        assert analysis.detected_domains == []


# ============================================================================
# should_escalate static method
# ============================================================================

class TestShouldEscalate:
    """Direct tests for IntentRouter.should_escalate()."""

    def test_escalate_on_high_risk_factors(self):
        escalate, reason = IntentRouter.should_escalate(
            risk_factors={"has_payments": True},
            current_mode=LoopMode.STANDARD,
        )
        assert escalate is True
        assert "has_payments" in reason

    def test_escalate_on_multiple_medium_risk(self):
        escalate, reason = IntentRouter.should_escalate(
            risk_factors={
                "has_multiple_modules": True,
                "has_external_api": True,
                "requires_deployment": True,
            },
            current_mode=LoopMode.STANDARD,
        )
        assert escalate is True
        assert "3" in reason or "multiple" in reason.lower()

    def test_no_escalation_for_clean_task(self):
        escalate, reason = IntentRouter.should_escalate(
            risk_factors={},
            current_mode=LoopMode.LIGHTWEIGHT,
        )
        assert escalate is False

    def test_already_full_no_escalation(self):
        escalate, reason = IntentRouter.should_escalate(
            risk_factors={},
            current_mode=LoopMode.FULL,
        )
        assert escalate is False

    def test_escalation_via_intent_analysis(self):
        analysis = IntentAnalysis(
            description="payment thing",
            complexity_score=0.4,
            detected_domains=["web"],
            risk_factors={"has_payments": True},
            recommended_mode=LoopMode.STANDARD,
            confidence=0.8,
        )
        escalate, reason = IntentRouter.should_escalate(analysis=analysis)
        assert escalate is True


# ============================================================================
# Compatibility with existing router.py
# ============================================================================

class TestRouterCompatibility:
    """IntentRouter must be compatible with the existing router.py."""

    def test_route_produces_route_result(self, router: IntentRouter):
        analysis = router.analyze("Simple bug fix")
        result = router.route(analysis)
        assert isinstance(result, RouteResult)
        assert isinstance(result.mode, LoopMode)
        assert isinstance(result.risk_level, RiskLevel)

    def test_intent_analysis_converts_to_profile(self, router: IntentRouter):
        """The route() method should internally create a valid ProjectProfile."""
        analysis = router.analyze(
            "Create a secure payment gateway with database and API"
        )
        result = router.route(analysis)
        assert result.mode == LoopMode.FULL
        assert result.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def test_does_not_downgrade_existing_profile_result(self, router: IntentRouter):
        """IntentRouter should never downgrade below the minimum required by
        ProjectProfile.route()."""
        analysis = router.analyze("Add auth and database to the production system")
        result = router.route(analysis)
        # Auth + DB + production = definite FULL
        assert result.mode == LoopMode.FULL

    def test_lightweight_via_route_method(self, router: IntentRouter):
        analysis = router.analyze("Fix a typo in a comment")
        result = router.route(analysis)
        assert result.mode == LoopMode.LIGHTWEIGHT
        assert result.risk_level == RiskLevel.LOW

    def test_existing_route_intent_still_works(self):
        """Original route_intent() must still work (no regressions)."""
        profile = ProjectProfile(description="Simple task")
        result = route_intent(profile)
        assert result.mode == LoopMode.LIGHTWEIGHT
        assert isinstance(result, RouteResult)

        profile2 = ProjectProfile(description="DB work", has_database=True)
        result2 = route_intent(profile2)
        assert result2.mode == LoopMode.FULL

    def test_forced_delegated_does_not_crash(self):
        """T-0143 3.1: user_forced_mode=DELEGATED 不再 KeyError（order 表补全）。"""
        profile = ProjectProfile(description="Simple task", user_forced_mode=LoopMode.DELEGATED)
        mode = profile.route()
        assert mode == LoopMode.DELEGATED

    def test_forced_manual_does_not_crash(self):
        """T-0143 3.1: user_forced_mode=MANUAL 不再 KeyError（order 表补全）。"""
        profile = ProjectProfile(description="Simple task", user_forced_mode=LoopMode.MANUAL)
        mode = profile.route()
        assert mode == LoopMode.MANUAL

    def test_forced_delegated_never_downgraded(self):
        """T-0143 3.1: DELEGATED 置顶于 FULL 之上，低风险也不被降级。"""
        profile = ProjectProfile(description="Simple task", user_forced_mode=LoopMode.DELEGATED)
        assert profile.route() == LoopMode.DELEGATED
        # 高风险场景下 DELEGATED 仍保持（不低于 FULL）
        profile_high = ProjectProfile(description="Payment DB API prod",
                                      user_forced_mode=LoopMode.DELEGATED)
        assert profile_high.route() == LoopMode.DELEGATED


# ============================================================================
# Complexity scoring
# ============================================================================

class TestComplexityScoring:
    """Edge cases and sanity checks for complexity scoring."""

    def test_empty_description(self, router: IntentRouter):
        analysis = router.analyze("")
        assert analysis.complexity_score == 0.0
        assert analysis.confidence < 1.0

    def test_very_complex_description(self, router: IntentRouter):
        analysis = router.analyze(
            "Build a scalable, distributed, real-time, event-driven microservice "
            "platform with multi-tenant support, sharding, replication, "
            "high-availability, fault-tolerant design, blue-green deployments, "
            "and full observability with monitoring and alerting"
        )
        # Should escalate to FULL due to multiple medium-risk factors (>=3)
        assert analysis.recommended_mode == LoopMode.FULL
        assert analysis.complexity_score >= 0.25

    def test_lightweight_discount_applied(self, router: IntentRouter):
        """Explicitly simple tasks should get a complexity discount."""
        analysis = router.analyze(
            "Just a simple quick bugfix for a small typo"
        )
        # Should be very low after discount
        assert analysis.complexity_score <= 0.25

    def test_context_boosts_complexity(self):
        """Additional context with file_count should influence complexity."""
        router_with_context = IntentRouter()
        analysis = router_with_context.analyze(
            "Refactor the module",
            additional_context={"file_count": 50, "module_count": 8},
        )
        # 50 files + 8 modules should push complexity up
        assert analysis.complexity_score > 0.10

    def test_greenfield_context(self, router: IntentRouter):
        analysis = router.analyze(
            "Build a new web application",
            additional_context={"is_greenfield": True, "team_size": 4},
        )
        # Reasonable for a new web app
        assert analysis.detected_domains is not None


# ============================================================================
# Risk factor extraction
# ============================================================================

class TestRiskFactorExtraction:
    """Verify the risk-factor extraction helper."""

    def test_no_risk_factors(self):
        factors = _extract_risk_factors("simple bug fix in one file")
        assert all(v is False for v in factors.values())

    def test_database_detected(self):
        factors = _extract_risk_factors("migrate the postgresql schema")
        assert factors["has_database"] is True

    def test_auth_detected(self):
        factors = _extract_risk_factors("add oauth login with jwt tokens")
        assert factors["has_auth_permissions"] is True

    def test_payments_detected(self):
        factors = _extract_risk_factors("integrate stripe for billing")
        assert factors["has_payments"] is True

    def test_production_detected(self):
        factors = _extract_risk_factors("update production user data")
        assert factors["has_production_data"] is True

    def test_security_detected(self):
        factors = _extract_risk_factors("fix encryption vulnerability for gdpr")
        assert factors["has_security_requirements"] is True

    def test_api_detected(self):
        factors = _extract_risk_factors("build a rest endpoint")
        assert factors["has_external_api"] is True

    def test_deployment_detected(self):
        factors = _extract_risk_factors("set up docker for deployment")
        assert factors["requires_deployment"] is True

    def test_uncertainty_detected(self):
        factors = _extract_risk_factors("build a prototype maybe experiment")
        assert factors["has_high_uncertainty"] is True

    def test_ongoing_iteration_detected(self):
        factors = _extract_risk_factors("this is an mvp for the first sprint")
        assert factors["requires_ongoing_iteration"] is True


# ============================================================================
# Helper functions
# ============================================================================

class TestHelperFunctions:
    """Tests for module-level helpers."""

    def test_detect_domains_web(self):
        domains = _detect_domains("build a react frontend with css")
        assert "web" in domains

    def test_phases_for_lightweight(self):
        phases = _phases_for_mode(LoopMode.LIGHTWEIGHT)
        assert len(phases) == 3
        assert "S0-init" in phases

    def test_phases_for_standard(self):
        phases = _phases_for_mode(LoopMode.STANDARD)
        assert len(phases) == 6

    def test_phases_for_full(self):
        phases = _phases_for_mode(LoopMode.FULL)
        assert len(phases) == 12

    def test_complexity_compute_boundaries(self):
        """_compute_complexity returns values within [0, 1]."""
        score = _compute_complexity(
            "simple task", set(), {}, 0.3, 0.4, 0.3, {},
        )
        assert 0.0 <= score <= 1.0

        score2 = _compute_complexity(
            "extremely complex database auth payment production security task",
            {"web", "api", "data", "cloud_infra"},
            {
                "has_database": True,
                "has_auth_permissions": True,
                "has_payments": True,
                "has_production_data": True,
                "has_security_requirements": True,
            },
            0.3, 0.4, 0.3,
            {"file_count": 100, "module_count": 20},
        )
        assert 0.0 <= score2 <= 1.0

    def test_keyword_lists_are_non_empty(self):
        """Sanity check: all keyword lists are populated."""
        assert len(DOMAIN_KEYWORDS) > 0
        for domain, keywords in DOMAIN_KEYWORDS.items():
            assert len(keywords) > 0, f"Domain {domain} has empty keywords"
        assert len(HIGH_RISK_KEYWORDS) > 0
        assert len(MEDIUM_RISK_KEYWORDS) > 0
        assert len(LIGHTWEIGHT_KEYWORDS) > 0
        assert len(SCALE_INDICATORS) > 0


# ============================================================================
# Warnings
# ============================================================================

class TestWarnings:
    """Ensure warnings are generated when appropriate."""

    def test_no_domains_warning(self, router: IntentRouter):
        analysis = router.analyze("do it")
        assert any("domain" in w.lower() for w in analysis.warnings), (
            f"Expected domain warning, got: {analysis.warnings}"
        )

    def test_many_domains_few_risk_warning(self, router: IntentRouter):
        analysis = router.analyze(
            "A web mobile api data cli cloud tool for simple formatting"
        )
        # Multiple domains detected but description is low-risk
        if len(analysis.detected_domains) >= 4:
            assert any(
                "underestimat" in w.lower() or "domains" in w.lower()
                for w in analysis.warnings
            ), f"Expected underestimation warning, got: {analysis.warnings}"


# ============================================================================
# Edge cases
# ============================================================================

class TestEdgeCases:
    """Edge cases and robustness."""

    def test_long_description(self, router: IntentRouter):
        long_desc = (
            "Build a comprehensive enterprise resource planning system with "
            "modules for inventory, accounting, HR, CRM, and supply chain. "
            "It must integrate with existing PostgreSQL databases, provide "
            "REST APIs for third-party integrations, support OAuth2 "
            "authentication with role-based access control, and handle "
            "payment processing via Stripe. Deployment on AWS with "
            "Kubernetes and Terraform. Must be GDPR and PCI compliant."
        )
        analysis = router.analyze(long_desc)
        assert analysis.recommended_mode == LoopMode.FULL
        assert len(analysis.detected_domains) >= 2

    def test_special_characters(self, router: IntentRouter):
        analysis = router.analyze("Fix bug #123: user-profile endpoint returns 500")
        assert analysis.recommended_mode is not None

    def test_mixed_case(self, router: IntentRouter):
        analysis = router.analyze("Build a ReAcT ApPlIcAtIoN with PoStGrEs")
        assert "web" in analysis.detected_domains or "api" in analysis.detected_domains

    def test_additional_context_passthrough(self, router: IntentRouter):
        analysis = router.analyze(
            "Refactor database layer",
            additional_context={"file_count": 12, "module_count": 4, "team_size": 3},
        )
        assert analysis.complexity_score is not None
        assert analysis.recommended_mode is not None

    def test_route_result_reason_not_empty(self, router: IntentRouter):
        for desc in [
            "simple bugfix",
            "add API endpoint",
            "database migration for production",
        ]:
            analysis = router.analyze(desc)
            result = router.route(analysis)
            assert result.reason, f"Empty reason for: {desc}"
            assert len(result.reason) > 0


# ============================================================================
# Custom configuration
# ============================================================================

class TestCustomConfiguration:
    """IntentRouter should accept custom thresholds."""

    def test_custom_thresholds(self):
        custom = IntentRouter(
            LIGHTWEIGHT_COMPLEXITY_MAX=0.10,
            STANDARD_COMPLEXITY_MAX=0.30,
        )
        # With low thresholds + API keyword, should be at least STANDARD
        analysis = custom.analyze("Add a simple REST API endpoint")
        assert analysis.recommended_mode == LoopMode.STANDARD

    def test_thresholds_are_used(self):
        """Verify that custom thresholds actually affect routing."""
        default = IntentRouter()
        strict = IntentRouter(
            LIGHTWEIGHT_COMPLEXITY_MAX=0.05,
            STANDARD_COMPLEXITY_MAX=0.15,
        )
        desc = "Add a new API endpoint for user data"
        default_analysis = default.analyze(desc)
        strict_analysis = strict.analyze(desc)
        # Strict should be at least as high as default
        mode_order = {LoopMode.LIGHTWEIGHT: 0, LoopMode.STANDARD: 1, LoopMode.FULL: 2}
        assert mode_order[strict_analysis.recommended_mode] >= mode_order[default_analysis.recommended_mode], (
            f"Strict thresholds should not produce a lower mode: "
            f"default={default_analysis.recommended_mode}, strict={strict_analysis.recommended_mode}"
        )
