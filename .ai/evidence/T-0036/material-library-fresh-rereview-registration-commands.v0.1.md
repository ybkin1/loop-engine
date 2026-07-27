# T-0036 Fresh Independent Rereview Gate Registration Commands v0.1

Gate: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`

Recorded at: `2026-07-24T15:56:12+08:00`

Mode: `create_pending_gate_only / rereview_not_started`

## Deterministic Startup

```text
validate_state.py
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0036
[ok] state is usable

audit_handoff.py
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0036

git diff --check
exit 0; no output
```

Startup `git status --porcelain -uall` was non-clean. Existing modified and untracked files were preserved. Startup pending Gate count was `0`.

## Freeze Precheck And Postcheck

The parser read exact consecutive `path`, `size`, and 64-hex-character `sha256` fields from `.ai/evidence/T-0036/material-library-repair-freeze-manifest.v0.1.md`.

| check | before registration | after registration |
| --- | ---: | ---: |
| declared subjects | 65 | 65 |
| parsed subjects | 65 | 65 |
| unique paths | 65 | 65 |
| matching path/size/SHA-256 | 65/65 | 65/65 |
| mismatches | 0 | 0 |
| manifest size | 10029 | 10029 |
| manifest SHA-256 | `1CE2751794FBF643CD68976A70EFBD31FF6CACD3EECB0F70746BE45F0236783F` | unchanged |
| ASCII `?` count | 0 | 0 |

The first experimental regular-expression parser matched no records because its line-boundary assumption was wrong; it made no writes. The corrected line-structured parser produced the results above. No Gate registration proceeded until `65/65` was established.

## Registration Delta

Only these seven allowed paths belong to this registration:

- `.ai/evidence/T-0036/material-library-fresh-rereview-gate-request.v0.1.md`
- `.ai/evidence/T-0036/material-library-fresh-rereview-changed-path-baseline.v0.1.md`
- `.ai/evidence/T-0036/material-library-fresh-rereview-control-manifest.v0.1.md`
- `.ai/evidence/T-0036/material-library-fresh-rereview-registration-commands.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

The baseline records pre-registration hashes for the three governance projections and `absent` markers for additive Gate and future rereview evidence. The final non-self-referential Gate artifact fingerprints are:

| path | size | SHA-256 |
| --- | ---: | --- |
| `material-library-fresh-rereview-gate-request.v0.1.md` | 7742 | `0432EA85A607904A74DD9456AE5C854FD12EBBF72B832DAE80C7EA6B6E304032` |
| `material-library-fresh-rereview-changed-path-baseline.v0.1.md` | 2331 | `9BFEC2DBAD44BBE0BD5E6E2AA714731E12E77CDB8135C096F357C4A0347A0EB4` |
| `material-library-fresh-rereview-control-manifest.v0.1.md` | 3979 | `550EB8917D94CCE68D608AF179E819AEA4489ABF0DA1B4CC71CE8C3DAF0196E4` |

This registration-commands file intentionally excludes its own fingerprint to avoid self-reference.

## Post-Registration Validation

```text
YAML_PARSE=PASS
PENDING_COUNT=1
PENDING_IDS=G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1
TARGET_STATUS=pending
TARGET_DECISION=pending
TARGET_EXECUTION=pending_user_decision

validate_state.py captured exit=2
[error] Pending gate(s) require user decision before continuing: G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1

audit_handoff.py captured exit=2
[error] Pending gate(s) not resolved: G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1

git diff --check
exit 0; no output
```

The validator and handoff audit have exactly the intended pending-Gate blocker. HANDOFF semantic classification and next-action markers were corrected during registration validation; no additional audit error remains.

## Absence And Scope Assertions

- `material-library-fresh-rereview-approval-record.v0.1.md`: absent.
- All four future rereview output files: absent.
- No substantive rereview, repair, candidate-baseline decision, version freeze, T-0036 closeout, T-0037 review, or Host Integration occurred.
- No frozen subject, freeze manifest, original review, repair, full-suite, reconciliation, candidate, global Project Governor, skill, MCP, agent, plugin, hook, automation, protocol, runtime, deployment, database, permission, secret, payment, production-data, migration, or external business-project path was modified by this registration.

## Required Next Decision

Gate creation is not approval. The next authorized action is exactly one explicit user decision:

- `批准 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`
- `拒绝 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`

Approval must be recorded as approved but not started. A later separate `执行 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1` request is still required before rereview.
