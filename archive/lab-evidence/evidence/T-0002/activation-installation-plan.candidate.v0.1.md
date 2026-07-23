# Activation / Installation Plan Candidate v0.1

Status: candidate
Proposed task id: T-0003-CANDIDATE
Source artifact: unified-governance-architecture.v0.2.1
Source artifact status: approved only as a formal basis
Active: false
Installed: false
Write authority: candidate evidence write-down only

## 0. Boundary Notice

This document is a candidate plan for later activation and installation decisions.

T-0003-CANDIDATE is only a proposed_task_id. It does not mean that `C:\Users\Administrator\.codex\loop-engine-lab\.ai\tasks\T-0003.md` exists, has been created, or has been approved for creation.

Writing this candidate document to disk does not approve, activate, install, deploy, roll back, or apply anything to a real business project.

Any later action that writes state, creates a task, marks an artifact as active, marks an artifact as installed, modifies AGENTS.md, enables a protocol/tooling surface, or enters a real business project requires a separate explicit user gate.

## 1. Must Read / Background Context

Any review, activation design, installation design, or follow-up task based on this candidate must read these exact paths first:

- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\state.yaml`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\tasks\T-0002.md`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\gates.yaml`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0002\unified-governance-architecture.candidate.v0.2.1.md`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0002\unified-governance-architecture.review-report.v0.2.1.md`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0002\unified-governance-architecture.approval.v0.2.1.md`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0002\artifact-registry.unified-governance-architecture.v0.2.1.yaml`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0002\activation-installation-plan.candidate.v0.1.md`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\PROGRESS.md`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\DECISIONS.md`

`C:\Users\Administrator\.codex\loop-engine-lab\.ai\gates.yaml` is required because the approved gate for unified-governance-architecture.v0.2.1 is recorded there.

## 2. Current Confirmed Baseline

Current project state:

- Project root: `C:\Users\Administrator\.codex\loop-engine-lab`
- Current phase: S0-discovery
- Current task id: T-0002
- Current gate id: null
- No pending gate is recorded in state.

Current artifact state for unified-governance-architecture.v0.2.1:

- candidate: retained as original evidence
- reviewed: retained via review report evidence
- user-approved: true for the scope-limited approval gate
- approved: true, meaning usable as a formal basis for later authorized work
- active: false
- installed: false

The approved gate recorded in `gates.yaml` is approval-record only. It does not authorize activation, installation, AGENTS.md installation, protocol/tool enablement, deployment, rollback, production action, or entry into a real business project.

## 3. Definition And Scope Of active

active means an approved artifact has been explicitly selected by the user as a governance and process reference for future work inside this governance project.

active scope:

- It may guide interpretation of project-governor context, task design, review criteria, handoff rules, and future governance documents inside `C:\Users\Administrator\.codex\loop-engine-lab`.
- It may be referenced by future task cards after a formal task exists and the relevant gate has been approved.
- It does not write to runtime entrypoints.
- It does not modify AGENTS.md.
- It does not install skill, MCP, agent, automation, or protocol behavior.
- It does not change Codex global behavior.
- It does not enter or affect any real business project.
- It does not deploy, roll back, change databases, change permissions, handle secrets, perform payment actions, touch production data, or run migrations.

approved does not imply active. active requires a separate explicit user gate.

## 4. Definition And Scope Of installed

installed means an artifact has been written into an effective location or configuration surface and has passed installation verification.

Examples of installed surfaces include:

- AGENTS.md or another startup rule entrypoint
- Codex global or project-level rule files
- skill files
- MCP configuration
- agent configuration
- automation configuration
- protocol definitions that are loaded or enforced
- any other executable, loaded, or behavior-changing surface

installed scope must be named by a separate installation gate. That gate must state exact target paths, exact behavior being installed, validation method, rollback method, and forbidden actions.

approved does not imply installed. active does not imply installed. installed requires a separate explicit user gate and successful installation verification.

## 5. Possible Future File Changes

This candidate itself authorizes only this candidate evidence write-down.

