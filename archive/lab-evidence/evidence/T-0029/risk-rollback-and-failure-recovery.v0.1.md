# Risk, Rollback, And Failure Recovery - T-0029

## Risks

### Compatibility

Existing task files use free-form Markdown and several lifecycle labels. Strict parsing may expose historical inconsistencies. Mitigation: inventory observed states, define normalization aliases, and fail with actionable findings rather than rewriting history.

### False Blocking

New invariants may block workflows previously accepted by shallow validation. Mitigation: run validators in report-only mode against fixtures and copied project states before enforcement; activation requires a separate gate.

### Scope Expansion

Action-mode enforcement could become a broad runtime control system. Mitigation: implementation gate must limit changes to Project Governor scripts/tests/docs and prohibit installation or runtime enablement beyond the tested CLI behavior.

### Data Loss

Sequential multi-file writes can leave partial state. Mitigation: staged files, snapshot hashes, atomic replace, recovery journal, and backups limited to affected governance files.

### Historical Repair Coupling

Fixing code and repairing T-0028 in one operation could hide whether prevention works. Mitigation: separate implementation from project-state repair/migration and require explicit approval for each.

## Rollback Plan

- Capture hashes and backups of every implementation target before changes.
- Keep changes grouped by domain layer, closeout, validators, action modes, and tests.
- If validation fails, restore the exact pre-change target set from backups or version control.
- Do not roll back by regenerating HANDOFF with the old script because it can mutate task graph status.
- Preserve implementation evidence and failed test output after rollback.

## Failure Recovery Protocol

1. Stop all normal governance writes when a recovery marker exists.
2. Load the recorded pre-write snapshot and staged file list.
3. Determine whether zero, some, or all atomic replacements completed.
4. If zero completed, delete staging and retain current destinations.
5. If all completed and hashes match, finalize the journal.
6. If partially completed, choose deterministic rollback to snapshot or roll-forward to validated staged set; never guess.
7. Re-run cross-artifact validation and HANDOFF audit.
8. Record recovery evidence before clearing the marker.

## Operational Failure Messages

Every failure should name:

- stable finding/error ID.
- affected files.
- whether writes occurred.
- recovery marker location.
- safe next command.
- actions that remain prohibited.

