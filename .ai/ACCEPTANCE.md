# Acceptance

## Product Acceptance

- The project helps a user without coding or project-management background move from rough goals to usable, verifiable software delivery.
- Every material change is governed by an explicit task, gate, evidence record, and validation result.
- Codex handles technical architecture, implementation, verification, review, and handoff details inside approved boundaries.
- The user is asked only for goals, key tradeoffs, and gate decisions.
- Governance states remain auditable and do not confuse `approved`, `active`, and `installed`.
- No runtime, startup, tool, protocol, or real-project behavior changes without a separate explicit user gate.

## Task Acceptance

- Every task states user-visible outcome, verification, and evidence path.
- Every task records scope, non-goals, and forbidden actions before execution.
- The current task in `state.yaml` matches the active work.
- Required evidence is stored under `.ai/evidence/<task-id>/`.
- `validate_state.py` returns `[ok] state is usable` before and after material governance changes.
- `PROGRESS.md` and `HANDOFF.md` are updated when task state or handoff-relevant facts change.
- Any high-risk action is blocked until the user explicitly approves the relevant gate.

## T-0004 Acceptance

- `.ai/CONTRACTS.md` no longer contains placeholder-only content.
- `.ai/ACCEPTANCE.md` no longer contains placeholder-only content.
- `.ai/KNOWN_ISSUES.md` no longer contains placeholder-only content.
- T-0004 evidence records the cleanup scope, validation, changed files, and preserved boundaries.
- `installed: false` remains true.
- No `AGENTS.md`, skill, MCP, agent, automation, protocol, real-project, deployment, rollback, database, permission, secret, payment, production data, or migration action occurs.
