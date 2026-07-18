# T-0034 Design Repair Commands v0.2

This is truthful execution evidence, including failed patch attempts and recovery.

## Startup And Preflight

Commands:

    python "C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py" "C:\Users\Administrator\.codex\loop-engine-lab"
    python "C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py" "C:\Users\Administrator\.codex\loop-engine-lab"

Both exited 2 with exactly the six preserved historical mismatches: T-0002, T-0004, T-0005, T-0007, T-0009, and T-0028.

Preflight Python/YAML/hash checks confirmed: Gate approved, exact approval record present, execution previously not started, 14 targets absent, 15 immutable evidence hashes matched, no pending Gate, and independent review/closeout unauthorized.

## Writes

Target writes used the Codex apply-patch entry:

    codex.exe --codex-run-as-apply-patch <unified-patch>

PowerShell multiline native-argument handling rejected several machine-catalog patch attempts with: Invalid patch: The last line of the patch must be '*** End Patch'. No partial write occurred for those failures. The same apply-patch entry was invoked directly through Node child_process.spawnSync and succeeded. A temporary TEST-MARKER used to prove the patch channel was removed in the immediately following patch.

## Deterministic Checks

Inline read-only Python checks performed:

- strict UTF-8 decoding;
- canonical payload SHA-256 recomputation;
- exact WS-01..08, OUT-01..09, and AC-01..12 counts;
- 17/17 itemized coverage rows;
- referenced checker/adversarial ID set equality;
- JSON parse for common checker examples and all 16 golden vectors;
- immutable evidence, candidate, global script, task, and task-graph hashes;
- changed-path containment and independent-review artifact absence.

The design-level checker exited 0 with all checks PASS. Final post-projection validator/audit outputs are appended after governance projection update.

## Post-Projection Governance Validation

validate_state.py exited 2 and reported only these preserved errors:

- T-0002 task=active task_graph=in_progress
- T-0004 task=active task_graph=completed
- T-0005 task=active task_graph=completed
- T-0007 task=active task_graph=in_progress
- T-0009 task=in_progress task_graph=completed
- T-0028 task=completed task_graph=in_progress

audit_handoff.py exited 2 and reported the same six historical mismatches only. No pending-Gate, HANDOFF next-action, current-task, current-gate, or evidence error occurred.
