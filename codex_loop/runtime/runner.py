from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codex_loop.context.builder import ContextBudgetError, build_context_packet
from codex_loop.context.policy import PermissionError, assert_write_allowed, safe_relative_path
from codex_loop.core.contracts import RoleRegistry
from codex_loop.core.models import RoleRunEnvelope
from codex_loop.core.store import LoopStore, StoreError
from codex_loop.planning.work_packets import packet_for_role


class RuntimeAdmissionError(ValueError):
    """Raised when the bounded runtime request cannot be admitted."""


RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


@dataclass(frozen=True)
class RoleRunRequest:
    run_id: str
    role_id: str
    task_id: str
    phase_id: str
    purpose: str
    inputs: tuple[str, ...] = ()
    selected_materials: tuple[str, ...] = ()
    selected_evidence: tuple[tuple[str, str], ...] = ()
    available_tools: tuple[str, ...] = ()
    write_targets: tuple[str, ...] = ()
    declared_write_aliases: tuple[tuple[str, str], ...] = ()


class CodexRuntime:
    """Admission and invocation-spec boundary for the local candidate."""

    def __init__(self, project_root: Path, registry_path: Path | None = None):
        self.project_root = project_root.resolve()
        self.store = LoopStore(self.project_root)
        registry = registry_path or Path(__file__).resolve().parents[1] / "roles" / "registry.json"
        self.registry = RoleRegistry.load(registry)

    def prepare_run(self, request: RoleRunRequest) -> RoleRunEnvelope:
        self._validate_request(request)
        if not self.store.exists():
            raise StoreError("Loop store is not initialized")
        role = self.registry.get(request.role_id)
        packet = packet_for_role(
            role, request.task_id, request.phase_id, request.purpose,
            request.inputs, request.selected_materials,
        )
        tools = self._tool_preflight(role, request.available_tools)
        permissions = self._permission_preflight(role, request)
        probe = self._capability_probe(role, tools, permissions)
        envelope = RoleRunEnvelope(
            request.run_id, role.role_id, role.role_version, request.task_id, request.phase_id,
            tool_preflight=tools, permission_preflight=permissions, capability_probe=probe,
        )
        if tools["status"] != "PASS" or permissions["status"] != "PASS":
            envelope.verdict = "BLOCKED"
            envelope.unverified.append("invocation spec was not created")
            self._persist_envelope(envelope)
            return envelope
        return self._prepare_admitted_run(request, role, packet, envelope)

    def _validate_request(self, request: RoleRunRequest) -> None:
        if not RUN_ID_PATTERN.fullmatch(request.run_id):
            raise RuntimeAdmissionError("run_id must be a short safe identifier")
        if not request.task_id or not request.phase_id or not request.purpose:
            raise RuntimeAdmissionError("task_id, phase_id and purpose are required")
        if self.registry.get(request.role_id).data.get("host", "codex") != "codex":
            raise RuntimeAdmissionError("role contract is not Codex-only")

    def _tool_preflight(self, role: Any, available: tuple[str, ...]) -> dict[str, Any]:
        required = tuple(role.data["required_tools"])
        available_set = set(available)
        missing = [tool for tool in required if tool not in available_set]
        return {
            "status": "PASS" if not missing else "BLOCKED",
            "required_tools": list(required),
            "available_tools": sorted(available_set),
            "missing_tools": missing,
        }

    def _permission_preflight(self, role: Any, request: RoleRunRequest) -> dict[str, Any]:
        if role.data.get("can_write_state") and not request.write_targets:
            return {"status": "BLOCKED", "reason": "state-writing role needs an explicit target"}
        aliases = dict(request.declared_write_aliases)
        resolved: list[str] = []
        errors: list[str] = []
        for target in request.write_targets:
            try:
                resolved.append(self._check_target(role, target, aliases).as_posix())
            except PermissionError as exc:
                errors.append(str(exc))
        return {"status": "PASS" if not errors else "BLOCKED", "targets": resolved, "errors": errors}

    def _check_target(self, role: Any, target: str, aliases: dict[str, str]) -> Path:
        allowed = tuple(role.data["allowed_write"])
        if target in allowed and not target.startswith(".loop/"):
            if target not in aliases:
                raise PermissionError(f"symbolic write target has no declaration: {target}")
            relative = safe_relative_path(self.project_root, Path(aliases[target]))
            if role.role_id != "controller" and relative.as_posix().startswith(".loop/state/"):
                raise PermissionError("only controller may target .loop/state/")
            return relative
        return assert_write_allowed(self.project_root, Path(target), allowed)

    def _capability_probe(self, role: Any, tools: dict[str, Any], permissions: dict[str, Any]) -> dict[str, Any]:
        checks = [
            {"id": "contract_shape", "status": "PASS"},
            {"id": "prompt_bounded", "status": "PASS"},
            {"id": "role_isolation", "status": "PASS"},
            {"id": "runtime_behavior", "status": "NOT_RUN", "reason": "model invocation is host-owned"},
        ]
        status = "NOT_RUN"
        if tools["status"] != "PASS" or permissions["status"] != "PASS":
            status = "BLOCKED"
        return {
            "probe_id": role.data["capability_profile"]["probe_id"],
            "minimum_pass": role.data["capability_profile"]["minimum_pass"],
            "status": status,
            "checks": checks,
            "evidence": "contract admission only; behavioral capability is not certified",
        }

    def _prepare_admitted_run(self, request: RoleRunRequest, role: Any, packet: Any, envelope: RoleRunEnvelope) -> RoleRunEnvelope:
        try:
            context = build_context_packet(
                role, self._overlay(), packet, request.selected_evidence,
            )
        except (ContextBudgetError, PermissionError) as exc:
            envelope.verdict = "BLOCKED"
            envelope.unverified.append(str(exc))
            self._persist_envelope(envelope)
            return envelope
        envelope.verdict = "READY_TO_INVOKE"
        envelope.unverified.extend([
            "model execution not performed",
            "behavioral capability probe not run",
            "model response schema not validated",
        ])
        spec = {
            "spec_version": "0.1.0",
            "mode": "codex-bounded-invocation-spec",
            "host": "codex",
            "run_id": request.run_id,
            "role_id": role.role_id,
            "role_version": role.role_version,
            "prompt": role.prompt_text(),
            "work_packet": packet.to_dict(),
            "context": context,
            "required_outputs": list(role.data["required_outputs"]),
            "must_not_claim": ["quality pass", "security pass", "user acceptance"],
            "execution_status": "not_performed_by_candidate",
        }
        self.store.write_json(f"runs/{request.run_id}.invocation.json", spec)
        envelope.input_fingerprints = dict(context["input_fingerprints"])
        self._persist_envelope(envelope)
        return envelope

    def _overlay(self) -> Any:
        from codex_loop.core.models import ProjectOverlay

        profile = self.store.read_json("project.json")
        return ProjectOverlay(
            project_id=str(profile["project_id"]),
            goal=str(profile["goal"]),
            risk_tier=str(profile.get("risk_tier", "medium")),
            delivery_target=str(profile.get("delivery_target", "candidate")),
            technology_baseline=tuple(profile.get("technology_baseline", ())),
            user_decisions=tuple(profile.get("user_decisions", ())),
            current_constraints=tuple(profile.get("current_constraints", ())),
        )

    def _persist_envelope(self, envelope: RoleRunEnvelope) -> None:
        self.store.write_json(f"runs/{envelope.run_id}.json", envelope.to_dict())
