# Decisions

## Active Decisions

- 2026-07-06: The project is formally initialized under `.ai`, but all protocol/design outputs remain candidate until user-approved gates promote them.
- 2026-07-06: Reviewer PASS, validator success, tests, and AI recommendations remain evidence only; they do not replace user approval.
- 2026-07-07: `unified-governance-architecture.v0.2.1` is approved, active, and installed only as this project's local `AGENTS.md` startup instruction file.
- 2026-07-07: T-0005 closeout rerun passed and T-0005 is completed.
- 2026-07-07: T-0006 is active only as a design candidate for real product delivery entry; it does not approve real-project entry, implementation, deployment, rollback, or tool/protocol enablement.
- 2026-07-08: The repaired Loop engineering method candidate is baseline-approved as a reference only under `G-T-0012-METHOD-BASELINE-APPROVAL`; this does not install or enable the method, modify `AGENTS.md`, change runtime behavior, or authorize real-project application.

## Decision Log

| Date | Decision | Reason | Revisit When |
| --- | --- | --- | --- |
| 2026-07-06 | Initialize `C:\Users\Administrator\.codex\loop-engine-lab` as the project root for "Codex 一人研发团队式 Loop 软件交付系统". | The work has a stable long-running objective and needs project memory, gates, evidence, and handoff continuity. | Revisit if the project root changes or if the user approves installing/activating a protocol. |
| 2026-07-06 | Keep current work in no-write design mode. | The current task is to design Loop 工程工作模式 and 规范架构, not to install automation or enter a real business project. | Revisit only after candidate designs pass review and the user explicitly approves a next-stage gate. |
| 2026-07-06 | Save unified governance architecture Candidate v0.2.1 as T-0002 evidence only. | The user approved completing P2 and entering write-down, while still preserving candidate/approved/active/installed boundaries. | Revisit when a formal Reviewer-Auditor review is complete and the user decides whether to approve, activate, or install any artifact. |
| 2026-07-06 | Record T-0002 Reviewer-Auditor `PASS_RECOMMENDED` as review evidence only. | The formal review found no P0/P1/P2/P3 findings and no blocking residual risk, but Reviewer PASS is not a user gate. | Revisit when the user explicitly decides whether to keep, repair, promote, activate, or install the candidate. |
| 2026-07-06 | Record the user's explicit approval of T-0002 Candidate v0.2.1 as `approved` evidence only. | The user approved promotion to approved with strict limits: no active status, no installed status, no AGENTS.md install, no skill/MCP/agent/automation/protocol enablement, no real business project entry, and no production action. | Revisit only if the user grants a separate gate for activation, installation, application to a real project, deployment, or other high-risk action. |
| 2026-07-06 | Activate `unified-governance-architecture.v0.2.1` as a governance/process reference only. | The user explicitly approved activation-only with strict limits: keep `installed: false`, do not modify `AGENTS.md`, do not enable skill/MCP/agent/automation/protocol, do not enter real business projects, do not deploy or rollback, do not touch database/permission/secret/payment/production data/migration, and do not perform placeholder cleanup. | Revisit only if the user grants a separate installation, real-project-application, rollback, cleanup, or protocol/tool enablement gate. |
| 2026-07-07 | Install `unified-governance-architecture.v0.2.1` only as the project-local `AGENTS.md` startup instruction file. | The user explicitly approved `G-T-0005-INSTALL-AGENTS-MD`; installation validation passed and did not enable skill/MCP/agent/automation/protocol or enter a real project. | Revisit only if the user approves further `AGENTS.md` modification, rollback, tool/protocol enablement, or real-project application. |
| 2026-07-07 | Mark T-0005 completed after closeout rerun passed. | `G-T-0005-CLOSEOUT-REVIEW-RERUN` recorded `PASS` after stale-memory repair and marked T-0005 completed in `task_graph.yaml`. | Revisit only if T-0005 evidence is disputed or a rollback/repair gate is approved. |
| 2026-07-07 | Create T-0006 as real product delivery entry design candidate only. | The user approved `G-T-0006-DESIGN-REAL-PRODUCT-ENTRY` to design a first product discovery protocol without entering any real business project. | Revisit when the user decides whether to approve a real-project discovery gate for a named product idea or project root. |
| 2026-07-07 | Repair T-0006 candidate artifact list and stale memory wording. | The user approved `G-T-0006-REPAIR-CANDIDATE-AND-MEMORY` after review found missing artifact-list entries and stale T-0005/T-0006 status text. | Revisit when T-0006 is formally reviewed again. |
| 2026-07-08 | Baseline-approve the repaired Loop engineering method candidate as a reference only. | The user explicitly approved `G-T-0012-METHOD-BASELINE-APPROVAL` after T-0011 recommended the repaired candidate for baseline consideration. | Revisit only if the user approves a separate activation, installation, `AGENTS.md` modification, real-project application, implementation, release, or repair gate. |

## Post-Merge Decisions (2026-07-21 ~ 2026-07-22)

- 2026-07-21: Merge loop-engine-lab + loop-engine-zcode + loop-plugin into single loop-engine project under `C:\Users\Administrator\ZCodeProject\loop-engine`.
- 2026-07-21: Install loop-governance runtime (skills + hooks) via T-0021.
- 2026-07-22: Execute T-0022~T-0027 completing full S0-init → S6-delivery lifecycle.
- 2026-07-22: Independent reviewer (isolated context) found 3 P0 gaps in requirements doc → repair via T-0028.
- 2026-07-22: Harden execution layer (T-0029): role isolation via Agent tool, structured veto JSON, self-review prevention.
- 2026-07-22: Extract Loop Core as host-independent protocol layer (T-0030): 6 JSON schemas, state machine, router, enforcement levels.
- 2026-07-22: Implement ZCode Host Adapter (T-0031) honestly declaring MEDIUM enforcement (can intercept writes, cannot intercept Bash commands).
- 2026-07-22: External independent audit (7 parallel sub-agents) validated architecture and identified stale memory files.
- 2026-07-22: ENFORCEMENT_LEVEL honesty principle: ADVISORY hosts must not claim ENFORCED.
