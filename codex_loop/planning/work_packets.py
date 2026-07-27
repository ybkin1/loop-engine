from __future__ import annotations

from codex_loop.core.contracts import RoleContract
from codex_loop.core.models import WorkPacket


def packet_for_role(
    role: RoleContract,
    task_id: str,
    phase_id: str,
    purpose: str,
    inputs: tuple[str, ...] = (),
    selected_materials: tuple[str, ...] = (),
) -> WorkPacket:
    return WorkPacket(
        packet_id=f"WP-{phase_id}-{role.role_id}-{task_id}",
        task_id=task_id,
        phase_id=phase_id,
        role_id=role.role_id,
        purpose=purpose,
        inputs=inputs,
        selected_materials=selected_materials,
        expected_outputs=tuple(role.data["required_outputs"]),
        allowed_read=tuple(role.data["allowed_read"]),
        allowed_write=tuple(role.data["allowed_write"]),
        forbidden_actions=tuple(role.data["forbidden_actions"]),
        context_budget_tokens=role.context_budget_tokens,
    )
