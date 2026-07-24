"""
Subagent Manifest Protocol — Enables role agents to decompose complex tasks
into parallel sub-tasks without nested agent calls.

Architecture:
    Role Agent -> produces SubagentManifest
    Main Thread -> reads Manifest, schedules sub-agents, collects results
    Role Agent -> receives aggregated results, produces final output

Key design principles:
    1. Role Agent decides WHAT (decomposition, aggregation)
    2. Main Thread decides HOW (scheduling, parallelism)
    3. SubagentSpec is self-contained (no external context needed)
    4. Parallel-first: all subagents default to parallel execution
    5. Result validation against expected output schema
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SubagentStatus(str, Enum):
    """Execution status of a single sub-agent."""
    PENDING = "pending"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SubagentSpec:
    """Single sub-agent specification.

    Filled by the Role Agent, executed by the Main Thread.
    Each SubagentSpec is self-contained: includes all needed context.
    """
    subagent_id: str                    # Unique ID
    role_hint: str                      # Suggested agent type (general-purpose/Explore/etc.)
    prompt: str                         # Complete self-contained prompt
    input_files: list[str] = field(default_factory=list)
    expected_output_schema: dict | None = None  # Expected output format (JSON Schema)
    max_parallel: bool = True           # Whether this can run in parallel with others
    timeout_seconds: int = 300
    retry_on_failure: bool = True
    max_retries: int = 2

    def __post_init__(self):
        if not self.subagent_id or not self.subagent_id.strip():
            raise ValueError("subagent_id must not be empty")
        if not self.prompt or not self.prompt.strip():
            raise ValueError(f"prompt must not be empty for subagent '{self.subagent_id}'")
        if self.timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be positive, got {self.timeout_seconds}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {self.max_retries}")


@dataclass
class SubagentResult:
    """Sub-agent execution result."""
    subagent_id: str
    status: SubagentStatus
    output: str                         # Agent's text output
    exit_code: int | None = None
    started_at: str | None = None       # ISO 8601
    completed_at: str | None = None
    error_message: str | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubagentManifest:
    """Sub-agent manifest — the output artifact of a Role Agent.

    The Role Agent produces this manifest.
    The Main Thread reads it, schedules sub-agents, and collects results.
    Results are then handed back to the Role Agent for aggregation.
    """
    manifest_id: str
    parent_role_id: str                 # Which role produced this
    parent_task_id: str                 # In which task context
    phase: str                          # Current phase
    subagents: list[SubagentSpec]
    aggregation_prompt: str             # Aggregation instructions (for the Role Agent)
    input_fingerprint: str              # Input fingerprint (anti-tamper)
    max_parallel_subagents: int = 5     # Max parallel count

    def validate(self) -> tuple[bool, list[str]]:
        """Validate manifest completeness.

        Returns:
            (is_valid, list_of_error_messages)
        """
        errors: list[str] = []

        if not self.manifest_id or not self.manifest_id.strip():
            errors.append("manifest_id is required")
        if not self.parent_role_id or not self.parent_role_id.strip():
            errors.append("parent_role_id is required")
        if not self.parent_task_id or not self.parent_task_id.strip():
            errors.append("parent_task_id is required")
        if not self.phase or not self.phase.strip():
            errors.append("phase is required")
        if not self.aggregation_prompt or not self.aggregation_prompt.strip():
            errors.append("aggregation_prompt is required")
        if not self.input_fingerprint or not self.input_fingerprint.strip():
            errors.append("input_fingerprint is required")
        if not self.subagents:
            errors.append("subagents list must not be empty")
        if self.max_parallel_subagents < 1:
            errors.append(
                f"max_parallel_subagents must be >= 1, got {self.max_parallel_subagents}"
            )

        # Validate each SubagentSpec
        seen_ids: set[str] = set()
        for i, spec in enumerate(self.subagents):
            prefix = f"subagents[{i}]"
            if not spec.subagent_id or not spec.subagent_id.strip():
                errors.append(f"{prefix}: subagent_id is required")
            elif spec.subagent_id in seen_ids:
                errors.append(f"{prefix}: duplicate subagent_id '{spec.subagent_id}'")
            else:
                seen_ids.add(spec.subagent_id)
            if not spec.prompt or not spec.prompt.strip():
                errors.append(f"{prefix} ({spec.subagent_id}): prompt is required")
            if spec.timeout_seconds <= 0:
                errors.append(
                    f"{prefix} ({spec.subagent_id}): timeout_seconds must be positive, "
                    f"got {spec.timeout_seconds}"
                )
            if spec.max_retries < 0:
                errors.append(
                    f"{prefix} ({spec.subagent_id}): max_retries must be >= 0, "
                    f"got {spec.max_retries}"
                )

        return (len(errors) == 0, errors)

    @staticmethod
    def compute_fingerprint(
        subagents: list[SubagentSpec], aggregation_prompt: str
    ) -> str:
        """Compute an input fingerprint for integrity verification.

        The fingerprint is a SHA256 hash of the concatenated subagent specs
        and aggregation prompt, providing tamper-evident integrity.
        """
        hasher = hashlib.sha256()
        for spec in sorted(subagents, key=lambda s: s.subagent_id):
            hasher.update(spec.subagent_id.encode("utf-8"))
            hasher.update(spec.prompt.encode("utf-8"))
            hasher.update(spec.role_hint.encode("utf-8"))
            hasher.update(
                json.dumps(spec.input_files, sort_keys=True).encode("utf-8")
            )
            if spec.expected_output_schema is not None:
                hasher.update(
                    json.dumps(
                        spec.expected_output_schema, sort_keys=True
                    ).encode("utf-8")
                )
            hasher.update(str(spec.max_parallel).encode("utf-8"))
            hasher.update(str(spec.timeout_seconds).encode("utf-8"))
            hasher.update(str(spec.retry_on_failure).encode("utf-8"))
            hasher.update(str(spec.max_retries).encode("utf-8"))
        hasher.update(aggregation_prompt.encode("utf-8"))
        return hasher.hexdigest()


class ManifestExecutor:
    """Manifest executor — Main Thread uses this component to schedule sub-agents.

    Does not replace agent tools; generates call parameters that can be
    passed directly to agent tools.
    """

    def plan_execution(
        self, manifest: SubagentManifest
    ) -> list[list[SubagentSpec]]:
        """Plan execution batches considering parallelism and dependencies.

        Sub-agents with max_parallel=True are grouped into batches of up to
        max_parallel_subagents. Sub-agents with max_parallel=False each get
        their own batch (serial execution).

        Returns:
            A list of batches, where each batch is a list of SubagentSpec
            that can run in parallel.
        """
        parallel: list[SubagentSpec] = []
        serial: list[SubagentSpec] = []

        for spec in manifest.subagents:
            if spec.max_parallel:
                parallel.append(spec)
            else:
                serial.append(spec)

        batches: list[list[SubagentSpec]] = []

        # Group parallel subagents into batches
        max_parallel = manifest.max_parallel_subagents
        for i in range(0, len(parallel), max_parallel):
            batches.append(parallel[i : i + max_parallel])

        # Serial subagents each get their own batch
        for spec in serial:
            batches.append([spec])

        return batches

    def validate_result(
        self, spec: SubagentSpec, result: SubagentResult
    ) -> tuple[bool, str]:
        """Validate sub-agent output against expectations.

        Checks:
        1. Result status is COMPLETED
        2. Output is non-empty
        3. If expected_output_schema is provided, output parses as JSON
           and contains the expected top-level properties

        Returns:
            (is_valid, message)
        """
        if result.status != SubagentStatus.COMPLETED:
            return (
                False,
                f"Subagent '{spec.subagent_id}' did not complete "
                f"(status: {result.status.value})",
            )

        if not result.output or not result.output.strip():
            return (
                False,
                f"Subagent '{spec.subagent_id}' produced empty output",
            )

        if spec.expected_output_schema is not None:
            # Basic JSON Schema validation (properties check only)
            try:
                output_json = json.loads(result.output)
            except json.JSONDecodeError as e:
                return (
                    False,
                    f"Subagent '{spec.subagent_id}' output is not valid JSON: {e}",
                )

            schema_properties = spec.expected_output_schema.get("properties", {})
            if schema_properties:
                required_fields = spec.expected_output_schema.get(
                    "required", list(schema_properties.keys())
                )
                missing = [f for f in required_fields if f not in output_json]
                if missing:
                    return (
                        False,
                        f"Subagent '{spec.subagent_id}' output missing "
                        f"required fields: {missing}",
                    )

        return (True, "OK")

    def aggregate_results(
        self,
        manifest: SubagentManifest,
        results: list[SubagentResult],
    ) -> str:
        """Generate an aggregation prompt for the Role Agent.

        Creates a prompt that includes:
        - The original aggregation instructions
        - Each sub-agent's ID, status, and output

        Returns:
            A prompt string for the Role Agent to produce the final summary.
        """
        lines: list[str] = []
        lines.append("## Aggregation Instructions")
        lines.append("")
        lines.append(manifest.aggregation_prompt)
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Sub-agent Results")
        lines.append("")

        for i, result in enumerate(results, 1):
            lines.append(f"### {i}. Sub-agent: {result.subagent_id}")
            lines.append(f"Status: {result.status.value}")
            if result.error_message:
                lines.append(f"Error: {result.error_message}")
            if result.exit_code is not None:
                lines.append(f"Exit code: {result.exit_code}")
            if result.started_at:
                lines.append(f"Started: {result.started_at}")
            if result.completed_at:
                lines.append(f"Completed: {result.completed_at}")
            lines.append("")
            lines.append("**Output:**")
            lines.append("```")
            lines.append(result.output)
            lines.append("```")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(
            "Based on the above sub-agent results and the aggregation "
            "instructions, produce a consolidated summary. If any sub-agents "
            "failed, note the failures and their impact on the overall task."
        )

        return "\n".join(lines)
