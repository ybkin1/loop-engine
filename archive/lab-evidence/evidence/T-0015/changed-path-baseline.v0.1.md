# Changed-Path Baseline v0.1

Task: T-0015
Captured at: 2026-07-08T16:26:02+08:00

## Target Baseline

Future execution target:

```text
AGENTS.md
```

Current target state before any T-0015 execution write:

```text
Path=C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md
Length=1574
LastWriteTime=2026-07-07T10:43:16
SHA256=DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
```

This matches the T-0014 baseline:

```text
DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
```

## Patch Baseline

Approved patch path:

```text
.ai/evidence/T-0014/agents-md.proposed-diff.v0.1.patch
```

Dry-run check:

```powershell
git apply --check --verbose -- 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0014\agents-md.proposed-diff.v0.1.patch'
```

Observed result:

```text
Checking patch AGENTS.md...
Exit code: 0
```

No patch was applied.

## Boundary

This baseline records readiness only. It does not authorize or perform the
`AGENTS.md` write.
