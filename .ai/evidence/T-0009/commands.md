# T-0009 Commands And Validation Evidence

Status: evidence
Task: T-0009
Recorded at: 2026-07-07T18:55:53+08:00
Scope: review-only / repair-recommendation-only

## User Gate

The user explicitly approved:

```text
批准 G-T-0009-METHOD-CANDIDATE-REVIEW
```

## Approved Write Paths

- `.ai/tasks/T-0009.md`
- `.ai/evidence/T-0009/`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`

## Forbidden Scope

- do not continue T-0007 product sample
- do not modify Harness artifacts
- do not create a real product project
- do not enter a real business project root
- do not create or modify real business project files
- do not write business project code
- do not build, implement, deploy, or roll back
- do not modify `AGENTS.md`
- do not install or enable skill, MCP, agent, automation, or protocol behavior
- do not change global or project runtime behavior
- do not change database, permission, secret, payment, production data, or migration resources
- do not treat reviewer PASS, validator success, tests, or AI recommendations as user approval
- do not treat T-0008 candidate method as an active, baseline-approved, or installed rule

## Startup Validation

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0008
[ok] state is usable
```

## Read Commands

- Read project governor skill file.
- Confirmed project root with `Get-Location`.
- Confirmed `.ai/` exists.
- Read `.ai/state.yaml`.
- Read `.ai/HANDOFF.md`.
- Read `.ai/tasks/T-0008.md`.
- Read `.ai/gates.yaml`.
- Read `.ai/task_graph.yaml`.
- Read `.ai/PROGRESS.md`.
- Listed `.ai/evidence/T-0008/`.
- Listed Harness artifacts directory read-only.
- Read T-0008 candidate documents.
- Read Harness README headings, API headings, frontend UX headings, security headings, contract-test headings, monitoring headings, and line-count sample read-only.
- Attempted `git status --short` and `git log -1 --oneline`; workspace is not a git repository.

## Command Error Recorded

The first directory creation attempt used `New-Item -LiteralPath`, which this PowerShell environment did not accept:

```text
New-Item : A parameter cannot be found that matches parameter name 'LiteralPath'.
```

Follow-up command used `New-Item -Path` successfully.

## Completed Updates

- Created `.ai/tasks/T-0009.md`.
- Created `.ai/evidence/T-0009/commands.md`.
- Created `.ai/evidence/T-0009/review-scope.v0.1.md`.
- Created `.ai/evidence/T-0009/role-review-findings.v0.1.md`.
- Created `.ai/evidence/T-0009/governance-safety-review.v0.1.md`.
- Created `.ai/evidence/T-0009/artifact-coverage-gap-review.v0.1.md`.
- Created `.ai/evidence/T-0009/harness-depth-comparison.v0.1.md`.
- Created `.ai/evidence/T-0009/repair-recommendations.v0.1.md`.
- Created `.ai/evidence/T-0009/next-gate-recommendation.v0.1.md`.
- Updated `.ai/state.yaml` to `current_task_id: T-0009`.
- Added T-0009 to `.ai/task_graph.yaml`.
- Recorded `G-T-0009-METHOD-CANDIDATE-REVIEW` in `.ai/gates.yaml`.
- Updated `.ai/PROGRESS.md`.
- Updated `.ai/HANDOFF.md`.

## Boundary Checks

- Harness artifacts modified: no.
- Real business project entered: no.
- Real business project files modified: no.
- Product project created: no.
- Business project code written: no.
- `AGENTS.md` modified: no.
- skill/MCP/agent/automation/protocol behavior enabled: no.
- global or project runtime behavior changed: no.
- build/implementation/deploy/rollback performed: no.
- database/permission/secret/payment/production-data/migration action performed: no.

## Post-T-0009 Validation

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0009
[ok] state is usable
```

## Post-T-0009 File Checks

T-0009 evidence directory contains:

- `artifact-coverage-gap-review.v0.1.md`
- `commands.md`
- `governance-safety-review.v0.1.md`
- `harness-depth-comparison.v0.1.md`
- `next-gate-recommendation.v0.1.md`
- `repair-recommendations.v0.1.md`
- `review-scope.v0.1.md`
- `role-review-findings.v0.1.md`

Additional checks:

- `gates.yaml` pending gate search returned no `status: pending` entries.
- `AGENTS.md` was not modified by T-0009; observed `LastWriteTime` remains `2026/7/7 10:43:16`.
- Harness artifacts directory was inspected read-only.
