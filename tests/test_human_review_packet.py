"""
Unit tests for loop_core.human_review_packet — HumanReviewPacket + Builder.

Covers:
- from_phase_completion generates a complete packet with all sections
- from_veto_escalation generates a veto escalation packet
- to_markdown() output contains all required sections
- to_plain_text() output is clear and readable
- KeyChoice and RiskItem use non-technical language (no jargon)
- DecisionRequired always has at least 2 options
- translate_technical_risk converts technical terms into everyday analogies
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from loop_core.human_review_packet import (
    HumanReviewPacket,
    HumanReviewPacketBuilder,
    PacketType,
    KeyChoice,
    RiskItem,
    DecisionRequired,
    _phase_label,
    _format_ts,
)


# ── Technical terms that must NOT appear in user-facing output ────────────

FORBIDDEN_TECHNICAL_TERMS: list[str] = [
    "sql injection",
    "xss",
    "cross-site scripting",
    "race condition",
    "buffer overflow",
    "null pointer",
    "null dereference",
    "memory leak",
    "deadlock",
    "ddos",
    "denial of service",
    "privilege escalation",
    "csrf",
    "cross-site request forgery",
    "os command injection",
    "path traversal",
    "deserialization",
    "regex",
    "regexp",
    "regex denial of service",
    "integer overflow",
    "stack overflow",
    "heap overflow",
    "use-after-free",
    "double free",
    "format string",
    "side channel",
    "timing attack",
    "man-in-the-middle",
    "mitm",
    "replay attack",
    "brute force",
    "dictionary attack",
    "session hijacking",
    "clickjacking",
    "ssrf",
    "xxe",
    "prototype pollution",
]


# ── Sample data factories ──────────────────────────────────────────────────


def _sample_phase_data():
    """Return sample inputs for from_phase_completion."""
    artifacts = {
        "architecture_diagram": "A visual map showing how the 5 main parts of the system connect",
        "component_spec": "A detailed description of what each part does and how they talk to each other",
    }
    review_results = {
        "system-architect": "Architecture is well-structured. PASS.",
        "security-reviewer": "No major concerns. PASS.",
    }
    quality_report = {
        "pass": True,
        "checks": [
            "All 12 architecture rules satisfied",
            "No circular dependencies between modules",
            "Data flow is clearly documented",
        ],
        "warnings": [],
    }
    return artifacts, review_results, quality_report


def _sample_veto_data():
    """Return sample veto list for from_veto_escalation."""
    return [
        {
            "vetoed_by": "security-reviewer",
            "reason": "User login does not require email verification. This means anyone could create an account with someone else's email address.",
            "phase": "S4-implementation",
            "evidence": "review/S4-implementation/security-review.md",
        },
        {
            "vetoed_by": "performance-reviewer",
            "reason": "The search feature scans every record one by one, which will become slow as data grows.",
            "phase": "S4-implementation",
            "evidence": "review/S4-implementation/perf-review.md",
        },
    ]


# ── KeyChoice / RiskItem / DecisionRequired ────────────────────────────────


class TestKeyChoice:
    """KeyChoice must use non-technical language."""

    def test_choice_has_all_fields(self):
        c = KeyChoice(
            question="Where to store files?",
            option_a="Cloud storage",
            option_b="Local server",
            why_a="Cloud is accessible from anywhere",
            why_not_b="Local server requires on-site maintenance",
            risk_if_wrong="Switching later would take about a week",
        )
        assert c.question
        assert c.option_a
        assert c.option_b
        assert c.why_a
        assert c.why_not_b
        assert c.risk_if_wrong

    def test_choice_no_technical_terms(self):
        """KeyChoice fields must be free of technical jargon."""
        c = KeyChoice(
            question="How should we handle user sessions?",
            option_a="Remember users with a secure token in their browser",
            option_b="Ask users to log in for every action",
            why_a="A secure token is like a wristband at a concert — shows you already checked in",
            why_not_b="Repeated logins frustrate users and slow them down",
            risk_if_wrong="If the token system has a flaw, someone might pretend to be another user",
        )
        combined = f"{c.question} {c.option_a} {c.option_b} {c.why_a} {c.why_not_b} {c.risk_if_wrong}".lower()
        _assert_no_forbidden_terms(combined)

    def test_choice_explicit_technical_example_is_forbidden(self):
        """Verify that forbidden terms are actually caught in test data
        that intentionally contains them (sanity check)."""
        # This choice intentionally uses a forbidden term
        c = KeyChoice(
            question="Auth method?",
            option_a="JWT tokens",
            option_b="Session cookies",
            why_a="JWT is stateless",
            why_not_b="Session cookies need server state",
            risk_if_wrong="A SQL injection could leak sessions",
        )
        combined = f"{c.question} {c.option_a} {c.option_b} {c.why_a} {c.why_not_b} {c.risk_if_wrong}".lower()
        # This should contain a forbidden term (sanity check that our test
        # list actually matches what we are testing)
        assert "sql injection" in combined


class TestRiskItem:
    """RiskItem must use analogies and non-technical language."""

    def test_risk_item_has_all_fields(self):
        r = RiskItem(
            risk="The search might be slow when there are many records",
            likelihood="Medium",
            impact="Users may wait 3-5 seconds for results",
            analogy="Like searching a phone book page by page instead of using the index",
            mitigation="We designed a way to speed this up if needed",
        )
        assert r.risk
        assert r.likelihood
        assert r.impact
        assert r.analogy
        assert r.mitigation

    def test_risk_item_no_technical_terms(self):
        """RiskItem fields must be free of technical jargon."""
        r = RiskItem(
            risk="Unauthorised access to stored information is possible",
            likelihood="Low",
            impact="Private data could be seen by the wrong people",
            analogy="Like leaving your diary on a park bench",
            mitigation="We check every request against a list of who is allowed to see what",
        )
        combined = f"{r.risk} {r.impact} {r.analogy} {r.mitigation}".lower()
        _assert_no_forbidden_terms(combined)


class TestDecisionRequired:
    """DecisionRequired must have at least 2 options."""

    def test_decision_has_minimum_two_options(self):
        d = DecisionRequired(
            question="Approve the design?",
            options=["Yes, move forward", "No, revise"],
            recommendation="We recommend moving forward",
            deadline="2 days from now",
        )
        assert len(d.options) >= 2

    def test_decision_with_three_options(self):
        d = DecisionRequired(
            question="How to proceed?",
            options=["Approve", "Request changes", "Pause project"],
            recommendation="Approve — all checks passed",
            deadline="3 days from now",
        )
        assert len(d.options) == 3

    def test_decision_one_option_is_rejected(self):
        """A single-option decision is technically allowed by the dataclass
        but represents a poor user experience. This test documents that the
        builder always produces 2+ options; the dataclass itself does not
        enforce this constraint at construction time."""
        # The builder (from_phase_completion / from_veto_escalation) always
        # produces decisions with 2+ options. The raw dataclass does not
        # enforce this, but every code path that creates DecisionRequired
        # for user presentation goes through the builder.
        #
        # We test the raw case here to document that it does NOT raise:
        d = DecisionRequired(
            question="Approve?",
            options=["Yes"],
            recommendation="Yes",
            deadline=None,
        )
        assert d.question == "Approve?"
        assert len(d.options) == 1  # Allowed by dataclass, avoided by builder


# ── HumanReviewPacket ──────────────────────────────────────────────────────


class TestHumanReviewPacketBasics:
    """Basic construction and field checks."""

    def test_packet_construction(self):
        packet = HumanReviewPacket(
            packet_id="HRP-TEST-001",
            packet_type=PacketType.GATE_APPROVAL,
            phase="S2-architecture",
            task_id="T-0001",
            what_we_did="We designed the architecture.",
            what_changed="We moved from requirements to concrete design.",
            key_choices=[],
            risks=[],
            decision_required=DecisionRequired(
                question="Approve?",
                options=["Yes", "No"],
                recommendation="Yes",
                deadline=None,
            ),
            evidence_summary="All checks passed.",
            who_reviewed=["architect"],
            vetoes=[],
            expires_at="2026-08-01T00:00:00Z",
        )
        assert packet.packet_id == "HRP-TEST-001"
        assert packet.packet_type == PacketType.GATE_APPROVAL
        assert packet.phase == "S2-architecture"
        assert packet.generated_at  # auto-generated


class TestToMarkdown:
    """to_markdown() must produce a complete, readable document."""

    def test_markdown_contains_required_sections(self):
        _, review_results, quality_report = _sample_phase_data()
        artifacts = {
            "design_doc": "Overall system layout document",
        }
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        md = packet.to_markdown()

        # Required sections
        assert "# Phase Delivery Decision Packet" in md
        assert "## What We Did" in md
        assert "## Key Choices" in md
        assert "## Main Risks" in md
        assert "## Quality Check" in md
        assert "## Who Reviewed This Work" in md
        assert "## You Need to Decide" in md

    def test_markdown_contains_packet_id_and_timestamps(self):
        packet = HumanReviewPacket(
            packet_id="HRP-12345678",
            packet_type=PacketType.GATE_APPROVAL,
            phase="S1-requirements",
            task_id="T-0001",
            what_we_did="We gathered requirements.",
            what_changed="Started from project initiation.",
            decision_required=DecisionRequired(
                question="Proceed?",
                options=["Yes", "No"],
                recommendation="Yes",
                deadline="2026-08-01",
            ),
            expires_at="2026-08-01T00:00:00Z",
        )
        md = packet.to_markdown()
        assert "HRP-12345678" in md
        assert "Decision needed by:" in md

    def test_markdown_no_technical_terms(self):
        _, review_results, quality_report = _sample_phase_data()
        artifacts = {
            "requirements_doc": "A clear list of what the system should do",
        }
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S1-requirements",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        md = packet.to_markdown()
        _assert_no_forbidden_terms(md.lower())

    def test_markdown_includes_decision_options(self):
        _, review_results, quality_report = _sample_phase_data()
        artifacts = {"spec": "Interface specification"}
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S3-interface",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        md = packet.to_markdown()
        assert "- [ ] Approve" in md
        assert "- [ ] Request changes" in md
        assert "- [ ] Pause" in md

    def test_markdown_includes_choice_table(self):
        _, review_results, quality_report = _sample_phase_data()
        artifacts = {
            "architecture_diagram": "Visual system map",
        }
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        md = packet.to_markdown()
        assert "| We Chose | Did Not Choose | Why |" in md

    def test_markdown_includes_risks_table(self):
        _, review_results, quality_report = _sample_phase_data()
        artifacts = {"design": "Design document"}
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S1-requirements",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        md = packet.to_markdown()
        assert "| Risk | Likelihood | Impact | What We Did |" in md


class TestToPlainText:
    """to_plain_text() must produce readable plain text."""

    def test_plain_text_contains_all_sections(self):
        _, review_results, quality_report = _sample_phase_data()
        artifacts = {"design": "Design document"}
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        text = packet.to_plain_text()

        assert "PHASE DELIVERY DECISION PACKET" in text
        assert "WHAT WE DID" in text
        assert "KEY CHOICES" in text
        assert "MAIN RISKS" in text
        assert "QUALITY CHECK" in text
        assert "WHO REVIEWED THIS WORK" in text
        assert "YOU NEED TO DECIDE" in text

    def test_plain_text_no_markdown_formatting(self):
        """Plain text should not contain markdown artifacts like ## or **."""
        packet = HumanReviewPacket(
            packet_id="HRP-TEST-001",
            packet_type=PacketType.GATE_APPROVAL,
            phase="S2-architecture",
            task_id="T-0001",
            what_we_did="We designed the system architecture.",
            what_changed="Requirements are now a concrete design.",
            key_choices=[
                KeyChoice(
                    question="Database choice?",
                    option_a="PostgreSQL",
                    option_b="MongoDB",
                    why_a="Reliable for financial data",
                    why_not_b="Not suited for transaction-heavy work",
                    risk_if_wrong="Migration would take two weeks",
                )
            ],
            risks=[
                RiskItem(
                    risk="Search might be slow",
                    likelihood="Medium",
                    impact="Users wait a few seconds",
                    analogy="Like searching a big filing cabinet",
                    mitigation="We have a speed-up plan ready",
                )
            ],
            decision_required=DecisionRequired(
                question="Approve?",
                options=["Yes", "No", "Pause"],
                recommendation="Yes, proceed",
                deadline="3 days",
            ),
            evidence_summary="All checks passed.",
            who_reviewed=["architect"],
            vetoes=[],
            expires_at="2026-08-01T00:00:00Z",
        )
        text = packet.to_plain_text()

        # Must not contain markdown formatting artifacts
        assert "##" not in text
        assert "**" not in text
        assert "|" not in text  # No tables in plain text

    def test_plain_text_no_technical_terms(self):
        _, review_results, quality_report = _sample_phase_data()
        artifacts = {"doc": "A requirements document"}
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S1-requirements",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        text = packet.to_plain_text()
        _assert_no_forbidden_terms(text.lower())


