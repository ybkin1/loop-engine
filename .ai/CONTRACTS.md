# Contracts

## Frozen Contracts

- Project root is `C:\Users\Administrator\.codex\loop-engine-lab`.
- The user owns goals, key tradeoffs, and gate approvals.
- Codex owns technical execution details inside approved task and gate boundaries.
- For implementation, review, debugging, design, or handoff work, Codex must use `$project-governor`, read current `.ai` context, and run `validate_state.py` before continuing.
- User gates are authority boundaries. Reviewer PASS, validator success, tests, and AI recommendations are evidence only; they do not replace user approval.
- Artifact lifecycle states must stay separate: `candidate`, `reviewed`, `user-approved`, `approved`, `active`, and `installed`.
- `unified-governance-architecture.v0.2.1` is `approved: true`, `active: true`, and `installed: true` only as this project's local `AGENTS.md` startup instruction file.
- `active` means governance/process reference for this project's `.ai` records only.
- `installed` required a separate installation gate naming exact target paths, expected diffs, validation, rollback, and residual risks; the current installed state was approved by `G-T-0005-INSTALL-AGENTS-MD`.
- Further `AGENTS.md` installation or modification, and any skill, MCP, agent, automation, or protocol surface installation or enablement, requires a separate explicit user gate.
- Real business projects must not be entered without a separate real-project-application gate.
- Deployment, rollback, database, permission, secret, payment, production data, and migration actions require separate explicit user approval.
- Evidence history should be superseded rather than deleted unless the user approves a destructive action.

## Open Contract Questions

- No open question remains about the already approved project-local `AGENTS.md` installation scope: it is installed only at `C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md`.
- T-0005 closeout/review rerun passed, T-0005 is completed, and T-0006 is active as a design candidate only.
- Real business project application rules are represented by the T-0006 candidate design, but they are not approved for application to any real project.
- Installation rollback exists only as candidate design in T-0005; no rollback gate has approved or executed rollback.
- No real-project discovery gate has been approved.
