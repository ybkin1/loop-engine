# Contracts

## Frozen Contracts

- Project root is `C:\Users\Administrator\.qoder-cn\loop-engine-lab`.
- The user owns goals, key tradeoffs, and gate approvals.
- Qoder owns technical execution details inside approved task and gate boundaries.
- For implementation, review, debugging, design, or handoff work, Qoder must read current `.ai` context, and run `validate_state.py` before continuing.
- User gates are authority boundary. Reviewer PASS, validator success, tests, and AI recommendations are evidence only; they do not replace user approval.
- Artifact lifecycle states must stay separate: `candidate`, `reviewed`, `user-approved`, `approved`, `active`, and `installed`.
- `active` means governance/process reference for this project's `.ai` records only.
- `installed` requires a separate installation gate naming exact target paths, expected diffs, validation, rollback, and residual risks.
- Further Skill installation or modification, and any MCP, agent, automation, or protocol surface installation or enablement, requires a separate explicit user gate.
- Real business projects must not be entered without a separate real-project-application gate.
- Deployment, rollback, database, permission, secret, payment, production data, and migration actions require separate explicit user approval.
- Evidence history should be superseded rather than deleted unless the user approves a destructive action.

## Open Contract Questions

- No open questions at initialization.
