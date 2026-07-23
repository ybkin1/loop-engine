# T-0005 Commands And Validation Evidence

Status: evidence
Task: T-0005
Recorded at: 2026-07-07T09:43:07+08:00
Scope: installation candidate design only

## User Gate

The user approved creating T-0005 for installation candidate design.

Allowed scope:

- read current `.ai` governance context
- create T-0005 task and evidence
- output and record installation candidate design
- update `PROGRESS.md`, `HANDOFF.md`, `gates.yaml`, `state.yaml`, and `task_graph.yaml`
- keep `installed: false`

Forbidden scope:

- do not install or modify `AGENTS.md`
- do not enable skill, MCP, agent, automation, or protocol
- do not enter any real business project
- do not deploy
- do not roll back
- do not touch database, permissions, secrets, payment, production data, or migrations

## Pre-T-0005 Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0004
[ok] state is usable
```

## Planned Updates

- Create `.ai/tasks/T-0005.md`.
- Create `.ai/evidence/T-0005/commands.md`.
- Create `.ai/evidence/T-0005/installation-candidate.v0.1.md`.
- Update `.ai/state.yaml` to `current_task_id: T-0005`.
- Add T-0005 to `.ai/task_graph.yaml`.
- Record `G-T-0005-DESIGN-INSTALLATION-CANDIDATE` in `.ai/gates.yaml`.
- Update `.ai/PROGRESS.md`.
- Update `.ai/HANDOFF.md`.

## Planned Boundary Checks

- Run `validate_state.py`.
- Run `rg -n "^\s*installed:\s*true" .ai` and expect no matches.
- Confirm no `AGENTS.md` file was created under the project root.
- Confirm `unified-governance-architecture.v0.2.1` remains `installed: false`.

## Completed Updates

- Created `.ai/tasks/T-0005.md`.
- Created `.ai/evidence/T-0005/commands.md`.
- Created `.ai/evidence/T-0005/installation-candidate.v0.1.md`.
- Updated `.ai/state.yaml` to `current_task_id: T-0005`.
- Added T-0005 to `.ai/task_graph.yaml`.
- Marked T-0004 completed in `.ai/task_graph.yaml`.
- Recorded `G-T-0005-DESIGN-INSTALLATION-CANDIDATE` in `.ai/gates.yaml`.
- Updated `.ai/PROGRESS.md`.
- Updated `.ai/HANDOFF.md`.

## Post-T-0005 Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0005
[ok] state is usable
```

## Boundary Checks

- `rg -n "^\s*installed:\s*true" .ai` returned no matches.
- `Get-ChildItem -Recurse -Filter AGENTS.md -File` returned no files.
- `.ai/evidence/T-0005/installation-candidate.v0.1.md` exists.
- `.ai/evidence/T-0002/artifact-registry.unified-governance-architecture.v0.2.1.yaml` still records `installed: false`.

## Handoff Audit

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0005
```

## Review Repair Gate

The user approved T-0005 candidate/memory repair after a review concluded `PASS_WITH_REPAIRS`.

Allowed repair scope:

- repair changed-path audit in `.ai/evidence/T-0005/installation-candidate.v0.1.md`
- repair expected diff in `.ai/evidence/T-0005/installation-candidate.v0.1.md`
- update stale T-0005 candidate wording in `.ai/CONTRACTS.md`
- update stale T-0005 candidate wording in `.ai/KNOWN_ISSUES.md`
- update necessary T-0005 evidence, `PROGRESS.md`, `HANDOFF.md`, and `gates.yaml`

Forbidden repair scope:

- do not install or modify `AGENTS.md`
- do not enable skill, MCP, agent, automation, or protocol
- do not enter any real business project
- do not deploy
- do not roll back
- do not touch database, permissions, secrets, payment, production data, or migrations
- do not clean up `task_graph.yaml`
- keep `installed: false`

## Review Repairs Completed

- Added future changed-path audit requirements to `installation-candidate.v0.1.md`.
- Replaced the abbreviated placeholder expected diff with a complete add-file diff for the proposed `AGENTS.md` content.
- Updated `.ai/CONTRACTS.md` to state that T-0005 proposes a candidate target/content/rollback, but no installation gate has approved them.
- Updated `.ai/KNOWN_ISSUES.md` to state that T-0005 candidate exists and has been repaired, but no installation gate has been approved.
- Recorded `G-T-0005-REPAIR-CANDIDATE-MEMORY` in `.ai/gates.yaml`.

## Post-Repair Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0005
[ok] state is usable
```

