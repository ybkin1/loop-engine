# Policy Guard Wrapper Implementation Plan Candidate v0.1

Status: candidate evidence
Task: T-0022

## Objective

Plan a future policy guard / wrapper prototype that classifies requested
actions and emits decision evidence, without becoming active runtime
enforcement.

## Candidate Prototype Components

| Component | Candidate Path | Purpose |
| --- | --- | --- |
| Guard decision schema | `.ai/guards/guard_decision.schema.yaml` | Define structured guard decisions. |
| Policy guard module | `.ai/guards/policy_guard.py` | Classify action family, target paths, sensitive classes, and gate context. |
| Tool restriction policy | `.ai/policies/tool-entry-restrictions.yaml` | Map sensitive action classes to required gates. |
| Sample decisions | `.ai/tests/samples/guard-decisions/` | Demonstrate allow/deny/require-gate outcomes. |

## Normalized Decision Enum

The future prototype should use this enum consistently:

- `allow`
- `deny`
- `require_user_gate`
- `require_repair`
- `require_checker`
- `allow_decision_recording_only`

The older T-0019 wording `allow_gate_recording_only` should be treated as
superseded before implementation.

## Classification Scope

The guard should classify by effect:

- requested action family
- target project root
- target paths
- sensitive action classes
- approved gate scope
- pending gates
- required checker state

## Non-Activation Rule

The future prototype may be invoked manually in tests. It must not wrap shell,
file write, browser, MCP, plugin, or tool calls unless a later runtime/tool
enablement gate explicitly approves that behavior.
