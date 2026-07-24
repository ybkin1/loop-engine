# Handoff

## Current Phase

`S1-integration`

## Current Task

Task: `none`

Status: `none`

Current gate: `null`

## Main Controller Orientation

The controlling north star is not governance self-operation. The purpose of this project is to help a non-technical user with no project-management background use Qoder to produce real software products that are usable, verifiable, deployable, acceptable, maintainable, and sustainably iterable.

The user owns goals, business facts, key tradeoffs, Gate decisions, and final acceptance. Qoder owns technical execution only inside explicit authorization boundaries.

Reviews, tests, validators, audits, subagent conclusions, and Qoder judgments are evidence only. They cannot replace user approval, product acceptance, project PASS, installation, activation, implementation authorization, or real-project entry.

Governance exists to reduce user burden and delivery risk. It is a guardrail for real delivery, not the product and not the achievement by itself.

## Current Facts

- 4 个 Crewlet/superdesigndev 工具已集成为 Loop 工程辅助 skill：
  - **archlet** — 架构治理与可视化（`skills/archlet/SKILL.md` + `roles/archlet-brief.md`）
  - **loopany** — 持久记忆与自我改进（`skills/loopany/SKILL.md` + `roles/loopany-brief.md` + `.ai/loopany/` 数据目录）
  - **tools-registry** — 团队工具与密钥管理（`skills/tools-registry/SKILL.md` + `roles/tools-registry-brief.md`）
  - **loopbase** — 跨会话记忆与可观测性（`skills/loopbase/SKILL.md` + `roles/loopbase-brief.md`）
- loop-engine 主编排 skill 已更新，新 skill 注册到调度表
- 所有新 skill 设计均为 candidate 状态，需用户审批
- 2026-07-22: Phase 0 cleanup completed — fixed corrupted state.yaml, removed duplicate documents, filled TBD docs.

## Allowed Scope

- Read current governance records and verify state.
- Create tasks after user authorization.
- Use new skills (archlet/loopany/tools-registry/loopbase) when their trigger conditions are met.
- Keep the user burden low.

## Forbidden Scope

- Do not create tasks without explicit user authorization.
- Do not implement, install, activate, deploy, migrate, or enter a real project.
- Do not modify governance files without a separate explicit Gate.
- Do not infer user acceptance from any review, validator, audit, or AI statement.
- Do not auto-activate new skills without user approval of their design.

## Verified

- All governance files adapted from original Codex loop-engine-lab.
- Python checkers and guards adapted with correct path constants.
- Test suite passes with adapted paths.
- 4 new skills created with SKILL.md and role briefs.
- loop-engine dispatch table updated with new skills.
- .ai/loopany/ data directory structure created.
- state.yaml, PROGRESS.md, DECISIONS.md updated to reflect S1-integration.
- Phase 0 cleanup: state.yaml corruption fixed, duplicate documents removed.

## Unverified

- First real loop execution with new skills has not been performed.
- Qoder subagent integration with new skills has not been validated.
- archlet/codegraph/madge toolchain not installed or tested.
- loopany reflect cycle not yet triggered.
- tools-registry (treg) not installed or connected to a server.
- loopbase not installed or indexed.
- TypeScript core (src/core/) not yet validated end-to-end.

## Evidence

- None yet.

## Pending Gates And Blockers

- Pending gate: 用户审批 4 个新 skill 的设计（archlet/loopany/tools-registry/loopbase）
- Blockers: none
- Next work requires explicit user direction.

## Next Session First Step

Read the latest user request first, then `.ai/state.yaml`, this HANDOFF, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.

Check `.ai/loopany/index.md` for persistent memory state.

Run `validate_state.py`. It should pass cleanly; any error is new and must be reported.

Then recommend the concrete next route based on the user's direction.
# Handoff

## Current Phase

`S1-integration`

## Current Task

Task: `none`

Status: `none`

Current gate: `null`

## Main Controller Orientation

The controlling north star is not governance self-operation. The purpose of this project is to help a non-technical user with no project-management background use Qoder to produce real software products that are usable, verifiable, deployable, acceptable, maintainable, and sustainably iterable.

The user owns goals, business facts, key tradeoffs, Gate decisions, and final acceptance. Qoder owns technical execution only inside explicit authorization boundaries.

Reviews, tests, validators, audits, subagent conclusions, and Qoder judgments are evidence only. They cannot replace user approval, product acceptance, project PASS, installation, activation, implementation authorization, or real-project entry.

Governance exists to reduce user burden and delivery risk. It is a guardrail for real delivery, not the product and not the achievement by itself.

## Current Facts