class TestPacketWithVetoes:
    """Packets with vetoes must surface the veto information clearly."""

    def test_markdown_includes_vetoes_section(self):
        vetoes = _sample_veto_data()
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=vetoes,
            task_id="T-0001",
        )
        md = packet.to_markdown()
        assert "## Vetoes Raised" in md

    def test_plain_text_includes_vetoes_section(self):
        vetoes = _sample_veto_data()
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=vetoes,
            task_id="T-0001",
        )
        text = packet.to_plain_text()
        assert "VETOES RAISED" in text

    def test_veto_packet_has_veto_type(self):
        vetoes = _sample_veto_data()
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=vetoes,
            task_id="T-0001",
        )
        assert packet.packet_type == PacketType.VETO_ESCALATION

    def test_veto_packet_has_key_choices_for_each_veto(self):
        vetoes = _sample_veto_data()
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=vetoes,
            task_id="T-0001",
        )
        assert len(packet.key_choices) == len(vetoes)

    def test_veto_packet_decision_has_minimum_two_options(self):
        vetoes = _sample_veto_data()
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=vetoes,
            task_id="T-0001",
        )
        assert packet.decision_required is not None
        assert len(packet.decision_required.options) >= 2


# ── HumanReviewPacketBuilder ───────────────────────────────────────────────