If a future activation-only gate is approved, possible files may include:

- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0002\artifact-registry.unified-governance-architecture.v0.2.1.yaml`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\gates.yaml`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\PROGRESS.md`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\DECISIONS.md`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md`
- a new activation evidence file under `C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0002\`

If a future formal T-0003 task is approved, possible files may include:

- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\tasks\T-0003.md`
- a new evidence directory for T-0003
- related T-0003 evidence files

Creating T-0003 is not authorized by this candidate. It requires a separate user gate.

If a future installation gate is approved, the installation plan must be written separately. It must list exact target files before any installation occurs.

## 6. Files And Actions Not Authorized

This candidate does not authorize modifying:

- any AGENTS.md
- Codex global bootstrap rules
- skill files
- MCP configuration
- agent configuration
- automation configuration
- protocol configuration
- real business project files
- source code outside the authorized governance evidence scope
- database resources
- permission settings
- secrets, passwords, tokens, or API keys
- payment systems
- production data
- migration files
- deployment or rollback targets

This candidate does not authorize changing unified-governance-architecture.v0.2.1 to active or installed.

## 7. Placeholder Cleanup Position

Known placeholder-level files include:

- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\CONTRACTS.md`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\ACCEPTANCE.md`
- `C:\Users\Administrator\.codex\loop-engine-lab\.ai\KNOWN_ISSUES.md`

Placeholder cleanup is useful but not required before an activation-only decision.

Placeholder cleanup must be treated as a separate cleanup gate unless the user explicitly approves a combined scope. It must not be silently bundled with activation or installation.

If installation is later considered, placeholder cleanup should either be completed first or recorded as an explicit residual risk in the installation candidate.

## 8. Risk Register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| approved is mistaken for active | Future agents may treat the artifact as current governing policy without user activation | Always record approved, active, and installed as separate fields |
| active is mistaken for installed | Governance reference may be treated as runtime behavior | Define active as reference-only and installed as write/load/behavior-changing |
| T-0003-CANDIDATE is mistaken for an existing task | A future session may assume `.ai\tasks\T-0003.md` exists | Use proposed_task_id wording and require exact path checks |
| AGENTS.md is installed accidentally | Startup behavior may change without gate | Keep AGENTS.md out of activation write set and require installation gate |
| skill/MCP/agent/automation/protocol is enabled accidentally | Runtime/tool behavior may change | List these as forbidden unless installation gate explicitly approves them |
| real business project is entered accidentally | Governance experiment may affect production-oriented work | Require a separate real-project-application gate |
| placeholder files are over-trusted | Future review may rely on incomplete policy memory | Treat placeholder cleanup as residual risk or separate cleanup task |

## 9. Rollback Plan

Candidate evidence write-down rollback:

- A future rollback gate may mark this candidate as superseded or rejected in a registry or follow-up evidence.
- The file should not be deleted by default because evidence history should remain auditable.
- If the user explicitly requests deletion, that is a separate destructive action gate.

Activation rollback, if activation is later approved and then must be reverted:

- Set active back to false in the relevant registry.
- Add rollback evidence.
- Update `gates.yaml`, `PROGRESS.md`, `DECISIONS.md`, and `HANDOFF.md`.
- Preserve all historical candidate, review, approval, activation, and rollback evidence.

Installation rollback is not defined here because installation is not authorized here. A future installation candidate must include its own exact rollback plan before installation can be approved.

## 10. Validation Plan

Validation for this candidate evidence write-down:

- Confirm the candidate file exists at `C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0002\activation-installation-plan.candidate.v0.1.md`.
- Run `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`.
- Confirm validation returns `[ok] state is usable`.
- Confirm unified-governance-architecture.v0.2.1 remains approved true, active false, installed false.
- Confirm no AGENTS.md, skill, MCP, agent, automation, protocol, deployment, rollback, database, permission, secret, payment, production data, migration, or real business project action occurred.

Validation for future activation-only gate:

