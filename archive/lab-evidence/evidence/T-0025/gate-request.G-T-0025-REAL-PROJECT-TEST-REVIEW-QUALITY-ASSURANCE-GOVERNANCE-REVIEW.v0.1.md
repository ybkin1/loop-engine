# Gate Request: G-T-0025-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REVIEW

## Gate ID

```text
G-T-0025-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REVIEW
```

## Gate Type

```text
real-project-test-review-quality-assurance-governance-review
```

## Status

```text
pending
```

## Purpose

Allow the user to decide whether Codex may perform a review-only assessment of
the T-0024 design evidence package and determine whether it is complete,
strict, executable, and suitable as a candidate for later baseline
consideration.

## Review Object

The review object is the T-0024 design evidence package only. It is not code
implementation, runtime behavior, a checker, an enabled workflow, a real
business project, deployment, release, rollback, or high-risk action.

## Allowed Before Explicit User Decision

- Create `.ai/tasks/T-0025.md`.
- Create `.ai/evidence/T-0025/`.
- Create T-0025 startup validation evidence.
- Create this T-0025 gate request evidence.
- Create T-0025 user decision packet.
- Record this gate as `pending`.
- Update `.ai/state.yaml`, `.ai/task_graph.yaml`, `.ai/gates.yaml`,
  `.ai/PROGRESS.md`, and `.ai/HANDOFF.md`.
- Run `validate_state.py` after gate registration and expect a pending gate
  blocker for T-0025.
- Stop and ask the user to approve, reject, or request repair.

## Review Scope After Explicit Approval Only

- Review whether T-0024 test review plan generation standards support real
  business projects.
- Review coverage of project manager, test manager, development manager, and
  delivery manager perspectives.
- Review adaptive strategy by project type, risk level, business requirement,
  and quality requirement.
- Review plan audit strictness against weak assertions, silent pass, false
  coverage, and broken evidence chains.
- Review boundaries for independent subagent or independent-thread testing and
  review after code completion.
- Review test report, review report, audit report, and final quality verdict
  schemas for delivery decision support.
- Review defect severity, quality release standards, and blocking standards.
- Review the traceability chain from business goal to requirement to scenario
  to code to test to defect to acceptance.
- Review real-project adaptation boundaries, risk layering, and later gate
  order.
- Review risks of over-governance, non-executability, role confusion, unclear
  gate boundaries, and treating AI recommendation as user approval.

## Required Review Inputs After Approval

- `.ai/evidence/T-0024/test-review-quality-governance-scope.v0.1.md`
- `.ai/evidence/T-0024/business-quality-role-model.v0.1.md`
- `.ai/evidence/T-0024/test-review-plan-generation-protocol.candidate.v0.1.md`
- `.ai/evidence/T-0024/test-review-plan-audit-protocol.candidate.v0.1.md`
- `.ai/evidence/T-0024/independent-subagent-test-review-execution-protocol.candidate.v0.1.md`
- `.ai/evidence/T-0024/test-review-report-and-quality-verdict-schema.candidate.v0.1.md`
- `.ai/evidence/T-0024/quality-release-gate-and-defect-severity-rules.candidate.v0.1.md`
- `.ai/evidence/T-0024/traceability-and-evidence-chain.candidate.v0.1.md`
- `.ai/evidence/T-0024/real-project-adaptation-boundaries.candidate.v0.1.md`
- `.ai/evidence/T-0024/next-gate-recommendation.v0.1.md`

## Contracts To Apply During Review

- `testing-standards.md`
- `test-plan-design.md`
- `test-execution.md`
- `test-report-output-spec.md`
- `review-gates.md`
- `review-process.md`
- `review-consistency-checklist.md`
- `agent-review-report-spec.md`
- `falsification-qa.md`
- `verification-checker.md`
- `scenario-traceability.md`
- `security-governance.md`
- `deployment-governance.md`
- `data-protection.md`

## Candidate Review Evidence After Approval Only

- `.ai/evidence/T-0025/review-scope-and-method.v0.1.md`
- `.ai/evidence/T-0025/review-findings.v0.1.md`
- `.ai/evidence/T-0025/quality-governance-review-report.v0.1.md`
- `.ai/evidence/T-0025/review-verdict.v0.1.md`
- `.ai/evidence/T-0025/next-gate-recommendation.v0.1.md`

## Review Verdicts After Approval Only

- `PASS_FOR_BASELINE_CONSIDERATION`
- `REPAIR_REQUIRED`
- `BLOCKED_BY_SCOPE_OR_MISSING_EVIDENCE`

## Forbidden Scope

- Do not treat this prompt as approval.
- Do not start the T-0025 review body while this gate is pending.
- Do not approve this gate without explicit user approval.
- Do not treat T-0024 completion, validator success, AI recommendation, tests,
  reviewer PASS, or handoff as user approval.
- Do not modify `AGENTS.md`.
- Do not implement any checker, workflow, subagent protocol, runtime behavior,
  tool behavior, hook, plugin, automation, MCP, skill, or policy.
- Do not install or enable any MCP, skill, policy guard, wrapper, automation,
  protocol, hook, plugin, or tool-entry behavior.
- Do not enter, create, or modify a real business project.
- Do not write business code.
- Do not build, deploy, release, or roll back.
- Do not change databases, permissions, secrets, payment systems, production
  data, or migrations.

## Required User Decision

The user must explicitly approve, reject, or request repair.

Exact approval phrase:

```text
批准 G-T-0025-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-REVIEW
```