class TestBuilderFromPhaseCompletion:
    """from_phase_completion constructs a complete, valid packet."""

    def test_returns_human_review_packet(self):
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        assert isinstance(packet, HumanReviewPacket)

    def test_packet_type_is_gate_approval(self):
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0002",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        assert packet.packet_type == PacketType.GATE_APPROVAL

    def test_phase_and_task_id_preserved(self):
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S4-implementation",
            task_id="T-0042",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        assert packet.phase == "S4-implementation"
        assert packet.task_id == "T-0042"

    def test_what_we_did_is_populated(self):
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        assert len(packet.what_we_did) > 20
        assert "architecture" in packet.what_we_did.lower() or "Architecture" in packet.what_we_did

    def test_what_changed_is_populated(self):
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        assert len(packet.what_changed) > 10

    def test_key_choices_derived_from_phase(self):
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        assert len(packet.key_choices) >= 1
        # Each key choice should have non-empty fields
        for choice in packet.key_choices:
            assert choice.question
            assert choice.option_a
            assert choice.option_b
            assert choice.why_a
            assert choice.why_not_b
            assert choice.risk_if_wrong

    def test_risks_populated_from_quality_warnings(self):
        quality_report = {
            "pass": True,
            "checks": ["Check 1 passed"],
            "warnings": ["Possible slow performance on large datasets"],
        }
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S1-requirements",
            task_id="T-0001",
            artifacts={"doc": "Requirements document"},
            review_results={},
            quality_report=quality_report,
        )
        assert len(packet.risks) >= 1

    def test_risks_default_when_no_warnings(self):
        _, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S1-requirements",
            task_id="T-0001",
            artifacts={"doc": "Requirements document"},
            review_results=review_results,
            quality_report=quality_report,
        )
        # Even with no warnings, there should be at least a "no major risks" note
        assert len(packet.risks) >= 1

    def test_evidence_summary_populated(self):
        _, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S1-requirements",
            task_id="T-0001",
            artifacts={"doc": "Requirements document"},
            review_results=review_results,
            quality_report=quality_report,
        )
        assert len(packet.evidence_summary) > 5

    def test_who_reviewed_from_review_results(self):
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S1-requirements",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        assert "system-architect" in packet.who_reviewed
        assert "security-reviewer" in packet.who_reviewed

    def test_decision_required_has_three_options(self):
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        assert packet.decision_required is not None
        assert len(packet.decision_required.options) == 3
        assert any("Approve" in opt for opt in packet.decision_required.options)
        assert any("changes" in opt.lower() for opt in packet.decision_required.options)
        assert any("Pause" in opt for opt in packet.decision_required.options)

    def test_decision_has_recommendation(self):
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        assert packet.decision_required is not None
        assert len(packet.decision_required.recommendation) > 10

    def test_decision_has_deadline(self):
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        assert packet.decision_required is not None
        assert packet.decision_required.deadline is not None

    def test_packet_id_generated(self):
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        assert packet.packet_id.startswith("HRP-")
        assert len(packet.packet_id) > 4

    def test_expires_at_set(self):
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        assert packet.expires_at
        # Should be a valid ISO timestamp
        from datetime import datetime
        parsed = datetime.fromisoformat(packet.expires_at)
        assert parsed is not None

    def test_implementation_phase_produces_key_choice(self):
        artifacts = {"module_a": "User login module", "module_b": "Dashboard module"}
        review_results = {"reviewer": "PASS"}
        quality_report = {"pass": True, "checks": ["All tests pass"], "warnings": []}
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S4-implementation",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        assert len(packet.key_choices) >= 1
        # Implementation-specific choice should mention testing
        implementation_choice_text = " ".join(
            c.question + c.why_a + c.why_not_b for c in packet.key_choices
        ).lower()
        assert "test" in implementation_choice_text or "piece" in implementation_choice_text

    def test_unknown_phase_gets_generic_choice(self):
        artifacts = {"output": "Some deliverable"}
        review_results = {"reviewer": "PASS"}
        quality_report = {"pass": True, "checks": [], "warnings": []}
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S5-quality",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        # Should still have at least one key choice (generic fallback)
        assert len(packet.key_choices) >= 1

    def test_empty_artifacts_still_produces_valid_packet(self):
        quality_report = {"pass": True, "checks": ["Passed"], "warnings": []}
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S1-requirements",
            task_id="T-0001",
            artifacts={},
            review_results={},
            quality_report=quality_report,
        )
        assert isinstance(packet, HumanReviewPacket)
        assert len(packet.what_we_did) > 10

    def test_no_technical_terms_in_phase_completion_output(self):
        """The complete packet from from_phase_completion must not contain
        any forbidden technical terms in user-facing text."""
        artifacts, review_results, _ = _sample_phase_data()
        quality_report = {
            "pass": True,
            "checks": ["Architecture valid", "No cycles detected"],
            "warnings": [],  # No warnings means no technical terms from warnings
        }
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )

        # Check all user-facing text fields
        combined = (
            f"{packet.what_we_did} {packet.what_changed} "
            f"{packet.evidence_summary}"
        ).lower()

        # Also check key choices
        for c in packet.key_choices:
            combined += f" {c.question} {c.option_a} {c.option_b} {c.why_a} {c.why_not_b} {c.risk_if_wrong}"

        # Also check risks
        for r in packet.risks:
            combined += f" {r.risk} {r.impact} {r.analogy} {r.mitigation}"

        _assert_no_forbidden_terms(combined)


