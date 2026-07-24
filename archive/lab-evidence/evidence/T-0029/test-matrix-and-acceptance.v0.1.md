# Test Matrix And Acceptance - T-0029

## Unit Tests

| Area | Scenario | Expected |
|---|---|---|
| Task status parsing | exactly one recognized status | parsed status |
| Task status parsing | missing/duplicate/unknown status | stable error finding |
| Transition matrix | approved_not_started -> in_progress with execution record | allowed |
| Transition matrix | approved_not_started -> completed | rejected |
| Transition matrix | completed -> in_progress during closeout | rejected |
| Gate pointer | current pending gate matches current task | valid |
| Gate pointer | approved gate remains current blocker | invalid |
| Projection sync | task completed, graph completed | no change |
| Projection sync | task completed, graph in_progress | mismatch finding, no silent repair |
| Next action | approved_not_started | require explicit execute request |
| Next action | completed | ask user continue/change direction |

## Integration Tests

1. Close completed task: close_session returns success and preserves graph `completed`.
2. Close in-progress task: preserves `in_progress` and renders resume-only next action.
3. Close pending-gate task: preserves task status and renders exact decision phrases.
4. Validate T-0028-style mismatch: validate_state fails with stable inconsistency ID.
5. Audit stale HANDOFF status: audit_handoff fails.
6. Audit stale next-task suggestion: audit_handoff fails.
7. Approval recording: task becomes `approved_not_started`, not `in_progress`.
8. Execute request: explicit execution record permits transition to `in_progress`.
9. Prompt-generation-only request: no task/gate/evidence files created.
10. Read-only request: filesystem remains unchanged.

## Failure Injection Tests

- Failure before staging: no destination changes.
- Failure after HANDOFF staging but before commit: destination unchanged, staging cleaned or recoverable.
- Failure after first atomic replace: recovery journal identifies exact state and rollback/roll-forward action.
- Invalid YAML during snapshot load: fail closed without writes.
- Concurrent modification detected by hash/mtime mismatch: abort without overwriting newer state.
- Audit failure on staged HANDOFF: no commit.

## Regression Fixture

Promote the T-0029 reproduction fixture into a maintained test fixture. It must prove that completed task state cannot be reopened by closeout and that both validators detect any intentional mismatch fixture.

## Acceptance Criteria

- No closeout path changes task lifecycle state.
- T-0028-style mismatch is detected by `validate_state.py` with nonzero exit.
- HANDOFF semantic mismatch is detected by `audit_handoff.py` with nonzero exit.
- Approval and execution remain separate transitions.
- All five action modes are mutually exclusive and covered by tests.
- Generated HANDOFF contains no stale or unauthorized next-task instruction.
- Partial-write tests demonstrate deterministic recovery without silent data loss.
- Existing valid Project Governor workflows remain green.
- No behavior is installed or enabled outside the separately approved implementation scope.

