# Review Findings - T-0031

Verdict: `REPAIR_REQUIRED`

## P0 - Active Global Script Modification Breaches The Activation Boundary

T-0030 gate evidence says implementation only, with no installation or activation. The implementation changed the four globally used Project Governor scripts in place under `C:\Users\Administrator\.codex\skills\project-governor\scripts\`.

Evidence:

- T-0030 gate request: `.ai/evidence/T-0030/gate-request.G-T-0030-PROJECT-GOVERNOR-CLOSE-SESSION-HANDOFF-CONSISTENCY-REPAIR-IMPLEMENTATION.v0.1.md` says "Implementation only; no installation or activation."
- T-0030 gate record: `.ai/gates.yaml` records `installation_authorized: false`, `activation_authorized: false`, and `runtime_tool_enablement_authorized: false`.
- Current commands execute `C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py` and `audit_handoff.py`, the modified global paths.
- Current behavior reports six historical mismatches with exit code `2`; the T-0030 backup scripts did not have this behavior.
- Backup-to-current diff stats show changes in all four target scripts: `governor_lib.py` +203 lines, `close_session.py` +37/-17, `validate_state.py` +2, `audit_handoff.py` +56/-1.

Conclusion:

The implementation is not merely a dormant candidate. It is active behavior at the paths the project actually invokes. "Modified in place but not activated" is not accurate if activation means runtime/tool behavior becoming effective. T-0030 exceeded or at least conflicted with its approved boundary unless a separate user decision explicitly treats in-place global modification as permitted implementation.

## P1 - Action-Mode Validator Exists But Is Not Wired To Real Entry Points

`validate_action_mode()` is defined in `governor_lib.py`, and the test file directly imports and calls it. No production script imports or calls it.

Evidence:

- Definition: `governor_lib.py` defines `validate_action_mode()` at line 142.
- Search results show real usage only in `.ai/evidence/T-0030/test_project_governor_consistency.py`.
- `validate_state.py` imports `governance_invariant_errors`, `pending_gates`, and related helpers, but not `validate_action_mode()`.
- `audit_handoff.py` and `close_session.py` do not call `validate_action_mode()`.

Conclusion:

The function is tested as a library helper, but the five action modes are not enforced at real create/approve/execute entry points. T-0030's completion statement overstates action-mode enforcement.

## P1 - HANDOFF Next-Action Audit Is Marker-Based, Not Contract-Based

`audit_handoff.py` checks for English marker substrings in `## Next Session First Step`, not a structured next-action contract.

Evidence:

- `audit_handoff.py` line 67 computes `expected_action`.
- `audit_handoff.py` line 68 checks whether the marker string is contained in the HANDOFF section.
- `expected_next_action()` returns fixed English phrases such as `approve or reject`, `execute the approved task`, `change direction`, and `Resume the current task`.
- `close_session.py` similarly renders English next-action sentences from state.

Conclusion:

The audit catches some stale-state cases, but it cannot prove a Chinese or otherwise localized HANDOFF carries the exact task ID, gate ID, action mode, allowed scope, forbidden scope, and stop condition. A HANDOFF could contain the marker while still being semantically wrong.

## P1 - Final Validation Evidence Is Stale Relative To Final Code And Completion Claims

T-0030 saved final validation says `Ran 12 tests`, while T-0030 review/summary claims `13/13`.

Evidence:

- `.ai/evidence/T-0030/final-validation-output.txt` records `Ran 12 tests in 4.913s`.
- Current rerun of `.ai/evidence/T-0030/test_project_governor_consistency.py` records `Ran 13 tests` with exit code `0`.
- `.ai/evidence/T-0030/final-validation-output.txt` mtime is `2026-07-13T18:49:40+08:00`.
- `.ai/evidence/T-0030/test_project_governor_consistency.py` mtime is `2026-07-13T18:51:07+08:00`.
- `audit_handoff.py` target mtime is `2026-07-13T18:54:19+08:00`.
- `.ai/evidence/T-0030/final-target-hashes.v0.1.md` was captured at `2026-07-13T18:55:34+08:00`.
- T-0030 task notes say implementation completed at `2026-07-13T18:51:34+08:00`.

Conclusion:

The saved final validation is not bound to the final target script set. At least `audit_handoff.py` changed after the saved validation output and after the recorded implementation completion time. The current 13-test rerun is useful evidence for T-0031, but it does not retroactively make the T-0030 final-validation artifact fresh.

## P2 - Historical Blockers Must Stay Separate From T-0030 Repair

The current validator and HANDOFF audit still report T-0002, T-0004, T-0005, T-0007, T-0009, and T-0028 status mismatches.

Conclusion:

These mismatches prevent a clean validator/audit pass, but they are historical consistency work. They should not be bundled into T-0030 activation-boundary or evidence repair except as known external blockers.

## P2 - Pending-Task Status Vocabulary Is Under-Specified

T-0031 registration initially used `blocked_pending_user_decision`, but `TASK_STATUSES` in `governor_lib.py` does not include that value. The standard approval transition to `approved_not_started` resolved the validator blocker.

Conclusion:

Future pending-gate registration should use a validator-supported task status or update the schema and validator in a separately approved change. This is not a T-0030 implementation defect, but it affected the T-0031 gate lifecycle.
