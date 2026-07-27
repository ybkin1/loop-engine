# T-0036 Path-Closure Fresh Rereview Gate Registration Commands v0.1

Gate: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-PATH-CLOSURE-REPAIR-V0-1`

Recorded at: `2026-07-24T17:48:00+08:00`

Mode: `create_pending_gate_only / rereview_not_started / baseline_not_accepted`

## Startup Validation

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

Startup pending Gate count was `0`. The worktree was already non-clean; unrelated modified and untracked files were preserved.

## Repair And Freeze Precheck

The repair validator was independently rerun with the project root and returned:

```text
catalog=46
authority_violations=0
register=46/46
status_conflicts=0
markdown_ids=46
coverage=46/46
freshness=46/46
phase_profile_ref=1/1
selection_materials=8/17
selection_templates=7/9
PASS
```

Exact repaired references were observed at two F-003 P1-P2 `evidence_packet` locations and one F-005 `selected_templates` location. The prohibited old paths were absent from those two YAML files.

The only baseline parser read 65 consecutive `path`, `size`, and 64-hex-character `sha256` triples from `.ai/evidence/T-0036/material-library-residual-path-repair-freeze-manifest.v0.1.md`.

| check | before registration | after registration |
| --- | ---: | ---: |
| declared subjects | 65 | 65 |
| parsed subjects | 65 | 65 |
| unique paths | 65 | 65 |
| matching path/size/SHA-256 | 65/65 | 65/65 |
| mismatches | 0 | 0 |
| manifest size | 9835 | 9835 |
| manifest SHA-256 | `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC` | unchanged |

## Registration Delta

Only these seven allowed paths belong to this registration:

- `.ai/evidence/T-0036/material-library-path-rereview-gate-request.v0.1.md`
- `.ai/evidence/T-0036/material-library-path-rereview-changed-path-baseline.v0.1.md`
- `.ai/evidence/T-0036/material-library-path-rereview-control-manifest.v0.1.md`
- `.ai/evidence/T-0036/material-library-path-rereview-registration-commands.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

Non-self-referential registration artifact fingerprints:

| path | size | SHA-256 |
| --- | ---: | --- |
| `material-library-path-rereview-gate-request.v0.1.md` | 6340 | `F9AE9396F733FD7A0D95014745A4CA573ED446B281FFFE0AD86A3BA734F134A8` |
| `material-library-path-rereview-changed-path-baseline.v0.1.md` | 2132 | `A8CFD4368E86696AB1986BA155D1C64CC2C53B3599DEE5412696BE3894D76BA4` |
| `material-library-path-rereview-control-manifest.v0.1.md` | 4760 | `65D1D9EF4F98CD73A68AAE3E6119D62B08EEA8A91811A8FB888DBF693C70876B` |

This registration-commands file excludes its own fingerprint to avoid self-reference.

## Post-Registration State

```text
YAML_PARSE=PASS
PENDING_COUNT=1
PENDING_IDS=G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-PATH-CLOSURE-REPAIR-V0-1
TARGET_STATUS=pending
TARGET_DECISION=pending
TARGET_EXECUTION=pending_user_decision

validate_state.py captured exit=2
[error] Pending gate(s) require user decision before continuing: G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-PATH-CLOSURE-REPAIR-V0-1

audit_handoff.py captured exit=2
[error] Pending gate(s) not resolved: G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-PATH-CLOSURE-REPAIR-V0-1

git diff --check
exit 0; no output
```

An intermediate handoff audit also reported semantic mismatches for `当前讨论主题` and `当前问题与状态`. Both were corrected deterministically inside the allowed `.ai/HANDOFF.md` projection; the final audit has only the intended pending-Gate blocker.

## Absence And Boundary Assertions

- All four future rereview output files remain absent.
- No fresh independent rereview was executed and no reviewer subagent was created during Gate preparation.
- No frozen object, freeze manifest, existing evidence, candidate, test, task, task graph, global Project Governor, Runtime, Agent, deployment, or real-project path was modified by this registration.
- Candidate-baseline acceptance, version freeze, T-0036 closeout, T-0037 review creation/execution, and Host Integration did not occur.

## Required Next Decision

Gate creation is not approval. The next authorized action is exactly one user decision:

- `批准 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-PATH-CLOSURE-REPAIR-V0-1`
- `拒绝 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-PATH-CLOSURE-REPAIR-V0-1`

Approval still does not execute rereview. After approval, the user must separately send `执行 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-PATH-CLOSURE-REPAIR-V0-1`; only then may a genuinely fresh independent reviewer subagent perform the bounded rereview and return an evidence-only verdict.
