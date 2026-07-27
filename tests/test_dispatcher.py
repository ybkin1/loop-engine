"""Tests for LoopDispatcher — host-orchestrated manifest execution."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.dispatcher import (
    BatchResult,
    ExecutionPlan,
    ExecutionStep,
    LoopDispatcher,
)
from loop_core.subagent_manifest import (
    ManifestExecutor,
    SubagentManifest,
    SubagentResult,
    SubagentSpec,
    SubagentStatus,
)
from loop_core.agent_adapter import (
    AgentAdapter,
    AgentInput,
    AgentOutput,
    AgentStatus,
)
from hooks.zcode_adapter import ZCodeAgentAdapter


# ── Fixtures ────────────────────────────────────────────────────────────

def _make_manifest(subagents=None, **kwargs) -> SubagentManifest:
    defaults = dict(
        manifest_id="M-TEST-001",
        parent_role_id="main-thread",
        parent_task_id="T-TEST",
        phase="S4-implementation",
        subagents=subagents or [
            SubagentSpec(
                subagent_id="dev:module-a",
                role_hint="developer",
                prompt="Implement module A",
            ),
            SubagentSpec(
                subagent_id="dev:module-b",
                role_hint="developer",
                prompt="Implement module B",
            ),
        ],
        aggregation_prompt="Summarize the implementation results.",
        input_fingerprint="abc123",
    )
    defaults.update(kwargs)
    return SubagentManifest(**defaults)


# ── Tests ───────────────────────────────────────────────────────────────

class TestLoopDispatcher:
    def test_prepare_produces_valid_plan(self):
        manifest = _make_manifest()
        adapter = ZCodeAgentAdapter()
        dispatcher = LoopDispatcher()

        plan = dispatcher.prepare(manifest, adapter)

        assert isinstance(plan, ExecutionPlan)
        assert plan.manifest_id == "M-TEST-001"
        assert plan.task_id == "T-TEST"
        assert plan.total_steps == 2
        assert len(plan.batches) == 1  # both parallel → single batch
        assert len(plan.batches[0]) == 2

        for step in plan.batches[0]:
            assert isinstance(step, ExecutionStep)
            assert step.agent_input.session_id is not None
            assert step.agent_input.actor_id is not None
            assert len(step.agent_input.prompt) > 0

    def test_serial_subagents_produce_separate_batches(self):
        manifest = _make_manifest(subagents=[
            SubagentSpec(subagent_id="a", role_hint="x", prompt="A", max_parallel=False),
            SubagentSpec(subagent_id="b", role_hint="x", prompt="B", max_parallel=False),
        ])
        adapter = ZCodeAgentAdapter()
        plan = LoopDispatcher().prepare(manifest, adapter)

        # Each serial subagent gets its own batch
        assert len(plan.batches) == 2
        assert plan.total_steps == 2

    def test_invalid_manifest_raises(self):
        manifest = _make_manifest(manifest_id="")  # invalid
        adapter = ZCodeAgentAdapter()

        with pytest.raises(ValueError, match="Invalid manifest"):
            LoopDispatcher().prepare(manifest, adapter)

    def test_collect_batch_validates_and_wraps_results(self):
        manifest = _make_manifest()
        adapter = ZCodeAgentAdapter()
        dispatcher = LoopDispatcher()
        plan = dispatcher.prepare(manifest, adapter)
        batch = plan.batches[0]

        # Use actual fingerprints from the prepared AgentInputs
        raw_outputs = [
            f"Module A implemented successfully.\n\nINPUT_HASH:{batch[0].agent_input.fingerprint()}",
            f"Module B implemented successfully.\n\nINPUT_HASH:{batch[1].agent_input.fingerprint()}",
        ]

        result = dispatcher.collect_batch(batch, raw_outputs, adapter)

        assert isinstance(result, BatchResult)
        assert result.all_succeeded
        assert len(result.results) == 2
        assert all(r.status == SubagentStatus.COMPLETED for r in result.results)

    def test_collect_batch_detects_failures(self):
        manifest = _make_manifest()
        adapter = ZCodeAgentAdapter()
        dispatcher = LoopDispatcher()
        plan = dispatcher.prepare(manifest, adapter)
        batch = plan.batches[0]

        # First sub-agent: correct hash → succeeds
        # Second sub-agent: wrong hash → fails input integrity
        raw_outputs = [
            f"Module A OK.\n\nINPUT_HASH:{batch[0].agent_input.fingerprint()}",
            "Module B OK.\n\nINPUT_HASH:0000000000000000000000000000000000000000000000000000000000000000",
        ]

        result = dispatcher.collect_batch(batch, raw_outputs, adapter)

        assert not result.all_succeeded
        assert result.results[0].status == SubagentStatus.COMPLETED
        assert result.results[1].status == SubagentStatus.FAILED

    def test_batch_size_mismatch_raises(self):
        manifest = _make_manifest()
        adapter = ZCodeAgentAdapter()
        dispatcher = LoopDispatcher()
        plan = dispatcher.prepare(manifest, adapter)

        with pytest.raises(ValueError, match="Batch size mismatch"):
            dispatcher.collect_batch(plan.batches[0], ["only one output"], adapter)

    def test_finalize_produces_aggregation_prompt(self):
        manifest = _make_manifest()
        adapter = ZCodeAgentAdapter()
        dispatcher = LoopDispatcher()
        plan = dispatcher.prepare(manifest, adapter)
        batch = plan.batches[0]
        raw = [
            f"Result A.\n\nINPUT_HASH:{batch[0].agent_input.fingerprint()}",
            f"Result B.\n\nINPUT_HASH:{batch[1].agent_input.fingerprint()}",
        ]
        result = dispatcher.collect_batch(batch, raw, adapter)

        prompt = dispatcher.finalize(manifest, [result])

        assert "Aggregation Instructions" in prompt
        assert "Summarize the implementation results" in prompt
        assert "dev:module-a" in prompt
        assert "dev:module-b" in prompt
        assert "Result A" in prompt
        assert "Result B" in prompt

    def test_retry_failed_generates_retry_steps(self):
        manifest = _make_manifest()
        adapter = ZCodeAgentAdapter()
        dispatcher = LoopDispatcher()
        plan = dispatcher.prepare(manifest, adapter)
        batch = plan.batches[0]

        # Both fail with wrong hash; both have retry_on_failure=True, max_retries=2
        raw = [
            f"Module A OK.\n\nINPUT_HASH:{'0'*64}",
            f"Module B OK.\n\nINPUT_HASH:{'0'*64}",
        ]
        result = dispatcher.collect_batch(batch, raw, adapter)

        retries = dispatcher.retry_failed(result, adapter)
        # Both failed, both retry-eligible → 2 retry steps
        assert len(retries) == 2
        assert all("[RETRY]" in r.spec.prompt for r in retries)
        assert all(r.spec.max_retries == 1 for r in retries)  # decremented from 2

    def test_retry_respects_max_retries(self):
        spec = SubagentSpec(
            subagent_id="dev:module-a",
            role_hint="developer",
            prompt="Implement module A",
            max_retries=0,  # no retries left
            retry_on_failure=True,
        )
        manifest = _make_manifest(subagents=[spec])
        adapter = ZCodeAgentAdapter()
        dispatcher = LoopDispatcher()
        plan = dispatcher.prepare(manifest, adapter)
        batch = plan.batches[0]
        raw = [f"Fail.\n\nINPUT_HASH:{'0'*64}"]
        result = dispatcher.collect_batch(batch, raw, adapter)

        retries = dispatcher.retry_failed(result, adapter)
        assert len(retries) == 0  # max_retries=0 → no retry

    def test_large_manifest_with_mixed_parallelism(self):
        """Integration: 5 parallel + 2 serial sub-agents."""
        subs = []
        for i in range(5):
            subs.append(SubagentSpec(subagent_id=f"p{i}", role_hint="dev", prompt=f"P{i}", max_parallel=True))
        for i in range(2):
            subs.append(SubagentSpec(subagent_id=f"s{i}", role_hint="qa", prompt=f"S{i}", max_parallel=False))

        manifest = _make_manifest(subagents=subs, max_parallel_subagents=3)
        adapter = ZCodeAgentAdapter()
        plan = LoopDispatcher().prepare(manifest, adapter)

        # 5 parallel → batches of 3, 2 = 2 batches
        # 2 serial → 2 batches
        # Total: 4 batches
        assert len(plan.batches) == 4
        assert plan.total_steps == 7

        # First two batches are parallel (3 + 2)
        assert len(plan.batches[0]) == 3
        assert len(plan.batches[1]) == 2
        # Last two are serial
        assert len(plan.batches[2]) == 1
        assert len(plan.batches[3]) == 1
