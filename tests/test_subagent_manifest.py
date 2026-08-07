"""
Unit tests for loop_core.subagent_manifest — Subagent Manifest Protocol.

Covers:
  - SubagentSpec validation (empty ID, empty prompt, invalid timeout/retries)
  - SubagentManifest.validate() — complete, missing fields, duplicate IDs
  - SubagentManifest.compute_fingerprint() — determinism, sensitivity
  - ManifestExecutor.plan_execution() — parallel batches, serial, mixed
  - ManifestExecutor.validate_result() — valid, missing fields, non-JSON, failed
  - ManifestExecutor.aggregate_results() — prompt format, multi-results
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.subagent_manifest import (
    SubagentStatus,
    SubagentSpec,
    SubagentResult,
    SubagentManifest,
    ManifestExecutor,
)


# ── Helpers ────────────────────────────────────────────────────────────

def _make_spec(
    subagent_id: str = "sa-1",
    role_hint: str = "general-purpose",
    prompt: str = "Do task X",
    **kwargs,
) -> SubagentSpec:
    defaults = {
        "input_files": [],
        "expected_output_schema": None,
        "max_parallel": True,
        "timeout_seconds": 300,
        "retry_on_failure": True,
        "max_retries": 2,
    }
    defaults.update(kwargs)
    return SubagentSpec(
        subagent_id=subagent_id, role_hint=role_hint, prompt=prompt, **defaults
    )


def _make_manifest(
    manifest_id: str = "M-001",
    parent_role_id: str = "developer",
    parent_task_id: str = "T-001",
    phase: str = "S4-implementation",
    subagents: list[SubagentSpec] | None = None,
    aggregation_prompt: str = "Summarize all results",
    input_fingerprint: str | None = None,
    max_parallel_subagents: int = 5,
) -> SubagentManifest:
    if subagents is None:
        subagents = [_make_spec("sa-1", prompt="Task 1")]
    if input_fingerprint is None:
        input_fingerprint = SubagentManifest.compute_fingerprint(
            subagents, aggregation_prompt
        )
    return SubagentManifest(
        manifest_id=manifest_id,
        parent_role_id=parent_role_id,
        parent_task_id=parent_task_id,
        phase=phase,
        subagents=subagents,
        aggregation_prompt=aggregation_prompt,
        input_fingerprint=input_fingerprint,
        max_parallel_subagents=max_parallel_subagents,
    )


def _make_result(
    subagent_id: str = "sa-1",
    status: SubagentStatus = SubagentStatus.COMPLETED,
    output: str = '{"result": "ok"}',
    **kwargs,
) -> SubagentResult:
    return SubagentResult(subagent_id=subagent_id, status=status, output=output, **kwargs)


# ═══════════════════════════════════════════════════════════════════════
# SubagentSpec validation
# ═══════════════════════════════════════════════════════════════════════

class TestSubagentSpec:
    """SubagentSpec construction and __post_init__ validation."""

    def test_valid_spec(self):
        spec = _make_spec("sa-1", "explore", "Investigate the codebase")
        assert spec.subagent_id == "sa-1"
        assert spec.role_hint == "explore"
        assert spec.prompt == "Investigate the codebase"
        assert spec.max_parallel is True
        assert spec.timeout_seconds == 300

    def test_empty_subagent_id_raises(self):
        with pytest.raises(ValueError, match="subagent_id must not be empty"):
            _make_spec(subagent_id="")

    def test_whitespace_subagent_id_raises(self):
        with pytest.raises(ValueError, match="subagent_id must not be empty"):
            _make_spec(subagent_id="   ")

    def test_empty_prompt_raises(self):
        with pytest.raises(ValueError, match="prompt must not be empty"):
            _make_spec(subagent_id="sa-1", prompt="")

    def test_whitespace_prompt_raises(self):
        with pytest.raises(ValueError, match="prompt must not be empty"):
            _make_spec(subagent_id="sa-1", prompt="   ")

    def test_negative_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            _make_spec(subagent_id="sa-1", timeout_seconds=-1)

    def test_zero_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            _make_spec(subagent_id="sa-1", timeout_seconds=0)

    def test_negative_max_retries_raises(self):
        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            _make_spec(subagent_id="sa-1", max_retries=-1)

    def test_zero_max_retries_allowed(self):
        spec = _make_spec(subagent_id="sa-1", max_retries=0)
        assert spec.max_retries == 0

    def test_default_input_files(self):
        spec = _make_spec("sa-1")
        assert spec.input_files == []

    def test_default_expected_output_schema(self):
        spec = _make_spec("sa-1")
        assert spec.expected_output_schema is None

    def test_with_output_schema(self):
        schema = {"type": "object", "properties": {"x": {"type": "string"}}}
        spec = _make_spec("sa-1", expected_output_schema=schema)
        assert spec.expected_output_schema == schema

    def test_serial_subagent(self):
        spec = _make_spec("sa-1", max_parallel=False)
        assert spec.max_parallel is False


# ═══════════════════════════════════════════════════════════════════════
# SubagentManifest.validate()
# ═══════════════════════════════════════════════════════════════════════

class TestManifestValidate:
    """SubagentManifest.validate() completeness checks."""

    def test_valid_manifest_passes(self):
        manifest = _make_manifest()
        is_valid, errors = manifest.validate()
        assert is_valid is True
        assert errors == []

    def test_valid_manifest_multiple_subagents_passes(self):
        specs = [
            _make_spec("sa-1", prompt="Task 1"),
            _make_spec("sa-2", prompt="Task 2"),
            _make_spec("sa-3", prompt="Task 3"),
        ]
        manifest = _make_manifest(subagents=specs)
        is_valid, errors = manifest.validate()
        assert is_valid is True
        assert errors == []

    def test_missing_manifest_id(self):
        manifest = _make_manifest(manifest_id="")
        is_valid, errors = manifest.validate()
        assert is_valid is False
        assert any("manifest_id" in e for e in errors)

    def test_missing_parent_role_id(self):
        manifest = _make_manifest(parent_role_id="")
        is_valid, errors = manifest.validate()
        assert is_valid is False
        assert any("parent_role_id" in e for e in errors)

    def test_missing_parent_task_id(self):
        manifest = _make_manifest(parent_task_id="")
        is_valid, errors = manifest.validate()
        assert is_valid is False
        assert any("parent_task_id" in e for e in errors)

    def test_missing_phase(self):
        manifest = _make_manifest(phase="")
        is_valid, errors = manifest.validate()
        assert is_valid is False
        assert any("phase" in e for e in errors)

    def test_missing_aggregation_prompt(self):
        manifest = _make_manifest(aggregation_prompt="")
        is_valid, errors = manifest.validate()
        assert is_valid is False
        assert any("aggregation_prompt" in e for e in errors)

    def test_missing_input_fingerprint(self):
        manifest = _make_manifest(input_fingerprint="")
        is_valid, errors = manifest.validate()
        assert is_valid is False
        assert any("input_fingerprint" in e for e in errors)

    def test_empty_subagents_list(self):
        manifest = _make_manifest(subagents=[])
        is_valid, errors = manifest.validate()
        assert is_valid is False
        assert any("subagents list must not be empty" in e for e in errors)

    def test_zero_max_parallel_subagents(self):
        manifest = _make_manifest(max_parallel_subagents=0)
        is_valid, errors = manifest.validate()
        assert is_valid is False
        assert any("max_parallel_subagents" in e for e in errors)

    def test_negative_max_parallel_subagents(self):
        manifest = _make_manifest(max_parallel_subagents=-1)
        is_valid, errors = manifest.validate()
        assert is_valid is False
        assert any("max_parallel_subagents" in e for e in errors)

    def test_duplicate_subagent_ids(self):
        specs = [
            _make_spec("dup", prompt="Task 1"),
            _make_spec("dup", prompt="Task 2"),
        ]
        manifest = _make_manifest(subagents=specs)
        is_valid, errors = manifest.validate()
        assert is_valid is False
        assert any("duplicate subagent_id" in e for e in errors)

    def test_duplicate_subagent_ids_in_validate(self):
        """Validate catches duplicates even with valid individual specs."""
        specs = [
            _make_spec("dup", prompt="Task 1"),
            _make_spec("dup", prompt="Task 2"),
        ]
        manifest = _make_manifest(subagents=specs)
        is_valid, errors = manifest.validate()
        assert is_valid is False
        assert any("duplicate subagent_id" in e for e in errors)

    def test_multiple_errors_reported(self):
        manifest = _make_manifest(
            manifest_id="",
            parent_role_id="",
            subagents=[],
            aggregation_prompt="",
            input_fingerprint="",
        )
        is_valid, errors = manifest.validate()
        assert is_valid is False
        # At least 5 distinct errors
        assert len(errors) >= 5

    def test_weighted_without_quality_pair_fails_validate(self):
        """T-0143 4.4: is_weighted=True 且 quality_pair=None → validate() 报错。

        __post_init__ 仅构造期拦截，JSON 反序列化路径可绕过（object.__new__
        不触发 __post_init__）；validate() 必须独立校验（fail-closed）。
        """
        from loop_core.subagent_manifest import SubagentSpec
        spec = _make_spec("sa-w")
        # 模拟 JSON 反序列化：绕过 __post_init__ 直接构造实例
        raw = SubagentSpec.__new__(SubagentSpec)
        for f in spec.__dataclass_fields__:
            setattr(raw, f, getattr(spec, f))
        raw.is_weighted = True
        raw.quality_pair = None
        manifest = _make_manifest(subagents=[raw])
        is_valid, errors = manifest.validate()
        assert is_valid is False
        assert any("quality_pair" in e for e in errors)

    def test_weighted_with_quality_pair_passes_validate(self):
        """T-0143 4.4: is_weighted=True 且 quality_pair 存在 → validate() 通过。"""
        from loop_core.subagent_manifest import QualityPair
        import dataclasses
        spec = _make_spec("sa-w")
        spec_w = dataclasses.replace(
            spec, is_weighted=True,
            quality_pair=QualityPair(quality_role="independent-reviewer"))
        manifest = _make_manifest(subagents=[spec_w])
        is_valid, errors = manifest.validate()
        assert is_valid is True, errors


# ═══════════════════════════════════════════════════════════════════════
# SubagentManifest.compute_fingerprint()
# ═══════════════════════════════════════════════════════════════════════

class TestFingerprint:
    """Input fingerprint computation and integrity."""

    def test_fingerprint_is_deterministic(self):
        specs = [
            _make_spec("sa-1", prompt="Task A"),
            _make_spec("sa-2", prompt="Task B"),
        ]
        fp1 = SubagentManifest.compute_fingerprint(specs, "Aggregate")
        fp2 = SubagentManifest.compute_fingerprint(specs, "Aggregate")
        assert fp1 == fp2

    def test_fingerprint_changes_with_different_prompt(self):
        specs = [_make_spec("sa-1", prompt="Task A")]
        fp1 = SubagentManifest.compute_fingerprint(specs, "Aggregate X")
        fp2 = SubagentManifest.compute_fingerprint(specs, "Aggregate Y")
        assert fp1 != fp2

    def test_fingerprint_changes_with_different_subagent(self):
        specs1 = [_make_spec("sa-1", prompt="Task A")]
        specs2 = [_make_spec("sa-1", prompt="Task B")]
        fp1 = SubagentManifest.compute_fingerprint(specs1, "Aggregate")
        fp2 = SubagentManifest.compute_fingerprint(specs2, "Aggregate")
        assert fp1 != fp2

    def test_fingerprint_changes_with_different_subagent_id(self):
        specs1 = [_make_spec("sa-1", prompt="Task")]
        specs2 = [_make_spec("sa-2", prompt="Task")]
        fp1 = SubagentManifest.compute_fingerprint(specs1, "Aggregate")
        fp2 = SubagentManifest.compute_fingerprint(specs2, "Aggregate")
        assert fp1 != fp2

    def test_fingerprint_changes_with_different_aggregation(self):
        specs = [_make_spec("sa-1", prompt="Task")]
        fp1 = SubagentManifest.compute_fingerprint(specs, "Agg A")
        fp2 = SubagentManifest.compute_fingerprint(specs, "Agg B")
        assert fp1 != fp2

    def test_fingerprint_order_independent(self):
        """Fingerprint should be the same regardless of subagent list order."""
        specs_a = [
            _make_spec("sa-2", prompt="Task B"),
            _make_spec("sa-1", prompt="Task A"),
        ]
        specs_b = [
            _make_spec("sa-1", prompt="Task A"),
            _make_spec("sa-2", prompt="Task B"),
        ]
        fp1 = SubagentManifest.compute_fingerprint(specs_a, "Aggregate")
        fp2 = SubagentManifest.compute_fingerprint(specs_b, "Aggregate")
        assert fp1 == fp2

    def test_fingerprint_includes_schema(self):
        specs1 = [_make_spec("sa-1", prompt="Task")]
        specs2 = [_make_spec(
            "sa-1", prompt="Task",
            expected_output_schema={"type": "object", "properties": {"x": {}}}
        )]
        fp1 = SubagentManifest.compute_fingerprint(specs1, "Agg")
        fp2 = SubagentManifest.compute_fingerprint(specs2, "Agg")
        assert fp1 != fp2

    def test_fingerprint_includes_max_parallel_flag(self):
        specs1 = [_make_spec("sa-1", prompt="Task", max_parallel=True)]
        specs2 = [_make_spec("sa-1", prompt="Task", max_parallel=False)]
        fp1 = SubagentManifest.compute_fingerprint(specs1, "Agg")
        fp2 = SubagentManifest.compute_fingerprint(specs2, "Agg")
        assert fp1 != fp2

    def test_fingerprint_is_hex_string(self):
        specs = [_make_spec("sa-1", prompt="Task")]
        fp = SubagentManifest.compute_fingerprint(specs, "Agg")
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)


# ═══════════════════════════════════════════════════════════════════════
# ManifestExecutor.plan_execution()
# ═══════════════════════════════════════════════════════════════════════

class TestPlanExecution:
    """Execution plan batch generation."""

    def test_single_subagent(self):
        exe = ManifestExecutor()
        manifest = _make_manifest(subagents=[_make_spec("sa-1")])
        plan = exe.plan_execution(manifest)
        assert len(plan) == 1
        assert len(plan[0]) == 1
        assert plan[0][0].subagent_id == "sa-1"

    def test_all_parallel_within_limit(self):
        exe = ManifestExecutor()
        specs = [_make_spec(f"sa-{i}") for i in range(1, 4)]  # 3 specs
        manifest = _make_manifest(subagents=specs, max_parallel_subagents=5)
        plan = exe.plan_execution(manifest)
        # All 3 should fit in one batch
        assert len(plan) == 1
        assert len(plan[0]) == 3

    def test_parallel_exceeds_max_batches(self):
        exe = ManifestExecutor()
        specs = [_make_spec(f"sa-{i}") for i in range(1, 8)]  # 7 specs
        manifest = _make_manifest(subagents=specs, max_parallel_subagents=3)
        plan = exe.plan_execution(manifest)
        # 7 specs, max 3 per batch -> 3 batches (3+3+1)
        assert len(plan) == 3
        assert len(plan[0]) == 3
        assert len(plan[1]) == 3
        assert len(plan[2]) == 1

    def test_serial_subagent_own_batch(self):
        exe = ManifestExecutor()
        specs = [
            _make_spec("sa-1", max_parallel=False),
            _make_spec("sa-2", max_parallel=False),
        ]
        manifest = _make_manifest(subagents=specs)
        plan = exe.plan_execution(manifest)
        # Each serial subagent gets its own batch
        assert len(plan) == 2
        assert len(plan[0]) == 1
        assert plan[0][0].subagent_id == "sa-1"
        assert len(plan[1]) == 1
        assert plan[1][0].subagent_id == "sa-2"

    def test_mixed_parallel_and_serial(self):
        exe = ManifestExecutor()
        specs = [
            _make_spec("sa-p1", max_parallel=True),
            _make_spec("sa-p2", max_parallel=True),
            _make_spec("sa-s1", max_parallel=False),
            _make_spec("sa-p3", max_parallel=True),
        ]
        manifest = _make_manifest(subagents=specs, max_parallel_subagents=3)
        plan = exe.plan_execution(manifest)
        # Parallel batch (3 items), then serial sa-s1 alone
        assert len(plan) == 2
        # First batch: 3 parallel specs
        assert len(plan[0]) == 3
        parallel_ids = {s.subagent_id for s in plan[0]}
        assert parallel_ids == {"sa-p1", "sa-p2", "sa-p3"}
        # Second batch: serial spec alone
        assert len(plan[1]) == 1
        assert plan[1][0].subagent_id == "sa-s1"

    def test_empty_subagents_returns_empty(self):
        exe = ManifestExecutor()
        manifest = _make_manifest(subagents=[])
        plan = exe.plan_execution(manifest)
        assert plan == []

    def test_respects_custom_max_parallel(self):
        exe = ManifestExecutor()
        specs = [_make_spec(f"sa-{i}") for i in range(1, 11)]  # 10 specs
        manifest = _make_manifest(subagents=specs, max_parallel_subagents=4)
        plan = exe.plan_execution(manifest)
        # 10 specs / 4 per batch = 3 batches (4+4+2)
        assert len(plan) == 3
        assert len(plan[0]) == 4
        assert len(plan[1]) == 4
        assert len(plan[2]) == 2


# ═══════════════════════════════════════════════════════════════════════
# ManifestExecutor.validate_result()
# ═══════════════════════════════════════════════════════════════════════

class TestValidateResult:
    """Sub-agent result validation."""

    def test_valid_result_without_schema(self):
        exe = ManifestExecutor()
        spec = _make_spec("sa-1")
        result = _make_result("sa-1", output="Some text output")
        is_valid, msg = exe.validate_result(spec, result)
        assert is_valid is True
        assert msg == "OK"

    def test_failed_result_rejected(self):
        exe = ManifestExecutor()
        spec = _make_spec("sa-1")
        result = _make_result("sa-1", status=SubagentStatus.FAILED)
        is_valid, msg = exe.validate_result(spec, result)
        assert is_valid is False
        assert "did not complete" in msg

    def test_pending_result_rejected(self):
        exe = ManifestExecutor()
        spec = _make_spec("sa-1")
        result = _make_result("sa-1", status=SubagentStatus.PENDING)
        is_valid, msg = exe.validate_result(spec, result)
        assert is_valid is False
        assert "did not complete" in msg

    def test_empty_output_rejected(self):
        exe = ManifestExecutor()
        spec = _make_spec("sa-1")
        result = _make_result("sa-1", output="")
        is_valid, msg = exe.validate_result(spec, result)
        assert is_valid is False
        assert "empty output" in msg

    def test_whitespace_output_rejected(self):
        exe = ManifestExecutor()
        spec = _make_spec("sa-1")
        result = _make_result("sa-1", output="   ")
        is_valid, msg = exe.validate_result(spec, result)
        assert is_valid is False
        assert "empty output" in msg

    def test_valid_json_output_with_schema(self):
        exe = ManifestExecutor()
        schema = {
            "type": "object",
            "properties": {"verdict": {"type": "string"}, "summary": {"type": "string"}},
            "required": ["verdict", "summary"],
        }
        spec = _make_spec("sa-1", expected_output_schema=schema)
        result = _make_result(
            "sa-1",
            output=json.dumps({"verdict": "PASS", "summary": "All good"}),
        )
        is_valid, msg = exe.validate_result(spec, result)
        assert is_valid is True
        assert msg == "OK"

    def test_missing_required_field_in_schema(self):
        exe = ManifestExecutor()
        schema = {
            "type": "object",
            "properties": {"verdict": {"type": "string"}, "summary": {"type": "string"}},
            "required": ["verdict", "summary"],
        }
        spec = _make_spec("sa-1", expected_output_schema=schema)
        result = _make_result(
            "sa-1",
            output=json.dumps({"verdict": "PASS"}),  # missing summary
        )
        is_valid, msg = exe.validate_result(spec, result)
        assert is_valid is False
        assert "missing required fields" in msg
        assert "summary" in msg

    def test_non_json_output_with_schema(self):
        exe = ManifestExecutor()
        schema = {"type": "object", "properties": {}}
        spec = _make_spec("sa-1", expected_output_schema=schema)
        result = _make_result("sa-1", output="Not valid JSON!!!")
        is_valid, msg = exe.validate_result(spec, result)
        assert is_valid is False
        assert "not valid JSON" in msg

    def test_schema_without_required_uses_all_properties(self):
        """When 'required' is not in schema, all properties are treated as required."""
        exe = ManifestExecutor()
        schema = {
            "type": "object",
            "properties": {"a": {}, "b": {}},
            # no "required" key
        }
        spec = _make_spec("sa-1", expected_output_schema=schema)
        result = _make_result("sa-1", output=json.dumps({"a": 1}))  # missing b
        is_valid, msg = exe.validate_result(spec, result)
        assert is_valid is False
        assert "b" in msg

    def test_schema_no_properties_any_json_ok(self):
        exe = ManifestExecutor()
        schema: dict = {"type": "object"}
        spec = _make_spec("sa-1", expected_output_schema=schema)
        result = _make_result("sa-1", output=json.dumps({"anything": "goes"}))
        is_valid, msg = exe.validate_result(spec, result)
        assert is_valid is True


# ═══════════════════════════════════════════════════════════════════════
# ManifestExecutor.aggregate_results()
# ═══════════════════════════════════════════════════════════════════════

class TestAggregateResults:
    """Result aggregation prompt generation."""

    def test_single_result_includes_aggregation_instructions(self):
        exe = ManifestExecutor()
        manifest = _make_manifest(aggregation_prompt="Combine all outputs")
        results = [_make_result("sa-1", output="Data from A")]
        prompt = exe.aggregate_results(manifest, results)
        assert "Combine all outputs" in prompt

    def test_single_result_includes_subagent_output(self):
        exe = ManifestExecutor()
        manifest = _make_manifest()
        results = [_make_result("sa-1", output="Data from A")]
        prompt = exe.aggregate_results(manifest, results)
        assert "Data from A" in prompt

    def test_multiple_results_all_included(self):
        exe = ManifestExecutor()
        manifest = _make_manifest(subagents=[
            _make_spec("sa-1"), _make_spec("sa-2"), _make_spec("sa-3")
        ])
        results = [
            _make_result("sa-1", output="Output 1"),
            _make_result("sa-2", output="Output 2"),
            _make_result("sa-3", output="Output 3"),
        ]
        prompt = exe.aggregate_results(manifest, results)
        assert "Output 1" in prompt
        assert "Output 2" in prompt
        assert "Output 3" in prompt

    def test_includes_subagent_ids(self):
        exe = ManifestExecutor()
        manifest = _make_manifest()
        results = [
            _make_result("alpha", output="A"),
            _make_result("beta", output="B"),
        ]
        prompt = exe.aggregate_results(manifest, results)
        assert "alpha" in prompt
        assert "beta" in prompt

    def test_includes_status_information(self):
        exe = ManifestExecutor()
        manifest = _make_manifest()
        results = [
            _make_result("sa-1", status=SubagentStatus.COMPLETED, output="OK"),
            _make_result("sa-2", status=SubagentStatus.FAILED, output="",
                         error_message="Timeout"),
        ]
        prompt = exe.aggregate_results(manifest, results)
        assert "completed" in prompt.lower()
        assert "failed" in prompt.lower()
        assert "Timeout" in prompt

    def test_includes_error_message(self):
        exe = ManifestExecutor()
        manifest = _make_manifest()
        results = [
            _make_result("sa-1", status=SubagentStatus.FAILED,
                         error_message="Connection refused", output=""),
        ]
        prompt = exe.aggregate_results(manifest, results)
        assert "Connection refused" in prompt

    def test_includes_exit_code(self):
        exe = ManifestExecutor()
        manifest = _make_manifest()
        results = [_make_result("sa-1", exit_code=1, output="")]
        prompt = exe.aggregate_results(manifest, results)
        assert "Exit code: 1" in prompt

    def test_includes_timestamps(self):
        exe = ManifestExecutor()
        manifest = _make_manifest()
        results = [_make_result(
            "sa-1",
            started_at="2026-07-23T10:00:00Z",
            completed_at="2026-07-23T10:05:00Z",
            output="Done",
        )]
        prompt = exe.aggregate_results(manifest, results)
        assert "2026-07-23T10:00:00Z" in prompt
        assert "2026-07-23T10:05:00Z" in prompt

    def test_empty_results_produces_valid_prompt(self):
        exe = ManifestExecutor()
        manifest = _make_manifest()
        prompt = exe.aggregate_results(manifest, [])
        assert "Aggregation Instructions" in prompt
        assert "Sub-agent Results" in prompt

    def test_closing_instruction_present(self):
        exe = ManifestExecutor()
        manifest = _make_manifest()
        results = [_make_result("sa-1", output="X")]
        prompt = exe.aggregate_results(manifest, results)
        assert "consolidated summary" in prompt.lower()


# ═══════════════════════════════════════════════════════════════════════
# Integration / end-to-end
# ═══════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    """Full workflow: create manifest -> validate -> plan -> execute (simulated) -> validate results -> aggregate."""

    def test_full_workflow(self):
        # 1. Role Agent creates specs
        specs = [
            SubagentSpec(
                subagent_id="explore-codebase",
                role_hint="Explore",
                prompt="Find all Python files and report their structure",
                expected_output_schema={
                    "type": "object",
                    "properties": {
                        "files": {"type": "array"},
                        "summary": {"type": "string"},
                    },
                    "required": ["files", "summary"],
                },
            ),
            SubagentSpec(
                subagent_id="check-dependencies",
                role_hint="general-purpose",
                prompt="List all external dependencies and their versions",
                expected_output_schema={
                    "type": "object",
                    "properties": {
                        "dependencies": {"type": "array"},
                        "total_count": {"type": "integer"},
                    },
                    "required": ["dependencies", "total_count"],
                },
            ),
        ]

        # 2. Compute fingerprint and create manifest
        aggregation = "Merge findings: list all files and dependencies."
        fp = SubagentManifest.compute_fingerprint(specs, aggregation)

        manifest = SubagentManifest(
            manifest_id="M-S4-001",
            parent_role_id="developer",
            parent_task_id="T-001",
            phase="S4-implementation",
            subagents=specs,
            aggregation_prompt=aggregation,
            input_fingerprint=fp,
        )

        # 3. Validate manifest
        is_valid, errors = manifest.validate()
        assert is_valid, f"Manifest should be valid, got: {errors}"

        # 4. Plan execution
        exe = ManifestExecutor()
        plan = exe.plan_execution(manifest)
        assert len(plan) == 1  # both are parallel
        assert len(plan[0]) == 2

        # 5. Simulate sub-agent execution (results)
        results = [
            SubagentResult(
                subagent_id="explore-codebase",
                status=SubagentStatus.COMPLETED,
                output=json.dumps({
                    "files": ["main.py", "utils.py"],
                    "summary": "Two Python files found",
                }),
                started_at="2026-07-23T10:00:00Z",
                completed_at="2026-07-23T10:01:00Z",
            ),
            SubagentResult(
                subagent_id="check-dependencies",
                status=SubagentStatus.COMPLETED,
                output=json.dumps({
                    "dependencies": ["requests==2.31.0", "pytest==7.4.0"],
                    "total_count": 2,
                }),
                started_at="2026-07-23T10:00:00Z",
                completed_at="2026-07-23T10:00:30Z",
            ),
        ]

        # 6. Validate each result
        for spec, result in zip(specs, results):
            ok, msg = exe.validate_result(spec, result)
            assert ok, f"Result for {spec.subagent_id} should be valid: {msg}"

        # 7. Aggregate results
        aggregate_prompt = exe.aggregate_results(manifest, results)
        assert "explore-codebase" in aggregate_prompt
        assert "check-dependencies" in aggregate_prompt
        assert "files" in aggregate_prompt
        assert "dependencies" in aggregate_prompt
        assert "Merge findings" in aggregate_prompt