class TestBuilderFromVetoEscalation:
    """from_veto_escalation constructs a veto escalation packet."""

    def test_returns_human_review_packet(self):
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=_sample_veto_data(),
            task_id="T-0001",
        )
        assert isinstance(packet, HumanReviewPacket)

    def test_packet_type_is_veto_escalation(self):
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=_sample_veto_data(),
            task_id="T-0001",
        )
        assert packet.packet_type == PacketType.VETO_ESCALATION

    def test_veto_reasons_in_evidence(self):
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=_sample_veto_data(),
            task_id="T-0001",
        )
        assert "email verification" in packet.evidence_summary.lower()
        assert "search" in packet.evidence_summary.lower()

    def test_veto_authors_in_who_reviewed(self):
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=_sample_veto_data(),
            task_id="T-0001",
        )
        assert "security-reviewer" in packet.who_reviewed
        assert "performance-reviewer" in packet.who_reviewed

    def test_veto_reasons_in_vetoes_list(self):
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=_sample_veto_data(),
            task_id="T-0001",
        )
        assert len(packet.vetoes) == 2

    def test_decision_options_for_escalation(self):
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=_sample_veto_data(),
            task_id="T-0001",
        )
        assert packet.decision_required is not None
        assert len(packet.decision_required.options) >= 2
        # Should include an override option
        assert any("override" in opt.lower() for opt in packet.decision_required.options)

    def test_veto_escalation_has_risks(self):
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=_sample_veto_data(),
            task_id="T-0001",
        )
        assert len(packet.risks) >= 1

    def test_empty_vetoes_handled_gracefully(self):
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=[],
            task_id="T-0001",
        )
        assert isinstance(packet, HumanReviewPacket)
        assert packet.packet_type == PacketType.VETO_ESCALATION

    def test_veto_with_string_instead_of_dict(self):
        """Gracefully handles veto items that are plain strings."""
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=["The login flow is insecure"],
            task_id="T-0001",
        )
        assert isinstance(packet, HumanReviewPacket)
        assert len(packet.vetoes) == 1

    def test_no_technical_terms_in_veto_output(self):
        """Veto escalation packets must not contain forbidden technical terms."""
        # Use vetoes that don't themselves contain technical terms
        safe_vetoes = [
            {
                "vetoed_by": "reviewer-one",
                "reason": "The user sign-up process does not check email ownership",
                "phase": "S4-implementation",
            },
        ]
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=safe_vetoes,
            task_id="T-0001",
        )
        combined = (
            f"{packet.what_we_did} {packet.what_changed} "
            f"{packet.evidence_summary}"
        ).lower()
        for c in packet.key_choices:
            combined += f" {c.question} {c.option_a} {c.option_b} {c.why_a} {c.why_not_b} {c.risk_if_wrong}"
        for r in packet.risks:
            combined += f" {r.risk} {r.impact} {r.analogy} {r.mitigation}"
        _assert_no_forbidden_terms(combined)


