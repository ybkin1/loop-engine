# Rollback / Recovery Plan v0.1

Task: T-0014
Gate: G-T-0014-METHOD-OPERATING-RULES-INSTALLATION

## T-0014 Recovery Scope

T-0014 does not modify `AGENTS.md`; therefore no runtime rollback is needed for this task.

If T-0014 evidence or governance records are wrong, recovery is a governance repair:

1. Stop before any installation or runtime action.
2. Record the incorrect artifact path and reason in `.ai/evidence/T-0014/commands.md`.
3. Ask the user to reject the pending gate or request repair.
4. Under a repair scope, update only `.ai` task/evidence/state records needed to correct the package.
5. Rerun `validate_state.py`.

## Future Installation Recovery Scope

If a later T-0015/new phase applies the approved diff and startup behavior is wrong:

These recovery actions require an approved future execution or recovery scope. T-0014 approval by itself would not authorize rollback or recovery writes.

1. Stop governed work immediately.
2. Capture `AGENTS.md` hash, file length, and the observed failure.
3. Restore `AGENTS.md` to the pre-installation baseline or apply the exact reverse patch from the approved diff.
4. Rerun `validate_state.py`.
5. Verify `AGENTS.md` hash matches the recovery target.
6. Record recovery evidence under the executing task evidence directory.
7. Keep the repaired method uninstalled until the user approves a corrected package.

## Baseline Needed For Future Recovery

Future execution must capture a fresh baseline before any write:

```text
AGENTS.md length
AGENTS.md SHA256
AGENTS.md last-write time
validate_state.py output
```

The T-0014 reference baseline for `AGENTS.md` is:

```text
SHA256=DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
Length=1574
LastWriteTime=2026-07-07T10:43:16.1314406+08:00
```

If the future baseline differs, the executing task must stop and ask for repair rather than applying this proposed diff.