## Post-Repair Boundary Checks

- `audit_handoff.py` returned `[ok] handoff audit passed`.
- `rg -n "^\s*installed:\s*true" .ai` returned no matches.
- `Get-ChildItem -Recurse -Filter AGENTS.md -File` returned no files.
- Search for abbreviated diff placeholders and stale memory phrases returned no matches in the repaired candidate and memory files.
- `task_graph.yaml` was not cleaned up under this repair gate.

## Status Boundary

Current artifact status remains:

```yaml
approved: true
active: true
installed: false
```

No installation occurred.
No `AGENTS.md` file was created or modified.
No skill, MCP, agent, automation, or protocol was installed or enabled.
No real business project was entered.
No deployment, rollback, database, permission, secret, payment, production data, or migration action occurred.

## Installation Gate

The user explicitly approved `G-T-0005-INSTALL-AGENTS-MD`.

Allowed installation scope:

- create `C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md` only if it did not already exist
- write content exactly matching `installation-candidate.v0.1.md` Proposed Installed Content
- record changed-path baseline and audit
- set `unified-governance-architecture.v0.2.1` to `installed: true` only for this project-local `AGENTS.md` installation
- update T-0005 installation evidence, artifact registry, `gates.yaml`, `PROGRESS.md`, and `HANDOFF.md`

Forbidden installation scope:

- do not enable skill, MCP, agent, automation, or protocol
- do not enter any real business project
- do not deploy
- do not roll back
- do not touch database, permissions, secrets, payment, production data, or migrations

Pre-install checks:

- `validate_state.py` returned `[ok] state is usable`
- target `AGENTS.md` did not exist
- pre-install changed-path baseline was recorded at `.ai/evidence/T-0005/installation.changed-path.baseline.csv`

Installation updates completed:

- created `AGENTS.md`
- created `.ai/evidence/T-0005/installation.execution.v0.1.md`
- updated `.ai/evidence/T-0002/artifact-registry.unified-governance-architecture.v0.2.1.yaml`
- updated `.ai/gates.yaml`
- updated `.ai/PROGRESS.md`
- updated `.ai/HANDOFF.md`

Post-install validation:

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0005
[ok] state is usable
```

Content validation:

```text
AGENTS_MATCHES_CANDIDATE_WITH_FINAL_NEWLINE
```

Changed-path audit:

```text
CREATED
.ai\evidence\T-0005\installation.changed-path.baseline.csv
.ai\evidence\T-0005\installation.execution.v0.1.md
AGENTS.md
MODIFIED
.ai\evidence\T-0002\artifact-registry.unified-governance-architecture.v0.2.1.yaml
.ai\evidence\T-0005\commands.md
.ai\gates.yaml
.ai\HANDOFF.md
.ai\PROGRESS.md
DELETED
CHANGED_PATH_AUDIT_PASS
```

Post-install handoff audit:

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0005
```

## Registry Wording Repair Gate

The user explicitly approved `G-T-0005-REPAIR-REGISTRY-WORDING`.

Allowed repair scope:

- repair only the `forbidden_actions` wording about `AGENTS.md` in `.ai/evidence/T-0002/artifact-registry.unified-governance-architecture.v0.2.1.yaml`
- update necessary T-0005 evidence, `PROGRESS.md`, `HANDOFF.md`, and `gates.yaml`

Forbidden repair scope:

- do not modify `AGENTS.md`
- do not enable skill, MCP, agent, automation, or protocol
- do not enter any real business project
- do not deploy
- do not roll back
- do not touch database, permissions, secrets, payment, production data, or migrations

Registry repair completed:

- Replaced the conflicting AGENTS.md install-only `forbidden_actions` wording with `further install or modify any AGENTS.md without a separate explicit user gate`.
- Preserved `status: installed`, `approved: true`, `active: true`, and `installed: true`.
- Preserved installation scope as project-local `AGENTS.md` only.

