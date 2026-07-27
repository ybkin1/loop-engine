from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from codex_loop.context.policy import assert_no_secret_markers
from codex_loop.core.contracts import RoleContract
from codex_loop.core.models import ProjectOverlay, WorkPacket


class ContextBudgetError(ValueError):
    """Raised when a role packet cannot fit within its declared context budget."""


def fingerprint_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fingerprint_paths(root: Path, paths: Iterable[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in paths:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        result[relative] = fingerprint_text(path.read_text(encoding="utf-8"))
    return result


def approximate_tokens(text: str) -> int:
    return max(1, len(text.encode("utf-8")) // 4)


def build_context_packet(
    role: RoleContract,
    overlay: ProjectOverlay,
    packet: WorkPacket,
    selected_evidence: Iterable[tuple[str, str]],
) -> dict[str, object]:
    evidence = list(selected_evidence)
    sections = [
        ("role_contract", role.prompt_text()),
        ("project_overlay", json.dumps(overlay.to_dict(), ensure_ascii=False, sort_keys=True)),
        ("work_packet", json.dumps(packet.to_dict(), ensure_ascii=False, sort_keys=True)),
    ]
    for label, content in evidence:
        sections.append((f"evidence:{label}", content))
    combined = "\n\n".join(f"[{label}]\n{content}" for label, content in sections)
    assert_no_secret_markers(combined)
    budget = min(role.context_budget_tokens, packet.context_budget_tokens)
    used = approximate_tokens(combined)
    if used > budget:
        raise ContextBudgetError(f"context budget exceeded: used={used}, budget={budget}")
    return {
        "role_id": role.role_id,
        "role_version": role.role_version,
        "packet_id": packet.packet_id,
        "input_fingerprints": {label: fingerprint_text(content) for label, content in sections},
        "approximate_tokens": used,
        "budget_tokens": budget,
        "sections": [{"label": label, "content": content} for label, content in sections],
    }
