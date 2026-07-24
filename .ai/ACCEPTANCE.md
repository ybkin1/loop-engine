# Acceptance

## Product Acceptance

- The project helps a user without coding or project-management background move from rough goals to usable, verifiable software delivery.
- Every material change is governed by an explicit task, gate, evidence record, and validation result.
- Qoder handles technical architecture, implementation, verification, review, and handoff details inside approved boundaries.
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