Post-registry-repair validation:

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0005
[ok] state is usable
```

Post-registry-repair handoff audit:

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0005
```

Registry wording check:

```text
rg -n "^\s*- install AGENTS\.md$" .ai\evidence\T-0002\artifact-registry.unified-governance-architecture.v0.2.1.yaml
```

returned no matches.

Current registry status check:

```text
7:status: installed
11:approved: true
12:active: true
13:installed: true
46:  - further install or modify any AGENTS.md without a separate explicit user gate
```

`AGENTS.md` unchanged check:

```text
SHA256 DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
```

## Closeout Review Gate

The user explicitly approved `G-T-0005-CLOSEOUT-REVIEW`.

Allowed closeout scope:

- read installed `AGENTS.md`, current `.ai` state, T-0005 task/gates/evidence, artifact registry, and stable project memory
- run `validate_state.py`
- run `audit_handoff.py`
- create `.ai/evidence/T-0005/closeout-review.v0.1.md`
- update this commands file, `PROGRESS.md`, `HANDOFF.md`, and `gates.yaml`
- mark T-0005 completed in `task_graph.yaml` only if review passes

Forbidden closeout scope:

- do not modify `AGENTS.md`
- do not create T-0006
- do not enter a real business project
- do not enable skill/MCP/agent/automation/protocol
- do not deploy or roll back
- do not touch database, permission, secret, payment, production data, or migration resources
- do not perform historical `task_graph.yaml` cleanup without a separate gate

Pre-closeout validation:

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0005
[ok] state is usable
```

Pre-closeout handoff audit:

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0005
```

AGENTS.md content validation:

```text
AGENTS_SHA256 DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
MATCHES_CANDIDATE_WITH_FINAL_NEWLINE True
AGENTS_PATH AGENTS.md
```

Stale memory search:

```text
.ai\KNOWN_ISSUES.md:5:- T-0005 installation candidate exists and has been repaired for review, but no installation gate has been approved. `installed` must remain false.
.ai\KNOWN_ISSUES.md:6:- `AGENTS.md` is proposed as a candidate installation target, but it is not installed, modified, or approved for creation.
.ai\CONTRACTS.md:11:- `unified-governance-architecture.v0.2.1` is `approved: true`, `active: true`, and `installed: false`.
.ai\CONTRACTS.md:21:- T-0005 proposes `C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md` as an installation candidate target, but no installation gate has approved that target.
.ai\CONTRACTS.md:22:- T-0005 proposes candidate `AGENTS.md` content, but no installation gate has approved creating, modifying, merging, or replacing `AGENTS.md`.
.ai\CONTRACTS.md:24:- Installation rollback exists only as candidate design in T-0005; no rollback gate or installation gate has approved it.
```

Closeout result:

```text
FAIL_BLOCKED_BY_STALE_MEMORY
```

The installed `AGENTS.md` review passes, but T-0005 closeout does not pass because `.ai/CONTRACTS.md` and `.ai/KNOWN_ISSUES.md` still contain stale pre-installation statements that contradict the approved installation gate, registry, evidence, and handoff.

Task graph decision:

- T-0005 was not marked completed.
- No historical `task_graph.yaml` cleanup was performed.

Recommended next step:

- request a narrow repair gate for stale `.ai/CONTRACTS.md` and `.ai/KNOWN_ISSUES.md`
- rerun T-0005 closeout/review
- if the rerun passes, enter T-0006 with the target `真实产品交付入口设计 / first product discovery protocol / real-project application candidate`

Post-closeout validation after evidence and handoff updates:

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0005
[ok] state is usable
```

Post-closeout handoff audit after evidence and handoff updates:

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0005
```

## Stale Memory Repair Gate

The user explicitly approved `G-T-0005-REPAIR-STALE-MEMORY`.

Allowed repair scope:

- update `.ai/CONTRACTS.md`
- update `.ai/KNOWN_ISSUES.md`
- record this repair gate in `.ai/gates.yaml`
- update this commands file
- update `.ai/PROGRESS.md`
- update `.ai/HANDOFF.md`
- run `validate_state.py`
- run `audit_handoff.py`

Forbidden repair scope:

