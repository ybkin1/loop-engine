"""
LoopDispatcher — Host-orchestrated manifest executor.

Since ZCode sub-agents cannot recursively create agents (live-fire confirmed),
the three-layer Loop model uses a host-orchestrated pattern:

  1. main-thread Agent produces a SubagentManifest
  2. The host (user session) reads the manifest and calls Agent() for each spec
  3. Results are collected and fed back to main-thread for aggregation

This module provides the execution plan, validation, and aggregation wiring.
It does NOT call Agent() — that remains the host's exclusive capability.
"""
from __future__ import annotations

from dataclasses import dataclass

from loop_core.agent_adapter import AgentAdapter, AgentInput, AgentOutput
from loop_core.subagent_manifest import (
    ManifestExecutor,
    SubagentManifest,
    SubagentResult,
    SubagentSpec,
    SubagentStatus,
)


@dataclass
class ExecutionStep:
    """A single step the host must execute: call Agent() with these params."""

    step_index: int
    batch_index: int
    spec: SubagentSpec
    agent_input: AgentInput

    # Human-readable summary for logging / progress display
    description: str = ""


@dataclass
class ExecutionPlan:
    """Complete execution plan produced by the dispatcher."""

    manifest_id: str
    task_id: str
    phase: str
    total_steps: int
    batches: list[list[ExecutionStep]]

    # Metadata
    aggregation_prompt: str = ""
    input_fingerprint: str = ""


@dataclass
class BatchResult:
    """Results from executing one batch of sub-agents."""

    batch_index: int
    steps: list[ExecutionStep]
    outputs: list[AgentOutput]
    results: list[SubagentResult]

    @property
    def all_succeeded(self) -> bool:
        return all(r.status == SubagentStatus.COMPLETED for r in self.results)

    @property
    def failure_summary(self) -> str:
        failed = [r for r in self.results if r.status != SubagentStatus.COMPLETED]
        if not failed:
            return ""
        return "; ".join(
            f"{r.subagent_id}: {r.error_message or 'unknown'}" for r in failed
        )


