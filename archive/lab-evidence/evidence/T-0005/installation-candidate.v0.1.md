# Installation Candidate v0.1

Status: candidate
Task: T-0005
Recorded at: 2026-07-07T09:43:07+08:00
Source artifact: `unified-governance-architecture.v0.2.1`
Current artifact state: `approved: true`, `active: true`, `installed: false`

## 0. Boundary Notice

This document is an installation candidate only. It does not install, enable, deploy, roll back, or apply anything.

Current T-0005 authority allows only candidate design and governance evidence updates. It does not authorize modifying `AGENTS.md`, enabling skill/MCP/agent/automation/protocol behavior, entering real business projects, deployment, rollback, database changes, permission changes, secret handling, payment actions, production data actions, or migrations.

## 1. Candidate Goal

The candidate goal is to define a future installation path for making the active governance architecture visible through a project-local startup rule file, while preserving strict boundaries and requiring a separate installation gate before any runtime/startup behavior changes.

## 2. Proposed Installation Target

Candidate target path:

```text
C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md
```

Target type:

- project-local Codex startup instruction file
- behavior-affecting surface
- requires separate installation gate before creation or modification

Target status during this candidate:

- not created
- not modified
- not installed

## 3. Proposed Installed Content

If a future installation gate approves this candidate, the proposed `AGENTS.md` content is:

````markdown
# Project Instructions

## Project Governor

For implementation, review, debugging, design, handoff, task state changes, or governance work in this project, use `$project-governor` before proceeding.

Project root:

`C:\Users\Administrator\.codex\loop-engine-lab`

Required startup steps:

1. Read the latest user request first.
2. Confirm the project root.
3. Read `.ai/state.yaml`, `.ai/HANDOFF.md`, and the current task file.
4. Run `validate_state.py`.
5. If a pending gate exists, stop and ask the user to approve or reject it.
6. Continue only inside the approved task and gate scope.

## Active Governance Artifact

`unified-governance-architecture.v0.2.1` is active only as a governance/process reference for this project's `.ai` records.

Lifecycle status after a future approved installation gate:

- approved remains true
- active remains true
- installed becomes true only after this `AGENTS.md` file is created by a separate installation gate and installation validation has passed

## Boundaries

- Do not install or enable skill, MCP, agent, automation, or protocol behavior without a separate explicit user gate.
- Do not enter real business projects without a separate explicit user gate.
- Do not deploy, roll back, change databases, change permissions, handle secrets, perform payment actions, touch production data, or run migrations without a separate explicit user gate.
- Treat reviewer PASS, validator success, tests, and AI recommendations as evidence only, not user approval.
- Keep `approved`, `active`, and `installed` lifecycle states separate.
````

## 4. Expected Diff

If the target file does not exist at installation time, expected diff:

```diff
+++ C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md
@@
+# Project Instructions
+
+## Project Governor
+
+For implementation, review, debugging, design, handoff, task state changes, or governance work in this project, use `$project-governor` before proceeding.
+
+Project root:
+
+`C:\Users\Administrator\.codex\loop-engine-lab`
+
+Required startup steps:
+
+1. Read the latest user request first.
+2. Confirm the project root.
+3. Read `.ai/state.yaml`, `.ai/HANDOFF.md`, and the current task file.
+4. Run `validate_state.py`.
+5. If a pending gate exists, stop and ask the user to approve or reject it.
+6. Continue only inside the approved task and gate scope.
+
+## Active Governance Artifact
+
+`unified-governance-architecture.v0.2.1` is active only as a governance/process reference for this project's `.ai` records.
+
+Lifecycle status after a future approved installation gate:
+
+- approved remains true
+- active remains true
+- installed becomes true only after this `AGENTS.md` file is created by a separate installation gate and installation validation has passed
+
+## Boundaries
+
+- Do not install or enable skill, MCP, agent, automation, or protocol behavior without a separate explicit user gate.
+- Do not enter real business projects without a separate explicit user gate.
+- Do not deploy, roll back, change databases, change permissions, handle secrets, perform payment actions, touch production data, or run migrations without a separate explicit user gate.
+- Treat reviewer PASS, validator success, tests, and AI recommendations as evidence only, not user approval.
+- Keep `approved`, `active`, and `installed` lifecycle states separate.
```

If the target file exists at installation time, installation must stop and produce a conflict report unless the user separately approves replacing or merging exact content.

No merge should be inferred.

## 5. Files A Future Installation Gate May Modify

A future installation gate may modify only paths explicitly named by that gate.

Candidate install-time paths:

- `C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md`
- `.ai/evidence/<task-id>/` installation execution evidence
- `.ai/evidence/T-0002/artifact-registry.unified-governance-architecture.v0.2.1.yaml`
- `.ai/gates.yaml`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`

This candidate does not modify those installation targets.

## 6. Future Changed-Path Audit

A future installation gate must name an exact allowed changed-path set before installation starts.

Minimum allowed path set for this candidate:

- `C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md`
- exact installation evidence files under a named `.ai/evidence/<installation-task-id>/`
- `.ai/evidence/T-0002/artifact-registry.unified-governance-architecture.v0.2.1.yaml`
- `.ai/gates.yaml`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`

The future installation task must record a baseline before any write:

