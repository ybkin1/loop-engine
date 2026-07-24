# Contracts

## Frozen Contracts

- Project root is `C:\Users\Administrator\ZCodeProject\loop-engine`.
- The user owns goals, key tradeoffs, and gate approvals.
- AI owns technical execution details inside approved task and gate boundaries.
- For implementation, review, debugging, design, or handoff work, AI must invoke the `loop-governance` skill, read current `.ai` context, and run `.zcode/tools/validate_state.py` before continuing.
- User gates are authority boundaries. Reviewer PASS, validator success, tests, and AI recommendations are evidence only; they do not replace user approval.
- Artifact lifecycle states must stay separate: `candidate`, `reviewed`, `user-approved`, `approved`, `active`, and `installed`.
- `unified-governance-architecture.v0.2.1` is `approved: true`, `active: true`, and `installed: true` only as this project's local `AGENTS.md` startup instruction file.
- `active` means governance/process reference for this project's `.ai` records only.
- `installed` required a separate installation gate naming exact target paths, expected diffs, validation, rollback, and residual risks; the current installed state was approved by `G-T-0005-INSTALL-AGENTS-MD`.
- Further `AGENTS.md` installation or modification, and any skill, MCP, agent, automation, or protocol surface installation or enablement, requires a separate explicit user gate.
- Real business projects must not be entered without a separate real-project-application gate.
- Deployment, rollback, database, permission, secret, payment, production data, and migration actions require separate explicit user approval.
- Evidence history should be superseded rather than deleted unless the user approves a destructive action.
- Loop Core (`loop_core/`) defines host-independent protocols. Host Adapter (`loop_engine/adapters/`) implements them for ZCode (MEDIUM enforcement level).
- Role isolation is enforced: developer != reviewer, each role via isolated Agent call.
- Bash command interception is NOT available via ZCode hooks — enforcement level is honestly MEDIUM.

## Open Contract Questions

- T-0022~T-0030 completed the full S0~S6 lifecycle. Project is at S6-delivery.
- Seeded defect validation confirmed independent review catches P0 defects (3/3 planted + 6 bonus).
- Bash command bypass (echo > file, cp) is a known limitation per ENFORCEMENT_LEVEL: MEDIUM.
- No real-project discovery gate has been approved.