class LoopDispatcher:
    """Host-side orchestrator for SubagentManifest execution.

    Usage (host / user session pseudo-code)::

        dispatcher = LoopDispatcher()
        plan = dispatcher.prepare(manifest, adapter)

        all_results: list[BatchResult] = []
        for batch in plan.batches:
            # The host calls Agent() for each step in the batch IN PARALLEL
            raw_outputs = []
            for step in batch:
                raw = Agent(
                    description=step.description,
                    prompt=step.agent_input.prompt,
                    subagent_type=step.spec.role_hint or "general-purpose",
                    run_in_background=False,
                )
                raw_outputs.append(raw)

            # Collect and validate
            batch_result = dispatcher.collect_batch(batch, raw_outputs, adapter)
            all_results.append(batch_result)

            if not batch_result.all_succeeded:
                # Optionally retry or abort
                break

        # Aggregate
        final_prompt = dispatcher.finalize(manifest, all_results)
        # Feed final_prompt back to main-thread
    """

    def __init__(self):
        self._executor = ManifestExecutor()

    # ── Phase 1: Prepare ───────────────────────────────────────────────

    def prepare(
        self,
        manifest: SubagentManifest,
        adapter: AgentAdapter,
    ) -> ExecutionPlan:
        """Produce a host-executable plan from a SubagentManifest.

        Validates the manifest, plans parallel batches, and prepares
        AgentInput for each sub-agent spec.
        """
        valid, errors = manifest.validate()
        if not valid:
            raise ValueError(f"Invalid manifest: {'; '.join(errors)}")

        spec_batches = self._executor.plan_execution(manifest)
        step_batches: list[list[ExecutionStep]] = []
        step_index = 0
        all_steps: list[ExecutionStep] = []

        for batch_idx, spec_batch in enumerate(spec_batches):
            steps: list[ExecutionStep] = []
            for spec in spec_batch:
                agent_input = AgentInput(
                    role_id=spec.subagent_id,
                    task_id=manifest.parent_task_id,
                    prompt=spec.prompt,
                    input_files=list(spec.input_files),
                )
                agent_input = adapter.prepare_launch(agent_input)
                step = ExecutionStep(
                    step_index=step_index,
                    batch_index=batch_idx,
                    spec=spec,
                    agent_input=agent_input,
                    description=f"{spec.subagent_id}: {spec.prompt[:80]}...",
                )
                steps.append(step)
                all_steps.append(step)
                step_index += 1
            step_batches.append(steps)

        # ── Execution-level role isolation verification ──
        # Check that developer and reviewer have different actor/session IDs
        # BEFORE any Agent is called. This catches violations at plan time.
        iso_errors = self._verify_role_isolation(all_steps)
        if iso_errors:
            raise ValueError(f"Role isolation violation: {'; '.join(iso_errors)}")

        return ExecutionPlan(
            manifest_id=manifest.manifest_id,
            task_id=manifest.parent_task_id,
            phase=manifest.phase,
            total_steps=step_index,
            batches=step_batches,
            aggregation_prompt=manifest.aggregation_prompt,
            input_fingerprint=manifest.input_fingerprint,
        )

    # ── Phase 2: Collect ────────────────────────────────────────────────

    def collect_batch(
        self,
        batch: list[ExecutionStep],
        raw_outputs: list[str],
        adapter: AgentAdapter,
    ) -> BatchResult:
        """Validate and wrap results from one batch of agent executions.

        Args:
            batch: The ExecutionSteps that were executed in this batch.
            raw_outputs: Raw text output from each Agent() call, in order.
            adapter: The AgentAdapter used for prepare_launch.

        Returns:
            BatchResult with validated SubagentResults.
        """
        if len(batch) != len(raw_outputs):
            raise ValueError(
                f"Batch size mismatch: {len(batch)} steps vs {len(raw_outputs)} outputs"
            )

        results: list[SubagentResult] = []
        outputs: list[AgentOutput] = []

        for step, raw in zip(batch, raw_outputs, strict=False):
            agent_output = adapter.collect_result(step.agent_input, raw)

            status = SubagentStatus.COMPLETED if agent_output.is_clean else SubagentStatus.FAILED
            subagent_result = SubagentResult(
                subagent_id=step.spec.subagent_id,
                status=status,
                output=agent_output.stdout,
                exit_code=agent_output.exit_code,
                started_at=agent_output.start_time,
                completed_at=agent_output.end_time,
                error_message=(
                    "; ".join(agent_output.tool_violations)
                    if agent_output.tool_violations
                    else None
                ),
            )

            # Validate against expected schema
            is_valid, msg = self._executor.validate_result(step.spec, subagent_result)
            if not is_valid:
                subagent_result.status = SubagentStatus.FAILED
                subagent_result.error_message = (
                    f"{subagent_result.error_message or ''}; Validation: {msg}"
                ).strip("; ")

            outputs.append(agent_output)
            results.append(subagent_result)

        return BatchResult(
            batch_index=batch[0].batch_index if batch else 0,
            steps=batch,
            outputs=outputs,
            results=results,
        )

    # ── Phase 3: Finalize ───────────────────────────────────────────────

    def finalize(
        self,
        manifest: SubagentManifest,
        batch_results: list[BatchResult],
    ) -> str:
        """Produce the aggregation prompt for the main-thread role agent.

        Collects all sub-agent results and generates a prompt that the
        main-thread uses to produce the final gate presentation.
        """
        all_results: list[SubagentResult] = []
        for br in batch_results:
            all_results.extend(br.results)

        return self._executor.aggregate_results(manifest, all_results)

    # ── Convenience: retry failed ───────────────────────────────────────

    def retry_failed(
        self,
        batch_result: BatchResult,
        adapter: AgentAdapter,
    ) -> list[ExecutionStep]:
        """Generate retry steps for failed sub-agents in a batch.

        Only sub-agents with retry_on_failure=True and remaining retries
        are included.
        """
        retry_steps: list[ExecutionStep] = []
        for step, result in zip(batch_result.steps, batch_result.results, strict=False):
            if result.status == SubagentStatus.COMPLETED:
                continue
            if not step.spec.retry_on_failure:
                continue
            if step.spec.max_retries <= 0:
                continue

            retry_spec = SubagentSpec(
                subagent_id=step.spec.subagent_id,
                role_hint=step.spec.role_hint,
                prompt=(
                    f"[RETRY] Previous attempt failed: {result.error_message}\n\n"
                    f"{step.spec.prompt}"
                ),
                input_files=step.spec.input_files,
                expected_output_schema=step.spec.expected_output_schema,
                max_parallel=step.spec.max_parallel,
                timeout_seconds=step.spec.timeout_seconds,
                retry_on_failure=True,
                max_retries=step.spec.max_retries - 1,
            )
            agent_input = AgentInput(
                role_id=retry_spec.subagent_id,
                task_id=step.agent_input.task_id,
                prompt=retry_spec.prompt,
                input_files=list(retry_spec.input_files),
            )
            agent_input = adapter.prepare_launch(agent_input)
            retry_steps.append(
                ExecutionStep(
                    step_index=-1,  # retry, index is informational
                    batch_index=batch_result.batch_index,
                    spec=retry_spec,
                    agent_input=agent_input,
                    description=f"[RETRY] {retry_spec.subagent_id}",
                )
            )
        return retry_steps

    # ── Role isolation verification (execution level) ──────────────────

    def _verify_role_isolation(self, all_steps: list[ExecutionStep]) -> list[str]:
        """Verify developer and reviewer have distinct execution identities.

        Checks actor_id and session_id at the execution level (after
        adapter.prepare_launch has generated them), not just at the plan
        level (SubagentSpec.subagent_id).

        This recovers the three-layer model's role isolation guarantee
        in the two-layer architecture.
        """
        errors: list[str] = []
        dev_steps = [s for s in all_steps if "dev" in s.spec.subagent_id.lower()]
        rev_steps = [s for s in all_steps if "review" in s.spec.subagent_id.lower()]

        for dev in dev_steps:
            for rev in rev_steps:
                if dev.agent_input.actor_id == rev.agent_input.actor_id:
                    errors.append(
                        f"SAME_ACTOR: developer '{dev.spec.subagent_id}' "
                        f"and reviewer '{rev.spec.subagent_id}' share "
                        f"actor_id={dev.agent_input.actor_id}"
                    )
                if dev.agent_input.session_id == rev.agent_input.session_id:
                    errors.append(
                        f"SAME_SESSION: developer '{dev.spec.subagent_id}' "
                        f"and reviewer '{rev.spec.subagent_id}' share "
                        f"session_id={dev.agent_input.session_id}"
                    )
        return errors

    # ── Build executable script (mini-loop aware) ──────────────────────

    def build_execution_script(
        self,
        manifest: SubagentManifest,
        adapter: AgentAdapter,
    ) -> dict:
        """Build a complete executable script with retry-native logic.

        Outputs a JSON structure that the session can follow step by step.
        Each batch includes retry instructions: if a step fails, retry up
        to max_retries times with the failure feedback injected into the
        prompt.

        This recovers the three-layer model's mini-loop automation in the
        two-layer architecture.
        """
        plan = self.prepare(manifest, adapter)

        script_batches = []
        for batch in plan.batches:
            batch_script = {
                "batch_index": batch[0].batch_index if batch else 0,
                "parallel": batch[0].spec.max_parallel if batch else True,
                "steps": [],
                "on_failure": {
                    "action": "retry_each_failed_separately",
                    "max_total_retries_per_step": max(
                        s.spec.max_retries for s in batch
                    ) if batch else 3,
                    "retry_strategy": "inject_failure_feedback_into_prompt",
                },
            }
            for step in batch:
                batch_script["steps"].append({
                    "subagent_id": step.spec.subagent_id,
                    "role_hint": step.spec.role_hint,
                    "prompt": step.agent_input.prompt,
                    "session_id": step.agent_input.session_id,
                    "actor_id": step.agent_input.actor_id,
                    "timeout_seconds": step.spec.timeout_seconds,
                    "max_retries": step.spec.max_retries,
                })
            script_batches.append(batch_script)

        # Collect all dev/reviewer IDs for role isolation reporting
        dev_actor_ids = []
        rev_actor_ids = []
        for batch in plan.batches:
            for step in batch:
                sid = step.spec.subagent_id.lower()
                if "dev" in sid:
                    dev_actor_ids.append(step.agent_input.actor_id)
                if "review" in sid:
                    rev_actor_ids.append(step.agent_input.actor_id)

        return {
            "manifest_id": manifest.manifest_id,
            "task_id": manifest.parent_task_id,
            "phase": manifest.phase,
            "total_batches": len(script_batches),
            "batches": script_batches,
            "aggregation": {
                "prompt": manifest.aggregation_prompt,
                "role": "main-thread",
                "description": "Call Agent('main-thread') with this prompt to aggregate all results and present gate.",
            },
            "role_isolation": {
                "verified": True,
                "developer_actor_ids": dev_actor_ids,
                "reviewer_actor_ids": rev_actor_ids,
                "distinct": len(set(dev_actor_ids) & set(rev_actor_ids)) == 0,
            },
        }