```powershell
Get-ChildItem -LiteralPath "C:\Users\Administrator\.codex\loop-engine-lab" -Recurse -Force -File |
  Select-Object FullName,Length,LastWriteTimeUtc |
  Sort-Object FullName
```

The future installation task must record the same inventory after installation, compare before and after, and list every created, modified, and deleted path.

Validation passes only if the actual changed-path set exactly matches the installation gate's approved path set.

Validation fails if:

- any unapproved path is created, modified, or deleted
- the target `AGENTS.md` path differs from the approved path
- any real business project path appears in the changed-path audit
- skill, MCP, agent, automation, or protocol configuration appears in the changed-path audit
- deployment, rollback, database, permission, secret, payment, production data, or migration paths appear in the changed-path audit

## 7. Files Not Authorized By This Candidate

This candidate does not authorize modifying:

- any existing or future `AGENTS.md`
- skill files
- MCP configuration
- agent configuration
- automation configuration
- protocol configuration
- real business project files
- database resources
- permission settings
- secrets, passwords, tokens, or API keys
- payment systems
- production data
- migration files
- deployment or rollback targets

## 8. Future Installation Validation

Before installation:

- run `validate_state.py`
- confirm a separate installation gate exists
- confirm exact target path is approved
- confirm exact allowed changed-path set is approved
- confirm current artifact state is `approved: true`, `active: true`, `installed: false`
- inspect whether `C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md` already exists
- if `AGENTS.md` exists, stop unless the installation gate explicitly approves an exact merge or replacement
- record the pre-install changed-path audit baseline

After installation, if future gate approves it:

- confirm `AGENTS.md` exists only at the approved path
- confirm file content matches the approved candidate exactly
- run and record the post-install changed-path audit
- confirm actual changed paths exactly equal the approved path set
- confirm artifact registry is updated to `installed: true`
- confirm `gates.yaml` records the installation gate
- run `validate_state.py`
- confirm no skill/MCP/agent/automation/protocol behavior was enabled
- confirm no real business project was entered
- confirm no deployment, rollback, database, permission, secret, payment, production data, or migration action occurred

## 9. Rollback Plan

Rollback must require a separate explicit rollback gate.

If `AGENTS.md` did not exist before installation:

- remove `C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md`
- set registry `installed: false`
- record rollback evidence
- update `gates.yaml`, `PROGRESS.md`, and `HANDOFF.md`
- run `validate_state.py`

If `AGENTS.md` existed before installation:

- restore the exact pre-installation content captured in installation evidence
- set registry `installed: false`
- record rollback evidence
- update `gates.yaml`, `PROGRESS.md`, and `HANDOFF.md`
- run `validate_state.py`

No rollback is performed by this candidate.

## 10. Risks And Controls

| Risk | Impact | Control |
| --- | --- | --- |
| Candidate mistaken for installation approval | `AGENTS.md` could be created without gate | State this artifact is candidate-only and keep `installed: false` |
| Existing `AGENTS.md` overwritten | Loss of local instructions | Stop if target exists unless exact merge/replacement is approved |
| `installed: true` applied too early | Lifecycle state becomes misleading | Require post-install validation before registry update |
| Tool/protocol behavior enabled accidentally | Runtime behavior changes beyond `AGENTS.md` | Keep skill/MCP/agent/automation/protocol forbidden |
| Real business project entered accidentally | Governance work affects business files | Require separate real-project-application gate |
| Rollback under-specified | Installation may be hard to undo | Require pre-install content capture and rollback gate |
| Unapproved path modified during installation | Installation changes more than the user approved | Require before/after changed-path audit and fail validation on any unapproved path |

## 11. Residual Risks

- `AGENTS.md` startup behavior may vary by runtime surface and should be verified after future installation.
- If an existing `AGENTS.md` appears before installation, this candidate must be revised or a merge candidate must be created.
- This candidate does not test startup behavior because no installation occurs.
- This candidate does not define real-project application.
- The changed-path audit design depends on a future installation task recording complete before/after inventories before any write.

## 12. Future User Gate Wording

Future installation gate wording must be created only after this candidate is reviewed.

Draft wording for later review:

```text
批准 installation gate：按 T-0005 installation-candidate.v0.1 仅创建 C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md；
内容必须与 candidate 中 Proposed Installed Content 完全一致；
将 unified-governance-architecture.v0.2.1 标记为 installed: true 仅限该项目本地 AGENTS.md 安装；
不启用 skill/MCP/agent/automation/protocol；
不进入真实业务项目；
不部署、不 rollback、不触碰数据库/权限/密钥/支付/生产数据/迁移；
如目标 AGENTS.md 已存在则停止并返回 NEED_USER_GATE。
```

This wording is not approved by this candidate.

## 13. PASS / FAIL Criteria

PASS if:

- candidate includes exact target path
- candidate includes proposed content
- candidate includes expected diff behavior
- candidate includes changed-path audit requirements
- candidate keeps installation separate from candidate design
- candidate defines validation and rollback
- candidate preserves `installed: false` until a future installation gate

FAIL if:

- this candidate creates or modifies `AGENTS.md`
- this candidate marks anything `installed: true`
- this candidate enables skill/MCP/agent/automation/protocol
- this candidate enters a real business project
- this candidate performs deployment, rollback, database, permission, secret, payment, production data, or migration actions

## 14. Current Candidate Result

Current result after T-0005 candidate design should remain:

```yaml
approved: true
active: true
installed: false
```
