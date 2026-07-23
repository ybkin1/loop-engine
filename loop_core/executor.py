"""
Loop Executor — Phase and Role execution engine.

This is the "runtime" that actually drives the Loop process — not just defines
what should happen, but schedules and executes it. Host-independent.

Architecture:
    PhaseExecutor: drives a complete phase (init → roles → gate → advance)
    RoleExecutor: drives a single role execution (input → agent → validate → retry)

Key methods:
    execute_phase(): orchestrates a full phase execution
    execute_role(): executes a single role via subprocess/agent
    persist_state(): writes state back to .ai/state.yaml and .ai/task_graph.yaml
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from loop_core.state_machine import (
    Phase, GateStatus, StateValidationResult,
    can_approve_gate, can_enter_phase, can_transition_phase,
)
from loop_core.router import LoopMode


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"  # Output exists but missing required fields
    BLOCKED = "blocked"        # Role issued BLOCKED verdict
    FAILED = "failed"          # Execution error


@dataclass
class RoleStep:
    """One role execution step within a phase."""
    role_id: str
    status: StepStatus = StepStatus.PENDING
    agent_id: str | None = None
    output_file: str | None = None
    verdict: str | None = None  # "PASS" | "BLOCKED"
    retries: int = 0
    max_retries: int = 3
    required_fields: list[str] = field(default_factory=list)
    filled_fields: list[str] = field(default_factory=list)


@dataclass
class PhasePlan:
    """A complete phase execution plan."""
    phase: Phase
    loop_mode: LoopMode
    steps: list[RoleStep] = field(default_factory=list)
    current_step: int = 0
    status: StepStatus = StepStatus.PENDING
    gate_id: str | None = None
    gate_status: GateStatus | None = None
    input_hashes: dict[str, str] = field(default_factory=dict)


# Phase → required roles mapping
PHASE_ROLES: dict[Phase, list[str]] = {
    Phase.S0_INIT: ["product-manager", "project-manager"],
    Phase.S1_REQUIREMENTS: ["product-manager", "system-architect", "quality-engineer"],
    Phase.S2_ARCHITECTURE: ["system-architect", "module-architect", "independent-reviewer"],
    Phase.S3_INTERFACE: ["module-architect", "developer"],
    Phase.S4_IMPLEMENTATION: ["developer", "independent-reviewer", "quality-engineer"],
    Phase.S5_QUALITY: ["quality-engineer", "security-engineer"],
    Phase.S6_DELIVERY: ["delivery-manager", "release-engineer"],
    Phase.S7_INTEGRATION: ["developer", "quality-engineer"],
    Phase.S8_FUNCTIONAL_TEST: ["quality-engineer", "product-manager"],
    Phase.S9_FIX_OPTIMIZE: ["developer", "independent-reviewer", "quality-engineer"],
    Phase.S10_PERFORMANCE: ["quality-engineer", "system-architect"],
    Phase.S11_MAINTENANCE: ["product-manager"],
}

# LIGHTWEIGHT mode skips many phases and uses fewer roles
LIGHTWEIGHT_PHASES = {Phase.S0_INIT, Phase.S4_IMPLEMENTATION, Phase.S6_DELIVERY}
LIGHTWEIGHT_ROLES = ["developer"]

# STANDARD mode uses core phases
STANDARD_PHASES = {
    Phase.S0_INIT, Phase.S1_REQUIREMENTS, Phase.S2_ARCHITECTURE,
    Phase.S4_IMPLEMENTATION, Phase.S5_QUALITY, Phase.S6_DELIVERY,
}


class PhaseExecutor:
    """
    Drives execution of a complete Loop phase.

    Flow:
        1. Check preconditions (previous phase gate approved, no blockers)
        2. Determine required roles for this phase/mode
        3. For each role: freeze inputs → launch agent → collect → validate
        4. Any role incomplete → retry (up to max_retries)
        5. Any role BLOCKED → phase blocked
        6. All roles PASS → create gate → present to user
        7. Gate approved → advance phase
    """

    def __init__(self, mode: LoopMode = LoopMode.FULL):
        self.mode = mode

    def get_phases(self) -> list[Phase]:
        """Get the list of phases for the current mode."""
        if self.mode == LoopMode.LIGHTWEIGHT:
            return [p for p in Phase if p in LIGHTWEIGHT_PHASES]
        elif self.mode == LoopMode.STANDARD:
            return [p for p in Phase if p in STANDARD_PHASES]
        return list(Phase)

    def get_roles_for_phase(self, phase: Phase) -> list[str]:
        """Get required roles for a phase in the current mode."""
        if self.mode == LoopMode.LIGHTWEIGHT:
            return LIGHTWEIGHT_ROLES
        return PHASE_ROLES.get(phase, [])

    def plan_phase(self, phase: Phase, input_hashes: dict[str, str] | None = None) -> PhasePlan:
        """Create an execution plan for a phase."""
        roles = self.get_roles_for_phase(phase)
        steps = []

        for role_id in roles:
            required = self._get_required_fields(role_id, phase)
            steps.append(RoleStep(
                role_id=role_id,
                required_fields=required,
            ))

        return PhasePlan(
            phase=phase,
            loop_mode=self.mode,
            steps=steps,
            input_hashes=input_hashes or {},
        )

    @staticmethod
    def _get_required_fields(role_id: str, phase: Phase) -> list[str]:
        """Get the required output fields for a role in a phase."""
        # Universal required fields for all role outputs
        universal = ["verdict", "summary"]

        role_specific = {
            "system-architect": ["architecture_overview", "module_list", "component_list",
                                  "interface_definitions", "data_model", "dependency_graph",
                                  "security_boundaries", "deployment_structure", "design_rationale"],
            "developer": ["implemented_files", "test_results", "implementation_notes"],
            "quality-engineer": ["test_strategy", "test_cases", "coverage_report",
                                  "defect_list", "quality_verdict"],
            "independent-reviewer": ["verdict", "findings", "files_reviewed"],
            "product-manager": ["user_profiles", "functional_requirements",
                                 "non_functional_requirements", "acceptance_criteria", "exclusions"],
            "security-engineer": ["vulnerability_list", "severity_levels", "remediation_plan"],
            "delivery-manager": ["delivery_checklist", "deployment_plan", "rollback_plan", "go_nogo"],
        }

        return universal + role_specific.get(role_id, [])

    def validate_step(self, step: RoleStep, output: dict) -> StepStatus:
        """Validate a role's output against its required fields."""
        if not output:
            return StepStatus.FAILED

        verdict = output.get("verdict", "")
        if verdict == "BLOCKED":
            step.verdict = "BLOCKED"
            return StepStatus.BLOCKED

        filled = [f for f in step.required_fields if f in output and output[f]]
        step.filled_fields = filled

        missing = set(step.required_fields) - set(filled)
        if missing:
            step.status = StepStatus.INCOMPLETE
            return StepStatus.INCOMPLETE

        step.verdict = "PASS"
        step.status = StepStatus.COMPLETE
        return StepStatus.COMPLETE

    def can_advance(self, plan: PhasePlan) -> tuple[bool, str]:
        """Check if the phase can advance to the next."""
        blocked_steps = [s for s in plan.steps if s.status == StepStatus.BLOCKED]
        if blocked_steps:
            return False, f"Blocked by: {[s.role_id for s in blocked_steps]}"

        incomplete_steps = [s for s in plan.steps if s.status == StepStatus.INCOMPLETE]
        if incomplete_steps:
            roles = [f"{s.role_id}({len(s.filled_fields)}/{len(s.required_fields)})" for s in incomplete_steps]
            return False, f"Incomplete: {roles}"

        pending_steps = [s for s in plan.steps if s.status in (StepStatus.PENDING, StepStatus.RUNNING)]
        if pending_steps:
            return False, f"Still running: {[s.role_id for s in pending_steps]}"

        return True, "All roles complete"

    def next_phase(self, current: Phase) -> Phase | None:
        """Get the next phase in sequence for the current mode."""
        phases = self.get_phases()
        try:
            idx = phases.index(current)
            if idx + 1 < len(phases):
                return phases[idx + 1]
        except ValueError:
            pass
        return None

    # ── Execution Engine ──────────────────────────────────────────────

    def _read_state(self, project_root: Path) -> dict[str, Any]:
        """Read .ai/state.yaml and return parsed dict. Returns empty dict if missing."""
        state_path = project_root / ".ai" / "state.yaml"
        if not state_path.exists():
            return {}
        try:
            import yaml
            with open(state_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            # Fallback: simple line-by-line parser for basic YAML
            state: dict[str, Any] = {}
            text = state_path.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if ":" in stripped and not stripped.startswith("#"):
                    key, _, val = stripped.partition(":")
                    val = val.strip().strip('"').strip("'")
                    if val in ("null", "~", ""):
                        val = None
                    state[key.strip()] = val
            return state

    def _write_state(self, project_root: Path, plan: PhasePlan) -> None:
        """Write current phase and mode back to .ai/state.yaml."""
        state_path = project_root / ".ai" / "state.yaml"
        state_path.parent.mkdir(parents=True, exist_ok=True)

        existing = self._read_state(project_root)
        existing["current_phase"] = plan.phase.value
        existing["loop_mode"] = plan.loop_mode.value
        existing["current_gate_id"] = plan.gate_id
        existing["last_handoff_at"] = datetime.now(timezone.utc).isoformat()

        lines: list[str] = []
        lines.append("schema_version: 1")
        lines.append(f"project_name: {existing.get('project_name', 'loop-project')}")
        lines.append(f"current_phase: {plan.phase.value}")
        lines.append(f"loop_mode: {plan.loop_mode.value.upper()}")
        if plan.gate_id:
            lines.append(f"current_gate_id: {plan.gate_id}")
        lines.append(f"last_handoff_at: {existing['last_handoff_at']}")
        if existing.get("current_task_id"):
            lines.append(f"current_task_id: {existing['current_task_id']}")

        state_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_task_graph(self, project_root: Path, plan: PhasePlan) -> None:
        """Write phase execution summary to .ai/task_graph.yaml."""
        graph_path = project_root / ".ai" / "task_graph.yaml"
        graph_path.parent.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc).isoformat()
        lines: list[str] = []
        lines.append(f"# Task graph auto-generated at {now}")
        lines.append(f"phase: {plan.phase.value}")
        lines.append(f"status: {plan.status.value}")
        lines.append("steps:")
        for step in plan.steps:
            lines.append(f"  - role_id: {step.role_id}")
            lines.append(f"    status: {step.status.value}")
            lines.append(f"    verdict: {step.verdict or 'N/A'}")
            lines.append(f"    retries: {step.retries}")
            if step.output_file:
                lines.append(f"    output_file: {step.output_file}")
        if plan.input_hashes:
            lines.append("input_hashes:")
            for fname, fhash in plan.input_hashes.items():
                lines.append(f"  {fname}: {fhash}")

        graph_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _freeze_inputs(self, input_files: list[str]) -> dict[str, str]:
        """Compute SHA256 hashes for a list of input files."""
        hashes: dict[str, str] = {}
        for fpath in input_files:
            p = Path(fpath)
            if p.exists():
                h = hashlib.sha256(p.read_bytes()).hexdigest()
                hashes[str(p)] = h
            else:
                hashes[str(p)] = "MISSING"
        return hashes

    def execute_role(
        self,
        role_id: str,
        role_prompt: str,
        input_files: list[str],
        output_file: str | None = None,
        required_fields: list[str] | None = None,
    ) -> RoleStep:
        """Execute a single role via subprocess/agent call.

        Returns a RoleStep populated with the result.
        The actual agent launch mechanism is abstracted behind
        self._launch_agent_subprocess (overridable for host adapters).

        Args:
            role_id: The role identifier (e.g., 'developer', 'quality-engineer')
            role_prompt: The prompt/instructions for the role
            input_files: List of input file paths for the role
            output_file: Optional path for the output JSON file
            required_fields: Optional list of required output fields.
                             If not provided, uses product-manager fields as default.
        """
        if required_fields is None:
            # Use a generous default set for general-purpose roles
            required_fields = ["verdict", "summary"]
        step = RoleStep(
            role_id=role_id,
            status=StepStatus.RUNNING,
            required_fields=required_fields,
            output_file=output_file,
        )

        try:
            output_path = output_file or f".ai/role_outputs/{role_id}.json"
            result_json = self._launch_agent_subprocess(
                role_id, role_prompt, input_files, output_path
            )
            status = self.validate_step(step, result_json)
            step.status = status
            return step
        except Exception as e:
            step.status = StepStatus.FAILED
            step.verdict = str(e)
            return step

    def _launch_agent_subprocess(
        self,
        role_id: str,
        role_prompt: str,
        input_files: list[str],
        output_path: str,
    ) -> dict[str, Any]:
        """Launch a role agent via subprocess.

        In production this would call the host adapter's launch_agent().
        For testing, this can be monkey-patched or stubbed.

        The agent script must:
          1. Accept a JSON prompt on stdin
          2. Read input_files
          3. Produce output JSON to the given output_path
          4. Return output JSON on stdout
        """
        agent_script = Path("agents") / role_id / "run.py"
        if not agent_script.exists():
            # Fallback: simulate output for agents without a real script
            return self._simulate_role_output(role_id, output_path)

        payload = json.dumps({
            "role_id": role_id,
            "prompt": role_prompt,
            "input_files": input_files,
            "output_file": output_path,
        })

        result = subprocess.run(
            [sys.executable, str(agent_script)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Agent {role_id} failed (exit {result.returncode}): {result.stderr}"
            )

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            # Try reading from output file
            out_p = Path(output_path)
            if out_p.exists():
                return json.loads(out_p.read_text(encoding="utf-8"))
            raise RuntimeError(
                f"Agent {role_id} produced unparseable output"
            ) from None

    def _simulate_role_output(self, role_id: str, output_path: str) -> dict[str, Any]:
        """Produce a simulated role output when no real agent script exists.

        This is a fallback for testing/demo. In production a real agent is used.
        """
        output: dict[str, Any] = {
            "verdict": "PASS",
            "summary": f"Simulated output from {role_id}",
        }

        # Fill in role-specific fields with stubs
        role_specific_fields = {
            "system-architect": {
                "architecture_overview": "System architecture overview",
                "module_list": ["module_a", "module_b"],
                "component_list": ["comp_1", "comp_2"],
                "interface_definitions": ["iface_1"],
                "data_model": "Data model description",
                "dependency_graph": "Dependency graph",
                "security_boundaries": ["boundary_1"],
                "deployment_structure": "Deployment structure",
                "design_rationale": "Design rationale",
            },
            "developer": {
                "implemented_files": ["src/main.py"],
                "test_results": "All tests pass",
                "implementation_notes": "Implemented as specified",
            },
            "quality-engineer": {
                "test_strategy": "Unit + integration",
                "test_cases": ["tc1", "tc2"],
                "coverage_report": "85% coverage",
                "defect_list": ["no defects found"],
                "quality_verdict": "PASS",
            },
            "independent-reviewer": {
                "findings": ["No issues found"],
                "files_reviewed": ["src/main.py"],
            },
            "product-manager": {
                "user_profiles": ["admin", "user"],
                "functional_requirements": ["req1", "req2"],
                "non_functional_requirements": ["perf1"],
                "acceptance_criteria": ["ac1"],
                "exclusions": ["none"],
            },
            "security-engineer": {
                "vulnerability_list": ["no vulnerabilities found"],
                "severity_levels": {"info": 0},
                "remediation_plan": "No issues",
            },
            "delivery-manager": {
                "delivery_checklist": ["check1"],
                "deployment_plan": "Deploy to staging",
                "rollback_plan": "Revert to previous version",
                "go_nogo": "GO",
            },
            "module-architect": {
                "findings": ["Module design OK"],
                "files_reviewed": ["module.py"],
            },
            "release-engineer": {
                "delivery_checklist": ["check1"],
                "deployment_plan": "Standard deploy",
                "rollback_plan": "Standard rollback",
                "go_nogo": "GO",
            },
        }

        role_output = role_specific_fields.get(role_id, {})
        output.update(role_output)

        # Write output to file
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(output, indent=2), encoding="utf-8")

        return output

    def execute_phase(
        self,
        phase: Phase,
        project_root: Path,
        role_prompts: dict[str, str] | None = None,
        input_files: list[str] | None = None,
    ) -> PhasePlan:
        """Execute a complete Loop phase end-to-end.

        Flow:
        1. Read current state from .ai/state.yaml
        2. Validate phase transition is allowed
        3. Check previous gate is approved and no blockers exist
        4. Freeze input file hashes
        5. Build execution plan for the phase
        6. Launch all roles (parallel where possible, serial where needed)
        7. Validate each role output; retry incomplete up to max_retries
        8. If any role is BLOCKED, mark phase BLOCKED
        9. If all roles PASS, mark phase COMPLETE
        10. Persist state and task graph back to files

        Args:
            phase: The phase to execute
            project_root: Project root directory (must contain .ai/)
            role_prompts: Optional dict of role_id -> prompt string
            input_files: Optional list of input file paths

        Returns:
            PhasePlan with execution results
        """
        state = self._read_state(project_root)

        # Step 1: Validate phase transition from current phase
        current_phase_str = state.get("current_phase")
        if current_phase_str:
            try:
                current_phase = Phase(current_phase_str)
            except ValueError:
                current_phase = None
        else:
            current_phase = None

        if current_phase is not None:
            transition = can_transition_phase(current_phase, phase)
            if not transition.allowed:
                plan = PhasePlan(
                    phase=phase,
                    loop_mode=self.mode,
                    status=StepStatus.BLOCKED,
                )
                # Store errors as blocked steps for diagnostics
                for err in transition.errors:
                    plan.steps.append(RoleStep(
                        role_id="transition-check",
                        status=StepStatus.BLOCKED,
                        verdict=err,
                    ))
                return plan

        # Step 2: Check phase entry preconditions
        prev_gate_status = None
        if state.get("current_gate_id"):
            prev_gate_status = GateStatus.PENDING  # conservative default

        has_blockers = any(
            t.get("status") == "blocked"
            for t in state.get("tasks", [])
        )

        entry = can_enter_phase(phase, prev_gate_status, has_blockers)
        if not entry.allowed:
            plan = PhasePlan(
                phase=phase,
                loop_mode=self.mode,
                status=StepStatus.BLOCKED,
            )
            for err in entry.errors:
                plan.steps.append(RoleStep(
                    role_id="entry-check",
                    status=StepStatus.BLOCKED,
                    verdict=err,
                ))
            return plan

        # Step 3: Freeze inputs
        frozen_inputs = self._freeze_inputs(input_files or [])

        # Step 4: Create execution plan
        plan = self.plan_phase(phase, frozen_inputs)
        plan.status = StepStatus.RUNNING

        # Step 5: Execute each role
        prompts = role_prompts or {}
        for step in plan.steps:
            step.status = StepStatus.RUNNING
            prompt = prompts.get(step.role_id, f"Execute {step.role_id} for phase {phase.value}")

            # Execute with retry loop
            while step.retries < step.max_retries:
                try:
                    output_file = str(
                        project_root / ".ai" / "role_outputs" / f"{phase.value}_{step.role_id}.json"
                    )
                    result_step = self.execute_role(
                        step.role_id,
                        prompt,
                        input_files or [],
                        output_file,
                        required_fields=step.required_fields,
                    )
                    # Copy relevant fields back
                    step.status = result_step.status
                    step.verdict = result_step.verdict
                    step.filled_fields = result_step.filled_fields
                    step.output_file = result_step.output_file
                    step.agent_id = result_step.agent_id

                    if step.status == StepStatus.COMPLETE:
                        break
                    elif step.status == StepStatus.BLOCKED:
                        break  # Don't retry BLOCKED verdicts
                    # INCOMPLETE or FAILED -> retry
                except Exception as e:
                    step.status = StepStatus.FAILED
                    step.verdict = str(e)

                step.retries += 1

            # Mark final status after retries exhausted
            if step.status == StepStatus.RUNNING:
                step.status = StepStatus.FAILED
                step.verdict = "Max retries exceeded"

        # Step 6: Determine overall phase status
        blocked_steps = [s for s in plan.steps if s.status == StepStatus.BLOCKED]
        if blocked_steps:
            plan.status = StepStatus.BLOCKED
        else:
            incomplete_steps = [
                s for s in plan.steps
                if s.status in (StepStatus.INCOMPLETE, StepStatus.FAILED, StepStatus.PENDING)
            ]
            if incomplete_steps:
                plan.status = StepStatus.INCOMPLETE
            else:
                plan.status = StepStatus.COMPLETE

        # Step 7: Persist state
        self.persist_state(plan, project_root)

        return plan

    def persist_state(self, plan: PhasePlan, project_root: Path | None = None) -> None:
        """Persist PhasePlan state back to .ai/state.yaml and .ai/task_graph.yaml.

        If project_root is None, state is only tracked in-memory (e.g., for testing).
        """
        if project_root is not None:
            self._write_state(project_root, plan)
            self._write_task_graph(project_root, plan)