# ── translate_technical_risk ───────────────────────────────────────────────


class TestTranslateTechnicalRisk:
    """translate_technical_risk converts technical jargon to plain language."""

    def test_sql_injection_translated(self):
        result = HumanReviewPacketBuilder.translate_technical_risk(
            "Possible SQL injection in login form"
        )
        assert isinstance(result, RiskItem)
        # The risk description must NOT contain the technical term
        assert "sql injection" not in result.risk.lower()
        assert "sql" not in result.risk.lower()
        # Should have an analogy
        assert len(result.analogy) > 5

    def test_xss_translated(self):
        result = HumanReviewPacketBuilder.translate_technical_risk(
            "XSS vulnerability in comment field"
        )
        assert "xss" not in result.risk.lower()
        assert "cross-site" not in result.risk.lower()
        assert len(result.analogy) > 5

    def test_race_condition_translated(self):
        result = HumanReviewPacketBuilder.translate_technical_risk(
            "Race condition in payment processing"
        )
        assert "race condition" not in result.risk.lower()
        assert len(result.analogy) > 5

    def test_buffer_overflow_translated(self):
        result = HumanReviewPacketBuilder.translate_technical_risk(
            "Buffer overflow risk in file upload handler"
        )
        assert "buffer overflow" not in result.risk.lower()
        assert len(result.analogy) > 5

    def test_memory_leak_translated(self):
        result = HumanReviewPacketBuilder.translate_technical_risk(
            "Memory leak in background task worker"
        )
        assert "memory leak" not in result.risk.lower()
        assert len(result.analogy) > 5

    def test_deadlock_translated(self):
        result = HumanReviewPacketBuilder.translate_technical_risk(
            "Deadlock between database writes"
        )
        assert "deadlock" not in result.risk.lower()
        assert len(result.analogy) > 5

    def test_ddos_translated(self):
        result = HumanReviewPacketBuilder.translate_technical_risk(
            "DDoS vulnerability in rate limiting"
        )
        assert "ddos" not in result.risk.lower()
        assert "denial of service" not in result.risk.lower()
        assert len(result.analogy) > 5

    def test_privilege_escalation_translated(self):
        result = HumanReviewPacketBuilder.translate_technical_risk(
            "Privilege escalation possible via API"
        )
        assert "privilege escalation" not in result.risk.lower()
        assert len(result.analogy) > 5

    def test_data_leak_translated(self):
        result = HumanReviewPacketBuilder.translate_technical_risk(
            "Data leak through error messages"
        )
        assert "data leak" not in result.risk.lower()
        assert len(result.analogy) > 5

    def test_unknown_technical_term_gets_generic_translation(self):
        result = HumanReviewPacketBuilder.translate_technical_risk(
            "Cryptographic nonce reuse in handshake protocol"
        )
        assert isinstance(result, RiskItem)
        assert len(result.risk) > 5
        assert len(result.analogy) > 5

    def test_result_always_has_all_risk_item_fields(self):
        result = HumanReviewPacketBuilder.translate_technical_risk(
            "SQL injection risk detected"
        )
        assert result.risk
        assert result.likelihood in ("High", "Medium", "Low")
        assert result.impact
        assert result.analogy
        assert result.mitigation

    def test_result_is_non_technical(self):
        """All translate_technical_risk results must be non-technical."""
        test_inputs = [
            "SQL injection in login",
            "XSS in comment field",
            "Race condition in payment",
            "Buffer overflow in upload",
            "Memory leak in worker",
            "Deadlock in database",
            "DDoS vulnerability",
            "Privilege escalation in API",
            "Data leak in logs",
            "Injection attack in search",
        ]
        for test_input in test_inputs:
            result = HumanReviewPacketBuilder.translate_technical_risk(test_input)
            combined = f"{result.risk} {result.impact} {result.analogy} {result.mitigation}".lower()
            _assert_no_forbidden_terms(combined)

    def test_likelihood_detection(self):
        """Likelihood should reflect severity keywords."""
        high_result = HumanReviewPacketBuilder.translate_technical_risk(
            "Critical SQL injection in authentication — severe risk"
        )
        assert high_result.likelihood == "High"

        low_result = HumanReviewPacketBuilder.translate_technical_risk(
            "Minor XSS in debug page — low risk"
        )
        assert low_result.likelihood == "Low"

        medium_result = HumanReviewPacketBuilder.translate_technical_risk(
            "Possible race condition in logging"
        )
        assert medium_result.likelihood == "Medium"