- 4 个 Crewlet/superdesigndev 工具已集成为 Loop 工程辅助 skill：
  - **archlet** — 架构治理与可视化（`skills/archlet/SKILL.md` + `roles/archlet-brief.md`）
  - **loopany** — 持久记忆与自我改进（`skills/loopany/SKILL.md` + `roles/loopany-brief.md` + `.ai/loopany/` 数据目录）
  - **tools-registry** — 团队工具与密钥管理（`skills/tools-registry/SKILL.md` + `roles/tools-registry-brief.md`）
  - **loopbase** — 跨会话记忆与可观测性（`skills/loopbase/SKILL.md` + `roles/loopbase-brief.md`）
- loop-engine 主编排 skill 已更新，新 skill 注册到调度表
- 所有新 skill 设计均为 candidate 状态，需用户审批

## Allowed Scope

- Read current governance records and verify state.
- Create tasks after user authorization.
- Use new skills (archlet/loopany/tools-registry/loopbase) when their trigger conditions are met.
- Keep the user burden low.

## Forbidden Scope

- Do not create tasks without explicit user authorization.
- Do not implement, install, activate, deploy, migrate, or enter a real project.
- Do not modify governance files without a separate explicit Gate.
- Do not infer user acceptance from any review, validator, audit, or AI statement.
- Do not auto-activate new skills without user approval of their design.

## Verified

- All governance files adapted from original Codex loop-engine-lab.
- Python checkers and guards adapted with correct path constants.
- Test suite passes with adapted paths.
- 4 new skills created with SKILL.md and role briefs.
- loop-engine dispatch table updated with new skills.
- .ai/loopany/ data directory structure created.
- state.yaml, PROGRESS.md, DECISIONS.md updated to reflect S1-integration.

## Unverified

- First real loop execution with new skills has not been performed.
- Qoder subagent integration with new skills has not been validated.
- archlet/codegraph/madge toolchain not installed or tested.
- loopany reflect cycle not yet triggered.
- tools-registry (treg) not installed or connected to a server.
- loopbase not installed or indexed.

## Evidence

- None yet.

## Integration Impact

- New skills added as candidate capabilities to the loop-engine framework.
- No runtime behavior changed; skills are invoked only when their trigger conditions are met.
- loopany data directory ready for task capture and outcome tracking.

## Pending Gates And Blockers

- Pending gate: 用户审批 4 个新 skill 的设计（archlet/loopany/tools-registry/loopbase）
- Blockers: none
- Next work requires explicit user direction.

## Next Session First Step

Read the latest user request first, then `.ai/state.yaml`, this HANDOFF, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.

Check `.ai/loopany/index.md` for persistent memory state.

Run `validate_state.py`. It should pass cleanly; any error is new and must be reported.

Then recommend the concrete next route based on the user's direction.
# Handoff

## Current Phase

`S0-init`

## Current Task

Task: `none`

Status: `none`

Current gate: `null`

## Main Controller Orientation

The controlling north star is not governance self-operation. The purpose of this project is to help a non-technical user with no project-management background use Qoder to produce real software products that are usable, verifiable, deployable, acceptable, maintainable, and sustainably iterable.

The user owns goals, business facts, key tradeoffs, Gate decisions, and final acceptance. Qoder owns technical execution only inside explicit authorization boundaries.

Reviews, tests, validators, audits, subagent conclusions, and Qoder judgments are evidence only. They cannot replace user approval, product acceptance, project PASS, installation, activation, implementation authorization, or real-project entry.

Governance exists to reduce user burden and delivery risk. It is a guardrail for real delivery, not the product and not the achievement by itself.

## Current Facts

- Project freshly initialized on 2026-07-18 as a Qoder adaptation.
- No tasks, gates, or evidence exist yet.
- `validate_state.py` should pass cleanly.
- `audit_handoff.py` should pass.

## Allowed Scope

- Read current governance records and verify the clean initial state.
- Create the first task to validate the governance framework.
- Keep the user burden low.

## Forbidden Scope

- Do not create tasks without explicit user authorization.
- Do not implement, install, activate, deploy, migrate, or enter a real project.
- Do not modify governance files without a separate explicit Gate.
- Do not infer user acceptance from any review, validator, audit, or AI statement.

## Verified

- All governance files adapted from original Codex loop-engine-lab.
- Python checkers and guards adapted with correct path constants.
- Test suite passes with adapted paths.

## Unverified

- First real loop execution has not been performed.
- Qoder subagent integration has not been validated.

## Evidence

- None yet.

## Integration Impact

- No runtime or product integration occurred.
- Governance state is positioned for the first explicit user decision.

## Pending Gates And Blockers

- Pending gates: none.
- Blockers: none.
- Next work requires explicit user direction.

## Next Session First Step

Read the latest user request first, then `.ai/state.yaml`, this HANDOFF, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.

Run `validate_state.py`. It should pass cleanly; any error is new and must be reported.

Then recommend the concrete next route based on the user's direction.