- Confirm a user-approved activation gate exists.
- Confirm registry says approved true, active true, installed false.
- Confirm activation scope is limited to governance reference inside `C:\Users\Administrator\.codex\loop-engine-lab`.
- Confirm AGENTS.md was not modified.
- Confirm no runtime or protocol/tool surface was installed or enabled.
- Confirm no real business project was entered.

Validation for future installation gate:

- Must be defined in a separate installation candidate.
- Must include exact target paths, expected diffs, load/inspection checks, rollback checks, and non-entry checks for real business projects.

## 11. User Gate Conditions

This candidate body being written as evidence is covered only by the user's current request to output the body to a document.

Separate explicit user gate is required before:

- creating `C:\Users\Administrator\.codex\loop-engine-lab\.ai\tasks\T-0003.md`
- creating a formal T-0003 evidence directory
- writing a T-0003 task card
- marking unified-governance-architecture.v0.2.1 as active
- marking any artifact as installed
- modifying or installing AGENTS.md
- enabling skill, MCP, agent, automation, or protocol behavior
- entering a real business project
- deploying
- rolling back
- changing databases
- changing permissions
- handling secrets
- performing payment actions
- touching production data
- running migrations
- cleaning placeholder files

Recommended activation-only gate wording:

```text
批准仅将 unified-governance-architecture.v0.2.1 标记为 active，范围限于 C:\Users\Administrator\.codex\loop-engine-lab 的 .ai 治理引用；保持 installed: false；不创建 T-0003.md；不安装或修改 AGENTS.md；不启用 skill/MCP/agent/automation/protocol；不进入真实业务项目；不部署、不 rollback、不触碰数据库/权限/密钥/支付/生产数据/迁移。
```

Recommended T-0003 creation gate wording:

```text
批准创建 C:\Users\Administrator\.codex\loop-engine-lab\.ai\tasks\T-0003.md，用于正式设计 activation / installation plan；本 gate 仅允许创建任务文件和 T-0003 evidence 目录，不允许 active、installed、AGENTS.md 安装、协议启用或进入真实业务项目。
```

## 12. Preventing approved From Becoming active Or installed

All future records must keep these fields separate:

```yaml
approved: true
active: false
installed: false
```

Rules:

- Reviewer PASS is evidence only.
- Validator success is evidence only.
- User approval for approved status is not activation.
- Activation requires a separate user gate.
- Installation requires a separate user gate.
- If active is missing, assume active false.
- If installed is missing, assume installed false.
- If status fields conflict, stop with BLOCKED_AUTHORITY_CONFLICT.

## 13. Preventing Installation From Entering Real Business Projects

Even if a future installation gate is approved, installation must not automatically enter real business projects.

Required protections:

- No automatic scanning for business project roots.
- No automatic task creation in real projects.
- No automatic writing outside the approved project root.
- No automatic deployment or production integration.
- No database, permission, secret, payment, production data, or migration actions.
- No use of real business project files as installation validation targets unless separately approved.
- Any real-project application requires a separate real-project-application gate.

Installation verification must inspect only the authorized installation target. It must not use a real business project as a test subject without a separate gate.

## 14. Review Expectations

A reviewer should determine whether this candidate is suitable as a basis for a later formal activation or installation task design.

The reviewer should not treat this candidate as:

- an active rule
- an installed rule
- a task creation approval
- an AGENTS.md installation approval
- a protocol/tool enablement approval
- permission to enter a real business project

Expected review outputs:

- findings with severity P0, P1, P2, or P3
- evidence for each finding
- required repairs
- pass/fail recommendation
- residual risk
- explicit statement whether a user gate is needed before any next action

## 15. Final Boundary

This document is candidate evidence only.

It does not:

- create T-0003
- activate unified-governance-architecture.v0.2.1
- install unified-governance-architecture.v0.2.1
- install AGENTS.md
- enable skill, MCP, agent, automation, or protocol behavior
- enter a real business project
- deploy
- roll back
- touch database, permissions, secrets, payment, production data, or migrations

