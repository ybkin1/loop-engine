# T-0036 Independent Review Gate Request v0.1

## Decision Requested

Decide whether a later, separate execution turn may run a fresh independent read-only review of the frozen T-0035 isolated candidate repair and continuity/recovery interfaces.

- Task: `T-0036`
- Gate: `G-T-0036-INDEPENDENT-CANDIDATE-REPAIR-CONTINUITY-FRESH-SESSION-RECOVERY-REVIEW`
- Mode: `create_pending_gate`
- Gate status: `pending`
- Task status: `active`

Gate creation is not approval. Approval is not review execution. A later exact execution request is required after approval.

## Proposed Review

The future reviewer must independently:

- recompute all 37 T-0035 final-manifest fingerprints and rerun all 28 tests;
- inspect candidate/global validators and audits, the 10-file/2-directory clean inventory, global protected files, environment/discovery, and no-install/no-activate boundaries;
- review correctness, readability, architecture, security, and performance;
- review lifecycle transitions, same-turn/request-id guards, path containment, transaction recovery, structured HANDOFF/checkpoint behavior, fresh-session semantic recovery, authority containment, evidence binding, stale-evidence detection, and completion claims;
- evaluate behavior-level test coverage and `governor_lib.py` responsibility concentration;
- report P0/P1/P2/P3 findings and one allowed verdict.

Allowed verdicts are `PASS_FOR_INSTALLATION_CONSIDERATION`, `REPAIR_REQUIRED`, `BLOCKED`, and `USER_DECISION_REQUIRED`.

## Independence And Freeze

- Use a fresh independent read-only reviewer, preferably `fork_context=false`, without implementation-session conclusions.
- L0 performs preflight, scope control, and evidence closeout only.
- Before review, every frozen path, SHA-256, size, and `mtime_ns`, plus the logical T-0035 Gate fingerprint, must match the freeze manifest. Any mismatch returns `BLOCKED`.
- Preliminary finding leads are hypotheses only; the reviewer must independently reproduce, rebut, or adjust them.

## Strict Boundary

The future review is read-only except for T-0036 evidence and separately approved governance projections. It may not modify or repair the candidate, global Project Governor, `AGENTS.md`, T-0035, or old evidence; create downstream tasks/Gates; install or activate anything; enable runtime/controller/orchestration; or enter a real project.

Any PASS is evidence only, not user acceptance, project PASS, installation, activation, or permission to continue automatically.

## Decision Phrases

Approval: `批准 G-T-0036-INDEPENDENT-CANDIDATE-REPAIR-CONTINUITY-FRESH-SESSION-RECOVERY-REVIEW`

Rejection: `拒绝 G-T-0036-INDEPENDENT-CANDIDATE-REPAIR-CONTINUITY-FRESH-SESSION-RECOVERY-REVIEW`
