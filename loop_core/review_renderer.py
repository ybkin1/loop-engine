"""
Human review packet renderer — markdown / plain-text rendering.

T-0110 批 B-2 拆分（行为等价，纯外提 re-export）：
- 原 loop_core/human_review_packet.py 的渲染逻辑（HumanReviewPacket.to_markdown /
  to_plain_text 的函数体 + _phase_label / _format_ts）逐字迁移至此
  （design-common-weakness.md 1.4 拆分边界表 :570-682,1282-1307）。
- 壳文件 HumanReviewPacket 的两个方法改为薄委托（``return render_markdown(self)``），
  输出逐字节不变；_phase_label / _format_ts 由壳 re-export（builder 继续消费）。
- 本模块零 loop_core 内部依赖（渲染函数按鸭子类型访问 packet 属性），无循环导入。
"""
from __future__ import annotations

from datetime import datetime


def render_markdown(packet) -> str:
    """Render the packet as a human-readable Markdown document."""
    lines: list[str] = []

    # Header
    phase_label = _phase_label(packet.phase)
    lines.append(f"# Phase Delivery Decision Packet — {phase_label}")
    lines.append("")
    lines.append(f"**Packet ID:** {packet.packet_id}  ")
    lines.append(f"**Generated:** {_format_ts(packet.generated_at)}  ")
    if packet.expires_at:
        lines.append(f"**Decision needed by:** {_format_ts(packet.expires_at)}  ")
    lines.append("")

    # What we did
    lines.append("## What We Did")
    lines.append("")
    lines.append(packet.what_we_did)
    lines.append("")

    # What changed
    if packet.what_changed:
        lines.append("## What Changed")
        lines.append("")
        lines.append(packet.what_changed)
        lines.append("")

    # Key choices
    if packet.key_choices:
        lines.append("## Key Choices")
        lines.append("")
        for i, choice in enumerate(packet.key_choices, 1):
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
    if packet.risks:
        lines.append("## Main Risks")
        lines.append("")
        lines.append("| Risk | Likelihood | Impact | What We Did |")
        lines.append("|------|-----------|--------|-------------|")
        for risk in packet.risks:
            lines.append(
                f"| {risk.risk} | {risk.likelihood} | {risk.impact} "
                f"| {risk.mitigation} |"
            )
        lines.append("")
        for risk in packet.risks:
            lines.append(f"- **{risk.risk}** — *Analogy:* {risk.analogy}")
            lines.append("")

    # Evidence
    if packet.evidence_summary:
        lines.append("## Quality Check")
        lines.append("")
        lines.append(packet.evidence_summary)
        lines.append("")

    # Who reviewed
    if packet.who_reviewed:
        lines.append("## Who Reviewed This Work")
        lines.append("")
        for reviewer in packet.who_reviewed:
            lines.append(f"- {reviewer}")
        lines.append("")

    # Vetoes
    if packet.vetoes:
        lines.append("## Vetoes Raised")
        lines.append("")
        for veto in packet.vetoes:
            lines.append(f"- {veto}")
        lines.append("")

    # Related past experience (U4) — only when the caller attached it
    if packet.related_experience:
        lines.append("## Related Past Experience")
        lines.append("")
        lines.append(
            "Past gate decisions with similar context may help your review:"
        )
        lines.append("")
        lines.append(packet.related_experience)
        lines.append("")

    # Decision required
    if packet.decision_required:
        lines.append("## You Need to Decide")
        lines.append("")
        lines.append(f"**{packet.decision_required.question}**")
        lines.append("")
        for option in packet.decision_required.options:
            lines.append(f"- [ ] {option}")
        lines.append("")
        lines.append(f"**Our recommendation:** {packet.decision_required.recommendation}")
        if packet.decision_required.deadline:
            lines.append("")
            lines.append(
                f"Please decide by **{packet.decision_required.deadline}**. "
                "If you have questions, your product manager can walk through "
                "each piece with you."
            )

    return "\n".join(lines)


def render_plain_text(packet) -> str:
    """Render the packet as plain text (no markdown formatting)."""
    lines: list[str] = []

    phase_label = _phase_label(packet.phase)
    lines.append(f"PHASE DELIVERY DECISION PACKET — {phase_label}")
    lines.append(f"Packet ID: {packet.packet_id}")
    lines.append(f"Generated: {_format_ts(packet.generated_at)}")
    if packet.expires_at:
        lines.append(f"Decision needed by: {_format_ts(packet.expires_at)}")
    lines.append("")

    lines.append("WHAT WE DID")
    lines.append(packet.what_we_did)
    lines.append("")

    if packet.what_changed:
        lines.append("WHAT CHANGED")
        lines.append(packet.what_changed)
        lines.append("")

    if packet.key_choices:
        lines.append("KEY CHOICES")
        for i, choice in enumerate(packet.key_choices, 1):
            lines.append(f"  {i}. {choice.question}")
            lines.append(f"     We chose: {choice.option_a}")
            lines.append(f"     Did not choose: {choice.option_b}")
            lines.append(f"     Why: {choice.why_a}")
            lines.append(f"     Why not the other: {choice.why_not_b}")
            lines.append(f"     If wrong: {choice.risk_if_wrong}")
            lines.append("")

    if packet.risks:
        lines.append("MAIN RISKS")
        for risk in packet.risks:
            lines.append(f"  - {risk.risk}")
            lines.append(f"    Likelihood: {risk.likelihood}")
            lines.append(f"    Impact: {risk.impact}")
            lines.append(f"    Analogy: {risk.analogy}")
            lines.append(f"    What we did: {risk.mitigation}")
            lines.append("")

    if packet.evidence_summary:
        lines.append("QUALITY CHECK")
        lines.append(packet.evidence_summary)
        lines.append("")

    if packet.who_reviewed:
        lines.append("WHO REVIEWED THIS WORK")
        for reviewer in packet.who_reviewed:
            lines.append(f"  - {reviewer}")
        lines.append("")

    if packet.vetoes:
        lines.append("VETOES RAISED")
        for veto in packet.vetoes:
            lines.append(f"  - {veto}")
        lines.append("")

    if packet.related_experience:
        lines.append("RELATED PAST EXPERIENCE")
        lines.append(
            "Past gate decisions with similar context may help your review:"
        )
        lines.append("")
        for line in packet.related_experience.splitlines():
            lines.append(line)
        lines.append("")

    if packet.decision_required:
        lines.append("YOU NEED TO DECIDE")
        lines.append(f"  {packet.decision_required.question}")
        for option in packet.decision_required.options:
            lines.append(f"  [ ] {option}")
        lines.append(f"  Recommendation: {packet.decision_required.recommendation}")
        if packet.decision_required.deadline:
            lines.append(f"  Deadline: {packet.decision_required.deadline}")

    return "\n".join(lines)


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
