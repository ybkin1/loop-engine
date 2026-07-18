# Checker Catalog And Blocking Semantics Candidate v0.1

Status: candidate evidence only
Task: T-0019

## Purpose

Define a candidate checker catalog for real-project governance and how checker
results block gates.

## Checker Result Shape

```yaml
checker_run_id: <checker-id>-<task-id>-<timestamp>
checker_id: <checker-id>
task_id: T-XXXX
run_at: <ISO8601>
mode: automated | manual | hybrid
status: passed | failed | blocked | unavailable | excepted | manual_pending
target_refs:
  - <path>
summary: <short summary>
evidence_ref: <path>
gate_binding:
  - value | professional | contract | <gate id>
blocking: direct | indirect | advisory
failure_detail:
  affected_gate: <gate id or gate family>
  severity: P0 | P1 | P2 | P3
  description: <text>
  remediation_hint: <text>
manual_evidence:
  method: <text>
  result: <text>
  evidence_path: <path>
  reviewed_by: <role or agent id>
```

`failure_detail` is required for `failed` and `blocked`. `manual_evidence` is
required for `manual_pending` or `excepted` when the exception depends on manual
evidence.

## Blocking Rules

| Binding | Rule |
| --- | --- |
| direct | Any `failed`, `blocked`, `pending`, or invalid `unavailable` result blocks the bound gate. |
| indirect | Result must be referenced by the gate packet, but may be resolved by manual evidence. |
| advisory | Result records risk, but cannot be used alone to block or approve a gate. |

Checkers are evidence producers. They never approve a gate.

## Minimum Catalog

| Checker ID | Stage | Mode | Binding | Blocks | Purpose |
| --- | --- | --- | --- | --- | --- |
| `governance-state-check` | all | automated | contract | direct | Verify `.ai/state.yaml`, current task, and current gate are consistent. |
| `pending-gate-check` | all | automated | contract | direct | Fail if any gate is pending unless the latest user request is the explicit decision being recorded. |
| `required-artifact-presence-check` | S0-S10 | automated | contract | direct | Verify required stage artifacts exist. |
| `artifact-schema-check` | S1-S10 | hybrid | professional, contract | direct | Verify required artifact fields are present. |
| `traceability-closure-check` | S3-S8 | hybrid | professional, contract | direct | Detect orphan requirements, workflows, APIs, data, tests, risks, and findings. |
| `prd-baseline-completeness-check` | S3 | hybrid | value, professional | direct | Verify MVP requirements link to goals, acceptance, workflows, and tests. |
| `architecture-node-coverage-check` | S4-S6 | hybrid | professional | direct | Verify architecture nodes have ownership, interfaces, data, risks, and verification strategy. |
| `detailed-design-readiness-check` | S5-S6 | hybrid | professional | direct | Verify API, data, UX, security, observability, tests, rollout, and failure behavior are design-ready. |
| `implementation-readiness-scope-check` | S6 | automated | contract | direct | Verify allowed paths, forbidden paths, work packets, validation commands, and rollback boundary. |
| `changed-path-baseline-check` | S6-S8 | automated | contract | direct | Record and compare intended write set before code/config changes. |
| `high-risk-gate-separation-check` | all | automated | contract | direct | Verify deployment, rollback, DB, permissions, secrets, payment, production data, migrations, AGENTS.md, and runtime/tool enablement each have separate gates. |
| `security-baseline-check` | S4-S8 | hybrid | professional | direct | Verify auth, authorization, input validation, secrets, logging redaction, and sensitive data handling are represented. |
| `secret-scan-check` | S7-S9 | automated | professional | direct | Detect hardcoded tokens, passwords, private keys, or API keys. |
| `migration-safety-check` | S6-S9 | hybrid | professional, contract | direct | Verify migrations are forward-compatible, non-destructive, and separately gated. |
| `deployment-preflight-check` | S9 | hybrid | professional, contract | direct | Verify artifact, smoke, monitoring, no-go, and approval evidence before deployment. |
| `rollback-plan-check` | S9 | hybrid | professional, contract | direct | Verify rollback or forward-fix plan exists without authorizing rollback. |
| `tool-entry-authorization-check` | all | automated | contract | direct | Verify sensitive action classes have approved gate and allowed tool path. |
| `stale-handoff-check` | all | automated | contract | direct | Verify `.ai/HANDOFF.md` current task/gate/scope matches state and gates. |
| `evidence-lock-check` | stage transition | automated | contract | direct | Verify register is frozen with all direct checkers cleared before stage transition. |

## Unavailable Checker Semantics

| `on_unavailable` | Handling | Stage Impact |
| --- | --- | --- |
| `fail_closed` | Create unavailable result and require repair or explicit exception. | blocks |
| `manual_evidence` | Create manual-pending result and require structured manual evidence. | blocks until evidence exists |
| `warn` | Record advisory evidence only. | does not block |

Security, database, migration, deployment, rollback, production, payment,
permission, secret, and tool-entry checkers default to `fail_closed`.

## Non-Waivable Classes

The following may not be waived by checker exception:

- explicit user gate approval
- real-project entry gate
- AGENTS.md / rule / runtime / tool enablement gate
- deployment gate
- rollback gate
- database, permission, secret, payment, production-data, or migration gate
- P0 security rules
- hardcoded secrets
- production PII in logs or tests
- reviewer PASS treated as user approval

## Boundary

This catalog is a candidate design. No checker is implemented or enabled by
T-0019.
