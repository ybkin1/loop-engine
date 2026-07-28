from __future__ import annotations

from collections.abc import Iterable


def render_human_review_packet(
    project_id: str,
    phase_id: str,
    conclusion: str,
    artifact_paths: Iterable[str],
    verified: Iterable[str],
    unverified: Iterable[str],
    user_questions: Iterable[str],
) -> str:
    verified_items = list(verified) or ["none"]
    unverified_items = list(unverified) or ["none"]
    lines = [
        f"# Human Review Packet：{project_id} / {phase_id}",
        "",
        "状态：`ready_for_review`；这不是用户批准。",
        "",
        "## 请用户决定",
        *[f"- {question}" for question in user_questions],
        "",
        "## 本阶段结论",
        conclusion,
        "",
        "## 关键产物",
        *[f"- `{path}`" for path in artifact_paths],
        "",
        "## 已验证",
        *[f"- {item}" for item in verified_items],
        "",
        "## 未验证/限制",
        *[f"- {item}" for item in unverified_items],
        "",
        "## 用户决定",
        "- [ ] approve",
        "- [ ] repair",
        "- [ ] reject",
        "- [ ] defer",
        "",
    ]
    return "\n".join(lines)