- do not modify `AGENTS.md`
- do not create T-0006
- do not enter a real business project
- do not enable skill/MCP/agent/automation/protocol
- do not deploy or roll back
- do not touch database, permission, secret, payment, production data, or migration resources
- do not perform historical `task_graph.yaml` cleanup
- do not mark T-0005 completed

Pre-repair validation:

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0005
[ok] state is usable
```

Repair completed:

- Updated `.ai/CONTRACTS.md` to record `unified-governance-architecture.v0.2.1` as `installed: true` only for this project's local `AGENTS.md` startup instruction file.
- Updated `.ai/CONTRACTS.md` open questions so the already approved project-local `AGENTS.md` installation is no longer described as unapproved.
- Updated `.ai/KNOWN_ISSUES.md` so it no longer claims no installation gate exists or that `installed` must remain false.
- Preserved unresolved boundaries: no real-project application is designed or approved; rollback is not approved or executed; T-0005 closeout/review must be rerun before completion or T-0006.
- Recorded `G-T-0005-REPAIR-STALE-MEMORY` in `.ai/gates.yaml`.
- Did not modify `AGENTS.md`.
- Did not create T-0006.
- Did not update `task_graph.yaml`.

Post-repair stale phrase check:

```text
rg -n "installed: false|no installation gate|not installed|not approved for creation|installed` must remain false|AGENTS.md.*not installed|no .*approved creating" ".ai\CONTRACTS.md" ".ai\KNOWN_ISSUES.md"
```

returned no matches.

Post-repair validation:

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0005
[ok] state is usable
```

Post-repair handoff audit:

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0005
```

Boundary checks:

```text
AGENTS.md SHA256 DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
T-0005 status remains in_progress in .ai/task_graph.yaml
```

## Closeout Review Rerun Gate

The user explicitly approved rerunning `G-T-0005-CLOSEOUT-REVIEW`.

Recorded rerun gate ID:

```text
G-T-0005-CLOSEOUT-REVIEW-RERUN
```

Allowed rerun scope:

- rerun T-0005 closeout/review
- review repaired `.ai/CONTRACTS.md` and `.ai/KNOWN_ISSUES.md`
- review `AGENTS.md`, artifact registry, gates, commands evidence, `PROGRESS.md`, `HANDOFF.md`, and `task_graph.yaml`
- if review passes, mark T-0005 completed
- record closeout rerun evidence
- update this commands file, `gates.yaml`, `PROGRESS.md`, `HANDOFF.md`, and `task_graph.yaml`

Forbidden rerun scope:

- do not modify `AGENTS.md`
- do not create T-0006
- do not enter a real business project
- do not enable skill/MCP/agent/automation/protocol
- do not deploy or roll back
- do not touch database, permission, secret, payment, production data, or migration resources

Pre-rerun validation:

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0005
[ok] state is usable
```

Rerun review checks:

```text
AGENTS_SHA256 DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
MATCHES_CANDIDATE_WITH_FINAL_NEWLINE True
AGENTS_PATH AGENTS.md
stale phrase search in CONTRACTS.md and KNOWN_ISSUES.md returned no matches
artifact registry status: installed / approved true / active true / installed true
G-T-0005-REPAIR-STALE-MEMORY recorded
commands evidence contains closeout blocker and stale-memory repair history
```

Closeout rerun result:

```text
PASS
```

Completed updates:

- Created `.ai/evidence/T-0005/closeout-review.rerun.v0.1.md`.
- Recorded `G-T-0005-CLOSEOUT-REVIEW-RERUN` in `.ai/gates.yaml`.
- Marked T-0005 `completed` in `.ai/task_graph.yaml`.
- Updated `.ai/PROGRESS.md`.
- Updated `.ai/HANDOFF.md`.
- Did not modify `AGENTS.md`.
- Did not create T-0006.

Post-rerun validation:

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0005
[ok] state is usable
```

Post-rerun handoff audit:

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0005
```

Post-rerun boundary checks:

```text
AGENTS.md SHA256 DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
.ai/tasks/T-0006.md exists: False
.ai/task_graph.yaml T-0005 status: completed
stale phrase search in CONTRACTS.md and KNOWN_ISSUES.md: no matches
```
