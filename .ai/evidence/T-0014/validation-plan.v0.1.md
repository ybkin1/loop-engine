# Validation Plan v0.1

Task: T-0014

## T-0014 Validation

| Step | Command / Check | Expected Result | Evidence |
| --- | --- | --- | --- |
| Startup validation | `C:\Python312\python.exe ...\validate_state.py <project-root>` | `[ok] state is usable` before T-0014 writes | `commands.md` |
| Baseline capture | hash and existence check for target/governance paths | `AGENTS.md` hash captured; T-0014 paths absent | `changed-path-baseline.v0.1.md` |
| Proposed diff syntax | read and review `agents-md.proposed-diff.v0.1.patch` | diff is evidence only and targets `AGENTS.md` | this plan + subagent review |
| Boundary check | verify no write to `AGENTS.md` | hash remains baseline value | final commands evidence |
| Final validation | run `validate_state.py` after gate registration | pending gate blocker for `G-T-0014-METHOD-OPERATING-RULES-INSTALLATION` | `commands.md` |

## Future T-0015 / New Phase Pre-Installation Validation

Before any future write:

1. Read latest user request.
2. Confirm project root.
3. Read `AGENTS.md`, `.ai/state.yaml`, `.ai/HANDOFF.md`, current task, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
4. Confirm explicit user approval of `G-T-0014-METHOD-OPERATING-RULES-INSTALLATION` is recorded.
5. Capture a fresh changed-path baseline for `AGENTS.md`.
6. Stop if the fresh `AGENTS.md` hash differs from the T-0014 baseline unless the user approves a repaired diff.
7. Run `validate_state.py`.
8. Verify the exact patch path and target list.

## Future Post-Installation Validation

If a later approved execution task writes `AGENTS.md`, it must verify:

1. The only runtime target changed is `AGENTS.md`.
2. The applied content matches the approved proposed diff.
3. `validate_state.py` returns the expected state for the executing task.
4. Startup behavior checks pass for governed work, simple Q&A, pending gate stop, and forbidden high-risk scope.
5. Handoff records installed status, residual risks, and recovery path.

## Evidence Paths

T-0014 evidence:

```text
.ai/evidence/T-0014/
```

Future execution evidence should be under the future task, for example:

```text
.ai/evidence/T-0015/
```
