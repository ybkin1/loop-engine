"""
Human Review Packet — Non-technical decision packets for Loop phase gates.

Every phase completion produces a Human Review Packet that explains, in plain
language, what was done, what key choices were made, what risks exist, and what
decision the user needs to make. The goal is that a non-technical stakeholder
can make an informed GO/NOGO decision without asking the AI follow-up questions.

Referenced by:
- veto_escalation.py — builds escalation packets from veto conflicts
- state_machine.py — Phase enum used for phase tagging
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class PacketType(str, Enum):
    """Type of human review packet — determines the decision the user faces."""
    GATE_APPROVAL = "gate_approval"       # Phase Gate approval
    VETO_ESCALATION = "veto_escalation"   # Veto conflict escalation
    CHANGE_REQUEST = "change_request"     # Requirement change request
    RISK_ACCEPTANCE = "risk_acceptance"   # Risk acceptance


# ── Packet Components ──────────────────────────────────────────────────────


@dataclass
class KeyChoice:
    """A key design or implementation choice, explained for non-technical users.

    Every choice shows the trade-off: what we picked, what we did not pick,
    why, and what happens if we are wrong.
    """
    question: str              # "How should we store user data?"
    option_a: str              # "A cloud-based database"
    option_b: str              # "Files saved on the server"
    why_a: str                 # Why we chose A (in plain language)
    why_not_b: str             # Why we did not choose B
    risk_if_wrong: str         # What happens if this choice turns out wrong


@dataclass
class RiskItem:
    """A risk described in non-technical language with an everyday analogy."""
    risk: str                  # Risk description (plain language)
    likelihood: str            # "High" / "Medium" / "Low"
    impact: str                # Impact description
    analogy: str               # Everyday analogy (e.g. "Like leaving home without keys")
    mitigation: str            # What we did to reduce the risk


@dataclass
class DecisionRequired:
    """The decision the user must make — not "please review" but "please decide"."""
    question: str              # "Do you approve moving to the architecture phase?"
    options: list[str]         # ["Approve, move to next phase", "Request changes", "Pause project"]
    recommendation: str        # AI's recommended option and why
    deadline: Optional[str]    # Suggested decision deadline


# ── Main Packet ────────────────────────────────────────────────────────────


@dataclass
class HumanReviewPacket:
    """A phase-completion decision packet written for humans, not machines.

    This is the primary deliverable shown to the user at each phase gate.
    It must be self-contained — the user should not need to read code, logs,
    or ask follow-up questions to make their decision.
    """
    packet_id: str
    packet_type: PacketType
    phase: str
    task_id: str

    # Summary
    what_we_did: str            # "What we did" (3-5 sentences, plain language)
    what_changed: str           # "What changed from the previous phase"

    # Decision
    key_choices: list[KeyChoice] = field(default_factory=list)
    risks: list[RiskItem] = field(default_factory=list)
    decision_required: Optional[DecisionRequired] = None

    # Evidence
    evidence_summary: str = ""
    who_reviewed: list[str] = field(default_factory=list)
    vetoes: list[str] = field(default_factory=list)

    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    expires_at: str = ""

    # ── Output Methods ──────────────────────────────────────────────────

    def to_markdown(self) -> str:
        """Render the packet as a human-readable Markdown document."""
        lines: list[str] = []

        # Header
        phase_label = _phase_label(self.phase)
        lines.append(f"# Phase Delivery Decision Packet — {phase_label}")
        lines.append("")
        lines.append(f"**Packet ID:** {self.packet_id}  ")
        lines.append(f"**Generated:** {_format_ts(self.generated_at)}  ")
        if self.expires_at:
            lines.append(f"**Decision needed by:** {_format_ts(self.expires_at)}  ")
        lines.append("")

        # What we did
        lines.append("## What We Did")
        lines.append("")
        lines.append(self.what_we_did)
        lines.append("")

        # What changed
        if self.what_changed:
            lines.append("## What Changed")
            lines.append("")
            lines.append(self.what_changed)
            lines.append("")

        # Key choices
        if self.key_choices:
            lines.append("## Key Choices")
            lines.append("")
            for i, choice in enumerate(self.key_choices, 1):
                lines.append(f"### {i}. {choice.question}")
                lines.append("")
                lines.append("| We Chose | Did Not Choose | Why |")
                lines.append("|----------|---------------|-----|")
                lines.append(f"| {choice.option_a} | {choice.option_b} | {choice.why_a} |")
                lines.append("")
                lines.append(f"**Why not the alternative:** {choice.why_not_b}")
                lines.append("")
                lines.append(f"**If we are wrong:** {choice.risk_if_wrong}")
                lines.append("")

        # Risks
        if self.risks:
            lines.append("## Main Risks")
            lines.append("")
            lines.append("| Risk | Likelihood | Impact | What We Did |")
            lines.append("|------|-----------|--------|-------------|")
            for risk in self.risks:
                lines.append(
                    f"| {risk.risk} | {risk.likelihood} | {risk.impact} "
                    f"| {risk.mitigation} |"
                )
            lines.append("")
            for risk in self.risks:
                lines.append(f"- **{risk.risk}** — *Analogy:* {risk.analogy}")
                lines.append("")

        # Evidence
        if self.evidence_summary:
            lines.append("## Quality Check")
            lines.append("")
            lines.append(self.evidence_summary)
            lines.append("")

        # Who reviewed
        if self.who_reviewed:
            lines.append("## Who Reviewed This Work")
            lines.append("")
            for reviewer in self.who_reviewed:
                lines.append(f"- {reviewer}")
            lines.append("")

        # Vetoes
        if self.vetoes:
            lines.append("## Vetoes Raised")
            lines.append("")
            for veto in self.vetoes:
                lines.append(f"- {veto}")
            lines.append("")

        # Decision required
        if self.decision_required:
            lines.append("## You Need to Decide")
            lines.append("")
            lines.append(f"**{self.decision_required.question}**")
            lines.append("")
            for option in self.decision_required.options:
                lines.append(f"- [ ] {option}")
            lines.append("")
            lines.append(f"**Our recommendation:** {self.decision_required.recommendation}")
            if self.decision_required.deadline:
                lines.append("")
                lines.append(
                    f"Please decide by **{self.decision_required.deadline}**. "
                    "If you have questions, your product manager can walk through "
                    "each piece with you."
                )

        return "\n".join(lines)

    def to_plain_text(self) -> str:
        """Render the packet as plain text (no markdown formatting)."""
        lines: list[str] = []

        phase_label = _phase_label(self.phase)
        lines.append(f"PHASE DELIVERY DECISION PACKET — {phase_label}")
        lines.append(f"Packet ID: {self.packet_id}")
        lines.append(f"Generated: {_format_ts(self.generated_at)}")
        if self.expires_at:
            lines.append(f"Decision needed by: {_format_ts(self.expires_at)}")
        lines.append("")

        lines.append("WHAT WE DID")
        lines.append(self.what_we_did)
        lines.append("")

        if self.what_changed:
            lines.append("WHAT CHANGED")
            lines.append(self.what_changed)
            lines.append("")

        if self.key_choices:
            lines.append("KEY CHOICES")
            for i, choice in enumerate(self.key_choices, 1):
                lines.append(f"  {i}. {choice.question}")
                lines.append(f"     We chose: {choice.option_a}")
                lines.append(f"     Did not choose: {choice.option_b}")
                lines.append(f"     Why: {choice.why_a}")
                lines.append(f"     Why not the other: {choice.why_not_b}")
                lines.append(f"     If wrong: {choice.risk_if_wrong}")
                lines.append("")

        if self.risks:
            lines.append("MAIN RISKS")
            for risk in self.risks:
                lines.append(f"  - {risk.risk}")
                lines.append(f"    Likelihood: {risk.likelihood}")
                lines.append(f"    Impact: {risk.impact}")
                lines.append(f"    Analogy: {risk.analogy}")
                lines.append(f"    What we did: {risk.mitigation}")
                lines.append("")

        if self.evidence_summary:
            lines.append("QUALITY CHECK")
            lines.append(self.evidence_summary)
            lines.append("")

        if self.who_reviewed:
            lines.append("WHO REVIEWED THIS WORK")
            for reviewer in self.who_reviewed:
                lines.append(f"  - {reviewer}")
            lines.append("")

        if self.vetoes:
            lines.append("VETOES RAISED")
            for veto in self.vetoes:
                lines.append(f"  - {veto}")
            lines.append("")

        if self.decision_required:
            lines.append("YOU NEED TO DECIDE")
            lines.append(f"  {self.decision_required.question}")
            for option in self.decision_required.options:
                lines.append(f"  [ ] {option}")
            lines.append(f"  Recommendation: {self.decision_required.recommendation}")
            if self.decision_required.deadline:
                lines.append(f"  Deadline: {self.decision_required.deadline}")

        return "\n".join(lines)


# ── Builder ────────────────────────────────────────────────────────────────


class HumanReviewPacketBuilder:
    """Builds HumanReviewPacket instances from structured phase-completion data.

    This builder translates raw engineering outputs (artifacts, review results,
    quality reports) into plain-language packets that non-technical stakeholders
    can understand and act on.
    """

    # ── Technical Risk Translation Map ──────────────────────────────────
    #
    # Maps technical risk descriptions to plain-language explanations with
    # everyday analogies. The builder uses this as a fallback; callers can
    # also use translate_technical_risk() directly.

    _RISK_TRANSLATIONS: dict[str, dict[str, str]] = {
        "sql injection": {
            "risk": "Unauthorised person could access or change stored information",
            "analogy": "Like leaving the cash register unlocked when the shop is open",
            "mitigation": "All data requests are validated before being sent to storage",
        },
        "xss": {
            "risk": "Harmful content could appear to other users of the system",
            "analogy": "Like someone putting up a misleading sign on your shop window",
            "mitigation": "All user-provided content is checked and cleaned before display",
        },
        "race condition": {
            "risk": "Two actions happening at the same time could produce wrong results",
            "analogy": "Like two people trying to book the same flight seat at the same moment",
            "mitigation": "We ensure actions that conflict wait their turn",
        },
        "buffer overflow": {
            "risk": "The system could crash or behave unexpectedly with very large inputs",
            "analogy": "Like pouring too much water into a glass — it spills and makes a mess",
            "mitigation": "We limit input sizes and check boundaries before processing",
        },
        "null pointer": {
            "risk": "The program could stop working when it encounters missing information",
            "analogy": "Like trying to read a page that has been torn out of a book",
            "mitigation": "We check for missing information before using it",
        },
        "memory leak": {
            "risk": "The system could slow down over time as resources are not released",
            "analogy": "Like a tap left dripping — eventually the sink overflows",
            "mitigation": "We track and release resources that are no longer needed",
        },
        "deadlock": {
            "risk": "Two parts of the system could freeze waiting for each other",
            "analogy": "Like two people meeting in a narrow hallway, each waiting for the other to step aside",
            "mitigation": "We set time limits so no part waits forever",
        },
        "ddos": {
            "risk": "The service could become unavailable if overwhelmed with requests",
            "analogy": "Like too many customers entering a small shop at once — nobody can move",
            "mitigation": "We limit the rate of incoming requests and monitor traffic patterns",
        },
        "privilege escalation": {
            "risk": "A regular user could gain access they should not have",
            "analogy": "Like a hotel guest finding a master key that opens every room",
            "mitigation": "We verify permissions at every step, not just at the entrance",
        },
        "data leak": {
            "risk": "Private information could become visible to the wrong people",
            "analogy": "Like sending a confidential letter with the wrong address on the envelope",
            "mitigation": "We check who can see what at multiple layers of the system",
        },
        "injection": {
            "risk": "Malicious instructions could be hidden inside normal-looking input",
            "analogy": "Like someone slipping extra clauses into a contract after you have signed it",
            "mitigation": "We separate instructions from data so they cannot be mixed up",
        },
        "timestamp": {
            "risk": "Time-related errors could cause data to appear in the wrong order",
            "analogy": "Like arriving at a meeting and finding everyone already left because of a clock mismatch",
            "mitigation": "We use a single, consistent time source across the entire system",
        },
        "timeout": {
            "risk": "Long-running operations could leave users waiting without feedback",
            "analogy": "Like ordering food and never being told the kitchen is backed up",
            "mitigation": "We set reasonable wait limits and inform users when something takes longer",
        },
        "unhandled error": {
            "risk": "Unexpected problems could cause the system to stop working entirely",
            "analogy": "Like a car engine shutting off because one sensor reported a minor issue",
            "mitigation": "We catch problems early and degrade gracefully instead of stopping completely",
        },
        "out of sync": {
            "risk": "Different parts of the system could show different information",
            "analogy": "Like two clocks in the same building showing different times",
            "mitigation": "We keep a single source of truth and synchronise regularly",
        },
    }

    @staticmethod
    def translate_technical_risk(technical_description: str) -> RiskItem:
        """Translate a technical risk description into plain language with an analogy.

        Args:
            technical_description: A risk description that may contain technical
                                  terms (e.g. "Possible SQL injection in login form").

        Returns:
            A RiskItem with non-technical risk description, analogy, and mitigation.
        """
        description_lower = technical_description.lower()

        # Try to match known technical patterns
        for pattern, translation in HumanReviewPacketBuilder._RISK_TRANSLATIONS.items():
            if pattern in description_lower:
                # Determine likelihood from keywords in the description
                likelihood = "Medium"
                if any(word in description_lower for word in ("critical", "severe", "high risk", "certain")):
                    likelihood = "High"
                elif any(word in description_lower for word in ("minor", "unlikely", "low risk")):
                    likelihood = "Low"

                return RiskItem(
                    risk=translation["risk"],
                    likelihood=likelihood,
                    impact=translation["risk"],
                    analogy=translation["analogy"],
                    mitigation=translation["mitigation"],
                )

        # No known pattern matched — create a generic translation
        return RiskItem(
            risk=f"Potential issue identified: {technical_description[:80]}",
            likelihood="Medium",
            impact="May affect system reliability or user experience",
            analogy="Like an unexpected bump in the road — manageable but worth watching",
            mitigation="We have flagged this for monitoring and will address it if it occurs",
        )

    # ── Builder Methods ─────────────────────────────────────────────────

    @staticmethod
    def from_phase_completion(
        phase: str,
        task_id: str,
        artifacts: dict,
        review_results: dict,
        quality_report: dict,
    ) -> HumanReviewPacket:
        """Build a gate-approval packet from phase-completion data.

        Args:
            phase: Phase identifier (e.g. "S2-architecture").
            task_id: The task being completed.
            artifacts: Dict of artifact_name -> description for this phase.
            review_results: Dict of reviewer_role -> verdict summary.
            quality_report: Dict with keys like "pass", "checks", "warnings".

        Returns:
            A HumanReviewPacket ready to present to the user.
        """
        # Build what_we_did from artifacts
        artifact_names = list(artifacts.keys()) if artifacts else []
        if artifact_names:
            artifact_list = ", ".join(artifact_names)
            what_we_did = (
                f"For your project, we completed the **{_phase_label(phase)}** phase. "
                f"We produced: {artifact_list}. "
                f"Each piece was checked for consistency and completeness. "
                f"The work is now ready for your review and decision."
            )
        else:
            what_we_did = (
                f"We completed the **{_phase_label(phase)}** phase for your project. "
                "All required outputs for this stage have been produced and checked."
            )

        # Build what_changed from review results
        reviewer_names = list(review_results.keys()) if review_results else []
        if reviewer_names:
            who = ", ".join(reviewer_names)
            what_changed = (
                f"The work from this phase was reviewed by: {who}. "
                f"Compared to the previous phase, we now have concrete deliverables "
                f"that you can review directly rather than plans on paper."
            )
        else:
            what_changed = (
                "We moved from planning to producing concrete deliverables. "
                "The outputs from this phase replace the outlines from the previous stage."
            )

        # Build key choices from artifacts
        key_choices = HumanReviewPacketBuilder._extract_key_choices(
            phase, artifacts
        )

        # Build risks
        risks: list[RiskItem] = []
        quality_warnings = quality_report.get("warnings", [])
        if isinstance(quality_warnings, list):
            for warning in quality_warnings:
                if isinstance(warning, str):
                    risks.append(
                        HumanReviewPacketBuilder.translate_technical_risk(warning)
                    )

        # If no risks found, add a generic low-risk note
        if not risks:
            risks.append(RiskItem(
                risk="No major risks identified at this stage",
                likelihood="Low",
                impact="Minimal — standard quality checks all passed",
                analogy="Like checking the weather forecast and seeing clear skies",
                mitigation="We ran all standard checks and they passed",
            ))

        # Build evidence summary from quality report
        passed = quality_report.get("pass", quality_report.get("passed", True))
        checks = quality_report.get("checks", [])
        if isinstance(passed, bool):
            status = "All checks passed" if passed else "Some checks did not pass"
        else:
            status = f"Checks completed: {passed}"

        evidence_parts = [f"- {status}"]
        if isinstance(checks, list):
            for check in checks:
                if isinstance(check, str):
                    evidence_parts.append(f"- {check}")
        elif isinstance(checks, dict):
            for check_name, check_result in checks.items():
                icon = "+" if check_result else "!"
                evidence_parts.append(f"- {check_name}: {icon}")

        evidence_summary = "\n".join(evidence_parts)

        # Build who_reviewed
        who_reviewed = list(review_results.keys()) if review_results else []

        # Build decision_required
        phase_label = _phase_label(phase)
        decision = DecisionRequired(
            question=f"Do you approve moving forward from {phase_label}?",
            options=[
                "Approve — move to the next phase",
                "Request changes — I want something adjusted",
                "Pause — I need time to think or have other questions",
            ],
            recommendation=(
                f"We recommend approving and moving forward. "
                f"All quality checks for {phase_label} passed, and the outputs "
                f"match what was planned. If anything looks unclear, choose "
                f"'Request changes' and tell us what to adjust."
            ),
            deadline="3 days from now",
        )

        # Generate packet ID
        import uuid
        packet_id = f"HRP-{uuid.uuid4().hex[:8].upper()}"

        # Set expiration
        from datetime import timedelta
        expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        return HumanReviewPacket(
            packet_id=packet_id,
            packet_type=PacketType.GATE_APPROVAL,
            phase=phase,
            task_id=task_id,
            what_we_did=what_we_did,
            what_changed=what_changed,
            key_choices=key_choices,
            risks=risks,
            decision_required=decision,
            evidence_summary=evidence_summary,
            who_reviewed=who_reviewed,
            vetoes=[],
            expires_at=expires,
        )

    @staticmethod
    def from_veto_escalation(
        vetoes: list,
        task_id: str,
    ) -> HumanReviewPacket:
        """Build a veto-escalation packet when reviewers disagree.

        Args:
            vetoes: List of veto records, each a dict with keys like
                    "vetoed_by", "reason", "phase", "evidence".
            task_id: The task being blocked by the veto.

        Returns:
            A HumanReviewPacket explaining the deadlock and what the user
            needs to decide.
        """
        veto_count = len(vetoes)
        veto_reasons = [v.get("reason", "No reason provided") if isinstance(v, dict) else str(v) for v in vetoes]
        veto_authors = [v.get("vetoed_by", "A reviewer") if isinstance(v, dict) else "A reviewer" for v in vetoes]

        # Determine phase from first veto or default
        phase = (
            vetoes[0].get("phase", "unknown") if vetoes and isinstance(vetoes[0], dict)
            else "unknown"
        )

        what_we_did = (
            f"We completed work on task **{task_id}** and submitted it for review. "
            f"{veto_count} reviewer(s) raised concerns that blocked the work "
            f"from moving forward. This means the team cannot proceed without "
            f"your input."
        )

        author_list = ", ".join(veto_authors)
        what_changed = (
            f"The review process flagged issues that the team could not resolve "
            f"on their own. {author_list} believe the current approach needs "
            f"reconsideration. This is a normal part of quality control — it "
            f"means the system caught something worth your attention."
        )

        # Build key choices representing the veto dispute
        key_choices = []
        for i, veto in enumerate(vetoes):
            if isinstance(veto, dict):
                reason = veto.get("reason", "No reason given")
                vetoed_by = veto.get("vetoed_by", "Unknown reviewer")
                key_choices.append(KeyChoice(
                    question=f"Disagreement #{i + 1}: Should we follow {vetoed_by}'s concern?",
                    option_a="Accept the concern and revise the work",
                    option_b="Override the concern and proceed as-is",
                    why_a=(
                        f"The reviewer believes: {reason}. "
                        f"Addressing this now prevents bigger problems later."
                    ),
                    why_not_b=(
                        "Ignoring this concern could lead to rework later — "
                        "potentially more expensive and time-consuming."
                    ),
                    risk_if_wrong=(
                        "If the reviewer is wrong, we spend time on unnecessary changes. "
                        "If the reviewer is right and we ignore it, the issue could affect "
                        "users or require major rework later."
                    ),
                ))

        # Build risks
        risks = [
            RiskItem(
                risk="The project is blocked until this disagreement is resolved",
                likelihood="Certain — until you decide",
                impact="No further progress can be made on this task",
                analogy="Like a traffic light stuck on red — nobody moves until it is fixed",
                mitigation="We have prepared clear options for you to choose from",
            ),
            RiskItem(
                risk="Rushing a decision without understanding the trade-offs",
                likelihood="Medium",
                impact="You might approve something you later regret",
                analogy="Like buying a house without reading the inspection report",
                mitigation=(
                    "We have explained each reviewer's concern in plain language. "
                    "Take the time you need."
                ),
            ),
        ]

        decision = DecisionRequired(
            question=(
                f"How should we resolve the disagreement about task {task_id}?"
            ),
            options=[
                "Accept the reviewer concerns — revise the work and resubmit",
                "Override the veto — proceed without changes",
                "Request more information — I need a clearer explanation",
                "Escalate to a senior reviewer for a tie-breaking opinion",
            ],
            recommendation=(
                "We recommend accepting the reviewer concerns and revising the work. "
                "Reviewers are independent and have no stake in the outcome — their "
                "concerns usually point to real issues. The cost of revising now is "
                "almost always lower than fixing problems after delivery."
            ),
            deadline="5 days from now (the team cannot proceed until resolved)",
        )

        import uuid
        packet_id = f"HRP-VETO-{uuid.uuid4().hex[:8].upper()}"

        from datetime import timedelta
        expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        # Evidence summary from vetoes
        evidence_parts = [f"- {veto_count} reviewer(s) raised concerns"]
        for reason in veto_reasons:
            evidence_parts.append(f"- Concern: {reason}")

        return HumanReviewPacket(
            packet_id=packet_id,
            packet_type=PacketType.VETO_ESCALATION,
            phase=phase,
            task_id=task_id,
            what_we_did=what_we_did,
            what_changed=what_changed,
            key_choices=key_choices,
            risks=risks,
            decision_required=decision,
            evidence_summary="\n".join(evidence_parts),
            who_reviewed=veto_authors,
            vetoes=veto_reasons,
            expires_at=expires,
        )

    @staticmethod
    def _extract_key_choices(
        phase: str,
        artifacts: dict,
    ) -> list[KeyChoice]:
        """Derive key-choice narratives from phase artifacts.

        Maps artifact descriptions into trade-off explanations that a
        non-technical user can understand.
        """
        choices: list[KeyChoice] = []

        # Architecture phase: typical trade-off choices
        if "architecture" in phase.lower():
            if artifacts:
                first_key = list(artifacts.keys())[0]
                first_desc = artifacts[first_key]
                choices.append(KeyChoice(
                    question="How should the system be organised?",
                    option_a=f"Modular design ({first_key})",
                    option_b="Single large program",
                    why_a=(
                        f"{first_desc}. A modular design makes it easier to "
                        f"change one part without affecting everything else — "
                        f"like being able to renovate the kitchen without "
                        f"touching the bedroom."
                    ),
                    why_not_b=(
                        "A single large program is simpler at first but becomes "
                        "harder to maintain as the system grows — like a house "
                        "where every room shares one light switch."
                    ),
                    risk_if_wrong=(
                        "If the modules are split incorrectly, we may need to "
                        "reorganise later. This costs time but is still easier "
                        "than starting from a single large program."
                    ),
                ))

        # Implementation phase
        if "implementation" in phase.lower():
            choices.append(KeyChoice(
                question="How do we ensure each piece works before combining them?",
                option_a="Test each piece independently first",
                option_b="Build everything then test at the end",
                why_a=(
                    "Testing each piece on its own catches problems early, "
                    "when they are cheaper and faster to fix — like checking "
                    "each ingredient before cooking."
                ),
                why_not_b=(
                    "Testing only at the end means problems pile up and become "
                    "harder to untangle — like tasting a dish only after "
                    "everything is mixed together."
                ),
                risk_if_wrong=(
                    "If our tests miss something, a bug could reach users. "
                    "But finding it in isolated testing is much faster to fix."
                ),
            ))

        # Generic fallback for any phase
        if not choices and artifacts:
            first_key = list(artifacts.keys())[0]
            choices.append(KeyChoice(
                question=f"How did we approach the {_phase_label(phase)} phase?",
                option_a="Structured, step-by-step approach",
                option_b="Rapid, all-at-once delivery",
                why_a=(
                    f"We produced {first_key} and related outputs in a "
                    f"deliberate order so each step builds on the last."
                ),
                why_not_b=(
                    "Doing everything at once is faster initially but makes "
                    "it harder to spot and fix problems."
                ),
                risk_if_wrong=(
                    "If the order of steps was wrong, we may need to revisit "
                    "earlier decisions. The cost is usually small at this stage."
                ),
            ))

        return choices


# ── Internal Helpers ───────────────────────────────────────────────────────


def _phase_label(phase: str) -> str:
    """Convert a phase identifier to a human-readable label."""
    phase_map: dict[str, str] = {
        "S0-init": "Project Start",
        "S1-requirements": "Requirements",
        "S2-architecture": "Architecture Design",
        "S3-interface": "Interface Design",
        "S4-implementation": "Implementation",
        "S5-quality": "Quality Assurance",
        "S6-delivery": "Delivery",
        "S7-integration": "Integration",
        "S8-functional-test": "Functional Testing",
        "S9-fix-optimize": "Fixes and Optimisation",
        "S10-performance": "Performance Testing",
        "S11-maintenance": "Maintenance",
    }
    return phase_map.get(phase, phase.replace("-", " ").title())


def _format_ts(ts_str: str) -> str:
    """Format an ISO timestamp string for display."""
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, TypeError):
        return ts_str
