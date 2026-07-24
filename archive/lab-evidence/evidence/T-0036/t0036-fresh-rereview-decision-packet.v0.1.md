# T-0036 Fresh Independent Rereview Decision Packet v0.1

## Decision

Decide whether to authorize a genuinely fresh independent reviewer to perform a read-only rereview of all nine original T-0036 findings against a new on-disk freeze of the repaired isolated candidate.

Approval phrase: `批准 G-T-0036-FRESH-INDEPENDENT-REREVIEW-ALL-FINDINGS-V0-1`

Rejection phrase: `拒绝 G-T-0036-FRESH-INDEPENDENT-REREVIEW-ALL-FINDINGS-V0-1`

Approval is not execution. A later separate message must say `执行已批准的 G-T-0036-FRESH-INDEPENDENT-REREVIEW-ALL-FINDINGS-V0-1`.

## Required Independence And Freeze

- Use a genuinely fresh reviewer that has not inherited the repair executor's conclusion.
- At execution start, enumerate the candidate directly from disk and record every file's path, SHA-256, size, mtime_ns, plus directory count, reparse status, and cache/compiled-artifact status.
- Independently freeze every protected subject and compare it with the 33-subject repair-final baseline.
- Stop on unexplained drift; do not review a silently changed subject.
- Treat the repair report, controlled manifest, tests, validators, and prior AI statements as evidence to challenge, not findings already closed.

## Required Finding Review

| Finding | Repair executor classification | Independent question |
|---|---|---|
| T0036-F001 | `SECURELY_ISOLATED_AUTHORITY_LIFECYCLE_UNAVAILABLE` | Does every production authority transition fail closed without a trusted host message/turn identity, with no false availability claim? |
| T0036-F002 | `SECURELY_ISOLATED_AUTHORITY_LIFECYCLE_UNAVAILABLE` | Can any multi-process or replay sequence cross create/approve/execute without separately trusted turns, or is production lifecycle simply unavailable? |
| T0036-F003 | `PASS` | Does a controlled runner actually execute approved argv and independently bind environment, outputs, exit, test identity, time, evidence, and fingerprints? |
| T0036-F004 | `PASS` | Is HANDOFF generated from valid `ProjectContinuity/v1`, with missing/drifted input preserving the old HANDOFF and failing closed? |
| T0036-F005 | `PASS` | Does the Gate projection copy canonical `state.current_gate_id` exactly and keep approved execution identity separate? |
| T0036-F006 | `PASS` | Are lifecycle and Unverified projections entirely structured, without prose or TBD scanning? |
| T0036-F007 | `PASS_FIXTURE_ONLY` | Are registry, quiescence, fence, evidence, and successor ack proven; is only `STABLE_FIXTURE_ONLY` possible in fixtures while production Stable remains unavailable? |
| T0036-F008 | `PASS_STRUCTURAL` | Are responsibilities separated and does the auditor reconstruct expected state independently without importing or sharing the producer path? |
| T0036-F009 | `PASS` | Is hashing bounded by an approved manifest, streamed, identity-stable, and resistant to traversal, ADS, collision, symlink, junction, and reparse escape? |

The reviewer may confirm, reject, narrow, or reclassify each executor result and severity. It must output a separate evidence-backed verdict and closure state for every finding.

## Contract And E2E Focus

- `ProjectContinuity/v1`: verify exact normative sources, `.ai/project_continuity.yaml`, schema enforcement, authorized writer/read-only candidate roles, missing behavior, and source/semantic/file hash binding.
- `TransactionRegistry/v1`: verify `.ai/transaction_registry.yaml`, ownership, generation fence, in-flight/delta/quiescence rules, successor acknowledgement, missing behavior, and hash binding.
- `EvidenceManifest/v1`: verify `.ai/evidence/<task-id>/evidence-manifest.v1.yaml`, create-only responsibility, schema, missing behavior, count/byte limits, streaming, fingerprints, and reparse boundaries.
- Controlled runner: independently exercise success, nonzero exit, fake-success metadata, environment drift, output tampering, stale fingerprint, and manifest drift.
- `E2E-CURRENT-001`: rerun real candidate subprocesses in a newly built current-project-shaped temporary mirror. Preserve `PASS_FIXTURE_ONLY`; do not claim production Stable or authority availability from fixtures.
- Live-project check: distinguish global projection validator/audit exit `0` from candidate `PROJECT_CONTINUITY_MISSING` fail-closed exit because live continuity state is absent.

## Protected Boundaries

The rereview is read-only. It must verify all 33 protected subjects, including `AGENTS.md`, global Project Governor files/templates, `.ai/PROJECT.md`, `.ai/CONTRACTS.md`, both T-0034 continuity contracts, and candidate `NOT_INSTALLED` / `NOT_ACTIVATED`. It must also verify no PATH/PYTHONPATH, startup/discovery, live structured-state, installation, activation, runtime, controller, agent, automation, skill, MCP, plugin, hook, protocol, T-0037, or real-project effect.

## Risks And Stop Conditions

- The largest interpretation risk is converting safe unavailability for F001/F002 into a false claim of restored functionality or installation eligibility.
- Fixture-only and structural evidence can conceal missing live integration; F007 and F008 must retain their distinct evidence levels unless independently disproven.
- Shared test and implementation assumptions can create correlated false confidence; the reviewer must add adversarial checks and reason independently.
- Stop on drift, missing reviewer independence, need for host/runtime integration, or any requested write outside review evidence and necessary governance projection.

The future rereview must stop after its report. It cannot install, activate, create T-0037, enter a real project, or turn evidence into user acceptance.

## Exact Future Write Boundary

After approval and the later exact execution request, the reviewer may update only `.ai/gates.yaml`, `.ai/state.yaml`, `.ai/task_graph.yaml`, `.ai/tasks/T-0036.md`, and `.ai/HANDOFF.md` as necessary to project the rereview result. New evidence is restricted to the exact `t0036-fresh-rereview-*` execution paths enumerated in the Gate record, including the execution request, fresh freeze, independence statement, test plan, commands/results, per-finding report, overall report, protected-boundary postcheck, validation, changed-path manifest, and failure record.

No candidate file, protected subject, repair evidence, original review evidence, T-0035 evidence, live structured-state file, or differently named path is writable under this Gate.
