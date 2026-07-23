# T-0036 Commands

Scope: registration and read-only preflight only. No formal review, repair, installation, activation, or downstream action was executed.

## Startup And Source-of-truth

- Read the attached request as UTF-8.
- Read `$project-governor` and `$code-review-and-quality` skill instructions.
- Read `.ai/state.yaml`, `.ai/HANDOFF.md`, `.ai/tasks/T-0035.md`, `.ai/gates.yaml`, `.ai/task_graph.yaml`, conventions, decisions, and Git status/log.
- Ran global `validate_state.py`; exit code `0` and `[ok] state is usable`.
- Parsed all 56 unique Gate records; pending count was `0`.
- Confirmed T-0036 task/evidence/Gate/task_graph records were absent.

## Frozen Sources

- Read T-0031 findings/repair plan, T-0033 boundary/provenance/recovery evidence, T-0034 canonical continuity/HANDOFF/checkpoint/additive repair chain, and required T-0035 execution evidence.
- Read all 10 candidate files and the current global Project Governor scripts plus project `AGENTS.md`.
- Snapshotted 60 file subjects and one logical T-0035 Gate record.
- Registration-time check found `0` mismatches among the 37 T-0035 final-manifest subjects.

## Preliminary Lead Reproduction

All Python processes used `-B`; audit environments used `PYTHONDONTWRITEBYTECODE=1` and removed inherited `PYTHONPATH`.

- Explicit candidate `audit_handoff.py`: exit `0`.
- Global `audit_handoff.py`: exit `0`.
- Parsed registration-time HANDOFF hash, structured Gate field, orientation phrases, and `Unverified` section without writing files.
- Candidate inventory: 10 files, 2 directories, 0 cache/compiled artifacts, 0 reparse points.
- Candidate root entries in `PATH`: 0; in `PYTHONPATH`: 0.

## Registration

- Created only the T-0036 task, pending Gate, task_graph/state/HANDOFF projections, and exact evidence files authorized by the user.
- No candidate, global Project Governor, `AGENTS.md`, T-0035, old evidence, environment, installation, activation, runtime, or downstream path was modified.

## Post-registration Commands

The exact validator/audit results and containment checks are recorded in the corresponding T-0036 registration evidence files.
