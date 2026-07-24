# T-0036 Fresh Independent Read-only Review Report v0.1

Completed: `2026-07-18T23:55:52.5241301+08:00`.

Reviewer: fresh agent `/root/t0036_fresh_independent_review`, launched with `fork_turns="none"`.

## Independence Declaration

- No parent or implementation-session conclusions were inherited or adopted.
- Preliminary leads were treated only as hypotheses and independently reproduced or adjusted from disk evidence.
- The reviewer performed a read-only review and wrote no project file.
- Temporary test fixtures were created only in system temporary directories and cleaned automatically.
- No installation, activation, runtime/controller/agent/automation/skill/MCP/plugin/hook/protocol enablement, repair, or downstream action occurred.

## Deterministic Results

- T-0035 final manifest: 37 subjects; SHA-256/size/mtime mismatches `0`.
- T-0036 freeze manifest: 60 subjects; mismatches `0`.
- T-0035 logical Gate: 63 fields, 11102 canonical JSON bytes, SHA-256 `1341D1E79A1D0715BEF7E1820ABEC5CFBE75EF75697E302F6FD6902892B57F63`.
- Candidate tests: exit `0`, `Ran 28 tests in 17.477s`, `OK`.
- Candidate/global `validate_state.py`: both exit `0`, state usable.
- Candidate/global `audit_handoff.py`: both exit `0`, handoff audit passed.
- Candidate inventory: 10 files, 2 directories, 0 cache/compiled artifacts, 0 reparse points.
- Candidate PATH/PYTHONPATH entries: 0/0.
- NOT_INSTALLED and NOT_ACTIVATED: present and unchanged.
- Config/skills/plugins/startup discovery search: no candidate reference found.

## Five-axis Coverage

- Correctness: lifecycle transitions, request identity, same-turn controls, transaction recovery, HANDOFF/checkpoint, stale fingerprints, and completion claims.
- Readability: naming, control flow, tests, duplicate canonicalization, and responsibility concentration.
- Architecture: authority/state ownership, HANDOFF producer/auditor coupling, serialization, transactions, lifecycle, and evidence boundaries.
- Security: inline JSON trust, authority/evidence provenance, paths/reparse points, and external protected subjects.
- Performance: recursive evidence hashing, whole-file reads, and missing count/size limits.

## Findings Summary

- P0: 0.
- P1: 7.
- P2: 2.
- P3: 0.

Full findings, evidence, reproduction, impact, and minimum repair guidance are in `t0036-review-findings.v0.1.md`.

## Preliminary Lead Dispositions

- Lead 1: `reproduced` — generated HANDOFF omits canonical main-controller orientation and audit does not require it.
- Lead 2: `reproduced` — canonical `state.current_gate_id` is null while structured HANDOFF projects the recent approved Gate.
- Lead 3: `reproduced` — `Unverified` derives from a literal `TBD` scan and can incorrectly output `none`.

## Residual Risks / Unverified

- No crash/power-loss-level process interruption was executed; transaction tests inject Python-level `os.replace` failures.
- No adversarial Windows reparse/TOCTOU concurrent test was performed.
- Non-file `.codex` database/session-index discovery references were not proven absent; configuration, skills, plugins, PATH/PYTHONPATH, protected hashes, and inventory were checked.
- No oversized evidence-tree benchmark was run; the performance finding follows from deterministic unbounded control flow.
- Existing 28 tests pass but do not cover authority binding, real command execution, cross-process same-turn enforcement, canonical orientation, lifecycle-derived Unverified, or stable-checkpoint rejection.

## Verdict

`REPAIR_REQUIRED`

This verdict is review evidence only. It is not user approval, user acceptance, project PASS, installation authorization, activation authorization, runtime enablement authorization, repair authorization, or downstream action authorization.