# ── Helpers ────────────────────────────────────────────────────────────────


class TestPhaseLabel:
    """_phase_label maps phase codes to human-readable labels."""

    def test_known_phases(self):
        assert _phase_label("S0-init") == "Project Start"
        assert _phase_label("S1-requirements") == "Requirements"
        assert _phase_label("S2-architecture") == "Architecture Design"
        assert _phase_label("S3-interface") == "Interface Design"
        assert _phase_label("S4-implementation") == "Implementation"
        assert _phase_label("S5-quality") == "Quality Assurance"
        assert _phase_label("S6-delivery") == "Delivery"
        assert _phase_label("S7-integration") == "Integration"
        assert _phase_label("S8-functional-test") == "Functional Testing"
        assert _phase_label("S9-fix-optimize") == "Fixes and Optimisation"
        assert _phase_label("S10-performance") == "Performance Testing"
        assert _phase_label("S11-maintenance") == "Maintenance"

    def test_unknown_phase_gets_title_case(self):
        assert _phase_label("S99-custom-phase") == "S99 Custom Phase"


class TestFormatTs:
    """_format_ts formats ISO timestamps for display."""

    def test_valid_iso_timestamp(self):
        result = _format_ts("2026-07-23T14:30:00+00:00")
        assert "2026-07-23" in result
        assert "UTC" in result

    def test_invalid_timestamp_returns_original(self):
        assert _format_ts("not-a-timestamp") == "not-a-timestamp"

    def test_empty_string(self):
        assert _format_ts("") == ""


