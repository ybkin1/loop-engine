# Rollback Boundary v0.1

Task: T-0015

## Current State

No T-0015 write to `AGENTS.md` has occurred.

Current `AGENTS.md` baseline:

```text
SHA256=DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
Length=1574
```

## If The Execution Gate Is Approved Later

Before applying the patch, T-0015 must re-check that `AGENTS.md` still matches
the baseline above. If it differs, stop and request repair.

If the approved patch is applied and startup behavior fails, recovery requires
an explicit recovery scope. Recovery should restore `AGENTS.md` to the captured
pre-execution baseline or apply the exact reverse patch, then rerun
`validate_state.py` and record evidence under `.ai/evidence/T-0015/`.

## Boundary

This file is rollback planning evidence only. It does not authorize rollback,
apply the patch, or modify `AGENTS.md`.
