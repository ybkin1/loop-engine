# T-0035 Implementation Commands v0.1

All candidate commands used explicit absolute candidate paths. Every Python process used `-B`; test and child-process environments set `PYTHONDONTWRITEBYTECODE=1` and removed inherited `PYTHONPATH`.

## Preflight

- Global/candidate/source SHA-256 verification: `52/52`, failures `0`.
- Candidate preflight inventory: `9` files, `2` directories, `0` reparse points, `0` cache/compiled artifacts.
- In-memory compilation before implementation: `5/5`.

## TDD Sequence

- RED run: `24` discovered tests; existing behavior tests passed and new lifecycle/HANDOFF/final-binding tests failed because the CLI and structured contracts did not yet exist.
- Lifecycle slice: `6/6` passed.
- HANDOFF/checkpoint slice: `8/8` passed.
- Final-validation slice: `2/2` passed.
- Integrated regression after coverage additions: `27/27` passed.
- Final interface/security regression after inline evidence and protected-global fingerprint support: `28/28` passed.

## Explicit Candidate Integration

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
C:\Python312\python.exe -B C:\Users\Administrator\.codex\loop-engine-lab\candidates\T-0030-project-governor-repair\scripts\close_session.py C:\Users\Administrator\.codex\loop-engine-lab
C:\Python312\python.exe -B C:\Users\Administrator\.codex\loop-engine-lab\candidates\T-0030-project-governor-repair\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
C:\Python312\python.exe -B C:\Users\Administrator\.codex\loop-engine-lab\candidates\T-0030-project-governor-repair\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab
```

Observed preliminary integration exit codes: close `0`, validate `0`, audit `0`.

## Final Validation

Exact argv:

```text
["C:\\Python312\\python.exe", "-B", "C:\\Users\\Administrator\\.codex\\loop-engine-lab\\candidates\\T-0030-project-governor-repair\\tests\\test_project_governor_consistency.py", "-v"]
```

- `validation_started_at`: `2026-07-18T16:58:09.4882061+08:00`
- `validation_completed_at`: `2026-07-18T16:58:26.8699996+08:00`
- `exit_code`: `0`
- `test_count`: `28`
- Result: `OK`

## Snapshot And Bind

- Snapshot froze `8` target/test fingerprints and `29` protected fingerprints.
- Two initial snapshot invocations were rejected by Windows PowerShell native-argv JSON quoting before action validation or fingerprinting; neither wrote a file.
- The successful invocation encoded JSON spaces as `\u0020`, preserving the exact parsed execution phrase.
- Final bind uses inline closed-world action/command JSON and durable references to the existing execution request and this command record; no transient evidence path is created.

No `py_compile`, installation, activation, runtime discovery, controller orchestration, downstream task creation, or real-project command was run.