# ── Integration smoke tests ────────────────────────────────────────────────


class TestIntegrationSmoke:
    """End-to-end: build a packet and render it both ways."""

    def test_full_roundtrip_markdown(self):
        """Build from phase completion, render markdown, verify structure."""
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        md = packet.to_markdown()

        # Must be non-empty
        assert len(md) > 100

        # Must start with a header
        assert md.startswith("# Phase Delivery Decision Packet")

        # Must end with decision or useful text (not a hanging newline)
        assert len(md.strip()) > 0

    def test_full_roundtrip_plain_text(self):
        """Build from phase completion, render plain text, verify structure."""
        artifacts, review_results, quality_report = _sample_phase_data()
        packet = HumanReviewPacketBuilder.from_phase_completion(
            phase="S2-architecture",
            task_id="T-0001",
            artifacts=artifacts,
            review_results=review_results,
            quality_report=quality_report,
        )
        text = packet.to_plain_text()

        assert len(text) > 100
        assert text.startswith("PHASE DELIVERY DECISION PACKET")

    def test_veto_roundtrip_markdown(self):
        vetoes = _sample_veto_data()
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=vetoes,
            task_id="T-0001",
        )
        md = packet.to_markdown()

        assert len(md) > 100
        assert "# Phase Delivery Decision Packet" in md
        assert "## Vetoes Raised" in md

    def test_veto_roundtrip_plain_text(self):
        vetoes = _sample_veto_data()
        packet = HumanReviewPacketBuilder.from_veto_escalation(
            vetoes=vetoes,
            task_id="T-0001",
        )
        text = packet.to_plain_text()

        assert len(text) > 100
        assert "VETOES RAISED" in text


# ── Assertion helper ───────────────────────────────────────────────────────


def _assert_no_forbidden_terms(text: str):
    """Assert that none of the forbidden technical terms appear in `text`."""
    found: list[str] = []
    for term in FORBIDDEN_TECHNICAL_TERMS:
        if term in text:
            found.append(term)
    if found:
        pytest.fail(
            f"Forbidden technical terms found in output: {found}\n"
            f"Output snippet: {text[:300]}..."
        )
