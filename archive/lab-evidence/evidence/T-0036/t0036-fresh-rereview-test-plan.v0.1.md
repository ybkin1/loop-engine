# T-0036 Fresh Independent Rereview Test Plan v0.1

## Baseline

- Re-freeze 16 candidate files and 33 protected subjects from disk.
- Reject any unexplained SHA-256, size, mtime_ns, inventory, reparse, or cache/compiled drift.

## Behavior And Adversarial Checks

- F001/F002: invoke production authority paths with forged inline data/request IDs, replayed IDs, same-turn/process and multi-process sequences; require fail closed and no authority write. Separately inspect fixture-only lineage without treating it as host trust.
- F003: exercise controlled runner success, real nonzero exit with fake success text, environment/output/result tampering, stale target/protected fingerprints, argv mismatch, evidence-manifest drift, timeout, and shell-injection-shaped arguments.
- F004-F006: exercise valid/missing/drifted/unknown-field ProjectContinuity, exact Gate projection, structured lifecycle and unverified states; prohibit prose/TBD-derived semantics.
- F007: exercise absent registry, active transaction, in-flight actor, unconsumed delta, fence mismatch, evidence mismatch, missing/wrong successor ack, and fixture ack; prohibit production Stable.
- F008: inspect module dependency graph and independently compare producer/auditor algorithms and expected-state construction, not just imports or filenames.
- F009: exercise count/per-file/total-byte bounds, streaming, traversal, ADS, case collisions, symlink/reparse/junction boundaries where supported, and identity change during streaming.
- E2E-CURRENT-001: create a fresh current-project-shaped temporary mirror, run real candidate subprocesses, require positive HANDOFF/lifecycle/checkpoint/controlled-validation path, preserve `PASS_FIXTURE_ONLY`, and verify live project remains unchanged.

## Output

For each F001-F009, report severity, independent verdict, closure status, code evidence, test evidence, residual limitation, and whether installation eligibility changes. Repair evidence is corroboration only.
